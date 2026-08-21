# Ansys 2026 R1 热学 / 固体传热基础能力 Smoke Test 报告

总状态：**PASS**  （生成时间：2026-08-11T12:44:35.971384+00:00）

全部模型均由 Ansys MAPDL 2026 R1 / 261 实际求解；Python 仅负责编排、解析解/热阻计算、误差判定和结果归档。

## Case A–G 汇总

| Case | 分析类型 | 网格（节点/实体单元） | 关键 Ansys 结果 | 理论/物理校验 | 误差 | 状态 |
|---|---|---:|---:|---:|---:|---|
| A | Steady-State Thermal | 99/40 | Heat flow [W]: 6 | 6 | 2.533e-09% | PASS |
| B | Steady-State Thermal | 99/40 | Maximum temperature [C]: 50 | 50 | 1.592e-09% | PASS |
| C | Steady-State Thermal | 108/48 | Surface temperature [C]: 77.1428571 | 77.1428571 | 1.13687e-12 C | PASS |
| D | Transient Thermal | 27/8 | Final center temperature [C]: 25.0997334 | 25.016818 | 0.0829154 C | PASS |
| E | Steady-State Thermal with CONTA174/TARGE170 | 108/40 | Contact temperature jump [C]: 26.6666667 | 26.6666667 | 2.491e-12% | PASS |
| F | Steady-State Thermal (nonlinear radiation) | 45/16 | Equilibrium surface temperature [C]: 303.505202 | 303.511469 | 0.00626703 C | PASS |
| G | Sequential Steady Thermal -> Static Structural | 44/10 | Tip displacement [m]: 7.31933882e-05 | 7.2e-05 | 1.657% | PASS |

## 逐项模型与输出

- **A 一维稳态导热**：0.10 × 0.02 × 0.02 m，k=15 W/(m·K)，120/20 °C 定温端。输出温度空间分布、热流率和热流密度；与 Fourier 线性解比较。
- **B 内部热生成**：0.10 m 对称平板，k=12 W/(m·K)，q'''=2.4×10⁵ W/m³，两端 25 °C。验证中心峰值和抛物线温度场，并做总生热/边界反力能量平衡。
- **C 对流边界**：L=0.08 m，k=8 W/(m·K)，左端 100 °C，右端 h=40 W/(m²·K)、T∞=20 °C。验证导热热阻 + 对流热阻。
- **D 瞬态冷却**：10 mm 立方体，k=200 W/(m·K)，ρ=7800 kg/m³，cp=500 J/(kg·K)，h=15 W/(m²·K)，100→20 °C。Bi=1.25×10⁻⁴，采用 5 s 步长，与 lumped-capacitance 指数响应比较。
- **E 接触热阻**：两个 50 mm 实体，CONTA174/TARGE170 纯热接触，TCC=200 W/(m²·K)。同时求解连续单体理想接触参考 case。
- **F 热辐射**：输入 8000 W/m²，ε=0.8，h=12 W/(m²·K)，T∞=25 °C；求解绝对温标下的非线性 Radiation + Convection 平衡。
- **G 热-结构顺序耦合**：热场结果文件通过 LDREAD 映射到由 ETCHG 转换的匹配结构网格；α=12×10⁻⁶/K，ΔT=60 K，L=0.1 m，验证自由热膨胀。

每个 case 的结构化 JSON、原始/整理 CSV、SVG 曲线和 MAPDL 输入/结果文件均位于 `outputs/`；Python 执行日志及完整 MAPDL solver listing 位于 `logs/`。汇总索引为 `outputs/thermal_suite_summary.csv`。

## 热学能力覆盖表

| 能力 | 覆盖 case | 覆盖状态 |
|---|---|---|
| 稳态固体导热、温度/热流/Heat Flux | A | 已覆盖 |
| 体积热生成与能量守恒 | B | 已覆盖 |
| Mechanical/MAPDL 对流边界与热阻网络 | C | 已覆盖 |
| 瞬态热容、中心/表面时间历程 | D | 已覆盖 |
| 有限热接触导热系数、界面温跳 | E | 已覆盖 |
| 非线性表面对环境辐射 + 对流 | F | 已覆盖 |
| Thermal → Structural 顺序数据传递 | G | 已覆盖 |

## 后续适合扩展的高级能力

相变/潜热与温度相关材料、各向异性与复合材料导热、真实 surface-to-surface enclosure 辐射及视角因子、移动/脉冲热源、热接触 conductance 随压力/温度变化、热循环疲劳、非匹配网格数据传递、Joule heating/电-热耦合、CFD-CHT 共轭换热，以及参数化/优化与网格收敛性研究。
