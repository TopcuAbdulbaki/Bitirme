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
