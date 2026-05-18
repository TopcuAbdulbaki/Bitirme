# TEZ İSKELETİ — ÖN TASLAK

> **Proje:** Dağıtık Mikro-Servis Mimarisinde Otonom Haber Toplama ve Yapay Zekâ Destekli Araştırma Ajanı Sistemi
>
> **Referans yapı:** OrnekTez.md (Afet Koordinasyon Sistemi tezi)

---

## ÖN SAYFALAR

| Bölüm | Açıklama |
|---|---|
| **Kapak** | Üniversite, bölüm, tez başlığı, öğrenci bilgileri, danışman, tarih |
| **Önsöz** | Kısa teşekkür ve motivasyon |
| **İçindekiler** | Otomatik oluşturulacak |
| **Tablo Listesi** | Otomatik |
| **Şekil Listesi** | Otomatik |
| **Kısaltmalar** | gRPC, RabbitMQ, CUA, LLM, VLM, pgvector, LangGraph, vLLM, MinIO, AMQP, SSH, REST, Proto(buf) vb. |
| **Özet** | ~200 kelime; sistemin amacı, mimari, ulaşılan sonuçlar |
| **Abstract** | Özetin İngilizce karşılığı |

---

## 1. GİRİŞ (≈ 2–3 sayfa)

Örnek tezdeki karşılık: **Bölüm 1 – GİRİŞ**

Bu bölümde anlatılacaklar:

- Geleneksel haber toplama ve analiz süreçlerinin sınırlılıkları (manuel tarama, tekil kaynak bağımlılığı, ölçeklenme problemi).
- Otonom ajan kavramına kısa giriş; LLM tabanlı ajanların araştırma ve karar destek süreçlerindeki potansiyeli [şuraya atıf verilebilir — örn. ReAct (Yao et al., 2023) https://arxiv.org/abs/2210.03629].
- Projenin amacı: İki bütünleşik bileşenden oluşan bir sistem geliştirmek:
  1. **Pipeline (boru hattı):** Çok kaynaklı, dağıtık haber toplama → depolama → VLM/LLM analiz zinciri — saf güç olarak veri işleme.
  2. **Otonom Araştırma Ajanı (CUA):** Tek başına tüm araştırma sürecini yürüten, web'de gezinen, makale toplayan ve sentez rapor üreten bağımsız ajan.
- "Ürün projesi" vurgusu: Akademik araştırma projesinden farklı olarak, **çalışan**, **dağıtılabilir**, **modüler** ve **ölçeklenebilir** bir sistem üretmenin hedeflendiği.
- Tezin organizasyonu (hangi bölümde ne anlatılacak, kısa roadmap).

**📸 Şekil Önerileri — Bölüm 1:**
- *Şekil 1.1:* Sistemin kuş bakışı kavramsal diyagramı (pipeline + ajan iki kolu gösteren basit blok şema)

---

## 2. GENEL KISIMLAR / LİTERATÜR VE TEKNOLOJİ TEMELLERİ (≈ 8–12 sayfa)

Örnek tezdeki karşılık: **Bölüm 2 – GENEL KISIMLAR**

> [!IMPORTANT]
> Örnek tezde bu bölüm "algoritma aileleri + veri setleri + kullanılan diller" şeklinde. Bizim projede model eğitimi yok, bunun yerine **mimari paradigmalar, kullanılan çerçeveler ve protokoller** anlatılacak.

### 2.1 Mikro-Servis Mimarisi ve Dağıtık Sistemler
- Monolitik vs. mikro-servis karşılaştırması [şuraya atıf verilebilir — Newman, S. (2021). *Building Microservices*, 2nd ed. O'Reilly https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/].
- Servis keşfi, kayıt (registry) ve sağlık kontrolü (heartbeat) kalıpları.
- Container tabanlı dağıtım (Docker, Docker Compose).

**📸 Şekil Önerileri — Bölüm 2:**
- *Şekil 2.1:* Monolitik vs. mikro-servis mimari karşılaştırma diyagramı (genel, literatürden alınabilir)

### 2.2 gRPC ve Protocol Buffers
- RPC paradigması; REST'e karşı gRPC'nin avantajları (tip güvenliği, ikili seri hale getirme, çift yönlü akış).
- `.proto` dosyalarından kod üretimi ve servis tanımları [şuraya atıf verilebilir — https://grpc.io/docs/].
- Projede gRPC'nin kullanıldığı noktalar (node kaydı, heartbeat, sonuç raporlama).
- *Şekil 2.2:* gRPC iletişim akışı diyagramı (client ↔ server, protobuf seri hale getirme)

### 2.3 Mesaj Kuyruğu Sistemleri: RabbitMQ ve AMQP
- Publish-subscribe ve iş kuyruğu desenleri.
- RabbitMQ'nun garantili teslim, yeniden deneme (retry), tıkanıklık yönetimi mekanizmaları [şuraya atıf verilebilir — RabbitMQ Documentation https://www.rabbitmq.com/docs].
- Projede hangi kuyrukların (VLM_TASKS, LLM_TASKS, AGENT_TASKS, ...) ne amaçla tanımlandığı.
- *Şekil 2.3:* RabbitMQ producer → exchange → queue → consumer akış şeması

### 2.4 Büyük Dil Modelleri (LLM) ve Görsel Dil Modelleri (VLM)
- Transformer mimarisinin kısa özeti [şuraya atıf verilebilir — Vaswani et al. (2017) "Attention Is All You Need" https://arxiv.org/abs/1706.03762].
- LLM'lerin metin özetleme, duygu analizi, varlık çıkarma gibi NLP görevlerinde kullanımı [şuraya atıf verilebilir — Brown et al. (2020) GPT-3 https://arxiv.org/abs/2005.14165].
- VLM'lerin görüntü–metin çapraz analiz yeteneği; projede haber görselleri üzerinde kullanımı.
- vLLM (PagedAttention) ile yüksek verimli çıkarım [şuraya atıf verilebilir — Kwon et al. (2023) https://arxiv.org/abs/2309.06180].

### 2.5 Otonom Ajanlar ve LangGraph
- LLM-tabanlı otonom ajan kavramı; plan → execute → evaluate döngüsü [şuraya atıf verilebilir — Yao et al. (2023) ReAct].
- LangGraph: durum tabanlı çizge (state graph) ile ajan iş akışı yönetimi [şuraya atıf verilebilir — LangGraph docs https://langchain-ai.github.io/langgraph/].
- `browser-use` kütüphanesi ile web sayfası etkileşimi (headless tarayıcı kontrol).
- Projede CUA (Computer Using Agent) düğümünün otonom araştırma ajanı olarak konumlandırılması.
- *Şekil 2.4:* LangGraph StateGraph kavramsal diyagramı (düğümler, kenarlar, koşullu yönlendirme)

### 2.6 Vektör Veritabanları ve Anlamsal Arama
- Vektör gömme (embedding) kavramı ve anlamsal benzerlik araması.
- pgvector: PostgreSQL üzerinde vektör desteği [şuraya atıf verilebilir — pgvector GitHub https://github.com/pgvector/pgvector].
- Cosine benzerliği ve KNN arama; projede haberlerin anlamsal olarak sorgulanması.

### 2.7 Nesne Depolama: MinIO
- S3-uyumlu nesne depolama; ikili varlıkların (görsel, medya) yönetimi [şuraya atıf verilebilir — MinIO docs https://min.io/docs/minio/linux/index.html].
- Projede haber görselleri ve medya dosyalarının MinIO'ya aktarılması.

### 2.8 Web Kazıma (Web Scraping) Teknikleri
- Headless tarayıcı tabanlı kazıma (Playwright/Chromium).
- Anti-bot mekanizmaları ve bunlara karşı stratejiler (user-agent döndürme, jitter, rate limiting).
- `crawl4ai` kütüphanesi ve "magic mode" [şuraya atıf verilebilir — crawl4ai GitHub https://github.com/unclecode/crawl4ai].

---

## 3. MATERYAL VE METOT / SİSTEM MİMARİSİ VE TASARIM (≈ 10–15 sayfa)

Örnek tezdeki karşılık: **Bölüm 3 – MATERYAL METOD**

> [!IMPORTANT]
> Bu bölüm tezin **kalbi**. Ürün projesinde "veri seti hazırlama + model eğitimi" yerine **sistem tasarımı, düğüm mimarisi, protokol tasarımı, dağıtım stratejisi** ön plandadır. Sistemde **yıldız (star) topolojisi** kullanılmıştır; bu tercihin gerekçeleri (merkezi koordinasyon, basitlik, gözlemlenebilirlik vs. tek hata noktası değiş-tokuşu) bu bölümde ele alınacaktır.

### 3.1 Çalışma Ortamı ve Donanım Altyapısı
- Geliştirme ortamı: Windows lokal makine + Vast.ai bulut GPU düğümleri.
- Docker Compose tabanlı orkestrasyon (lokal).
- Vast.ai üzerinde GPU kiralama ve SSH tünelleri ile bağlantı kurma (node bridge yapısı).

**📸 Şekil Önerileri — Bölüm 3:**
- *Şekil 3.1:* Geliştirme ortamı topolojisi (lokal makine + Vast.ai bulut düğümleri + SSH köprüleri)

### 3.2 Genel Sistem Mimarisi (Üst Düzey)
- **Şekil 3.2:** Sistem bileşen diyagramı — Orchestrator, Crawler, DB, VLM, LLM, CUA düğümleri, RabbitMQ ve PostgreSQL/MinIO bağlantıları. **(Tezin en kritik şekli)**
- **Yıldız (Star) Topolojisi:** Orchestrator merkez düğüm, diğer tüm servisler uç düğümler. Tercih gerekçesi:
  - Merkezi koordinasyon ve görev dağıtımının basitliği.
  - Düğüm ekleme/çıkarma işlemlerinin merkezi registry üzerinden kolay yönetimi.
  - Tüm sistem durumunun tek noktadan gözlemlenebilirliği.
  - Değiş-tokuş: Orchestrator tek hata noktasıdır (single point of failure) — bu sınırlama 6. bölümde tartışılacak.
- İki iletişim katmanı:
  - **gRPC:** Senkron kayıt, heartbeat, görev atama/raporlama (kontrol düzlemi).
  - **RabbitMQ:** Asenkron görev dağıtımı ve sonuç toplama (veri düzlemi).
- "Neden ikili iletişim?" kararının gerekçesi (kontrol düzlemi vs. veri düzlemi ayırımı).
- *Şekil 3.3:* gRPC vs. RabbitMQ kullanım alanlarını gösteren ikili iletişim diyagramı

### 3.3 Orchestrator Düğümü
- Görevleri: Node kaydı, heartbeat izleme, görev yaratma, boru hattı yönetimi, admin HTTP paneli.
- `PipelineManager` ile görev durum makinesi (crawl → store → VLM → LLM → tamamlandı).
- `NodeRegistry` ile dinamik düğüm keşfi ve zaman aşımı tespiti.
- `AdminHttpServer` — REST tabanlı yönetim arayüzü.
- Poll modeli (Crawler) vs. Push modeli (VLM/LLM/CUA) kararı.
  > *Öz-not:* Bu ayrımın teknik gerekçesi tezde detaylanacak — Crawler poll ile kendi hızında çalışırken, diğer düğümler kuyruk tabanlı push ile tetikleniyor. Sağladığı fayda/zararlar tartışılacak.
- *Şekil 3.4:* Orchestrator iç bileşen diyagramı (Registry, PipelineManager, gRPC Server, RabbitMQ Manager, Admin HTTP)
- *Şekil 3.5:* Görev durum makinesi akış şeması (state machine: created → crawled → stored → vlm_done → llm_done → completed)

### 3.4 Crawler Düğümü
- Modüler `NewsCrawler` sınıfı.
- Google News üzerinden kaynak bazlı link toplama → sayfa indirme → içerik ve medya çıkarma boru hattı.
- Anti-bot stratejileri: `magic=True`, `simulate_user`, rastgele jitter, user-agent döndürme.
- Görsel filtreleme zinciri (boyut, tür, önem skoru).
- Standalone ve dağıtık modlar arası geçiş.
- Dış kaynak yapılandırması (SOURCES listesi, configurable arama sorguları).
- *Şekil 3.6:* Crawler boru hattı akış şeması (Google arama → link filtreleme → sayfa indirme → içerik/medya çıkarma → sonuç raporlama)
- *Şekil 3.7:* Görsel filtreleme karar ağacı (boyut kontrolü, URL keyword kontrolü, OG image çıkarma)

### 3.5 Veritabanı (DB) Düğümü
- PostgreSQL şeması: `news`, `vlm_analysis`, `llm_analysis`, `research_missions` tabloları.
- pgvector ile 1024 boyutlu gömme vektörleri ve anlamsal arama.
- MinIO entegrasyonu: medya dosyalarının nesne depolamaya aktarılması.
- Embedding pipeline: haber içeriği → yerel embedding modeli → pgvector INSERT.
- Çift yazma koruması (URL tabanlı deduplication).
- *Şekil 3.8:* Veritabanı ER diyagramı (news, vlm_analysis, llm_analysis, research_missions tablolarının ilişkileri)
- *Şekil 3.9:* Embedding ve anlamsal arama akışı (metin → embedding model → pgvector → cosine similarity sorgusu)

### 3.6 VLM Düğümü
- Görsel analiz iş akışı: haber görseli → MinIO'dan çekme → VLM çıkarımı → sonuç raporlama.
- Model seçimi ve yükleme stratejisi (GPU bellek yönetimi).
- RabbitMQ üzerinden görev tüketimi ve sonuç yayınlama.

### 3.7 LLM Düğümü
- Metin analiz iş akışı: haber metni + VLM sonuçları → LLM çıkarımı → özetleme, duygu analizi, varlık çıkarma.
- Prompt tasarımı ve çıktı yapılandırma (JSON parse).
- RabbitMQ üzerinden görev tüketimi.

### 3.8 CUA (Computer Using Agent) Düğümü — Otonom Araştırma Ajanı
- **Bu bölüm projenin en özgün katkısı** olarak vurgulanacak.
- **Tasarım evrimi:** İlk sürümde LLM'in tamamen iradeli (free-form) kararlar aldığı serbest ajan mimarisi denenmiş; ancak ajanın sonsuz döngülere girmesi, CAPTCHA'lara takılması ve tutarsız çıktılar üretmesi nedeniyle bu yaklaşımdan vazgeçilmiştir. Son sürümde ajan, **sıkılaştırılmış bir motor (engine)** olarak yeniden tasarlanmış; LLM yalnızca belirli karar noktalarında (sorgu planı üretme, kalite kapısı, sentez) devreye girerken, navigasyon ve durum yönetimi deterministik kurallara bağlanmıştır. Bu evrim süreci tezde detaylıca ele alınacaktır.
- LangGraph StateGraph ile `Plan → Execute → Evaluate → Synthesize` döngüsü.
- `AgentState` yapısı ve durum yönetimi (ziyaret edilen URL'ler, toplanan makaleler, döngü sayacı, ilerleme izleme).
- Arama sorgusu çeşitlendirme stratejisi: sorgu planı üretme, zayıf sorgu koruması (guardrail), fallback sorgu mekanizması.
- `BrowserTool`: Playwright tabanlı headless tarayıcı sarmalayıcı (arama, sayfa gezinme, içerik çıkarma).
- `ContentExtractor`: Ham HTML → yapılandırılmış makale verisi dönüşümü.
- `CUAModelHandler`: LLM ile sorgu planı üretimi, makale kalite kapısı (quality gate), makale analizi, sentez raporu üretimi.
- Durdurma koşulları: max döngü, max arama, max makale, ilerleme yokluğu.
- Raporlama ve Orchestrator'a sonuç gönderme (RabbitMQ).
- *Şekil 3.10:* CUA LangGraph durum çizgesi (Plan → Execute → Evaluate → koşullu dal → Synthesize / Plan)
- *Şekil 3.11:* CUA tasarım evrimi karşılaştırması (v1 serbest ajan vs. v2 sıkı motor — iki sütunlu diyagram)

### 3.9 Dağıtım ve Operasyon (DevOps)
- Dockerfile tasarımları (her düğüm için ayrı).
- Docker Compose ile yerel geliştirme ortamı.
- Vast.ai dağıtım scriptleri (`vast_*_host_guarded.sh`): SSH tünelleme, sağlık kontrolü, otomatik yeniden başlatma.
  > *Not:* Vast.ai, geliştirme aşamasında GPU düğümlerini hızla kaldırma/indirme imkânı sağladığı için tercih edilmiştir. Üretim ortamı değil, hızlı iterasyon ortamı olarak kullanılmıştır.
- Node bridge mekanizması: Bulut düğümleri ile lokal Orchestrator arasındaki SSH köprüleme.
- `host_guarded` scriptlerindeki idempotent kurulum ve güvenlik kontrolleri.
- *Şekil 3.12:* Dağıtım topolojisi (lokal Orchestrator + Vast.ai düğümleri + SSH tünelleri ile bağlantı haritası)

### 3.10 Protocol Buffers Tanımları
- `orchestrator.proto` dosyasının yapısı: ortak mesajlar, servis tanımları, enum'lar.
- İleri ve geri uyumluluk kararları.
- Kod üretimi süreci (`compile_proto.py`).

---

## 4. UYGULAMA / SİSTEM GÖSTERİMİ (≈ 5–8 sayfa)

Örnek tezdeki karşılık: **Bölüm 4 – UYGULAMA** (arayüz ekran görüntüleri)

### 4.1 Orchestrator Yönetim Paneli (Admin HTTP)
- Ekran görüntüleri ile yönetim arayüzü gösterimi.
- Düğüm durumu, görev listesi, kuyruk boyutları, crawl başlatma/durdurma.
- *Şekil 4.1:* Admin paneli ana ekranı — düğüm listesi ve durum göstergeleri (ekran görüntüsü)
- *Şekil 4.2:* Görev listesi ve kuyruk boyutları ekranı (ekran görüntüsü)

### 4.2 Haber Toplama Akışı Gösterimi
- Uçtan uca bir crawl döngüsünün adım adım gösterimi (log çıktıları veya ekran görüntüleri).
- Google'dan link toplama → sayfa indirme → doğrulama → DB'ye kayıt.
- *Şekil 4.3:* Crawler terminal çıktısı — bir kaynağın taranması süreci (log ekran görüntüsü, emojili çıktılar)
- *Şekil 4.4:* PostgreSQL'de saklanan haber kaydı örneği (tablo görünümü veya JSON)

### 4.3 CUA Otonom Araştırma Gösterimi
- Bir araştırma görevinin başlatılması, ajanın plan → arama → ziyaret → sentez adımları.
- Makale kalite kapısı örnekleri (kabul/ret).
- Son rapor çıktısı.
- *Şekil 4.5:* CUA çalışma logları — Plan/Execute/Evaluate adımlarının terminal çıktısı
- *Şekil 4.6:* Kalite kapısı karar örnekleri (kabul edilen vs. reddedilen makale karşılaştırması)
- *Şekil 4.7:* CUA sentez raporu örneği (JSON veya formatlanmış çıktı)

### 4.4 VLM/LLM Analiz Boru Hattı Gösterimi
- Bir haber öğesinin VLM ve LLM aşamalarından geçişi.
- Örnek analiz çıktıları (özetleme, duygu, varlıklar).
- *Şekil 4.8:* VLM görsel analiz girdi/çıktı örneği (haber görseli → analiz JSON'ı)
- *Şekil 4.9:* LLM metin analiz çıktısı (özetleme, duygu analizi, varlık çıkarma örneği)

### 4.5 Anlamsal Arama Gösterimi
- pgvector ile benzer haber arama sorgusu ve sonuçları.
- *Şekil 4.10:* Anlamsal arama sorgusu ve benzerlik skorlarıyla dönen sonuçlar (tablo)

---

## 5. BULGULAR VE DEĞERLENDİRME (≈ 5–8 sayfa)

Örnek tezdeki karşılık: **Bölüm 5 – BULGULAR**

> [!IMPORTANT]
> Örnek tezde model doğruluk skorları (mAP, Dice, IoU) verilmiş. Bizim projede model eğitimi yok, dolayısıyla bulgular **sistem performansı, işletimsel metrikler ve kalite gözlemleri** üzerinden sunulacak.

### 5.1 Crawler Performans Metrikleri
- Kaynak başına ortalama link bulma sayısı, doğrulama oranı, toplama hızı.
- Anti-bot mekanizmalarına karşı başarı/başarısızlık oranları.
- Duplicate tespiti istatistikleri.
- *Tablo 5.1:* Kaynak bazlı crawl performans tablosu (kaynak adı, bulunan link, doğrulanan makale, oran)
- *Şekil 5.1:* Kaynak başarı oranları çubuk grafiği

### 5.2 CUA Araştırma Ajanı Performansı
- Görev başına ortalama döngü sayısı, toplanan makale sayısı, arama sayısı.
- Kalite kapısı kabul/ret oranları.
- Farklı konularda ajan davranışının gözlenmesi.
- *Tablo 5.2:* CUA görev metrikleri tablosu (konu, döngü, arama, toplanan makale, durdurma nedeni)
- *Şekil 5.2:* Kalite kapısı kabul/ret pasta grafiği
- Sentez raporlarının nitel değerlendirmesi (örnekler ile).

### 5.3 Boru Hattı Uçtan Uca Gecikmeleri
- Bir haberin crawl → DB → VLM → LLM → tamamlanma zaman ölçümleri.
- RabbitMQ kuyruk gecikmesi gözlemleri.

### 5.4 Anlamsal Arama Kalitesi
- Örnek sorgular ve dönen sonuçların anlamlılık değerlendirmesi (nitel).

---

## 6. SONUÇ VE TARTIŞMA (≈ 2–3 sayfa)

Örnek tezdeki karşılık: **Bölüm 6 – SONUÇ VE TARTIŞMA**

### 6.1 Özet
- Geliştirilen sistemin bütüncül değerlendirmesi: dağıtık mimari, otonom ajan, analiz boru hattı.

### 6.2 Güçlü Yönler
- **Modülerlik:** Her düğüm bağımsız olarak geliştirilebilir, dağıtılabilir, ölçeklenebilir.
- **Hibrit iletişim:** gRPC + RabbitMQ kombinasyonunun sağladığı esneklik.
- **Otonom araştırma:** CUA düğümünün insan müdahalesi olmadan çok adımlı araştırma yapabilmesi.
- **Semantik zenginlik:** pgvector ile anlamsal arama desteği.

### 6.3 Sınırlamalar (Yumuşak Karın)
- LLM/VLM düğümlerinin GPU bağımlılığı ve maliyet kısıtı.
- Crawler'ın anti-bot mekanizmalarına karşı kırılganlığı (CAPTCHA, IP banlama).
- CUA ajanının hallucination riski ve kalite kapısının yetersiz kalabileceği durumlar.
- Tek Orchestrator = tek hata noktası (single point of failure); yatay ölçekleme eksikliği.
- gRPC proto güncellemelerinin tüm düğümlerde senkronize edilme zorluğu.

### 6.4 Gelecek Çalışmalar ve Geliştirme Önerileri
- Orchestrator'ın yatay ölçeklenmesi (leader election, dağıtık durum).
- CUA'nın çok modlu (multi-modal) araştırma kabiliyeti (görüntü + metin analizi).
- Gerçek zamanlı bildirim sistemi (WebSocket/SSE).
- Daha gelişmiş embedding modelleri ve RAG (Retrieval-Augmented Generation) entegrasyonu.
- Güvenlik katmanı: kimlik doğrulama, TLS, API anahtarı yönetimi.
- Kullanıcı arayüzü (frontend dashboard) geliştirme.

---

## 7. KAYNAKÇA

Kaynakça stili: IEEE veya APA (üniversitenin kılavuzuna göre belirlenecek).

Metin içinde `[şuraya atıf verilebilir]` ile işaretlenen muhtemel kaynaklar:

| # | Kaynak | Bağlam |
|---|--------|--------|
| 1 | Newman, S. (2021). *Building Microservices*, 2nd ed. O'Reilly. | Mikro-servis mimarisi |
| 2 | gRPC Authors. *gRPC Documentation.* https://grpc.io/docs/ | gRPC ve Protocol Buffers |
| 3 | RabbitMQ. *Official Documentation.* https://www.rabbitmq.com/docs | Mesaj kuyruğu |
| 4 | Vaswani, A. et al. (2017). "Attention Is All You Need." https://arxiv.org/abs/1706.03762 | Transformer temeli |
| 5 | Brown, T. et al. (2020). "Language Models are Few-Shot Learners." https://arxiv.org/abs/2005.14165 | LLM temeli |
| 6 | Kwon, W. et al. (2023). "Efficient Memory Management for LLMs with PagedAttention." https://arxiv.org/abs/2309.06180 | vLLM |
| 7 | Yao, S. et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." https://arxiv.org/abs/2210.03629 | Otonom ajan, ReAct |
| 8 | LangChain. *LangGraph Documentation.* https://langchain-ai.github.io/langgraph/ | LangGraph |
| 9 | pgvector. *Open-source vector similarity search for Postgres.* https://github.com/pgvector/pgvector | Vektör veritabanı |
| 10 | MinIO. *Official Documentation.* https://min.io/docs/minio/linux/index.html | Nesne depolama |
| 11 | crawl4ai. *GitHub Repository.* https://github.com/unclecode/crawl4ai | Web kazıma |
| 12 | Docker. *Docker Documentation.* https://docs.docker.com/ | Konteynerizasyon |
| 13 | Vast.ai. *GPU Cloud Documentation.* https://vast.ai/docs | Bulut GPU |
| 14 | browser-use. *Browser automation for AI agents.* https://github.com/browser-use/browser-use | Tarayıcı otomasyon |

---

## 8. EKLER

- **Ek A:** `orchestrator.proto` tam metin
- **Ek B:** Docker Compose konfigürasyonu
- **Ek C:** CUA Agent durum diyagramı (LangGraph çizgesi)
- **Ek D:** Örnek crawler çıktısı (JSON)
- **Ek E:** Örnek CUA sentez raporu

---

## YAPI KARŞILAŞTIRMA: ÖRNEK TEZ ↔ BİZİM TEZ

| Örnek Tez Bölümü | Bizim Tez Karşılığı | Fark |
|---|---|---|
| 1. Giriş | 1. Giriş | Benzer yapı, farklı problem alanı |
| 2. Genel Kısımlar (algoritmalar, veri setleri) | 2. Genel Kısımlar (mimari paradigmalar, teknolojiler) | Algoritma anlatımı yerine **mimari ve çerçeve** anlatımı |
| 3. Materyal Metod (donanım, veri hazırlama, model eğitimi) | 3. Sistem Mimarisi ve Tasarım (düğüm mimarileri, protokoller) | Model eğitimi yerine **sistem tasarımı** |
| 4. Uygulama (arayüz ekranları) | 4. Sistem Gösterimi (akış gösterimleri, arayüz) | Benzer yaklaşım |
| 5. Bulgular (mAP, Dice, IoU) | 5. Bulgular (performans metrikleri, kalite gözlemleri) | Sayısal metrikler farklı (model skoru → sistem KPI'ları) |
| 6. Sonuç ve Tartışma | 6. Sonuç ve Tartışma | Benzer yapı |
| 7. Kaynakça | 7. Kaynakça | — |
| 8. Ekler | 8. Ekler | Benzer |
