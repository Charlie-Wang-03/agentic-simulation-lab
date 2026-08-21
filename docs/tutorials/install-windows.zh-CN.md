# Windows 安装

1. 从可信来源安装受支持的 64 位 Python，并启用 Python launcher。
2. 将仓库克隆或解压到普通、用户可写的项目目录，不要放入 Ansys 安装目录。
3. 在仓库根目录打开 PowerShell，运行 `py -3.12 tools/bootstrap.py --extras dev`。
4. 用 `.venv\Scripts\Activate.ps1` 激活，然后运行 `agentic-sim doctor`。
5. 任何消耗许可证的执行前，都先查看案例并使用 `--dry-run`。

若执行策略禁止激活脚本，可直接调用 `.venv\Scripts\python.exe`；不要放宽整机安全策略。Ansys 软件需要用官方安装程序单独安装，并遵守其独立许可证。
