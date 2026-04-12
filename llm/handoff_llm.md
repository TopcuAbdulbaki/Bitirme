# LLM Node - Proje Handoff Dokümanı

## 1. Genel Bakış
LLM Node, sistemin metin analizi, özetleme ve duygu (sentiment) sınıflandırması yapan zekâ merkezidir. Haber içeriklerini ve VLM (Vision Language Model) tarafından üretilen görüntü analiz sonuçlarını birleştirerek kapsamlı bir metin analizi raporu sunar.

## 2. Dizin Yapısı ve Dosya Görevleri

| Dosya/Dizin | Görev |
| :--- | :--- |
| `main.py` | Uygulamanın giriş noktası. RabbitMQ kuyruklarını dinler, görevleri işler ve sonuçları yayınlar. |
| `config.py` | Çevre değişkenleri (RabbitMQ, gRPC, Model ayarları) ve yapılandırmalar. |
| `services/` | İş mantığının (logic) bulunduğu ana servisler. |
| `services/model_handler.py` | LLM model yükleme ve çıkarım (inference) mantığı. (LM Studio ve Transformers desteği). |
| `services/grpc_client.py` | Orchestrator ile iletişim kuran gRPC istemcisi (heartbeat ve kayıt). |
| `services/rabbitmq_consumer.py` | RabbitMQ üzerinden mesaj alıp göndermeyi sağlayan yardımcı sınıf. |
| `proto/` | gRPC için tanımlanmış `.proto` dosyaları. |
| `generated/` | `.proto` dosyalarından otomatik üretilen Python kodları. |
| `Dockerfile` | GPU destekli (NVIDIA/CUDA) konteynerizasyon yapılandırması. |
| `requirements.txt` | Gerekli Python kütüphaneleri (`transformers`, `torch`, `grpcio`, `pika` vb.). |

## 3. Çalışma Mantığı (Workflow)

1.  **Başlatma**: `main.py` çalıştığında Orchestrator'a (`GRPCClient`) kayıt olur ve ID alır.
2.  **Görev Tüketimi**: `llm_tasks` RabbitMQ kuyruğundan görevleri (`task_id`, `json_data`) çeker.
3.  **Veri Hazırlama**: Haber başlığı, içeriği ve varsa VLM'den gelen görüntü analiz sonuçları birleştirilir.
4.  **LLM Analizi**:
    *   **Local Mode**: LM Studio API'sini (`http://localhost:1234`) kullanır. Prototipleme için idealdir.
    *   **Production Mode**: HuggingFace üzerindeki modelleri (`transformers` kütüphanesi ile) doğrudan GPU'ya yükler.
5.  **Sonuç Yayını**: Üretilen analiz (JSON formatında) `llm_results` kuyruğuna basılır ve durum Orchestrator'a bildirilir.

## 4. Önemli Key Pointler (Kritik Noktalar)

### JSON Çıktı Formatı
LLM her zaman aşağıdaki yapıda bir JSON üretmeye zorlanır:
```json
{
    "summary": "Makalenin 2-3 cümlelik özeti",
    "sentiment": -1,  // -1: Negatif, 0: Nötr, 1: Pozitif
    "sentiment_label": "negative",
    "keywords": ["anahtar", "kelimeler"],
    "entities": {
        "countries": ["Türkiye"],
        "organizations": ["NATO"],
        "people": ["Başkan"]
    },
    "category": "politics",
    "relevance_to_topic": "high"
}
```

### Prompt Mühendisliği
`services/model_handler.py` içinde tanımlanan `LLM_SYSTEM_PROMPT`, modelin halüsinasyon görmesini engellemek ve sadece geçerli JSON döndürmesini sağlamak için tasarlanmıştır.

### VLM Entegrasyonu
LLM sadece metne bakmaz; eğer veri setinde görseller varsa, VLM'den gelen nesne tanımları ve sahne yorumları da prompt'a dahil edilerek çok modlu bir analiz yapılır.

### Hata Yönetimi
Eğer LLM geçersiz bir JSON döndürürse veya model çökerse, sistem `None` veya boş string yerine varsayılan bir "Neutral" sonucunu hata mesajıyla birlikte döndürerek boru hattının (pipeline) kırılmasını önler.

## 5. Önemli Komutlar

### Yerel Çalıştırma
```bash
# Model modunu ayarlayın (env dosyasında veya shell'de)
set MODEL_MODE=local
python -m llm.main
```

### Docker ile Çalıştırma
```bash
docker build -t llm-node -f llm/Dockerfile .
docker run --gpus all llm-node
```

### Proto Derleme
```bash
python -m grpc_tools.protoc -Iproto --python_out=llm/generated --grpc_python_out=llm/generated orchestrator.proto
```

## 6. Geliştirme Notları
- **Bellek Yönetimi**: Transformers modunda model (~8B parametre) yaklaşık 16GB VRAM gerektirir. Düşük sistemlerde LM Studio üzerinden `quantized` modeller kullanılması tavsiye edilir.
- **Async Yapı**: Mesaj çekme ve gRPC heartbeat işlemleri `asyncio` ile yönetilmektedir, bu sayede model çıkarımı sırasında ağ bağlantıları kopmaz.
