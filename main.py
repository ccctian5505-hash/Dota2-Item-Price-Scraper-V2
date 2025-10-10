that code is working good, but i now i need to change the source . I want  that I will input the item name in telegram then the code will word, same sa old, scrape the name, and price and and the result is in two format, txt files and just telegram message, in telegram message put summary  thats all make sure that it is php format. I'll paste the code of my old but working well code so you can base to this.

import requests
import time
import unicodedata
from datetime import datetime
import pytz
import os

# ✅ Load from environment (Railway Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 📂 Load item names from file
ITEM_FILE = "items.txt"
with open(ITEM_FILE, "r", encoding="utf-8") as f:
    items = [line.strip() for line in f if line.strip()]

# ⏰ Get PH time with full timestamp
ph_time = datetime.now(pytz.timezone("Asia/Manila"))
now = ph_time.strftime("%Y-%m-%d_%H-%M")
output_file = f"Price_Checker_Dota2_{now}.txt"


# 🔤 Clean up item name to match Steam's formatting
def clean_item_name(name):
    name = name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    name = unicodedata.normalize("NFKC", name)
    return name


# 🏷️ Steam price scraper function (PHP currency)
def get_price(item_name, retries=3):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "country": "PH",   # ✅ Philippine region
        "currency": 12,    # ✅ Peso ₱
        "appid": 570,
        "market_hash_name": item_name
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9"
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("lowest_price") or data.get("median_price") or "No price listed"
        except Exception:
            pass
        time.sleep(2)

    return "Error fetching price"


# 🛎️ Telegram sender (text file upload)
def send_telegram_file(file_path, token, chat_id):
    if not token or not chat_id:
        print("⚠️ Telegram not configured, skipping upload.")
        return
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, "rb") as doc:
            response = requests.post(url, data={"chat_id": chat_id}, files={"document": doc})
        if response.status_code == 200:
            print("📨 Telegram file sent!")
        else:
            print(f"⚠️ Failed to send file: {response.text}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# 🚀 Start scraping
with open(output_file, "w", encoding="utf-8") as f:
    f.write("Source Name\tScraped Name\tPrice (PHP)\n")
    for i, item in enumerate(items, start=1):
        clean_name = clean_item_name(item)
        price = get_price(clean_name)
        print(f"{item} → {clean_name} → {price}")
        f.write(f"{item}\t{clean_name}\t{price}\n")

        time.sleep(2.5)

        if i % 20 == 0:
            print("⏳ Cooling down for 12 seconds...")
            time.sleep(12)

print(f"\n✅ Scraping done! Results saved to: {output_file}")

# ✅ Send to Telegram
send_telegram_file(output_file, BOT_TOKEN, CHAT_ID)

Thanks. I will deploy this in railway

Also I want in my telegram has button if i will input the data
