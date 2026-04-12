# 🕸️ Crawler Handoff Documentation

Bu belge, **Crawler (Örümcek)** modülünün işlevlerini, yapısını ve operasyonel detaylarını hızlıca anlamak ve devretmek için oluşturulmuştur.

---

## 🏗️ Modül Mimarisi ve Dizin Yapısı

Crawler, Google Haberler araması üzerinden belirlenen kaynaklardan (BBC, CNN, Al Jazeera, vb.) veri toplayan, içerik ve medya analizi yapan bağımsız bir node'dur.

| Dosya / Dizin | Görevi |
| :--- | :--- |
| `main.py` | Ana giriş noktası. Link toplama, içerik çıkarma, medya filtreleme ve asenkron işleyişi yönetir. |
| `config.py` | gRPC bağlantı ayarları, çalışma modu (Standalone/Distributed) ve demo limiti konfigürasyonları. |
| `services/grpc_client.py` | Orchestrator ile iletişimi sağlar. Register, Heartbeat ve Task Poll işlemlerini yürütür. |
| `proto/` | gRPC iletişim sözleşmesini (protobuf) barındırır. |
| `generated/` | gRPC proto dosyalarından üretilen Python kodlarını içerir. |
| `toplanan_haberler.json` | Standalone modda veya son yedekleme amacıyla tutulan yerel veri dosyası. |
| `Dockerfile` | Playwright ve Chromium bağımlılıklarıyla modülü paketleyen Docker konfigürasyonu. |

---

## 🚀 Önemli Özellikler (Key Points)

1.  **Crawl4AI Entegrasyonu**: Gelişmiş içerik çıkarma için `AsyncWebCrawler` kullanır.
2.  **Anti-Bot Stratejileri**: 
    - `magic=True`: İnsan davranışlarını simüle eder.
    - `user_agent_mode="random"`: İzlenmeyi zorlaştırır.
    - `bypass` cache mode ve rastgele jitter (bekleme) süreleri.
3.  **Haber Kaynakları & Filtreleme**:
    - Google üzerinden `site:domain.com (Turkey OR Türkiye)` sorgusuyla link avlar.
    - Belirli keywordler (`turkey`, `türkiye`, `ankara`, `istanbul`) üzerinden içerik doğrulaması yapar.
4.  **Zengin Medya Çıkarımı**:
    - Article hero image ve içerik görsellerini toplar.
    - Çok küçük resimleri (ikon/logo) alan (width x height) bazlı analizle eler.
    - Video kaynaklarını tespit eder.
5.  **Poll Model (Dağıtık Mimari)**:
    - Crawler artık bir sunucu *değildir*. Orchestrator'a bağlanır ve "iş var mı?" diye sorar (Polling). Bu sayede NAT/Firewall arkasında sorunsuz çalışır.

---

## 🛠️ Komutlar ve Çalıştırma

### 1. Yerel Çalıştırma (Standalone)
Modülü tek başına test etmek için:
```powershell
# Bağımlılıkları kurun
pip install -r .\crawler\requirements.txt
playwright install chromium

# Çalıştırın
$env:CRAWLER_MODE="standalone"
python -m crawler.main
```

### 2. Dağıtık Mod (Distributed)
Orchestrator'a bağlanmak için:
```powershell
$env:CRAWLER_MODE="distributed"
$env:ORCHESTRATOR_HOST="localhost"
$env:ORCHESTRATOR_PORT="50051"
python -m crawler.main
```

### 3. Docker ile Yayına Alma
```bash
docker build -t bitirme-crawler -f crawler/Dockerfile .
docker run -e ORCHESTRATOR_HOST=orchestrator bitirme-crawler
```

---

## ⚠️ Dikkat Edilmesi Gerekenler

-   **Donanım Gereksinimi**: Playwright/Chromium çalıştığı için Docker üzerinde en az 2 CPU ve 4GB RAM önerilir.
-   **Google Blokajı**: Çok sık deneme yapılırsa Google araması CAPTCHA'ya düşebilir. `POLL_INTERVAL` ve jitter süreleri bu yüzden kritiktir.
-   **Kod Gevşekliği**: `main.py` içindeki `wait_for="css:body"` ayarı, çok katı sayfa yükleme beklemelerinden kaçınarak hızı artırır.
