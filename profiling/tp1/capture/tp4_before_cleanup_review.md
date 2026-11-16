**TP4 before profile cleanup ownership review**

The single raw `active_peer_event` is the same PID generation previously identified as experiment-owned. PID **1896069**, start_ticks **391975092**, and PPID **1889760** remain unchanged when `in_own_container` changes to false during teardown. This event does not establish a newly arrived peer.

The [original capture manifest](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/capture_manifest.json) still records `status=failed` and `cleanup_error=active or unresolved selected-GPU peer; cancel only owned server`. Both remain unchanged; this document records retrospective attribution separately.

| Observation | Raw source position | UTC |
|---|---|---|
| First own=True for the generation | [telemetry line33](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/telemetry.jsonl:33), sample31 | 08:04:55.082320 |
| Last own=True | [telemetry line91](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/telemetry.jsonl:91), sample89 | 08:05:53.082353 |
| Same generation becomes own=False, alive=True/stateR | [telemetry line92](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/telemetry.jsonl:92), sample90 | 08:05:54.082324 |
| No later GPU-owner entry for this generation | telemetry samples91-98, lines93-100 | 08:05:55–08:06:02 |

The 59 prior samples contain 236 own=True mappings across selected GPUs4-7. Only sample90 changes the membership label. The parent host PID1889760 remains own=True; its start_ticks391972407 matches the manifest's owned target server-group start_ticks. The manifest group PID1083 and host PID1889760 belong to different recorded PID contexts; this review does not invent a further namespace mapping.

The captured request ran from **08:05:47.524796 to08:05:48.044800 UTC**. `/stop_profile` returned200. All four ranks logged `Profiling done` at08:05:51 in [server.log:584](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/server.log:584), before the ownership transition. At08:05:54, [server.log:589](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/server.log:589) records SIGTERM, followed by scheduler exit−15 and SIGQUIT cleanup. The transition therefore occurs after profiling/export, in the teardown interval. The one-second signal timestamps do not establish exact ordering within that second; sample90's collection spans08:05:54.082324–08:05:54.710983.

The event contains no KFD queue and no memory growth. Selected GPU utilization samples89/90 are all0%; sample91 VRAM has fallen to approximately1.70GB onGPU4 and0.303GB onGPU5-7. These observations do not prove process death or complete isolation; they support keeping the teardown event separate from the captured profiling window.

All four local original trace copies match the manifest sizes and SHA256 values:

| TP rank | Original trace | Bytes | SHA256 |
|---|---|---:|---|
| 0 | [full-tgemm-before-before-TP-0.trace.json.gz](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/traces/full-tgemm-before-before-TP-0.trace.json.gz) | 1999439 | `4388e53ea3ad6982ff3b81654989158941373781dbee5ab64d09ea454660b1dc` |
| 1 | [full-tgemm-before-before-TP-1.trace.json.gz](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/traces/full-tgemm-before-before-TP-1.trace.json.gz) | 1992906 | `270326a0ac2155e91fe7fb8f1a5b63caae662034947d1a8148bc5f9ac9a86c7d` |
| 2 | [full-tgemm-before-before-TP-2.trace.json.gz](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/traces/full-tgemm-before-before-TP-2.trace.json.gz) | 2000987 | `a4c051dc90b4988bfb8c2aceff7cdbb2a8ebdb169be47307805a85ed7e2a2d1a` |
| 3 | [full-tgemm-before-before-TP-3.trace.json.gz](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/results/profile_before/traces/full-tgemm-before-before-TP-3.trace.json.gz) | 1992548 | `220a6ba4dde268028c38d7fa720eaccc8b8fbaaa2de1e32138d9ac8e9edfb574` |

Source hashes and the preserved raw event are in [the machine-readable review](/home/hatian/workspace/projects/Qwen3.8/experiments/pr107_full_tgemm_20261116/review/tp4_before_cleanup_review.json). No original manifest/trace, source, runtime or hardware state was changed.
