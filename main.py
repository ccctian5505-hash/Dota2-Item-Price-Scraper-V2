import requests
import time
import unicodedata
from datetime import datetime
import pytz
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ✅ Load from environment (Railway Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 🕒 Get PH time
def get_ph_time():
    ph_time = datetime.now(pytz.timezone("Asia/Manila"))
    return ph_time.strftime("%Y-%m-%d_%H-%M")

# 🔤 Clean up item name
def clean_item_name(name):
    name = name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return unicodedata.normalize("NFKC", name)

# 🏷️ Steam price scraper (PHP)
def get_price(item_name, retries=3):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "country": "PH",
        "currency": 12,  # PHP
        "appid": 570,
        "market_hash_name": item_name
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9"
    }

    for _ in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    price = data.get("lowest_price") or data.get("median_price") or "No price"
                    return price
        except Exception:
            pass
        time.sleep(2)

    return "Error fetching price"

# 🧮 Clean numeric price
def extract_numeric_price(price_text):
    if not price_text or "Error" in price_text or "No" in price_text:
        return 0.0
    cleaned = price_text.replace("₱", "").replace("P", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

# 🛎️ Telegram: send file
async def send_telegram_file(context: ContextTypes.DEFAULT_TYPE, file_path):
    try:
        with open(file_path, "rb") as doc:
            await context.bot.send_document(chat_id=CHAT_ID, document=doc)
    except Exception as e:
        print(f"❌ Error sending file: {e}")

# 🚀 Command handler: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me the Dota 2 item names (one per line), and I’ll scrape their Steam prices in PHP.")

# 📩 Message handler: user sends item names
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    items = [line.strip() for line in text.splitlines() if line.strip()]
    if not items:
        await update.message.reply_text("⚠️ Please send valid item names.")
        return

    now = get_ph_time()
    output_file = f"Price_Checker_Dota2_{now}.txt"

    results = []
    total_value = 0.0
    success = 0
    failed = 0

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source Name\tScraped Name\tPrice (PHP)\n")
        for i, item in enumerate(items, start=1):
            clean_name = clean_item_name(item)
            price = get_price(clean_name)
            numeric_price = extract_numeric_price(price)

            if numeric_price > 0:
                success += 1
                total_value += numeric_price
            else:
                failed += 1

            results.append(f"{item} → {price}")
            f.write(f"{item}\t{clean_name}\t{numeric_price:.2f}\n")

            print(f"{item} → {clean_name} → {price}")
            time.sleep(2.5)

            if i % 20 == 0:
                print("⏳ Cooling down for 12 seconds...")
                time.sleep(12)

    summary = (
        "✅ *Dota 2 Price Checker Summary*\n\n"
        + "\n".join(results[:10])  # show up to 10 items in Telegram
        + ("\n...and more\n" if len(results) > 10 else "")
        + f"\n\n💰 *Total Items:* {len(items)}"
        + f"\n🟢 *Success:* {success}"
        + f"\n🔴 *Failed:* {failed}"
        + f"\n💵 *Total Value:* ₱{total_value:,.2f}"
    )

    await update.message.reply_text(summary, parse_mode="Markdown")
    await send_telegram_file(context, output_file)

# 🧠 Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Dota 2 Price Checker Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
