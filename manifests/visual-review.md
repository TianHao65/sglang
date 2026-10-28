# 原始 trace 四图核验

四张图均通过原生Perfetto网页截图生成，尺寸2400×1000，暗色主题。
已逐张查看：原生蓝色Area Selection边界、原生选择时长、Current Selection >
Slices、Name/Count/Wall Duration/Self Duration/平均Wall Duration列及周围真实算子可见。
没有画框、重建表格、改轨道或改原始事件。长Tensile名字在页面列末自然省略，完整名称
保留在原生DOM/check JSON；相关BBS/kernel tile前缀与耗时列可读。

| 阶段 | Before | After | 同阶段可见时间宽度 |
|---|---:|---:|---:|
| Prefill BA投影 | 32.120µs | 31.919µs | 100µs |
| Decode BA投影 | 8.959µs | 5.279µs | 40µs |

这些是同rank、同模块形状与ordered sample0的单次原始GPU slice样本，不能代替整模ETE
或统计性能结论。Layer0是PP1非MTP完整forward执行顺序推断，不是profiler直接命名。
Decode实际请求batch1、矩阵M1，server日志明确包含bs1 CUDA graph capture。

Before使用ddccab6e0d，After使用corrected176150ccc3。两张Prefill图仍为BF16hipBLASLt
BA投影；Decode图显示Cijk_BBS→_swizzled_gemv。两个模型样本都没有独立输出copy事件，
因此这些图没有证明caller-owned-output API在默认整模路径中移除了copy。

原始文件保持完整且字节不变：

- port-r1 TP0：1e3a6b58acdde8df08c4d61cbf1b8c9999f20a7e7a28176812b2b80e8b0f4b6a。
- direct-r1 TP0：31fba39480ab5e9a734e0ca33cf03cd9d3b882150e4788c4349e148f151ac0e8。

Perfetto原始导入诊断为 `slice_spill_overlapping_complete_event`：Before36、After37。
没有为消除诊断重写trace；所选GPU原始事件的name/ts/dur逐一匹配到导入slice。
原生Slices聚合同时包含外层step/scheduler scope，汇总Wall Duration会重复计入包围scope；
GPU耗时应使用选中的GPU kernel那一行，不把3/4行聚合总数解释为GPU调用数或GPU总时长。

输出在 `output/figures/`、`output/checks/`、`output/capture-manifest.json`。
公开完整trace的Perfetto直开URL、SHA/manifest与四图加载仍由主任务发布后核验。
