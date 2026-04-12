# DB Node Handoff Documentation

Bu dosya, projenin veritabanı ve depolama katmanını yöneten `db` klasöründeki dosyaların, dizin yapısının ve işleyiş mantığının detaylı analizini içerir.

## 📌 Genel Bakış
DB Node, sistemin kalıcı veri deposudur. PostgreSQL (metasal veri), pgvector (vektör arama) ve MinIO (medya dosyaları) kullanarak tüm haber akışını ve analiz sonuçlarını saklamaktan sorumludur. Distributed (dağıtık) yapıda çalışacak şekilde tasarlanmıştır.

---

## 📂 Dizin Yapısı ve Dosya Analizi

### 📁 Root Dosyaları
- **`main.py`**: DB Node'un ana giriş noktasıdır. 
  - Tüm servisleri (Postgres, MinIO, RabbitMQ, gRPC) başlatır.
  - Orchestrator'a kayıt (register) olur ve heartbeat gönderir.
  - RabbitMQ üzerindeki `db_tasks` kuyruğunu dinleyerek gelen analiz sonuçlarını (VLM/LLM) veritabanına işler.
- **`config.py`**: Ortam değişkenlerini (`.env`) okuyarak tüm bağlantı ayarlarını yapılandırır. Dağıtık mimari için default değerler yerine environment variable önceliklidir.
- **`Dockerfile`**: Node'un Docker üzerinde izole bir şekilde çalışmasını sağlar.
- **`requirements.txt`**: Gerekli kütüphaneler (asyncpg, minio, pika, grpcio, sentence-transformers vb.).

### 📁 `services/` (Mantıksal Katman)
Bu klasör, farklı veri depoları ile iletişimi yöneten sınıfları içerir:

1. **`postgres_manager.py` (Kritik Core)**
   - **Kütüphane**: `asyncpg` (Async PostgreSQL)
   - **Veri Modeli**: `NewsItem` dataclass.
   - **Önemli İşlemler**:
     - `generate_news_id`: URL'in SHA-256 hash'inin ilk 16 karakterini alır (Unique ID).
     - `_init_tables`: `news`, `vlm_analysis`, `llm_analysis` tablolarını oluşturur.
     - **pgvector Entegrasyonu**: Haber içeriklerini 1024 boyutlu vektörler olarak saklar.
     - `search_similar`: Semantik arama (similarity search) yeteneği sağlar.
   - **Mekanizma**: `insert_news` sırasında otomatik olarak embedding üretir.

2. **`minio_manager.py` (Medya Yönetimi)**
   - **Kütüphane**: `minio` & `aiohttp`
   - **Mantık**: Haberlerle ilişkili görselleri indirir ve MinIO bucket'ında (`news-media`) haber ID'sine göre klasörler (`{news_id}/main.jpg`).
   - **Özellik**: `process_news_images` ile hem kapak fotoğrafını hem de içerik fotoğraflarını asenkron indirip yükler.

3. **`embedding_manager.py` (Vektörizasyon)**
   - **Model**: `Qwen/Qwen3-Embedding-0.6B` (Local) veya API modu.
   - **Fonksiyon**: Metinleri sayısal vektörlere dönüştürür. 
   - **Key Point**: OOM (Out of Memory) hatalarını önlemek için metinleri 8000 karakterle sınırlar.

4. **`grpc_client.py` & `rabbitmq_consumer.py`**
   - **gRPC**: Orchestrator ile iletişim (Kayıt, Durum Raporlama).
   - **RabbitMQ**: Dağıtık görevleri almak için kullanılır. `basic_get` (non-blocking) ile asenkron döngüye uyum sağlar.

### 📁 `proto/` & `generated/`
- **`orchestrator.proto`**: Node'lar arası iletişim protokol tanımları.
- **`generated/`**: Python gRPC sınıfları (protoc tarafından üretilmiştir).

---

## ⚙️ Önemli İşleyiş Akışları (Key Processes)

### 1. Yeni Haber Kayıt Akışı
1. Crawl verisi DB node'a gelir.
2. `postgres_manager` URL'i kontrol eder (Duplicate check).
3. `minio_manager` görselleri indirip S3 bucket'ına yükler, yollarını (minio://...) döner.
4. `embedding_manager` haber metni için vektör oluşturur.
5. Veri `news` tablosuna `news_id` ile kaydedilir.

### 2. Analiz Verisi İşleme
1. Orchestrator, VLM veya LLM analizini tamamladığında RabbitMQ'ya bir mesaj atar.
2. `rabbitmq_consumer` bu mesajı yakalar.
3. `main.py` -> `_process_analysis_task` ile sonuçlar `vlm_analysis` veya `llm_analysis` tablolarına, ana habere referans verilerek kaydedilir.

---

## 🚀 Önemli Key Pointler & Komutlar

### Komutlar (Terminal)
- **Node'u Başlatmak**: `python -m db.main`
- **Vektör Eklentisini Açmak (Manuel gerekirse)**: `CREATE EXTENSION vector;` (Postgres içinde)

### Dikkat Edilmesi Gerekenler
- **Distributed Mode**: `ORCHESTRATOR_HOST` ve `POSTGRES_HOST` gibi değişkenler `.env` dosyasında mutlaka tanımlanmalıdır.
- **Vektör Boyutu**: Qwen3 modeli 1024 boyutlu vektör döner. DB tablosu (`vector(1024)`) buna göre yapılandırılmıştır. Başka model kullanılırsa tablo şeması güncellenmelidir.
- **Duplicate Logic**: Sistem aynı URL'e sahip haberi ikinci kez kaydetmez, mevcudu döner. Bu sayede gereksiz analiz maliyetinden kaçınılır.

---

## 📊 Tablo Şemaları Sırları
- **`news`**: `vlm_processed` ve `llm_processed` flagları ile analizin hangi aşamada olduğu takip edilir.
- **`idx_news_url`**: Haber aramalarını hızlandırmak için URL üzerinde benzersiz index bulunur.
- **`1 - (content_embedding <=> $1::vector)`**: Kosinüs benzerliği ile en yakın haberleri bulma mantığı.

---
> [!TIP]
> Yeni bir analiz tipi eklenirse önce `postgres_manager._init_tables` içine yeni bir tablo eklenmeli ve `main.py` içindeki `_process_analysis_task` metodunda bu veriyi işleyecek logic kurulmalıdır.
