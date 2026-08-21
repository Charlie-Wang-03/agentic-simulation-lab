# 旗舰学习路径

这条路径从完整目录中精选 8 个案例。每一级都先运行 `info` 和 `--dry-run`；只有声明的产品与有效许可证均可用时才执行。成本是相对教学估计，不是性能保证。列出的状态都是历史目录证据，不代表当前机器必然得到相同结果。

Level 0 是无求解器的环境与目录入门：

```bash
agentic-sim list
agentic-sim doctor
agentic-sim list --role dataset
```

## Level 1 — `mechanics/static-cantilever`

- 物理：线弹性梁弯曲与 Euler–Bernoulli 端部挠度。
- 自动化：建模、约束、求解、提取位移并与解析参考对比。
- 验证：历史端部位移相对误差；目录状态为 `PASS`。
- 要求：领域清单声明 Mechanical 与 MAPDL；真实运行需要兼容产品和许可证。
- 成本：低；推荐作为第一个求解器案例，规模通常适合 Student 版本。

```bash
agentic-sim run mechanics --case static-cantilever --dry-run
agentic-sim run mechanics --case static-cantilever
```

## Level 2A — `thermal/thermal-conduction`

- 物理：稳态一维导热与温度梯度。
- 自动化：热材料/边界设置与温度提取。
- 验证：与导热解析解比较；目录状态为 `PASS`。
- 要求：thermal 清单声明 Mechanical/MAPDL。
- 成本：低；紧凑的 Student 规模热学入门。

```bash
agentic-sim run thermal --case thermal-conduction --dry-run
agentic-sim run thermal --case thermal-conduction
```

## Level 2B — `thermal/thermal-transient`

- 物理：随时间变化的热响应与物理合理的温度历史。
- 自动化：瞬态步进、历史提取与时间序列检查。
- 验证：历史结果中的瞬态解析/趋势检查；目录状态为 `PASS`。
- 要求：thermal 清单声明 Mechanical/MAPDL。
- 成本：低到中等；比稳态导热包含更多时间步和输出。

```bash
agentic-sim run thermal --case thermal-transient --dry-run
agentic-sim run thermal --case thermal-transient
```

## Level 3 — `cfd/fluent-laminar-channel`

- 物理：充分发展层流通道与 Poiseuille 速度剖面。
- 自动化：生成网格、配置 Fluent 稳态求解并导出剖面。
- 验证：速度剖面、压降与质量流量检查；目录状态为 `PASS`。
- 要求：Fluent；小网格旨在保持 Student 规模可访问性。
- 成本：对 CFD 而言较低，但包含求解器启动。

```bash
agentic-sim run cfd --case fluent-laminar-channel --dry-run
agentic-sim run cfd --case fluent-laminar-channel
```

## Level 4 — `multiphysics/cht-fluent`

- 物理：流体区与固体区之间的共轭传热。
- 自动化：多区域设置、界面处理、场提取与守恒核算。
- 验证：全局能量闭合与温度边界；目录状态为 `PASS`。
- 要求：领域清单声明 Fluent、Mechanical 与 System Coupling；执行前检查具体案例和本地许可证。
- 成本：中等；比单物理案例具有更强的守恒要求。

```bash
agentic-sim run multiphysics --case cht-fluent --dry-run
agentic-sim run multiphysics --case cht-fluent
```

## Level 5A — `acoustics/acoustic-tube`

- 物理：闭口/开口声管驻波与四分之一波长共振。
- 自动化：MAPDL 谐响应设置、频率扫描、轴线场导出与峰值检测。
- 验证：共振频率与四分之一波长关系对比；目录状态为 `PASS`。
- 要求：acoustics 领域声明 Mechanical、MAPDL 与 Fluent；本案例的求解器标签为 MAPDL/Mechanical。
- 成本：中等；包含频率扫描和较丰富的场输出。

```bash
agentic-sim run acoustics --case acoustic-tube --dry-run
agentic-sim run acoustics --case acoustic-tube
```

## Level 5B — `dem/particle-freefall`

- 物理：恒定重力下的 Lagrangian 粒子运动。
- 自动化：Rocky 工程构建、瞬态粒子表导出与轨迹分析。
- 验证：位置、速度与恒重力运动学对比；目录状态为 `PASS`。
- 要求：Rocky 与适用许可证；案例超时为 300 秒。
- 成本：中等；物理模型很小，但包含商业求解器启动。

```bash
agentic-sim run dem --case particle-freefall --dry-run
agentic-sim run dem --case particle-freefall
```

## Scientific-AI 轨道 — `cfd/fluent-parametric-dataset`

- 物理：12 个 Reynolds 数下的稳态层流二维顶盖驱动方腔。
- 自动化：参数扫描、Fluent 场导出、Dataset Contract v1 写入、checksum/重载验证与包级 NumPy 加载。
- 验证：contract/payload 检查与历史物理证据明确分离；目录状态为 `PASS`。
- 要求：Fluent；本地加载样本还需要 `data` extra。
- 成本：相对较高：12 次求解，每个样本最多请求 900 次迭代。它是教学 smoke dataset，不是训练规模数据集。

```bash
agentic-sim run cfd --case fluent-parametric-dataset --dry-run
agentic-sim run cfd --case fluent-parametric-dataset
```

随后进入[数据集教程](tutorials/generate-a-dataset.zh-CN.md)，检查 `dataset.json`、加载一个样本并运行通用 validator。`doctor` 找到可执行文件并不代表应当启动求解器；执行仍需要明确意图和可用许可证。
