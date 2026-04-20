KLÍČOVÁ PRAVIDLA PRO ZimaOS DEPLOYMENT

Tento projekt běží na specifickém setupu (ZimaOS + Docker + Cloudflare Tunnel). Jakákoliv změna v infrastruktuře musí respektovat následující body, jinak dojde k pádu produkčního serveru.

1. Architektura Dockeru
    Container Names: Názvy kontejnerů jsou fixní: wms_backend (pro Django) a lejbl_db_final (pro Postgres). Na tyto názvy jsou navázány interní skripty a Docker sítě. Neměnit!
    Volumes: Vždy používej relativní cesty v docker-compose.yml (např. ./src:/app). Nikdy nepoužívej absolutní cesty hostitele.
    Ports: Django běží interně na portu 8000. Na hostiteli (ZimaOS) je mapováno na 8002. Cloudflare Tunnel směřuje na localhost:8002.

2. Environment & Security (Settings.py)
    Bezpečné načítání: Všechny citlivé údaje (DB, Domény, Klíče) MUSÍ být načítány dynamicky z prostředí pomocí python-dotenv nebo os.environ.
    Klíčové proměnné v .env:
        DATABASE_URL: Musí používat formát postgres://user:pass@db:5432/dbname. Na produkci je hostitel vždy db (název služby v compose).
        ALLOWED_HOSTS: Musí obsahovat app.lejbl-lab.space.
        CSRF_TRUSTED_ORIGINS: Musí obsahovat https://app.lejbl-lab.space.
    Settings.py: Nikdy nehardkóduj doménu app.lejbl-lab.space přímo do souboru. Používej proměnnou prostředí.

3. Requirements.txt & Encoding
    Kódování: Soubor requirements.txt MUSÍ být uložen v kódování UTF-8 (bez BOM). Linux/Docker nepřečte UTF-16 (paznaky ^@ způsobí pád buildu).
    Povinné balíčky: Vždy udržuj v seznamu dj-database-url, psycopg2-binary, python-dotenv, djangorestframework a django-unfold.

4. Git Flow
    Zákaz Force Push na main: Nikdy nepoužívej push -f na větev main, pokud k tomu nemáš výslovný pokyn od operátora.
    Větve: Veškerý vývoj probíhá ve feature-branch. Do main se merguje až po lokálním otestování stability.
