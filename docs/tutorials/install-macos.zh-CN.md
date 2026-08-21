# macOS 安装

macOS 可运行核心包的目录浏览、清单、报告、测试、审计、路径检查和试运行。本项目不声称 macOS 支持本地 Ansys Student 求解器。

```bash
python3 tools/bootstrap.py --extras dev
source .venv/bin/activate
agentic-sim list
agentic-sim doctor
agentic-sim run mechanics --case static-cantilever --dry-run
pytest
```

本地没有求解器时，`doctor` 应清楚报告缺失而不产生 traceback。部分 PyAnsys 客户端可连接另行许可的远程求解器，但远程许可与部署不在本教程范围内。不要把 Windows Student 二进制复制到 macOS，也不要绕过平台或许可证限制。
