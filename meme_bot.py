import os, time, random, requests, threading
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CANAL = os.environ.get("TELEGRAM_CHANNEL_ID", "")
LINK = os.environ.get("LINK_AFILIADO", "")
PROXY = os.environ.get("PROXY", "")

if not TOKEN or not CANAL:
    print("❌ Faltan variables de entorno!")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}"
enviados = set()
contador = 0
SUBS = ["memes","dankmemes","funny","me_irl","wholesomememes","animemes","gamingmemes","historymemes"]

# HORARIOS UTC (Render usa UTC)
# Estos horarios UTC equivalen a 08:00-22:15 en Caracas (UTC-4)
HORAS = [
    (12,0),(12,45),(13,30),(14,15),(15,0),
    (15,45),(16,30),(17,15),(18,0),(18,45),
    (19,30),(20,15),(21,0),(21,45),(22,30),
    (23,15),(0,0),(0,45),(1,30),(2,15)
]

proxies = {"http": PROXY, "https": PROXY} if PROXY else None

def log(m): 
    t = datetime.now(timezone.utc).strftime("%H:%M")
    print(f"[UTC {t}] {m}")
    import sys
    sys.stdout.flush()

def tg(m, d):
    try:
        r = requests.post(f"{URL}/{m}", json=d, timeout=20, proxies=proxies)
        return r.json().get("ok", False)
    except Exception as e:
        log(f"TG error: {e}")
        return False

def meme():
    try:
        r = requests.get(f"https://meme-api.com/gimme/{random.choice(SUBS)}", timeout=15, headers={"User-Agent":"Mozilla/5.0"}, proxies=proxies)
        d = r.json()
        if d.get("nsfw"): return None
        url = d.get("url","")
        if not url.endswith((".jpg",".jpeg",".png",".gif",".webp")):
            p = d.get("preview",[])
            url = p[-1] if p else None
        post = d.get("postLink","")
        if not url or post in enviados: return None
        enviados.add(post)
        return {"t":d.get("title","Meme"),"u":url,"p":post,"s":d.get("subreddit","memes"),"v":d.get("ups",0),"a":d.get("author","?")}
    except Exception as e:
        log(f"API error: {e}")
        return None

def esc(t):
    for c in ['_','*','[',']','(',')','~','`','>','#','+','-','=','|','{','}','.','!']:
        t = t.replace(c,f"\\{c}")
    return t

def send():
    global contador
    m = None
    for _ in range(15):
        m = meme()
        if m: break
        time.sleep(1)
    if not m: log("No se encontro meme"); return False
    contador += 1
    try:
        if (contador % 20 == 0) and LINK:
            return tg("sendMessage", {"chat_id": CANAL, "text": f"🚀 *Te gustan los memes?*\n\nUnete!\n\n{LINK}", "parse_mode": "Markdown"})
        h = random.sample(["#memes","#meme","#funny","#lol","#viral","#dankmemes","#humor"], 3)
        c = f"🖼️ *Meme del momento*\n\n📌 {esc(m['t'])}\n👤 u/{esc(m['a'])}\n⬆️ {m['v']:,} upvotes\n📍 r/{m['s']}\n\n{' '.join(h)}"
        k = {"inline_keyboard": [[{"text":"😂","callback_data":"lol"},{"text":"❤️","callback_data":"love"},{"text":"🔥","callback_data":"fire"}],[{"text":"🔗 Ver en Reddit","url":m['p']},{"text":"📤 Compartir","url":f"https://t.me/share/url?url={m['p']}"}]]}
        return tg("sendPhoto", {"chat_id": CANAL, "photo": m['u'], "caption": c, "parse_mode": "MarkdownV2", "reply_markup": k})
    except Exception as e:
        log(f"Error: {e}")
        return False

def bot_loop():
    log("🤖 MemeBot iniciado!")
    log(f"📍 Canal: {CANAL}")
    log(f"📊 {len(HORAS)} memes/dia")
    log("🌍 Usando hora UTC (hora de Render)")

    tg("sendMessage", {
        "chat_id": CANAL, 
        "text": f"🤖 *MemeBot activado!* ☁️\n\n📅 {len(HORAS)} memes/dia\n🌍 Hora UTC (Render)\n\n_¡Activa notificaciones!_ 🔔", 
        "parse_mode": "Markdown"
    })

    log("🧪 Enviando meme de prueba...")
    if send(): log("✅ Meme de prueba enviado!")
    else: log("❌ Fallo meme de prueba")

    while True:
        n = datetime.now(timezone.utc)
        for h, m in HORAS:
            t = n.replace(hour=h, minute=m, second=0, microsecond=0)
            if t <= n: t += timedelta(days=1)
            s = (t - n).total_seconds()
            log(f"⏳ Durmiendo {int(s/60)} min hasta UTC {h:02d}:{m:02d}")
            time.sleep(s)
            log(f"📤 Enviando meme #{contador+1}...")
            if send(): log("✅ Enviado")
            else: log("❌ Fallo")
            time.sleep(random.randint(3, 8))

@app.route("/")
def home():
    return f"🤖 MemeBot | {len(HORAS)} memes/dia | UTC: {datetime.now(timezone.utc).strftime('%H:%M')}"

@app.route("/health")
def health():
    return {"status": "ok", "utc": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    log(f"🌐 Web en puerto {port}")
    app.run(host="0.0.0.0", port=port)
