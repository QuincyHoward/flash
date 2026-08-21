# -*- coding: utf-8 -*-
"""
HTML 测试报告生成器
====================

读取 test/test_summary.json, 生成交互式 HTML 测试报告。
报告内容:
  - 总览统计 (材料数 / 步骤成功失败 / 图像数 / 耗时)
  - 每个材料的参数卡片 (成分/原子量/网格/能群)
  - 每个任务的缩略图画廊 (点击放大) + 拟合优度表
  - 失败步骤的错误信息

用法:
    python generate_report.py [--summary test_summary.json] [--out report.html]
"""

import argparse
import base64
import io
import json
import os
import sys

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:                                   # noqa: BLE001
    _HAS_PIL = False

HERE = os.path.dirname(os.path.abspath(__file__))
# 缩略图最大宽度 (px), 用于画廊预览内嵌, 控制报告体积
THUMB_W = 480


def _thumb_data(uri):
    """生成轻量缩略图 base64 (预览用); 完整原图通过相对路径链接打开。"""
    if not uri or not os.path.exists(uri):
        return None
    if not _HAS_PIL:
        # 退化: 直接内嵌原图 (体积大但可用)
        ext = os.path.splitext(uri)[1].lower().lstrip(".")
        mime = "image/png" if ext in ("png", "PNG") else "image/jpeg"
        with open(uri, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    try:
        im = Image.open(uri)
        w, h = im.size
        if w > THUMB_W:
            im = im.resize((THUMB_W, int(h * THUMB_W / w)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:                               # noqa: BLE001
        return None


def _task_label(key):
    return {
        "A": "A. 2D Heatmaps (彩图)",
        "B": "B. 1D Curves (变化曲线)",
        "C": "C. Time Series (时间序列)",
        "D": "D. Fittings (函数拟合)",
        "E": "E. EOS Paths (物态方程路径)",
    }.get(key, key)


def _info_table(info):
    """将 info dict 渲染为 HTML 小表 (拟合参数等)"""
    if not info:
        return ""
    rows = []
    for k, v in info.items():
        if isinstance(v, dict):
            sub = ", ".join(f"{sk}={sv}" for sk, sv in v.items())
            rows.append(f"<tr><td>{k}</td><td>{sub}</td></tr>")
        elif isinstance(v, list):
            rows.append(f"<tr><td>{k}</td><td>{', '.join(map(str, v))}</td></tr>")
        else:
            rows.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
    if not rows:
        return ""
    return ("<table class='info'><tbody>" +
            "".join(rows) + "</tbody></table>")


def build_html(summary):
    mats = summary.get("materials", [])
    cards = []
    for m in mats:
        sp = m.get("species", "?")
        aw = m.get("atomwt")
        aw_s = " / ".join(f"{v:.3f}" for v in aw) if aw else "unknown"
        gb = m.get("group_bounds", [])
        gb_s = ", ".join(f"{v:.2e}" for v in gb) if gb else "-"
        recs = m.get("results", [])

        gallery = []
        for r in recs:
            files = r.get("files", [])
            cls = "ok" if r.get("ok") else "fail"
            info_html = _info_table(r.get("info", {}))
            imgs = []
            for fp in files:
                data = _thumb_data(fp)
                rel = os.path.relpath(fp, HERE).replace("\\", "/") if fp else ""
                if data:
                    imgs.append(
                        f"<figure><a href='{rel}' target='_blank' "
                        f"title='点击打开原图: {os.path.basename(fp)}'>"
                        f"<img loading='lazy' src='{data}' "
                        f"alt='{os.path.basename(fp)}'></a>"
                        f"<figcaption>{os.path.basename(fp)}</figcaption>"
                        f"</figure>")
                else:
                    imgs.append(f"<div class='missing'>{rel} (缺失)</div>")
            err = ""
            if not r.get("ok"):
                err = (f"<div class='err'>ERROR: {r.get('error','')}</div>")
            gallery.append(
                f"<section class='task {cls}'>"
                f"<h4>[{r.get('task')}] {r.get('name')} "
                f"<span class='badge {cls}'>{'OK' if r.get('ok') else 'FAIL'}"
                f" · {r.get('elapsed_s','-')}s</span></h4>"
                f"{info_html}{err}"
                f"<div class='gallery'>{''.join(imgs)}</div>"
                f"</section>")

        cards.append(f"""
        <article class='card'>
          <header>
            <h3>{m.get('name','?')}</h3>
            <span class='sp'>{sp}</span>
          </header>
          <table class='meta'>
            <tr><td>Atomwt (amu)</td><td>{aw_s}</td></tr>
            <tr><td>Grid</td><td>ntemp={m.get('ntemp')}, ndens={m.get('ndens')}, ngrups={m.get('ngrups')}</td></tr>
            <tr><td>T range (eV)</td><td>{m.get('T_range')}</td></tr>
            <tr><td>n_i range (cm⁻³)</td><td>{m.get('nion_range')}</td></tr>
            <tr><td>Group bounds (eV)</td><td>{gb_s}</td></tr>
          </table>
          <div class='tasks'>{''.join(gallery)}</div>
        </article>""")

    ok = summary.get("n_steps_ok", 0)
    fail = summary.get("n_steps_fail", 0)
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IONMIX eosop_pro 测试报告</title>
<style>
  :root {{ --bg:#f7f8fa; --card:#fff; --line:#e2e6ea; --ok:#2e9e4f;
          --fail:#d23b3b; --accent:#1f6feb; --txt:#1f2328; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         background:var(--bg); color:var(--txt); line-height:1.5; }}
  header.top {{ background:linear-gradient(120deg,#1f6feb,#0b3d91); color:#fff;
                padding:24px 32px; }}
  header.top h1 {{ margin:0 0 6px; font-size:26px; }}
  header.top p {{ margin:2px 0; opacity:.9; font-size:14px; }}
  .wrap {{ max-width:1280px; margin:0 auto; padding:24px 32px; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
            gap:14px; margin-bottom:26px; }}
  .stat {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:16px; text-align:center; }}
  .stat .num {{ font-size:30px; font-weight:700; }}
  .stat .lab {{ font-size:13px; color:#666; }}
  .filters {{ margin:0 0 18px; font-size:13px; color:#555; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
           padding:20px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  .card header {{ display:flex; align-items:baseline; gap:12px; border-bottom:1px
                  solid var(--line); padding-bottom:10px; margin-bottom:12px; }}
  .card h3 {{ margin:0; font-size:20px; }}
  .sp {{ font-size:13px; color:#666; background:#eef2f7; padding:3px 9px;
         border-radius:20px; }}
  table.meta {{ border-collapse:collapse; font-size:13px; margin-bottom:14px; }}
  table.meta td {{ border:1px solid var(--line); padding:5px 10px; }}
  table.meta td:first-child {{ color:#555; background:#fafbfc; width:150px; }}
  section.task {{ border:1px solid var(--line); border-radius:10px; padding:12px;
                  margin:12px 0; }}
  section.task.fail {{ border-color:var(--fail); background:#fff6f6; }}
  section.task.ok {{ border-color:#cfe9d6; }}
  section.task h4 {{ margin:0 0 8px; font-size:15px; display:flex; justify-content:space-between;
                    align-items:center; }}
  .badge {{ font-size:11px; padding:2px 8px; border-radius:10px; color:#fff; }}
  .badge.ok {{ background:var(--ok); }} .badge.fail {{ background:var(--fail); }}
  .gallery {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
              gap:12px; }}
  figure {{ margin:0; }}
  figure img {{ width:100%; border:1px solid var(--line); border-radius:8px;
                cursor:zoom-in; }}
  figcaption {{ font-size:11px; color:#666; margin-top:3px; word-break:break-all; }}
  .missing {{ padding:20px; background:#f0f0f0; border:1px dashed #ccc; border-radius:8px;
              font-size:12px; color:#999; }}
  .err {{ background:#fff0f0; border:1px solid var(--fail); color:var(--fail);
          padding:8px; border-radius:8px; font-size:12px; margin:6px 0; }}
  table.info {{ border-collapse:collapse; font-size:12px; margin:6px 0; }}
  table.info td {{ border:1px solid var(--line); padding:3px 8px; }}
  table.info td:first-child {{ color:#555; }}
  .overlay {{ position:fixed; display:none; inset:0; background:rgba(0,0,0,.8);
              z-index:99; align-items:center; justify-content:center; }}
  .overlay img {{ max-width:94%; max-height:94%; }}
</style>
</head>
<body>
<header class="top">
  <h1>IONMIX eosop_pro 可视化测试报告</h1>
  <p>生成时间: {summary.get('generated_at','-')} · Python {summary.get('python','-')}</p>
  <p>任务集: {', '.join(summary.get('tasks', []))}</p>
</header>
<div class="wrap">
  <div class="stats">
    <div class="stat"><div class="num">{summary.get('n_materials',0)}</div><div class="lab">材料数</div></div>
    <div class="stat"><div class="num">{summary.get('n_images',0)}</div><div class="lab">生成图像</div></div>
    <div class="stat"><div class=" -num" style="color:var(--ok)">{ok}</div><div class="lab">步骤成功</div></div>
    <div class="stat"><div class="num" style="color:var(--fail)">{fail}</div><div class="lab">步骤失败</div></div>
    <div class="stat"><div class="num">{summary.get('total_elapsed_s',0)}s</div><div class="lab">总耗时</div></div>
  </div>
  {''.join(cards)}
</div>
<div class="overlay" id="ov" onclick="this.style.display='none'">
  <img id="ovimg" src="">
</div>
<script>
  document.querySelectorAll('figure img').forEach(function(im){{
    im.onclick = function(){{
      document.getElementById('ovimg').src = this.src;
      document.getElementById('ov').style.display = 'flex';
    }};
  }});
</script>
</body>
</html>"""
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=os.path.join(HERE, "test_summary.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "report.html"))
    args = ap.parse_args()

    if not os.path.exists(args.summary):
        print(f"[!] 摘要文件不存在: {args.summary}\n"
              f"    请先运行: python test_all.py")
        sys.exit(1)
    with open(args.summary, encoding="utf-8") as f:
        summary = json.load(f)
    html = build_html(summary)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[i] 报告已生成: {args.out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
