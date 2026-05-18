# Legacy Scripts

Bu klasordeki scriptler yeni deployment akisi icin aktif yol degildir. Silinmediler; eski denemeleri, Docker Hub push komutlarini ve kopyala-yapistir Vast.ai notlarini kaybetmemek icin burada tutuluyorlar.

Guncel yol icin `scripts/handoff_scripts.md` dosyasina bak.

## Dosyalar

- `0_build_all.ps1`, `0_update_all.ps1`: Eski toplu build/update referanslari.
- `1_orchestrator.ps1` - `5_llm.ps1`: Eski servis bazli Docker komut ureticileri.
- `6_cua.ps1`: Eski CUA Docker helper'i.
- `run_orchestrator_local.ps1`: Sabit lokal orchestrator baslatma helper'i.
- `vast_cua_standalone.sh`: Eski CUA standalone prototipi.
- `vast_cua_allinone.sh`: Eski public CUA all-in-one Docker helper'i. Dockerfile/compose korunur, ama bu akış bu refaktorde public entrypoint degildir.
- `deploy_orchestrator.sh`: Eski orchestrator container deploy scripti.
