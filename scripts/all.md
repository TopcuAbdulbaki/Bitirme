# Bitirme Node Kurulum Notlari

Ilk hedef: CUA standalone.

## CUA Standalone Kurulum

Repo public oldugu icin token gerekmez.

```bash
cd ~
curl -o vast_cua_standalone.sh https://raw.githubusercontent.com/TopcuAbdulbaki/Bitirme/master/scripts/vast_cua_standalone.sh
chmod +x vast_cua_standalone.sh
REPO_URL='https://github.com/TopcuAbdulbaki/Bitirme.git' ./vast_cua_standalone.sh
```

Iki GPU varsa opsiyon:

```bash
TENSOR_PARALLEL_SIZE=2 REPO_URL='https://github.com/TopcuAbdulbaki/Bitirme.git' ./vast_cua_standalone.sh
```
