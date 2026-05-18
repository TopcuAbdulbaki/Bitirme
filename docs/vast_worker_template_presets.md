# Vast Worker Template Presets

Bu dosya su senaryo icindir:

- `orchestrator` bu yerel Windows makinede calisir
- `RabbitMQ`, `PostgreSQL`, `MinIO` yine bu yerel makinededir
- `crawler`, `db`, `vlm`, `llm`, `cua` worker olarak Vast.ai uzerinde calisir

Bu nedenle Vast worker template'lerinde desktop zorunlu degildir. Normal akista SSH/Jupyter yeterlidir; worker kurulumunu guarded shell scriptleri yapar. CUA icin kullanici browser'i gormek isterse desktop image tercih edilebilir, ama headless CUA icin o da zorunlu degildir. `73478` ve `72299` gibi degerler gecerli TCP portlari degildir; burada bilerek kullanilmadi.

## Ortak Alanlar

Asagidaki alanlari tum worker template'lerinde ayni tut:

- Launch Mode: `Jupyter-python notebook + SSH`
- On-start Script: `entrypoint.sh`
- Jupyter direct HTTPS: `enabled`
- Use Jupyter Lab interface: `optional`
- Kiralanan makine Docker tabanli Vast instance olarak acilmalidir. Vast CLI `docker=true` diye bir search key kabul etmez; Docker gereksinimini offer filtresiyle degil template/image secimi ve startup kontroluyle dogrula.

Vast'ta offer arama donanim/availability filtresidir; instance'in hangi container image ile acilacagi template tarafinda belirlenir. Bu dosyadaki ana worker akisi `vastai/base-image:cuda-12.9.1-auto` gibi Docker image path'leriyle acilan Vast container'larini varsayar. Guarded host scriptleri Docker daemon gerektirmez; repo/venv/proto/import/connectivity kontrollerini yapip node'u dogrudan host/container icinde baslatir.

Eger eski `docker build` / `docker run` akisini bilerek kullanacaksan, bunu search filtresiyle garanti edemezsin. Bunun yerine Docker CLI/daemon'i olan bir image/template sec veya on-start/preflight kontroluyle uygun olmayan instance'i hemen fail ettir.

Vast CLI ile offer ararken Docker filtresi kullanma:

```bash
vastai search offers 'rentable=true verified=true'
```

GPU worker ararken sadece gecerli GPU kosullarini ekle:

```bash
vastai search offers 'rentable=true verified=true compute_cap>=700 cuda_max_good>=12.1'
```

Docker CLI/daemon gerektiren eski Docker build/run akisini kullanacaksan node icinde once su preflight kontrolunu yap:

```bash
command -v docker >/dev/null 2>&1 || { echo "Docker CLI yok; bu template Docker build/run akisi icin uygun degil"; exit 1; }
docker version >/dev/null 2>&1 || { echo "Docker daemon erisilemiyor"; exit 1; }
```

Bu kontrolu Vast template'in on-start scriptinin basina da koyabilirsin. Kontrol gecmezse worker kurulumu baslamaz; boylece yanlis instance uzerinde yarim kurulum kalmaz.

Varsayilan SSH/Jupyter image:

```text
vastai/base-image:cuda-12.9.1-auto
```

CUA'da browser gorunur olsun istenirse opsiyonel desktop image:

```text
vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05
```

Opsiyonel vLLM hazir image sadece manuel model API denemeleri icindir; guarded CUA scripti kendi vLLM venv'ini kurdugu icin ana yol degildir:

```text
vastai/vllm:v0.20.1-cuda-12.9
```

Ortak environment variables:

```text
OPEN_BUTTON_TOKEN="1"
JUPYTER_DIR="/"
DATA_DIRECTORY="/workspace/"
OPEN_BUTTON_PORT="1111"
SELKIES_ENCODER="x264enc"
```

Ortak portal iskeleti:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing
```

SSH-only/base-image worker'larda Selkies/Guacamole buttonlari anlamli olmayabilir; kritik erisim SSH ve Jupyter terminalidir. Options/env ayni tutulabilir, sadece desktop image secildiyse desktop buttonlari kullanilir.

Ortak docker options cekirdegi:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Bridge ile calisacaksan bu komutu yerel makinede ac:

```powershell
.\scripts\helper\windows\open_node_bridge.ps1 -VastHost <VAST_IP> -VastSshPort <SSH_PORT>
```

Sonra ilgili Vast node icinde `ORCHESTRATOR_HOST=127.0.0.1` ve gerekiyorsa `RABBITMQ_HOST=127.0.0.1`, `POSTGRES_HOST=127.0.0.1`, `MINIO_HOST=127.0.0.1` kullan.

## 1. Crawler Worker

- Template Name: `Base Image SSH/Jupyter (Crawler)`
- Template Description: `Vast worker for crawler node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `40 GB`
- Extra Filters: `gpu_display_active=false`

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
su - root
cd ~
curl -fsSL -o crawler.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/crawler.sh
chmod +x crawler.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 ./crawler.sh
```

## 2. DB Worker

- Template Name: `Base Image SSH/Jupyter (DB Worker)`
- Template Description: `Vast worker for DB node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `60 GB`
- Extra Filters: `gpu_display_active=false`

Bu worker kendi icinde `postgres` ve `minio` acmiyor; bridge uzerinden yerel makinedeki `5432` ve `9000` portlarina baglaniyor. Bu yuzden template seviyesinde ek browser portu acmaya gerek yok.

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
su - root
cd ~
curl -fsSL -o db.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/db.sh
chmod +x db.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=15432 \
MINIO_HOST=127.0.0.1 MINIO_PORT=19000 \
./db.sh
```

## 3. VLM Worker

- Template Name: `Base Image SSH/Jupyter (VLM)`
- Template Description: `GPU worker for VLM node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `100 GB`
- Extra Filters: `compute_cap>=700 cuda_max_good>=12.1 gpu_display_active=false`

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
su - root
cd ~
curl -fsSL -o vlm.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/vlm.sh
chmod +x vlm.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
MINIO_HOST=127.0.0.1 MINIO_PORT=19000 \
./vlm.sh
```

## 4. LLM Worker

- Template Name: `Base Image SSH/Jupyter (LLM)`
- Template Description: `GPU worker for LLM node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `100 GB`
- Extra Filters: `compute_cap>=700 cuda_max_good>=12.1 gpu_display_active=false`

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
su - root
cd ~
curl -fsSL -o llm.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/llm.sh
chmod +x llm.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
./llm.sh
```

## 5. CUA Worker (Distributed Node)

- Template Name: `Base Image SSH/Jupyter (CUA Node)`
- Template Description: `GPU worker for distributed CUA node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `100 GB`
- Extra Filters: `compute_cap>=700 cuda_max_good>=12.8 gpu_display_active=false`

Bu node `cua.sh` ile yerel vLLM de acacagi icin `1234` portunu debug amacli acmak mantiklidir. Browser'in gorunur olmasi istenirse ayni env/options ile sadece image `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05` yapilabilir ve `BROWSER_HEADLESS=false` verilebilir.

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing|localhost:1234:11234:/v1/models:vLLM API
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -p 1234:1234 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing|localhost:1234:11234:/v1/models:vLLM API" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
su - root
cd ~
curl -fsSL -o cua.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/cua.sh
chmod +x cua.sh
CUA_RUN_MODE=node \
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
./cua.sh
```

## 6. CUA Worker (Standalone Test)

Bu sadece lokal test veya tek makine denemesi icindir. Dagitik sisteme worker olarak baglanmaz.

- Template Name: `Base Image SSH/Jupyter (CUA Standalone)`
- Template Description: `GPU standalone CUA + vLLM test node`
- Image Path:Tag: `vastai/base-image:cuda-12.9.1-auto`
- Version Tag: `cuda-12.9.1-auto`
- Disk: `100 GB`
- Extra Filters: `compute_cap>=700 cuda_max_good>=12.8 gpu_display_active=false`

`PORTAL_CONFIG`:

```text
localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing|localhost:1234:11234:/v1/models:vLLM API
```

Docker Options:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -p 1234:1234 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/guacamole:Apache Guacamole Desktop (VNC)|localhost:8080:8080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing|localhost:1234:11234:/v1/models:vLLM API" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Node baslatma:

```bash
cd ~
curl -fsSL -o cua.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/linux/cua.sh
chmod +x cua.sh
REPO_URL='https://github.com/TopcuAbdulbaki/Bitirme.git' ./cua.sh
```

## Notlar

- Worker template'lerinde `50051`, `5672`, `15672`, `5432`, `9000`, `9001` gibi portlari Vast tarafinda acmak zorunda degilsin; bridge kullaniyorsan bunlar yerel makinede kalir.
- Crawler, VLM ve LLM node'lari browser UI sunmaz; bu yuzden portal tarafinda ek HTTP button tanimlamadim.
- CUA distributed template'inde `1234` acik birakildi cunku script node modunda da yerel vLLM aciyor.
- Worker komutlarinin guncel hali [scripts/all.md](/C:/Users/HP/Desktop/Projeler/Bitirme/scripts/all.md) icinde de bulunur.
