import os, json, hashlib, hmac, urllib.parse, asyncio
from datetime import datetime, date
from zoneinfo import ZoneInfo

import aiosqlite
import swisseph as swe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder

load_dotenv()
TOKEN=os.getenv("BOT_TOKEN")
WEBAPP_URL=os.getenv("WEBAPP_URL","").rstrip("/")
DB="astrology.db"
if not TOKEN: raise RuntimeError("BOT_TOKEN missing")

bot=Bot(TOKEN); dp=Dispatcher(); app=FastAPI()
swe.set_sid_mode(swe.SIDM_LAHIRI)

SIGNS=["Овен","Телец","Близнецы","Рак","Лев","Дева","Весы","Скорпион","Стрелец","Козерог","Водолей","Рыбы"]
NAK=["Ашвини","Бхарани","Криттика","Рохини","Мригашира","Ардра","Пунарвасу","Пушья","Ашлеша","Магха","Пурва-Пхалгуни","Уттара-Пхалгуни","Хаста","Читра","Свати","Вишакха","Анурадха","Джйештха","Мула","Пурва-Ашадха","Уттара-Ашадха","Шравана","Дхаништха","Шатабхиша","Пурва-Бхадрапада","Уттара-Бхадрапада","Ревати"]
PLANETS=[("Солнце",swe.SUN),("Луна",swe.MOON),("Марс",swe.MARS),("Меркурий",swe.MERCURY),("Юпитер",swe.JUPITER),("Венера",swe.VENUS),("Сатурн",swe.SATURN),("Раху",swe.MEAN_NODE)]

class Birth(BaseModel):
    user_id:int
    day:int; month:int; year:int
    hour:int; minute:int
    city:str

class UserID(BaseModel):
    user_id:int

async def db():
    con=await aiosqlite.connect(DB)
    await con.execute("""CREATE TABLE IF NOT EXISTS users(
      user_id INTEGER PRIMARY KEY, day INTEGER, month INTEGER, year INTEGER,
      hour INTEGER, minute INTEGER, city TEXT, subscribed INTEGER DEFAULT 0)""")
    await con.commit(); return con

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60)

def planet_lon(j,p):
    x,_,_ = swe.calc_ut(j,p,swe.FLG_SWIEPH|swe.FLG_SIDEREAL)
    return x[0]%360

def calculate(b):
    # City coordinates are intentionally kept as a small demo table.
    # Replace with geocoding in production.
    cities={
      "Алматы":(43.2389,76.8897,"Asia/Almaty"),
      "Астана":(51.1694,71.4491,"Asia/Almaty"),
      "Москва":(55.7558,37.6173,"Europe/Moscow"),
      "Дубай":(25.2048,55.2708,"Asia/Dubai"),
      "Лондон":(51.5074,-0.1278,"Europe/London"),
      "Нью-Йорк":(40.7128,-74.0060,"America/New_York")
    }
    key=b.city.strip()
    if key not in cities: raise ValueError("Город пока не добавлен в демо. Используйте: Алматы, Астана, Москва, Дубай, Лондон или Нью-Йорк.")
    lat,lon,tz=cities[key]
    local=datetime(b.year,b.month,b.day,b.hour,b.minute,tzinfo=ZoneInfo(tz))
    utc=local.astimezone(ZoneInfo("UTC")); j=julian(utc)
    p={n:planet_lon(j,x) for n,x in PLANETS}
    p["Кету"]=(p["Раху"]+180)%360
    _,asc=swe.houses_ex(j,lat,lon,b"W",swe.FLG_SIDEREAL)
    lagna=asc[0]%360
    moon=p["Луна"]; idx=int(moon/(360/27)); pada=int(((moon%(360/27))/(360/27))*4)+1
    return {"city":key,"tz":tz,"lagna":lagna,"nakshatra":NAK[idx],"pada":pada,"planets":p}

def label(lon):
    return {"sign":SIGNS[int(lon//30)],"degree":round(lon%30,1),"lon":round(lon,2)}

def chart_payload(c):
    return {
      "lagna":label(c["lagna"]),
      "nakshatra":c["nakshatra"],"pada":c["pada"],
      "planets":[{"name":n,**label(x)} for n,x in c["planets"].items()]
    }

def daily(c):
    today=date.today()
    j=swe.julday(today.year,today.month,today.day,12)
    jup=planet_lon(j,swe.JUPITER); sat=planet_lon(j,swe.SATURN)
    moon=c["planets"]["Луна"]
    h1=int(((jup-moon)%360)//30)+1; h2=int(((sat-moon)%360)//30)+1
    return {"date":today.isoformat(),"title":"Фокус дня","text":f"Юпитер от Луны: дом {h1}. Сатурн: дом {h2}. Используйте день для осознанных решений, порядка в делах и наблюдения за своими реакциями."}

def annual(c):
    out=[]
    moon=c["planets"]["Луна"]
    for m in range(1,13):
      d=date(date.today().year,m,15); j=swe.julday(d.year,d.month,d.day,12)
      ju=planet_lon(j,swe.JUPITER); sa=planet_lon(j,swe.SATURN)
      out.append({"month":m,"jupiter_house":int(((ju-moon)%360)//30)+1,"saturn_house":int(((sa-moon)%360)//30)+1})
    return out

def compatibility(a,b):
    pairs=[("Луна","Луна"),("Солнце","Солнце"),("Венера","Марс"),("Марс","Венера")]
    score=40
    for x,y in pairs:
      d=abs((a["planets"][x]-b["planets"][y]+180)%360-180)
      score += 15 if d<=30 else 10 if d<=60 else 5
    return min(100,score)

def validate_webapp(init_data):
    # Telegram WebApp initData verification.
    if not init_data: raise HTTPException(401,"Missing Telegram initData")
    q=urllib.parse.parse_qs(init_data,keep_blank_values=True)
    received=q.pop("hash",[None])[0]
    if not received: raise HTTPException(401,"Missing hash")
    pairs=[f"{k}={v[0]}" for k,v in sorted(q.items())]
    data_check="\n".join(pairs)
    secret=hmac.new(b"WebAppData",TOKEN.encode(),hashlib.sha256).digest()
    calc=hmac.new(secret,data_check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc,received): raise HTTPException(401,"Invalid initData")
    user=json.loads(q["user"][0]); return int(user["id"])

@app.get("/")
async def index(): return FileResponse("index.html")
@app.get("/health")
async def health(): return {"ok":True}

@app.post("/api/profile")
async def profile(b:Birth):
    c=calculate(b)
    con=await db()
    await con.execute("""INSERT INTO users(user_id,day,month,year,hour,minute,city)
      VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET day=excluded.day,month=excluded.month,year=excluded.year,hour=excluded.hour,minute=excluded.minute,city=excluded.city""",
      (b.user_id,b.day,b.month,b.year,b.hour,b.minute,b.city))
    await con.commit(); await con.close()
    return chart_payload(c)

@app.delete("/api/profile/{user_id}")
async def delete_profile(user_id:int):
    con=await db()
    await con.execute("DELETE FROM users WHERE user_id=?",(user_id,))
    await con.commit(); await con.close()
    return {"ok":True}

@app.get("/api/chart/{user_id}")
async def chart_api(user_id:int):
    con=await db(); cur=await con.execute("SELECT day,month,year,hour,minute,city FROM users WHERE user_id=?",(user_id,))
    r=await cur.fetchone(); await con.close()
    if not r: raise HTTPException(404,"Profile not found")
    b=Birth(user_id=user_id,day=r[0],month=r[1],year=r[2],hour=r[3],minute=r[4],city=r[5])
    return chart_payload(calculate(b))

@app.get("/api/daily/{user_id}")
async def daily_api(user_id:int):
    con=await db(); cur=await con.execute("SELECT day,month,year,hour,minute,city FROM users WHERE user_id=?",(user_id,))
    r=await cur.fetchone(); await con.close()
    if not r: raise HTTPException(404,"Profile not found")
    b=Birth(user_id=user_id,day=r[0],month=r[1],year=r[2],hour=r[3],minute=r[4],city=r[5])
    return daily(calculate(b))

@app.get("/api/annual/{user_id}")
async def annual_api(user_id:int):
    con=await db(); cur=await con.execute("SELECT day,month,year,hour,minute,city FROM users WHERE user_id=?",(user_id,))
    r=await cur.fetchone(); await con.close()
    if not r: raise HTTPException(404,"Profile not found")
    b=Birth(user_id=user_id,day=r[0],month=r[1],year=r[2],hour=r[3],minute=r[4],city=r[5])
    return {"year":date.today().year,"months":annual(calculate(b))}

@dp.message(CommandStart())
async def start(m:Message):
    b=ReplyKeyboardBuilder()
    b.button(text="🚀 Открыть приложение",web_app=WebAppInfo(url=WEBAPP_URL))
    b.adjust(1)
    await m.answer("🪐 Добро пожаловать в Vedic Astrology.\nНатальная карта • годовой прогноз • совместимость • ежедневный гороскоп",reply_markup=b.as_markup(resize_keyboard=True))

async def bot_loop():
    await db()
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    asyncio.create_task(bot_loop())
