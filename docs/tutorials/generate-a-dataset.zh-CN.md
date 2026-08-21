# 生成并重载数据集

本教程遵循旗舰 Scientific-AI 路径：

```text
发现 → 检查 → 试运行 → 生成 → 检查 contract → 重载样本 → 验证
```

示例是 12 样本教学 smoke dataset，不是训练规模 benchmark。它展示如何把经过验证的仿真输出转换成可移植结构化数据，不训练模型。

## 1. 发现并检查

```bash
agentic-sim list --role dataset
agentic-sim info cfd fluent-parametric-dataset
```

源物理问题是稳态、层流、二维顶盖驱动方腔。确定性扫描使用 100–1200 的 Reynolds 数、一个共享 40 × 40 四边形网格，以及节点场 `velocity_x`、`velocity_y` 和 `pressure`。

## 2. 始终先 dry-run

```bash
agentic-sim run cfd --case fluent-parametric-dataset --dry-run
agentic-sim run cfd --case fluent-parametric-dataset --dry-run --json
```

试运行返回 `NOT_RUN`，不会创建 artifacts。JSON 输出给出计划的 `output_directory`、超时、入口和权威 Case Result 路径。

## 3. 只在已授权的求解器环境生成

下面的命令会启动 Fluent 并执行 12 个样本。只有明确需要本次执行且兼容的 Fluent 产品/许可证可用时才运行：

```bash
agentic-sim run cfd --case fluent-parametric-dataset --json
```

返回的 `output_directory` 形式如下：

```text
artifacts/datasets/cfd/fluent-parametric-dataset/<UTC timestamp>
```

可移植数据集根目录是其中的 `fluent_dataset/` 子目录。本地 proprietary solver evidence（如果写出）位于可移植目录之外的 `solver-evidence/`。

## 4. 检查 Dataset Contract v1

以下用 `<dataset-path>` 表示生成的 `.../<timestamp>/fluent_dataset` 目录。

```bash
agentic-sim dataset info <dataset-path>
agentic-sim dataset info <dataset-path> --json
```

`<dataset-path>/dataset.json` 是权威 dataset descriptor。它记录 identity、representation、参数、fields/units、mesh 语义、sample 到文件的映射、SHA-256 checksum、requested/observed provenance、validation evidence 和 split 语义。`dataset_index.csv` 与 `dataset_validation.json` 只是 supporting artifacts。

## 5. 重载一个 NumPy 样本

如有需要，安装已有的 data extra：

```bash
python -m pip install -e ".[data]"
```

然后通过包级 API 加载：

```python
from agentic_simulation_lab.datasets import open_dataset

dataset = open_dataset("<dataset-path>")
print(dataset.metadata["source"])
print(dataset.metadata["parameters"])
print(dataset.metadata["fields"])

sample = dataset.load_sample(0)
print(sample["sample_id"], sample["parameters"])
print(sample["coordinates"].shape)
print(sample["connectivity"].shape)
print(sample["velocity_x"].shape)
print(sample["velocity_y"].shape)
print(sample["pressure"].shape)
```

reader 始终以 `allow_pickle=False` 调用 NumPy。

## 6. 验证结构与 payload

```bash
agentic-sim dataset validate <dataset-path>
agentic-sim dataset validate <dataset-path> --json
```

验证内容包括 contract、安全相对路径、引用文件、checksum、必需 arrays、数值有限性、dtype、shape、connectivity 边界、参数对齐与 shared geometry。`status` 只描述 dataset structure/payload；独立的 `physics_validation` 报告声明的源案例证据，绝不从文件有效性推断。

NPZ 格式可接入下游 surrogate 或 neural-operator pipeline，但本仓库在 ML training 之前停止。12 个样本且没有官方 train/validation/test split，不能支持训练质量声明。
