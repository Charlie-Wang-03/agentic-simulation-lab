[English](README.md) | **简体中文**

# Agentic Simulation Lab

![Agentic Simulation Lab：用物理验证判断结果，覆盖 11 个领域、134 个案例](docs/assets/hero.svg)

**把依赖 GUI 操作和一次性脚本的工程仿真，整理成由 Agent 编排、可复现、可验证、可追溯的工作流。**

[快速开始](#快速开始) · [仿真案例总览](docs/BENCHMARKS.zh-CN.md) · [文档导航](docs/README.zh-CN.md) · [学习路径](docs/LEARNING_PATH.zh-CN.md)

项目把下面这条链路真正落到代码和证据上：

> **人的物理意图 → Coding Agent → 可复现脚本 / CLI → Ansys 求解器 → 物理验证 → 结构化结果**

Agent 负责查找案例、检查条件和编排执行；数值计算仍由 Ansys 软件完成；最终状态由事先声明的物理检查决定。进程正常退出只是必要条件，不能直接推出 `PASS`。项目明确保留 `FAIL`、`BLOCKED`、`PARTIAL` 与 `NOT_RUN`。

## 真实的多领域仿真结果

这个仓库包含真实的多领域仿真结果。下面的 PNG 都由经过确认的求解器数值证据确定性后处理得到，不是 AI 生成的云图，也不是专有 GUI 截图。

| | |
|---|---|
| [![悬臂梁位移与应力场](docs/assets/simulations/mechanics/static-cantilever.png)](docs/assets/simulations/mechanics/static-cantilever.png) | [![Fluent 非定常圆柱绕流速度与压力尾迹](docs/assets/simulations/cfd/fluent-cylinder-unsteady.png)](docs/assets/simulations/cfd/fluent-cylinder-unsteady.png) |
| **力学：** 求解节点位移与等效应力 | **CFD：** 瞬态速度场与压力场 |
| [![共轭传热温度场与速度场](docs/assets/simulations/multiphysics/cht-fluent.png)](docs/assets/simulations/multiphysics/cht-fluent.png) | [![声学腔体模态的正交压力切片](docs/assets/simulations/acoustics/acoustic-cavity-modal.png)](docs/assets/simulations/acoustics/acoustic-cavity-modal.png) |
| **多物理场：** 流固区域共轭传热 | **声学：** 求解器特征模态压力切片 |
| [![同轴结构静磁通密度场](docs/assets/simulations/electromagnetics/magnetostatic.png)](docs/assets/simulations/electromagnetics/magnetostatic.png) | [![DEM 安息角颗粒最终构型](docs/assets/simulations/dem/angle-of-repose.png)](docs/assets/simulations/dem/angle-of-repose.png) |
| **电磁场：** 轴对称求解场重建 | **DEM：** 求解后的最终颗粒构型 |
| [![SPH 溃坝粒子演化](docs/assets/simulations/sph/sph-dam-break.png)](docs/assets/simulations/sph/sph-dam-break.png) | [![相变液相率演化](docs/assets/simulations/phase_reactive/fluent-melting.png)](docs/assets/simulations/phase_reactive/fluent-melting.png) |
| **SPH：** 拉格朗日自由液面快照 | **相变：** 液相率随时间演化 |

可在[仿真结果来源清单](docs/SIMULATION_RESULTS.zh-CN.md)查看 11 个领域的全部代表图，也可直接进入[完整案例总览](docs/BENCHMARKS.zh-CN.md)。解释性 SVG 继续作为独立的导航层，并明确标注为示意图或领域图。

## 先看案例，再看架构

![力学、CFD、多物理场、声学、DEM 与 SPH 的 6 个代表性案例](docs/assets/showcase-board.svg)

图中的数值来自仓库保存的历史证据，示意图只解释物理问题和验证方法，不冒充求解器云图，也不保证其他版本、许可证、网格或机器得到完全相同的结果。

| 物理问题 | 求解器 / 产品 | 验证依据 | 历史证据 |
|---|---|---|---|
| [静力悬臂梁](benchmarks/mechanics/cases/smoke_static_cantilever.py) | Mechanical / MAPDL | Euler–Bernoulli 梁端挠度 | **PASS** — 0.100143 mm 对比 0.100000 mm，误差 0.143% |
| [层流通道](benchmarks/cfd/cases/smoke_fluent_laminar_channel.py) | Fluent | Poiseuille 速度剖面、压降、质量守恒 | **PASS** — 剖面 L2 误差 0.210%，压降误差 0.150% |
| [共轭传热](benchmarks/multiphysics/cases/smoke_cht_fluent.py) | Fluent | 全局能量闭合与温度范围 | **PASS** — 能量不平衡 0.900% |
| [驻波声管](benchmarks/acoustics/cases/smoke_acoustic_tube.py) | MAPDL / Mechanical | 四分之一波长共振 | **PASS** — 86.0 Hz 对比 85.81 Hz，误差 0.221% |
| [粒子自由落体](benchmarks/dem/cases/smoke_particle_freefall.py) | Rocky | 恒重力运动学 | **PASS** — 最大位置误差 1.34 µm |
| [SPH 溃坝](benchmarks/sph/cases/smoke_sph_dam_break.py) | Rocky | 液面前缘、质量守恒、时间历史和投影检查 | **PASS** — 历史记录中的声明检查全部通过 |

[完整案例总览](docs/BENCHMARKS.zh-CN.md)收录 **11 个物理领域的 134 个案例**。其中不仅有通过案例，也会直接展示有证据的失败、受产品或 API 限制的阻塞，以及没有可归属运行证据的案例。

## 这个项目解决什么问题？

传统仿真流程常把关键状态留在 GUI 点击、本地工程文件和临时脚本里。这样的流程很难复现、复核，也不适合交给 Coding Agent 稳定执行，更难作为数据集生成管线重复使用。

本项目为每个案例提供稳定的 manifest、统一 CLI、领域内求解脚本、明确的验证逻辑、结构化结果契约和精简证据记录。它是一套用于学习和建设可信仿真自动化的实验室，不替代 Ansys 产品、许可证、专业工程审查或数值判断。

## 工作方式

![从人的意图开始，经过 Coding Agent、脚本和 CLI、Ansys 求解器、物理验证，最终形成结构化结果](docs/assets/workflow.svg)

1. `list` 和 `info` 只读取与求解器解耦的 manifest，不会因为浏览目录就导入商业求解器接口。
2. `doctor` 检查当前机器；默认不启动求解器。
3. `run ... --dry-run` 先解析完整命令、前置条件、路径、超时和预期结果。
4. 只有得到明确授权并确认产品与许可证可用后，才通过受支持的 API 或脚本接口运行本地求解器。
5. 案例提取数值证据，并执行预先声明的解析解、守恒、经典基准、量纲或物理趋势检查。
6. `run.json` 分开记录进程状态和物理状态；manifest 指定的结果文件才是案例结论的事实来源。

需要深入了解时，再阅读[架构](docs/ARCHITECTURE.md)、[验证规范](docs/VALIDATION.md)和 [Agent 工作流](agent/WORKFLOW.md)。

## 快速开始

浏览目录、CLI、dry-run、测试和静态审计都不要求安装 Ansys 软件。

```bash
python -m pip install -e ".[dev]"
agentic-sim list
agentic-sim doctor
agentic-sim info cfd fluent-laminar-channel
agentic-sim run cfd --case fluent-laminar-channel --dry-run
agentic-sim validate
```

如果希望得到可复现的项目本地环境，可以运行 `python tools/bootstrap.py --extras dev`。求解器依赖按需安装，例如 `.[mechanical]`、`.[fluent]`、`.[aedt]` 或 `.[rocky]`，不必一次装全。

去掉 `--dry-run` 是另一项决定：必须有明确执行授权、兼容的官方本地产品和可用许可证。建议先完成[快速开始](docs/tutorials/quickstart.zh-CN.md)，再阅读[运行一个 benchmark](docs/tutorials/run-a-benchmark.zh-CN.md)。

## 按你的目标探索

| 你是… | 建议入口 | 能找到什么 |
|---|---|---|
| 工程或理工科学生 | [旗舰学习路径](docs/LEARNING_PATH.zh-CN.md) | 从梁弯曲逐步进入热学、CFD、CHT、声学、粒子与数据集的 8 个案例 |
| Mechanical / Fluent / AEDT / Rocky 用户 | [案例总览](docs/BENCHMARKS.zh-CN.md)与[求解器矩阵](docs/SOLVER_MATRIX.md) | 可复现脚本、产品要求、验证方法和如实记录的历史状态 |
| Scientific AI 研究者 | [数据集说明](docs/DATASETS.md)与[数据集教程](docs/tutorials/generate-a-dataset.zh-CN.md) | 参数扫描、Dataset Contract v1、NPZ 安全读取、checksum 与独立的物理来源信息 |
| 贡献者或工具开发者 | [开发指南](docs/DEVELOPMENT.md)与[贡献说明](CONTRIBUTING.md) | manifest、结果契约、延迟加载、静态验证和公开发布边界 |

[文档首页](docs/README.zh-CN.md)把入门教程、原理、技术参考、合规材料、领域报告和维护者发布记录分开，并说明哪些内容需要长期维护中英文版本。

## 技术原则

- **Local First**：核心运行时没有遥测、自动上传或在线 AI API；仿真输入和结果留在本地。
- **API / Script First**：默认使用受支持的 CLI、Python API 与求解器脚本接口，不把脆弱的 GUI 自动化作为基础设施。
- **Agent / Model Agnostic**：只要遵守仓库约定，不同 Coding Agent 都能检查和编排同一套流程。
- **Physics First**：程序退出码不能证明结果正确，`PASS` 必须有声明的物理证据。
- **可复现、可审阅**：路径相对化，产物集中路由，子进程有超时边界，来源和结果契约清楚。
- **如实记录状态**：`FAIL`、`BLOCKED` 和 `NOT_RUN` 不是展示瑕疵，而是科学可信度的一部分。

最新数量见自动生成的[项目指标](docs/PROJECT_METRICS.md)。AEDT 静电回归、Turek–Hron FSI、反应流能量核算、Rocky 双向耦合和部分 SPH 模式等限制均保留在[已知限制](docs/known-limitations.md)中。

## 平台与求解器要求

需要 Python 3.10 或更高版本。无求解器的核心功能和静态流程支持 Windows、macOS 以及 CI 中配置的 Linux；本地 Ansys Student 桌面求解目前按兼容的 Windows 安装编写文档。产品、许可证、模型规模、接口版本和通信方式会随环境变化。

具体边界见[测试环境](docs/TESTED_ENVIRONMENTS.md)、[求解器支持矩阵](docs/SOLVER_MATRIX.md)、[Student 产品限制](docs/STUDENT_PRODUCT_LIMITS.md)和 [`docs/tutorials/`](docs/tutorials/) 下的平台教程。

## 参与贡献

欢迎在不破坏物理验收条件、证据状态、路径可移植性、求解器延迟加载和公开树隐私的前提下贡献代码与案例。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)；一般问题见 [SUPPORT.md](SUPPORT.md)，安全问题按 [SECURITY.md](SECURITY.md) 处理。

修改 manifest 或案例总览后，请重新生成并检查导航：

```bash
python tools/build_catalog.py
python tools/build_project_metrics.py
python tools/build_gallery.py
python tools/build_gallery.py --check
python tools/build_simulation_visuals.py --check
python tools/check_links.py
```

## 许可证、合规与免责声明

本项目是独立社区项目，与 Ansys, Inc. 不存在隶属、背书、认证或官方支持关系。Ansys 软件和适用许可证必须另行取得，并按相应条款使用。仓库不分发 Ansys 软件、专有求解器数据库、厂商文档、标志或商业外观。

仓库原创代码、文档和 fixtures 采用 [Apache License 2.0](LICENSE)。该许可证不许可 Ansys 软件、文档、示例、商标或专有格式。Student 许可证限教育用途，不适用于商业用途或竞争分析。工程结果必须由具备相应资质的专业人员独立复核。

请阅读 [Ansys 使用与合规](docs/ANSYS_USAGE_AND_COMPLIANCE.md)、完整[免责声明](DISCLAIMER.md)与[第三方声明](THIRD_PARTY_NOTICES.md)。

Ansys、Mechanical、Fluent、AEDT、Maxwell、HFSS、Rocky、System Coupling、SpaceClaim 与 PyAnsys 是 Ansys, Inc. 或其子公司在美国或其他国家/地区的商标或注册商标，相关权利归各自所有者所有。
