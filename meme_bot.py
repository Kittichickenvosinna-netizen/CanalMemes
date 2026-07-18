import os, time, random, requests, threading
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)

# ============ CONFIGURACION ============
with open(".env") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ[k] = v

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CANAL = os.getenv("TELEGRAM_CHANNEL_ID", "")
LINK = os.getenv("LINK_AFILIADO", "")
PROXY = os.getenv("PROXY", "")

URL = f"https://api.telegram.org/bot{TOKEN}"
enviados = set()
contador = 0
SUBS = ["memes","dankmemes","funny","me_irl","wholesomememes","animemes","gamingmemes","historymemes"]

# 20 memes distribuidos desde 08:00 hasta 22:15 (cada ~45 min)
HORAS = [
    (8,0),(8,45),(9,30),(10,15),(11,0),
    (11,45),(12,30),(13,15),(14,0),(14,45),
    (15,30),(16,15),(17,0),(17,45),(18,30),
    (19,15),(20,0),(20,45),(21,30),(22,15)
]

proxies = {"http": PROXY, "https": PROXY} if PROXY else None

def log(m): print(f"[{time.strftime('%H:%M')}] {m}")

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
    for _ in range(10):
        m = meme()
        if m: break
        time.sleep(1)
    if not m: log("No meme"); return False
    contador += 1
    if (contador % 20 == 0) and LINK:
        return tg("sendMessage", {"chat_id": CANAL, "text": f"🚀 *Te gustan los memes?*\n\nUnete!\n\n{LINK}", "parse_mode": "Markdown"})
    h = random.sample(["#memes","#meme","#funny","#lol","#viral","#dankmemes","#humor"], 3)
    c = f"🖼️ *Meme del momento*\n\n📌 {esc(m['t'])}\n👤 u/{esc(m['a'])}\n⬆️ {m['v']:,} upvotes\n📍 r/{m['s']}\n\n{' '.join(h)}"
    k = {"inline_keyboard": [[{"text":"😂","callback_data":"lol"},{"text":"❤️","callback_data":"love"},{"text":"🔥","callback_data":"fire"}],[{"text":"🔗 Ver en Reddit","url":m['p']},{"text":"📤 Compartir","url":f"https://t.me/share/url?url={m['p']}"}]]}
    return tg("sendPhoto", {"chat_id": CANAL, "photo": m['u'], "caption": c, "parse_mode": "MarkdownV2", "reply_markup": k})

def bot_loop():
    log("🤖 Bot iniciado!")
    log(f"📍 {CANAL}")
    log(f"📊 {len(HORAS)} memes/dia")
    if PROXY: log(f"🔒 Proxy: {PROXY}")

    tg("sendMessage", {"chat_id": CANAL, "text": f"🤖 *MemeBot activado!*\n\n📅 {len(HORAS)} memes/dia\n⏰ Desde 08:00 hasta 22:15\n\n_¡Activa notificaciones!_ 🔔", "parse_mode": "Markdown"})

    while True:
        n = datetime.now()
        for h, m in HORAS:
            t = n.replace(hour=h, minute=m, second=0, microsecond=0)
            if t <= n: t += timedelta(days=1)
            s = (t - n).total_seconds()
            log(f"⏳ {int(s/60)} min hasta {h:02d}:{m:02d}")
            time.sleep(s)
            if send(): log("✅ Enviado")
            else: log("❌ Fallo")
            time.sleep(random.randint(3, 8))

# ============ SERVIDOR WEB (para Render no se duerma) ============
@app.route("/")
def home():
    return f"🤖 MemeBot activo | {len(HORAS)} memes/dia | Canal: {CANAL}"

@app.route("/health")
def health():
    return {"status": "ok", "memes_today": len(HORAS), "channel": CANAL}

if __name__ == "__main__":
    # Iniciar bot en un hilo separado
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()

    # Iniciar servidor web
    port = int(os.environ.get("PORT", 8080))
    log(f"🌐 Servidor web en puerto {port}")
    app.run(host="0.0.0.0", port=port)
