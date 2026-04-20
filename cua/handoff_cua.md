# 🤖 CUA (Computer Using Agent) Handoff Documentation

Bu belge, Bitirme Projesi'nin 6. ve en gelişmiş düğümü olan **CUA (Computer Using Agent)** modülünün tüm mimari kararlarını, işleyiş mantığını, entegrasyon noktalarını ve geliştirme yönergelerini içermektedir. Bu belge, `handoff_all.md` ve `handoff_files.md` belgelerine ek olarak, CUA'nın sistemdeki rolünü detaylandıran "Single Source of Truth" (Tek Gerçeklik Kaynağı) dokümanıdır.

---

## 📌 1. Genel Bakış ve Misyon

Mevcut sistemde yer alan `Crawler` modülü, statik URL'ler üzerinden (Örn: `bbc.com/turkey`) haber toplayan deterministik bir yapıdadır. CUA ise **stokastik (olasılıksal/kendi inisiyatifiyle ilerleyen)** bir "Avcı (Hunter)" ajanıdır. Belli URL'lere gitmek yerine, arama motorlarını (Google/DuckDuckGo) kullanarak insan gibi gezinir.

CUA, iki farklı görev modunda (Dual-Mode) çalışacak şekilde tasarlanmıştır:

1.  **Mod 1: Yüzeysel Haber Tarama (Surface Search)**
    *   **Amacı:** Statik crawler'ın kaçırabileceği güncel/farklı kaynaklardaki haberleri bulmak.
    *   **İşleyiş:** Orchestrator bir haber tarama işi başlattığında, Crawler ile *paralel (fan-out)* çalışır. Belirtilen anahtar kelimeyi (Örn: "Turkey economy") Google'da arar, farklı sitelerden haberi ve görseli çeker, normal pipeline'a aktarır.
    *   **Durma Koşulu:** Orchestrator tarafından sağlanan limitlere (Örn: `max_articles=10`) ulaştığında durur.
    *   **Hafıza (State):** Olası sonsuz döngüleri ve tekrarı önlemek için sadece o anki görev (session) boyunca gezilen URL'lerin bir listesini (Python `set()`) tutar. Ayrıca Orchestrator'dan bir "exclude list" (zaten DB'de olan URL'ler) alabilir.

2.  **Mod 2: Derin İstihbarat Araştırması (Deep Intelligence Research)**
    *   **Amacı:** Kullanıcı tarafından verilen spesifik bir konu üzerine internette derinlemesine bir dedektif çalışması yapmak. (Örn: "2026 Türkiye ekonomik sızıntı iddiaları ve X forumundaki yankıları").
    *   **İşleyiş:** Çok kaynaklı bilgileri okur, bağlantıları kurar ve sentezler. Sayfadan sayfaya atlayarak bulgular (findings) biriktirir.
    *   **Durma Koşulu:** Ajan, her döngüde kendi kendine "Yeterli ve emin bir bilgi topladım mı?" diye sorar (Self-Evaluation). Öz-güven (Confidence) skoru ≥ %80 olduğunda aramayı durdurur ve son bir sentez raporu üretir.
    *   **Hafıza (State):** LangGraph State üzerinde `visited_urls`, `findings`, `current_hypothesis` gibi yapılandırılmış bir "grafik hafıza" taşır. Görev sonunda bu state kalıcı rapora dönüştürülür.

---

## 🏗️ 2. Mimari ve Teknoloji Yığını

CUA, karmaşık bir yapay zeka ajanı olduğundan kendine has güçlü kütüphaneler barındırır.

*   **Ajan Çerçevesi (Agent Framework):** `LangGraph (Minimal)`
    *   Basit bir "Döngüsel (Cyclic)" durum makinesi kullanır. Düğümler: `Plan → Execute/Browse → Evaluate → Synthesize`.
*   **Bilgisayar Kullanımı (Computer Use / Tarayıcı):** `Browser-Use` kütüphanesi.
    *   *Neden?* Playwright tabanlı bu kütüphane "Hybrid" (DOM okuma + Vision screenshot okuma) destekler. Ajan, sayfadaki HTML'i okur, ancak site bot koruması (Captcha) çıkarırsa Vision (Görüntü İşleme) moduna geçip ekrandaki koordinatlara göre "robot olmadığımı onayla" butonuna tıklayabilir.
*   **Ajan Beyni (LLM / VLM):** 
    *   **Production:** `Qwen3.5-9B` veya `Qwen3-8B` (Quantized, GPU kullanımı, tam otonomi).
    *   **Fallback / Local Dev:** LM Studio API (Örn: `Qwen-4B`) - Cihazı yormadan test edebilmek için.

---

## 🔌 3. Sistem Entegrasyonu ve Veri Akışı

CUA, 6. Nod (Düğüm) olarak mevcut Yıldız Topolojisine entegre edilir.

### Ağ ve Kayıt (gRPC)
Tıpkı diğer node'lar gibi ayağa kalktığında Orchestrator'a `RegisterRequest` atar ve `Heartbeat` gönderir. `NodeType` enumeration'ında `CUA` olarak tanımlanır.

### Görev Dağıtımı (RabbitMQ)
İletişim **Push/Queue-Based** model ile sağlanır:
*   Orchestrator görevi `agent_tasks` (Yeni Kuyruk) üzerine atar.
*   CUA asenkron olarak görevi alır, LangGraph döngüsünü çalıştırır.
*   **Sonuç:**
    *   (Mod 1 için): Toplanan her bireysel haber direkt Orchestrator'a veya `db_tasks` kuyruğuna (VLM/LLM gereksinimine göre analizden geçecek şekilde) itilir.
    *   (Mod 2 için): Kapsamlı görev raporu `agent_results` (Yeni Kuyruk) üzerinden Orchestrator'a döner, o da DB'ye yazdırır.

### Failover (Düşme Durumu)
Crawler hedeflenen statik bir sitede "403 Forbidden" ya da "Bot Detection" kısıtlamasına takılırsa, Orchestrator bu spesifik URL işini CUA'ya devredebilir. Çünkü CUA'nın `magic=True` konfigürasyonu ve görsel tıklama (Vision) yetenekleri standart crawler'ı aşan engelleri geçebilir.

---

## 🗄️ 4. Veritabanı (DB) Değişim İhtiyaçları

CUA'nın dahil olması, PostgreSQL veritabanında yapısal yenilikler gerektirir. DB Node (`postgres_manager.py`) üzerinde yapılması KESİN olan değişiklikler:

1.  **Yeni Enumeration / Kolon:** 
    *   `news` tablosuna haberi kimin getirdiğini belirtmek için `source_type` Enum eklenecek: `crawler` (varsayılan), `agent_surface` (Mod 1).
2.  **Mod 2 İçin Yeni Tablo (`research_missions`):**
    *   Mod 2'de çekilen veriler dağınık "haberler" değil, bir "bütünsel rapordur".
    *   Tablo şeması (Öneri):
        *   `mission_id` (PK, string)
        *   `topic` (string)
        *   `status` (enum: in_progress, completed, failed)
        *   `final_report_json` (jsonb - sentezlenen nihai metin ve iddialar)
        *   `graph_state_json` (jsonb - son LangGraph hafıza durumu)
        *   `created_at` / `completed_at`
3.  **Haber İlişkisi (Foreign Key):**
    *   `news` tablosuna nullable bir `mission_id` kolonu. Mod 2 çalışırken toplanan somut haber maddeleri `news`'e kaydedilse bile "Bu araştırma görevi kapsamında bulunmuştur" diyerek bu ID ile `research_missions`'a bağlanmalıdır.

---

## ☢️ 5. Kritik Yapısal Kod Değişiklikleri ve Gözden Kaçmaması Gerekenler

Bu ajanın kodlaması sırasında mevcut ana sistemde güncellenmesi *şart* olan yerler:

1.  **`orchestrator/services/node_registry.py`**: 
    *   `NodeType` Enum içine `CUA = "cua"` (Satır 13-17 arası) eklenmeli. Yorumlardaki `(Crawler, VLM, LLM, DB)` listesine `CUA` yazılmalı.
2.  **`orchestrator/config.py` ve `rabbitmq_manager.py`**:
    *   Yeni `QUEUE_AGENT_TASKS = 'agent_tasks'` ve `QUEUE_AGENT_RESULTS = 'agent_results'` env variable'ları ve ilgili `publish/consume` metotları eklenmeli.
3.  **`orchestrator/services/pipeline_manager.py`**:
    *   Mod 1'in fan-out mantığı: `trigger_crawl` fonksiyonu çalıştığında, idle durumda olan CUA'ları kontrol edecek ve `agent_tasks`'a paralel iş verecek şekilde genişletilmeli.
    *   CUA dönüşlerini (Özellikle Mod 2) işleyecek `on_agent_result_complete` mantığı/tetikleyicisi eklenmeli.
4.  **`proto/orchestrator.proto`**:
    *   RabbitMQ kullanıldığı için spesifik bir rpc çağrısı açılmayacak olsa bile, yorumlarda ve Enum tanımlarında CUA adaptasyonları belirtilmeli (Örn. `RegisterRequest` açıklaması).
5.  **Docker & DevOps (`docker-compose.yml`)**:
    *   CUA'nın kullanacağı Browser-Use için bir Chromium bağımlılığı (`playwright install`) + LLM için Cuda (GPU) bağımlılığı bir araya gelecek. Konteyner imajı oldukça büyük (15-20 GB) olabilir. Bu yüzden `cua` servisi `depends_on: orchestrator` mantığıyla kendi `Dockerfile`'ında (Multi-stage build önerilir) tanımlanmalıdır.

---

## 🚦 6. Hataya Tolerans (Error Codes)

CUA, modüller ailesinin `6xx` veya `1xx (CRAWLER vari)` hata standartlarına tabi olmalıdır:
*   `CUA_NET_105`: Aranan URL'in düşmesi / Timeout
*   `CUA_SYS_402`: LangGraph döngüsünün sonsuza girmesi (Örn: Max Cycle Timeout, `depth > 15`)
*   `CUA_PROC_203`: Browser-Use'un screenshot alma arızaları (Playwright çökmesi)

Hata durumlarında `agent_results` üzerinden `status: FAILED` ve kısmi (partial) graph-state sonuçları ileterek raporu Orchestrator'a dönmeli.

---

Geliştiriciler için Not: *Bu dosya, yeni CUA modülü yaratılırken LangChain, Playwright ve DB Entegrasyon adımlarını izlemek için "Checkpoint" niteliğindedir. Kodlarken mutlaka bu mimari kurallar baz alınmalıdır!*
