已完成 14/24 次启动、1792/3072 个正式请求。

Qwen3.8 使用11K/350、sigma4、prefix0.35、MTP/radix开启、AITER prefill。Base沿用标准8K/500、con1、MTP/radix关闭。每个配置在同一台PTL机器完成各实现两次独立启动。

| 模型 / TP | 机器 | 配置 | 实现 | 启动数 | TTFT ms | TPOT ms | ETE ms | Output tok/s |
|---|---|---|---|---:|---:|---:|---:|---:|
| Qwen3.8 TP2 | 52 | custom | Baseline | 2 | 510.672 | 5.147 | 2296.284 | 152.202 |
| Qwen3.8 TP2 | 52 | custom | PR63 linear | 2 | 482.501 | 4.800 | 2147.713 | 162.769 |
| Qwen3.8 TP2 | 52 | custom | tgemm / CK decode | 2 | 483.087 | 5.018 | 2223.287 | 157.193 |
| Qwen3.8 TP4 | 34 | custom | Baseline | 0 | 未测 | 未测 | 未测 | 未测 |
| Qwen3.8 TP4 | 34 | custom | PR63 linear | 0 | 未测 | 未测 | 未测 | 未测 |
| Qwen3.8 TP4 | 34 | custom | tgemm / CK decode | 0 | 未测 | 未测 | 未测 | 未测 |
| Qwen3.5-35B TP4 | 52 | Base | Baseline | 2 | 166.933 | 4.070 | 2197.886 | 227.414 |
| Qwen3.5-35B TP4 | 52 | Base | PR63 linear | 2 | 167.673 | 4.198 | 2262.247 | 220.945 |
| Qwen3.5-35B TP4 | 52 | Base | tgemm / CK decode | 2 | 170.229 | 4.105 | 2218.759 | 225.270 |
| Qwen3.5-397B TP8 | 52 | Base | Baseline | 1 | 358.945 | 6.245 | 3475.193 | 143.841 |
| Qwen3.5-397B TP8 | 52 | Base | PR63 linear | 1 | 324.112 | 6.473 | 3554.254 | 140.646 |
| Qwen3.5-397B TP8 | 52 | Base | tgemm / CK decode | 0 | 未测 | 未测 | 未测 | 未测 |

11K/350为客户生成器指定均值；文本解码后重新分词会改变实际输入长度，实际均值保留在逐轮表。

[Excel](performance.xlsx) · [汇总CSV](summary.csv) · [逐轮CSV](rounds.csv)。原始结果、运行配置、质量检查和资源释放证据见各结果目录。
