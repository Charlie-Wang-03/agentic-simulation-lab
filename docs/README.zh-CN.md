# 文档导航

[English](README.md) | **简体中文**

Agentic Simulation Lab 把物理意图转成可复现、可审阅的 Agent 仿真流程，并用明确的物理检查判断结果。这里不是文件清单，而是一张阅读地图：先找到自己的目标，再进入相应教程或技术参考。

## 从哪里开始？

| 你的目标 | 建议入口 | 读完能做什么 |
|---|---|---|
| 用几分钟弄懂项目 | [Agent-first 工作方式](tutorials/agent-first-workflow.zh-CN.md) | 分清 Agent、求解器和物理验证各自负责什么 |
| 安装项目并查看案例 | [快速开始](tutorials/quickstart.zh-CN.md) | 安装核心包，浏览目录，检查环境并安全试运行 |
| 系统学习仿真自动化 | [旗舰学习路径](LEARNING_PATH.zh-CN.md) | 从悬臂梁逐步进入热学、CFD、多物理场、声学、DEM 与数据集 |
| 查看真实结果图与来源 | [真实仿真结果](SIMULATION_RESULTS.zh-CN.md) | 对照 11 个领域各一张由求解器数据生成的论文式结果图 |
| 浏览全部公开案例 | [仿真案例总览](BENCHMARKS.zh-CN.md) | 按物理、求解器、状态、验证依据、代码和图示查看 134 个案例 |
| 为 Scientific AI 生成数据 | [数据集教程](tutorials/generate-a-dataset.zh-CN.md) | 生成、读取并校验 Dataset Contract v1 数据 |
| 贡献案例或修改代码 | [开发指南](DEVELOPMENT.md) | 遵循 manifest、结果契约、静态检查与发布边界 |

## 入门与学习

- [快速开始](tutorials/quickstart.zh-CN.md)：最短的无求解器入门流程，涵盖 `list`、`info`、`doctor` 和 `--dry-run`。
- [项目安装](tutorials/install-project.zh-CN.md)、[Windows](tutorials/install-windows.zh-CN.md) 与 [macOS](tutorials/install-macos.zh-CN.md)：按平台拆分的环境配置。
- [运行一个 benchmark](tutorials/run-a-benchmark.zh-CN.md)：在明确授权并具备许可证后运行 Mechanical 案例、检查证据。
- [旗舰学习路径](LEARNING_PATH.zh-CN.md)：8 个精选案例及其物理、自动化重点、环境要求和成本。
- [Ansys Student](tutorials/install-ansys-student.zh-CN.md) 与 [AEDT Student](tutorials/install-aedt-student.zh-CN.md)：产品安装与版本边界。

## 仿真案例与可视化证据

- [完整案例总览](BENCHMARKS.zh-CN.md)：根据 manifest、源码 docstring 与精简证据自动生成。
- [真实仿真结果与来源](SIMULATION_RESULTS.zh-CN.md)：11 张报告式 PNG，以及对应 benchmark、证据表达和重跑状态。
- [项目指标](PROJECT_METRICS.md)：自动生成的领域、状态、案例类型和求解器标签统计。
- [求解器支持矩阵](SOLVER_MATRIX.md)：区分历史测试证据与当前机器诊断。
- [已知限制](known-limitations.md)：如实保留失败、外部阻塞与迁移限制。
- [各领域实现](../benchmarks/)与[详细报告](reports/)。

案例总览会把解释性的 SVG 领域状态图与真实的求解器结果 PNG 分开。没有真实结果图的案例不会添加装饰性结果占位；案例状态始终以 manifest 和引用的结果文件为准。

## 原理与技术参考

- [架构](ARCHITECTURE.md)：目录注册、延迟加载、子进程执行、产物路径与结果契约。
- [验证规范](VALIDATION.md)：`PASS`、`FAIL`、`BLOCKED`、`PARTIAL`、`NOT_RUN` 的准确含义。
- [数据集](DATASETS.md)：Case Result Contract v1、Dataset Contract v1、可移植性与 Python 读取方式。
- [执行安全](EXECUTION_SECURITY.md)：子进程、可执行文件可信来源、网络和环境边界。
- [测试环境](TESTED_ENVIRONMENTS.md)：历史环境证据与平台支持范围。

## 项目、合规与维护材料

- [开发指南](DEVELOPMENT.md)、[贡献说明](../CONTRIBUTING.md)与 [Agent 工作流](../agent/WORKFLOW.md)。
- [Ansys 使用与合规](ANSYS_USAGE_AND_COMPLIANCE.md)、[Student 产品限制](STUDENT_PRODUCT_LIMITS.md)与[免责声明](../DISCLAIMER.md)。
- [安全策略](../SECURITY.md)与[问题支持](../SUPPORT.md)。
- [`release/`](release/) 保存来源审计、需求追踪、发布决策和回归记录；新人无需把它们作为入门前置阅读。

## 双语文档原则

新人最常用的内容默认提供中英文版本，包括根 README、文档首页、快速开始与安装、旗舰学习路径、案例总览入口、数据集教程以及其他关键教程。每一对文档都应直接互链。

底层架构、自动生成指标、实现细节、安全与合规来源审计、领域报告、发布记录可以只保留英文。这样既保证主要入口可读，也避免维护大量容易失真的翻译。中文页面按中文工程写作习惯独立编辑，不逐句照搬英文句式。

```bash
python tools/build_catalog.py
python tools/build_project_metrics.py
python tools/build_gallery.py
```

验证时使用各命令的 `--check`。不要手工修改自动生成的案例表，也不要把进程正常退出当成物理 `PASS`。
