> Published report snapshot. Local evidence references below identify the retained workspace artifacts; they are not downloadable links in this snapshot.

# PLE-BF16 淘宝小蜜独立审查

审查时间：2026-10-13T01:24:16.748525+00:00。审查者：Codex independent agent `/root/ple_validation_audit`。

六份当前模型原始响应均通过冻结核心语义回归标准，未发现阻断项；最终验收仍由根代理完成。模型为 `sammysun0711/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16`，revision `6c0545042bbd870060214ca88aa59f1bfbc07d8e`。这里只覆盖同一个历史 n=1 案例的六种配置。

逐份完整阅读原始响应，核验保存的 HTTP body、请求、原自动结果、模型/源树/campaign 身份和模板证明。共 210 项离线完整性检查通过。六份都 HTTP 200、finish_reason=stop、15,772 prompt tokens；唯一 closing-only `</think>` 由当前模板隐式开标记证明支持，独立解析的 final JSON 与原文件一致。

| 配置 / attempt | 核心判断 | 当前输出及措辞观察 |
| --- | --- | --- |
| non-mtp baseline 0013 | 通过 | 抱歉给您带来困扰了。；您这边是想申请退货退款，还是申请退款呢？ “退货退款”与“退款”在日常用语中有重叠，且两个选项都围绕退款；相比开放式询问，可能把用户诉求收窄到退款。 |
| non-mtp prepare 0014 | 通过 | 抱歉给您添麻烦啦，您这边是想申请退货退款，还是换货/补发处理呢？ “换货/补发”把两个不同结果合并成一个选项，连同退货退款实际列出三种结果；对“标题未标注生制品”的问题，补发相关性较弱，换货也未证明能解决商品属性争议。斜杠话术不够口语化。 |
| non-mtp pr40 0015 | 通过 | 抱歉给您带来困扰了。；您这边是想申请退货退款，还是申请退款呢？ “退货退款”与“退款”在日常用语中有重叠，且两个选项都围绕退款；相比开放式询问，可能把用户诉求收窄到退款。 |
| mtp3 baseline 0019 | 通过 | 抱歉给您带来困扰了。；您这边是想申请退货退款，还是换货处理呢？ 询问换货意图未声称换货成功或可保证办理，但同类商品换货对未标注生制品问题的帮助有限，当前没有确定的换货适用性证据。 |
| mtp3 prepare 0020 | 通过 | 抱歉给您带来困扰了，您这边是想申请退货退款，还是退款呢？ “退货退款”与“退款”在日常用语中有重叠，且两个选项都围绕退款；相比开放式询问，可能把用户诉求收窄到退款。 |
| mtp3 pr40 0021 | 通过 | 抱歉给您带来困扰了。；您这边是想申请退货退款，还是退款呢？ “退货退款”与“退款”在日常用语中有重叠，且两个选项都围绕退款；相比开放式询问，可能把用户诉求收窄到退款。 |

所有输出都先询问当前处理意图，没有执行退款 SOP，也没有声称退款已发起或承诺代联系商家、赔偿或升级。非 MTP prepare 的“换货/补发”弱相关并合并多个结果，MTP baseline 的“换货”也缺少解决生制品属性问题的适用性证明，均记为非阻断措辞观察。其余四份的“退货退款/退款”语义有重叠、询问范围局限于退款，不能据此声称开放式诉求确认质量得到验证。

冻结场景一允许先确认诉求并枚举选择，服务流程同时写有“未明确表达退款诉求时不要引导退款”。本审查按冻结的三个核心标准作判断，保留这组文字竞争；不把核心通过表述为全部业务规则都已满足。六个配置都询问诉求，未直接劝用户发起申请或承诺申请可获支持。

新模型的请求、fixture、protocol、模板、tokenizer/config 哈希均匹配当前 v3 冻结清单。各运行 startup/after 原始 server-info 与 runtime 记录一致，保留 GPU 内 BF16 PLE、effective memory fraction 0.80、actual token capacity 262144；MTP 三组确认为 EAGLE steps=3、topk=1、draft_tokens=4，target/draft TP0/TP1 加载完成，独立 probe 的 draft execution 已核验。

原 automatic summary 的 manual pending 字段、raw response、冻结文件及 monitor state 均未修改，也未重跑 GPU。六份单独 JSON 包含原始 artifact 路径与 SHA256、逐项 identity 检查、当前 final JSON、语义证据及观察；`summary.json` 汇总本审查。
