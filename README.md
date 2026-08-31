# Vedic Astrology Bot V3

Full-stack starter for a Telegram bot + Mini App.

### Included
- Responsive premium-style Mini App UI
- Dashboard and profile
- Birth-data form
- Natal chart calculation with Swiss Ephemeris / Lahiri sidereal zodiac
- Planet cards and nakshatra
- Annual forecast screen
- Compatibility screen
- Daily horoscope screen
- Daily notification toggle
- Premium purchase entry point
- SQLite persistence
- FastAPI API endpoints
- Telegram WebApp authentication validation
- Docker deployment starter

### Run
```bash
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env   # заполните BOT_TOKEN и WEBAPP_URL

# локально:
uvicorn main:app --host 0.0.0.0 --port 8000
```

Через Docker: `docker build -t vedic-astro . && docker run -p 8000:8000 vedic-astro`.

### Деплой (Render.com)
1. Create new **Web Service** → `Docker` environment.
2. Port: **8000**.
3. Environment variables:
   - `BOT_TOKEN` — токен от @BotFather
   - `WEBAPP_URL=https://ВАШ_ПРОЕКТ.onrender.com` (обязательно HTTPS)
4. Мини-апп открывается по `WEBAPP_URL` в Telegram.

Set `WEBAPP_URL` to your HTTPS Mini App URL.

For production, use PostgreSQL, HTTPS reverse proxy, proper secret management, and Telegram WebApp init-data validation on every protected API request.

Astrology interpretations are traditional/entertainment content and are not scientifically validated.
