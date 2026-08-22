# 快速开始：浏览案例并检查环境

1. 用 `python -m pip install -e ".[dev]"` 以可编辑方式安装项目。
2. 运行 `agentic-sim list`；可用 `--domain cfd` 限定领域。
3. 用 `agentic-sim info cfd fluent-laminar-channel` 查看案例。
4. 运行 `agentic-sim doctor`；只有获得主动探测授权时才加 `--probe fluent`。
5. 消耗许可证前先执行 `agentic-sim run cfd --case fluent-laminar-channel --dry-run`。
6. 运行 `agentic-sim validate` 和 `agentic-sim audit` 检查项目契约。

清单状态是历史证据，`doctor` 描述当前环境；两者默认都不会启动求解器。
