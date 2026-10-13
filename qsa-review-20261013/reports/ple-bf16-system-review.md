> Published report snapshot. Local evidence references below identify the retained workspace artifacts; they are not downloadable links in this snapshot.

# 新 PLE-BF16 系统性能与 MTP3 运行证据独立审核

审核通过：0013–0018 的六次 non-MTP 系统测试和 0019–0021 的三次 MTP3 启动均与 v3 冻结来源、固定配置、同一物理 GPU pair 及原始日志相符。此次仅进行本地 CPU 复核；未重跑 GPU、改写原始/冻结/state 或标记 campaign 完成。

审核 UTC：`2026-10-13T01:29:08.196002+00:00`。Campaign SHA256：`d41c9dc426a3d3543dfd234b0e0712d0c354105d971d57ead70d0fc6fe4bf337`。

模型：`sammysun0711/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16`，revision `6c0545042bbd870060214ca88aa59f1bfbc07d8e`；24 文件、236,552,720,653 bytes。原始完整 pinned SHA256 验证记录和当前 size/mtime 保持相符，本次重读了配置/元数据及首 shard 的 128 BF16 PLE、MTP shard 的 31 BF16 tensor headers；没有重哈希 236.55 GB payload。

九次启动均使用 `gpuf2a0` GPU4/5：`0xc35a36a6a1cfe34b` / `0x66603cc02f3f6cc1`，KFD IDs `41880` / `32388`。CLI `0.9411764705882354` 经 AITER ×0.85 后有效 fraction 为 `0.80`；每次启动/结束的 server info 与 TP0/TP1 日志均确认实际 `262144` token capacity，BF16 PLE 留在 GPU，radix disabled，无 dtype/旧 FP8 PLE override。

逐次调用保存的 `validate_system()` / `validate_mtp3()`，重查源文件 SHA256、model/campaign provenance、配置、启动/结束 runtime、请求原文/评分 hash、GPU before/after 与运行期 PID/ancestry/start ticks 守卫；九条重算 acceptance 与保存记录完全一致。详细结果见 audit.json (`audit.json`; local evidence path) 和 validation-api-rechecks.json (`validation-api-rechecks.json`; local evidence path)。

## non-MTP 性能

每次启动按 c1/c8/c16 做 1 轮丢弃 warmup + 2 轮测量，12000 input / 350 output，TP2、固定 262144 pool。表格为两次独立启动平均；括号为这两次启动各自均值的实际最小–最大值。TTFT/TPOT 单位为 ms。

| Variant | c | output tok/s（范围） | TTFT（范围） | TPOT（范围） |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1 | 51.501 (51.379–51.624) | 1237.384 (1233.189–1241.580) | 15.920 (15.886–15.955) |
| baseline | 8 | 160.143 (159.710–160.576) | 7661.191 (7635.269–7687.114) | 28.101 (28.040–28.162) |
| baseline | 16 | 185.175 (184.651–185.699) | 13776.224 (13731.905–13820.543) | 40.951 (40.846–41.057) |
| prepare | 1 | 56.080 (56.073–56.087) | 1233.136 (1232.005–1234.268) | 14.343 (14.337–14.348) |
| prepare | 8 | 165.153 (164.919–165.387) | 7651.657 (7642.684–7660.630) | 26.610 (26.568–26.653) |
| prepare | 16 | 186.070 (185.844–186.295) | 13759.084 (13744.266–13773.902) | 40.878 (40.824–40.932) |
| pr40 | 1 | 61.530 (61.449–61.610) | 1234.343 (1231.671–1237.016) | 12.756 (12.742–12.769) |
| pr40 | 8 | 170.392 (170.194–170.589) | 7662.072 (7646.158–7677.986) | 25.089 (25.080–25.097) |
| pr40 | 16 | 186.871 (186.697–187.045) | 13780.053 (13763.310–13796.796) | 40.726 (40.682–40.771) |

| 比较 | c1 tok/s | c8 tok/s | c16 tok/s |
| --- | ---: | ---: | ---: |
| baseline → prepare | +8.89% | +3.13% | +0.48% |
| prepare → pr40 | +9.72% | +3.17% | +0.43% |
| baseline → pr40 | +19.47% | +6.40% | +0.92% |

原始 54 轮 / 2016 请求全部完成，0 请求错误、0 cached tokens；36 测量轮 / 1344 请求均大于 60 s，时长范围 65.651–121.348 s。原始吞吐 `output_tokens/duration` 与 TTFT 向量均值也重新核对，完整轮次见 rounds.json (`rounds.json`; local evidence path)。两次启动范围不是置信区间；c16 包含既有 fallback，小幅差异不代表统计显著性。

## 启动、运行期守卫和退出释放

| Attempt | Variant / phase | ready 相对 attempt 开始 (s) | Active guard rows | 退出后 VRAM 范围 (MiB) |
| --- | --- | ---: | ---: | ---: |
| 0013 | baseline / system-accuracy | 202.691 | 920 | 283.836–283.836 |
| 0014 | prepare / system-accuracy | 201.229 | 885 | 283.836–283.836 |
| 0015 | pr40 / system-accuracy | 202.874 | 856 | 283.836–283.836 |
| 0016 | pr40 / system | 201.814 | 529 | 283.836–283.836 |
| 0017 | prepare / system | 204.506 | 544 | 283.836–283.836 |
| 0018 | baseline / system | 204.034 | 569 | 283.836–283.836 |
| 0019 | baseline / accuracy | 366.247 | 265 | 283.836–283.836 |
| 0020 | prepare / accuracy | 259.010 | 269 | 283.836–283.836 |
| 0021 | pr40 / accuracy | 259.959 | 256 | 283.836–283.836 |

九次 runner 状态均 complete、launcher returncode=0，无 failure/contention/active-owner-failure。每个 GPU 在前后各有三次身份一致样本；退出后所有样本 utilization=0、KFD positive VRAM owners 为空、总 VRAM 低于 1 GiB。运行期守卫从 after_health_ready 建立到 before_success，冻结精确 runner/server/scheduler host/container PID、start ticks 和 ancestry，所有样本 established/pass。标称 poll interval 为 2 s，但实际采样还含探测耗时：non-MTP 每次最大间隔为 15.751–18.952 s，MTP3 为 26.862–31.326 s；这些是离散采样证据。当前远端 PID 是否仍存活由 root 的独立只读生命周期审核覆盖。

所有九次均已成功加载完整 target，完成 BF16 KV 分配和 readiness；loader 修复后的 startup 问题已由运行证据闭合。load-end 的 target `mem usage=120.24 GB` 和 MTP draft `4.06 GB` 是日志观测值，不能据此计算修复前后精确 GPU 峰值差。

## MTP3 target/draft 与执行 probe

实际 runtime 为 EAGLE、steps=3、topk=1、draft_tokens=4、V2，checkpoint 内置 1 层 MTP；target/draft 指向同一新模型。三次的 TP0/TP1 均记录 target `Qwen4ExpForConditionalGeneration` 与 draft `Qwen4ExpForCausalLMMTP` 的 Load weight end，原文及载入耗时见 audit.json。

| Attempt / variant | Target elapsed TP0 / TP1 (s) | Draft elapsed TP0 / TP1 (s) | Probe output / verify / proposed / accepted |
| --- | ---: | ---: | --- |
| 0019 / baseline | 66.14 / 65.63 | 33.63 / 33.69 | 64 / 16 / 48 / 48 |
| 0020 / prepare | 67.00 / 65.82 | 17.70 / 17.14 | 64 / 16 / 48 / 48 |
| 0021 / pr40 | 69.83 / 64.48 | 16.91 / 17.31 | 64 / 16 / 48 / 48 |

三次独立 probe 均原始 response/parsed response/hash 一致，64 个 output IDs、completion_tokens=64、length stop，实际 draft execution verified，accept length=4、accept rate=1.0。这个简单计数 probe 证明 draft 执行，不是 GSM8K acceptance rate 或 MTP throughput benchmark。

## Kernel 可达性

| 证据 | 观测 | 适用范围 |
| --- | --- | --- |
| 新 v3 prepare 0011 GPU profiler 单测 | batch 1/4/8：prepare 1 + 原 packed attention 1 | 当前 source tree 的 GPU dispatch |
| 新 v3 PR40 0012 GPU profiler 单测 | batch 1/4/8：prepare 1 + PR40 main 1 + AITER reduce 1 | 当前 source tree 的 GPU dispatch |
| 2026-10-09 full-model TP0/TP1 trace 重新解析且 SHA 相符 | 每 rank prepare/main/reduce 各 96 次，8 步×12 层，顺序正确，无旧 packed main | 历史模型 c1 TP2、32768 pool 的完整模型可达性 |

历史 profile 不冒充此次 PLE-BF16 新模型 profile，也不作为当前 262144-pool 吞吐数字。新路径 dispatch gate query rows 1–8；non-MTP c16 包含 fallback，MTP3/c8 target verify 可达 32 rows/fallback，draft decode 可达 8 rows，Taobao/c1 verify 4 rows 可进新路径。

## 待处理及结论限制

- 系统性能与 MTP3 加载/执行审核已通过；Taobao/GSM8K 最终人工审核与 campaign 生命周期完成由 root 复核处理。
- 共同 loader 修复后的九次完整模型启动已成功；修复前后精确 GPU 峰值减少量未测量，不能从 steady/load-end 日志推算。
- 两次启动的实际范围不是置信区间；c16 小幅差异包含既有 fallback，不建立统计显著性。
- MTP3 精度启动与独立 64-token probe 不构成 MTP 吞吐基准或 GSM8K draft acceptance rate 测量。
- 释放样本和运行期守卫证明保存的 run ownership/release；当前远端进程存活状态由 root 的另一个只读生命周期审核覆盖。
