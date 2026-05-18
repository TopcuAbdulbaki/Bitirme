# 1.GİRİŞ

Günümüzün bilgi yoğun dijital ekosisteminde, haber ve veri akışının hacmi geleneksel izleme yöntemlerinin kapasitesini çoktan aşmış durumdadır. Özellikle uluslararası ilişkiler, jeopolitik gelişmeler ve ekonomik dalgalanmalar gibi çok boyutlu konularda, farklı coğrafyalardaki onlarca haber kaynağını eş zamanlı olarak takip etmek, toplanan verileri anlamlandırmak ve eyleme dönüştürülebilir çıktılar üretmek üstelik bunu dil bariyerlerine rağmen yapmak insan gücüyle sürdürülebilir bir süreç olmaktan çıkmıştır. Manuel haber taraması tekil kaynak bağımlılığı, kısıtlı zaman penceresi ve analiz tutarsızlığı gibi yapısal sorunları beraberinde getirmektedir [şuraya atıf verilebilir — Reuters Institute Digital News Report, 2024].

Bu sorun alanına geleneksel yazılım mühendisliği perspektifinden bakılırsa, çözüm genellikle bir web kazıma (web scraping) aracı ve ardına eklenen basit bir doğal dil işleme (NLP) boru hattından ibarettir. Ancak bu yaklaşım iki temel eksiklikle maluldür: Birincisi, kazıma araçları yalnızca önceden tanımlanmış kaynaklardan veri toplayabilir ve beklenmedik kaynaklara uyum sağlayamaz. İkincisi, toplanan verilerin bağlamsal analizi — örneğin, bir haberin jeopolitik önemini değerlendirme veya birden fazla kaynaktaki bilgileri çapraz doğrulama — statik kurallarla değil, derin bir anlayış ve analiz ile mümkündür.

Son yıllarda özellikle transformer mimarisinin kullanımıyla büyük dil modellerinin (LLM) hızlı gelişimi, bu anlama boşluğunu kapatacak yeni bir paradigma sunmuştur. Özellikle LLM tabanlı otonom ajanlar — yani dış araçları kullanarak, kendi başlarına plan yapıp uygulayabilen(ReAct) yapay zekâ sistemleri — normalde çok vakit alabilecek ve yoğun emek gerektiren birçok iş kalemi için umut verici sonuçlar sergilemekte bu sayede saf insan gücünü/kaynağını daha verimli olacağı alanlara çekebilecek bir düzlem oluşturmaktadır [şuraya atıf verilebilir — Yao, S. et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." https://arxiv.org/abs/2210.03629]. Bu ajanlar, bir insanın web tarayıcısında yaptığı arama → okuma → değerlendirme → sentezleme döngüsünü otonom olarak gerçekleştirebilmekte; üstelik bunu çok daha geniş bir kaynak havuzunda ve çok daha kısa sürede yapabilmektedir [şuraya atıf verilebilir — Significant Gravitas. "AutoGPT." https://github.com/Significant-Gravitas/AutoGPT]. Bu tür sistemler karakutu olduğundan ve veri yanlılığı/önyargı(bias) gibi faktörlerden dolayı kritik mevzularda karar mercii haline gelmesi günümüz teknolojisi/konjonktüründe mümkün olmasa da karar-destek sistemi olarak hız, esneklik ve ölçeklenebilirlik kazandırma açısından olmazsa olmaz bir araç haline gelmektedir.

Bu tez çalışmasında, yukarıda özetlenen iki ihtiyacı — geniş kapsamlı ve ölçekli otomatik veri toplama ve otonom yapay zekâ destekli araştırma — tek bir dağıtık sistem çatısı altında birleştiren bir platform geliştirilmiş olan proje ele alınmıştır. Geliştirilen sistem iki bütünleşik bileşenden oluşmaktadır:

1. **Dağıtık Haber Toplama ve Analiz Boru Hattı (Pipeline):** Çoklu uluslararası haber kaynaklarını periyodik olarak tarayan, toplanan haberleri yapılandırılmış biçimde depolayan ve her bir haber üzerinde görsel dil modeli (VLM) ile büyük dil modeli (LLM) aracılığıyla otomatik analiz (özetleme, duygu analizi, varlık çıkarma) gerçekleştiren bir veri işleme zinciri. Bu kısım, sistemin "saf güç" kanadını oluşturarak geniş hacimli veriyi yüksek verimlilikle işlemektedir.

2. **Otonom Araştırma Ajanı (CUA — Computer Using Agent):** Belirli bir konu veya anahtar kelime seti verildiğinde, web üzerinde bağımsız olarak arama yapan, bulunan sayfaları ziyaret eden, içerikleri değerlendiren ve sonunda kapsamlı bir sentez raporu üreten LangGraph tabanlı otonom ajan. Bu bileşen, pipeline'ın aksine önceden tanımlanmış kaynaklara bağlı kalmaksızın, verilen konu etrafında keşifsel araştırma yürütmektedir.

Mevzubahis iki bileşen de mikro-servis mimarisi üzerine inşa edilmiştir. Bağımsız olarak geliştirilebilir, dağıtılabilir, ölçeklenebilir ve izlenebilir durumdadır. Sistem, merkezi bir orkestrasyon düğümü (Orchestrator) etrafında yıldız (star) topolojisinde organize edilmiş altı bağımsız düğümden (Crawler, Database, VLM, LLM, CUA ve Orchestrator) meydana gelmektedir. Düğümler arası iletişim, kontrol düzlemi için gRPC (Google Remote Procedure Call) [şuraya atıf verilebilir — https://grpc.io/docs/], veri düzlemi için ise RabbitMQ mesaj kuyruğu sistemi [şuraya atıf verilebilir — https://www.rabbitmq.com/docs] üzerinden sağlanmaktadır. Veritabanı katmanı, yapılandırılmış veri depolamanın yanı sıra pgvector eklentisi aracılığıyla vektör tabanlı anlamsal arama desteği sunmakta; medya dosyaları ise S3-uyumlu MinIO nesne deposunda saklanmaktadır.

Bu çalışmanın, klasik bir akademik araştırma projesinden farklı olarak, **çalışan bir ürün** ortaya koyma hedefiyle yürütüldüğünü vurgulamak gerekmektedir. Dolayısıyla tezin odak noktası, belirli bir modelin eğitilmesi veya bir algoritmanın iyileştirilmesi değil; birden fazla karmaşık alt sistemi tutarlı bir mimari çatı altında bir araya getiren, dağıtılabilir, hata toleranslı ve genişletilebilir bir yazılım sistemi tasarlayıp inşa etmektir. Bu bağlamda tez, yazılım mühendisliği disiplininin mimari tasarım, dağıtık sistemler, protokol tasarımı ve operasyonel mükemmellik boyutlarını ön plana çıkarmaktadır.

Tezin geri kalanı şu şekilde organize edilmiştir: 2. bölümde sistemin dayandığı teknolojik temeller ve ilgili literatür ele alınmaktadır. 3. bölümde sistemin mimari tasarımı, her bir düğümün iç yapısı, iletişim protokolleri ve dağıtım stratejisi ayrıntılı olarak sunulmaktadır. 4. bölümde sistemin çalışan gösterimleri ekran görüntüleri ve örnek çıktılarla desteklenmektedir. 5. bölümde sistem performans metrikleri ve değerlendirmeler paylaşılmakta; 6. bölümde ise sonuçlar, sınırlamalar ve gelecek çalışma önerileri tartışılmaktadır.

---

> [!NOTE]
> **Şekil 1.1** — Sistemin kuş bakışı kavramsal diyagramı burada yer alacaktır.
> İçerik: Sol kolda Pipeline (Crawler → DB → VLM → LLM zinciri), sağ kolda CUA otonom ajanı, ortada Orchestrator merkez düğümü. Her iki kol da Orchestrator'a bağlı yıldız yapısında gösterilecek.

# 2. GENEL KISIMLAR

Dağıtık boru hattı (pipeline) sistemleri, veriyi birden fazla düğüme yayarak toplama, dönüştürme ve depolama süreçlerini paralel biçimde yürütmeyi hedefleyen mimari yaklaşımlardır. Endüstride yaygın olarak ETL (Extract, Transform, Load) adıyla anılan bu kalıp, büyük veri platformlarından gerçek zamanlı akış sistemlerine kadar geniş bir uygulama yelpazesine sahiptir. Günümüzde bu alandaki çözümler, iş akışlarını tanımlayan bir orkestrasyon katmanı ile işi fiilen gerçekleştiren dağıtık işçi (worker) düğümlerinden oluşan iki katmanlı mimariler etrafında şekillenmektedir.

Bu mimari yaklaşımın endüstriyel örnekleri arasında iki sistem, geliştirilen proje ile yapısal benzerlikler taşımaktadır:

**Netflix Conductor** [şuraya atıf verilebilir — Conductor OSS, https://conductor-oss.org/], mikro-servis tabanlı iş akışı orkestrasyon motoru olarak tasarlanmıştır. Conductor'da merkezi bir orkestratör, JSON tabanlı iş akışı tanımları üzerinden görevleri planlar; işçi düğümler ise kuyruk mekanizmasıyla bu görevleri çekerek (poll modeli) yürütür. Bu yapı — merkezi koordinatör, görev kuyrukları ve bağımsız işçi düğümler — geliştirilen sistemin Orchestrator merkezli yıldız topolojisiyle doğrudan örtüşmektedir. Ancak Conductor genel amaçlı bir iş akışı motoru iken, bu projede haber toplama, yapay zekâ analizi ve otonom araştırma gibi alan-özgü görevler bütünleşik biçimde ele alınmaktadır.

**Temporal** [şuraya atıf verilebilir — Temporal Technologies, https://temporal.io/], dağıtık iş akışlarını dayanıklı durum (durable state) ve otomatik yeniden deneme (retry) mekanizmalarıyla yöneten bir orkestrasyon platformudur. İşçi düğümlerin uzak sunucularda bağımsız çalışması, merkezi sunucunun ise durumu takip edip hata durumlarında kurtarma sağlaması prensibi, projede Vast.ai üzerinde dağıtılan GPU düğümlerinin SSH köprüleriyle Orchestrator'a bağlanması modeliyle benzerdir. Temporal'ın sağladığı dayanıklılık garantileri, geliştirilen sistemde RabbitMQ'nun mesaj kalıcılığı (persistence) ve onay (acknowledgement) mekanizmalarıyla kısmen karşılanmaktadır.

Ancak bu endüstriyel çözümlerden farklı olarak, geliştirilen sistem yalnızca veri işleme boru hattı değil, aynı zamanda LLM tabanlı otonom araştırma ajanını (CUA) da aynı orkestrasyon çatısı altında barındırmaktadır. Bu hibrit yapı — yapılandırılmış pipeline ile keşifsel ajan davranışının tek bir dağıtık sistemde birleştirilmesi — projenin özgün mimari katkısını oluşturmaktadır.

Bu bölümde, sistemin üzerine inşa edildiği temel teknolojiler ve mimari paradigmalar ele alınacaktır: mikro-servis mimarisi ve dağıtık sistem kalıpları (2.1), gRPC ve Protocol Buffers ile servisler arası iletişim (2.2), RabbitMQ mesaj kuyruğu sistemi (2.3), büyük dil modelleri ve görsel dil modelleri (2.4), LangGraph tabanlı otonom ajan mimarisi (2.5), pgvector ile vektör tabanlı anlamsal arama (2.6), MinIO nesne depolama (2.7) ve web kazıma teknikleri (2.8).

## 2.1 Mikro-Servis Mimarisi ve Dağıtık Sistemler

Yazılım sistemlerinin mimarisi, geleneksel olarak tüm işlevlerin tek bir süreç (process) içinde çalıştığı **monolitik** yapılar üzerine inşa edilmiştir. Monolitik mimaride uygulamanın tüm bileşenleri (veri erişimi, iş mantığı, kullanıcı arayüzü) aynı kod tabanında derlenir ve tek bir birim olarak dağıtılır. Bu yaklaşım küçük ölçekli projeler için geliştirme kolaylığı sağlar. Ancak ne var ki sistem büyüdükçe ciddi sınırlamalar ortaya çıkmaktadır: herhangi bir bileşendeki değişiklik tüm uygulamanın yeniden derlenmesini ve dağıtılmasını gerektirir. Bileşenler arasındaki sıkı bağımlılık (tight coupling) bağımsız ölçeklemeyi engeller ve tek bir hata noktası yalnızca bir bileşeni değil pek muhtemel tüm sistemi çökertir [şuraya atıf verilebilir — Newman, S. (2021). *Building Microservices*, 2nd ed. O'Reilly].

**Mikro-servis mimarisi**, bu sınırlamalara yanıt olarak ortaya çıkan bir yaklaşımdır. Bu modelde sistem, her biri belirli bir iş alanından sorumlu, bağımsız olarak geliştirilebilen, dağıtılabilen ve ölçeklenebilen küçük servislere ayrılır. Söz konusu projede Python kullanılmış olsa da mikro-servis mimarisinde farklı programlama dilleri de kullanılabilir, her servis kendi veri deposuna sahip olabilir ve yine her biri bağımsız yaşam döngüsüne sahiptir. Servisler arası iletişim ise ağ üzerinden (genellikle HTTP/REST, gRPC veya mesaj kuyrukları aracılığıyla) sağlanır [şuraya atıf verilebilir — Fowler, M. & Lewis, J. (2014). "Microservices." https://martinfowler.com/articles/microservices.html].

> [!NOTE]
> **Şekil 2.1** — Monolitik ve mikro-servis mimari karşılaştırma diyagramı burada yer alacaktır.
> Sol tarafta tek blok monolitik uygulama; sağ tarafta bağımsız servisler (Crawler, DB, VLM, LLM, CUA) ve aralarındaki ağ iletişim bağlantıları gösterilecektir.

Mikro-servis mimarisinin dağıtık bir ortamda işlevsel olabilmesi için bir dizi destekleyici kalıba ihtiyaç duyulmaktadır:

**Servis Keşfi ve Kayıt (Service Discovery & Registry):** Dağıtık bir sistemde her servisin diğer servisleri bulabilmesi gerekmektedir. Bu amaçla merkezi bir kayıt defteri (registry) tutulur ki daha sonra ele alınacak olan yıldız(star) topolojisinin kullanılmasının sebeplerinden biri de budur. Servisler başlatıldığında kendilerini bu deftere kaydeder, durduklarında kayıtları silinir. Geliştirilen sistemde bu işlev, Orchestrator düğümündeki `NodeRegistry` bileşeni tarafından üstlenilmektedir. Her düğüm (Crawler, DB, VLM, LLM, CUA) başlatıldığında gRPC üzerinden Orchestrator'a `Register` çağrısı yapar ve benzersiz bir düğüm kimliği (node ID) alır.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** Burada `orchestrator.proto` dosyasından `RegisterRequest` / `RegisterResponse` mesaj tanımlarının kısa bir kesiti gösterilebilir:
> ```protobuf
> message RegisterRequest {
>   string node_type = 1;  // "crawler", "vlm", "llm", "db", "cua"
>   string host = 2;
>   int32 port = 3;
> }
> message RegisterResponse {
>   bool success = 1;
>   string node_id = 2;   // e.g., "crawler_a3f2b8c9"
>   string message = 3;
> }
> ```

**Sağlık Kontrolü (Heartbeat):** Kayıt tek başına yeterli değildir; bir düğümün çalışır durumda olup olmadığının sürekli izlenmesi gerekmektedir. Bu amaçla periyodik sağlık sinyalleri (heartbeat) kullanılır. Geliştirilen sistemde her düğüm belirli aralıklarla Orchestrator'a `Heartbeat` mesajı gönderir; belirtilen zaman aşımı süresi içinde sinyal alınmayan düğümler otomatik olarak çevrimdışı (offline) olarak işaretlenir.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** Orchestrator'ın zaman aşımı tespiti yapan `_heartbeat_checker` döngüsünden kısa bir kesit veya bir düğümün çevrimdışı olarak işaretlendiğini gösteren terminal çıktısı eklenebilir:
> ```
> [Orchestrator] Node offline: vlm_8a3c1f2e
> ```

**Container Tabanlı Dağıtım (Docker):** Mikro-servislerin bağımsız olarak paketlenmesi ve dağıtılması için Docker tabanlı konteynerler kullanılmaktadır. Docker, servislerin kendi bağımlılıklarıyla birlikte izole bir ortamda çalışmasını sağlar; Docker Compose ise birden fazla konteynerin tek bir yapılandırma dosyasıyla tanımlanıp birlikte yönetilmesine olanak tanır [şuraya atıf verilebilir — Docker Documentation, https://docs.docker.com/]. Geliştirilen sistemde Orchestrator, RabbitMQ, Crawler, DB, PostgreSQL ve MinIO gibi **çekirdek servisler** Docker Compose aracılığıyla tek komutla ayağa kaldırılabilmektedir. Bununla birlikte, GPU gerektiren düğümler (VLM, LLM, CUA) — yerel donanım kısıtları nedeniyle — Compose tanımında yorum satırı olarak bulunmakta; bu düğümler pratikte bulut GPU sağlayıcıları (Vast.ai) üzerinde ayrı konteynerler olarak çalıştırılmakta ve lokal Orchestrator'a SSH tünelleri aracılığıyla bağlanmaktadır. Bu hibrit dağıtım modeli — yerel çekirdek + uzak GPU düğümleri — geliştirme sürecinde hızlı iterasyon sağlamakla birlikte, IP ve port yapılandırmalarının her oturumda manuel olarak ayarlanmasını gerektirmektedir. Söz konusu operasyonel zorluk, 6. bölümde bir sınırlama olarak tartışılacaktır.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** `docker-compose.yml` dosyasından çekirdek servislerin tanımlandığı kısa bir kesit gösterilebilir (orchestrator + rabbitmq + crawler). Ayrıca GPU düğümlerinin yorum satırında olduğunu gösteren VLM/LLM bölümü ve CUA'nın `shm_size`, `healthcheck` gibi özel yapılandırmaları vurgulanabilir.

Bu üç kalıp — servis keşfi, sağlık kontrolü ve konteyner tabanlı dağıtım — geliştirilen sistemin dağıtık yapısının temelini oluşturmaktadır. İlerleyen alt bölümlerde, bu temeller üzerine inşa edilen iletişim protokolleri (gRPC, RabbitMQ) ve özelleşmiş bileşenler ayrıntılı olarak ele alınacaktır.

## 2.2 gRPC ve Protocol Buffers

Dağıtık sistemlerde servisler arası iletişim, sistemin genel performansını, güvenilirliğini ve bakım kolaylığını doğrudan etkileyen kritik bir tasarım kararıdır. Geleneksel yaklaşımda bu iletişim HTTP/REST protokolü üzerinden JSON formatında sağlanmaktadır. REST, insan tarafından okunabilir bir format sunması ve geniş araç desteğiyle yaygın kullanım bulmakla birlikte, yüksek frekanslı servisler arası çağrılarda belirgin performans kısıtları ortaya çıkmaktadır: JSON serileştirme/deserileştirme maliyeti, metin tabanlı protokolün bant genişliği verimliliğindeki düşüklüğü ve tip güvenliğinin derleme zamanında değil çalışma zamanında doğrulanması bu kısıtların başında gelmektedir [şuraya atıf verilebilir — Indrasiri, K. & Kuruppu, D. (2020). *gRPC: Up and Running.* O'Reilly].

**gRPC** (Google Remote Procedure Call), bu kısıtlamalara yanıt olarak Google tarafından geliştirilmiş açık kaynaklı bir RPC (Uzak Yordam Çağrısı) çerçevesidir [şuraya atıf verilebilir — gRPC Documentation, https://grpc.io/docs/]. gRPC, taşıma katmanı olarak HTTP/2'yi, veri serileştirme formatı olarak ise **Protocol Buffers** (protobuf) kullanmaktadır. Bu kombinasyon birkaç kritik avantaj sağlamaktadır:

- **Performans:** İkili (binary) serileştirme sayesinde JSON'a kıyasla çok daha küçük mesaj boyutları ve düşük işlemci kullanımı elde edilmektedir.
- **Tip Güvenliği:** Servis sözleşmeleri `.proto` dosyalarında tanımlanır; kod üreteci bu tanımlardan istemci ve sunucu kodlarını otomatik olarak üretir. Tip uyumsuzlukları derleme aşamasında yakalanır.
- **Çift Yönlü Akış:** HTTP/2 altyapısı sayesinde hem istemciden sunucuya hem de sunucudan istemciye sürekli veri akışı (streaming) desteklenmektedir.
- **Çok Dilli Destek:** Python, Go, Java, C++ dahil pek çok dilde istemci/sunucu kodu otomatik üretilebilmektedir.

### Geliştirilen Sistemde gRPC Kullanımı

Geliştirilen sistemde gRPC, **kontrol düzlemi** iletişimini üstlenmektedir. Her düğüm ile Orchestrator arasındaki kayıt, sağlık bildirimi ve görev atama/raporlama işlemleri gRPC üzerinden gerçekleşmektedir. Servis sözleşmesi, proje kök dizinindeki `proto/orchestrator.proto` dosyasında tanımlanmıştır.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** `orchestrator.proto` dosyasından `OrchestratorService` servis tanımı gösterilebilir:
> ```protobuf
> service OrchestratorService {
>   rpc Register(RegisterRequest) returns (RegisterResponse);
>   rpc Heartbeat(HeartbeatRequest) returns (HeartbeatResponse);
>   rpc ReportTaskResult(TaskResultRequest) returns (TaskResultResponse);
>   rpc GetTask(GetTaskRequest) returns (GetTaskResponse);
> }
> ```

Bu `.proto` tanımından `compile_proto.py` betiği aracılığıyla hem Orchestrator tarafındaki sunucu kodu hem de tüm düğümlerin kullandığı istemci kütüphaneleri otomatik olarak üretilmektedir. Bu yaklaşım, servis sözleşmesinin tek bir dosyada merkezileşmesini ve tüm tarafların aynı tanımı kullanmasını garantilemektedir.

gRPC'nin bu sistemde tercih edilmesinin temel gerekçeleri şunlardır: düğüm kaydı ve heartbeat gibi sık tekrarlanan, gecikme duyarlı çağrıların düşük yükle (low overhead) işlenmesi gerekliliği; ve servis sözleşmesinin merkezi bir `.proto` dosyasıyla yönetilmesinin sağladığı bakım kolaylığı. Asenkron ve yük dengelemesi gerektiren görev dağıtımı ise gRPC yerine RabbitMQ üzerinden yürütülmekte; bu iki protokolün birbirini tamamlayan rolleri bir sonraki alt bölümde ele alınmaktadır.

## 2.3 Mesaj Kuyruğu Sistemleri: RabbitMQ ve AMQP

gRPC'nin senkron istek-yanıt modelinin yanı sıra, dağıtık sistemlerde görev dağıtımı ve bileşenler arası gevşek bağlantı (loose coupling) için **mesaj kuyruğu** sistemleri yaygın biçimde kullanılmaktadır. Bu yaklaşımda üretici (producer) bileşen, işi doğrudan tüketiciye (consumer) aktarmak yerine bir aracı kuyruğa bırakır; tüketici ise kendi hızında bu kuyruğu işler. Bu model üç kritik avantaj sağlar: üretici ve tüketici birbirinden bağımsız ölçeklenebilir; tüketici geçici olarak çevrimdışı olsa bile mesajlar kaybolmaz; ve kuyruk sistemi doğal bir yük dengeleyici görevi üstlenir [şuraya atıf verilebilir — RabbitMQ Documentation, https://www.rabbitmq.com/docs].

**RabbitMQ**, AMQP (Advanced Message Queuing Protocol) standardını uygulayan açık kaynaklı bir mesaj aracısıdır [şuraya atıf verilebilir — AMQP Specification, https://www.amqp.org/]. RabbitMQ'nun mimarisinde üç temel kavram bulunmaktadır:

- **Exchange:** Üreticiden gelen mesajları alır ve yönlendirme kurallarına göre uygun kuyruğa iletir.
- **Queue (Kuyruk):** Mesajların tüketiciye ulaşana kadar kalıcı olarak saklandığı yapı.
- **Binding:** Exchange ile kuyruk arasındaki yönlendirme kuralı.

RabbitMQ'nun mesaj kalıcılığı (persistence) ve onay (acknowledgement) mekanizmaları, işlenmemiş görevlerin tüketici yeniden başlatıldığında kaybolmamasını garanti etmektedir. Bu özellik, uzun süren GPU çıkarım görevlerinin (VLM analizi, LLM özetleme) kayıpsız iletilmesi açısından kritik önem taşımaktadır.

### Geliştirilen Sistemde RabbitMQ Kullanımı

Geliştirilen sistemde RabbitMQ, **veri düzlemi** iletişimini — yani ağır veri işleme görevlerinin dağıtımını — üstlenmektedir. Orchestrator, yeni bir haber öğesi için işlem başlatmak istediğinde ilgili görevi doğrudan hedef düğüme göndermez; bunun yerine görevi uygun kuyruğa yazar. İlgili düğüm (VLM, LLM, CUA veya DB) kendi hızında kuyruğu tüketerek görevi işler ve sonucu sonuç kuyruğuna yazar.

Sistemde tanımlanan başlıca kuyruklar şunlardır:

| Kuyruk | Üretici | Tüketici | İçerik |
|---|---|---|---|
| `vlm_tasks` | Orchestrator | VLM düğümü | Görsel analiz görevleri |
| `llm_tasks` | Orchestrator | LLM düğümü | Metin analiz görevleri |
| `agent_tasks` | Orchestrator | CUA düğümü | Araştırma görevleri |
| `db_tasks` | Orchestrator | DB düğümü | Depolama görevleri |
| `task_results` | Tüm düğümler | Orchestrator | Görev sonuçları |

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** RabbitMQ yönetim panelinden (port 15672) kuyruk listesi ve mesaj sayıları ekran görüntüsü eklenebilir. Ayrıca `orchestrator/services/rabbitmq_manager.py` dosyasından kuyruk tanımlama kodunun kısa bir kesiti gösterilebilir.

### Push vs. Poll Tasarım Kararı

Crawler düğümü, VLM/LLM/CUA/DB düğümlerinden farklı olarak RabbitMQ kuyruğu tüketmez. Mevcut implementasyonda Crawler, Orchestrator'a gRPC istemcisi olarak bağlanır; kayıt sırasında erişilebilir bir servis adresi bildirmez ve görevleri `GetCrawlTask` gRPC çağrısı ile periyodik olarak talep eder. Sonuçlar ise `ReportCrawlResult` çağrısıyla yine gRPC üzerinden Orchestrator'a iletilir. Bu nedenle Crawler görev akışı push yerine **poll modeli** üzerinden yürütülmektedir.

Bu modelin tercih edilmesinin temel gerekçesi şudur: Crawl işlemi, VLM/LLM analiz görevleri gibi sürekli yüksek hacimli kuyruk tüketen bir iş değil; operatör tarafından Orchestrator paneli üzerinden başlatılan, talebe göre uzun sürebilen ve Orchestrator kontrolünde ilerleyen seyrek bir görevdir. Crawler, sürekli görev kuyruğu tüketen bir worker gibi değil, Orchestrator'a bağlı çalışan ve uygun görev olup olmadığını belirli aralıklarla sorgulayan bir istemci olarak tasarlanmıştır. Aynı görev akışı RabbitMQ tabanlı bir `crawler_tasks` kuyruğuyla da modellenebilirdi; nitekim bu yaklaşım daha tutarlı izlenebilirlik ve yük dengeleme imkânı sunar. Ancak mevcut prototipte Crawler için ayrı bir kuyruk eklemek yerine, Orchestrator kontrollü gRPC poll modeli uygulanmış; RabbitMQ ise analiz ve depolama hattındaki worker düğümleri için kullanılmıştır.

## 2.4 Büyük Dil Modelleri (LLM) ve Görsel Dil Modelleri (VLM)

Geliştirilen sistemin analiz katmanı, metin ve görüntü verilerini yorumlayabilen yapay zekâ modelleri üzerine inşa edilmiştir. Bu alt bölümde söz konusu modellerin mimari temelleri ve sistemdeki kullanım amaçları ele alınmaktadır.

### Transformer Mimarisi

Modern büyük dil modellerinin temelini Vaswani ve ark. (2017) tarafından önerilen **Transformer** mimarisi oluşturmaktadır [şuraya atıf verilebilir — Vaswani et al. (2017), "Attention Is All You Need", https://arxiv.org/abs/1706.03762]. Transformer, ardışık (RNN/LSTM) yapıların sekans uzunluğuyla doğrusal artan hesaplama maliyeti sorununu, öz-dikkat (self-attention) mekanizmasıyla paralel işleme yaparak çözmektedir. Öz-dikkat mekanizması, bir dizi içindeki her simgenin diğer tüm simgelerle ilişkisini aynı anda hesaplar; bu sayede uzak bağlamsal bağımlılıklar etkin biçimde yakalanabilmektedir.

Bu mimari, ölçeklendirildiğinde ortaya çıkan dil modellerinin (GPT, LLaMA, Qwen, Gemma vb.) temelini oluşturmaktadır. Brown ve ark. (2020) tarafından yürütülen GPT-3 çalışması, yeterince büyük ölçekli dil modellerinin ince-ayar (fine-tuning) gerektirmeksizin bağlam içi öğrenme (in-context learning) yoluyla pek çok NLP görevini gerçekleştirebildiğini göstermiştir [şuraya atıf verilebilir — Brown et al. (2020), "Language Models are Few-Shot Learners", https://arxiv.org/abs/2005.14165].

### LLM: Metin Analizi ve Özetleme

Geliştirilen sistemde LLM düğümü, Crawler tarafından toplanan haber metinleri üzerinde doğal dil işleme (NLP) görevleri yürütmektedir. Bu görevler arasında **metin özetleme** (uzun haber içeriklerinin kısa özete dönüştürülmesi), **duygu analizi** (haberin olumlu/olumsuz/nötr tonunun belirlenmesi) ve **varlık çıkarma** (kişi, kurum, yer adı, tarih gibi yapılandırılmış bilgilerin metinden çıkarılması) yer almaktadır. Bu görevler, istem tabanlı (prompt-based) yaklaşımla gerçekleştirilmekte; modelin ağırlıkları güncellenmemekte, yalnızca uygun istemler (prompt) aracılığıyla model yönlendirilmektedir.

### VLM: Görüntü–Metin Çapraz Analizi

**Görsel Dil Modelleri** (VLM), metin ve görüntü verisini birleşik bir temsil uzayında işleyebilen çok kipli (multimodal) modellerdir. Sistemde VLM düğümü, Crawler'ın topladığı haber görsellerini (ana görsel, içerik görselleri) analiz ederek görsel içerik tanımlaması, görüntü–metin tutarlılık analizi ve görsel varlık tespiti görevlerini yerine getirmektedir. Bu yetenek, yalnızca metin tabanlı analizin yakalayamayacağı görsel bağlamı (fotoğraftaki kişi, coğrafi yer, olay sahnesi vb.) sistematik olarak elde etmeyi mümkün kılmaktadır.

> [!NOTE]
> **📸 Şekil Yeri —** LLM metin analiz pipeline'ını (ham metin → istem → model → yapılandırılmış çıktı) gösteren basit bir akış diyagramı eklenebilir.

### vLLM ile Yüksek Verimli Çıkarım

Büyük dil modellerinin servis ortamında çalıştırılması, bellek yönetimi açısından önemli güçlükler doğurmaktadır. Geleneksel çıkarım (inference) motorlarında KV (Key-Value) önbelleği için bellek önceden ayrılmakta; bu da bellek parçalanmasına ve düşük GPU kullanımına yol açmaktadır. Kwon ve ark. (2023) tarafından geliştirilen **vLLM** (virtual LLM), işletim sistemlerindeki sayfalı bellek (paged memory) kavramını LLM çıkarımına uyarlayan **PagedAttention** mekanizmasıyla bu sorunu çözmektedir [şuraya atıf verilebilir — Kwon et al. (2023), "Efficient Memory Management for Large Language Model Serving with PagedAttention", https://arxiv.org/abs/2309.06180]. PagedAttention, KV önbelleğini sabit boyutlu sayfalara bölerek parçalanmayı ortadan kaldırmakta; bellek kullanım verimliliğini artırmakta ve eşzamanlı istek kapasitesini yükseltmektedir.

Mevcut prototipte vLLM yalnızca **CUA düğümü** tarafında kullanılmaktadır. CUA, `docker-compose.cua-allinone.yml` ve `Dockerfile.allinone` yapılandırmasıyla aynı GPU makinesinde hem `vllm serve` sunucu sürecini hem de ajan işlemini barındırmakta; ajan model çağrılarını bu sunucunun OpenAI uyumlu REST API'si üzerinden gerçekleştirmektedir. LLM ve VLM düğümleri ise farklı bir yaklaşımla çalışmaktadır: varsayılan modda (`MODEL_MODE=transformers`) HuggingFace Transformers kütüphanesi aracılığıyla modeli doğrudan kendi işlem sürecine yüklemekte; geliştirme modunda (`MODEL_MODE=lm-studio`) ise LM Studio'nun OpenAI uyumlu yerel API'sine bağlanmaktadır. Bu durum, LLM/VLM düğümlerinin yüksek eşzamanlılık gerektiren senaryolarda vLLM'in sağladığı istek zamanlama ve bellek optimizasyon avantajlarından yararlanamadığı anlamına gelmektedir.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** `cua/entrypoint_allinone.sh` içindeki `vllm serve ...` komutunun çıktısı veya `vast_worker_template_presets.md`'den ilgili başlatma parametreleri gösterilebilir. LLM/VLM tarafı için `llm/services/model_handler.py`'deki `MODEL_MODE` dallanması da faydalı bir kod kesiti olabilir.

## 2.5 Otonom Ajanlar ve LangGraph

Geleneksel yazılım sistemleri belirlenmiş kurallara ve sabit iş akışlarına göre çalışır; öngörülemeyen durumlar veya karmaşık çok adımlı kararlar bu sistemler için ciddi tasarım güçlükleri doğurur. **Otonom ajan** yaklaşımında ise bir LLM, gelen göreve göre eylem planı oluşturmakta, planı adım adım yürütmekte ve sonuçları değerlendirerek bir sonraki adıma karar vermektedir. Bu döngüsel yapı — **plan → execute → evaluate** — ajanın dinamik ortamlara uyum sağlamasına olanak tanır.

### ReAct Paradigması

Yao ve ark. (2023) tarafından önerilen **ReAct** (Reasoning + Acting) çerçevesi, LLM tabanlı ajanların karar süreçlerini dil üretimi yoluyla nasıl yönetebileceğini ortaya koymuştur [şuraya atıf verilebilir — Yao et al. (2023), "ReAct: Synergizing Reasoning and Acting in Language Models", https://arxiv.org/abs/2210.03629]. ReAct'te ajan her adımda şu döngüyü gerçekleştirir: önce durumu gözlemler (Observe), ardından bir düşünce zinciri üretir (Reason), son olarak bir araç çağrısı veya eylemi yürütür (Act). Bu yapı, ajanın her kararını açıklanabilir bir gerekçeyle üretmesini ve hata ayıklamayı kolaylaştıran izlenebilir bir yürütme izi bırakmasını sağlar.

### LangGraph: Durum Tabanlı Ajan İş Akışı

Serbest döngülü ReAct uygulamalarının belirsizlik ve kontrol güçlüğü sorunlarına yanıt olarak **LangGraph**, ajan iş akışını açık bir **durum grafiği** (StateGraph) olarak modelleme imkânı sunmaktadır [şuraya atıf verilebilir — LangGraph Documentation, https://langchain-ai.github.io/langgraph/]. LangGraph'ta iş akışı, düğümler (node) ve kenarlardan (edge) oluşan yönlü bir çizge biçiminde tanımlanır:

- **Düğüm:** Her biri belirli bir görevi yerine getiren Python fonksiyonları (arama, sayfa okuma, değerlendirme, sentez vb.).
- **Kenar:** Düğümler arası geçiş kuralları; koşullu kenarlar (conditional edge) sayesinde akış çalışma zamanı kararlarına göre yönlendirilebilir.
- **Durum (State):** Ajanın tüm yaşam döngüsü boyunca taşıdığı paylaşımlı veri yapısı. Her düğüm bu durumu okur ve güncellenmiş bir versiyonunu üretir.

Bu model, ajanı serbest bir "her şeyi yapabilir" varlık olmaktan çıkarıp sınırlı geçiş kurallarıyla yönetilen, denetlenebilir ve tekrarlanabilir bir iş akışına dönüştürür. Özellikle sisteme entegre edilmiş bir ajan bileşeninde bu kısıtlılık bir dezavantaj değil; güvenilirliği ve öngörülebilirliği artıran bir tasarım tercihi olarak değerlendirilmektedir.

> [!NOTE]
> **📸 Şekil Yeri —** LangGraph `StateGraph` kavramsal diyagramı: düğümler (plan, execute, evaluate, synthesize), koşullu kenarlar ve `END` durumu gösterilebilir.

### browser-use: Tarayıcı Kontrolü

Web sayfalarıyla etkileşim kurmak, geleneksel LLM çağrılarının ötesinde tarayıcı otomasyonu gerektirmektedir. **browser-use** kütüphanesi, Playwright tabanlı bir headless ya da talebe göre headful tarayıcıyı LLM ajan döngüsüne entegre ederek sayfa gezme, metin okuma ve içerik çıkarma gibi eylemleri LLM çıktısıyla yönlendirilebilir araç çağrılarına dönüştürür [şuraya atıf verilebilir — browser-use GitHub, https://github.com/browser-use/browser-use]. Bu kütüphane, ajanın gerçek web sayfalarıyla insan benzeri bir etkileşim kurmasını ve yalnızca statik API'lerle ulaşılamayan dinamik içeriklere erişmesini mümkün kılar.

Geliştirilen sistemde CUA (Computer Using Agent) düğümü, bu üç katmanı — LangGraph iş akışı, LLM model entegrasyonu ve browser-use tarayıcı kontrolü — bir araya getirerek otonom araştırma görevlerini yürütmektedir. CUA'nın iç mimarisi ve iş akışının ayrıntıları Bölüm 3'te ele alınacaktır.

## 2.6 Vektör Veritabanları ve Anlamsal Arama

Geleneksel ilişkisel veritabanları, metin aramasını kelime eşleştirme (keyword matching) yöntemiyle gerçekleştirir. Bu yaklaşım, tam veya kısmi kelime örtüşmesi olmayan ancak anlamsal olarak ilişkili içerikleri bulma konusunda yetersiz kalmaktadır. **Vektör gömme** (embedding) yaklaşımında ise bir metin parçası, bir sinir ağı modeli aracılığıyla yüksek boyutlu bir sayısal vektöre dönüştürülür. Bu vektör, metnin anlamsal içeriğini kodlar; anlamca benzer metinler vektör uzayında birbirine yakın konumlanır.

İki vektör arasındaki anlamsal benzerlik tipik olarak **kosinüs benzerliği** (cosine similarity) ile ölçülür. Kosinüs benzerliği, iki vektör arasındaki açının kosinüsüdür ve [-1, 1] aralığında değer alır; 1'e yakın değerler yüksek anlamsal benzerliği ifade eder. Bu metrik, vektör boyutu ve uzunluğundan bağımsız olduğu için metin temsil vektörlerinde tercih edilmektedir [şuraya atıf verilebilir — Manning, C. D. et al. (2008). *Introduction to Information Retrieval.* Cambridge University Press].

### pgvector: PostgreSQL Üzerinde Vektör Desteği

**pgvector**, PostgreSQL'e vektör veri tipi ve vektör benzerlik araması yeteneği kazandıran açık kaynaklı bir eklentidir [şuraya atıf verilebilir — pgvector GitHub, https://github.com/pgvector/pgvector]. pgvector sayesinde vektörler, ilişkisel tablolardaki diğer alanlarla birlikte saklanabilmekte ve SQL sorguları ile sorgulanabilmektedir. Bu yaklaşım, ayrı bir vektör veritabanı çözümü (Pinecone, Qdrant, Weaviate vb.) gerektirmeksizin mevcut PostgreSQL altyapısı üzerinde anlamsal arama yeteneği eklemenin pratik bir yolunu sunmaktadır.

### Geliştirilen Sistemde Kullanımı

Geliştirilen sistemde DB düğümü, her haber öğesinin metni için otomatik olarak vektör gömme üretmektedir. Bu işlem `embedding_manager.py` bileşeni tarafından `Qwen/Qwen3-Embedding-0.6B` modeli kullanılarak gerçekleştirilmekte ve **1024 boyutlu** bir vektör üretilmektedir. Bu vektör, haber kaydıyla birlikte PostgreSQL'deki `news` tablosuna `content_embedding vector(1024)` alanı olarak işlenmektedir.

Anlamsal arama, pgvector'ün `<=>` operatörü (kosinüs mesafesi) üzerinden aşağıdaki SQL kalıbıyla gerçekleştirilmektedir:

```sql
SELECT * FROM news
ORDER BY 1 - (content_embedding <=> $1::vector)
LIMIT 10;
```

Bu yapı sayesinde bir arama sorgusu veya referans metin vektöre dönüştürüldükten sonra, içerik deposundaki anlamsal olarak en yakın haberler verimli biçimde sorgulanabilmektedir.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** `db/services/postgres_manager.py` içindeki `search_similar()` fonksiyonu ve `_init_tables()` içindeki `vector(1024)` sütun tanımı gösterilebilir.

## 2.7 Nesne Depolama: MinIO

İkili dosyaların (görsel, medya) ilişkisel bir veritabanında saklanması hem performans hem de ölçeklenebilirlik açısından uygun değildir. Bu tür içerikler için **nesne depolama** (object storage) sistemleri, büyük miktarda yapılandırılmamış verinin düşük maliyetle ve yüksek erişilebilirlikle depolanmasına olanak tanır.

**Amazon S3** (Simple Storage Service), nesne depolama alanındaki fiili standarttır. S3 uyumlu API'ler, bu ekosisteme dahil olmayı sağlarken aynı istemci kodunun farklı depolama altyapılarında çalışabilmesine imkân tanır. **MinIO**, bu S3 uyumlu API'yi açık kaynak olarak uygulayan, kendi altyapısında (on-premise) veya konteyner ortamında çalıştırılabilen bir nesne depolama çözümüdür [şuraya atıf verilebilir — MinIO Documentation, https://min.io/docs/].

### Geliştirilen Sistemde Kullanımı

Geliştirilen sistemde MinIO, DB düğümü tarafından haber görsellerinin kalıcı olarak depolanması amacıyla kullanılmaktadır. Crawler tarafından toplanan bir haber öğesinin işlenmesi sırasında `minio_manager.py` bileşeni, habere ait kapak görseli ve içerik görsellerini uzak URL'lerinden indirir ve `news-media` adlı bucket içinde `{news_id}/main.jpg` ve `{news_id}/content_{n}.jpg` yol yapısıyla MinIO'ya yükler. Yükleme tamamlandıktan sonra, orijinal HTTP URL'leri yerine `minio://{bucket}/{path}` şemasıyla dahili referans adresleri veritabanına kaydedilmektedir.

Bu yaklaşımın sağladığı iki kritik avantaj bulunmaktadır: birincisi, haber görsellerine erişimin orijinal kaynağa bağımlılıktan kurtulması (kaynak sayfa kaldırılsa bile görsellerin sistemde korunması); ikincisi, VLM düğümünün görsel analizini gerçekleştirirken görsellere güvenilir ve hızlı bir şekilde erişebilmesi.

> [!NOTE]
> **📸 Şekil Yeri —** MinIO yönetim arayüzünden (port 9001) `news-media` bucket içeriği veya örnek bir `{news_id}/` klasör yapısı ekran görüntüsü eklenebilir.

## 2.8 Web Kazıma (Web Scraping) Teknikleri

Dağıtık sistemin veri giriş noktası, dış dünyadan anlık haberleri toplayan web kazıma (web scraping) bileşenidir. Modern web siteleri artık statik HTML belgeleri olmaktan çıkıp, içerikleri JavaScript ile asenkron olarak yükleyen karmaşık Single Page Application (SPA) mimarilerine dönüşmüştür. Bu nedenle, geleneksel HTTP istekleri (örneğin Python `requests` kütüphanesi) modern web kazıma operasyonlarında yetersiz kalmakta; bunun yerine gerçek bir tarayıcı motorunu simüle eden headless tarayıcı (headless browser) teknolojileri kullanılmaktadır.

Geliştirilen Crawler düğümü, tarayıcı otomasyonu için açık kaynaklı **crawl4ai** kütüphanesini temel almaktadır [şuraya atıf verilebilir — crawl4ai GitHub, https://github.com/unclecode/crawl4ai]. Bu kütüphane, Playwright üzerinde çalışan asenkron bir web kazıyıcı olup, dinamik içeriklerin render edilmesini, gereksiz DOM elementlerinin (reklamlar, pop-up'lar, navigasyon menüleri) temizlenmesini ve doğrudan Markdown formatında temiz metin üretilmesini sağlar.

### Anti-Bot Mekanizmaları ve Magic Mode

Gelişmiş haber siteleri, otomatik erişimleri engellemek için Cloudflare, Akamai gibi CDN tabanlı güvenlik duvarları (WAF) ve tarayıcı parmak izi (browser fingerprinting) analizi kullanır. Crawler bileşeni, bu anti-bot önlemlerine uyum sağlamak için crawl4ai kütüphanesinin **Magic Mode** özelliğini aktifleştirmektedir (`magic=True`). Bu mod;
- Dinamik olarak User-Agent ve tarayıcı parmak izi döndürür (rotation),
- İnsan benzeri rastgele gecikmeler ve fare hareketleri (jitter) simüle eder,
- IP yasaklanmalarını engellemek için `asyncio.Semaphore` kullanılarak eşzamanlı sekme açılışlarını sınırlar (rate limiting).

### Asenkron Medya Çıkarımı

Haber metninin yanı sıra, habere ait görseller (kapak fotoğrafı ve gövde içi görseller) içerik analizi için kritik öneme sahiptir. Crawler, bir haber sayfasını okuduğunda DOM içindeki medya bağlantılarını (`<img src=...>`, `<video src=...>`) ayıklar. Daha sonra, performansı artırmak amacıyla bu görsellerin sadece alan (genişlik × yükseklik) olarak en büyük ve haber açısından en önemli olanları seçilerek MinIO'ya aktarılmak üzere DB düğümüne iletilir. Tüm bu operasyonlar `aiohttp` üzerinden asenkron bağlantı havuzlarıyla yürütülerek Crawler'ın bloklanmadan binlerce sayfayı paralel işleyebilmesi sağlanır.

> [!NOTE]
> **📋 Kod/Çıktı Yeri —** `crawler/main.py` içindeki `CrawlerRunConfig(magic=True, ...)` konfigürasyonu ve `verify_and_extract` fonksiyonundaki `Semaphore` ve `jitter` kullanımı (örnek kod kesitleri) verilebilir.

---
*(Bölüm 2'nin Sonu. Bölüm 3: Sistem Mimarisi ve Tasarım başlığına geçilebilir.)*

# 3. MATERYAL VE METOT / SİSTEM MİMARİSİ VE TASARIM

Bu bölümde geliştirilen sistemin çalışma ortamı, dağıtık mimarisi, düğüm yapısı, iletişim protokolleri ve veri işleme akışı ele alınmaktadır. Tezin önceki bölümünde anlatılan mikro-servis, gRPC, RabbitMQ, vektör veritabanı, nesne depolama ve otonom ajan kavramları bu bölümde somut sistem tasarımı üzerinden açıklanmaktadır.

Geliştirilen sistem, klasik bir veri toplama betiği veya tek süreçli bir analiz uygulaması olarak değil, birden fazla bağımsız servisin birlikte çalıştığı dağıtık bir ürün prototipi olarak tasarlanmıştır. Bu tercih, haber toplama, medya depolama, görsel analiz, metin analizi ve otonom araştırma gibi birbirinden farklı kaynak gereksinimlerine sahip işlerin ayrı düğümlere bölünmesini sağlamaktadır. Böylece her düğüm kendi bağımlılıklarıyla paketlenebilmekte, gerektiğinde farklı makinede çalıştırılabilmekte ve sistemin geri kalanından bağımsız olarak geliştirilebilmektedir.

Sistemin temel düğümleri şunlardır:

| Düğüm | Temel görev |
|---|---|
| Orchestrator | Düğüm kaydı, heartbeat takibi, görev oluşturma, kuyruklara iş basma, operasyon paneli |
| Crawler | Haber kaynaklarından bağlantı toplama, sayfa indirme, metin ve medya çıkarımı |
| DB | PostgreSQL, pgvector ve MinIO üzerinden kalıcı depolama |
| VLM | Haber görselleri üzerinde görsel dil modeli analizi |
| LLM | Haber metni ve VLM çıktısını kullanarak özet, duygu, varlık ve kategori analizi |
| CUA | Web üzerinde otonom yüzey araştırması yapan LangGraph tabanlı ajan |

## 3.1 Çalışma Ortamı ve Donanım Altyapısı

Geliştirme ortamı Windows tabanlı yerel bir makine ve gerektiğinde Vast.ai üzerinde kiralanan GPU düğümlerinden oluşmaktadır. Yerel makinede Orchestrator, RabbitMQ, PostgreSQL, MinIO, Crawler ve DB gibi çekirdek servisler Docker Compose ile ayağa kaldırılabilmektedir. GPU gereksinimi yüksek olan VLM, LLM ve CUA düğümleri ise geliştirme sürecinde iki farklı biçimde çalıştırılabilecek şekilde tasarlanmıştır: uygun donanım varsa yerel Docker ortamında, aksi durumda uzak GPU sunucuları üzerinde.

Yerel Compose yapılandırmasında `orchestrator`, `rabbitmq`, `crawler`, `db`, `postgres`, `minio` ve `cua` servisleri tanımlıdır. `vlm` ve `llm` servisleri de aynı dosyada yer almakla birlikte, GPU ve model boyutu gereksinimleri nedeniyle varsayılan olarak yorum satırı durumundadır. Bu tercih, çekirdek sistemin düşük maliyetli bir yerel ortamda test edilebilmesini, model çıkarımı gerektiren işlerin ise güçlü GPU düğümlerine taşınabilmesini sağlamaktadır.

Orchestrator gRPC sunucusu varsayılan olarak `50051` portunda çalışmaktadır. RabbitMQ mesaj aracısı `5672` portu üzerinden AMQP trafiğini, `15672` portu üzerinden yönetim arayüzünü sunmaktadır. PostgreSQL `pgvector/pgvector:pg16` imajı ile çalıştırılmakta ve `news_db` veritabanını barındırmaktadır. MinIO ise `9000` portu üzerinden S3 uyumlu API, `9001` portu üzerinden yönetim konsolu sağlamaktadır. Orchestrator'ın yerel operasyon paneli kodda `8088` portuna bağlanacak şekilde tanımlanmıştır.

> [!NOTE]
> **Şekil 3.1** — Geliştirme ortamı topolojisi burada yer alacaktır. Şekilde yerel makinede çalışan Orchestrator, RabbitMQ, PostgreSQL, MinIO, Crawler ve DB servisleri; uzak GPU tarafında ise VLM/LLM/CUA düğümleri ve bunların Orchestrator'a bağlanma biçimi gösterilecektir.

## 3.2 Genel Sistem Mimarisi

Sistem, merkezi bir Orchestrator düğümü etrafında örgütlenen yıldız (star) topolojisine sahiptir. Crawler, DB, VLM, LLM ve CUA düğümleri doğrudan birbirleriyle kalıcı ve sıkı bağlı bir iletişim kurmak yerine Orchestrator ve RabbitMQ üzerinden koordine edilmektedir. Bu yapı, dağıtık sistem karmaşıklığını azaltmakta ve düğüm durumlarının tek bir kontrol noktasından izlenmesini sağlamaktadır.

Yıldız topolojisinin tercih edilmesinin başlıca gerekçeleri şunlardır:

- Düğüm kayıt, heartbeat ve görev durumlarının merkezi olarak izlenebilmesi.
- Worker düğümlerinin sisteme eklenip çıkarılmasının basitleştirilmesi.
- Crawler, VLM, LLM, DB ve CUA gibi farklı görev türlerinin tek bir görev yönetim modeli altında toplanması.
- Operasyon panelinde sistem sağlığı, kuyruklar, görevler, araştırma misyonları ve arama sonuçlarının tek noktadan görüntülenebilmesi.

Bu tasarımın temel değiş-tokuşu, Orchestrator'ın tek hata noktası haline gelmesidir. Mevcut prototipte yüksek erişilebilirlik (high availability), lider seçimi veya dağıtık Orchestrator durumu uygulanmamıştır. Bu nedenle Orchestrator'ın yatay ölçeklenmesi ve dayanıklı durum yönetimi, gelecek çalışma başlığı altında ele alınması gereken bir geliştirme alanıdır.

Sistemde iki ayrı iletişim katmanı bulunmaktadır:

| Katman | Kullanılan teknoloji | Kullanım amacı |
|---|---|---|
| Kontrol düzlemi | gRPC + Protocol Buffers | Düğüm kaydı, heartbeat, Crawler görev çağrısı, sonuç raporlama |
| Veri düzlemi | RabbitMQ | VLM, LLM, DB ve CUA görevlerinin asenkron dağıtımı |

gRPC tarafında tüm düğümler `Register` çağrısıyla Orchestrator'a kayıt olmakta ve bir `node_id` almaktadır. Ardından `Heartbeat` çağrılarıyla durumlarını periyodik olarak bildirmektedir. RabbitMQ tarafında ise Orchestrator, analiz ve depolama görevlerini ilgili kuyruklara kalıcı mesajlar olarak yazmaktadır. Kodda tanımlanan temel kuyruklar `vlm_tasks`, `llm_tasks`, `db_tasks`, `agent_tasks`, `vlm_results`, `llm_results` ve `agent_results` biçimindedir.

Haber işleme hattının mevcut koddaki gerçek akışı şu şekildedir:

1. Crawler haber metnini ve medya bağlantılarını çıkarır.
2. Crawler sonucu gRPC üzerinden Orchestrator'a raporlar.
3. Orchestrator ham haber verisini `vlm_tasks` kuyruğuna yazar.
4. VLM düğümü görselleri analiz eder ve sonucu Orchestrator'a bildirir.
5. Orchestrator ham haber verisi ile VLM sonucunu birleştirerek `llm_tasks` kuyruğuna yazar.
6. LLM düğümü metin analizini üretir ve sonucu Orchestrator'a bildirir.
7. Orchestrator ham veri, VLM analizi ve LLM analizini tek payload halinde `db_tasks` kuyruğuna yazar.
8. DB düğümü haberi PostgreSQL'e, medya dosyalarını MinIO'ya, analiz sonuçlarını ilgili tablolara kaydeder.

Bu akışta DB düğümü yalnızca ilk ham crawl çıktısını değil, nihai analiz paketini de saklayacak şekilde konumlandırılmıştır. `db/main.py` içinde DB düğümü `db_tasks` kuyruğunu tüketmekte; normal haber analizleri, CUA yüzey ajanından gelen makaleler ve araştırma misyonu çıktıları için ayrı işleme dalları kullanmaktadır.

> [!NOTE]
> **Şekil 3.2** — Sistem bileşen diyagramı burada yer alacaktır. Orchestrator merkezde; Crawler, DB, VLM, LLM ve CUA uç düğümler olarak; RabbitMQ, PostgreSQL ve MinIO altyapı bileşenleri olarak gösterilecektir.

> [!NOTE]
> **Şekil 3.3** — Kontrol düzlemi ve veri düzlemi ayrımı burada gösterilecektir. gRPC okları kayıt/heartbeat/raporlama için, RabbitMQ okları ise kuyruk tabanlı görev dağıtımı için kullanılacaktır.

## 3.3 Orchestrator Düğümü

Orchestrator düğümü sistemin koordinasyon merkezidir. Kod tabanında bu düğüm; gRPC sunucusu, düğüm kayıt defteri, pipeline yöneticisi, RabbitMQ yöneticisi ve yerel HTTP operasyon panelinden oluşmaktadır. Bu bileşenler birlikte çalışarak worker düğümlerinin sisteme katılmasını, görevlerin oluşturulmasını, kuyruklara dağıtılmasını ve tamamlanan işlerin sonraki aşamaya geçirilmesini sağlar.

### NodeRegistry: Düğüm Kaydı ve Sağlık Takibi

`NodeRegistry`, sisteme bağlanan düğümlerin kimlik, tip, durum, adres, port, kayıt zamanı, son heartbeat zamanı ve aktif görev bilgilerini bellekte tutmaktadır. Düğüm tipleri `crawler`, `db`, `vlm`, `llm` ve `cua` olarak sınırlandırılmıştır. Her düğüm kayıt sırasında tipini, host bilgisini ve portunu gönderir; Orchestrator ise `{node_type}_{hash}` formatında benzersiz bir `node_id` üretir.

Heartbeat mekanizmasında düğümler durumlarını `IDLE`, `BUSY` veya `ERROR` olarak bildirir. Orchestrator tarafında heartbeat zaman aşımı kontrolü yapılmakta; belirlenen süre içinde sinyal göndermeyen düğümler `OFFLINE` durumuna alınmaktadır. Bu mekanizma özellikle uzak GPU düğümlerinin bağlantı kopması, konteyner kapanması veya model yükleme hatası gibi durumlarda sistemin güncel görünümünü koruması için gereklidir.

### PipelineManager: Görev Durum Makinesi

`PipelineManager`, haber ve ajan görevlerinin yaşam döngüsünü izleyen ana bileşendir. Her görev `PipelineTask` veri yapısıyla temsil edilir ve `task_id`, `news_id`, aşama bilgisi, ham veri, VLM sonucu, LLM sonucu, hata bilgisi ve zaman damgalarını taşır.

Kodda tanımlanan görev aşamaları şunlardır:

| Aşama | Anlamı |
|---|---|
| `CRAWLED` | Crawler tarafından ham haber verisi üretildi |
| `VLM_ANALYZING` | Haber görsel analizi için VLM kuyruğuna gönderildi |
| `VLM_COMPLETE` | VLM sonucu alındı |
| `LLM_ANALYZING` | Haber metin analizi için LLM kuyruğuna gönderildi |
| `AGENT_SURFACE` | CUA yüzey araştırması başlatıldı veya sonucu alındı |
| `AGENT_RESEARCH` | Araştırma ajanı sonucu işlendi |
| `AGENT_COMPLETE` | Ajan çıktısı DB kuyruğuna aktarıldı |
| `COMPLETE` | Haber analiz hattı tamamlandı ve DB kuyruğuna aktarıldı |
| `FAILED` | Görev hata ile sonlandı |

Haber hattında Orchestrator, Crawler sonucunu aldıktan sonra görevi VLM kuyruğuna yazar. VLM sonucu geldiğinde ham haber ile görsel analiz çıktısını birleştirip LLM kuyruğuna gönderir. LLM sonucu geldiğinde ise ham veri, görsel analiz ve metin analizini tek bir JSON paketi haline getirerek DB kuyruğuna yazar. Böylece DB düğümü nihai kaydı bütüncül bir bağlamla oluşturur.

CUA tarafında Orchestrator, uygun ve boşta olan bir CUA düğümü arar. Boşta CUA düğümü varsa araştırma görevini `agent_tasks` kuyruğuna yazar ve ilgili düğümü `BUSY` durumuna alır. CUA yüzey araştırmasını tamamladığında Orchestrator, toplanan makaleleri `agent_surface_articles` tipinde DB kuyruğuna aktarır. Bu kayıtlar DB tarafında `source_type='agent_surface'` işaretiyle haber tablosuna yazılır.

### RabbitMQManager: Asenkron Görev Dağıtımı

Orchestrator içindeki `RabbitMQManager`, kuyrukların tanımlanması ve mesajların ilgili kuyruğa kalıcı olarak yazılmasından sorumludur. Kuyruklar `durable=True` olarak oluşturulmakta, mesajlar ise `delivery_mode=2` ile kalıcı yayınlanmaktadır. Bu tercih, RabbitMQ yeniden başlatıldığında görev mesajlarının kaybolmaması için önemlidir.

Mevcut uygulamada Orchestrator görevleri doğrudan worker süreçlerine push etmek yerine RabbitMQ kuyruklarına yazar. VLM, LLM, DB ve CUA düğümleri kendi hızlarında bu kuyrukları tüketir. Bu model, GPU çıkarımı gibi uzun sürebilen işlerde Orchestrator'ın bloklanmasını engeller ve worker kapasitesi arttıkça kuyruk tüketiminin yatay olarak ölçeklenmesine imkân verir.

### Admin HTTP Paneli

Orchestrator ayrıca `aiohttp` tabanlı yerel bir operasyon paneli sunmaktadır. Bu panel sistemin ürün prototipi niteliğini güçlendiren pratik bir yönetim arayüzüdür. Panel üzerinden araştırma görevi başlatma, Crawler çalıştırma/durdurma, sistem özeti görüntüleme, node durumlarını izleme, pipeline görevlerini takip etme, research mission kayıtlarını listeleme, veritabanında arama yapma ve PostgreSQL/MinIO yedeği alma işlemleri yürütülebilmektedir.

HTTP API tarafında `/api/summary`, `/api/nodes`, `/api/research`, `/api/crawl/start`, `/api/crawl/stop`, `/api/search`, `/api/news/{news_id}`, `/api/missions` ve `/api/backups` gibi uç noktalar tanımlanmıştır. Bu uç noktalar, tezin uygulama bölümünde ekran görüntüleriyle desteklenebilecek somut sistem gösterimleri sağlamaktadır.

> [!NOTE]
> **Şekil 3.4** — Orchestrator iç bileşen diyagramı burada yer alacaktır. NodeRegistry, PipelineManager, RabbitMQManager, gRPC Server ve Admin HTTP Panel birlikte gösterilecektir.

> [!NOTE]
> **Şekil 3.5** — Haber görev durum makinesi burada yer alacaktır. Koddan doğrulanan akış `CRAWLED → VLM_ANALYZING → VLM_COMPLETE → LLM_ANALYZING → COMPLETE → DB queue` biçiminde gösterilecektir.

---
## 3.4 Crawler Düğümü

Crawler düğümü, sistemin dış dünyadan veri toplayan giriş katmanıdır. Bu düğümün görevi, haber kaynaklarından ilgili bağlantıları bulmak, her bağlantıdaki haber içeriğini indirmek, metin ve medya öğelerini ayıklamak, temel geçerlilik kontrollerini uygulamak ve uygun haberleri Orchestrator'a raporlamaktır. Kod tabanında bu işlevler `crawler/main.py` içindeki `NewsCrawler` sınıfı etrafında toplanmıştır.

Crawler, iki çalışma biçimini desteklemektedir. Varsayılan çalışma biçimi `distributed` modudur; bu modda Crawler Orchestrator'a gRPC istemcisi olarak bağlanır, kendisini `crawler` düğümü olarak kaydeder, heartbeat gönderir ve belirli aralıklarla görev olup olmadığını sorgular. `-standalone` bayrağıyla çalıştırıldığında ise Orchestrator'a bağlanmadan tek seferlik yerel crawl işlemi yürütür ve sonuçları `toplanan_haberler.json` dosyasına yazar. Bu ayrım, hem dağıtık sistem içinde çalışma hem de hızlı yerel test yapma ihtiyacını karşılamaktadır.

### Görev Alma Modeli: Poll Yaklaşımı

Crawler düğümü, VLM/LLM/DB/CUA düğümlerinden farklı olarak RabbitMQ kuyruğu tüketmemektedir. Bunun yerine Orchestrator ile gRPC üzerinden poll modeli kullanmaktadır. Başlangıçta Orchestrator'a `Register` çağrısı yapar; bu çağrıda callback için host ve port bildirmez, çünkü Crawler dışarıdan çağrı alan bir servis olarak değil, Orchestrator'a düzenli olarak bağlanan bir istemci olarak tasarlanmıştır.

Dağıtık modda ana döngü şu şekilde çalışmaktadır:

1. Crawler Orchestrator'a bağlanır ve `crawler` tipiyle kayıt olur.
2. Arka planda heartbeat döngüsü başlatılır.
3. Her `POLL_INTERVAL` saniyede bir `GetCrawlTask` çağrısı yapılır.
4. Görev varsa Crawler durumunu `BUSY` yapar ve crawl işlemini başlatır.
5. Geçerli her haber öğesi `ReportCrawlResult` çağrısıyla Orchestrator'a gönderilir.
6. Görev tamamlandığında Crawler tekrar `IDLE` durumuna döner.

Bu modelin pratik sonucu, Crawler'ın dışarıya port açmadan yalnızca Orchestrator'a giden bağlantılarla çalışabilmesidir. Dockerfile içinde de Crawler için herhangi bir servis portu expose edilmemiştir. Bu, özellikle NAT arkasında veya uzak makinede çalışan Crawler örneklerinin yönetimini basitleştirmektedir.

### Kaynak ve Arama Yapılandırması

Crawler'ın varsayılan arama konfigürasyonu Türkiye ile ilgili haberleri hedeflemektedir. Kodda varsayılan arama sorgusu `Turkey OR Türkiye OR Turkiye` olarak tanımlanmıştır. Zaman filtresi son 12 saatlik haberleri hedefleyecek biçimde `time_unit="h"` ve `time_value=12` değerleriyle kurulmuştur. İçerik doğrulama aşamasında haber metninde `turkey`, `türkiye`, `turkiye`, `ankara`, `istanbul` veya `turkish` anahtar kelimelerinden en az birinin bulunması beklenmektedir.

Varsayılan kaynak listesinde BBC, CNN International, Al Jazeera, Ekathimerini, Greek Reporter, Greek City Times, Times of Israel, Haaretz, Jerusalem Post, Israel National News ve Iran International gibi uluslararası haber kaynakları yer almaktadır. Her kaynak için alan adı, ülke bilgisi ve kaynak özelinde engellenecek URL yolları tanımlanmıştır. Bunun yanında tüm kaynaklara uygulanan genel bir blok listesi de bulunmaktadır. Bu liste PDF, ofis dokümanları, arşiv dosyaları, görsel/video dosyaları, galeri sayfaları, login sayfaları, RSS/feed çıktıları, yazar profilleri, reklam sayfaları ve yorum/print gibi haber dışı yolları elemek için kullanılmaktadır.

Orchestrator'dan gelen görevler, varsayılan kaynakların yanında özel URL veya alan adı hedefleri de taşıyabilmektedir. Crawler, kendisine verilen hedefleri normalize eder. Eğer hedef bir site kökü ise Google üzerinden o alan adına ait haber bağlantıları aranır; doğrudan haber URL'si verilmişse bağlantı doğrudan işlenir. Görev konfigürasyonu ayrıca arama sorgusu, zaman filtresi, maksimum haber sayısı, maksimum görsel sayısı ve zorunlu kelime listesi gibi değerleri geçici olarak değiştirebilmektedir.

> [!NOTE]
> **Şekil 3.6** — Crawler görev alma ve çalışma akışı burada gösterilecektir. Orchestrator poll döngüsü, Google link toplama, sayfa indirme, doğrulama ve sonuç raporlama adımları yer alacaktır.

### Google Bağlantı Toplama Aşaması

Crawler, kaynak bazlı bağlantı keşfi için Google arama sonucunu kullanmaktadır. Her kaynak için `site:{domain} ({search_query})` formatında bir sorgu oluşturulur ve `tbs=qdr:{time_unit}{time_value}` parametresiyle zaman filtresi uygulanır. Varsayılan durumda her kaynak için 30 sonuca kadar bağlantı hedeflenmektedir.

Google araması `crawl4ai` kütüphanesinin `AsyncWebCrawler` sınıfıyla yürütülmektedir. Arama aşamasında `CrawlerRunConfig` içinde `magic=True`, `simulate_user=True` ve `override_navigator=True` ayarları kullanılmaktadır. Bu ayarlar, otomatik tarayıcı davranışının daha insan benzeri görünmesini ve basit bot tespitlerinin azaltılmasını amaçlamaktadır. Ayrıca sayfanın yüklenmesi için `body` seçicisi beklenmekte, sayfa aşağı kaydırılmakta ve dönüşten önce rastgele 3-4 saniyelik bekleme uygulanmaktadır.

Google yanıtı alındıktan sonra Crawler CAPTCHA, consent sayfası veya olağan dışı kısa HTML gibi bloklanma belirtilerini kontrol eder. Ardından farklı Google HTML formatlarını yakalayabilmek için birden fazla regex deseniyle hedef alan adına ait URL'leri çıkarır. Bulunan bağlantılar URL decode işleminden geçirilir, Google cache veya Google iç bağlantıları elenir, kaynak özelindeki ve genel blok listelerinden geçen bağlantılar aday haber bağlantısı olarak tutulur.

### Haber Sayfası İndirme ve İçerik Çıkarımı

Aday bağlantılar toplandıktan sonra Crawler bu bağlantıları asenkron olarak işler. Aynı anda açılan sekme sayısı `asyncio.Semaphore(3)` ile sınırlandırılmıştır. Her bağlantı işlenmeden önce 0.1-1.2 saniye aralığında rastgele bekleme uygulanır. Bu yaklaşım, tüm bağlantıların aynı anda hedef kaynaklara yük bindirmesini engeller ve bot tespiti riskini azaltır.

Her haber sayfası için ayrı bir `CrawlerRunConfig` kullanılır. Bu konfigürasyonda `magic=True`, dış bağlantıların dışlanması, `nav`, `header`, `footer`, `aside`, `script`, `style`, `form` ve `iframe` gibi haber içeriği dışındaki etiketlerin çıkarılması, overlay öğelerinin temizlenmesi ve sayfanın aşağı kaydırılması gibi ayarlar bulunmaktadır. Sayfa zaman aşımı 60 saniye olarak belirlenmiştir.

Metin çıkarımı üç aşamalı bir fallback yapısına sahiptir. Önce `crawl4ai` tarafından üretilen `fit_markdown` alanı kullanılır. Bu alan yeterli uzunlukta değilse genel markdown çıktısı denenir. O da yetersizse HTML etiketleri temizlenerek düz metin elde edilir. Elde edilen metin 200 karakterden kısa ise haber geçersiz sayılır. Daha sonra metin küçük harfe çevrilir ve zorunlu anahtar kelime listesiyle eşleştirilir. Eşleşme yoksa içerik ilgisiz kabul edilir ve Orchestrator'a gönderilmez.

Geçerli bulunan haber öğeleri şu temel alanlarla yapılandırılır:

| Alan | İçerik |
|---|---|
| `source` | Kaynak adı |
| `country` | Kaynağın ülke bilgisi |
| `url` | Haber bağlantısı |
| `keyword_found` | İçerikte bulunan zorunlu anahtar kelime |
| `scraped_at` | Toplama zamanı |
| `content` | Temizlenmiş haber metni, mevcut kodda ilk 5000 karakter |
| `media` | Ana görsel, içerik görselleri ve video bağlantıları |

Bu yapı, sonraki VLM ve LLM aşamalarında kullanılacak ortak ham haber verisini oluşturmaktadır.

### Medya Çıkarımı ve Görsel Filtreleme

Crawler yalnızca metin değil, haberle ilişkili görsel ve video öğelerini de çıkarmaktadır. Ana görsel için Open Graph ve Twitter image meta etiketleri kontrol edilir. İçerik görselleri ise `crawl4ai` tarafından döndürülen medya listesi üzerinden işlenir.

Görsel seçiminde birden fazla filtre uygulanmaktadır. SVG, GIF, ICO ve inline SVG gibi formatlar elenir. URL içinde logo, icon, avatar, sprite, banner, advert, thumbnail, placeholder, social, tracker, header, footer, menu ve benzeri haber dışı görsel işaretleri taşıyan bağlantılar atılır. BBC için bazı küçük boyutlu thumbnail yolları ayrıca filtrelenmektedir. Eğer `crawl4ai` görsel skoru düşükse görsel haber açısından zayıf kabul edilir.

Görsellerin önem sıralaması alan hesabına dayanmaktadır. Genişlik ve yükseklik bilgisi mevcutsa `width × height` değeri kullanılır. Boyut bilgisi yoksa Crawler `aiohttp` ile görseli indirip Pillow aracılığıyla gerçek boyutu okumaya çalışır. Çok küçük görseller elenir; ancak `crawl4ai` skorunun yüksek olduğu durumlarda görsele ikinci bir şans verilir. Aynı görselin farklı boyutlu sürümlerini tekrar tekrar kaydetmemek için URL normalize edilir ve her görsel grubunda en büyük sürüm seçilir. Ana görsel ile aynı normalize URL'ye sahip içerik görselleri tekrar eklenmez.

Varsayılan ayarda her haber için en fazla üç içerik görseli seçilmektedir. Video bağlantıları da medya alanına eklenmekte, ancak mevcut pipeline'da görsel analiz odağı haber görselleri üzerindedir.

> [!NOTE]
> **Şekil 3.7** — Görsel filtreleme karar akışı burada gösterilecektir. Format/URL filtresi, boyut kontrolü, önem skoru, ana görsel tekrarı ve maksimum görsel sınırı ayrı karar adımları olarak verilebilir.

### Orchestrator'a Sonuç Raporlama

Dağıtık modda Crawler, geçerli bulduğu her haber öğesini görev bitimini beklemeden Orchestrator'a gönderir. Bu işlem `send_crawl_result` fonksiyonu ile yapılır. Haber verisi JSON'a çevrilir ve `CrawlTaskResponse` mesajı içinde `SUCCESS` durumuyla Orchestrator'ın `ReportCrawlResult` gRPC metoduna iletilir. Orchestrator bu sonucu aldığında Bölüm 3.2'de açıklanan pipeline akışını başlatır ve ham haber verisini VLM kuyruğuna yazar.

Bu yaklaşımda tek bir crawl görevi birden fazla haber öğesi üretebilir. Her geçerli haber, aynı görev bağlamı içinde ayrı bir sonuç olarak Orchestrator'a gönderildiği için downstream analiz hattı haber bazında ilerleyebilmektedir. Crawler tarafında görev için `max_items` verilmişse bu sayıya ulaşıldığında işlem erken sonlandırılır. `CRAWLER_DEMO_MODE` etkinleştirildiğinde ise hızlı test amacıyla `CRAWLER_DEMO_LIMIT` kadar haber toplandıktan sonra döngü durur.

### Paketleme ve Çalıştırma

Crawler Docker imajı `python:3.13-slim` tabanı üzerine kurulmuştur. Sistem bağımlılıkları arasında Playwright tarayıcılarının kurulumu için gerekli paketler ve sağlık kontrolleri için `netcat-openbsd` bulunmaktadır. Python bağımlılıkları `crawl4ai`, `aiohttp`, `Pillow`, `grpcio`, `grpcio-tools`, `python-dotenv` ve `regex` paketlerinden oluşmaktadır. Dockerfile içinde Playwright bağımlılıkları ve Chromium kurulmakta, ortak `orchestrator.proto` dosyasından Crawler tarafındaki gRPC kodları üretilmektedir.

Docker ortamında varsayılan olarak `CRAWLER_MODE=distributed`, `ORCHESTRATOR_HOST=orchestrator` ve `ORCHESTRATOR_PORT=50051` değerleri kullanılmaktadır. Crawler dışarıdan çağrı almadığı için container üzerinde port expose edilmemiştir; tüm iletişim Crawler'dan Orchestrator'a doğru giden bağlantılarla sağlanmaktadır.

Crawler düğümü bu haliyle sistemde kontrollü, yapılandırılabilir ve asenkron bir veri toplama katmanı sunmaktadır. Google üzerinden kaynak bazlı bağlantı keşfi, crawl4ai tabanlı dinamik sayfa işleme, anahtar kelime doğrulaması ve medya filtreleme zinciri sayesinde sonraki VLM/LLM analiz aşamalarına daha temiz ve haber odaklı veri aktarılması hedeflenmektedir.

---
## 3.5 Veritabanı (DB) Düğümü

DB düğümü, sistemde kalıcı veri yönetiminden sorumlu bileşendir. Bu düğüm haber kayıtlarını PostgreSQL üzerinde saklamakta, haber görsellerini MinIO nesne deposuna aktarmakta, haber metinleri için vektör gömme üretmekte ve VLM/LLM analiz sonuçlarını ilişkisel tablolarla ilişkilendirmektedir. Ayrıca CUA yüzey ajanından gelen makale çıktıları ve araştırma misyonu sonuçları da DB düğümü üzerinden kalıcı hale getirilmektedir.

Mevcut uygulamada DB düğümünün aktif görev alma kanalı RabbitMQ'dur. Düğüm Orchestrator'a gRPC istemcisi olarak bağlanıp kendisini `db` tipiyle kaydeder ve heartbeat gönderir; fakat analiz/depolama görevlerini doğrudan gRPC çağrısıyla değil, `db_tasks` kuyruğunu tüketerek işler. Bu tasarım, DB yazma işlemlerinin Orchestrator'dan ayrıştırılmasını ve analiz hattının asenkron biçimde tamamlanmasını sağlamaktadır.

### DB Düğümünün Çalışma Akışı

DB düğümü başlatıldığında sırasıyla Orchestrator, PostgreSQL, MinIO ve RabbitMQ bağlantılarını kurmaya çalışır. PostgreSQL bağlantısı `asyncpg` havuzu üzerinden oluşturulur. Bağlantı başarılı olduğunda gerekli tablolar ve indeksler yoksa oluşturulur. MinIO tarafında hedef bucket yoksa otomatik oluşturulur. RabbitMQ bağlantısı kurulduktan sonra `db_tasks` kuyruğu declare edilir ve ana döngü bu kuyruktan mesaj okumaya başlar.

Ana çalışma döngüsü non-blocking poll mantığıyla kurulmuştur. DB düğümü `db_tasks` kuyruğundan mesaj alırsa ilgili görevi işler; kuyruk boşsa kısa süre bekleyip tekrar dener. Bu yaklaşım, `asyncpg` ile çalışan asenkron veritabanı işlemlerinin RabbitMQ tüketimiyle aynı event loop içinde yönetilmesine imkân verir.

DB düğümünün işlediği üç temel payload türü bulunmaktadır:

| Payload tipi | Kaynak | Saklama davranışı |
|---|---|---|
| Standart haber analiz paketi | Orchestrator pipeline | Haber, medya, VLM ve LLM analizlerini kaydeder |
| `agent_surface_articles` | CUA yüzey ajanı | Toplanan ajan makalelerini `source_type='agent_surface'` ile haber tablosuna yazar |
| `research_mission` | CUA araştırma çıktısı | Araştırma misyonunu ve final rapor JSON'unu `research_missions` tablosuna yazar |

Standart haber analiz paketinde Orchestrator, ham haber verisini, VLM analiz çıktısını ve LLM analiz çıktısını tek JSON payload içinde DB kuyruğuna gönderir. DB düğümü önce haberin veritabanında var olup olmadığını URL tabanlı `news_id` üzerinden kontrol eder. Haber yoksa medya dosyalarını MinIO'ya aktarır ve haber kaydını PostgreSQL'e ekler. Daha sonra varsa VLM analizlerini `vlm_analysis` tablosuna, LLM analizini ise `llm_analysis` tablosuna kaydeder.

> [!NOTE]
> **Şekil 3.8** — DB düğümü işleme akışı burada gösterilecektir. `db_tasks` kuyruğundan mesaj alma, payload tipini ayırma, MinIO medya aktarımı, PostgreSQL kayıt ve analiz tablolarına yazma adımları yer alacaktır.

### PostgreSQL Şeması

PostgreSQL tarafında temel veri modeli dört ana tablo üzerine kurulmuştur: `news`, `vlm_analysis`, `llm_analysis` ve `research_missions`.

`news` tablosu haberin ana kaydını tutar. Bir haber için benzersiz `news_id`, haber URL'sinin SHA-256 özetinin ilk 16 karakteriyle üretilmektedir. URL alanı ayrıca unique olarak tanımlanmıştır; bu sayede aynı haber ikinci kez geldiğinde duplicate olarak algılanır ve tekrar eklenmez. Tabloda kaynak adı, ülke, bulunan anahtar kelime, toplanma zamanı, kayıt zamanı, haber metni, medya JSON'u, VLM/LLM işlenme durum bayrakları ve tamamlanma zamanı yer almaktadır.

`news` tablosunda ayrıca CUA entegrasyonu için iki alan bulunmaktadır. `source_type` alanı varsayılan olarak `crawler` değerini alır; CUA yüzey ajanından gelen haberlerde `agent_surface` olarak işaretlenir. `mission_id` alanı ise bir haberin hangi CUA araştırma görevi kapsamında toplandığını ilişkilendirmek için kullanılmaktadır.

`vlm_analysis` tablosu haber görselleri için üretilen analizleri saklar. Her satır bir haber görseline ait MinIO yolu veya orijinal URL, açıklama, nesne listesi, görsel duygu etiketi, haberle ilgililik derecesi ve analiz zamanını içerir. Tablo `news_id` üzerinden `news` tablosuna bağlıdır.

`llm_analysis` tablosu haberin metin analizini saklar. Bu tabloda haber özeti, sayısal duygu değeri, duygu etiketi, anahtar kelimeler, varlıklar JSON'u, kategori, konuya ilgililik ve analiz zamanı bulunur. `news_id` bu tabloda primary key olarak kullanılır; aynı haber için LLM analizi tekrar geldiğinde `ON CONFLICT` ile güncellenmektedir.

`research_missions` tablosu CUA araştırma görevlerinin kalıcı çıktısını tutar. Mission ID, konu, durum, final rapor JSON'u, son graph state JSON'u, bulgu sayısı, confidence skoru, oluşturulma zamanı ve tamamlanma zamanı bu tabloda saklanmaktadır. Mevcut yüzey ajanı çıktıları çoğunlukla haber tablosuna makale olarak yazılırken, research mission payload'ları bu tabloda görev/rapor düzeyinde tutulmaktadır.

| Tablo | Amaç |
|---|---|
| `news` | Ham haber kaydı, medya referansları, embedding ve işlenme bayrakları |
| `vlm_analysis` | Görsel analiz sonuçları |
| `llm_analysis` | Metin analizi, özet, duygu, varlık ve kategori çıktıları |
| `research_missions` | CUA araştırma görevi raporları ve graph state çıktıları |

> [!NOTE]
> **Şekil 3.9** — PostgreSQL ER diyagramı burada yer alacaktır. `news` merkez tablo olarak; `vlm_analysis`, `llm_analysis` ve `research_missions` ilişkileriyle birlikte gösterilecektir.

### Duplicate Kontrolü ve Haber Kimliği

DB düğümünde haber kimliği URL üzerinden deterministik olarak üretilmektedir. `PostgresManager.generate_news_id()` fonksiyonu URL'yi SHA-256 ile özetler ve ilk 16 karakteri `news_id` olarak kullanır. Bu yöntem, aynı URL'nin farklı görevlerden veya farklı kaynak akışlarından tekrar gelmesi durumunda aynı kimliğin üretilmesini sağlar.

Haber ekleme sırasında önce `news` tablosunda aynı URL'nin var olup olmadığı sorgulanır. Eğer kayıt varsa yeni satır oluşturulmaz ve mevcut `news_id` duplicate bilgisiyle döndürülür. Kayıt yoksa haber PostgreSQL'e eklenir. Bu mekanizma, Crawler ve CUA gibi farklı veri giriş yollarının aynı haberi tekrar üretmesi durumunda temel tekrar yazma koruması sağlamaktadır.

### MinIO ile Medya Kalıcılığı

Haber görselleri ilişkisel veritabanına doğrudan ikili veri olarak yazılmamaktadır. Bunun yerine DB düğümü, Crawler veya CUA tarafından sağlanan görsel URL'lerini indirip MinIO'ya yüklemektedir. MinIO hedef bucket adı varsayılan olarak `news-media` değerindedir.

Medya işleme sırasında ana görsel `main.{uzantı}` adıyla, içerik görselleri ise `content_{n}.{uzantı}` biçiminde saklanır. Nesne yolu `{news_id}/{filename}` formatındadır. Yükleme sonrasında PostgreSQL'de saklanan medya JSON'u, orijinal URL ile birlikte `minio://{bucket}/{news_id}/{filename}` biçimindeki dahili nesne yolunu içerir. Eğer gelen medya öğesi zaten `minio://` yolu içeriyorsa tekrar indirilmeden olduğu gibi korunur.

Mevcut kodda içerik görselleri MinIO tarafında en fazla beş adet işlenmektedir. Bu sınır Crawler tarafındaki varsayılan üç görsel sınırından bağımsızdır; DB düğümü gelen payload daha fazla içerik görseli taşısa bile ilk beşini kalıcılaştıracak şekilde korunmuştur.

Bu medya ayrıştırma yaklaşımı iki avantaj sağlamaktadır. İlk olarak, haber görselleri kaynak sitedeki URL'nin daha sonra erişilemez hale gelmesinden bağımsız olarak sistem içinde korunur. İkinci olarak, VLM ve sonraki analiz/inceleme süreçleri için medya dosyalarına standart bir nesne deposu yolu üzerinden erişilebilir.

### Embedding ve Anlamsal Arama Desteği

DB düğümü, haber metinleri için vektör gömme üretme yeteneğine sahiptir. `EmbeddingManager`, varsayılan yerel modda `sentence-transformers` üzerinden `Qwen/Qwen3-Embedding-0.6B` modelini yüklemekte ve 1024 boyutlu vektör üretmektedir. PostgreSQL tarafında `pgvector` eklentisi etkinleştirilmekte ve `news` tablosunda `content_embedding vector(1024)` alanı oluşturulmaktadır.

Haber eklendikten sonra içerik metni mevcutsa `_store_embedding()` fonksiyonu çağrılır. Metin yaklaşık 8000 karakterle sınırlandırılır, embedding üretilir ve pgvector formatına uygun string temsil olarak `content_embedding` alanına yazılır. Bu işlem başarısız olursa hata loglanır; haber kaydının oluşturulması embedding hatasına bağlı olarak geri alınmaz.

Anlamsal arama `search_similar()` fonksiyonuyla sağlanmaktadır. Bu fonksiyon arama sorgusunu embedding'e dönüştürür ve PostgreSQL üzerinde pgvector kosinüs mesafesi operatörüyle en yakın haberleri sıralar. Sorgu kalıbı `ORDER BY content_embedding <=> query_vector` mantığına dayanır; sonuçlarda benzerlik skoru `1 - distance` olarak döndürülür.

> [!NOTE]
> **Şekil 3.10** — Embedding ve anlamsal arama akışı burada gösterilecektir. Haber metni → Qwen embedding modeli → `content_embedding vector(1024)` → pgvector benzerlik sorgusu adımları kullanılacaktır.

### CUA Çıktılarının Saklanması

DB düğümü yalnızca klasik Crawler pipeline çıktısını değil, CUA düğümünden gelen sonuçları da saklamaktadır. CUA yüzey ajanı tamamlandığında Orchestrator, toplanan makaleleri `agent_surface_articles` tipinde DB kuyruğuna yazar. DB düğümü bu payload içindeki her makaleyi ayrı haber kaydı olarak işler. Her makale için medya MinIO'ya aktarılır, `source_type` alanı `agent_surface` yapılır ve ilgili `mission_id` haber kaydına eklenir.

CUA makaleleri VLM veya LLM analizlerini kendi içinde taşıyorsa DB düğümü bu analizleri de standart `vlm_analysis` ve `llm_analysis` tablolarına yazar. Böylece CUA tarafından keşfedilen haberler ile Crawler tarafından toplanan haberler aynı ana veri modelinde birleşir; fark kaynak tipinin `crawler` veya `agent_surface` olmasından izlenebilir.

`research_mission` tipindeki payload'larda ise DB düğümü önce `research_missions` tablosunda görev kaydını oluşturur veya günceller. Durum tamamlanmışsa final rapor JSON'u, graph state JSON'u ve bulgu sayısı aynı tabloya yazılır. Bu yapı, CUA'nın haber satırı üretmeyen görev/rapor çıktılarının da kalıcı olarak izlenmesini sağlar.

### Paketleme ve Çalıştırma

DB düğümü `python:3.13-slim` tabanlı Docker imajı ile paketlenmiştir. Sistem bağımlılıkları arasında `netcat-openbsd` ve Python paketlerinin derlenmesi için `build-essential` bulunmaktadır. Python bağımlılıkları `asyncpg`, `minio`, `aiohttp`, `pika`, `grpcio`, `grpcio-tools`, `protobuf`, `python-dotenv`, `numpy` ve `sentence-transformers` paketlerinden oluşmaktadır. Dockerfile içinde ortak `orchestrator.proto` dosyasından DB tarafındaki gRPC kodları üretilmektedir.

Docker yapılandırmasında DB düğümü varsayılan olarak `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`, `MINIO_HOST=minio` ve `MINIO_PORT=9000` değerleriyle çalışacak şekilde hazırlanmıştır. `docker-compose.yml` içinde DB servisi Orchestrator, RabbitMQ, PostgreSQL ve MinIO servislerine bağımlı olarak tanımlanmıştır. Compose ortamında `ORCHESTRATOR_HOST`, `RABBITMQ_HOST`, PostgreSQL erişim bilgileri ve MinIO erişim bilgileri çevre değişkenleriyle verilmektedir.

DB düğümü bu haliyle sistemin kalıcı veri katmanını tek bir servis altında birleştirmektedir. PostgreSQL ilişkisel veri ve analiz kayıtlarını, pgvector anlamsal arama vektörlerini, MinIO ise haber görsellerini saklamaktadır. RabbitMQ tabanlı asenkron tüketim modeli sayesinde DB yazma işlemleri analiz hattından ayrıştırılmakta; Crawler, VLM, LLM ve CUA kaynaklı veriler ortak bir depolama modelinde bir araya getirilmektedir.

---
## 3.6 VLM Düğümü

VLM düğümü, haber görsellerini analiz eden görsel dil modeli servisidir. Crawler tarafından çıkarılan ve pipeline içinde VLM kuyruğuna gönderilen haber payload'ları bu düğüm tarafından işlenir. VLM'nin temel görevi, haberin ana görseli ve içerik görselleri üzerinde açıklama, nesne listesi, görsel duygu etiketi ve haberle ilgililik derecesi üretmektir.

Mevcut uygulamada VLM düğümü Orchestrator'a gRPC istemcisi olarak kayıt olmakta ve heartbeat göndermektedir. Fakat görevleri gRPC üzerinden doğrudan almamakta, RabbitMQ üzerindeki `vlm_tasks` kuyruğunu non-blocking poll modeliyle tüketmektedir. İşlenen sonuçlar ise `vlm_results` kuyruğuna yazılmaktadır. Orchestrator bu sonuç kuyruğunu takip ederek ilgili pipeline görevini bir sonraki aşama olan LLM analizine taşımaktadır.

### Çalışma Akışı

VLM düğümü başlatıldığında önce Orchestrator bağlantısını kurar, ardından RabbitMQ bağlantısını açar ve `vlm_tasks` ile `vlm_results` kuyruklarını declare eder. MinIO bilgileri sağlanmışsa `minio://` şemalı medya yollarını okuyabilmek için MinIO istemcisi de yapılandırılır. Model handler oluşturulduktan sonra modelin erişilebilirliği kontrol edilir; Transformers modunda model ilk görev geldiğinde yüklenebildiği için başlangıçta modelin hazır olmaması hata olarak ele alınmamaktadır.

Ana döngüde VLM düğümü `vlm_tasks` kuyruğundan mesaj okur. Mesaj varsa Crawler'dan gelen ham haber JSON'u ayrıştırılır. Haber metninin ilk 500 karakteri görsel analiz için bağlam olarak kullanılır. Daha sonra `media` alanındaki `main_image` ve `content_images` öğeleri sırayla işlenir.

Görsel kaynağı üç biçimde gelebilmektedir:

| Görsel biçimi | İşleme davranışı |
|---|---|
| HTTP/HTTPS URL | `aiohttp` ile indirilir |
| `minio://` yolu | MinIO istemcisiyle nesne deposundan okunur |
| Payload içinde `bytes` | Doğrudan model handler'a verilir |

Ana görsel varsa önce ana görsel analiz edilir. Ardından içerik görsellerinden en fazla üç tanesi işlenir. Her başarılı görsel için VLM model handler'ı çağrılır ve sonuç listesine `ImageAnalysisResult` nesnesi eklenir. Görev sonunda sonuçlar JSON formatına çevrilir ve `vlm_results` kuyruğuna yazılır.

Eğer payload görsel referansı taşıyorsa fakat hiçbir başarılı analiz üretilemezse görev sonucu `FAILED` olarak işaretlenir. Buna karşılık payload hiç görsel referansı taşımıyorsa, VLM sonucu boş olsa bile görev başarılı kabul edilmektedir. Bu ayrım, görselsiz haberlerin pipeline'ı gereksiz yere durdurmaması için uygulanmıştır.

> [!NOTE]
> **Şekil 3.11** — VLM işleme akışı burada gösterilecektir. `vlm_tasks` kuyruğu, görsel kaynağı seçimi, HTTP/MinIO okuma, model çıkarımı ve `vlm_results` kuyruğuna sonuç yazma adımları gösterilecektir.

### Model Çalıştırma Modları

VLM düğümü iki model çalışma modunu desteklemektedir. `MODEL_MODE=transformers` olduğunda model HuggingFace Transformers üzerinden aynı işlem içinde yüklenir. Bu modda `AutoModelForImageTextToText` ve `AutoProcessor` kullanılmaktadır. Model adı `PRODUCTION_MODEL` çevre değişkeniyle değiştirilebilir; kodda varsayılan değer `Qwen/Qwen3.5-9B` olarak verilmiştir.

Geliştirme veya yerel test senaryoları için ikinci yol LM Studio uyumlu OpenAI API modudur. `MODEL_MODE` transformers dışında olduğunda handler, `LM_STUDIO_HOST` üzerinde çalışan OpenAI uyumlu `/v1/chat/completions` endpoint'ine bağlanır. Bu modda görsel verisi base64 data URL formatına çevrilerek modele gönderilir. Varsayılan LM Studio model adı `qwen3-vl-2b-instruct` olarak tanımlanmıştır.

Her iki modda da modelden beklenen çıktı JSON yapısındadır:

| Alan | Anlamı |
|---|---|
| `description` | Görselin kısa, olgusal açıklaması |
| `objects` | Görselde tespit edilen nesne/öğe listesi |
| `sentiment` | `positive`, `negative` veya `neutral` |
| `relevance` | Haber içeriğiyle ilgililik: `high`, `medium`, `low` |

Model yanıtı JSON olarak ayrıştırılamazsa VLM handler, yanıt metnini açıklama alanına düşürerek nötr/orta varsayılan değerlerle sonuç üretmektedir. Hata durumunda ise sonuç nesnesinde `error` alanı doldurulmaktadır.

### Paketleme ve Dağıtım

VLM Docker imajı `python:3.11-slim` tabanı üzerine kurulmuştur. Python 3.11 tercihi, makine öğrenmesi kütüphaneleriyle uyumluluğu artırmak içindir. Dockerfile içinde `MODEL_MODE=transformers` varsayılan olarak tanımlanmıştır. Sistem bağımlılıkları arasında `netcat-openbsd` ve `git` bulunmaktadır. Ortak `orchestrator.proto` dosyasından VLM tarafındaki gRPC kodları imaj oluşturma aşamasında üretilmektedir.

Dockerfile yorumlarında VLM düğümü için NVIDIA GPU ve yaklaşık 24 GB üzeri VRAM gereksinimi belirtilmiştir. `docker-compose.yml` içinde VLM servisi varsayılan olarak yorum satırı durumundadır; bunun nedeni model boyutu ve GPU gereksinimleridir. Uygun donanımda çalıştırıldığında düğüm `ORCHESTRATOR_HOST`, `RABBITMQ_HOST` ve gerektiğinde MinIO bağlantı bilgileriyle dağıtık sisteme katılmaktadır.

## 3.7 LLM Düğümü

LLM düğümü, haber metni ve VLM görsel analiz sonuçlarını kullanarak yapılandırılmış metin analizi üreten servis bileşenidir. Pipeline'da VLM aşaması tamamlandıktan sonra Orchestrator ham haber verisi ile VLM sonucunu birleştirir ve `llm_tasks` kuyruğuna yazar. LLM düğümü bu kuyruğu tüketerek haber özeti, duygu analizi, anahtar kelimeler, varlıklar, kategori ve konuya ilgililik alanlarını üretir.

VLM düğümünde olduğu gibi LLM düğümü de Orchestrator'a gRPC üzerinden kayıt olmakta ve heartbeat göndermektedir; görevleri ise RabbitMQ üzerinden almaktadır. İşlenen sonuçlar `llm_results` kuyruğuna yazılır. Orchestrator bu sonucu aldığında haber pipeline'ını tamamlanmış sayar ve ham haber, VLM sonucu ve LLM sonucunu DB kuyruğuna aktarır.

### Çalışma Akışı

LLM düğümü başlatıldığında Orchestrator bağlantısı, RabbitMQ bağlantısı ve model handler hazırlanır. RabbitMQ üzerinde `llm_tasks` ve `llm_results` kuyrukları declare edilir. Ana döngü `llm_tasks` kuyruğundan mesaj okur; mesaj yoksa kısa süre bekleyip tekrar dener.

Gelen görev payload'ı çoğunlukla iki parçadan oluşur:

| Alan | İçerik |
|---|---|
| `original` | Crawler tarafından üretilen ham haber verisi |
| `vlm_analysis` | VLM düğümünün ürettiği görsel analiz sonuçları |

LLM düğümü `original` alanından kaynak, başlık ve içerik bilgisini çıkarır. Başlık varsa analiz metni `[Source: ...]`, başlık ve içerik birleşiminden oluşturulur; başlık yoksa doğrudan içerik kullanılır. VLM sonuçları liste formatına dönüştürülür ve model handler'a ek bağlam olarak verilir. Böylece metin analizi yalnızca haber metnine değil, varsa haber görsellerinden çıkarılan açıklama ve nesne bilgilerine de dayanır.

Analiz tamamlandıktan sonra `TextAnalysisResult` nesnesi JSON'a çevrilir. Hata alanı boşsa sonuç `SUCCESS`, hata varsa `FAILED` durumuyla `llm_results` kuyruğuna yazılır.

### Üretilen Analiz Alanları

LLM düğümünün sistem prompt'u haber analizi için yapılandırılmış JSON çıktısı istemektedir. Beklenen çıktı alanları şunlardır:

| Alan | Anlamı |
|---|---|
| `summary` | Haberin 2-3 cümlelik özeti |
| `sentiment` | Sayısal duygu değeri: `-1`, `0`, `1` |
| `sentiment_label` | `negative`, `neutral` veya `positive` |
| `keywords` | Haberi temsil eden anahtar kelimeler |
| `entities` | Ülkeler, kurumlar ve kişiler gibi varlıklar |
| `category` | `politics`, `economy`, `sports`, `technology` veya `other` |
| `relevance_to_topic` | Konuya ilgililik: `high`, `medium`, `low` |

Model yanıtı geçerli JSON içermiyorsa handler, yanıt metninin ilk kısmını özet alanına alarak nötr duygu ve varsayılan kategori değerleriyle fallback sonuç üretmektedir. Bu tercih, modelin biçimsel çıktı hatası verdiği durumlarda pipeline'ın tamamen durmasını engellemektedir.

### Model Çalıştırma Modları

LLM düğümü de VLM gibi iki çalışma moduna sahiptir. `MODEL_MODE=transformers` olduğunda `AutoModelForCausalLM` ve `AutoTokenizer` üzerinden HuggingFace Transformers modeli aynı süreç içinde yüklenir. Varsayılan üretim modeli `Qwen/Qwen3-8B` olarak tanımlanmıştır. Model ilk analiz çağrısında yüklenir ve sonra aynı handler içinde kullanılır.

Transformers modunda istemler chat template ile tokenize edilir, üretim `do_sample=False` olacak şekilde deterministik yürütülür ve en fazla 800 yeni token üretilir. LM Studio modunda ise OpenAI uyumlu `/v1/chat/completions` endpoint'i kullanılır; varsayılan model adı `qwen3-8b` olarak verilmiştir. Bu mod yerel geliştirme ve ayrı çalışan model sunucusu senaryoları için kullanılmaktadır.

### VLM Sonuçlarının Metin Analizine Katılması

LLM analizinde VLM çıktıları isteğe bağlı bağlam olarak kullanılır. VLM sonucu mevcutsa her görsel için açıklama, nesne listesi ve görsel duygu etiketi metin istemine eklenir. Bu sayede haber metninde açıkça bulunmayan görsel bağlam, özetleme ve duygu/kategori değerlendirmesine yardımcı olabilir. Örneğin bir haber metni kısa veya eksik olsa bile, görsel açıklaması olay yeri, kişi, nesne veya atmosfer hakkında ek sinyal sağlayabilir.

Mevcut kodda LLM düğümü VLM sonucunu doğrudan değiştirmez; yalnızca analiz bağlamı olarak kullanır. Nihai LLM sonucu, Orchestrator üzerinden DB düğümüne aktarılır ve `llm_analysis` tablosuna kaydedilir.

### Paketleme ve Dağıtım

LLM Docker imajı `python:3.11-slim` tabanı üzerine kurulmuştur. Dockerfile içinde `MODEL_MODE=transformers` varsayılan değerdir. Sistem bağımlılıkları `netcat-openbsd` ve `git`; Python bağımlılıkları ise Transformers tabanlı model çalıştırma, RabbitMQ, gRPC ve yardımcı paketleri içermektedir. Ortak `orchestrator.proto` dosyasından LLM tarafındaki gRPC kodları build sırasında üretilmektedir.

Dockerfile yorumlarında LLM düğümü için NVIDIA GPU ve yaklaşık 16 GB üzeri VRAM gereksinimi belirtilmiştir. `docker-compose.yml` içinde LLM servisi de VLM gibi varsayılan olarak yorum satırı durumundadır. Uygun GPU ortamında çalıştırıldığında düğüm `llm_tasks` kuyruğundan görev alıp `llm_results` kuyruğuna sonuç yazarak haber analiz zincirinin son model çıkarımı aşamasını tamamlamaktadır.

---
## 3.8 CUA (Computer Using Agent) Düğümü

CUA düğümü, sistemde otonom web araştırması yürüten ajan bileşenidir. Pipeline'ın Crawler kolu önceden tanımlı haber kaynakları üzerinden veri toplarken, CUA düğümü Orchestrator tarafından verilen bir konu veya sorgu etrafında web araması yapar, sayfaları ziyaret eder, haber niteliğindeki içerikleri ayıklar, kalite kapısından geçirir, analiz eder ve sonunda yapılandırılmış bir yüzey araştırması raporu üretir.

Mevcut implementasyonda CUA'nın tamamlanmış ve aktif görev tipi `surface` modudur. Bu mod, haber odaklı yüzey araştırması yapmak, bulunan makaleleri Crawler uyumlu veri formatına dönüştürmek ve Orchestrator üzerinden DB katmanına aktarılabilecek yapılandırılmış çıktı üretmek için kullanılmaktadır. `deep_research` benzeri daha derin araştırma görevleri için mimaride genişleme açıklığı bırakılmıştır; ancak mevcut kodda `surface` dışındaki modlar çalıştırılmamakta, `run_agent()` fonksiyonu tarafından başarısız sonuçla döndürülmektedir. Bu nedenle bu bölümde anlatılan çalışan ajan, haber odaklı ve kontrollü surface araştırma ajanıdır.

CUA tasarımı geliştirme sürecinde serbest ajan yaklaşımından daha kontrollü bir motor yapısına evrilmiştir. İlk yaklaşımda LLM'in arama, gezinme ve durma kararlarını daha serbest biçimde üretmesi hedeflenmiş; ancak bu tarz free-form ajan davranışı sonsuz döngüye girme, CAPTCHA veya güvenlik sayfalarına takılma ve tutarsız çıktı üretme riskini artırmıştır. Son yapıda ajan, LangGraph ile tanımlanmış sıkılaştırılmış bir yürütme motoru olarak konumlandırılmıştır. LLM yalnızca sorgu planı üretme, makale kalite kapısı, makale analizi ve final sentez gibi belirli karar/çıkarım noktalarında devreye girmekte; navigasyon sırası, sayaçlar, durdurma koşulları, tekrar önleme ve kaynak filtreleme gibi akış kontrolü ise deterministik Python kurallarıyla yürütülmektedir.

Bu mimari tercihin sonucu olarak CUA'da LLM, tüm akışı tek başına yöneten merkezi bir karar verici değildir. Akışın iskeleti Python kodu ve LangGraph durum grafiği tarafından yönetilmekte; arama mı yapılacağı, sıradaki URL'nin mi ziyaret edileceği, döngünün durdurulup durdurulmayacağı ve güvenlik sınırları Python tarafındaki sayaçlar, kuyruklar ve guardrail kontrolleriyle belirlenmektedir.

### Düğüm Yaşam Döngüsü

CUA düğümünün giriş noktası `cua/main.py` dosyasındaki `CUANode` sınıfıdır. Başlatma sırasında sırasıyla Orchestrator bağlantısı, tarayıcı oturumu, model handler ve RabbitMQ bağlantısı hazırlanır. Orchestrator bağlantısı başarılı olursa düğüm `cua` tipiyle kayıt olur ve heartbeat döngüsü başlatılır. Bağlantı başarısız olursa kod `cua_standalone` kimliğiyle devam edebilmekte; ancak görev işlemek için RabbitMQ, tarayıcı ve model bileşenlerinin hazır olması gerekmektedir.

CUA, görevleri `agent_tasks` kuyruğundan alır ve sonuçları `agent_results` kuyruğuna yazar. RabbitMQ consumer `prefetch_count=1` ile çalışmaktadır; bu sayede düğüm aynı anda tek görev üzerinde yoğunlaşır. Bir görev başarıyla işlenip sonuç kuyruğuna yazıldıktan sonra mesaj `ack` edilir. Sonuç yayınlanamazsa mesaj `nack` edilerek yeniden kuyruğa alınabilir.

CUA runtime sağlığı `HealthState` üzerinden izlenmektedir. Sağlık durumunda düğümün çalışıp çalışmadığı, hazır olup olmadığı, Orchestrator'a kayıt durumu, RabbitMQ bağlantısı, tarayıcı hazırlığı, model hazırlığı ve aktif görev kimliği gibi alanlar tutulur. Docker healthcheck de bu sağlık dosyasını kullanan `cua.healthcheck` modülü üzerinden çalışmaktadır.

### LangGraph Durum Grafiği

CUA'nın ajan akışı `cua/agent/graph.py` içinde LangGraph `StateGraph` ile tanımlanmıştır. Grafikte dört temel düğüm bulunmaktadır:

| Graph düğümü | Görev |
|---|---|
| `plan` | Bir sonraki mekanik eylemi belirler: arama, URL ziyareti veya tamamlama |
| `execute` | Arama veya sayfa çıkarımı işlemini BrowserTool ile yürütür |
| `evaluate` | Sayaçlara ve ilerlemeye göre döngünün devam edip etmeyeceğini belirler |
| `synthesize` | Toplanan makalelerden final raporu üretir |

Akış `plan → execute → evaluate` döngüsüyle ilerler. `evaluate` düğümü `should_stop` alanını `True` yaparsa akış `synthesize` düğümüne, aksi halde tekrar `plan` düğümüne gider. `synthesize` tamamlandığında LangGraph `END` durumuna ulaşılır.

Agent state yapısı `AgentState` TypedDict'iyle tanımlanmıştır. Bu durumda görev modu, sorgu, konu, görev parametreleri, ziyaret edilen URL'ler, dışlanacak URL'ler, toplanan makaleler, döngü sayacı, durma bayrağı, final rapor ve hata alanları yer alır. Ayrıca ajan içi bellek olarak son eylem, arama sonuçları, daha önce denenmiş sorgular, bekleyen URL kuyruğu, arama sayısı, ilerleme olmayan döngü sayısı, son aramadan beri reddedilen ve ziyaret edilen sayfalar gibi alanlar taşınmaktadır.

> [!NOTE]
> **Şekil 3.12** — CUA LangGraph durum çizgesi burada gösterilecektir. `plan`, `execute`, `evaluate`, `synthesize` düğümleri, koşullu dönüş ve `END` durumu diyagramda yer alacaktır.

### Planlama ve Guardrail Mekanizması

CUA'da planlama tamamen serbest LLM eylem seçimi değildir. `plan_node`, mevcut state'e bakarak önce durdurma koşullarını kontrol eder. Maksimum döngü sayısı, maksimum arama sayısı ve maksimum makale sayısı aşılmışsa eylem `complete` yapılır. Bekleyen URL kuyruğu varsa ve yeni arama yapmayı gerektiren özel bir durum yoksa sıradaki URL ziyaret edilir. Bekleyen URL yoksa veya ilerleme için yeni arama gerekiyorsa sorgu planı kullanılarak arama eylemi oluşturulur.

Arama sorgularının üretiminde LLM ve deterministik fallback birlikte kullanılır. İlk sorgu planı `CUAModelHandler.generate_query_plan()` ile LLM'den istenir. Modelden gelen sorgular doğrudan kullanılmadan önce zayıf sorgu kontrolünden geçirilir. Çok genel sorgular, boş sorgular, konu terimlerini taşımayan sorgular ve daha önce denenmiş sorgular elenir. Kullanılabilir sorgu bulunamazsa `SearchStrategy.generate_queries()` şablonları ve toplanan son içeriklerden çıkarılan anahtar kelimelerle fallback sorgular oluşturulur.

Bu guardrail katmanı, ajanın “latest news” gibi genel ve bağlamsız aramalara sapmasını, aynı sorguyu tekrar tekrar denemesini veya ana konudan kopmasını azaltmak için uygulanmıştır. Arama çeşitlendirmesi yine mümkündür; ancak çeşitlilik, konu ile ilişkili kalma şartıyla sınırlandırılmıştır.

### Execute Aşaması: Arama ve Sayfa Ziyareti

`execute_node`, `plan_node` tarafından belirlenen mekanik eylemi uygular. Eylem `search` ise `BrowserTool.search()` çağrılır. Varsayılan arama motoru config içinde `duckduckgo` olarak tanımlanmıştır. `bing` ve `auto` seçenekleri de desteklenmektedir. `auto` modunda önce DuckDuckGo, gerekirse DuckDuckGo HTML endpoint'i ve ardından Bing News RSS denenmektedir.

Arama sonuçları geldikten sonra CUA, Crawler tarafından zaten kapsanan kaynakları ve yüzey ajanı için uygun görülmeyen alan adlarını filtreler. Varsayılan dışlanan alan adları arasında BBC, CNN International, Al Jazeera ve diğer Crawler kaynakları bulunmaktadır. Ayrıca Wikipedia, Britannica, World Bank, IMF ve benzeri ansiklopedi/istatistik kaynakları surface mod için engellenmiştir. Böylece CUA, Crawler'ın varsayılan kaynak listesiyle aynı alanda tekrar toplama yapmak yerine daha keşifsel bir haber araması yürütür.

Eylem `visit` ise `BrowserTool.extract_page()` ile hedef URL açılır. Tarayıcı oturumu Playwright Chromium üzerinde tek bir persistent page yaklaşımıyla tutulur. Sayfa açıldıktan sonra yaygın popup/çerez butonları kapatılmaya çalışılır, sayfa bir miktar kaydırılır ve DOM üzerinden başlık, açıklama, içerik, görsel adayları ve aynı domain içindeki olası makale bağlantıları çıkarılır.

Sayfa çıkarımı sırasında haber dışı DOM alanları temizlenir. `nav`, `header`, `footer`, `aside`, `script`, `style`, `form`, related/popular/newsletter/comment gibi alanlar ve Taboola/promoted benzeri bölümler içerik dışı bırakılır. İçerik yeterli değilse gövde metninden fallback çıkarım yapılır. Sayfa HTTP hata kodu, Cloudflare hata metinleri, CAPTCHA/human verification işaretleri ve error page belirtileri açısından kontrol edilir.

### ContentExtractor ve Crawler Uyumlu Makale Formatı

CUA'nın çıkardığı ham sayfa verisi, `ContentExtractor.extract_from_raw()` ile Crawler uyumlu haber formatına dönüştürülmektedir. Bu tasarım, CUA tarafından bulunan makalelerin downstream depolama ve analiz katmanında Crawler haberleriyle aynı veri modeli üzerinden işlenebilmesini sağlamaktadır.

Dönüştürülen makale formatında kaynak, ülke, URL, arama anahtar kelimesi, toplanma zamanı, başlık, içerik, açıklama, medya bilgisi ve `source_type='agent_surface'` alanı bulunmaktadır. Kaynak adı URL host bilgisinden çıkarılır. Ülke bilgisi bilinen haber domainleri için sabit eşlemeden, diğer durumlarda ccTLD üzerinden tahmin edilir; eşleşme yoksa `unknown` kullanılır.

Makale geçerliliği için URL, başlık ve en az 200 karakter içerik şartı aranır. Ayrıca Cloudflare, CAPTCHA, erişim engeli ve hata sayfası belirtileri taşıyan sayfalar geçersiz kabul edilir. Bu geçerlilik kontrolünden geçen makaleler LLM kalite kapısına gönderilir.

### LLM Kalite Kapısı ve Makale Analizi

CUA'da aday bir makalenin kabul edilmesi iki aşamalı bir süreçtir. İlk olarak `ContentExtractor.is_valid_article()` ile deterministik geçerlilik kontrolü yapılır. Ardından `CUAModelHandler.assess_article_quality()` çağrılır. Bu fonksiyon önce bazı bariz hata/security/product/marketplace durumlarını sezgisel olarak eleyebilir; uygun görünen adaylar için LLM'e kısa bir kalite kapısı prompt'u gönderilir.

Kalite kapısında modelden şu alanları içeren JSON yanıt beklenir:

| Alan | Anlamı |
|---|---|
| `accept` | Makale kabul edilsin mi: `1` veya `0` |
| `reason` | Kısa kabul/ret gerekçesi |
| `page_type` | `news_article`, `report`, `product`, `security_wall`, `error`, `category`, `seo_spam`, `unrelated` vb. |
| `relevance` | Konuya ilgililik: `high`, `medium`, `low` |

`page_type` geçersiz sayfa türlerinden biriyse veya ilgililik `low` ise makale reddedilir. Kabul edilen makale için `CUAModelHandler.analyze_article()` çağrılır. Bu çağrı makaleye `llm_analysis` ve `vlm_analysis` alanlarını ekler. Metin analizi özet, duygu, anahtar kelime, varlık, kategori ve konuya ilgililik üretir. Görsel analizi için ana görsel ve içerik görsellerinden `CUA_MAX_IMAGES_PER_ARTICLE` sınırına kadar olanlar ayrı ayrı değerlendirilir.

Kabul edilen makale `collected_articles` listesine eklenir. Reddedilen makalelerde reddedilme sayacı artırılır; sayfa içinde başka makale bağlantıları varsa ve sayfa tipi güvenlik/ürün/hata gibi kötü sınıflardan değilse bu bağlantılar bekleyen URL kuyruğuna eklenebilir.

### Durdurma Koşulları

CUA'nın döngüsü açık uçlu değildir. `evaluate_node`, her döngü sonunda şu koşulları değerlendirir:

| Koşul | Anlamı |
|---|---|
| `max_articles` | Hedef makale sayısına ulaşıldı |
| `max_searches` | Arama sayısı sınırına ulaşıldı ve bekleyen URL kalmadı |
| `max_cycles` | Toplam graph döngüsü sınırına ulaşıldı |
| `max_no_progress_cycles` | Belirli sayıda döngü boyunca yeni makale veya URL ilerlemesi olmadı |
| `error` | Akışı durduracak hata oluştu |

Bu sınırlar Orchestrator'dan gelen `params` alanı ile görev bazında belirlenebilir. Orchestrator tarafındaki varsayılan CUA parametreleri `max_articles=10`, `max_searches=20` ve `max_cycles=12` olarak oluşturulmaktadır. Bu yapı, ajanın sonsuz arama/ziyaret döngüsüne girmesini engelleyen temel güvenlik katmanıdır.

### Sentez ve Sonuç Yayınlama

Durdurma koşulu oluştuğunda akış `synthesize` düğümüne geçer. Bu düğüm `CUAModelHandler.synthesize_report()` fonksiyonunu çağırarak toplanan makalelerden yapılandırılmış bir final raporu üretir. Surface modda beklenen rapor; özet, makale sayısı, kaynak listesi, üst anahtar kelimeler ve temel bulgular gibi alanlar içerir.

Eğer surface modda hiç geçerli makale toplanamazsa `run_agent()` görev sonucunu `FAILED` durumuyla döndürür. Makale toplanmışsa sonuç `COMPLETED` olarak işaretlenir, durma nedeni `stop_reason` alanına eklenir ve `articles` listesi final rapora dahil edilir. `CUANode`, bu sonucu görev kimliği ve mod bilgisiyle birlikte `agent_results` kuyruğuna yayınlar.

Orchestrator, CUA yüzey ajanı sonucunu aldığında toplanan makaleleri DB kuyruğuna `agent_surface_articles` payload'ı olarak aktarır. DB düğümü bu makaleleri `source_type='agent_surface'` alanıyla `news` tablosuna kaydeder ve varsa makale içi LLM/VLM analizlerini standart analiz tablolarına yazar.

> [!NOTE]
> **Şekil 3.13** — CUA sonuç akışı burada gösterilecektir. `agent_tasks` kuyruğu, LangGraph döngüsü, `agent_results` kuyruğu, Orchestrator ve DB'ye `agent_surface_articles` aktarımı gösterilebilir.

### Paketleme ve Çalıştırma

CUA Dockerfile çok aşamalı yapıdadır. İlk aşamada `python:3.11-slim` üzerinde Playwright ve Chromium binary'leri hazırlanır. İkinci aşama `nvidia/cuda:12.1.0-runtime-ubuntu22.04` tabanlı runtime imajıdır. Bu aşamada Python 3.11, Chromium için gerekli sistem kütüphaneleri, CUA Python bağımlılıkları ve proje dosyaları kurulur. Playwright browser binary'leri ilk aşamadan runtime imajına kopyalanır.

Container içinde varsayılan olarak `MODEL_MODE=local`, `LMSTUDIO_URL=http://host.docker.internal:1234/v1`, `ORCHESTRATOR_HOST=orchestrator`, `RABBITMQ_HOST=rabbitmq`, `CUA_GRPC_PORT=50054` ve `CUA_HEALTH_FILE=/tmp/cua_health.json` değerleri tanımlıdır. `docker-compose.yml` içinde CUA için `shm_size: '2gb'` verilmiştir; bu ayar Playwright/Chromium'un container içinde daha kararlı çalışması için kullanılmaktadır. CUA servisi ayrıca healthcheck ile izlenmektedir.

CUA düğümü bu haliyle sistemin en esnek veri keşif bileşenidir. Ancak bu esneklik sınırsız bir ajan serbestliğiyle değil, LangGraph ile tanımlanan kontrollü bir durum makinesi, deterministik guardrail'ler ve belirli LLM çıkarım noktalarıyla sağlanmaktadır. Bu tasarım, haber toplama sistemi içinde otonom araştırma kabiliyeti eklerken, görev sınırlarının ve çıktı formatının korunmasını amaçlamaktadır.

---
## 3.9 Dağıtım ve Operasyon

Sistemin dağıtım yaklaşımı, her ana bileşenin ayrı bir servis olarak paketlenmesine dayanmaktadır. Orchestrator, Crawler, DB ve CUA düğümleri kendi Dockerfile tanımlarıyla imaj haline getirilmekte; RabbitMQ, PostgreSQL/pgvector ve MinIO ise hazır altyapı imajları üzerinden çalıştırılmaktadır. Bu yapı, haber toplama, analiz, ajan araştırması ve kalıcı depolama işlevlerinin birbirinden bağımsız container'lar halinde başlatılmasını sağlamaktadır.

Yerel Compose yapılandırmasında servisler `bitirme-net` adlı bridge network üzerinde aynı sanal ağda çalışmaktadır. Servisler birbirlerine dış IP adresleriyle değil, Compose servis adlarıyla erişir. Örneğin DB düğümü PostgreSQL'e `postgres`, MinIO'ya `minio`, RabbitMQ'ya `rabbitmq` host adıyla bağlanır. Orchestrator ise worker düğümleri için merkezi kayıt ve koordinasyon noktası olarak `orchestrator:50051` adresinde konumlanmaktadır.

Mevcut Compose dosyasında çekirdek çalışma ortamı şu bileşenlerden oluşmaktadır:

| Bileşen | Dağıtım rolü |
|---|---|
| `orchestrator` | gRPC koordinasyon sunucusu ve operasyonel kontrol bileşeni |
| `rabbitmq` | Analiz, depolama ve ajan görevleri için mesaj aracısı |
| `crawler` | Orchestrator'dan crawl görevi alan haber toplama düğümü |
| `db` | PostgreSQL, pgvector ve MinIO ile kalıcı kayıt işlemlerini yürüten düğüm |
| `postgres` | Haber, analiz ve araştırma kayıtlarının ilişkisel/vektörel veritabanı |
| `minio` | Haber görselleri için S3 uyumlu nesne depolama katmanı |
| `cua` | Playwright ve model bağlantısı kullanan otonom yüzey araştırması düğümü |

VLM ve LLM servisleri de Compose dosyasında tanımlanmış, ancak GPU ve model boyutu gereksinimleri nedeniyle varsayılan durumda yorum satırı olarak bırakılmıştır. Bu tercih, temel sistemin daha hafif bir ortamda başlatılabilmesini; model çıkarımı gerektiren düğümlerin ise uygun GPU ortamında ayrıca devreye alınabilmesini sağlamaktadır. CUA servisi ise Playwright/Chromium çalıştırdığı için `shm_size` ayarı ve healthcheck tanımıyla birlikte paketlenmiştir.

### Yapılandırma

Servisler arası bağlantılar ortam değişkenleriyle tanımlanmaktadır. Orchestrator için gRPC portu ve RabbitMQ bağlantısı; DB düğümü için Orchestrator, RabbitMQ, PostgreSQL ve MinIO bağlantı bilgileri; CUA için Orchestrator, RabbitMQ, model endpoint'i, tarayıcı modu ve sağlık dosyası yolu container ortamına değişken olarak aktarılmaktadır. Bu yapı, aynı kodun farklı çalışma ortamlarında bağlantı adresleri değiştirilerek kullanılmasına imkân verir.

Dış dünyaya açılan portlar geliştirme ve gözlem ihtiyaçlarına göre belirlenmiştir. RabbitMQ AMQP trafiği için `5672`, yönetim arayüzü için `15672`; PostgreSQL için `5432`; MinIO API için `9000`, konsol için `9001`; Orchestrator gRPC için `50051`; DB ve CUA düğümleri için sırasıyla `50053` ve `50054` portları kullanılmaktadır.

### Operasyonel İzleme

Operasyon tarafında sistemin temel görünürlüğü Orchestrator'ın düğüm kayıt ve heartbeat mekanizmasıyla sağlanmaktadır. Worker düğümleri kayıt olduktan sonra durumlarını periyodik olarak bildirir; Orchestrator bu bilgiler üzerinden aktif, boşta, hatalı veya çevrimdışı düğümleri izleyebilir. RabbitMQ yönetim arayüzü kuyruk doluluğu ve mesaj akışını, MinIO konsolu ise nesne depolama durumunu gözlemlemek için kullanılmaktadır.

CUA düğümünde ek olarak dosya tabanlı bir sağlık durumu tutulmakta ve Docker healthcheck bu durum üzerinden container'ın hazır olup olmadığını denetlemektedir. Bu mekanizma özellikle tarayıcı oturumu, RabbitMQ bağlantısı, model handler ve Orchestrator kaydı gibi birden fazla bağımlılığa sahip CUA düğümünün çalışma durumunu izlemek için kullanılmaktadır.

Orchestrator içinde yer alan HTTP operasyon paneli, sistemin yönetilebilir prototip niteliğini desteklemektedir. Panel üzerinden sistem özeti, düğüm listesi, araştırma görevleri, crawl başlatma/durdurma, kayıt arama ve yedekleme işlemleri gibi temel operasyonel işlevler yürütülebilmektedir.

### Veri Sürekliliği

Kalıcı veri iki ana katmanda tutulmaktadır. PostgreSQL container'ı `postgres-data` volume'u ile haber, analiz ve araştırma kayıtlarını korur. MinIO container'ı ise `minio-data` volume'u ile haber görsellerini ve medya nesnelerini saklar. RabbitMQ tarafında kuyruklar durable olarak tanımlanmakta ve Orchestrator tarafından yayımlanan görev mesajları kalıcı mesaj olarak gönderilmektedir.

Mevcut prototip tek Orchestrator, tek RabbitMQ, tek PostgreSQL ve tek MinIO örneği üzerinden çalışmaktadır. Bu nedenle dağıtım yapısı, çok düğümlü yüksek erişilebilirlik kurulumundan ziyade geliştirme, doğrulama ve tez kapsamında sistem davranışını gösterebilecek kontrollü bir prototip ortamı olarak konumlanmaktadır.

> [!NOTE]
> **Şekil 3.14** — Dağıtım görünümü burada gösterilecektir. `bitirme-net` ağı üzerindeki servisler, dışa açılan portlar, kalıcı volume'lar ve GPU gerektiren düğümlerin konumu diyagramda yer alacaktır.

---
## 3.10 Protocol Buffers Tanımları

Sistemde gRPC ile yürütülen kontrol düzlemi iletişiminin sözleşmesi `proto/orchestrator.proto` dosyasında tanımlanmaktadır. Bu dosya, Orchestrator ile worker düğümleri arasında kullanılan ortak mesaj tiplerini, durum enum'larını ve servis metotlarını merkezi bir kaynakta toplar. Böylece Orchestrator, Crawler, DB, VLM, LLM ve CUA düğümleri aynı arayüz tanımından üretilen Python sınıflarını kullanır.

Proto dosyası `proto3` sözdizimini ve `bitirme` paket adını kullanmaktadır. Ortak mesajlar içinde düğüm kaydı için `RegisterRequest` / `RegisterResponse`, sağlık bildirimi için `HeartbeatRequest` / `HeartbeatResponse`, düğüm durumu için `NodeStatus`, görev sonucu için ise `TaskStatus` enum'u tanımlanmıştır. `NodeStatus` tarafında `IDLE`, `BUSY` ve `ERROR`; `TaskStatus` tarafında ise `SUCCESS`, `FAILED` ve `TIMEOUT` durumları yer almaktadır.

Kontrol düzleminde aktif olarak kullanılan ana servis `OrchestratorService` servisidir. Bu servis, düğümlerin sisteme katılması, heartbeat göndermesi, Crawler'ın görev istemesi ve analiz sonuçlarının Orchestrator'a raporlanması için kullanılmaktadır:

| RPC | Kullanım amacı |
|---|---|
| `Register` | Düğümün Orchestrator'a kayıt olup `node_id` alması |
| `Heartbeat` | Düğüm durumunun periyodik olarak bildirilmesi |
| `GetCrawlTask` | Crawler'ın poll modeliyle görev istemesi |
| `ReportCrawlResult` | Crawler çıktısının Orchestrator'a iletilmesi |
| `ReportImageAnalysis` | VLM sonucunun Orchestrator'a iletilmesi |
| `ReportTextAnalysis` | LLM sonucunun Orchestrator'a iletilmesi |
| `ReportStoreResult` | DB kayıt sonucunun Orchestrator'a iletilmesi |
| `ReportQueueData` | DB tarafındaki kuyruk verisinin Orchestrator'a raporlanması |

Crawler tarafında `GetCrawlTaskRequest` ve `GetCrawlTaskResponse` mesajları poll modelini destekler. Crawler, kayıt olduktan sonra Orchestrator'a düzenli olarak görev olup olmadığını sorar; görev varsa `task_id`, URL listesi ve opsiyonel `config_json` alanı döndürülür. Crawl sonucu ise `CrawlTaskResponse` içinde `task_id`, durum, JSON veri ve hata mesajı alanlarıyla raporlanır.

VLM ve LLM tarafında proto sözleşmesi sonuç raporlama mesajlarını da tanımlar. VLM için `AnalyzeImagesResponse`, görev kimliği, durum, görsel analiz JSON'u ve hata mesajı taşır. LLM için `AnalyzeTextResponse`, görev kimliği, durum, özet, sayısal duygu değeri, tam analiz JSON'u ve hata mesajı alanlarını içerir. Mevcut pipeline'da analiz görevlerinin dağıtımı RabbitMQ kuyruklarıyla yapılmakta; gRPC ise kayıt, heartbeat ve sonuç raporlama tarafında kullanılmaktadır.

Proto dosyasında ayrıca `CrawlerService`, `DatabaseService`, `VLMService` ve `LLMService` adlı worker servis tanımları da bulunmaktadır. Ancak mevcut haber işleme akışında Orchestrator'ın VLM, LLM ve DB düğümlerine doğrudan RPC çağrısıyla görev göndermesi yerine RabbitMQ görev kuyrukları kullanılmaktadır. Bu nedenle çalışan mimaride ana sözleşme `OrchestratorService` ve RabbitMQ mesaj payload'ları etrafında şekillenmektedir.

### JSON Payload Tercihi

Proto mesajlarında bazı alanlar doğrudan yapılandırılmış alt mesajlar olarak değil, `json_data`, `analysis_json`, `text_json`, `image_analysis_json` ve `full_analysis_json` gibi string alanlar içinde JSON olarak taşınmaktadır. Bu tercih, haber içeriği, medya listeleri, model çıktıları ve ajan sonuçları gibi sık değişebilen veri yapılarının proto dosyasını sürekli değiştirmeden aktarılabilmesini sağlamaktadır.

Bu yaklaşımın temel avantajı esnekliktir. Crawler çıktısı, VLM analizi, LLM analizi veya CUA kaynaklı makale formatı genişletildiğinde, her küçük alan değişimi için protobuf sözleşmesinin yeniden tasarlanması gerekmez. Buna karşılık JSON gövdesinin iç yapısı protobuf tarafından derleme zamanında doğrulanmaz; doğrulama ve hata yönetimi ilgili servis kodlarının sorumluluğunda kalır. Mevcut prototipte bu değiş-tokuş, hızlı geliştirme ve farklı analiz çıktılarının aynı pipeline içinde taşınabilmesi açısından uygun görülmüştür.

### Kod Üretimi

Proto dosyasından Python kodu üretimi `compile_proto.py` betiğiyle yapılmaktadır. Betik, merkezi `proto/orchestrator.proto` dosyasını Orchestrator, Crawler, DB, VLM, LLM ve CUA düğümlerinin kendi `proto` klasörlerine kopyalar; ardından `grpc_tools.protoc` ile `orchestrator_pb2.py` ve `orchestrator_pb2_grpc.py` dosyalarını üretir. Üretilen dosyalar her düğümün `generated` klasörü altında tutulmaktadır.

Python gRPC üreticisi varsayılan olarak düz import ürettiği için betik, `orchestrator_pb2_grpc.py` içindeki import satırını paket içi göreli import biçimine çevirir. Bu düzenleme sayesinde her düğüm kendi `generated` modülünü bağımsız olarak import edebilir. Dockerfile tanımlarında da aynı import düzeltmesi build aşamasında uygulanmaktadır.

Bu yapı, servis sözleşmesinin tek dosyada merkezileşmesini ve tüm düğümlerin aynı mesaj/RPC tanımından türeyen istemci-sunucu sınıflarını kullanmasını sağlar. Böylece gRPC tarafındaki arayüz değişiklikleri kontrollü biçimde `orchestrator.proto` üzerinden yapılmakta; üretilen kodlar ilgili düğümlere dağıtılmaktadır.

> [!NOTE]
> **Şekil 3.15** — Protocol Buffers kod üretim akışı burada gösterilecektir. `orchestrator.proto` dosyasından `compile_proto.py` aracılığıyla her düğümün `generated` klasörüne `orchestrator_pb2.py` ve `orchestrator_pb2_grpc.py` dosyalarının üretildiği gösterilebilir.

---
*(Bölüm 3'ün Sonu. Bölüm 4: Sistem Gösterimi ve Uygulama Akışları başlığına geçilebilir.)*
