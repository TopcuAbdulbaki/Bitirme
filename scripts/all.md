# Bitirme Node Kurulum Notlari

Ilk hedef: Vast.ai uzerinde CUA standalone. Bu modda Orchestrator, RabbitMQ ve DB gerekmez; CUA dogrudan browser-use + vLLM ile surface haber toplama testini calistirir.

## CUA Standalone - Vast.ai Linux

### 0. Vast terminale gir

Vast instance icinde Guacamole desktop varsa sol panel clipboard icin `Ctrl + Alt + Shift` ise yariyor. Kurulum icin yine de terminal/SSH kullanmak daha saglam.

```bash
ssh root@<VAST_IP> -p <SSH_PORT>
```

### 1. Tek komutla indir ve calistir

Repo public oldugu icin token gerekmez. Script repo dosyalarini GitHub'dan ceker, vLLM'i ayri venv'e kurar, Qwen vision modeli servis eder, CUA venv'ini hazirlar ve standalone surface testi calistirir.

```bash
cd ~
curl -fsSL -o vast_cua_standalone.sh \
  https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_standalone.sh
chmod +x vast_cua_standalone.sh
./vast_cua_standalone.sh
```

Varsayilanlar:

```bash
REPO_URL=https://github.com/TopcuAbdulbaki/Bitirme.git
APP_DIR=$HOME/Bitirme
MODEL_ID=Qwen/Qwen3.5-9B
VLLM_PORT=1234
VLLM_API_KEY=lm-studio
CUA_QUERY="Turkey economy 2026"
MAX_ARTICLES=3
MAX_CYCLES=6
SEARCH_ENGINE=duckduckgo
MAX_MODEL_LEN=32768
GPU_MEMORY_UTILIZATION=0.92
```

### 2. Sorgu/model parametreleriyle calistir

```bash
CUA_QUERY="Turkey inflation latest news" \
MAX_ARTICLES=5 \
MAX_CYCLES=8 \
./vast_cua_standalone.sh
```

Iki GPU varsa:

```bash
TENSOR_PARALLEL_SIZE=2 \
GPU_MEMORY_UTILIZATION=0.90 \
./vast_cua_standalone.sh
```

Farkli repo branch/URL ile:

```bash
REPO_URL="https://github.com/TopcuAbdulbaki/Bitirme.git" \
APP_DIR="$HOME/Bitirme" \
./vast_cua_standalone.sh
```

### 3. Manuel Linux kurulumu

Script kullanmadan elle yapmak istersen:

```bash
apt-get update
apt-get install -y git curl ca-certificates python3 python3-venv python3-pip build-essential

cd ~
git clone https://github.com/TopcuAbdulbaki/Bitirme.git Bitirme
cd ~/Bitirme
```

vLLM icin ayri venv:

```bash
python3 -m venv ~/.venvs/vllm
source ~/.venvs/vllm/bin/activate
python -m pip install -U pip
pip install -U vllm transformers accelerate safetensors sentencepiece
deactivate
```

vLLM server baslat:

```bash
pkill -f "vllm serve" || true
export VLLM_USE_V1=0
nohup ~/.venvs/vllm/bin/vllm serve Qwen/Qwen3.5-9B \
  --trust-remote-code \
  --host 0.0.0.0 \
  --port 1234 \
  --api-key lm-studio \
  --dtype half \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92 \
  --tensor-parallel-size 1 \
  > ~/vllm.log 2>&1 &
```

Hazir mi kontrol et:

```bash
tail -f ~/vllm.log
curl -s http://127.0.0.1:1234/v1/models \
  -H "Authorization: Bearer lm-studio"
```

CUA venv ve browser kurulumu:

```bash
cd ~/Bitirme
python3 -m venv cua/.venv
source cua/.venv/bin/activate
python -m pip install -U pip
pip install -U -r cua/requirements.txt
python -m playwright install chromium --with-deps
```

Standalone CUA surface test:

```bash
cd ~/Bitirme
source cua/.venv/bin/activate

export MODEL_NAME="Qwen/Qwen3.5-9B"
export LMSTUDIO_URL="http://127.0.0.1:1234/v1"
export SEARCH_ENGINE="duckduckgo"
export BROWSER_HEADLESS="true"

python -m cua.test_local \
  --mode surface \
  --query "Turkey economy 2026" \
  --max-articles 3 \
  --max-cycles 6 \
  --engine duckduckgo \
  --lmstudio-url "$LMSTUDIO_URL" \
  --output cua_test_result_surface.json
```

### 4. Beklenen cikti

Basarili calisinca repo kokunde su dosya olusur:

```bash
~/Bitirme/cua_test_result_surface.json
```

Kontrol:

```bash
cat ~/Bitirme/cua_test_result_surface.json
```

### 5. Siklikla gereken debug komutlari

vLLM log:

```bash
tail -n 200 ~/vllm.log
```

vLLM sureci:

```bash
pgrep -af "vllm serve"
```

GPU:

```bash
nvidia-smi
```

CUA'yi tekrar calistir:

```bash
cd ~/Bitirme
source cua/.venv/bin/activate
export MODEL_NAME="Qwen/Qwen3.5-9B"
export LMSTUDIO_URL="http://127.0.0.1:1234/v1"
python -m cua.test_local --mode surface --query "Turkey economy" --max-articles 3
```

vLLM'i durdur:

```bash
pkill -f "vllm serve"
```

Repoyu guncelle:

```bash
cd ~/Bitirme
git pull --ff-only
source cua/.venv/bin/activate
pip install -U -r cua/requirements.txt
```

## Sonraki Node Notlari

Bu dosyaya ayni formatta sirayla eklenecek:

- Orchestrator
- Crawler
- DB
- VLM
- LLM
- CUA distributed
