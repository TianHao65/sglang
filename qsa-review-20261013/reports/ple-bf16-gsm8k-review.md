> Published report snapshot. Local evidence references below identify the retained workspace artifacts; they are not downloadable links in this snapshot.

# PLE-BF16 GSM8K 独立最终复核（2026-10-13）

六配置完整响应、冻结评分与输入身份均通过独立复核，可作为该模型此次实验的观察结果汇报。每配置1319题，共7914条响应，无HTTP/server请求错误；原始评分和汇总无需修订。此复核不更新monitor/state.json，不代表全任务已complete，仍需根代理最终审查。

| 配置 | run | 成功/总数 | primary / strict | 准确率 | stop / length | strict无答案 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| nonmtp-baseline | 0013 | 1319 / 1319 | 1279 / 1279 | 96.9674% | 1318 / 1 | 2 |
| nonmtp-prepare | 0014 | 1319 / 1319 | 1281 / 1281 | 97.1190% | 1319 / 0 | 1 |
| nonmtp-pr40 | 0015 | 1319 / 1319 | 1282 / 1282 | 97.1948% | 1318 / 1 | 3 |
| mtp3-baseline | 0019 | 1319 / 1319 | 1281 / 1281 | 97.1190% | 1319 / 0 | 1 |
| mtp3-prepare | 0020 | 1319 / 1319 | 1282 / 1282 | 97.1948% | 1318 / 1 | 2 |
| mtp3-pr40 | 0021 | 1319 / 1319 | 1278 / 1278 | 96.8916% | 1317 / 2 | 3 |

primary/strict正确性分歧为0。两种提取结果存在12条差异（5条截断、六组id1001、nonMTP PR40 id1176），全部双方均计错；不能把无正确性分歧理解为无格式问题。primary全部有数字，strict无独立数字答案行共12条。0016–0018是第二次性能启动，无GSM8K生成；准确率分母每配置均为一次1319题。旧模型结果未纳入本复核。

## 成对变化

下表的C→W/W→C分别表示前组正确后组错误、前组错误后组正确；primary与strict结果一致。完整15个跨六配置配对及每题ID见pairwise.json。

| 比较 | C→W | W→C | 净正确数 | 净百分点 | 原文不同题数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| nonmtp-baseline → nonmtp-prepare | 7 | 9 | +2 | +0.151630 | 749 |
| nonmtp-prepare → nonmtp-pr40 | 4 | 5 | +1 | +0.075815 | 751 |
| nonmtp-baseline → nonmtp-pr40 | 6 | 9 | +3 | +0.227445 | 733 |
| mtp3-baseline → mtp3-prepare | 8 | 9 | +1 | +0.075815 | 751 |
| mtp3-prepare → mtp3-pr40 | 9 | 5 | -4 | -0.303260 | 753 |
| mtp3-baseline → mtp3-pr40 | 7 | 4 | -3 | -0.227445 | 744 |
| nonmtp-baseline → mtp3-baseline | 8 | 10 | +2 | +0.151630 | 736 |
| nonmtp-prepare → mtp3-prepare | 7 | 8 | +1 | +0.075815 | 762 |
| nonmtp-pr40 → mtp3-pr40 | 7 | 3 | -4 | -0.303260 | 716 |

PR40 nonMTP→MTP3净少4题（-0.303260个百分点）：变错241/298/340/570/724/796/1183，变对675/754/1046。这10题都正常stop；两组id119都错误，新增id255截断前后也都错误，故这次净差的10个正确性flip并非长度截断直接造成。题意/运算变化在manual-review.json逐项记录；c8请求调度和浮点路径可影响生成，不能把一个pass的变化单独归因于提交。

## 五条长度截断

| 配置 | id | completion tokens | primary | strict | primary / strict正确 |
| --- | ---: | ---: | ---: | --- | --- |
| nonmtp-baseline | 119 | 4096 | 40000 | None | false / false |
| nonmtp-pr40 | 119 | 4096 | 1.3 | None | false / false |
| mtp3-prepare | 119 | 4096 | 40000 | None | false / false |
| mtp3-pr40 | 119 | 4096 | 1 | None | false / false |
| mtp3-pr40 | 255 | 4096 | 10 | None | false / false |

五条finish_reason均明确为length=4096，均无####答案行，末尾停在未完成推导中；原协议把截断响应留在分母和评分里。id119四条长文本反复讨论30%高/低及涨幅、字面答案与整数答案；id255 MTP PR40反复讨论Ten/twenty矛盾、选哪八栏及176/192。记录的是反复推导与截断现象，并未证明无限循环，也未解决该模型行为。未开启新的GPU重跑。

id119另两组正常stop：nonMTP prepare 1590 tokens、MTP baseline 3560 tokens，均为#### 99076.92且官方计错。id255另五组均正常stop：nonMTP baseline/prepare/PR40和MTP baseline为176（3428/2465/3403/3671 tokens，官方计错），MTP prepare为192（3799 tokens，官方计对）。

## 评分与人工语义局限

人工复核覆盖32个正确性flip的题目，加id119/1001/1176共35题，记录六组预测/finish及不同预测的代表原文。完整选中原文、官方参考和题干在manual-review-cases.json；人工观察在manual-review.json，均未改写原始评分。

- id1001六组算出2:00 pm，语义正确，但#### 2:00 pm被primary取末尾00为0，strict为空，六组按冻结协议计错。
- id1176六组答1，采用原始5英寸为20%基数；官方每天消耗剩余量得2。nonMTP PR40以Answer: 1正常stop，无####，strict为空；此格式差异无正确数影响。
- id119官方把'A比L高30%'改用'L比A低30%'，还假设两人同涨40%；字面计算99076.92与官方95200不同。id255题干Ten/twenty矛盾而官方除以10。
- id403题干减少by 5小时，官方按to 5小时；id649把70倍总量视为新增；id675的官方中间24→36推导不一致。id517/241/1035/796等还有乘法措辞、去重计数、端点、雇用生效时间口径差异。保留官方gold和本次观察，不能笼统将所有官方计错都称数学错误。
- scorer比较最后一个有符号数字（优先最后####后，否则全文本）和Decimal gold；strict只认独立####数字行。它未做时间、单位或百分比的语义归一化；截断中间数字可被primary当预测，数字匹配也不保证推理有效。

## 输入、协议和模型身份

CPU独立检查重新生成全部1319题渲染提示和token IDs，逐项与frozen requests匹配；每响应gold/prompt_sha256/prompt_tokens也匹配。官方数据固定revision 3101c7d5072418e28b9008a6636bde82a006892c，train7473/test1319哈希匹配；仅前五条train演示，未用test示范。

共同协议SHA256为34d17423728e75cde8bf2cd6be5b506e37f2eeefb3e67066a9b9a1bb9a1616b2，requests SHA256为f5cdee4808a8c00d5c9caff8dabeb9ce1bc3811b630e854ebea4848bcfd77ff6，client SHA256为88d768cbc3e25ae39a92871426863bef6a51c1711eac87ddde8891214907e60d。六组完全同一bundle、无--limit、client c8、temperature0/topk1/topp1、sampling/server seed2311、thinking disabled、无自定义stop、max_new_tokens4096、errors不重试且保留分母；cached_tokens全部0。

六组都绑定sammysun0711/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16，HF revision 6c0545042bbd870060214ca88aa59f1bfbc07d8e。本次核对model identity SHA、24项大小/mtime、非shard文件SHA、九个safetensors header；128 PLE与31 MTP张量为BF16。24个模型文件合计236552720653字节；全量SHA引用10月12日已完成的固定身份清单，本次没有重读全量shard payload。

六run的model_info、campaign provenance、source identity、启动/结束server-info独立匹配；来源tree为baseline 1b0fe42a9be47de079efcad62654ba5c29d2c397、prepare e638bac72a2a530d412a43502281ff672fc327ab、PR40 ad46ebf68cc0ea69be1ba006820320a41dd7e03c，共用v3 loader-cycle修复。GSM8K client的简式source_identity.head=null来自无.git的export；完整树身份仍由run source-identity及campaign绑定。

runtime TP2、GPU4/5、effective mem_fraction_static0.8、actual token pool262144、radix disabled、PLE不offload、dtype auto、无模型override/额外quantization override，startup/after均符合。CLI0.9411764705882354经AITER规则落到0.8。MTP3为EAGLE steps3/topk1/draft_tokens4、checkpoint内建一层MTP，三组均目标/draft在TP0/1完成加载并有draft_execution verified；64-token独立probe非GSM8K接受率。该精度运行不是受控MTP吞吐benchmark，也不声称c8所有阶段使用新增kernel。

## 可审查产物

- audit.py / audit.log：CPU复核脚本和实际执行输出。
- audit-result.json：7914条重算、summary、official comparison全部0差异；源输入在复核前后哈希一致。
- rescore.jsonl：7914条独立预测、正确性、finish、token数及生成文本hash。
- summaries.json / pairwise.json：独立汇总、全部15组成对翻转ID。
- identity-and-protocol.json / input-hashes.json：提示重建、runtime/model身份和逐输入hash。
- manual-review-cases.json / manual-review.json：35题原文/参考/六配置和人工观察。

本次一配置一次全量生成，只支持该固定模型、协议和此次运行的观察分数及双向flip；不支持统计等效、非劣性保证、因果归因或一般任务能力保证。
