# 真实仿真结果与来源

[English](SIMULATION_RESULTS.md) | **简体中文**

项目把视觉内容明确分成两层：

- `assets/gallery/`、`assets/showcase/` 以及 hero、workflow 中的 SVG 是解释示意图、状态图或品牌图。
- `assets/simulations/<domain>/` 中的 PNG 是论文式结果图，由相邻的精简 `*.evidence.json` 求解器数据确定性绘制。

这些 PNG 不是 GUI 截图，也不会补造证据中不存在的数值。每个 evidence 文件都记录求解器、单位、验证摘要、来源哈希，以及导入这份精简证据时是否需要重新运行求解器。

## 11 个领域的代表结果

| 领域 | 代表 benchmark | 图中使用的求解器证据 | 论文式 PNG | 本次升级是否需要重跑求解器 |
|---|---|---|---|---|
| 力学 | [`mechanics/static-cantilever`](../benchmarks/mechanics/cases/smoke_static_cantilever.py) | 621 个三维求解节点、位移模与等效应力 | [结果图](assets/simulations/mechanics/static-cantilever.png) · [证据](assets/simulations/mechanics/static-cantilever.evidence.json) | 否；本分支此前已导入一次合格的新 Mechanical 运行结果 |
| 热分析 | [`thermal/thermal-conduction`](../benchmarks/thermal/cases/smoke_thermal_conduction.py) | SOLID70 节点温度；图中明确标注横向延拓 | [结果图](assets/simulations/thermal/thermal-conduction.png) · [证据](assets/simulations/thermal/thermal-conduction.evidence.json) | 否 |
| CFD | [`cfd/fluent-cylinder-unsteady`](../benchmarks/cfd/cases/smoke_fluent_cylinder_unsteady.py) | 120 s 时刻的 Fluent 节点速度模与压力 | [结果图](assets/simulations/cfd/fluent-cylinder-unsteady.png) · [证据](assets/simulations/cfd/fluent-cylinder-unsteady.evidence.json) | 否 |
| 多物理场 | [`multiphysics/cht-fluent`](../benchmarks/multiphysics/cases/smoke_cht_fluent.py) | 共形流体—固体区域的温度场与速度场 | [结果图](assets/simulations/multiphysics/cht-fluent.png) · [证据](assets/simulations/multiphysics/cht-fluent.evidence.json) | 否 |
| 材料 | [`materials/plasticity`](../benchmarks/materials/cases/smoke_plasticity.py) | SOLID185 双线性塑性加载—卸载响应 | [结果图](assets/simulations/materials/plasticity.png) · [证据](assets/simulations/materials/plasticity.evidence.json) | 否 |
| 电磁场 | [`electromagnetics/magnetostatic`](../benchmarks/electromagnetics/cases/smoke_magnetostatic.py) | Maxwell 2-D 径向 `Mag_B` 样本；只按已求解的轴对称性旋转重建 | [结果图](assets/simulations/electromagnetics/magnetostatic.png) · [证据](assets/simulations/electromagnetics/magnetostatic.evidence.json) | 否 |
| 声学 | [`acoustics/acoustic-cavity-modal`](../benchmarks/acoustics/cases/smoke_acoustic_cavity_modal.py) | FLUID30 压力特征向量的三个正交中面 | [结果图](assets/simulations/acoustics/acoustic-cavity-modal.png) · [证据](assets/simulations/acoustics/acoustic-cavity-modal.evidence.json) | 否 |
| 多孔介质 / 岩土 | [`porous_geomechanics/terzaghi-consolidation`](../benchmarks/porous_geomechanics/cases/smoke_terzaghi_consolidation.py) | CPT212 孔压与位移的瞬态快照 | [结果图](assets/simulations/porous_geomechanics/terzaghi-consolidation.png) · [证据](assets/simulations/porous_geomechanics/terzaghi-consolidation.evidence.json) | 否 |
| DEM | [`dem/angle-of-repose`](../benchmarks/dem/cases/smoke_angle_of_repose.py) | Rocky 最终三维颗粒位置、粒径与速度 | [结果图](assets/simulations/dem/angle-of-repose.png) · [证据](assets/simulations/dem/angle-of-repose.evidence.json) | 否 |
| SPH | [`sph/sph-dam-break`](../benchmarks/sph/cases/smoke_sph_dam_break.py) | 三个求解时刻的 Rocky 拉格朗日粒子位置与速度 | [结果图](assets/simulations/sph/sph-dam-break.png) · [证据](assets/simulations/sph/sph-dam-break.evidence.json) | 否 |
| 相变 / 反应流 | [`phase_reactive/fluent-melting`](../benchmarks/phase_reactive/cases/smoke_fluent_melting.py) | Fluent 焓—多孔介质法液相率快照 | [结果图](assets/simulations/phase_reactive/fluent-melting.png) · [证据](assets/simulations/phase_reactive/fluent-melting.evidence.json) | 否 |

现在 11 个领域都有一张可用于报告的 PNG。本次升级使用已有精简证据，没有启动任何商业求解器。证据旁原有的 SVG 仍可作为轻量矢量摘要，但公开文档中的正式结果图以 PNG 为准。

## 重建与检查

安装 `visuals` extra（或开发环境）后运行：

```bash
python tools/build_simulation_visuals.py
python tools/build_simulation_visuals.py --check
```

一致性检查会验证 SVG 内容，以及每张 PNG 的尺寸、渲染版本标记和来源 evidence SHA-256。维护者专用的本地导入流程见[开发指南](DEVELOPMENT.md)。
