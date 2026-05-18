# Scripts Handoff Documentation

`scripts/` artik public entrypoint, internal helper ve legacy katmanlarina ayrilmistir.

## Public Entrypoints

| Linux | Windows | Amac |
| --- | --- | --- |
| `linux/all.sh` | `windows/all.ps1` | `nodes.example.json` / `nodes.local.json` config'ine gore tum node akisini baslatir. |
| `linux/orchestrator.sh` | `windows/orchestrator.ps1` | Orchestrator guarded baslatma. |
| `linux/crawler.sh` | `windows/crawler.ps1` | Crawler node guarded baslatma. |
| `linux/db.sh` | `windows/db.ps1` | DB node guarded baslatma. |
| `linux/vlm.sh` | `windows/vlm.ps1` | VLM node guarded baslatma. |
| `linux/llm.sh` | `windows/llm.ps1` | LLM node guarded baslatma. |
| `linux/cua.sh` | `windows/cua.ps1` | CUA + vLLM host guarded baslatma. |
| `linux/orch_and_crawler.sh` | `windows/orch_and_crawler.ps1` | Lokal orchestrator + crawler wrapper/supervisor. |

Linux ve Windows entrypoint'leri ayni anlamdaki parametreleri kullanir:

```bash
./scripts/linux/cua.sh --target-host 203.0.113.10 --ssh-port 40001
./scripts/linux/cua.sh --local
./scripts/linux/all.sh --config scripts/nodes.example.json --dry-run
```

```powershell
.\scripts\windows\cua.ps1 -TargetHost 203.0.113.10 -SshPort 40001
.\scripts\windows\cua.ps1 -Local
.\scripts\windows\all.ps1 -Config scripts\nodes.example.json -DryRun
```

## Helpers

`helper/` altindaki dosyalar dogrudan public API degildir. Public scriptler bunlari cagirir.

- `helper/linux/{orchestrator,crawler,db,vlm,llm,cua}.sh`: Saglam Linux/Vast guarded scriptlerinin internal yeri.
- `helper/linux/role_runner.sh`: Linux public role wrapper'larinin ortak local/remote/SSH mantigi.
- `helper/linux/bridge.sh`: Linux tarafinda SSH reverse tunnel reconnect helper'i.
- `helper/windows/remote_role.ps1`: Windows controller'dan remote Linux/Vast node baslatma helper'i.
- `helper/windows/orchestrator_local.ps1`: Windows lokal orchestrator guarded runner.
- `helper/windows/bridge.ps1`: Eski coklu node SSH bridge supervisor'i.
- `helper/windows/orch_and_crawler_supervisor.ps1`: `orch_and_crawler.ps1` tarafindan kullanilan lokal supervisor.

## Config

Commitlenen sablon:

```text
scripts/nodes.example.json
```

Kullaniciya ozel dosya:

```text
scripts/nodes.local.json
```

`nodes.local.json` git'e alinmaz. Varsayilan `mode` degeri `local-core-remote-workers`: orchestrator+crawler lokal, GPU/storage worker'lar remote.

## Legacy

`legacy/` altindaki scriptler yeni deployment yolu degildir. Eski Docker Hub push, kopyala-yapistir deploy ve CUA all-in-one prototipleri burada tutulur. Dockerfile ve compose dosyalarina bu refaktorde dokunulmamistir.
