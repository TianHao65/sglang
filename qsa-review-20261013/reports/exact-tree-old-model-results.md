> Published report snapshot. Local evidence references below identify the retained workspace artifacts; they are not downloadable links in this snapshot.

# Qwen3.8 QSA：最终验证结果

验证与人工复核完成于 2026-10-10T14:01:05.837341+00:00。本次使用 `watch-20261010T033900-fc54-20261010T102611Z`，所有受控测量均在 `gpufc54` GPU4/5 完成。

两个最终 commit 已于 2026-10-10T14:03:39.945061+00:00 在本地创建，**尚未 push**；hash、subject 和父子关系以 commits.json (`commits/commits.json`; local evidence path) 为准。

| 版本 | 最终本地 commit | Subject |
|---|---|---|
| prepare | `e64399a32dcee958096488ca4c63fea350e5d580` | perf(rocm): prepare packed QSA KV outside attention |
| pr40 | `91622b8d2dc06f28d7e8f293bf3eb6f2909c7c01` | perf(rocm): use PR40 split-K attention on packed QSA KV |

两项改动分别为独立整理 packed K/V，以及在其后使用 PR40 split-K attention + AITER reduce。验证源码树分别为 `dad26ee848eed80dea2d3aab546ad99a375c67be` 和 `4cb0b974290eef6d9ee0471647988e624502aeea`。最终 commit 记录见 commits/commits.json (`commits/commits.json`; local evidence path)。

## 非 MTP 性能

TP2、12000 输入 / 350 输出、并发 1/8/16，固定 262144-token KV 池、关闭 radix cache。每版两次独立服务启动，每档丢弃首轮，再测两轮。54 个轮次共 2016 个请求全部完成，36 个正式轮均超过 60 秒。下表为两个启动均值；完整范围见 六启动独立复核 (`reviews/system_six_starts/README.md`; local evidence path)。

| 版本 | 并发 | Output tok/s | TTFT ms | TPOT ms |
|---|---:|---:|---:|---:|
| baseline | 1 | 51.609 | 1230.738 | 15.899 |
| baseline | 8 | 160.988 | 7618.341 | 27.962 |
| baseline | 16 | 185.903 | 13720.225 | 40.766 |
| prepare | 1 | 56.025 | 1227.975 | 14.375 |
| prepare | 8 | 166.059 | 7612.084 | 26.461 |
| prepare | 16 | 186.752 | 13719.360 | 40.662 |
| pr40 | 1 | 61.672 | 1225.856 | 12.743 |
| pr40 | 8 | 171.248 | 7613.839 | 24.993 |
| pr40 | 16 | 187.819 | 13708.268 | 40.525 |

| 改动 | 并发 | tok/s 变化 | TTFT 变化 | TPOT 变化 |
|---|---:|---:|---:|---:|
| baseline → prepare | 1 | +8.56% | -0.22% | -9.58% |
| baseline → prepare | 8 | +3.15% | -0.08% | -5.37% |
| baseline → prepare | 16 | +0.46% | -0.01% | -0.25% |
| prepare → pr40 | 1 | +10.08% | -0.17% | -11.36% |
| prepare → pr40 | 8 | +3.13% | +0.02% | -5.55% |
| prepare → pr40 | 16 | +0.57% | -0.08% | -0.34% |

相对 baseline，最终 PR40 吞吐在并发 1/8/16 下分别提高约 **19.50% / 6.37% / 1.03%**。各版本两启动吞吐的观测范围差最大约 0.302%。两次启动的范围不构成置信区间；c16 包含 query rows >8 时的旧 fallback。

## GSM8K 与 MTP=3

每个配置使用完整 1319 题、同一份冻结 token 输入、5 个仅来自 train split 的示例、greedy、thinking 关闭、并发 8、4096-token 输出上限。合计 7914 个请求，全部无 HTTP/server 错误；截断保留在分母，不改写原评分。

MTP=3 按项目定义使用 `EAGLE`、steps=3、topk=1、draft_tokens=4，复用 checkpoint 内置的一层 MTP 权重。三个 MTP 启动都已核验实际参数、双 rank 权重加载和真实 draft 执行计数；单独的不计分 64-token 探针均记录 verify=16、proposed=48、accepted=48。

| 模式 | 版本 | Primary | Strict | 截断 | 请求错误 |
|---|---|---:|---:|---:|---:|
| non-MTP | baseline | 1282/1319 (97.1948%) | 1282/1319 (97.1948%) | 1 | 0 |
| non-MTP | prepare | 1280/1319 (97.0432%) | 1279/1319 (96.9674%) | 1 | 0 |
| non-MTP | pr40 | 1285/1319 (97.4223%) | 1285/1319 (97.4223%) | 0 | 0 |
| MTP3 | baseline | 1280/1319 (97.0432%) | 1280/1319 (97.0432%) | 1 | 0 |
| MTP3 | prepare | 1283/1319 (97.2707%) | 1283/1319 (97.2707%) | 1 | 0 |
| MTP3 | pr40 | 1287/1319 (97.5739%) | 1286/1319 (97.4981%) | 1 | 0 |

完整三版及各版本 MTP/非 MTP 比较已生成于 monitor/results (`monitor/results/`; local evidence path)。逐题复核见 最终精度复核 (`reviews/mtp3_pr40_0017/README.md`; local evidence path)。这些是单次全量评估的观测值，包含双向 correctness flips，未据此声明统计等价或代码因果关系。

## 淘宝小蜜与适用范围

六次响应均为 HTTP 200、正常 stop，通过冻结 JSON/场景一/话术回复规则和独立的意图确认、无擅自执行 SOP 核心语义复核。每个配置只有一个历史独立用例（n=1）。最终 PR40 的 MTP 回复为致歉后询问“您这边是想申请退货退款，还是申请退款呢？”。

- MTP baseline 的“换货/补发”选项与当前问题关联较弱，执行条件尚未建立，且实际涉及三种处理结果。复核认为它没有声称可用或已执行，但保留措辞观察，未称所有业务细节完全合规。
- GSM8K id 119 在三个 MTP 版本均达到 4096-token 上限并判错；non-MTP baseline/prepare 同样截断，non-MTP PR40 曾在 4085 tokens 正常结束。该行为未被视为已系统性解决。
- MTP PR40 的 id 806 输出 `#### 70%`，primary 判对、strict 因百分号不匹配判错；这与截断题是两个不同问题。其他单位表达限制和全部 flips 保存在原始复核记录中。
- 新路径支持 query rows 1–8。MTP/c8 target verify 可有 32 行并走 fallback；draft decode 的 8 行及淘宝 c1 verify 的 4 行可进入新路径。此处没有将 MTP 精度运行当作 MTP 吞吐基准。

## 单测与完整证据

基线 187 passed / 1 skipped；prepare 最终树 202 passed / 1 skipped；PR40 最终树 249 passed / 1 skipped。唯一跳过项依赖可选 TileLang。测试含 GPU profiler 的调用次数断言、FP32 参考、动态 HIP graph、空行/无效页/脏尾和输出不混叠检查；另有 30 个 case 与原 PR40 逐位一致。

- 单测报告 (`unit/report.md`; local evidence path)
- 完整技术审计 (`reviews/final_validation/overall-audit.md`; local evidence path)
- 最后人审完成记录 (`reviews/final_validation/completion.json`; local evidence path)
- 六启动性能复核 (`reviews/system_six_starts/README.md`; local evidence path)
- MTP 最终精度与语义复核 (`reviews/mtp3_pr40_0017/README.md`; local evidence path)
- 当前状态 (`monitor/state.json`; local evidence path)

旧节点的 0008 baseline 仅保留为历史。原始 parser 失败状态 (`runner/runs/watch-20261010T033900-0008-system-baseline/status.json`; local evidence path)、原始请求/响应/摘要，以及对同一响应的离线复评凭据 (`runner/runs/watch-20261010T033900-0008-system-baseline/reviewed-completion.json`; local evidence path)和派生摘要均原样保留；离线评分没有回写原始失败产物。本次最终比较只使用当前 fc54 campaign 的 0009–0017。源文件、原始响应、既有自动摘要和 manifest 均保持原字节。
