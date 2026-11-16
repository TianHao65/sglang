**TP1 原始四采样审定**

四项均与完整原始trace的SHA、名称、Decimal纳秒时间、GPU6/rank0和correlation一致；原文件未改。

| 阶段 | before单次GPU时长 | after单次GPU时长 | 形状依据 |
|---|---:|---:|---|
| FP8 Prefill，M8000/N12288/K2048 |1169.323µs|853.602µs|CPU Input Dims直接记录，External id441/430与GPU correlation199/189|
| BF16 Decode，M1/N64/K2048 |9.199µs|4.959µs|首Graph correlation7014/6210中按GPU ts排序第5kernel；形状为graph/source推断|

in_proj_qkvz的N=2×(128×16)+2×(128×32)=12288；in_proj_ba的N=2×32=64，K=hidden2048。模型layer0为linear_attention。模块/layer命名由模型配置和执行顺序佐证，CPU scope本身是AITER算子名。

两侧各64个hipGraphLaunch；首graph各774个GPU kernel。第4个相同FP8 CK，第5个before BBS/after wv_splitk_small，第6个fused_qkvzba_split_reshape，随后causal_conv/recurrent GDN，支持首GDN layer0 ba归因。Decode个体CPU shape/External id不可用，保留inferred标签。

CPU首GraphLaunch后至GPU首graph执行前仍有416/584个非该graph工作，执行延迟约98.326/131.100ms。当前按correlation归组没有混入前序GPU工作；不能仅用ts晚于CPU launch判定Decode。

每张图选择一调用，Prefill此调用−27.00%，Decode此调用−46.09%；不能称平均模型ETE、整个Decode或所有层收益。64次GraphLaunch是trace计数，不直接等同64个有效输出Decode步骤。

[完整归因JSON](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/review/trace_selection_audit_tp1.json)保留全部原始选择元数据、相关CPU/launch事件、源SHA及推断边界。未GPU查询、未重构/平移/删选原trace。
