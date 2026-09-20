# -*- coding: utf-8 -*-
"""增量下载器：并行 + 幂等 + 收敛遍，专用于长跑中途同步。

★ 与 03_run_16ns_pipeline.py 的 stage_fetch 同逻辑，但：
  1. 不做帧抽取（全量），因为中途抽帧会因帧数变化而索引漂移、幂等失效；
     （抽帧索引 = i*(n-1)/(frames-1)，n 增长 ⇒ 索引漂移 ⇒ 已下帧被判不符而重下）
  2. 单独可反复调用 —— 每次只补"远端有而本地缺/大小不符"的文件；
  3. **每 worker 线程一个复用会话**（threading.local）—— 见下方实测对比。

★★ 会话策略实测（2026-09-15，618 文件 / 5.1 GB）
  | 策略 | 失败率 | 速率 |
  |---|---|---|
  | 逐文件独立建连 | **233/618 = 37.7%** | 0.63 MB/s |
  | 每线程复用会话 + 单文件 3 次重试 | **1/170 = 0.6%** | **4.81 MB/s** |
  ⇒ 逐文件建连的 SSH 握手开销会触发服务端限流，**反而不如复用**。
  但**绝不能跨线程共享一个会话**（paramiko 非线程安全；曾致 `as_completed`
  永不返回的静默挂死——见坑位 P31）。正确折中 = 线程内复用、线程间隔离。

★ 幂等判定用"文件大小"而非 md5：chk 每帧大小恒定（10,110,924 B），
  中断残留的半截文件必然尺寸不符 ⇒ 可靠识别。md5 留作收敛遍的可选加强。

★ 唯一"永久失败"的正常情形 = 运行中的 `wsl_run_*.log`（远端持续增长，
  本地永远追不上其即时大小）。作业结束后再取即可，非缺陷。

★ chk-only 默认策略 (2026-09-16 全场景统一, flash/flash_run/remote/fetch_policy.py):
  默认只同步 chk + 日志; plt 须显式 --with-plt。--no-plt/--only-chk 保留为兼容别名。

用法:
  python _fetch_incremental.py                 # chk-only: 同步 chk+日志 (默认)
  python _fetch_incremental.py --with-plt      # 连 plt 一起同步
  python _fetch_incremental.py --jobs 6
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _longrun_lib as L  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default=L.ACCOUNT_NCE)
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--no-plt', action='store_true',
                    help='(兼容别名) 只同步 chk — 2026-09-16 起即为默认')
    ap.add_argument('--only-chk', action='store_true',
                    help='(兼容别名) 只同步 chk — 2026-09-16 起即为默认')
    ap.add_argument('--with-plt', dest='with_plt', action='store_true',
                    help='★ 连 plt 一起同步 (默认 chk-only, 2026-09-16 定案)')
    ap.add_argument('--dir', default=None, help='本地目标目录')
    args = ap.parse_args()

    local_dir = Path(args.dir) if args.dir else (L.FLASH_OUT / f'hpc_{args.account}_16ns')
    local_dir.mkdir(parents=True, exist_ok=True)

    rm = L.R._HpcRemote(args.account)
    rm.__enter__()
    try:
        obj = L.abs_snb_home(rm) + '/' + L.M.OBJDIR
        L.log(f'远端源: {obj}')
        L.log(f'本地目标: {local_dir}')

        names, sizes = L.remote_list(rm, obj)
        rsize = dict(zip(names, sizes))

        # ★ chk-only 默认 (2026-09-16 全场景统一): 选择逻辑统一走
        #   flash/flash_run/remote/fetch_policy.py (frames=0: 中途同步不抽帧,
        #   否则索引漂移破坏幂等); --no-plt/--only-chk 为兼容别名(现即默认)。
        #   独立脚本用 importlib 按路径加载策略模块, 避免 import flash 副作用。
        import importlib.util as _ilu
        _fp = None
        for _root in Path(__file__).resolve().parents:
            _f = _root / 'flash' / 'flash_run' / 'remote' / 'fetch_policy.py'
            if _f.is_file():
                _spec = _ilu.spec_from_file_location('_fetch_policy', _f)
                _fp = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_fp)
                break
        if _fp is None:
            raise ImportError('fetch_policy.py not found above ' + str(__file__))
        want, sel = _fp.select_fetch_files(
            names, basenm=L.M.BASENM,
            log_names=[getattr(L.M, 'LOG_FILE', '') or ''],
            with_plt=bool(getattr(args, 'with_plt', False)),
            frames=0)
        if sel['plt_skipped']:
            L.log(f"★ chk-only 模式: 跳过远端 {sel['n_plt']} 个 plt 文件 "
                  f'(--with-plt 可改)')

        nchk = sel['n_picked']
        nplt = 0 if sel['plt_skipped'] else sel['n_plt']
        tot_b = sum(rsize.get(n, 0) for n in want)
        L.log(f'远端: {len(want)} 文件 (chk={nchk}, plt={nplt}) / {L.human(tot_b)}')

        have = {p.name: p.stat().st_size for p in local_dir.iterdir() if p.is_file()}
        todo = [n for n in want if have.get(n) != rsize.get(n, -1)]
        already = len(want) - len(todo)
        L.log(f'本地已有(大小匹配): {already}；需下载: {len(todo)} '
              f'({L.human(sum(rsize.get(n, 0) for n in todo))})')
        if not todo:
            L.log('✓ 全部已同步', 'OK')
            return 0

        # ── 并行下载（★ 逐文件独立建连，避免共享会话挂死）──
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        lock = threading.Lock()
        stats = {'ok': 0, 'fail': 0, 'bytes': 0}
        t0 = time.time()

        def _one(nm: str):
            rp = f'{obj}/{nm}'
            lp = local_dir / nm
            exp = rsize.get(nm)
            tt = time.time()
            # ★★ 修 (2026-09-15): 原实现**每文件独立建连** → 618 次 SSH 握手，
            #   实测 233/618 = 37.7% 失败（握手开销 + 服务端限流）。
            #   改为 **每 worker 线程一个复用会话** (threading.local)：
            #     - 线程间互不共享会话 ⇒ 规避 paramiko 非线程安全（挂死事故根因）；
            #     - 线程内复用 ⇒ 握手次数从 N 降到 workers。
            #   并加单文件级重试（3 次 + 退避）兜住偶发 socket 10054。
            sess = _tls.__dict__.get('s')
            if sess is None:
                sess = L.R._HpcRemote(args.account)
                sess.__enter__()
                _tls.s = sess
            last_exc = None
            for attempt in range(1, 4):
                try:
                    ok = sess.download(rp, str(lp))
                    dt = time.time() - tt
                    act = lp.stat().st_size if lp.exists() else -1
                    good = bool(ok) and act > 0 and (exp is None or act == exp)
                    if good:
                        return nm, True, act, dt, 'size-ok'
                    last_exc = f'sizeFAIL(act={act},exp={exp})'
                except Exception as e:
                    last_exc = f'{type(e).__name__}'
                    # 会话可能已坏 → 丢弃并重建
                    try:
                        sess.__exit__(None, None, None)
                    except Exception:
                        pass
                    _tls.s = None
                    try:
                        sess = L.R._HpcRemote(args.account)
                        sess.__enter__()
                        _tls.s = sess
                    except Exception:
                        sess = None
                if attempt < 3:
                    time.sleep(2 * attempt)
            return nm, False, (lp.stat().st_size if lp.exists() else -1), \
                time.time() - tt, f'FAIL:{last_exc}'

        workers = min(args.jobs, max(1, len(todo)))
        L.log(f'启动 {workers} 线程并行下载（每线程复用会话 + 单文件 3 次重试）...')
        import threading as _th
        _tls = _th.local()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_one, nm): nm for nm in todo}
            done = 0
            for fu in as_completed(futs):
                done += 1
                try:
                    nm, good, act, dt, gate = fu.result()
                except Exception as e:
                    with lock:
                        L.log(f'  ✗ {futs[fu]}: {type(e).__name__}: {e}', 'WARN')
                        stats['fail'] += 1
                    continue
                with lock:
                    if good:
                        stats['ok'] += 1
                        stats['bytes'] += act
                        rate = act / 1e6 / dt if dt > 0 else 0
                        if done % 20 == 0 or done == len(todo):
                            L.log(f'  [{done}/{len(todo)}] ✓ {nm} '
                                  f'{L.human(act)} {dt:.1f}s {rate:.2f}MB/s')
                    else:
                        stats['fail'] += 1
                        L.log(f'  [{done}/{len(todo)}] ✗ {nm} (act={act} {gate})', 'WARN')

        el = time.time() - t0
        # ★ 修 (2026-09-15): 原写 `L.human(el)` —— 把**秒数当字节**格式化，
        #   日志出现 "3.6 GB / 1.1 KB" 的荒谬分母。应为人读时长。
        L.log(f'并行下载完成: 成功 {stats["ok"]}, 失败 {stats["fail"]}, '
              f'{L.human(stats["bytes"])} / {L.human_dur(el)} '
              f'= {stats["bytes"]/1e6/max(el,1e-9):.2f} MB/s')

        # ── 收敛遍：顺序重下缺失/不符者 ──
        def _sizes():
            return {p.name: p.stat().st_size for p in local_dir.iterdir() if p.is_file()}

        bad = [n for n in want if _sizes().get(n) != rsize.get(n, -1)]
        if bad:
            L.log(f'★ 收敛遍: 顺序重下 {len(bad)} 个...', 'WARN')
            for n in bad:
                lp = local_dir / n
                rp = f'{obj}/{n}'
                try:
                    if lp.exists():
                        lp.unlink()
                    w = L.R._HpcRemote(args.account)
                    w.__enter__()
                    try:
                        ok = w.download(rp, str(lp))
                    finally:
                        try:
                            w.__exit__(None, None, None)
                        except Exception:
                            pass
                    act = lp.stat().st_size if lp.exists() else -1
                    good = bool(ok) and act == rsize.get(n, -1)
                    L.log(f'  [converge] {"OK" if good else "FAIL"} {n} {act}',
                          'OK' if good else 'WARN')
                except Exception as e:
                    L.log(f'  [converge] ✗ {n}: {type(e).__name__}: {e}', 'WARN')

        still = [n for n in want if _sizes().get(n) != rsize.get(n, -1)]
        fs = [f for f in local_dir.iterdir() if f.is_file()]
        tot = sum(f.stat().st_size for f in fs)
        L.log(f'本地最终: {len(fs)} 文件 / {L.human(tot)}')
        if still:
            L.log(f'★ 仍有 {len(still)} 个不完整 → 重跑本脚本会自动补齐', 'WARN')
            return 2
        L.log('✓ 同步完成', 'OK')
        return 0
    finally:
        try:
            rm.__exit__(None, None, None)
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())
