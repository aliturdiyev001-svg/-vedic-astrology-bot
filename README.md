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
cp .env.example .env
python main.py
```

Set `WEBAPP_URL` to your HTTPS Mini App URL.

For production, use PostgreSQL, HTTPS reverse proxy, proper secret management, and Telegram WebApp init-data validation on every protected API request.

Astrology interpretations are traditional/entertainment content and are not scientifically validated.
