# Scripts Handoff Documentation

Bu doküman, `scripts/` dizini altındaki yardımcı betiklerin (PowerShell scripts) amaçlarını, kullanım şekillerini ve çalışma mantığını detaylandırmak amacıyla oluşturulmuştur. Bu betikler, projenin **Vast.ai** gibi uzak sunucular üzerinde yayına alınması (deployment) ve güncellenmesi süreçlerini otomatize etmek/kolaylaştırmak için tasarlanmıştır.

## 🛠️ Dizin Yapısı ve Dosya Listesi

| Dosya Adı             | Açıklama                                                                 |
| :-------------------- | :----------------------------------------------------------------------- |
| `.env`                | Yerel geliştirme ve scriptler için saklanan hassas değişkenler (Token vb.) |
| `.env.example`        | `.env` dosyası için şablon.                                              |
| `0_build_all.ps1`     | Tüm servisleri derleyip Docker Hub'a push etmek için hazırlanan toplu script. |
| `0_update_all.ps1`    | Mevcut tüm makineleri güncellemek için referans komut listesi.            |
| `1_orchestrator.ps1`  | Orchestrator servisinin kurulum ve güncelleme komutlarını üretir.         |
| `2_crawler.ps1`       | Crawler servisinin kurulum ve güncelleme komutlarını üretir.              |
| `3_db.ps1`            | Database, MinIO ve DB servisinin kurulum komutlarını üretir.             |
| `4_vlm.ps1`           | VLM (Visual Language Model) servisinin kurulum ve güncelleme komutlarını üretir. |
| `5_llm.ps1`           | LLM (Large Language Model) servisinin kurulum ve güncelleme komutlarını üretir. |
| `6_cua.ps1`           | CUA (Computer Using Agent) — browser-use + vLLM GPU node kurulumu ve uzak deploy. |

---

## 🚀 Önemli Betikler ve Fonksiyonları

### 1. `0_build_all.ps1` (Toplu Derleme)
Bu betik, yereldeki kodları GitHub'a push eder ve ardından uzak bir "Build Machine" (hızlı upload kapasiteli) üzerinde tüm Docker imajlarını derlemek için gereken komutları ekrana yazdırır.
- **Ne Yapar?**
  - Git commit ve push işlemlerini otomatikleştirir.
  - Docker Hub login ve `docker build` komutlarını hazırlar.
- **Key Point:** Imajların merkezi bir noktadan derlenip Docker Hub'a (`abdulbakitopcu/`) gönderilmesini sağlar.

### 2. `0_update_all.ps1` (Hızlı Referans)
Tüm servislerin `docker run` komutlarını ve gerekli ortam değişkenlerini (Environment Variables) tek bir yerde toplar.
- **Ne Yapar?** servislerin hangi IP ve Port ile çalışacağını, ağ yapılandırmalarını (db-net vb.) gösterir.
- **Önemli:** Hangi servisin hangi opsiyonlarla çalıştığını görmek için ana döküman niteliğindedir.

### 3. Servis Bazlı Scriptler (1–6)
Her bir servis (`orchestrator`, `crawler`, `db`, `vlm`, `llm`, `cua`) için özelleşmiş kurulum betikleridir.
- **Ortak Özellikler:**
  - `.env` dosyasından veya parametrelerden (`-OrchHost`, `-GrpcPort`) veri alırlar.
  - Uzak sunucuya (Vast.ai) yapıştırılacak **Bash** kod bloklarını üretirler.
  - Sistem güncellemeleri, Docker kurulumu, `nvidia-container-toolkit` (GPU servisleri için) gibi hazırlıkları içerirler.

---

## 🔑 Önemli Komutlar ve Kullanım

Betikler genellikle şu şekilde çalıştırılır (PowerShell üzerinde):

```powershell
# Orchestrator için kurulum kodu üretme
.\1_orchestrator.ps1 -GrpcPort "50051" -RabbitPort "5672"

# Crawler için (Orchestrator IP'si belirterek)
.\2_crawler.ps1 -OrchHost "142.170.xx.xx" -OrchPort "50051"

# GPU Servisleri (VLM / LLM)
.\4_vlm.ps1 -OrchHost "142.170.xx.xx" -ModelMode "transformers"

# CUA Node — Yerel
.\6_cua.ps1

# CUA Node — Vast.ai SSH ile uzak deploy
.\6_cua.ps1 -RemoteHost "192.168.x.x" -RemoteUser root -RemotePort 22 -UseSSH $true
```

---

## 💡 Kritik Bilgiler (Key Points)

1.  **Vast.ai Odaklılık:** Scriptlerin çoğu, uzak bir Linux sunucusuna (Vast.ai instance) SSH ile bağlandıktan sonra kopyala-yapıştır yapılabilecek komutlar üretmek üzere tasarlanmıştır.
2.  **GPU Desteği:** `4_vlm.ps1` ve `5_llm.ps1` dosyaları, NVIDIA sürücüleri ve Docker GPU runtime (`nvidia-ctk`) kurulumlarını otomatik olarak içerir.
3.  **Hassas Veriler:** `.env` dosyası içerisindeki `GH_TOKEN` ve `DOCKER_TOKEN` gibi değişkenler, scriptlerin içine gömülmek yerine buradan dinamik olarak çekilir. Bu dosyayı asla Git'e push etmeyin!
4.  **Network Yapısı:**
    - `3_db.ps1`, servisler arası iletişim için `db-net` adında bir Docker network'ü oluşturur.
    - `postgres` ve `minio` container'ları bu network üzerinde izole çalışır.
5.  **Otomasyon Mantığı:** Betikler önce `git pull` yapar, sonra imajı derler (`docker build`) ve en son konteyneri yeniden başlatır (`docker rm -f` -> `docker run`).

---

## ⚠️ Dikkat Edilmesi Gerekenler

- **Token Güncelliği:** `GH_TOKEN` (GitHub Personal Access Token) süresi dolduğunda `.env` üzerinden güncellenmelidir.
- **IP Adresleri:** Vast.ai üzerinde makineler her kiralandığında IP adresleri değişir. Bu yüzden `-OrchHost` parametresi her seferinde yeni Orchestrator IP'sine göre güncellenmelidir.
- **Port Yönlendirme:** Docker'daki `-p` port eşleştirmelerinin, Vast.ai'nin sağladığı dış portlarla uyumlu olduğundan emin olunmalıdır.
- **CUA özel:** `6_cua.ps1` içindeki `LMSTUDIO_URL` değeri, Vast.ai vLLM endpoint'ine (`http://localhost:8000/v1`) göre ayarlanmalıdır. `SEARCH_ENGINE` varsayılanı `duckduckgo`'dur.

---

## 🤖 `6_cua.ps1` — CUA Deployment Script

**Amaç:** CUA node'unu Vast.ai GPU instance’ına (veya yerel Docker ortamına) deploy eder.

**Parametreler:**

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `-RemoteHost` | `localhost` | Hedef sunucu IP'si |
| `-RemoteUser` | `root` | SSH kullanıcısı |
| `-RemotePort` | `22` | SSH portu |
| `-UseSSH` | `$false` | `$true` → uzak deploy, `$false` → yerel |
| `-WireGuardIP` | `10.0.0.6` | WireGuard VPN IP (opsiyonel) |

**Dahili Değişkenler** (script içinde güncellenebilir):
```powershell
$ORCHESTRATOR_HOST = "orchestrator"   # Docker network servis adı
$ORCHESTRATOR_PORT = 50051
$CUA_GRPC_PORT    = 50054
$RABBITMQ_HOST    = "rabbitmq"
$MODEL_MODE       = "local"           # "local" = vLLM, "production" = transformers
# LMSTUDIO_URL    = "http://lmstudio:1234/v1"  ← Vast.ai için 8000 olarak güncelle
```

**Ne Yapar?**
1. `cua/Dockerfile` kullanarak `abdulbakitopcu/cua:latest` imajını derler
2. `--gpus all` ile GPU'ya bağlı başlatır, port `50054` dışa açılır
3. `UseSSH=$true` ise uzak sunucuya SSH üzerinden `docker run` komutunu gönderir

> **⚠️ Not:** `LMSTUDIO_URL` script’teki `http://lmstudio:1234/v1` değerini Vast.ai vLLM için
> `http://localhost:8000/v1` olarak güncellemeden önce çalıştırmayın!
