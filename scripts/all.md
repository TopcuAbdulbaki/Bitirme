# Bitirme Node Scriptleri

Guncel public komutlar:

```powershell
.\scripts\windows\all.ps1 -Config scripts\nodes.example.json -DryRun
.\scripts\windows\orch_and_crawler.ps1 -Visible
.\scripts\windows\cua.ps1 -TargetHost <VAST_IP> -SshPort <SSH_PORT>
```

```bash
bash scripts/linux/all.sh --config scripts/nodes.example.json --dry-run
bash scripts/linux/orch_and_crawler.sh --visible
bash scripts/linux/cua.sh --target-host <VAST_IP> --ssh-port <SSH_PORT>
```

Varsayilan akista `nodes.local.json` varsa kullanilir, yoksa `nodes.example.json` okunur. `nodes.local.json` host/port bilgileri icindir ve git'e alinmaz.

Detayli envanter ve migration notlari icin `scripts/handoff_scripts.md` dosyasina bak.
