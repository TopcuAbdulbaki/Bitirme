# TEZ DÜZELTİLECEKLER

Buradaki maddeler iki amaca hizmet eder:
1. **Projede** yapılacak teknik iyileştirmeler
2. **Tezde** güncellenecek ilgili paragraflar

Önce proje güncellenir → ardından tez düzeltilir.

---

## 1. Docker / Dağıtım — Çok Komutlu Manuel Yapı

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

**4. Node Registry Kalıcı Hale Getirilir**
Şu an `node_registry.py` bellekte tutuyor. Eklenmesi gerekenler:
- `role`, `ssh_host`, `ssh_port`, `tunnel_mode` (ssh / wireguard)
- `public_callback_host`, `public_callback_port`
- `status`, `last_heartbeat`, `provision_log`

**Var olan altyapı (bunların üstüne inşa edilecek):**
- `scripts/manage_node_bridges.ps1` — SSH reverse tunnel supervisor
- `scripts/node_bridges.example.json` — node konfigürasyon şablonu
- `docs/wireguard_setup.md` — VPN modeli
- `scripts/vast_cua_host_guarded.sh` — bootstrap mantığının büyük kısmı hazır

#### Kritik Ayrım
> Orchestrator **çalışma zamanı** işleri yönetir.
> Provisioner **altyapıyı** kurar.
> SSH anahtarları Orchestrator container'ına koyulmaz; ayrı bir provisioner service/script işletir.

### Tezde Güncellenecek Paragraf
**Konum:** `tez.md` → Bölüm 2.1, "Container Tabanlı Dağıtım (Docker)" paragrafı son cümlesi:

> ~~"IP ve port yapılandırmalarının her oturumda manuel olarak ayarlanmasını gerektirmektedir. Söz konusu operasyonel zorluk, 6. bölümde bir sınırlama olarak tartışılacaktır."~~

**Yeni yazılacak:**
> "Mevcut prototipte yeni GPU düğümleri manuel olarak yapılandırılmaktadır. Önerilen genişletmede ise tek bir `provision_node` komutuyla SSH üzerinden uzak makineye bağlanılması, Docker kurulumu, servis başlatma ve tünel açma adımlarının otomatikleştirilmesi hedeflenmektedir. Vast.ai IP'lerinin dinamik yapısı nedeniyle oluşan yaşam döngüsü yönetimi zorluğu, çözüm önerileriyle birlikte 6. bölümde ele alınacaktır."

---

## 2. [Buraya yeni maddeler eklenecek]

---

*Son güncelleme: 2026-05-18*
