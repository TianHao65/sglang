> Published report snapshot. Local evidence references below identify the retained workspace artifacts; they are not downloadable links in this snapshot.

# Qwen3.8 PLE-BF16 重测结果

最终复核完成：2026-10-13T01:31:26.292744+00:00。本轮模型切换、三个版本 GPU 单测、六次非 MTP 系统启动、三次 MTP=3 精度启动及六份淘宝语义审查已完成。测试工作完成，仍保留以下精度、截断和话术限制。

最终 PR40 相对 baseline 的非 MTP output throughput，在并发 1/8/16 分别变化 **+19.47% / +6.40% / +0.92%**。完整 GSM8K 共 7,914 条响应、零请求错误；MTP3 PR40 得分 1278/1319，比 MTP3 baseline 少三题。本结果不构成精度等效或无回归保证。

## 模型、来源与协议

- 模型：`sammysun0711/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16`。
- HF revision：`6c0545042bbd870060214ca88aa59f1bfbc07d8e`。24 个文件、236,552,720,653 bytes 的既有完整 SHA256 身份记录与当前文件 size/mtime 一致；元数据及 BF16 tensor headers 在最终复核中重新读取。
- 当前配置版本：`v3-loader-cycle`；campaign：`watch-20261012T070337-89e48c`。
- Campaign SHA256：`d41c9dc426a3d3543dfd234b0e0712d0c354105d971d57ead70d0fc6fe4bf337`。
- 统一的 loader 修复只消除 PLE 加载闭包的自引用，保留权重映射、数值、dtype/device、copy 和 AITER shuffle 算法。下表明确区分原始提交与实际测试的补丁源码树。

| 版本 | 原始提交 | 实际测试源码树 | GPU 单测通过 / 可选跳过 |
| --- | --- | --- | ---: |
| baseline | `d619d57b18e0bc70bfb65ed22702dba3c73ef071` | `1b0fe42a9be47de079efcad62654ba5c29d2c397` | 187 / 1 |
| prepare | `e64399a32dcee958096488ca4c63fea350e5d580` | `e638bac72a2a530d412a43502281ff672fc327ab` | 202 / 1 |
| pr40 | `91622b8d2dc06f28d7e8f293bf3eb6f2909c7c01` | `ad46ebf68cc0ea69be1ba006820320a41dd7e03c` | 249 / 1 |

三个单测组均绑定当前补丁树；根审查逐一复验 25,548 个源码文件哈希，重新解析 JUnit、imports/source/GPU 守卫证据。可选跳过为 TileLang。此前 171 个 CPU harness 检查及 39 个 resource-admission 检查的记录保留。

六次非 MTP 与三次 MTP3 整模都使用 `gpuf2a0` 的 GPU4/5，同一物理 ID `0xc35a36a6a1cfe34b` / `0x66603cc02f3f6cc1`。TP2、BF16 PLE 留在 GPU，无模型 dtype 或旧 FP8 PLE override。CLI fraction `0.9411764705882354` 经 AITER ×0.85 后为有效 `0.80`；各 TP scheduler 实际 token capacity 均为 `262144`。

v3 的九次完整启动均成功，包含 AITER FP8 shuffle、KV 分配与请求执行。v2 的 OOM 与 v1 的显存参数偏差已保留在原记录和配置归档，未混入当前均值。当前成功启动证明本配置可运行，没有测得精确的加载峰值节省量。

## 非 MTP 系统性能

固定协议：12000 input / 350 output，radix cache disabled，并发 1/8/16。每个版本两次独立启动，每个并发先丢弃一轮，再测两轮；每轮请求数为 max(16, 4×c)。全 54 轮 / 2016 请求完成，36 轮测量 / 1344 请求，零错误与 cached tokens。
测量轮时长为 65.65–121.35 秒，全部超过 60 秒。表格是两次启动各自均值的平均，括号为这两次启动均值的最小–最大值。TTFT/TPOT 单位为 ms。

| 版本 | 并发 | output tok/s（范围） | TTFT（范围） | TPOT（范围） |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1 | 51.50 (51.38–51.62) | 1237.38 (1233.19–1241.58) | 15.920 (15.886–15.955) |
| baseline | 8 | 160.14 (159.71–160.58) | 7661.19 (7635.27–7687.11) | 28.101 (28.040–28.162) |
| baseline | 16 | 185.18 (184.65–185.70) | 13776.22 (13731.91–13820.54) | 40.951 (40.846–41.057) |
| prepare | 1 | 56.08 (56.07–56.09) | 1233.14 (1232.00–1234.27) | 14.343 (14.337–14.348) |
| prepare | 8 | 165.15 (164.92–165.39) | 7651.66 (7642.68–7660.63) | 26.610 (26.568–26.653) |
| prepare | 16 | 186.07 (185.84–186.30) | 13759.08 (13744.27–13773.90) | 40.878 (40.824–40.932) |
| pr40 | 1 | 61.53 (61.45–61.61) | 1234.34 (1231.67–1237.02) | 12.756 (12.742–12.769) |
| pr40 | 8 | 170.39 (170.19–170.59) | 7662.07 (7646.16–7677.99) | 25.089 (25.080–25.097) |
| pr40 | 16 | 186.87 (186.70–187.04) | 13780.05 (13763.31–13796.80) | 40.726 (40.682–40.771) |

| 比较 | 并发 | tok/s 变化 | TTFT 变化 | TPOT 变化 |
| --- | ---: | ---: | ---: | ---: |
| baseline → prepare | 1 | +8.89% | -0.34% | -9.91% |
| baseline → prepare | 8 | +3.13% | -0.12% | -5.31% |
| baseline → prepare | 16 | +0.48% | -0.12% | -0.18% |
| prepare → pr40 | 1 | +9.72% | +0.10% | -11.06% |
| prepare → pr40 | 8 | +3.17% | +0.14% | -5.72% |
| prepare → pr40 | 16 | +0.43% | +0.15% | -0.37% |
| baseline → pr40 | 1 | +19.47% | -0.25% | -19.88% |
| baseline → pr40 | 8 | +6.40% | +0.01% | -10.72% |
| baseline → pr40 | 16 | +0.92% | +0.03% | -0.55% |

两次启动的范围不是置信区间。c16 包含 query rows>8 时的原 fallback；约 0.92% 的差异仅作为本次观察，不作统计显著性判断。

## 内核可达性

| 证据 | 实际验证 | 范围 |
| --- | --- | --- |
| v3 prepare GPU profiler 单测（0011，rows=1/4/8） | 每次 1 次 `_prepare_qsa_packed_kv` + 1 次 `_sparse_gqa_chunk_prefill` | 当前源码树的 GPU 调用验证 |
| v3 PR40 GPU profiler 单测（0012，rows=1/4/8） | 每次 `_prepare_qsa_packed_kv` / `_qsa_sparse_packed_gqa_kernel` / `_mla_decode_fwd_reduce_kernel` 各 1 次 | 当前源码树的 GPU 调用验证；FP32、动态图及 metadata 测试也通过 |
| 保留的 full-model profile | 两个 TP rank 的 prepare/main/reduce 各 96 次 | 旧模型、c1、32768-token pool 的历史可达性证据，不充当本轮新模型 profile 或吞吐测量 |

Packed 分派上限仍为 8 query rows。MTP3 c8 的 target verify 可达到 32 rows 使用 fallback，draft decode 可为 8 rows；不能声称全部 MTP/c8 阶段走新内核。

## 完整 GSM8K

六个配置各 1319 个 frozen token inputs，train-only demonstrations 0–4，client c8、greedy、seed 2311、thinking off、4096 output-token limit、无重试。独立 CPU 复核重新生成全部 prompt/token IDs，对所有 7914 条 raw responses 重算主/严格评分、finish 与成对 flips；与原响应记录、summary、官方 comparison 均无差异。

| 版本 | 非 MTP 主/严格正确数 | 非 MTP 分数 | MTP3 主/严格正确数 | MTP3 分数 | 非 MTP / MTP3 截断 |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 1279/1319 | 96.9674% | 1281/1319 | 97.1190% | 1 / 0 |
| prepare | 1281/1319 | 97.1190% | 1282/1319 | 97.1948% | 0 / 1 |
| pr40 | 1282/1319 | 97.1948% | 1278/1319 | 96.8916% | 1 / 2 |

六组主评分与严格评分的正确数相同，HTTP/server 请求错误都为零。跨版本有双向正确性 flips，单轮数据集测试不提供等效、非劣效或源码因果保证。

**MTP3 PR40 的观察分数下降必须保留：** 相对 MTP3 baseline 少 3 题，相对 MTP3 prepare 少 4 题。PR40 自身 non-MTP→MTP3 有 7 个 correct→incorrect（241、298、340、570、724、796、1183）和 3 个反向改善（675、754、1046），净 -4 题 / -0.30326 个百分点；这 10 条都正常 stop，分差并非由截断个例变化造成。

**五次长度截断尚未解决：** id 119 在 non-MTP baseline/PR40 和 MTP3 prepare/PR40 达到 4096 tokens，id 255 在 MTP3 PR40 达到 4096 tokens。五条主/严格均错；不得丢出分母或以增大上限重跑替代本轮 frozen protocol。

保留评分与参考局限：id 1001 的六组回答都正确给出 `2:00 pm`，冻结 numeric scorer 却提取为 0 / strict invalid，仍原样记错；id 119 的 “30% higher” 与参考的 “30% less” 基数不一致，且同时涨薪未明确同百分比；id 255 的 ten/twenty stalls 与参考分母不一致；id 1176 的每日 20% 基数有解释差异。人工审查这些问题不改写原始得分。详见 GSM8K 独立审查 (`reviews/final_validation_20261013/gsm8k/README.md`; local evidence path)。

## 淘宝小蜜与 MTP3 运行

六份当前模型回复均通过 HTTP/JSON/场景/动作自动检查和独立核心语义审查：先确认当前诉求，没有执行或声称发起退款 SOP，没有承诺联系商家、赔偿或升级。这里只验证同一个历史 n=1 案例的六种配置，不是六题数据集准确率。210 项身份/原响应/模板/请求完整性检查通过。

话术观察仍保留：non-MTP prepare 的“换货/补发”把两个结果并列，补发与生制品未标注问题关联较弱；MTP baseline 的换货适用性没有证明；其余四份“退货退款还是退款”存在术语重叠，询问范围局限于退款。冻结 prompt 既允许场景一枚举诉求，又要求未明确退款时不引导退款，因此核心回归通过不等于全部业务措辞要求完全满足。

MTP=3 为 EAGLE steps=3、topk=1、draft_tokens=4，同 checkpoint 的单个内置 MTP layer，实际 V2 runtime。三次启动均确认 TP0/TP1 target 与 draft 加载。独立 64-token probe 的 verify/proposed/accepted 各为 16/48/48，只证明 draft execution；不作为 GSM8K acceptance rate 或 MTP 吞吐测试。

## 最终验收与生命周期

自动测试结束于 2026-10-12 20:33 UTC；最终审查于 2026-10-13 完成。原 READY、automatic summaries、raw response、hash-bound manifests 及历史 pending 标志保留；最终状态由以下记录补充。

- 最终验收 (`reviews/final_validation_20261013/completion.json`; local evidence path)。
- 系统/性能审核 (`reviews/final_validation_20261013/system/README.md`; local evidence path)。
- GSM8K 审核 (`reviews/final_validation_20261013/gsm8k/README.md`; local evidence path)。
- 淘宝独立审核 (`reviews/final_validation_20261013/taobao/README.md`; local evidence path)。
- 根审查与进程释放证明 (`reviews/final_validation_20261013/root-audit.json`; local evidence path)。
- 生命周期完成记录 (`monitor/results/COMPLETE.json`; local evidence path)。

控制器已自然退出，原锁未占用；在 f2a0 host PID namespace 重新核验九次运行的 runner/server/descendant 精确 PID+start ticks，共 648 条身份，均无匹配的存活任务进程。各次运行原 GPU 后置释放证据也通过。运行期间守卫记录通过；虽然配置 poll interval 为 2 秒，原始记录的实际最大采样间隔在 non-MTP 为 15.75–18.95 秒、MTP3 为 26.86–31.33 秒，不能把它描述成全程每 2 秒连续采样。

本轮新模型验证没有创建源码提交或推送。之前两个 local commits 保留，当前验证源码树因共同 loader 修复与它们区分。
