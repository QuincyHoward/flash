# skills/ — flash-sim Agent 技能库

> 最后核对：2026-11-06 · commit 72f6428

本目录存放随项目分发的 Agent skills（WorkBuddy / Claude Code / Codex / OpenCode 等通用）。
入口索引在仓库根 `AGENTS.md`（Claude Code 经根级 `CLAUDE.md` 的 `@AGENTS.md` 导入）。

## 编写规范

1. **单一 frontmatter**（禁双重）：`name`（flash- 前缀小写连字符）+ `description`（含触发场景关键词）。
2. **SKILL.md 目标 ≤200 行**；长文/大参考放 `references/`，按需指引，不默认加载。
3. **不设 scripts/**：脚本实现留在仓库原位（`scripts/`、`flash/` 子包），SKILL.md 只写调用方式与护栏，避免双份拷贝漂移。
4. **防腐锚点**：frontmatter 后首行 `> 最后核对：YYYY-MM-DD · commit <8位hash>`；含上游吸收内容另加 `> 上游：FLASH-Expert @ <hash>`。
5. **敏感信息**：凭据/机器名/绝对路径一律占位符化（`<ACCOUNT>`、`<HPC_WORKDIR>`）。
6. **命名分工**：操作型 `flash-<动作>`；知识型 `flash-knowledge` / `flash-pitfalls`。

## SKILL.md 模板

```markdown
---
name: flash-<name>
description: <一句话说明何时使用本 skill，含触发场景关键词>
---

> 最后核对：YYYY-MM-DD · commit <8位hash>

## 适用场景
## 前置条件
## 操作步骤（命令/模块调用方式）
## 护栏与铁律（禁止事项、稳定性判据）
## 常见坑
## 关联资源（docs/、flash.* 模块、references/）
```

## WorkBuddy 同步

```bash
python scripts/sync_workbuddy_skills.py            # 全量镜像 skills/ → .workbuddy/skills/
python scripts/sync_workbuddy_skills.py --dry-run  # 只打印计划
python scripts/sync_workbuddy_skills.py --check    # 一致性校验（CI 可用）
```

`.workbuddy/` 已在 `.gitignore`（本地生成物不入 git）；修改 `skills/` 后运行一次 sync 即可让 WorkBuddy 项目级生效。

## 技能清单

| skill | 优先级 | 主题 |
|---|---|---|
| flash-sim-overview | P0 | 项目入口导航 |
| flash-scenario-setup | P1 | SNB/FL-SH 场景设置、dtmax、分享合规 |
| flash-scenario-family | P1 | 场景家族派生、cn4 核查、关辐射变体 |
| flash-run-deploy | P1 | 三模式运行与超算部署 |
| flash-output-analysis | P1 | HDF5 输出分析、绘图纪律 |
| flash-par-gen | P1 | .par 生成与排版规范 |
| flash-eos-op | P2 | IONMIX cn4/cnr 表处理 |
| flash-flychk-history | P2 | FLASH → FLYCHK history 输入 |
| flash-hpc-fetch | P2 | 超算结果并行下载 |
| flash-data-extract | P2 | 纯 h5py 提取 FLASH AMR |
| flash-backup-verify | P2 | 发布前备份验证 |
| flash-knowledge | P2 | FLASH 知识层导航（上游吸收） |
| flash-pitfalls | P2 | 报错→根因→修复库 |
