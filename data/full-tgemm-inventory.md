# PR107 full tgemm data inventory

The datasets below have different source revisions and workloads. They remain separate; raw artifact values and regressions are preserved.

## Regular six-model local prototype CI

Before: PR63 `8511084989b4`; after: the same source plus the local tgemm patch and accepted GEMM tables. One startup per arm. AITER `514c166`, pyhip `8027faa`, client `fc6ddbb`, Torch2.12/ROCm7.14. Qwen3.8 configured12000/350; Qwen3.5 8000/500. Random, con1, ten warmups,128 formal requests and200 GSM8K examples per case/arm. Five cases onPTL34;35B/TP1/DFlash onPTL52.

| Case | Output tok/s before → after (Δ) | TTFT ms | TPOT ms | ETE ms | GSM8K correct/200 (Δ pp) |
|---|---|---|---|---|---|
| Qwen3.8-Flash-TP2-Base | 63.110 → 65.396 (+3.62%) | 934.786 → 924.615 (-1.09%) | 13.210 → 12.684 (-3.98%) | 5545.063 → 5351.246 (-3.50%) | 196/200 → 197/200 (+0.50 pp) |
| Qwen3.8-Flash-TP2-MTP | 89.920 → 91.805 (+2.10%) | 1008.787 → 1002.395 (-0.63%) | 8.260 → 8.050 (-2.55%) | 3891.627 → 3811.752 (-2.05%) | 198/200 → 197/200 (-0.50 pp) |
| Qwen3.5-35B-TP4-Base | 221.117 → 200.478 (-9.33%) | 171.425 → 189.339 (+10.45%) | 4.186 → 4.617 (+10.28%) | 2260.441 → 2493.081 (+10.29%) | 194/200 → 193/200 (-0.50 pp) |
| Qwen3.5-35B-TP1-DFlash | 280.805 → 284.802 (+1.42%) | 340.043 → 321.651 (-5.41%) | 2.885 → 2.872 (-0.45%) | 1779.750 → 1754.866 (-1.40%) | 197/200 → 197/200 (+0.00 pp) |
| Qwen3.5-397B-TP8-Base | 143.223 → 150.996 (+5.43%) | 320.585 → 319.966 (-0.19%) | 6.352 → 5.993 (-5.65%) | 3490.246 → 3310.598 (-5.15%) | 198/200 → 198/200 (+0.00 pp) |
| Qwen3.5-397B-TP8-DFlash | 277.447 → 281.024 (+1.29%) | 337.593 → 338.728 (+0.34%) | 2.933 → 2.885 (-1.65%) | 1801.303 → 1778.348 (-1.27%) | 198/200 → 197/200 (-0.50 pp) |

| Case | QPS before → after (Δ) | Acceptance length before → after (Δ) | GSM8K reference / minimum |
|---|---|---|---|
| Qwen3.8-Flash-TP2-Base | 0.180314 → 0.186846 (+3.62%) | — | 98.00% / 95.06% |
| Qwen3.8-Flash-TP2-MTP | 0.256914 → 0.262300 (+2.10%) | 3.550 → 3.518 (-0.91%) | 98.50% / 95.54% |
| Qwen3.5-35B-TP4-Base | 0.442233 → 0.400956 (-9.33%) | — | 97.00% / 94.09% |
| Qwen3.5-35B-TP1-DFlash | 0.561609 → 0.569604 (+1.42%) | 5.932 → 6.017 (+1.42%) | 97.00% / 94.09% |
| Qwen3.5-397B-TP8-Base | 0.286446 → 0.301992 (+5.43%) | — | 99.00% / 96.03% |
| Qwen3.5-397B-TP8-DFlash | 0.554893 → 0.562048 (+1.29%) | 7.855 → 7.925 (+0.88%) | 98.50% / 95.54% |

**All6/6 cases pass both arms**:1536 formal performance requests and2400 GSM8K scored examples,0 terminal errors. The same200-question subset is reused for six cases;2400 is not2400 distinct problems. Accuracy differences are percentage points, minimum=reference×.97, not a ±3pp gate. Performance has no speedup gate. All128 raw35B/TP4 requests retain its+10.29% ETE regression; last21 are a sustained slow interval, cause unconfirmed. This is local prototype CI, not online/final-head f315 CI.

## Qwen3.8 custom11K/350 and tuning

Nov9 initial image4d63dea three-way comparison onPTL52: configured11K/350,sigma4,prefix.35,MTP EAGLE3steps/4draft,radix on. Two starts/implementation; actual inputs average11730.414 and outputs349.477. Baseline ETE2296.284ms,PR63 linear2147.713ms,tgemm/CK2223.287ms. Initial tgemm has +3.52% ETE and +4.53% TPOT versus PR63linear, although it improves versus imagebaseline. **Q38TP4 has zero formal measured startups**; only a discard attempt exists. Do not invent TP4 data.

Nov10 tuning-only comparison keeps the same image4d63dea tgemm source and AITER514c166, changing base→selected CSVs onPTL34/GPU2–3,TP2. Two starts/arm ABBA,16-request discard then128formal per startup,512formal0errors,arithmetic smoke.

| TP / concurrency | Output tok/s before → tuned | TTFT ms | TPOT ms | ETE ms |
|---|---|---|---|---|
| 2 / 1 |156.941 →168.326 (+7.25%) |476.562 →479.689 (+0.66%) |5.032 →4.598 (-8.62%) |2226.815 →2076.229 (-6.76%) |

This is a tune-only comparison, not the six-model source change. Generator means andprefix ratio are not fixed actual lengths/hit rates; QPS=con1/meanETE, collector throughput is separate. No full GSM8K was run for this custom workload.

## All operator tuning records

GPU2,PTL34,16 rotating tensor sets,five eager/three Graph samples. All16 GEMMs and29 actual caller cases/58 changed-input Graph replays passed. All records, including regressions, follow.

| Family / M,N,K | Eager µs before→final (Δ) | Graph µs before→final (Δ) | Selected override |
|---|---|---|---|
| ck_decode /1,8192,2560 |9.003 →9.396 (+4.37%) |10.365 →10.786 (+4.06%) |False /default |
| ck_decode /4,8192,2560 |9.631 →9.177 (-4.71%) |10.989 →10.518 (-4.28%) |False /default |
| ck_decode /16,8192,2560 |9.342 →9.911 (+6.09%) |11.052 →10.908 (-1.30%) |False /default |
| ck_decode /1,2560,3072 |6.107 →5.981 (-2.06%) |7.469 →7.450 (-0.26%) |False /default |
| ck_decode /4,2560,3072 |29.230 →6.155 (-78.94%) |29.255 →7.526 (-74.27%) |True /ck |
| ck_decode /16,2560,3072 |5.484 →5.425 (-1.08%) |6.615 →6.564 (-0.77%) |False /default |
| ck_decode /1,6656,2560 |8.129 →8.394 (+3.26%) |9.621 →9.781 (+1.66%) |False /default |
| ck_decode /4,6656,2560 |8.286 →8.602 (+3.81%) |9.986 →9.914 (-0.72%) |False /default |
| ck_decode /16,6656,2560 |8.465 →8.641 (+2.07%) |10.005 →9.532 (-4.73%) |False /default |
| tgemm /8192,8192,2560 |783.408 →693.392 (-11.49%) |784.318 →697.227 (-11.10%) |True /hipblaslt |
| tgemm /8192,2560,3072 |281.701 →281.616 (-0.03%) |283.162 →282.396 (-0.27%) |False /hipblaslt |
| tgemm /8192,6656,2560 |633.880 →563.051 (-11.17%) |634.934 →564.700 (-11.06%) |True /hipblaslt |
| tgemm /256,1728,1152 |12.036 →12.049 (+0.10%) |15.067 →15.077 (+0.06%) |False /hipblaslt |
| tgemm /256,2152,1152 |15.781 →15.738 (-0.27%) |16.251 →18.074 (+11.22%) |False /torch |
| tgemm /256,1152,2152 |17.754 →16.019 (-9.77%) |19.607 →17.687 (-9.79%) |True /hipblaslt |
| tgemm /256,1152,576 |7.965 →5.758 (-27.70%) |9.565 →6.723 (-29.71%) |True /asm |

Five selected overrides: CK M4/N2560/K3072; FP8 M8192/N8192/K2560 andM8192/N6656/K2560; BF16 ViT M256/N1152/K2152(dense) andM256/N1152/K576(packed). CSVs remain external AITER tuning artifacts. Nonselected BF16 M256/N2152/K1152 Graph+11.22% remains recorded, not hidden.

## Nov16 controlled35B follow-up

Four independent starts onPTL52/GPU0–3,con1,random8K/500,seed42,pool262144,Graph on/radix off. Each startup has two qualitysmokes,128 discarded then128formal;10warmup each repetition.512formal+512discard allcomplete0errors,8smokes. MeanETE2702.621→2605.640ms(-3.59%),TTFT196.138→189.617(-3.32%),TPOT5.023011→4.841730(-3.61%),output184.945→191.823(+3.72%). Startup ranges before2681.692–2723.550,after2590.476–2620.805ms are n2 descriptive ranges, not confidence intervals. Formal1361/1361 owner samples complete;3cleanup-only gaps.

After-only original-pool control25637215:128discard+128formal,2smokes,formal ETE2620.343ms,TTFT191.011,TPOT4.868401,out190.742;late21ETE2663.289ms,0requests>3s. Formal335/335 owner samples complete;1cleanup gap. Single startup, not a sourceA/B andnot blended into primary CI/ABBA. Originalhost34/auto pool~25.6M/different serverseeds differ; historical trigger remains unresolved.

## Validation scope and final-head boundary

- {"scope": "Nov10 image4d63dea tgemm+selected tables", "source": "/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/RESULTS.md", "operator_shapes": 16, "actual_caller_cases": 29, "changed_input_graph_replays": 58, "claims": "Numerical and Graph checks only; operator timings separate from model ETE."}
- {"scope": "Nov12 prototype on PR63/851108", "source": "/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_tgemm_full_ci_20261112/review/cpu_audit/RESULTS.md", "driver_tests_passed": 26, "evaluation_shell_scripts_syntax_passed": 10, "dflash_layout_cpu_tests_passed": 5, "caller_cases": 28, "changed_input_graph_replays": 56, "raw_case_independent_audit_checks": 322, "claims": "322 are independent artifact checks, not 322 unit tests; all6 cases use GSM200, not full1319."}
- {"scope": "Nov16 frozen prototype (not f315e8d)", "source": "/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_tgemm_regression_host34_20261116/review/dispatch/MICRO_RESULTS.json", "actual_caller_cases": 81, "changed_input_graph_replays": 162, "max_relative_l2": 0.0017078167293220758, "max_graph_relative_l2": 0.0017358391778543591, "claims": "One startup per micro arm, endpoint resource checks; no complete model Perfetto trace."}
- {"scope": "Final draft source f315e8da on9ac4ebe", "source": "/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_issue88_draft_20261116/review/final_head.json", "head": "f315e8da2e3e9bed6e948fd5a835aeae165b5921", "base": "9ac4ebe4a16d5b8a55473eec17cdeee8916a544f", "cpu_regression_tests_passed": 8, "native_actual_caller_cases": 16, "changed_input_graph_replays": 32, "max_relative_l2": 0.002739968942478299, "max_graph_relative_l2": 0.0023766374215483665, "claims": "Includes scalar-scale/FP16 packed tuples. Final-head six-model GPU CI and matched complete-model Perfetto pending; earlier prototype CI cannot be labeled final-head CI."}

Supplemental CT35BTP4:128perf+200GSM per arm,97%→98%,ETE2319.546→2231.603ms;different single-shard checkpoint,excluded from Quark14 standard CI.

Final sourcef315e8d onbase9ac4ebe has8CPU regressions and16nativecaller/32Graph replay pass,maxL20.002740. It adds tuple fallback fixes and baseintegration after the prototype measurements. Final-head six-modelGPU CI remains pending; changed-file checks pass butrepository-wide registryhook hasunchanged base taxonomyfailuretest/registered/kernels/test_pyhip_qsa.py.

No matched full-model tgemm Perfetto captures are present in these inventories. PR63/PR8 original screenshots are historicalport evidence andcannot be reused ascurrenttgemm screenshots. Root will supply current-version complete original traces forfixedfour-figure format.

Provenance/rawartifact SHA checks are indata_inventory.json.60 regularCI artifact hashes andallcase length equality/percentage calculations checked; rawfiles untouched.

## Complete initial image matrix (Nov9 supplement)

This is image4d63dea / transplanted PR63 / initial untuned tgemm, separate from later851108 CI and table-only tuning.14/24planned startups and1792/3072formal requests completed. Qwen3.8 uses11K/350,sigma4,prefix0.35,MTP/radix on;35B/397B use standard8000/500,Base,MTP/radix off.

| Case | implementation | startups / formal | TTFT ms | TPOT ms | ETE ms | Output tok/s |
|---|---|---|---|---|---|---|
| Qwen3.8 TP2 | Baseline | 2 / 256 | 510.672 | 5.147 | 2296.284 | 152.202 |
| Qwen3.8 TP2 | PR63 linear | 2 / 256 | 482.501 | 4.800 | 2147.713 | 162.769 |
| Qwen3.8 TP2 | tgemm / CK decode | 2 / 256 | 483.087 | 5.018 | 2223.287 | 157.193 |
| Qwen3.8 TP4 | Baseline | 0 / 0 | unmeasured | unmeasured | unmeasured | unmeasured |
| Qwen3.8 TP4 | PR63 linear | 0 / 0 | unmeasured | unmeasured | unmeasured | unmeasured |
| Qwen3.8 TP4 | tgemm / CK decode | 0 / 0 | unmeasured | unmeasured | unmeasured | unmeasured |
| Qwen3.5-35B TP4 | Baseline | 2 / 256 | 166.933 | 4.070 | 2197.886 | 227.414 |
| Qwen3.5-35B TP4 | PR63 linear | 2 / 256 | 167.673 | 4.198 | 2262.247 | 220.945 |
| Qwen3.5-35B TP4 | tgemm / CK decode | 2 / 256 | 170.229 | 4.105 | 2218.759 | 225.270 |
| Qwen3.5-397B TP8 | Baseline | 1 / 128 | 358.945 | 6.245 | 3475.193 | 143.841 |
| Qwen3.5-397B TP8 | PR63 linear | 1 / 128 | 324.112 | 6.473 | 3554.254 | 140.646 |
| Qwen3.5-397B TP8 | tgemm / CK decode | 0 / 0 | unmeasured | unmeasured | unmeasured | unmeasured |

Each completed implementation uses the same physical PTL52 GPUs per case. Q38TP4 has no valid formal run;397TP8 has one startup for imagebaseline and transplantedPR63, with zero tgemm starts. Raw planned/unmeasured entries are retained. The linked Nov9 archive preserves the raw unrounded summary and per-round protocols.
