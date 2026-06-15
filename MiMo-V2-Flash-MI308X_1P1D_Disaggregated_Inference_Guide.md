# MiMo-V2-Flash 1P1D Disaggregated Inference Guide on 12N MI308X

## Prefill node: mi308-ccs-aus-e06-10.prov.aus.ccs.cpe.ice.amd.com (10.235.192.101)
## Decode node:  mi308-ccs-aus-e06-01.prov.aus.ccs.cpe.ice.amd.com (10.235.192.97)

## 1. Access to 12N MI308X in Citrix
```bash
ssh  -i .ssh/id_rsa xisun@mi308-ccs-aus-e06-10.prov.aus.ccs.cpe.ice.amd.com
ssh  -i .ssh/id_rsa xisun@mi308-ccs-aus-e06-01.prov.aus.ccs.cpe.ice.amd.com
```

## 2. MiMo-V2-Flash single node TP=8 test
### 2.1 Pull docker image
```bash
sudo docker pull rocm/sgl-dev:v0.5.11-rocm720-mi30x-20260510
```
| Rocm version  | 7.2.0                                       |
| ------------- | ------------------------------------------- |
| Docker        | 29.1.3                                      |
| Docker  image | rocm/sgl-dev:v0.5.11-rocm720-mi30x-20260510 |
| Sglang        | 0.5.11.dev20260510+g2f0686712               |
| Aiter         | 0.1.12.post2.dev150+ga6bb49937.d20260510    |
| Pytorch       | 2.9.1                                       |
| Mooncake      | v0.3.7.post2                                |

### 2.1 Launch docker 

```bash
sudo docker run -it --name sgl-dev-v0.5.11-rocm720-mi30x-20260510-mimo-v2.5-pro-xisun --shm-size 64g --privileged --network=host --ipc=host \
--device=/dev/kfd --device=/dev/dri \
--group-add video \
--cap-add=SYS_PTRACE \
--security-opt seccomp=unconfined \
-v /apps/shared/xisun/:/workspace \
-v /apps/shared/xiaomi:/models \
--workdir /workspace \
rocm/sgl-dev:v0.5.11-rocm720-mi30x-20260510
```



安装支持MTP的sglang版本

```bash
pip uninstall -y sglang
git clone -b https://github.com/TianHao65/sglang.git
cd sglang
git checkout Mimo_mtp_enable

\# Compile sgl-kernel
pip install --upgrade pip
cd sgl-kernel
python3 setup_rocm.py install

\# Install sglang python package
cd ..
rm -rf python/pyproject.toml && mv python/pyproject_other.toml python/pyproject.toml
pip install -e "python[all_hip]"
```



### 2.2 Launch server with TP=8 in single node w/o PD disaggreate

```bash
declare -x SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN="1" 
declare -x SGLANG_DISABLE_CUDNN_CHECK="1" 
declare -x SGLANG_INT4_WEIGHT="0" 
declare -x SGLANG_MOE_PADDING="1" 
declare -x SGLANG_ROCM_DISABLE_LINEARQUANT="0" 
declare -x SGLANG_ROCM_FUSED_DECODE_MLA="1" 
declare -x SGLANG_SET_CPU_AFFINITY="1" 
declare -x SGLANG_USE_AITER="1" 
declare -x SGLANG_USE_ROCM700A="1" 
 
python3 -m sglang.launch_server \
    --model /models/MiMo-V2-Flash \
    --port 30000 \
    --host 0.0.0.0 \
    --tp-size 8 \
    --dp-size 2 \
    --trust-remote-code \
    --cuda-graph-max-bs 32 \
    --mem-fraction-static 0.8 \
    --attention-backend triton \
    --chunked-prefill-size 32768\
2>&1 | tee sglang_server.log  

```

### 2.3 Run single curl for functional test
```bash
curl -X POST http://127.0.0.1:30000/generate \
-H "Content-Type: application/json" \
-d '{ "text": "Let me tell you a story ", "sampling_params": { "temperature":
0.3 } }'
```

### 2.4 Run GSM8K Accruacy test
```bash
cd /sgl-workspace/sglang
python3 benchmark/gsm8k/bench_sglang.py --parallel 128 --num-questions 1400
```
```bash
root@mi308-ccs-aus-e07-22:/sgl-workspace/sglang# python3 benchmark/gsm8k/bench_sglang.py --parallel 128 --num-questions 1400
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████| 1319/1319 [02:25<00:00,  9.05it/s]
Accuracy: 0.958
Invalid: 0.002
Latency: 145.740 s
Output throughput: 1078.936 token/s
```

## 3. MiMo-V2-Flash 1P1D w/ PD disaggreate

### 2.1 Launch docker 
```bash
sudo docker run -itd --name sgl-dev-v0.5.11-rocm720-mi30x-20260510-mimo-v2-flash-hatian --shm-size 64g --privileged --network=host --ipc=host \
--device=/dev/kfd --device=/dev/dri \
--group-add video \
--cap-add=SYS_PTRACE \
--security-opt seccomp=unconfined \
-v /apps/shared/hatian/:/work \
-v /apps/shared/xiaomi:/models \
--workdir /work \
rocm/sgl-dev:v0.5.11-rocm720-mi30x-20260510
```
```bash
sudo docker run -itd --name sgl-dev-v0.5.11-rocm720-mi30x-20260510-mimo-v2-flash-hatian --shm-size 64g --privileged --network=host --ipc=host \
--device=/dev/kfd --device=/dev/dri \
--group-add video \
--cap-add=SYS_PTRACE \
--security-opt seccomp=unconfined \
-v /apps/shared/hatian/:/work \
-v /apps/shared/xiaomi:/models \
--workdir /work \
rocm/sgl-dev:v0.5.11-rocm720-mi30x-20260510
```
### 3.1. Setup environment for prefill node: mi308-ccs-aus-e06-10
#### 3.1.1. Clone llm-distributed-inference repo for helper scripts
```bash
git clone https://github.com/sammysun0711/llm-distributed-inference.git
cd llm-distributed-inference/sglang
```

#### 3.1.2. Install etcd for cluster metadata storage
```bash
./scripts/install_etcd.sh
```

#### 3.1.3. Install Mooncake for KV cache transfer between nodes
```bash
./scripts/install_mooncake.sh
#pip install mooncake-transfer-engine==0.3.7.post2
```

#### 3.1.4. Install the NIC RDMA driver
```bash
./scripts/install_nic_rdma_driver.sh
```
Check the RDMA devices: 
```
    device                 node GUID
    ------              ----------------
    mlx5_0              58a2e1030011d554
    mlx5_1              58a2e1030011d555
    mlx5_2              a088c20300391dc4
    mlx5_3              a088c20300391dc5
    bnxt_re_benic6b     4cc6f6fffe54aab3
    bnxt_re_benic1b     3ce00dfffe516e78
    bnxt_re_benic7b     d8d754fffe9e4614
    bnxt_re_benic2b     981847fffeecc8f7
    bnxt_re_benic8b     d0f794fffec75983
    bnxt_re_benic5b     904359fffe4fe96f
    bnxt_re_benic3b     e89ae9fffe2a5983
    bnxt_re_benic4b     18fb8dfffe266b37
```

#### 3.1.5. Build and install the ROCm-aware UCX library
```bash
source ./scripts/build_ucx.sh
```
Verify UCX ROCm support
```bash
ucx_info -v
```
```bash
# Library version: 1.18.1
# Library path: /opt/ucx/lib/libucs.so.0
# API headers version: 1.18.1
# Git branch '', revision d9aa565
# Configured with: --with-rocm=/opt/rocm --enable-mt --prefix=/opt/ucx
```

#### 3.1.6. Build and install the ROCm-Aware Open MPI library
```bash
source ./scripts/build_ompi.sh
```
Verify Open MPI ROCm support
```bash
ompi_info | grep "extensions"
```
```bash
          MPI extensions: affinity, cuda, ftmpi, rocm
```

### 3.2. Repeat step 3.1.1 – 3.1.6 on decode node

### 3.3 Setup SSH for docker container on multi GPU node
Use setup_docker_passwdless_ssh.sh to setup passwordless ssh connection, please follow the instructions provided by the scripts. 
Please note: Need to manually copy public key to /root/.ssh/authorized_keys on remote GPU node.

Setup ssh connection for docker container on prefill node mi308-ccs-aus-e06-10 to remote decode node mi308-ccs-aus-e06-01, need to follow script instruction to copy ssh key to /root/.ssh/authorized_keys on mi308-ccs-aus-e06-01
```bash
./scripts/setup_docker_passwdless_ssh.sh mi308-ccs-aus-e06-01
```
Setup ssh connection for docker container on decode node mi308-ccs-aus-e06-01 to remote prefill node mi308-ccs-aus-e06-10, need to follow script instruction to copy ssh key to /root/.ssh/authorized_keys on mi308-ccs-aus-e06-10
```bash
./scripts/setup_docker_passwdless_ssh.sh mi308-ccs-aus-e06-10
```
Check passwordless connections on mi308-ccs-aus-e06-10
```bash
ssh mi308-ccs-aus-e06-01 hostname
```
```bash
root@mi308-ccs-aus-e06-10:/workspace# ssh mi308-ccs-aus-e06-01 hostname
mi308-ccs-aus-e06-01.prov.aus.ccs.cpe.ice.amd.com
```

Check passwordless connections on mi308-ccs-aus-e06-01
```bash
ssh mi308-ccs-aus-e06-10 hostname
```
```bash
mi308-ccs-aus-e06-10.prov.aus.ccs.cpe.ice.amd.com
```

### 4.1 Build and run RCCL test
```bash
git clone https://github.com/ROCm/rccl-tests
cd rccl-tests
./install.sh --mpi --rocm_home /opt/rocm --rccl_home /opt/rocm --mpi_home /opt/ompi/ --hip_compiler /opt/rocm/bin/amdclang++
```
### 4.2 Create mpi_hosts file as follows and save in disk: 
```
cd /workspace/xiaomi/rccl-tests

cat > mpi_hosts <<EOF
mi308-ccs-aus-e06-01 slots=8
mi308-ccs-aus-e06-10 slots=8
EOF

cat mpi_hosts
```


# 4.3.	Run RCCL All Reduce test on 2 GPU nodes
```bash
TORCH_NCCL_HIGH_PRIORITY=1 \
RCCL_MSCCL_ENABLE=0 \
mpirun -np 16 \
  --map-by ppr:8:node \
  --hostfile mpi_hosts \
  --allow-run-as-root \
  --mca pml ucx --mca btl ^openib \
  --mca plm_rsh_args "-p 2222" \
  -x NCCL_SOCKET_IFNAME=ens50f1np1 \
  -x NCCL_DEBUG=VERSION \
  -x NCCL_IB_HCA="=bnxt_re_benic1b,bnxt_re_benic2b,bnxt_re_benic3b,bnxt_re_benic4b,bnxt_re_benic5b,bnxt_re_benic6b,bnxt_re_benic7b,bnxt_re_benic8b" \
  -x NCCL_IB_GID_INDEX=3 \
  -x HSA_NO_SCRATCH_RECLAIM=1 \
  ./build/all_reduce_perf -b 1K -e 2G -f 2 -g 1
```


```bash
root@mi308-ccs-aus-e06-10:/workspace/xiaomi/rccl-tests# TORCH_NCCL_HIGH_PRIORITY=1 \
RCCL_MSCCL_ENABLE=0 \
mpirun -np 16 \
  --map-by ppr:8:node \
  --hostfile mpi_hosts \
  --allow-run-as-root \
  --mca pml ucx --mca btl ^openib \
  --mca plm_rsh_args "-p 2222" \
  -x NCCL_SOCKET_IFNAME=ens50f1np1 \
  -x NCCL_DEBUG=VERSION \
  -x NCCL_IB_HCA="=bnxt_re_benic1b,bnxt_re_benic2b,bnxt_re_benic3b,bnxt_re_benic4b,bnxt_re_benic5b,bnxt_re_benic6b,bnxt_re_benic7b,bnxt_re_benic8b" \
  -x NCCL_IB_GID_INDEX=3 \
  -x HSA_NO_SCRATCH_RECLAIM=1 \
  ./build/all_reduce_perf -b 1K -e 2G -f 2 -g 1
bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
# Collective test starting: all_reduce_perf
# nThread 1 nGpus 1 minBytes 1024 maxBytes 2147483648 step: 2(factor) warmup iters: 5 iters: 20 agg iters: 1 validation: 1 graph: 0
#
rccl-tests: Version develop_deprecated:40b1b17
# Using devices
#  Rank  0 Group  0 Pid 224254 on mi308-ccs-aus-e06-01 device  0 [0000:05:00] AMD Instinct MI308X
#  Rank  1 Group  0 Pid 224255 on mi308-ccs-aus-e06-01 device  1 [0000:27:00] AMD Instinct MI308X
#  Rank  2 Group  0 Pid 224258 on mi308-ccs-aus-e06-01 device  2 [0000:47:00] AMD Instinct MI308X
#  Rank  3 Group  0 Pid 224257 on mi308-ccs-aus-e06-01 device  3 [0000:65:00] AMD Instinct MI308X
#  Rank  4 Group  0 Pid 224256 on mi308-ccs-aus-e06-01 device  4 [0000:85:00] AMD Instinct MI308X
#  Rank  5 Group  0 Pid 224259 on mi308-ccs-aus-e06-01 device  5 [0000:a7:00] AMD Instinct MI308X
#  Rank  6 Group  0 Pid 224260 on mi308-ccs-aus-e06-01 device  6 [0000:c7:00] AMD Instinct MI308X
#  Rank  7 Group  0 Pid 224261 on mi308-ccs-aus-e06-01 device  7 [0000:e5:00] AMD Instinct MI308X
#  Rank  8 Group  0 Pid 420341 on mi308-ccs-aus-e06-10 device  0 [0000:05:00] AMD Instinct MI308X
#  Rank  9 Group  0 Pid 420342 on mi308-ccs-aus-e06-10 device  1 [0000:27:00] AMD Instinct MI308X
#  Rank 10 Group  0 Pid 420343 on mi308-ccs-aus-e06-10 device  2 [0000:47:00] AMD Instinct MI308X
#  Rank 11 Group  0 Pid 420344 on mi308-ccs-aus-e06-10 device  3 [0000:65:00] AMD Instinct MI308X
#  Rank 12 Group  0 Pid 420345 on mi308-ccs-aus-e06-10 device  4 [0000:85:00] AMD Instinct MI308X
#  Rank 13 Group  0 Pid 420346 on mi308-ccs-aus-e06-10 device  5 [0000:a7:00] AMD Instinct MI308X
#  Rank 14 Group  0 Pid 420347 on mi308-ccs-aus-e06-10 device  6 [0000:c7:00] AMD Instinct MI308X
#  Rank 15 Group  0 Pid 420348 on mi308-ccs-aus-e06-10 device  7 [0000:e5:00] AMD Instinct MI308X
RCCL version : 2.27.7-HEAD:0d2c4fd
HIP version  : 7.2.26015-fc0010cf6a
ROCm version : 7.2.0.0-43-fc0010cf6a
Hostname     : mi308-ccs-aus-e06-01.prov.aus.ccs.cpe.ice.amd.com
Librccl path : /opt/rocm-7.2.0/lib/librccl.so.1
#
#                                                              out-of-place                       in-place          
#       size         count      type   redop    root     time   algbw   busbw #wrong     time   algbw   busbw #wrong                               
#        (B)    (elements)                               (us)  (GB/s)  (GB/s)            (us)  (GB/s)  (GB/s)                                      
        1024           256     float     sum      -1    40.86    0.03    0.05      0    39.88    0.03    0.05      0
        2048           512     float     sum      -1    43.40    0.05    0.09      0    43.70    0.05    0.09      0
        4096          1024     float     sum      -1    45.41    0.09    0.17      0    44.33    0.09    0.17      0
        8192          2048     float     sum      -1    46.04    0.18    0.33      0    44.61    0.18    0.34      0
       16384          4096     float     sum      -1    46.49    0.35    0.66      0    45.46    0.36    0.68      0
       32768          8192     float     sum      -1    47.75    0.69    1.29      0    47.22    0.69    1.30      0
       65536         16384     float     sum      -1    50.34    1.30    2.44      0    50.05    1.31    2.45      0
      131072         32768     float     sum      -1    55.77    2.35    4.41      0    51.86    2.53    4.74      0
      262144         65536     float     sum      -1    64.23    4.08    7.65      0    62.18    4.22    7.91      0
      524288        131072     float     sum      -1    78.71    6.66   12.49      0    81.75    6.41   12.02      0
     1048576        262144     float     sum      -1    70.21   14.94   28.00      0    136.2    7.70   14.44      0
     2097152        524288     float     sum      -1    81.85   25.62   48.04      0    80.73   25.98   48.71      0
     4194304       1048576     float     sum      -1    94.90   44.19   82.87      0    93.63   44.80   83.99      0
     8388608       2097152     float     sum      -1    229.6   36.53   68.49      0    231.2   36.29   68.04      0
    16777216       4194304     float     sum      -1    335.9   49.94   93.64      0    338.3   49.59   92.97      0
    33554432       8388608     float     sum      -1    431.3   77.79  145.86      0    434.4   77.24  144.83      0
    67108864      16777216     float     sum      -1    673.5   99.65  186.84      0    673.6   99.63  186.80      0
   134217728      33554432     float     sum      -1   1509.4   88.92  166.73      0   1494.2   89.82  168.42      0
   268435456      67108864     float     sum      -1   1748.4  153.53  287.87      0   1726.7  155.47  291.50      0
   536870912     134217728     float     sum      -1   3027.1  177.35  332.54      0   3022.3  177.64  333.07      0
  1073741824     268435456     float     sum      -1   6397.1  167.85  314.71      0   6400.5  167.76  314.55      0
  2147483648     536870912     float     sum      -1    12816  167.56  314.17      0    12829  167.39  313.87      0
# Errors with asterisks indicate errors that have exceeded the maximum threshold.
# Out of bounds values : 0 OK
# Avg bus bandwidth    : 95.233 
#
# Collective test concluded: all_reduce_perf
```

## 5.1 Launch prefill server on prefill node
```bash
export SGLANG_USE_AITER=1
export TORCH_NCCL_BLOCKING_WAIT=1
export MC_GID_INDEX=3
export HSA_NO_SCRATCH_RECLAIM=1
export MC_TE_METRIC=1
export SGLANG_DISAGGREGATION_THREAD_POOL_SIZE=12
export SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=5000
export SGLANG_DISAGGREGATION_WAITING_TIMEOUT=5000
python3 -m sglang.launch_server \
    --model /models/MiMo-V2-Flash \
    --disaggregation-mode prefill \
    --disaggregation-transfer-backend mooncake \
    --disaggregation-ib-device bnxt_re_benic1b,bnxt_re_benic2b,bnxt_re_benic3b,bnxt_re_benic4b,bnxt_re_benic5b,bnxt_re_benic6b,bnxt_re_benic7b,bnxt_re_benic8b \
    --port 30000 \
    --host 0.0.0.0 \
    --tp-size 8 \
    --dp-size 2 \
    --enable-dp-attention \
    --enable-dp-lm-head \
    --mm-enable-dp-encoder \
    --trust-remote-code \
    --mem-fraction-static 0.9 \
    --attention-backend triton \
    --max-running-requests 96 \
    --disable-cuda-graph \
    --chunked-prefill-size 32768 \
    --page-size 64 \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 1 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 2 \
    --enable-multi-layer-eagle \
    2>&1 | tee ./server_log/mimo_v2_flash_pd_prefill_server.log

```

## 5.2 Launch decode server on decode node
```bash
export SGLANG_USE_AITER=1
export MC_GID_INDEX=3
export TORCH_NCCL_BLOCKING_WAIT=1
export HSA_NO_SCRATCH_RECLAIM=1
export MC_TE_METRIC=1
export SGLANG_DISAGGREGATION_THREAD_POOL_SIZE=12
export SGLANG_DISAGGREGATION_BOOTSTRAP_TIMEOUT=5000
export SGLANG_DISAGGREGATION_WAITING_TIMEOUT=5000

python3 -m sglang.launch_server \
    --model /models/MiMo-V2-Flash \
    --disaggregation-mode decode \
    --disaggregation-transfer-backend mooncake \
    --disaggregation-ib-device bnxt_re_benic1b,bnxt_re_benic2b,bnxt_re_benic3b,bnxt_re_benic4b,bnxt_re_benic5b,bnxt_re_benic6b,bnxt_re_benic7b,bnxt_re_benic8b \
    --port 30001 \
    --host 0.0.0.0 \
    --tp-size 8 \
    --dp-size 2 \
    --enable-dp-attention \
    --enable-dp-lm-head \
    --mm-enable-dp-encoder \
    --trust-remote-code \
    --mem-fraction-static 0.9 \
    --attention-backend triton \
    --max-running-requests 96 \
    --chunked-prefill-size 32768 \
    --page-size 64 \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 1 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 2 \
    --enable-multi-layer-eagle \
    2>&1 | tee ./server_log/mimo_v2_flash_pd_decode_server_mtp.log
```

## 5.3 Launch sglang router on prefill node
```bash
python -m sglang_router.launch_router \
--pd-disaggregation \
--prefill http://10.235.192.101:30000 \
--decode http://10.235.192.97:30001 \
--host 0.0.0.0 \
--port 40000
```

### 5.4 Run single curl for functional test
```bash
curl -X POST http://127.0.0.1:40000/generate \
-H "Content-Type: application/json" \
-d '{ "text": "Let me tell you a story ", "sampling_params": { "temperature":
0.3 } }'
```

```bash
{"text":" Let me tell you a story about a man named Charlie  On a tragic and fateful day  He put ten cents in his pocket, kissed his wife and family  Went to ride on the MTA  Well, did he ever return? No, he never returned  And his fate is still unlearned (what a pity)  He may ride forever 'neath the streets of Boston  He's the man who never returned  Now, Charlie handed in his dime at the Kendall Square Station  And he changed for Jamaica Plain  When he got there the conductor told him, \"One more nickel\"  Charlie couldn't get off","output_ids":[6771,752,3291,498,264,3364,911,264,883,6941,24927,220,1913,264,34179,323,282,20840,1899,220,1260,2182,5779,30191,304,806,17822,11,58234,806,7403,323,2997,220,53759,311,11877,389,279,386,15204,220,8325,11,1521,566,3512,470,30,2308,11,566,2581,5927,220,1597,806,24382,374,2058,650,12675,291,320,12555,264,56943,8,220,1260,1231,11877,15683,364,27817,279,14371,315,10196,220,1260,594,279,883,879,2581,5927,220,4695,11,24927,22593,304,806,73853,518,279,73076,15619,16629,220,1597,566,5497,369,56175,43199,220,3197,566,2684,1052,279,60756,3229,1435,11,330,3966,803,51249,1,220,24927,7691,944,633,1007],"meta_info":{"id":"3c98ab3684934687b2f863f0c267d35e","finish_reason":{"type":"length","length":128},"prompt_tokens":7,"weight_version":"default","num_retractions":0,"reasoning_tokens":0,"completion_tokens":128,"cached_tokens":0,"cached_tokens_details":null,"dp_rank":null,"e2e_latency":12.085600160993636,"response_sent_to_client_ts":1779867031.223716}}
```
### 5.5 Run GSM8K Accuracy test
```bash
cd /sgl-workspace/sglang
python3 benchmark/gsm8k/bench_sglang.py --parallel 128 --num-questions 1400 --host 0.0.0.0 --port 40000
```

```bash
root@mi308-ccs-aus-e06-10:/workspace/xiaomi# ./run_gsm8k.sh 
Downloading from https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl to /tmp/test.jsonl
/tmp/test.jsonl: 732kB [00:00, 38.0MB/s]                   
100%|██████████| 1319/1319 [02:36<00:00,  8.44it/s]
Accuracy: 0.958
Invalid: 0.002
Latency: 156.316 s
Output throughput: 1008.646 token/s
```
### 5.6 Run benchmark
```bash
#!/bin/bash # 推荐添加 shebang

# TOKEN_LIST=(1024 2048 4096 8192 16384 32768 65536 131072)
TOKEN_LIST=(1)
output_tokens=2048 
concurrency_list=(64 96) # 定义并发列表

# 循环执行：每个长度跑多次 (1次)，每次对应不同的并发
for input_tokens in "${TOKEN_LIST[@]}"; do
  for concurrency in "${concurrency_list[@]}"; do # 遍历并发列表
    # 每个长度和并发组合执行1轮测试
    run=1 # 只运行一轮
    echo -e "\n============================================================"
    echo "正在测试：输入 Token = ${input_tokens}, 并发数 = ${concurrency} | 第 ${run} 次运行"
    echo "日志文件：benchmark_decode_${input_tokens}_con${concurrency}_${run}.log"
    echo "============================================================"

    # 执行压测：终端显示 + 写入独立日志
    python3 -m sglang.bench_serving \
        --backend sglang \
        --model /models/MiMo-V2-Flash \
        --host 0.0.0.0 \
        --port 40000 \
        --dataset-name random \
        --random-input-len ${input_tokens} \
        --random-output-len ${output_tokens} \
        --random-range-ratio 1.0 \
        --flush-cache \
        --seed 12345 \
        --num-prompts 128 \
        --warmup-requests 32 \
        --max-concurrency ${concurrency} \
        --pd-separated \
        2>&1 | tee "./benchmark_log/benchmark_decode_mtp_${input_tokens}_con${concurrency}.log"

    echo -e "============================================================\n"
  done
done

echo "✅ 所有长度、并发测试全部完成！"
```



