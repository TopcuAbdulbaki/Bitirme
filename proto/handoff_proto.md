# Proto Modülü Handoff Belgesi

Bu belge, projenin tüm mikro servisleri arasındaki iletişimi sağlayan gRPC/Protobuf tanımlamalarını ve yönetim süreçlerini detaylandırmaktadır. `proto` klasörü, sistemin "Source of Truth" (Doğruluğun Kaynağı) noktasıdır.

## 📂 Dizin Yapısı

- `orchestrator.proto`: Tüm servislerin ve mesajların tanımlandığı ana Protobuf dosyası.
- `orchestrator_pb2.py`: `orchestrator.proto` dosyasından derlenen Python mesaj sınıfları.
- `orchestrator_pb2_grpc.py`: `orchestrator.proto` dosyasından derlenen gRPC servis sınıfları.

## 🛠 Ana Bileşenler ve Mesajlar

`orchestrator.proto` dosyası aşağıdaki temel bloklara ayrılmıştır:

### 1. Ortak Mesajlar (Common)
- **`RegisterRequest/Response`**: Yeni bir düğüm (node) sisteme dahil olduğunda (Crawler, VLM, LLM, DB) kendini merkezi Orchestrator'a kaydeder.
- **`HeartbeatRequest/Response`**: Düğümlerin hayatta olup olmadığını ve mevcut durumlarını (`IDLE`, `BUSY`, `ERROR`) raporladığı periyodik mesaj.
- **`NodeStatus` & `TaskStatus`**: Sistem genelinde kullanılan durum enumları.

### 2. Modül Bazlı Mesajlar
- **Crawler**: `CrawlTaskRequest` (URL listesi) ve `GetCrawlTaskRequest` (Crawler'ın görev beklediği poll modeli).
- **Database**: `StoreDataRequest` (JSON verisi saklama) ve `GetQueueRequest` (İşlenmemiş verileri çekme).
- **VLM**: `AnalyzeImagesRequest` (Görsel analizi için JSON context).
- **LLM**: `AnalyzeTextRequest` (VLM sonuçlarını da içeren metin analiz talebi).

### 3. Servis Tanımları
- **`OrchestratorService`**: Merkezi sunucunun sunduğu hizmetler (Register, Heartbeat, Raporlama). Tüm modüller sonuçlarını bu servise rapor eder.
- **İşçi Servisleri (`CrawlerService`, `DatabaseService`, etc.)**: Orchestrator'ın modülleri doğrudan tetikleyebilmesi için her modülün kendi içinde çalıştırdığı servis tanımlarıdır.

## 🚀 Önemli Komutlar

### Tüm Servisler İçin Derleme
Proje kök dizininde bulunan `compile_proto.py` betiği, proto dosyasını tüm alt modüllere (crawler, llm, vlm, db, orchestrator) kopyalar ve derler.

```bash
python compile_proto.py
```

### Manuel Derleme (Tekil)
Eğer manuel bir derleme gerekirse (Örn: `proto` klasörü içinde):
```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. orchestrator.proto
```

## 🔑 Önemli Noktalar (Key Points)

1.  **Merkezi Güncelleme**: `orchestrator.proto` dosyasında bir değişiklik yapıldığında, `compile_proto.py` mutlaka çalıştırılmalıdır. Aksi halde modüller arasında "Serialization" veya "Method Not Found" hataları oluşur.
2.  **Import Düzeltmesi (Fixing Imports)**: gRPC araçları varsayılan olarak `import orchestrator_pb2` şeklinde çıktı üretir. Ancak modüler yapıda bu durumun `from . import orchestrator_pb2` şeklinde güncellenmesi gerekir. `compile_proto.py` bu düzeltmeyi otomatik olarak yapmaktadır.
3.  **JSON Esnekliği**: Proto dosyası içinde kompleks veri yapıları için genellikle `string json_data` alanları kullanılmıştır. Bu, şemayı her küçük veri değişikliğinde güncelleme gerekliliğini ortadan kaldırır ancak JSON içeriğinin iki taraflı doğruluğunu gerektirir.
4.  **Poll & Push Hibrit Yapı**: Sistem, Crawler için bir "Poll" (Crawler'ın iş istemesi) modelini, diğer işçiler için ise doğrudan RPC çağrısı ("Push") modelini destekleyecek şekilde tasarlanmıştır.

## ⚠️ Dikkat Edilmesi Gerekenler
- Yeni bir düğüm tipi (Node Type) eklendiğinde `orchestrator.proto` dosyasındaki `RegisterRequest` içindeki yorum satırı ve ilgili servis tanımları güncellenmelidir.
- Veritabanı (Db) klasör ismi sistemde bazen büyük/küçük harf hassasiyetine (`db` vs `Db`) takılabilir; `compile_proto.py` bunu `if node_name != 'db' else 'Db'` mantığı ile yönetmektedir.
