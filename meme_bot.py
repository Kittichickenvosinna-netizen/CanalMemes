import os, time, random, requests, threading, traceback
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CANAL = os.environ.get("TELEGRAM_CHANNEL_ID", "")
LINK = os.environ.get("LINK_AFILIADO", "")

if not TOKEN or not CANAL:
    print("❌ Faltan variables de entorno!")
    exit(1)

URL = f"https://api.telegram.org/bot{TOKEN}"
enviados = set()
contador = 0
SUBS = ["memes","dankmemes","funny","me_irl","wholesomememes","animemes"]
HORAS = [
    (12,0),(12,45),(13,30),(14,15),(15,0),
    (15,45),(16,30),(17,15),(18,0),(18,45),
    (19,30),(20,15),(21,0),(21,45),(22,30),
    (23,15),(0,0),(0,45),(1,30),(2,15)
]

def log(m): 
    t = datetime.now(timezone.utc).strftime("%H:%M")
    print(f"[UTC {t}] {m}")
    import sys
    sys.stdout.flush()

def tg(method, data):
    try:
        full_url = f"{URL}/{method}"
        log(f"📡 Enviando a Telegram: {method}")
        r = requests.post(full_url, json=data, timeout=20)
        log(f"📡 Respuesta HTTP: {r.status_code}")
        j = r.json()
        log(f"📡 Respuesta JSON: ok={j.get('ok')}")
        if not j.get("ok"):
            log(f"❌ Telegram error: {j.get('description', 'unknown')}")
            return False
        return True
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        traceback.print_exc()
        return False

def get_meme():
    try:
        sub = random.choice(SUBS)
        api_url = f"https://meme-api.com/gimme/{sub}"
        log(f"🔍 Buscando meme en: {api_url}")
        r = requests.get(api_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        log(f"🔍 Respuesta API: {r.status_code}")
        d = r.json()
        log(f"🔍 Titulo: {d.get('title','N/A')[:50]}...")
        if d.get("nsfw"): 
            log("⚠️ Meme NSFW, saltando")
            return None
        url = d.get("url","")
        log(f"🔍 URL imagen: {url[:80]}...")
        if not url.endswith((".jpg",".jpeg",".png",".gif",".webp")):
            p = d.get("preview",[])
            url = p[-1] if p else None
            log(f"🔍 Usando preview: {url[:80] if url else 'N/A'}...")
        post = d.get("postLink","")
        if not url:
            log("❌ Sin URL de imagen")
            return None
        if post in enviados:
            log("⚠️ Meme ya enviado, saltando")
            return None
        enviados.add(post)
        return {"t":d.get("title","Meme"),"u":url,"p":post,"s":d.get("subreddit",sub),"v":d.get("ups",0),"a":d.get("author","?")}
    except Exception as e:
        log(f"❌ API exception: {e}")
        traceback.print_exc()
        return None

def esc(t):
    for c in ['_','*','[',']','(',')','~','`','>','#','+','-','=','|','{','}','.','!']:
        t = t.replace(c,f"\\{c}")
    return t

def send():
    global contador
    log("🚀 Iniciando envio de meme...")
    m = None
    for i in range(15):
        log(f"🔄 Intento {i+1}/15...")
        m = get_meme()
        if m: 
            log(f"✅ Meme encontrado: {m['t'][:50]}...")
            break
        time.sleep(1)
    if not m: 
        log("❌ No se encontro meme despues de 15 intentos")
        return False
    contador += 1
    try:
        if (contador % 20 == 0) and LINK:
            log("📢 Enviando post promocional")
            return tg("sendMessage", {
                "chat_id": CANAL, 
                "text": f"🚀 Te gustan los memes?\n\nUnete!\n\n{LINK}"
            })
        
        h = random.sample(["#memes","#meme","#funny","#lol","#viral","#dankmemes","#humor"], 3)
        
        # Caption en TEXTO PLANO (sin MarkdownV2) = cero errores de parsing
        c = (f"🖼️ Meme del momento\n\n"
             f"📌 {m['t']}\n"
             f"👤 u/{m['a']}\n"
             f"⬆️ {m['v']:,} upvotes\n"
             f"📍 r/{m['s']}\n\n"
             f"{' '.join(h)}")
        
        k = {"inline_keyboard": [
            [{"text":"😂","callback_data":"lol"},{"text":"❤️","callback_data":"love"},{"text":"🔥","callback_data":"fire"}],
            [{"text":"🔗 Ver en Reddit","url":m['p']},{"text":"📤 Compartir","url":f"https://t.me/share/url?url={m['p']}"}]
        ]}
        
        log(f"📤 Enviando foto a {CANAL}...")
        # SIN parse_mode, o sea, texto plano
        return tg("sendPhoto", {
            "chat_id": CANAL, 
            "photo": m['u'], 
            "caption": c, 
            "reply_markup": k
        })
    except Exception as e:
        log(f"❌ Error en send(): {e}")
        traceback.print_exc()
        return False

def bot_loop():
    log("🤖 MemeBot iniciado!")
    log(f"📍 Canal: {CANAL}")
    log(f"📊 {len(HORAS)} memes/dia")

    log("🧪 === MEME DE PRUEBA ===")
    ok = send()
    log(f"🧪 Resultado prueba: {'✅ OK' if ok else '❌ FALLO'}")

    log("📨 Enviando mensaje de activacion...")
    tg("sendMessage", {
        "chat_id": CANAL, 
        "text": f"🤖 *MemeBot activado!* ☁️\n\n📅 {len(HORAS)} memes/dia\n🌍 Hora UTC\n\n_¡Activa notificaciones!_ 🔔", 
        "parse_mode": "Markdown"
    })

    while True:
        n = datetime.now(timezone.utc)
        for h, m in HORAS:
            t = n.replace(hour=h, minute=m, second=0, microsecond=0)
            if t <= n: t += timedelta(days=1)
            s = (t - n).total_seconds()
            log(f"⏳ Durmiendo {int(s/60)} min hasta UTC {h:02d}:{m:02d}")
            time.sleep(s)
            ok = send()
            log(f"📤 Resultado: {'✅ OK' if ok else '❌ FALLO'}")
            time.sleep(random.randint(3, 8))

@app.route("/")
def home():
    return f"🤖 MemeBot | {len(HORAS)} memes/dia | UTC: {datetime.now(timezone.utc).strftime('%H:%M')}"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    log(f"🌐 Web en puerto {port}")
    app.run(host="0.0.0.0", port=port)
