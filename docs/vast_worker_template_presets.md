# Vast Worker Template Presets

Bu dosya su senaryo icindir:

- `orchestrator` bu yerel Windows makinede calisir
- `RabbitMQ`, `PostgreSQL`, `MinIO` yine bu yerel makinededir
- `crawler`, `db`, `vlm`, `llm`, `cua` worker olarak Vast.ai uzerinde calisir

Bu nedenle Vast worker template'lerinde sadece desktop/Jupyter erisimi ve gerekiyorsa worker'a ozel debug portlari acilir. `73478` ve `72299` gibi degerler gecerli TCP portlari degildir; burada bilerek kullanilmadi.

## Ortak Alanlar

Asagidaki alanlari tum worker template'lerinde ayni tut:

- Launch Mode: `Jupyter-python notebook + SSH`
- On-start Script: `entrypoint.sh`
- Jupyter direct HTTPS: `enabled`
- Use Jupyter Lab interface: `optional`

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

Ortak desktop docker options cekirdegi:

```text
-p 8080:8080 -p 1111:1111 -p 6100:6100 -p 6200:6200 -p 5900:5900 -p 8384:8384 -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e OPEN_BUTTON_PORT="1111" -e SELKIES_ENCODER="x264enc" --ipc=host
```

Bridge ile calisacaksan bu komutu yerel makinede ac:

```powershell
.\scripts\open_vast_node_bridge.ps1 -VastHost <VAST_IP> -VastSshPort <SSH_PORT>
```

Sonra ilgili Vast node icinde `ORCHESTRATOR_HOST=127.0.0.1` ve gerekiyorsa `RABBITMQ_HOST=127.0.0.1`, `POSTGRES_HOST=127.0.0.1`, `MINIO_HOST=127.0.0.1` kullan.

## 1. Crawler Worker

- Template Name: `Linux Desktop Container (Crawler)`
- Template Description: `Vast worker for crawler node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
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
curl -fsSL -o vast_crawler_host_guarded.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_crawler_host_guarded.sh
chmod +x vast_crawler_host_guarded.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 ./vast_crawler_host_guarded.sh
```

## 2. DB Worker

- Template Name: `Linux Desktop Container (DB Worker)`
- Template Description: `Vast worker for DB node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
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
curl -fsSL -o vast_db_host_guarded.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_db_host_guarded.sh
chmod +x vast_db_host_guarded.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=15432 \
MINIO_HOST=127.0.0.1 MINIO_PORT=19000 \
./vast_db_host_guarded.sh
```

## 3. VLM Worker

- Template Name: `Linux Desktop Container (VLM)`
- Template Description: `GPU worker for VLM node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
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
curl -fsSL -o vast_vlm_host_guarded.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_vlm_host_guarded.sh
chmod +x vast_vlm_host_guarded.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
MINIO_HOST=127.0.0.1 MINIO_PORT=19000 \
./vast_vlm_host_guarded.sh
```

## 4. LLM Worker

- Template Name: `Linux Desktop Container (LLM)`
- Template Description: `GPU worker for LLM node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
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
curl -fsSL -o vast_llm_host_guarded.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_llm_host_guarded.sh
chmod +x vast_llm_host_guarded.sh
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
./vast_llm_host_guarded.sh
```

## 5. CUA Worker (Distributed Node)

- Template Name: `Linux Desktop Container (CUA Node)`
- Template Description: `GPU worker for distributed CUA node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
- Disk: `100 GB`
- Extra Filters: `compute_cap>=700 cuda_max_good>=12.8 gpu_display_active=false`

Bu node `vast_cua_host_guarded.sh` ile yerel vLLM de acacagi icin `1234` portunu debug amacli acmak mantiklidir.

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
curl -fsSL -o vast_cua_host_guarded.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_host_guarded.sh
chmod +x vast_cua_host_guarded.sh
CUA_RUN_MODE=node \
ORCHESTRATOR_HOST=127.0.0.1 ORCHESTRATOR_PORT=15051 \
RABBITMQ_HOST=127.0.0.1 RABBITMQ_PORT=15670 \
./vast_cua_host_guarded.sh
```

## 6. CUA Worker (Standalone Test)

Bu sadece lokal test veya tek makine denemesi icindir. Dagitik sisteme worker olarak baglanmaz.

- Template Name: `Linux Desktop Container (CUA Standalone)`
- Template Description: `GPU standalone CUA + vLLM test node`
- Image Path:Tag: `vastai/linux-desktop:cuda-12.9-ubuntu24.04-2026-02-05`
- Version Tag: `cuda-12.9-ubuntu24.04-2026-02-05`
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
curl -fsSL -o vast_cua_standalone.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_standalone.sh
chmod +x vast_cua_standalone.sh
REPO_URL='https://github.com/TopcuAbdulbaki/Bitirme.git' ./vast_cua_standalone.sh
```

## Notlar

- Worker template'lerinde `50051`, `5672`, `15672`, `5432`, `9000`, `9001` gibi portlari Vast tarafinda acmak zorunda degilsin; bridge kullaniyorsan bunlar yerel makinede kalir.
- Crawler, VLM ve LLM node'lari browser UI sunmaz; bu yuzden portal tarafinda ek HTTP button tanimlamadim.
- CUA distributed template'inde `1234` acik birakildi cunku script node modunda da yerel vLLM aciyor.
- Worker komutlarinin guncel hali [scripts/all.md](/C:/Users/HP/Desktop/Projeler/Bitirme/scripts/all.md) icinde de bulunur.
