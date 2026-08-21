# 教程二：运行 Mechanical 基准

先确认 Mechanical 可选依赖、本地安装与许可证，再查看和试运行案例：

```bash
agentic-sim doctor --probe mechanical
agentic-sim info mechanics static-cantilever
agentic-sim run mechanics --case static-cantilever --dry-run
```

产品与许可证可用时，去掉 `--dry-run`。真实运行记录写入 `artifacts/runs/mechanics/static-cantilever/`，日志写入 `artifacts/logs/`。案例会把提取位移与梁理论对比；进程返回零只是必要条件。

```bash
agentic-sim validate mechanics --case static-cantilever
```

应同时查看 `run.json` 和案例结果，只有物理检查通过时才能报告 PASS。
