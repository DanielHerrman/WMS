FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    libmariadb-dev-compat \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Přidáme upgrade pipu, aby si poradil s novějšími balíčky
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Entrypoint script (runs collectstatic at container start because /app is volume-mounted)
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
