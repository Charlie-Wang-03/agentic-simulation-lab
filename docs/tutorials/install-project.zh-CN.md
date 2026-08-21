# 安装项目

前置条件：Python 3.10 或更高版本（CI 明确覆盖 3.10 与 3.12）；如需克隆则安装 Git；为本地虚拟环境预留空间。浏览目录、试运行、测试和审计不需要安装 Ansys。

在仓库根目录运行：

```bash
python tools/bootstrap.py --extras dev
```

PowerShell 使用 `.venv\Scripts\Activate.ps1`，POSIX shell 使用 `source .venv/bin/activate`。随后验证：

```bash
agentic-sim list
agentic-sim info mechanics static-cantilever
agentic-sim doctor
agentic-sim audit
```

只安装需要的求解器可选依赖，例如 `python tools/bootstrap.py --extras dev,fluent`。安装 Python 包不会安装或许可任何 Ansys 产品。
