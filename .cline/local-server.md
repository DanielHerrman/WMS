# Spuštění lokálního serveru – WMS Backend

## Rychlý start

```powershell
cd c:\Users\Danie\wms_backend
py -3.13 manage.py runserver
```

Server běží na: **http://127.0.0.1:8000/**

## Důležité informace

| Položka | Hodnota |
|---|---|
| **Python příkaz** | `py -3.13` (NE `python`, NE `python3`) |
| **Verze Pythonu** | 3.13.0 (`C:\Python313\python.exe`) |
| **Verze Django** | 6.0.3 |
| **Správce balíčků** | `py -3.13 -m pip install <balicek>` |
| **Umístění site-packages** | `C:\Users\Danie\AppData\Roaming\Python\Python313\site-packages` |

## Prerekvizity

Pokud chybí balíčky, doinstaluj je:

```powershell
# Základní závislosti z requirements.txt
py -3.13 -m pip install django djangorestframework django-cors-headers mysqlclient python-dotenv django-filter

# Poznámka: django-filter NENÍ v requirements.txt, ale je potřeba pro modul print3d
```

## Známá varování (neškodná pro vývoj)

- `staticfiles.W004`: Chybí složka `wms_core/static/` – neovlivňuje běh vývojového serveru.

## Ukončení serveru

**CTRL + BREAK** (nebo **CTRL + C** v CMD, v PowerShell Ctrl+C)