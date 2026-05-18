# TEZ DÜZELTİLECEKLER

Buradaki maddeler iki amaca hizmet eder:
1. **Projede** yapılacak teknik iyileştirmeler
2. **Tezde** güncellenecek ilgili paragraflar

Önce proje güncellenir → ardından tez düzeltilir.

---

## 1. LLM ve VLM Düğümlerini vLLM Altyapısına Taşıma

> [!IMPORTANT]
> **Bu madde 2. maddeden önce yapılmalıdır.** Tek komutla tüm servisleri kaldırabilmek için önce her worker node'un kendi vLLM sunucusunu ayağa kaldırabilmesi gerekiyor.

### Mevcut Durum
- **CUA:** `docker-compose.cua-allinone.yml` + `Dockerfile.allinone` ile aynı GPU makinesinde hem `vllm serve` hem ajan çalışıyor. ✅
- **LLM:** `MODEL_MODE=transformers` → HuggingFace Transformers ile modeli doğrudan process içinde yüklüyor. `MODEL_MODE=lm-studio` → LM Studio API'ye istemci. ❌ vLLM yok.
- **VLM:** Aynı iki mod, `AutoModelForImageTextToText` ile. ❌ vLLM yok.

### Yapılacak Proje Değişikliği

**LLM için (düşük risk):**
- CUA'daki `vllm serve` + OpenAI API istemci şablonu LLM'e uyarlanır.
- `llm/Dockerfile` → `vllm/vllm-openai` base image veya vLLM kurulumu eklenir.
- `llm/services/model_handler.py` → `MODEL_MODE=vllm` dalı eklenir, `openai` istemciyle `vllm serve` API'sine bağlanır.
- LLM tamamen text model → vLLM uyumluluk riski düşük.

**VLM için (önce doğrula):**
- Kullanılacak modelin vLLM multimodal desteğini doğrula (`Qwen3-VL` ailesi vLLM'de destekleniyor mu?).
- Doğrulanmışsa LLM ile aynı pattern uygulanır.
- Doğrulanmamışsa mevcut `transformers` modu korunur, tezde sınırlama olarak belirtilir.

**Sağladığı Fayda:**
| | Mevcut (Transformers) | vLLM'e taşınırsa |
|---|---|---|
| Eşzamanlı istek | Tek sıralı | PagedAttention ile verimli batching |
| GPU kullanımı | Düşük (fragmentation) | Belirgin iyileşme |
| İlk istek gecikmesi | Yüksek (lazy-load) | Sunucu zaten hazır |
| Kod karmaşıklığı | Basit | CUA şablonu mevcut |

### Tezde Güncellenecek Paragraf
**Konum:** `tez.md` → Bölüm 2.4, "vLLM ile Yüksek Verimli Çıkarım" son paragrafı:

> ~~"Bu durum, LLM/VLM düğümlerinin yüksek eşzamanlılık gerektiren senaryolarda vLLM'in sağladığı... avantajlarından yararlanamadığı anlamına gelmektedir."~~

**Geçici not olarak:** Bu madde tamamlandığında son paragraf güncellenerek tüm worker'ların vLLM kullandığı yazılacak.

---

## 2. Docker / Dağıtım — Çok Komutlu Manuel Yapı

### Mevcut Durum (tezde şu an böyle yazıyor)
> GPU gerektiren düğümler (VLM, LLM, CUA) Compose tanımında yorum satırı olarak bulunmakta; bu düğümler pratikte Vast.ai üzerinde ayrı çalıştırılmakta ve lokal Orchestrator'a SSH tünelleri aracılığıyla **her oturumda manuel olarak** bağlanmaktadır.

### Yapılacak Proje Değişikliği

**--- SOHBET: OTO NODE KURULUMU ---**

Temel fikir: Orchestrator sabit kontrol düzlemi olur; yeni bir GPU node eklemek için tek komut yeterli olur.

#### Önerilen Mimari Adımlar

**1. Provisioner Script (`provision_node.ps1` / `.sh`)**
- Uzak makineye SSH ile bağlan
- Docker yoksa kur
- Repo'yu çek/güncelle
- Role göre `.env` yaz (`cua`, `llm`, `vlm`)
- İlgili Compose profilini çalıştır
- Tüneli aç / WireGuard kurulumunu tamamla

```
.\scripts\provision_node.ps1 -Role cua -Host 1.2.3.4 -SshPort 40001 -Key ~/.ssh/vast_key
```

**2. Tünel Yönetimi (kısa vadeli: SSH, uzun vadeli: WireGuard)**
- Kısa vade: Vast node `ORCHESTRATOR_HOST=127.0.0.1` alır, SSH -R ile lokal portlara erişir. IP değişince sadece `node_bridges.local.json` güncellenir, supervisor tüneli yeniden açar.
- Uzun vade: WireGuard — her node sabit VPN IP'si (10.0.0.x) alır. Port çakışması/kopma sorunları ortadan kalkar.

**3. Compose Dosyası İkiye Bölünür**
- `docker-compose.core.yml` → orchestrator, rabbitmq, postgres, minio, crawler, db
- `docker-compose.worker.yml` → cua, llm, vlm (profil bazlı)
- `.env.generated` → orchestrator/rabbitmq/minio/postgres adresleri otomatik yazılır

**3.1. Yerel Linux Desteği ve Tek Komutla Ayağa Kaldırma**
- Şu an geliştirme akışı ağırlıklı olarak Windows/PowerShell betikleriyle yürütülüyor; buna ek olarak Linux yerel geliştirme ortamı için de aynı seviyede çalıştırma altyapısı sağlanacak.
- Hedef: Linux üzerinde `docker compose` + `.env.generated` + shell script ile core servislerin tek komutla ayağa kalkması.
- Windows için mevcut `.ps1` başlatma akışı korunacak; Linux için eşdeğer `.sh` başlatma/sağlık kontrol betikleri eklenecek.
- Ortak amaç: Windows yerel geliştirme, Linux yerel geliştirme ve uzak Vast.ai worker kurulumlarının aynı değişken isimleri ve aynı Compose ayrımı üzerinden yönetilmesi.
- Bu değişiklik tamamlandığında tezde Bölüm 3.1'deki çalışma ortamı paragrafı güncellenecek. Konum: `tez.md` → `## 3.1 Çalışma Ortamı ve Donanım Altyapısı`.

**4. Node Registry Kalıcı Hale Getirilir**
Şu an `node_registry.py` bellekte tutuyor. Eklenmesi gerekenler:
- `role`, `ssh_host`, `ssh_port`, `tunnel_mode` (ssh / wireguard)
- `public_callback_host`, `public_callback_port`
- `status`, `last_heartbeat`, `provision_log`

**Var olan altyapı (bunların üstüne inşa edilecek):**
- `scripts/helper/windows/bridge.ps1` — SSH reverse tunnel supervisor
- `scripts/node_bridges.example.json` — node konfigürasyon şablonu
- `docs/wireguard_setup.md` — VPN modeli
- `scripts/linux/cua.sh` — bootstrap mantığının büyük kısmı hazır

#### Kritik Ayrım
> Orchestrator **çalışma zamanı** işleri yönetir.
> Provisioner **altyapıyı** kurar.
> SSH anahtarları Orchestrator container'ına koyulmaz; ayrı bir provisioner service/script işletir.

### Tezde Güncellenecek Paragraf
**Konum:** `tez.md` → Bölüm 2.1, "Container Tabanlı Dağıtım (Docker)" paragrafı son cümlesi:

> ~~"IP ve port yapılandırmalarının her oturumda manuel olarak ayarlanmasını gerektirmektedir. Söz konusu operasyonel zorluk, 6. bölümde bir sınırlama olarak tartışılacaktır."~~

**Yeni yazılacak:**
> "Mevcut prototipte yeni GPU düğümleri manuel olarak yapılandırılmaktadır. Önerilen genişletmede ise tek bir `provision_node` komutuyla SSH üzerinden uzak makineye bağlanılması, Docker kurulumu, servis başlatma ve tünel açma adımlarının otomatikleştirilmesi hedeflenmektedir. Vast.ai IP'lerinin dinamik yapısı nedeniyle oluşan yaşam döngüsü yönetimi zorluğu, çözüm önerileriyle birlikte 6. bölümde ele alınacaktır."

**Ek tez atfı:**
- Konum: `tez.md` → Bölüm 3.1, "Geliştirme ortamı..." ve "Yerel Compose yapılandırması..." paragrafları.
- Konum: `tez.md` → Bölüm 3.9, "Dağıtım ve Operasyon" bölümü.
  - Tek komutla ayağa kaldırma, Linux yerel destek, core/worker Compose ayrımı ve uzak GPU worker kurulum akışı kod tarafında tamamlandığında bu bölüm güncellenecek.
  - Özellikle servis tablosu, yapılandırma paragrafı ve Şekil 3.14 dağıtım görünümü yeni dağıtım mimarisine göre revize edilecek.
- Kod tarafında Linux yerel başlatma ve tek komutlu kurulum tamamlanmadan `tez.md` içine bu gelecek hedefleri yazılmayacak; mevcut tez metni yalnızca çalışan/var olan altyapıyı anlatacak.

---

## 3. CUA: LLM'in Rolü ve Yönlendirilmiş Ajan Tasarımına Geçiş

### Gerçek Mimari (Koddan Doğrulandı)

CUA'da LLM **karar mekanizması değil**, durumlar arası **çıkarım aracı** olarak konumlandırılmıştır. Akışın kendisi Python kodu tarafından yönetilmektedir:

| Karar | Kim alıyor? |
|---|---|
| Arama mı yap, URL mi ziyaret et? | Python (`plan_node` — `if/else` sayıçlar) |
| Durdulmalı mı? | Python (`evaluate_node` — tamamen sayıç karşılaştırması, LLM yok) |
| Tarayıcı eylemleri | Python (doğrudan `browser.search()`, `browser.extract_page()`) |
| Hangi arama sorgusunu kullan? | LLM (`model.generate_query_plan()`) |
| Bu makale kabul edilmeli mi? | LLM (`model.assess_article_quality()`) |
| Makale analizi | LLM (`model.analyze_article()`) |
| Final rapor sentezi | LLM (`model.synthesize_report()`) |

### Yapılacak Proje Değişikliği
Mevcut mimari zaten büyük ölçüde yönlendirilmiş bir yapıdadır. İyileştirme şunólarda yapılabilir:

- `evaluate_node` tamamen LLM'siz çalışıyor; bu doğru. Ancak durdurma kriter parametreleri (`max_cycles`, `max_searches`) şu an Orchestrator'dan değil config dosyasından geliyor. Bunların Orchestrator üzerinden dinamik geçirilmesi denetim kapasitesini artırır.
- `assess_article_quality` LLM kararı şu an binary (accept 0/1). Daha sönüş bir derecelendirme (skor + eşlik parametresi) geliştirilebilir.
- `generate_query_plan` LLM çıktısını doğrudan kullanıyor; mevcut guardrail sistemi (\_query\_too\_weak, fallback) iyi. Genisletilebilir.

### Tezde Güncellenecek Paragraf
**Konum:** `tez.md` → Bölüm 2.5 ve Bölüm 3 CUA mimarisi:

> Geçerli yazı doğru: "CUA'nın iç mimarisi Bölüm 3'te ele alınacaktır." — Bunu koruyun. Bölüm 3'te LLM'in çıkarım aracı, Python'un akış yöneticisi olduğu açıkça belirtilecek.

---

## 4. CUA: LLM Çağrılarını Birleştirme ve Daha Agentic Tasarım

### Mevcut Durum (Koddan Doğrulandı)

Her ziyaret edilen URL için **2 ayrı LLM çağrısı** yapılıyor:

1. `assess_article_quality()` → ayrı prompt, ayrı LLM çağrısı → `{"accept": 0/1, ...}` JSON döndürüyor
2. Eğer `accept == 1` ise → `analyze_article()` çağrılıyor → `analyze_article_text()` + her görsel için `analyze_image_url()` (ayrı çağrılar)

Yani kabul edilen bir makale için: **1 kalite + 1 metin + N görsel = 2+N LLM çağrısı**.

Ayrıca mevcut sistemde LLM gerçek anlamda **agentic değil**: browser-use'un kendi akışını yönetmesi yerine, Python `graph.py`'nin belirlediği aksiyonlar (`search`, `visit`, `complete`) doğrultusunda sadece belirli noktalarda inference yapıyor. Tool call mekanizması kullanılmıyor.

### Önerilen Değişiklik

> **Not:** Aşağıdaki öneri mevcut kodun tam incelenmesine dayanmaktadır ancak bazı detaylar optimize edilebilir.

**A. Kalite Değerlendirmesi + Analiz → Tek LLM Çağrısına Birleştirme**

Öneri: `assess_article_quality` ve `analyze_article_text` tek bir prompt'a birleştirilir. Model şu şekilde çalışır:

```
1. Makale metnini + filtrelenmiş görsellerden max 3 tanesini al (browser-use çıktısından)
2. Tek prompt gönder:
   - "Bu makale kabul kriterlerini karşılıyor mu? Önce değerlendir.
      Eğer HAYIR (accept=0) ise sadece ret gerekçesini yaz ve dur.
      Eğer EVET (accept=1) ise devam et ve tam analizi yap."
3. Çıktıdan regex ile önce accept değerini parse et
4. accept=0 → makaleyi reddet, geçersiz_makaleler.jsonl'e {id, url, reason} ekle, döngü sona er
5. accept=1 → aynı LLM yanıtından analiz alanlarını parse et
```

**Sağladığı Faydalar:**
- Kabul edilmeyecek makaleler için `analyze_article_text` çağrısı hiç yapılmaz → token tasarrufu
- 2 çağrı → 1 çağrı (görseller hariç)
- `geçersiz_makaleler.jsonl` → reddedilen makalelerin izlenebilirliği artar

**B. Daha Agentic Yapıya Geçiş**

Uzun vadede LLM'in `search/visit/complete` kararlarını da kendisinin vermesi hedefleniyor (şu an Python `plan_node` veriyor). Bu için:
- `plan_node` içindeki Python `if/else` mantığının bir kısmı LLM prompt'una taşınır
- Tool call / function calling mekanizması eklenir (`browser_search`, `browser_visit`, `stop` araçları)
- LLM `{"tool": "browser_search", "query": "..."}` tarzı çıktı üretir, Python bu çıktıyı execute eder
- Guardrail'ler (max_cycles, max_searches, blacklist) Python tarafında korunur

**C. Görsel Optimizasyonu**

- Browser-use'dan zaten filtrelenmiş görseller geliyorsa max 3'ü tek multimodal çağrıda değerlendirmeye ekle
- Mevcut `analyze_image_url` döngüsü görsel sayısı kadar ayrı çağrı yapıyor; bunları batch'e al veya metin analiziyle birleştir

### Bağlı Tez Bölümü
**Konum:** `tez.md` → Bölüm 3 CUA iç mimarisi + Bölüm 6 Sınırlamalar/Gelecek Çalışmalar

---

## 5. Kod İyileştirme (Refactoring) ve Veritabanı Tezi

### A. Model Handler OOP Düzenlemesi
**Durum:** `model_handler.py` dosyası şu anda 900+ satırlık monolitik bir yapıda (hem LM Studio, hem Transformers fallback, hem de `assess_article`, `analyze_article`, `generate_query_plan` gibi tüm iş mantıkları aynı sınıfta).
**Yapılacaklar:**
- Sınıf yapısı Single Responsibility Principle (SRP) kurallarına göre bölünmeli.
- İstemci katmanı (LMStudio/Transformers/OpenAI wrapper) ayrı bir sınıfa (`LLMClient` veya `InferenceEngine`), iş mantığı (prompt oluşturma ve JSON parse) ayrı sınıflara (`ArticleAnalyzer`, `AgentPlanner`) taşınmalı.
- Bu refactor işlemi, Madde 4'teki "çağrıları birleştirme" optimizasyonuyla eşzamanlı yapılmalıdır.

### B. PostgreSQL'in Tezde Detaylandırılması
**Durum:** Bölüm 2.6'da pgvector sayesinde PostgreSQL'in vektör yeteneklerinden bahsedildi, ancak ana tablo yapısı (news, vlm_analysis, llm_analysis) ve asenkron `asyncpg` kullanım mantığı henüz teze işlenmedi.
**Teze Eklenecek Yer:** 
- **Bölüm 3.x (DB Düğümü ve Depolama Mimarisi)** başlığı altında:
  - `news_id` (URL SHA-256) üretimi.
  - State takibi (`vlm_processed`, `llm_processed` flag'leri ile haberin analiz zincirindeki konumu).
  - CUA çıktıları için eklenen `source_type='agent_surface'` ayrımı.
  - `asyncpg` havuzu ile eşzamanlı asenkron kuyruk tüketimi (RabbitMQ'dan gelen görevlerin asenkron işlenmesi).

---

## 6. Yeni Özellik Planı: Deep Research Agent Modülü

### Fikir ve Kapsam
Mevcut CUA'yı (Computer Using Agent) "surface_agent" (yönlendirilmiş/daha kısıtlı araç seti) olarak koruyup, yanına daha derinlemesine analiz yapabilen bir **Deep Research Agent** alt modülü eklemek.

- **Bağımsız Alt Modül:** CUA'nın temel işleyişini bozmadan, Orchestrator'dan gelen görev tipiyle (örn. `mission_type: deep_research`) tetiklenebilir.
- **Tam Otonom Yapı:** Madde 4'te bahsedilen "Tam Agent Özellikleri" (Tool call ile kararları kendisinin vermesi, browser-use'u native bir agent gibi kullanıp serbest web gezintisi yapması) doğrudan bu modülde uygulanabilir.
- **Odak Noktası:** Yüzey haber toplamaktan ziyade belirli bir hipotezi doğrulamak, PDF raporları okumak, kaynakları çapraz kontrol etmek ve daha uzun soluklu "araştırmacı gazeteci" veya "analist" rolü üstlenmek.

**Tasarım Kararı (Tartışılacak):** Bu yeni modül, `cua/agent/` altında yeni bir graph dosyası (`deep_graph.py`) olarak mı konumlandırılmalı, yoksa bağımsız yeni bir Docker servisi (Node) olarak mı tasarlanmalı?

### Bağlı Terminoloji Kararı: `surface` / `agent_surface`

Mevcut kodda CUA görevi `mode='surface'`, DB kayıt ayrımı ise `source_type='agent_surface'` olarak geçiyor. Tez bu aşamada bu etiketleri kodda olduğu gibi kullanacak.

Kod tarafında Deep Research Agent veya daha agentic yapı eklendiğinde bu isimlendirme yeniden değerlendirilecek:
- `surface` korunabilir,
- `surface_agent` gibi daha açıklayıcı bir ada taşınabilir,
- ya da görev tipleri `mission_type` / `agent_type` gibi daha genel bir alanla ayrıştırılabilir.

Bu karar kodda uygulanmadan tezde terminoloji değiştirilmeyecek. Değişiklik yapılırsa güncellenecek yerler:
- `tez.md` → Bölüm 3.3, `AGENT_SURFACE` ve `agent_surface_articles` anlatımı.
- `tez.md` → Bölüm 3 CUA alt bölümü yazıldığında CUA görev tipi ve DB kayıt ayrımı.
- `tez.md` → Bölüm 4 CUA gösterimi ve örnek çıktı adlandırmaları.


---

## 7. Orchestrator Dayanıklılığı ve Tek Hata Noktası

### Mevcut Durum

Tezde şu an doğru olarak Orchestrator'ın yıldız topolojisinde merkezi düğüm olduğu ve tek hata noktası oluşturduğu yazıyor. Bu, mevcut kod durumunun doğru yansımasıdır; tez metninden kaldırılmayacak.

### Yapılacak Proje Değişikliği

Bu sınırlamayı azaltmak için ileride şu mimari geliştirmeler değerlendirilecek:
- `NodeRegistry` ve pipeline task durumlarının bellek yerine kalıcı bir depoda tutulması.
- Orchestrator yeniden başladığında aktif/pending görevlerin geri yüklenmesi.
- Birden fazla Orchestrator örneği için lider seçimi veya aktif-pasif çalışma modeli.
- RabbitMQ ve DB bağlantı durumlarına göre daha açık degraded/healthy durum modelinin tanımlanması.

### Tezde Güncellenecek Yer

- `tez.md` → Bölüm 3.2, yıldız topolojisi ve tek hata noktası paragrafı.
- `tez.md` → Bölüm 6, sınırlamalar ve gelecek çalışmalar.


*Son güncelleme: 2026-05-18*
