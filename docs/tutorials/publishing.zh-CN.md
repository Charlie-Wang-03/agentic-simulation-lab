# 发布检查清单

发布是由维护者控制的阶段，不是智能体的默认行为。

## 冻结并双重导出候选版本

绝不能把 private R&D mother repository 直接改为公开仓库。先冻结 private `main` 的精确 commit SHA，再从该 SHA 创建两个彼此独立、无历史的导出：

```text
python tools/export_public.py --revision <exact-private-main-sha> --output artifacts/public-exports/export-a
python tools/export_public.py --revision <exact-private-main-sha> --output artifacts/public-exports/export-b
python tools/check_public_tree.py --root artifacts/public-exports/export-a
python tools/check_source_provenance.py --root artifacts/public-exports/export-a
python tools/check_public_tree.py --root artifacts/public-exports/export-b
python tools/check_source_provenance.py --root artifacts/public-exports/export-b
```

两个报告的排序文件清单、逐文件 SHA-256 和 tree SHA-256 必须完全相同。每个导出都不得包含 `.git`、private history/remote、`artifacts`、本地配置或私人路径。

1. 审阅 `docs/release/OFFICIAL_SOURCE_AUDIT.md` 与当前 Ansys 条款。
2. 验证已批准的 Apache-2.0 `LICENSE`、SPDX/打包元数据，并确认它与 Ansys 产品许可证相互独立。
3. 运行完整静态、打包、隐私、链接、双语教程配对和发布审计。
4. 确认生成物、`.venv`、秘密、求解器数据库与私人身份信息均被忽略。
5. 审阅 `git status --short` 与 `git status --ignored`；逐项暂存，不要使用未经审阅的批量操作。
6. 只有在另一次明确公开授权后，才可把一个已审阅 clean export 复制到新的空目录；不得 clone private 仓库或复制 `.git`。
7. 仅在该新目录执行 `git init`、建立 `main`、生成一个干净的首次 commit、创建空的公开仓库 `Charlie-Wang-03/agentic-simulation-lab`，并只 push `main`。
8. 配置元数据与安全设置；在任何 tag 或发布前审阅 v0.1.0 release plan。

公开仓库具有独立历史，不能带入任何 private remote、branch、commit、tag、reflog、worktree metadata 或 R&D-only 文件。

唯一允许的公开维护者标识是 `Charlie-Wang-03`。只能使用维护者提供的脱敏 Git metadata；不得猜测或公开真实姓名、私人邮箱、主机名或许可证端点。
