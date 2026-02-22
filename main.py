import urllib.request
import json
import time

# 👇 1. Apna Telegram Token yahan dalein (Quotes " " ke andar)
TOKEN = "7285531671:AAEoqt4Ft395C6HQeyi6dKRkh24NQnmYF40"

# 👇 2. Apna NAYA Make.com Webhook URL yahan dalein
WEBHOOK_URL = "https://hook.us2.make.com/r82fqw228ta95m8cva6lr8gbi4e3zsji"

def get_updates(offset):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=10&offset={offset}"
    try:
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req)
        return json.loads(res.read()).get("result", [])
    except Exception as e:
        return []

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        pass

def send_to_make(text):
    data = {
        "title": text[:40], 
        "description": "Telegram Bot se bheja gaya product: " + text,
        "price": 99,
        "quantity": 1
    }
    req = urllib.request.Request(WEBHOOK_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        return False

print("🤖 Jadoo shuru! Bot chalu ho gaya hai...")

offset = 0
while True:
    try:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]
                
                if user_text == "/start":
                    send_message(chat_id, "👋 Hello Boss! Main aapka Etsy AI Bot hu. Mujhe product ka naam bhejein!")
                else:
                    send_message(chat_id, "⏳ Make.com ko bhej raha hu, 2 second dijiye...")
                    success = send_to_make(user_text)
                    if success:
                        send_message(chat_id, "✅ Boom! 💥 Aapka product Make.com ne receive kar liya hai!")
                    else:
                        send_message(chat_id, "❌ Error aaya Make.com ko bhejne me.")
    except Exception as e:
        pass
    time.sleep(2)
    
