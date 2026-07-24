# 🚀 WMS Backend – Deployment Guide

## Přístupové údaje

### ZimaOS Server (SSH)
| Položka | Hodnota |
|---------|---------|
| **IP (Tailscale)** | `100.65.97.17` |
| **IP (LAN)** | nezjištěno – používáme Tailscale |
| **Uživatel** | `Dinoman95` |
| **Heslo** | `Oid0MOLO95` |
| **Port SSH** | `22` |
| **Příkaz** | `ssh Dinoman95@100.65.97.17` (nebo přes sshpass) |

**sshpass pro automatizaci (Windows):**
```powershell
sshpass -p "Oid0MOLO95" ssh -o ConnectTimeout=30 -o StrictHostKeyChecking=no Dinoman95@100.65.97.17
```
sshpass je nainstalován v: `C:\Users\Danie\AppData\Local\Microsoft\WinGet\Packages\xhcoding.sshpass-win32_Microsoft.Winget.Source_8wekyb3d8bbwe\sshpass.exe`

### Django Admin (aplikace)
| Položka | Hodnota |
|---------|---------|
| **URL** | `https://app.lejbl-lab.space/admin/` |
| **Superuser** | `Dinoman95` |
| **Heslo** | `Oid0MOLO95` |

### Databáze (PostgreSQL)
| Položka | Hodnota |
|---------|---------|
| **Host** | `lejbl_db_final` (Docker kontejner) |
| **Port** | `5432` |
| **Database** | `wms_db` |
| **User** | `wms_user` |
| **Password** | `Oid0MOLO95` |
| **DATABASE_URL** | `postgres://wms_user:Oid0MOLO95@lejbl_db_final:5432/wms_db` |

---

## Architektura na ZimaOS

### Docker kontejnery
```
lejbl_db_final      → postgres:15          (bridge: lejbl_src_default)
wms_backend         → lejbl_src-wms_app    (bridge + lejbl_src_default)
cloudflare-tunnel   → cloudflare/cloudflared (bridge)
```

- `wms_backend` a `lejbl_db_final` jsou propojeny přes síť `lejbl_src_default`
- Cloudflare Tunnel směřuje na `http://100.65.97.17:8002` → `wms_backend:8000`
- Aplikace běží na portu **8002** (mapováno na 8000 v kontejneru)

### Cesty na serveru
| Co | Cesta |
|----|-------|
| Projekt (Django) | `/DATA/AppData/lejbl-wms/src/lejbl_src/` |
| Media soubory | `/DATA/AppData/lejbl-wms/media/` |
| DB data | `/DATA/AppData/lejbl-wms/db_data/` |
| .env soubor | `/DATA/AppData/lejbl-wms/src/lejbl_src/.env` |
| docker-compose.yml | `/DATA/AppData/lejbl-wms/src/lejbl_src/docker-compose.yml` |

---

## Deployment Workflow

### 1. Lokálně – zapni Tailscale
```powershell
# Ověř že ZimaOS je online
tailscale status
# Mělo by ukazovat: zimaos ... linux active
```

### 2. Push na GitHub
```powershell
git add -A
git commit -m "popis změn"
git pull --rebase origin main
git push origin main
```

### 3. Připoj se na server
```powershell
sshpass -p "Oid0MOLO95" ssh -o StrictHostKeyChecking=no Dinoman95@100.65.97.17
```

### 4. Aktualizuj kód na serveru
```bash
cd /DATA/AppData/lejbl-wms/src/lejbl_src
git fetch origin
git reset --hard origin/main
```

### 5. Přebuild a restart (POUZE pokud se změnil Dockerfile/requirements.txt/settings.py)
```bash
# Kopíruj requirements.txt z lokálního repo (pokud se změnil)
# Pak:
echo Oid0MOLO95 | sudo -S docker stop wms_backend
echo Oid0MOLO95 | sudo -S docker rm wms_backend
echo Oid0MOLO95 | sudo -S docker build -t lejbl_src-wms_app .
echo Oid0MOLO95 | sudo -S docker run -d --name wms_backend --network bridge -p 8002:8000 \
  -v /DATA/AppData/lejbl-wms/src/lejbl_src:/app \
  -e DATABASE_URL=postgres://wms_user:Oid0MOLO95@lejbl_db_final:5432/wms_db \
  -e ALLOWED_HOSTS='app.lejbl-lab.space,localhost,127.0.0.1,100.65.97.17' \
  -e CSRF_TRUSTED_ORIGINS='https://app.lejbl-lab.space' \
  -e DJANGO_ENV=production \
  -e SECRET_KEY='django-insecure-2jqa0a_h-_-qnq_bu__ga_r_5pj69lka_6g7bycg9tpkpxyl_q' \
  --restart unless-stopped lejbl_src-wms_app
echo Oid0MOLO95 | sudo -S docker network connect lejbl_src_default wms_backend
```
> **Poznámka:** Aplikace nyní běží přes **Gunicorn** (production WSGI server) – CMD je definován v Dockerfilu. `collectstatic` se spouští automaticky při buildu image. Pokud přidáš nové statické soubory (CSS/JS), je potřeba rebuildnout image.

### 6. Rychlý restart (jen kód, beze změny image)
```bash
echo Oid0MOLO95 | sudo -S docker restart wms_backend
```

### 7. Migrace databáze
```bash
echo Oid0MOLO95 | sudo -S docker exec wms_backend python manage.py migrate
```

### 8. Vytvoření superusera (pokud je potřeba)
```bash
echo Oid0MOLO95 | sudo -S docker exec wms_backend python manage.py createsuperuser
```

---

## Důležité: SUDO + Docker

Uživatel `Dinoman95` **nemá** přímý přístup k Docker socketu. Všechny Docker příkazy musí jít přes `sudo -S`:
```bash
echo Oid0MOLO95 | sudo -S docker ...
```

---

## Jak řešit problémy

### 502 Bad Gateway
- Cloudflare Tunnel se nemůže připojit k `wms_backend`
- Zkontroluj: `echo Oid0MOLO95 | sudo -S docker ps | grep wms`
- Restartuj Cloudflare Tunnel: `echo Oid0MOLO95 | sudo -S docker restart cloudflare-tunnel`
- Ověř, že wms_backend naslouchá: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8002/admin/`

### Forbidden (403) – CSRF
- Zkontroluj `.env` soubor: `CSRF_TRUSTED_ORIGINS=https://app.lejbl-lab.space`
- Zkontroluj Docker ENV proměnné

### 500 Server Error
- Zapni DEBUG: změň `DEBUG = True` v `settings.py` a restartuj kontejner
- Podívej se na detailní chybu v prohlížeči
- Po opravě vrať `DEBUG = False`

### Migrační konflikty
Pokud se migrační historie rozbije, vytvoř DB znovu:
```bash
echo Oid0MOLO95 | sudo -S docker exec lejbl_db_final psql -U wms_user -d postgres -c "DROP DATABASE IF EXISTS wms_db;"
echo Oid0MOLO95 | sudo -S docker exec lejbl_db_final psql -U wms_user -d postgres -c "CREATE DATABASE wms_db OWNER wms_user;"
echo Oid0MOLO95 | sudo -S docker exec wms_backend python manage.py migrate
```

---

## Soubory, které musí být synchronizované

| Soubor | Poznámka |
|--------|----------|
| `requirements.txt` | Přidávat nové závislosti sem (musí být nainstalovány v Docker image) |
| `wms_core/settings.py` | **Kritický** – musí obsahovat `CSRF_TRUSTED_ORIGINS`, `UNFOLD`, `STATIC_ROOT`, `DEFAULT_AUTO_FIELD` |
| `.env` | Obsahuje `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DJANGO_ENV`, `DEBUG` |
| `Dockerfile` | Build image – změny vyžadují rebuild kontejneru |

---

## GitHub Actions (automatický deploy)

Workflow v `.github/workflows/deploy.yml` se spouští při push na `main`, ale **spoléhá na SSH klíč** (`secrets.ZIMA_SSH_KEY`). Pokud nefunguje, použij manuální postup výše.

---

## Změny v databázovém schématu

Při změně modelů:
1. Lokálně: `python manage.py makemigrations`
2. Commit + push migrační soubory
3. Na serveru: `git pull` + `docker exec wms_backend python manage.py migrate`
4. Pokud migrace selžou → viz "Migrační konflikty" výše (DROP + CREATE DB)