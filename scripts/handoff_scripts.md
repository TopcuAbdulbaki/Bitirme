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

### 3. Servis Bazlı Scriptler (1-5)
Her bir servis (`orchestrator`, `crawler`, `db`, `vlm`, `llm`) için özelleşmiş kurulum betikleridir.
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
