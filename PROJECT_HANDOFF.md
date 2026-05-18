# Bitirme Projesi - Güncel Devralma Handoff

Bu dosya, önceki chat dökümleri ve mevcut repo durumu üzerinden hazırlanmış güncel devralma notudur. Amaç yeni gelen geliştiricinin veya ajan oturumunun projeyi hızlıca kavraması, hangi kararların neden alındığını bilmesi ve doğru dosyalardan başlamasıdır.

Son güncelleme bağlamı: 13 Mayıs 2026. Chat dökümü sıralı değildi; kronoloji içerikteki tarih/saat ve konu akışından çıkarıldı.

## 1. Projenin Kısa Tanımı

Bu proje dağıtık, node tabanlı bir haber toplama ve analiz sistemidir. Merkezde `orchestrator` vardır; diğer node'lar ona kayıt olur, heartbeat gönderir ve görevleri ondan alır. Haberler crawler/CUA tarafından bulunur, DB node tarafından PostgreSQL + MinIO'ya alınır, VLM görselleri yorumlar, LLM metin/görsel bağlamından nihai analiz üretir.

Ana hedef sadece haber çekmek değil; toplanan haberleri kaynak, görsel, sentiment, entity, keyword ve ileride semantik arama katmanlarıyla analiz edilebilir hale getirmektir.

## 2. Güncel Mimari Kararları

### Orchestrator merkezdir

- Tüm node'lar `Register` ve `Heartbeat` ile Orchestrator'a bağlanır.
- Orchestrator node durumunu, task akışını, RabbitMQ kuyruklarını ve admin HTTP panelini yönetir.
- Panel varsayılan olarak `http://127.0.0.1:8088` üzerinden izlenir.
- Başlangıç için en önemli dosyalar:
  - `orchestrator/main.py`
  - `orchestrator/services/pipeline_manager.py`
  - `orchestrator/services/node_registry.py`
  - `orchestrator/services/admin_http.py`
  - `orchestrator/services/rabbitmq_manager.py`

### Crawler artık inbound gRPC server değildir

Crawler için kritik karar: gRPC kaldırılmadı, sadece eski inbound crawler gRPC server modeli terk edildi.

Eski model:

```text
Orchestrator -> Crawler gRPC server -> ExecuteCrawl
```

Güncel model:

```text
Crawler -> Orchestrator.GetCrawlTask
Crawler -> Orchestrator.ReportCrawlResult
```

Nedeni: Vast.ai ve dağıtık ortamda crawler node'ları NAT/firewall arkasında kalabilir. Orchestrator'ın crawler'a dışarıdan bağlanması kırılgan. Poll modelde crawler dışarıya doğru Orchestrator'a bağlanır; bu canlı kurulumda daha sağlamdır.

Bakılacak dosyalar:

- `crawler/main.py`
- `crawler/services/grpc_client.py`
- `crawler/config.py`
- `crawler/Dockerfile`
- `scripts/vast_crawler_host_guarded.sh`

Not: `crawler/services/grpc_server.py` eski push modele ait olduğu için kaldırıldı. Bu, gRPC'nin kaldırıldığı anlamına gelmez.

### RabbitMQ ack/nack semantiği önemlidir

RabbitMQ sadece mesajı taşır; "bu iş başarıyla işlendi mi?" kararını consumer ack/nack ile verir.

CUA tarafında alınan karar:

- Mesaj `auto_ack=False` ile alınır.
- İş gerçekten bitip sonuç `agent_results` kuyruğuna publish edilince `ack` atılır.
- İşleme veya publish patlarsa `nack(requeue=True)` ile görev geri kuyruğa döner.
- CUA aynı anda tek task işler; aktif iş varken yeni RabbitMQ mesajı çekmez.

Bu kararın sebebi: Önceki davranışta CUA mesajı alır almaz ack ederse browser/model/result publish hatasında görev kayboluyordu.

Bakılacak dosyalar:

- `cua/main.py`
- `cua/services/rabbitmq_consumer.py`
- `orchestrator/services/rabbitmq_manager.py`

Uyarı: `TODO.md` içinde Orchestrator result consumption için hâlâ bir hardening işi var. Orchestrator tarafında bazı result mesajları downstream işlem başarıya ulaşmadan ack edilebiliyor; bu ileride düzeltilmeli.

### DB storage DB node tarafında olmalı

Son topoloji kararı: PostgreSQL ve MinIO doğal olarak DB node tarafındadır.

Doğru dağılım:

```text
Orchestrator makinesi: orchestrator + rabbitmq + admin panel
DB makinesi: postgres + minio + db node
Diğer Vast/GPU makineleri: crawler, vlm, llm, cua
```

Pratikte yerel geliştirme için PostgreSQL/MinIO orchestrator makinesinde compose ile açılabilir, ama final mimari DB-hosted storage modelidir.

Sonuçları:

- VLM MinIO görsellerini okuyacaksa DB makinesindeki MinIO `9000` erişilebilir olmalı.
- Orchestrator paneli DB arama/istatistik gösterecekse remote PostgreSQL'e erişebilmeli.
- `scripts/vast_db_host_guarded.sh` storage servislerini kurmaktan çok DB node'u hazır storage'a bağlama odaklıdır; storage'ın nerede kalktığı env ile net verilmeli.

Bakılacak dosyalar:

- `db/main.py`
- `db/services/postgres_manager.py`
- `db/services/minio_manager.py`
- `docs/database_schema.md`
- `docs/minio_storage.md`
- `scripts/vast_db_host_guarded.sh`

## 3. Kronolojik Karar Özeti

### 4 Mayıs 2026 - CUA task güvenilirliği

- CUA'nın standalone ve orchestrator'a bağlı akışlarında aynı stop limitlerini kullanması hedeflendi.
- `max_cycles`, `max_searches`, `max_articles` parametrelerinin task üzerinden taşınması kararlaştırıldı.
- CUA'nın tek seferde tek RabbitMQ task işlemesi kararlaştırıldı.
- CUA result formatının Orchestrator'ın beklediği wrapper formatında olması gerektiği netleşti: `task_id` + `json_data`.
- Heartbeat enum uyumu düzeltildi: idle/busy durumu Orchestrator tarafından doğru görülecek.

### 4 Mayıs 2026 - Vast.ai ve CUA çalıştırma denemeleri

- CUA standalone için Orchestrator/RabbitMQ gerekmediği netleştirildi; sadece LLM endpoint + Playwright/browser gerekir.
- `duckduckgo` Vast ortamında Google'a göre daha stabil kabul edildi, çünkü Google CAPTCHA/rate-limit çıkarabiliyor.
- vLLM endpoint için `LMSTUDIO_URL=http://127.0.0.1:<port>/v1` formatı benimsendi.
- RabbitMQ `guest/guest` kullanıcısının uzak makineden çalışmayacağı hatırlatıldı; dağıtık senaryoda ayrı kullanıcı açılmalı veya doğru network/bridge kurulmalı.
- Vast portal/caddy bazı makinelerde `1234` portunu kullanabildiği için `VLLM_PORT=1235` gibi alternatif port kullanımı gerekti.
- vLLM manuel pip kurulumunda CUDA wheel uyuşmazlıkları görüldü; uzun vadede Docker-first yaklaşım daha doğru kabul edildi.

### 11 Mayıs 2026 - CUA yeniden inceleme ve Docker kararı

- CUA için nihai yön: önce davranış stabilize edilecek, sonra Dockerize edilecek.
- vLLM pip/CUDA sorunlarının Docker imajı içinde sabitlenmesi gerektiği kararlaştırıldı.
- O aşamada "Docker'a hemen geçmeyelim; önce CUA loop'a giriyor mu, limitler çalışıyor mu, orchestrator bağlı modda doğru task mı geliyor" yaklaşımı seçildi.

### 11 Mayıs 2026 - CUA mode kararı

- `research/deep research` modu geçici olarak kapsam dışı bırakıldı.
- Güncel CUA'nın ana üretim yolu `surface` agent task'tır.
- Orchestrator'ın CUA'ya `mode: research` göndermesi riskli bulundu; güncel kodda `_fan_out_to_cua` artık `mode: surface` üretir.
- CUA'ya yanlışlıkla `research` gelirse güvenli `FAILED` sonucu dönmeli, queue retry döngüsüne sokmamalı.
- Query stratejisi için "tam deterministik" yaklaşım çok katı bulundu.
- Kabul edilen yaklaşım: LLM önerili + guardrail kontrollü hibrit query stratejisi.
  - LLM yeni ve anlamlı query önerirse kullanılır.
  - Aynı normalized query tekrar aratılmaz.
  - Çok genel/boş query veya tekrar durumunda sistem kontrollü fallback/çeşitlendirme yapar.
  - `max_searches`, `max_cycles`, `max_articles` her zaman nihai frenlerdir.

### 12 Mayıs 2026 - DB storage kararı

- PostgreSQL ve MinIO'nun DB node tarafında olması gerektiği netleştirildi.
- Orchestrator + RabbitMQ merkezi, DB storage ise DB makinesi modeli benimsendi.
- Yerel geliştirmede storage'ı orchestrator makinesinde açmak pratik olabilir ama final topoloji olarak görülmemeli.

### 12 Mayıs 2026 - Crawler poll model ve dar kapsamlı düzeltmeler

- Crawler'ın Orchestrator'dan gelen `urls` listesini dikkate alması sağlandı.
- `urls` boşsa eski default kaynak davranışı korunur.
- Domain/root verilirse sadece o domain için arama yapılır.
- Doğrudan haber URL'si verilirse direkt işlenir.
- `task_id` artık crawler içinde yeniden üretilmez; Orchestrator'dan gelen `task_id` ile `ReportCrawlResult` gönderilir.
- Her crawl task başında sonuç state'i temizlenir.
- Tek bozuk haber batch'i tüm görevi düşürmesin diye partial-failure tolerant gather yaklaşımı kullanıldı.
- gRPC readiness/register başarısı görülmeden polling'e geçilmemesi hedeflendi.

### 12 Mayıs 2026 - Ölçekleme ve guarded script kararları

- Birden fazla crawler varsa hepsinin aynı kaynaklara bakmaması gerektiği açık TODO olarak yazıldı.
- İleride Orchestrator merkezi assignment/queue/state ile crawler'lara disjoint kaynak/domain batch dağıtmalı.
- CUA guarded scriptlerine benzer şekilde crawler için `scripts/vast_crawler_host_guarded.sh` eklendi.
- Genel hedef: önce bir "adam gibi çalışan", korumalı guarded kurulum yolu kanıtlansın; sonra manuel paket/kurulum yolları azaltılıp Docker-first modele geçilsin.

## 4. Güncel Modül Durumu

### Orchestrator

Görevleri:

- Node register/heartbeat.
- Crawler poll task servis etme.
- CUA tasklarını `agent_tasks` kuyruğuna basma.
- CUA sonuçlarını `agent_results` üzerinden alma.
- VLM/LLM/DB pipeline state yönetimi.
- Admin panel ve storage backup.

Hızlı bakılacak yerler:

- `orchestrator/main.py`: süreç giriş noktası, admin command loop, CUA result dispatch, crawler poll callback.
- `orchestrator/services/pipeline_manager.py`: fan-out, CUA surface publish, DB publish, pipeline state.
- `orchestrator/services/admin_http.py`: panel endpointleri.
- `orchestrator/services/storage_backup.py`: PostgreSQL/MinIO backup akışı.
- `orchestrator/services/rabbitmq_manager.py`: queue publish/consume.

Riskler:

- Eski push crawler path izleri bazı fonksiyonlarda durabilir; güncel canlı crawler akışı poll modeldir.
- Result mesajlarında ack/downstream başarı sıralaması için `TODO.md` hardening maddesi önemlidir.

### Crawler

Görevleri:

- Haber URL/domain/task bazlı crawl.
- Google/DuckDuckGo kaynaklı link bulma.
- İçerik, görsel URL ve video URL çıkarma.
- Orchestrator'a `ReportCrawlResult` gönderme.

Hızlı bakılacak yerler:

- `crawler/main.py`: ana crawl mantığı, URL normalizasyonu, task başına state reset.
- `crawler/services/grpc_client.py`: `Register`, `Heartbeat`, `GetCrawlTask`, `ReportCrawlResult`.
- `crawler/config.py`: distributed/standalone ayarları.
- `scripts/vast_crawler_host_guarded.sh`: Vast kurulumu ve korumalı başlatma.

Güncel davranış:

- Distributed modda crawler port açmaz.
- `urls` verilirse o hedefler işlenir.
- `urls` boşsa default kaynaklar kullanılır.

Riskler:

- Google CAPTCHA hâlâ gerçek risk.
- Çoklu crawler ölçeklemede merkezi disjoint assignment henüz yok.

### CUA

Görevleri:

- Statik crawler'ın kaçırabileceği haberleri agent/browser ile bulmak.
- Surface agent olarak arama, ziyaret, extraction, kalite değerlendirme ve rapor üretmek.
- Sonucu `agent_results` kuyruğuna wrapper formatında döndürmek.

Hızlı bakılacak yerler:

- `cua/agent/graph.py`: surface agent state machine, stop koşulları, pending URL ve query guardrail.
- `cua/agent/model_handler.py`: LLM bağlantısı, query plan, article quality, synthesize.
- `cua/agent/browser_tool.py`: browser-use/Playwright extraction.
- `cua/main.py`: node modu, active task guard, heartbeat lifecycle.
- `cua/services/rabbitmq_consumer.py`: `agent_tasks` consume, ack/nack, `agent_results` publish.
- `cua/test_local.py`: standalone surface test.
- `scripts/vast_cua_host_guarded.sh`: host üzerinde vLLM + CUA guarded kurulum.
- `scripts/vast_cua_allinone.sh` ve `cua/Dockerfile.allinone`: Docker all-in-one yol.

Güncel davranış:

- `test_local.py` sadece `surface` kabul eder.
- `run_agent()` `surface` dışı mode gelirse güvenli `FAILED` döndürür.
- `graph.py` limitleri task `params` içinden okur: `max_cycles`, `max_searches`, `max_articles`.
- CUA task state'inde `visited_urls`, `exclude_urls`, `exclude_domains`, `_pending_urls`, `_search_count` gibi alanlarla loop kontrolü vardır.
- Orchestrator `_fan_out_to_cua` `mode: surface` üretir.

Önemli karar:

- Deep research ileride yeniden yapılacak. Şu an production kabul edilen yol surface agent'tır.

Riskler:

- Surface çıktıları bazen `max_cycles_reached` ile biterken yine makale üretmiş olabilir; bu başarısızlık değil, stop reason olarak yorumlanmalı.
- CUA'nın browser/model tarafı gerçek web ve LLM davranışına bağlı olduğu için deterministic testler sınırlı.
- Query stratejisi ne tamamen LLM'e bırakılmalı ne de tamamen şablona kilitlenmeli.

### DB

Görevleri:

- PostgreSQL ve MinIO bağlantıları.
- Haber kayıtları.
- Görsel indirme ve MinIO path üretme.
- VLM/LLM analizlerini saklama.
- İleride semantik arama/embedding.

Hızlı bakılacak yerler:

- `db/main.py`
- `db/services/postgres_manager.py`
- `db/services/minio_manager.py`
- `db/services/embedding_manager.py`
- `docs/database_schema.md`
- `docs/minio_storage.md`

Riskler:

- Final topolojide remote PostgreSQL/MinIO erişimleri net port/env ister.
- Backup dosyaları `backups/` altında büyüyebilir.

### VLM

Görevleri:

- MinIO'daki görselleri okuyup görsel açıklama/obje/sentiment üretmek.
- Kısmi hata toleransı ile pipeline'ı düşürmeden sonuç döndürmek.

Hızlı bakılacak yerler:

- `vlm/main.py`
- `vlm/services/model_handler.py`
- `vlm/services/rabbitmq_consumer.py`
- `vlm/services/grpc_client.py`
- `scripts/vast_vlm_host_guarded.sh`

Riskler:

- GPU/VRAM uyumu.
- MinIO erişimi.
- Model adı ve quantization ayarları.

### LLM

Görevleri:

- Haber metni + VLM bağlamından summary, sentiment, keyword ve entity üretmek.
- Strict JSON benzeri çıktı üretmek.

Hızlı bakılacak yerler:

- `llm/main.py`
- `llm/services/model_handler.py`
- `llm/services/rabbitmq_consumer.py`
- `llm/services/grpc_client.py`
- `scripts/vast_llm_host_guarded.sh`

Riskler:

- Model çıktısı strict schema dışına çıkabilir.
- GPU/VRAM ve model backend seçimi deployment'ta kritik.

## 5. En Önemli Dizinler ve Ne İşe Yararlar

```text
orchestrator/   Merkezi kontrol, panel, pipeline, node registry, queue yönetimi.
crawler/        Poll model haber crawler; URL/domain/task bazlı crawl.
cua/            Browser kullanan surface agent; standalone ve node modları.
db/             PostgreSQL + MinIO node; kayıt, medya, embedding işleri.
vlm/            Görsel analiz node'u.
llm/            Metin/final analiz node'u.
proto/          Ana protobuf sözleşmesi ve generated Python çıktıları.
scripts/        Guarded host, Vast, bridge, build/update scriptleri.
docs/           Mimari, deployment, schema, RabbitMQ, gRPC, storage dokümanları.
backups/        Panel/script ile alınan PostgreSQL dump ve MinIO backup çıktıları.
.runtime/       Lokal runtime pid/log/bridge state dosyaları.
```

Devralan kişinin ilk bakması gereken dosyalar:

```text
PROJECT_HANDOFF.md
TODO.md
scripts/all.md
orchestrator/main.py
orchestrator/services/pipeline_manager.py
cua/agent/graph.py
cua/main.py
cua/services/rabbitmq_consumer.py
crawler/main.py
crawler/services/grpc_client.py
db/services/postgres_manager.py
docker-compose.yml
```

## 6. Çalıştırma ve Debug İçin Hızlı Komutlar

### Yerel orchestrator

```powershell
cd C:\Users\HP\Desktop\Projeler\Bitirme
.\scripts\orchestrator_host_guarded.ps1
```

RabbitMQ da compose ile kalksın:

```powershell
.\scripts\orchestrator_host_guarded.ps1 -StartRabbitWithCompose
```

RabbitMQ + PostgreSQL + MinIO + schema bootstrap:

```powershell
.\scripts\orchestrator_host_guarded.ps1 -StartRabbitWithCompose -StartStorageWithCompose -StopExistingOrchestrator
```

### Crawler Vast node

```bash
su - root
cd ~
curl -fsSL -o vast_crawler_host_guarded.sh \
  https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_crawler_host_guarded.sh
chmod +x vast_crawler_host_guarded.sh

ORCHESTRATOR_HOST=<ORCH_IP> \
ORCHESTRATOR_PORT=50051 \
./vast_crawler_host_guarded.sh
```

Eski crawler varsa ve bilerek durdurulacaksa:

```bash
STOP_EXISTING_CRAWLER=true ./vast_crawler_host_guarded.sh
```

### CUA standalone Vast node

Host guarded yol:

```bash
su - root
cd ~
curl -fsSL -o vast_cua_host_guarded.sh \
  https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_host_guarded.sh
chmod +x vast_cua_host_guarded.sh

CUA_RUN_MODE=standalone \
CUA_QUERY="Turkey economy 2026" \
./vast_cua_host_guarded.sh
```

Vast portal `1234` portunu kullanıyorsa:

```bash
VLLM_PORT=1235 CUA_RUN_MODE=standalone ./vast_cua_host_guarded.sh
```

Browser görünür gelsin:

```bash
CUA_RUN_MODE=standalone BROWSER_HEADLESS=false ./vast_cua_host_guarded.sh
```

Docker all-in-one yol:

```bash
cd ~
curl -fsSL -o vast_cua_allinone.sh \
  https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_allinone.sh
chmod +x vast_cua_allinone.sh
./vast_cua_allinone.sh
```

### CUA node modu

```bash
CUA_RUN_MODE=node \
ORCHESTRATOR_HOST=<ORCH_IP> \
RABBITMQ_HOST=<ORCH_IP> \
./vast_cua_host_guarded.sh
```

Uyarı: RabbitMQ başka makinedeyse `guest/guest` çoğu kurulumda uzaktan çalışmaz. Gerçek kullanıcı/parola veya doğru bridge/VPN gerekir.

### CUA local standalone test

```powershell
cd C:\Users\HP\Desktop\Projeler\Bitirme
$env:MODEL_NAME="Qwen/Qwen3.5-9B"
$env:LMSTUDIO_URL="http://127.0.0.1:1234/v1"
$env:SEARCH_ENGINE="duckduckgo"
$env:BROWSER_HEADLESS="true"

python -m cua.test_local `
  --mode surface `
  --query "Turkey economy 2026" `
  --max-articles 3 `
  --max-cycles 15 `
  --engine duckduckgo `
  --lmstudio-url "$env:LMSTUDIO_URL" `
  --output cua_test_result_surface.json
```

### Bridge helper

Doğrudan IP erişimi yoksa:

```powershell
.\scripts\open_vast_node_bridge.ps1 -VastHost <VAST_HOST> -VastSshPort <PORT>
```

Birden çok node için:

```powershell
Copy-Item .\scripts\node_bridges.example.json .\scripts\node_bridges.local.json
.\scripts\manage_node_bridges.ps1 -Action start
.\scripts\manage_node_bridges.ps1 -Action status
```

## 7. Proto ve Contract Kuralları

Ana sözleşme:

```text
proto/orchestrator.proto
```

Modül kopyaları:

```text
orchestrator/proto/orchestrator.proto
crawler/proto/orchestrator.proto
cua/proto/orchestrator.proto
db/proto/orchestrator.proto
vlm/proto/orchestrator.proto
llm/proto/orchestrator.proto
```

Proto değişirse:

```powershell
python compile_proto.py
```

Sonra tüm node importları kontrol edilmeli. Crawler/CUA guarded scriptleri bazı proto import kontrollerini kendileri yapıyor ama contract değişikliği yine merkezi dikkat ister.

## 8. Açık İşler ve Öncelik Sırası

En güncel açık işler `TODO.md` içindedir. Devralan kişinin önceliklendirmesi:

1. Orchestrator result consumption hardening: result mesajları downstream handling/DB publish başarılı olmadan ack edilmemeli.
2. Çoklu crawler assignment: Birden fazla crawler aynı default kaynakları taramamalı; Orchestrator disjoint batch/task dağıtmalı.
3. CUA surface path end-to-end stabilizasyonu: standalone + node mode + RabbitMQ ack/nack + node busy/idle.
4. Deep research'i geri açma: Mevcut research kodunu doğrudan açmak yerine gerçek agent loop olarak yeniden tasarlamak.
5. Guarded full-system script: preflight, port/process validation, cleanup on failure, no half-running services.
6. Docker-first deployment: vLLM/CUA CUDA sorunlarını image içinde sabitleyip manuel venv yollarını azaltmak.

## 9. Bilinen Tuzaklar

- `docs/local_dev_guide.md` içinde eski `FilteredCrawler.py` referansları var; güncel crawler entrypoint `crawler/main.py`.
- `handoff_all.md` genel mimari için yararlı ama CUA'nın güncel "surface-only" kararını ve DB-hosted storage kararını tam yansıtmayabilir.
- CUA `research` belgelerde anlatılıyor olabilir; güncel üretim yolu `surface`.
- RabbitMQ `guest/guest` localhost dışı kullanımlarda çalışmayabilir.
- Vast template üzerinde `1234` portu dolu olabilir; `VLLM_PORT=1235` gibi alternatif kullanılmalı.
- vLLM pip kurulumu CUDA/runtime uyuşmazlığı çıkarabilir; Docker all-in-one veya sabit image uzun vadede daha doğru.
- Crawler Google CAPTCHA'ya düşebilir; `duckduckgo`, headful browser, persistent profile ve browser type denemeleri debug amaçlıdır, kesin çözüm değildir.
- Backup zip/dump dosyaları `backups/` altında büyüyebilir.
- `.venv-orch`, `.runtime`, `backups` ve `temp_browser_use` gibi dizinler repo okumasında gürültü yaratır; hızlı aramada `rg` kullanırken gerekirse dışla.

## 10. Devralan İçin İlk 30 Dakika Planı

1. `git status --short` çalıştır; mevcut kullanıcı değişikliklerini not al, geri alma.
2. `TODO.md` ve bu dosyayı oku.
3. CUA üzerinde çalışacaksan önce `cua/agent/graph.py`, `cua/main.py`, `cua/services/rabbitmq_consumer.py`, `orchestrator/services/pipeline_manager.py` dosyalarını birlikte oku.
4. Crawler üzerinde çalışacaksan önce `crawler/main.py`, `crawler/services/grpc_client.py`, `orchestrator/main.py` poll callback kısmını oku.
5. Deployment üzerinde çalışacaksan `scripts/all.md` ve ilgili `scripts/vast_*_host_guarded.sh` dosyasından başla.
6. Proto veya queue formatına dokunacaksan tüm node'ların aynı contractı kullandığını doğrula.
7. Gerçek web/LLM testleri pahalı ve değişken olduğu için önce `python -m py_compile` ve küçük limitli smoke test ile ilerle.

## 11. Tek Cümlelik Durum Özeti

Sistem artık Orchestrator merkezli, crawler poll model kullanan, CUA tarafında surface agent yolunu stabilize etmeye odaklanan, storage'ı DB node tarafında konumlandırmayı hedefleyen ve canlı kurulumda guarded scriptleri ana güvenli yol kabul eden dağıtık haber analiz projesidir.
