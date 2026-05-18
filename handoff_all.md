# Bitirme Projesi - Sistem Mimarisi ve Tam Handoff Rehberi (Master Document)

Bu doküman, projeyi devralan yapay zeka ajanları (AI Agents) ve geliştiriciler için projenin **tek gerçeklik kaynağı (Single Source of Truth)** olması amacıyla oluşturulmuştur. Özel sistemlerin görevleri, iletişim mimarisi, veritabanı şemaları, olası hata senaryoları ve devops kurulum süreçleri gibi projeye dair tüm mimari bilgi detaylıca işlenmiştir. 

> [!NOTE]
> Bu doküman tek bir ana merkez olmakla beraber, her modülün kendi altında spesifik detaylarına yer verilen ek `handoff` veya `docs/` belgeleri bulunmaktadır. İlgili bölümlerin altında "📚 **Daha Fazla Detay İçin Okuyunuz:**" referansları ile özel belgelere yönlendirmeler yapılmıştır.

---

## 1. 🏗️ Sistem Mimarisi ve Topoloji (Star Topology)

Sistem yapay zeka ajanlarına bağımsız işlemler vererek ölçeklenebilir bir dağıtık haber toplama ve analiz ağı (Pipeline) yaratacak şekilde **Yıldız Topolojisi (Star Topology)** olarak tasarlanmıştır.

*   **Merkez (Central Hub):** `Orchestrator`
*   **Uydu İşçiler (Satellite Nodes):** `Crawler`, `DB`, `VLM`, `LLM`

Düğümler arası doğrudan bir iletişim ASLA söz konusu değildir. Her bir node, kimliğini oluşturduktan sonra gRPC üzerinden sadece Orchestrator ile kayıt (`Register`) olur ve Heartbeat sinyallerini merkeze yollar. Görevler ve mesaj trafiği de RabbitMQ üzerinden sadece Orchestrator vasıtasıyla dağıtılır.

### Akış Senaryosu (Life Cycle)
1.  **Crawl (Toplama):** Crawler, internetten URL ve raw verileri alır ➔ Orchestrator'a iletir.
2.  **Storage ID (Ön Kayıt):** Orchestrator, verileri ID & Media Path atanması için DB'ye (gRPC) iletir ➔ DB bunu cevaplar.
3.  **VLM (Görüntü İşleme):** Orchestrator, resim yolları atanmış bu işi `vlm_tasks` RabbitMQ kuyruğuna koyar. VLM alır, işler ➔ `vlm_results` kuyruğundan geri atar.
4.  **LLM (Metin Okuma):** Orchestrator VLM çıktısını haber ile birleştirir, `llm_tasks` RabbitMQ kuyruğuna koyar. LLM alır ➔ `llm_results` kuyruğundan geri atar.
5.  **Final DB (Kalıcı Kayıt):** Orchestrator tüm tamamlamaları nihai olarak DB'ye (gRPC) aktararak analizi bitirir.

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `handoff_files.md` (Topoloji Özeti)
- `docs/node_id_strategy.md` (Kimlik Üretim Mekanizması `node_type_uuid`)

---

## 2. 🛜 İletişim Protokolleri (gRPC & RabbitMQ)

Projeyi ölçeklenebilir ve sağlam kılmak adına hibrit bir network katmanı kullanılmaktadır:

### 2.1 gRPC (Senkron İletişim & Kontrol)
- **Rol:** Node Kaydı (Register), Heartbeat, Crawler'a Görev Atama (Poll Model: `GetCrawlTask`), Veritabanına Yazım İşlemleri (`StoreDataRequest`).
- **Sözleşme (Contract):** `proto/orchestrator.proto` üzerinden tüm mimari tanımlanmıştır. `RegisterRequest/Response` ile eşleşmeler yapılır. Veri modellerinin her yeni özelliği için proto bozulmasın diye esneklik adına sıklıkla `json_data` (string) tipinde iletişim kurulur.
- **Limitasyonlar:** gRPC Maximum Message Size kasten **100MB** olarak ayarlanmıştır ki ağır medyalar Payload limitine takılmasın.

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `proto/handoff_proto.md`
- `docs/grpc_guide.md` (Örnek Python Client/Server kodları)

### 2.2 RabbitMQ (Asenkron İş Dağıtımı & Yük Yönetimi)
- **Rol:** VLM ve LLM gibi derin öğrenme (GPU) işlemleri ağır olduğundan anlık (RPC) cevaplar yerine kuyruklama mekanizmaları (`pika` kütüphanesi ile) kullanılır. 
- **Kuyruklar (Queues):**
  - Gidenler: `vlm_tasks` ve `llm_tasks` 
  - Dönenler: `vlm_results` ve `llm_results` (Bu dönüşleri yine Orchestrator dinler).

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `docs/rabbitmq_architecture.md`

---

## 3. 📂 Modüllerin (Düğümlerin) Teknik İncelemeleri

Sistem 5 ana servisten oluşur. Bütün servislerin kendi Dockerfile, requirements.txt, config.py dosyaları izole edilmiştir.

### 3.1 🧠 Orchestrator (`/orchestrator`)
- **Görevi:** Ağın beyni. PipelineManager sayesinde yukarıda bahsedilen döngüyü işletir ve görev eyaletlerini yönetir.
- **Detay:** `NodeRegistry` thread-safe mantığında çalışan singleton ile çalışır (`node_registry.py`). Heartbeat'ları sürekli dinler, bir uçtan 30s içinde Heartbeat gelmezse node `OFFLINE` moduna çekilip görev iptal / re-queue yapılır.

📚 **Daha Fazla Detay İçin Okuyunuz:** `orchestrator/handoff_orchestrator.md`

### 3.2 🕷️ Crawler (`/crawler`)
- **Görevi:** Haber kaynaklarında gezip içerik (`Crawl4AI`) toplar. 
- **Detay:** Push model yerine **Poll** mantığıyla çalışır. Orchestrator'dan "Bana iş ver" diyerek kendi asenkron döngüsünde görev arar. `magic=True`, Cache bypass ve Proxy destekleri ile Google Bot Algoritmalarını alt etmeyi hedefler.
- **Kritik:** Tüm medya dosyalarını (Resim vd.) indirip kendi üzerinde tutmaz. Sadece o görsellerin URL'lerini bulur. Dosyayı asıl indirecek kişi DB'dir.

📚 **Daha Fazla Detay İçin Okuyunuz:** `crawler/handoff_crawler.md`

### 3.3 💾 DB (Database & Vector Storage) (`/db`)
- **Görevi:** Metin ve resim medyalarını muhafaza etmek ve semantik yeteneklerle veriyi işlemek. İş akışlarını dinlemek için RabbitMQ'ya değil doğrudan Orchestrator RPC'sine bağlıdır.
- **PostgreSQL (pgvector):** `news`, `vlm_analysis`, `llm_analysis` ana tablolarıdır. Yeni veriler girerken (URL `shasum256` alınır), Qwen3-Embedding-0.6B ile haber içerikleri `vector(1024)` veritabanına dönüştürülebilir. Böylelikle Semantik Arama yapılabilir. Haber limitleri 50KB olarak korunur.
- **MinIO (Image Storage):** Haber URL imajları Crawler'dan DB'ye gelince asenkron çekilen `aiohttp` yardımıyla DB'de indirilir, MinIO sunucusundaki `news-media` bucket'larına kalıcı atılır (Örn. ID `a3...c9` için `minio://news-media/a3f2b8c9/main.jpg` veya `content_0.jpg`).

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `db/handoff_db.md` (DB Node Sorumlulukları)
- `docs/database_schema.md` (PostgreSQL ve Vektör Tabloları Schema Özeti)
- `docs/minio_storage.md` (S3 Folder Configuration)

### 3.4 👁️ VLM (Vision Language Modeli) (`/vlm`)
- **Görevi:** Görsellerin yapay zekaya okutulup sahne betimlemesi ve obje analizi çıkarımı.
- **Detay:** Prod. modda Transformer (`Qwen3-VL-8B-Instruct`) üzerinden **8-bit quantization** kullanır (Bunu `bitsandbytes` desteğiyle sağlar). Olası OOM (Memory yetersizliği) veya bozuk resim süreçlerinde pipeline'ı düşürmemek adına bitirebildiği kadarıyla Orchestrator'a **Partial Result** yollar. Sistem sadece bu analiz sonuçlarını geçerli sayar.

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `vlm/handoff_vlm.md`
- `docs/system_prompts.md` (VLM JSON Çıktı Promptu)

### 3.5 🤖 LLM (Large Language Modeli) (`/llm`)
- **Görevi:** Toplanan metni (Tüm body/context) ve VLM'in görsel notlarını harmanlayıp haberdeki final hissiyatına (Sentiment: `-1` Negatif, `0` Nötr, `+1` Pozitif), anahtar kelimelere (`keywords`) ve ülke/kişi bazlı varlıklara (`entities`) erişim sağlar.
- **Detay:** 8B modeller VRAM kullanım limitleriyle sınırlı olabilir. Veri json döngüsünü bozmamak adına strict system prompt ile koşturulur, Local-Deployment evresi için `lmstudio` desteği barındırır.
- **Payload Strictness:** Kategorizasyonu `politics`, `economy`, `sports`, `technology`, `other` gibi kesin kavramlarla limitlemeye çalıştırılır.

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `llm/handoff_llm.md`
- `docs/system_prompts.md` (LLM JSON Çıktı Promptu)

### 3.6 🤖 CUA (Computer Using Agent) (`/cua`)
- **Görevi:** Stokastik (olasılıksal) bir "Avcı" ajanı. Statik Crawler'ın kaçırdığı haberleri bulmak ve derin araştırmalar yapmak.
- **Detay:** Dual-mode çalışır — (1) Yüzeysel Tarama (Surface Search) hızlı haber bulma, (2) Derin İstihbarat Araştırması (Deep Research) çok kaynaklı sentez. LangGraph + Browser-Use ile tarayıcı gibi gezinir, Google/DuckDuckGo arar, sayfaları parse eder.
- **Kritik:** Crawler ile paralel fan-out çalışır (`agent_tasks` RabbitMQ kuyruğu). Verileri mevcut pipeline'a (VLM→LLM→DB) uyumlu JSON formatında aktarır. Mod 2'de araştırma raporlarını `research_missions` tablosuna yazar.

📚 **Daha Fazla Detay İçin Okuyunuz:** `cua/handoff_cua.md`

---

## 4. 📄 Standart Veri Değişim Formatları (JSON Schemas)

Sıradan bir makale (Örn: Turkey-related bir haber) dört kilit değişim (State) yaşar. Sistemde veriler akarken veri JSON paketinin üzerine **sadece ekleme yapılarak** bir top (blob) gibi ilerletilir.
1. **Raw (Crawler'dan çıkan):** `{"source": "BBC", "country": "uk", "url": "...", "content": "Text", "media": {"main_image": "http..."}}`
2. **Stored (DB MinIO sonrası):** `url`'in sha256'sı alınıp `news_id` yaratılır! Resimler `{"minio_path": "minio://news-media/news_id/main.jpg"}` formatına bürünür.
3. **VLM Result:** Orijinal veriye ek olarak `"vlm_analysis": { "images": [ {"description": "...", "objects": ["flag", "police"], "sentiment": "negative"} ] }` gibi bir ağaç (tree) eklenir.
4. **Final Result:** Metne `llm_analysis` finalizasyonu (`summary, sentiment_label, entities...` json yapısı) eklenip saklanır.

📚 **Daha Fazla Detay İçin Okuyunuz:** `docs/json_schemas.md`

---

## 5. 🛑 Hatalar ve Tolerans Kodları (Error Codes Yönetimi)

Otonom makineler hatalarda kırılmamaları adına bir Error standardizayonu üstlenir. Hata konseptleri `{NODE}_{CATEGORY}_{ERROR}` biçimindedir.

*   `1xx` **Ağ Hataları (NET):** Crawl sitesi timeout olduğunda (Örn: `CRAWLER_NET_102`) veya DB bağlantı gidince (`DB_NET_101`). Retries/Backoffs mekanizmasını (`3x`, `5x`) tetikler.
*   `2xx` **İşlem Hataları (PROC):** Resim okunamayınca `VLM_PROC_201 (IMAGE_CORRUPT)`, Rabbit kuyruğu dolunca Queue uyarısı verir. Vector embedding hata verirse `DB_PROC_202`, veritabanına resimsiz/vektörsüz ama salt tekstli şekilde yazım ("Mark for retry") kaydına zorlar.
*   `3xx` **Data (PAYLOAD) Hataları:** Crawler 50KB üstü çok bozuk DOM data yollarsa, Json'lar corrupt (`ORCH_DATA_301`) olursa yoksay/drop (skip) işlemi görür, sistem boğulması engellenir.
*   `4xx` / `5xx` **Sistem ve İzinler:** En yaygın olan GPU çökmesi durumu `LLM_SYS_401 (GPU_OOM)`'da cache temziler, retry count 2'yi esnetir ve partial sonuçlarını döndürür, Orchestrator'a iletir; gerekirse DB doluluk oranlarını bildirir (`DB_SYS_401/2 DISK FULL`).

**Format:** `{"success": false, "error": {"code": "...", "message": "...", "recoverable": true, "partial_result": null}}`

📚 **Daha Fazla Detay İçin Okuyunuz:** `docs/error_codes.md`

---

## 6. 🛠 Ağ Yapılandırmaları, Devops ve Scriptler

Projeyi canlı (Production) bir sunucular grubunda ayağa kaldırmak komplike olabilir çünkü Node'lar Vast.ai gibi farklı IP adreslerinde ve NAT (Network Address Translation) arkasında kapalı portlara sahip olabilirler.

### 6.1 WireGuard Sanal Özel Ağ
Makineler dünyasındaki en emniyetli iletişim `10.0.0.x` bandında kurulacak WireGuard (WG) Sanal Özel Ağı ile idare edilmesidir.
- Çok hafif ve ucuz bir Linux VPS makinesi `10.0.0.1` Orchestrator VPN Server olarak konumlanır. `51820` UDP Wireguard portu açıktır. Diğer VLM (`10.0.0.4`), LLM (`10.0.0.5`) gibi Vast.ai veya şirket içi GPU canavarları, bu merkeze WireGuard client configiyle bağlanır. İletişim RabbitMQ (`5672`) ve gRPC (`50051`) internal ağından yürüdüğü için kimse (external world) portları tarayamaz, VPN sertifikasını kıramaz.

📚 **Daha Fazla Detay İçin Okuyunuz:** `docs/wireguard_setup.md`

### 6.2 Çalıştırma Kodları (Deployment Commands & Automation)
Kodlar `/scripts` dizini altında guarded host ve bridge akışlarıyla mevcuttur:
- **Guarded core:** `orchestrator.ps1` ve `orchestrator.sh`, Orchestrator'i readiness kontrolüyle başlatır; gerekirse RabbitMQ/PostgreSQL/MinIO servislerini Compose ile kaldırır.
- **Guarded worker:** `crawler.sh`, `db.sh`, `vlm.sh`, `llm.sh` ve `cua.sh` Vast/Linux node'larında preflight, venv, proto, bağlantı ve startup doğrulaması yapar.
- **Bridge:** `scripts/helper/windows/bridge.ps1`, dinamik Vast.ai IP/port oturumları için SSH reverse tunnel supervisor olarak kullanılır.
- Eski Docker Hub push ve kopyala-yapıştır deploy scriptleri `scripts/legacy/` altına alınmıştır.

📚 **Daha Fazla Detay İçin Okuyunuz:** 
- `scripts/handoff_scripts.md` (Otomasyon İşlemleri Açıklaması)
- `docs/deployment_commands.md` (Vast.ai İçin Modüllerin Tam Açık Docker Run Konfigürasyonları)
- `docs/vast_ai_guide.md` (Vast Instances Kurulum / Seçim Önerileri)
- `docs/local_dev_guide.md` (Kendi cihazında test edecek Geliştiriciler (Localhost Docker Compose & LM Studio Fallback Modları için)).

### 6.3 🛠️ Proto Nasıl Derlenir? (Kritik Unsur)
Her `orchestrator.proto` sözleşmesinde yapılacak en küçük bir değişiklik (Örn: `RegisterRequest` içine bir değer katma) node'lar arası kırılıma sebep olur. Bu proto'yu derleyip tüm dosyalardaki python sınıflarına (relative import ile) yamalamak için ana dizinde kesin çözüm scripti bulundurulur:
> **Terminal'de direkt bunu çalıştırın:** `python compile_proto.py`

📚 **Daha Fazla Detay İçin Okuyunuz:** `proto/handoff_proto.md`

---

## 7. 🚀 Yol Haritası ve Gelecek Geliştirilmeleri (Roadmap & Improvements)

Sistemi evrensel ve kusursuz yapmak adına tanımlı olan ek çalışmalar:
1.  **FastAPI ve Arayüz Ağı:** Veritabanına inen semantik JSON analizlerin sorgulanması (Ülke bazlı istatistik grafikleri vs) için Web UI Dashboard entegrasyonu.
2.  **Sosyal Ağ Gezgini:** Haberler haricinde X (Twitter) API'leri veya Reddit paylaşımlarını bir `CRAWL MODEL` gibi ağa dahil etmek.
3.  **Translate / Çok Dilli (Multilingual) Düğüm:** Toplanan bilginin LLM modelleri için context'inin optimize edilmesi (Ana Node'a inmeden Translator modeline gitme veya HuggingFace Qwen3-Base-Multilingual ağırlıklarının optimize tuning işleminden geçmesi).
4.  **Zaman ve Olay Bazlı Tetikleyiciler (Triggers):** Sistem açık oldukça Crawler'ın sürekli URL aramalarına boğulmayıp, Cron-job/APScheduler üzerinden (Örn. `08:00 AM Daily` haberleri topla gibi) idare edilmesi.

📚 **Daha Fazla Detay İçin Okuyunuz:** `docs/future_improvements.md`
