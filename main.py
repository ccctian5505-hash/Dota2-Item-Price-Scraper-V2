import requests
import time
import unicodedata
from datetime import datetime
import pytz
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ Load from Railway environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
        "appid": 570,      # Dota 2 App ID
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

# 🛎️ Telegram sender (file)
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

# 🧠 Handle Telegram messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    items_text = update.message.text.strip()
    items = [line.strip() for line in items_text.split("\n") if line.strip()]
    if not items:
        await update.message.reply_text("⚠️ Please send item names, one per line.")
        return

    ph_time = datetime.now(pytz.timezone("Asia/Manila"))
    now = ph_time.strftime("%Y-%m-%d_%H-%M")
    output_file = f"Price_Checker_Dota2_{now}.txt"

    success_count = 0
    fail_count = 0
    total_price_value = 0
    telegram_message_lines = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source Name\tScraped Name\tPrice (PHP)\n")

        for i, item in enumerate(items, start=1):
            clean_name = clean_item_name(item)
            price = get_price(clean_name)

            numeric_price = 0
            if "₱" in price:
                try:
                    numeric_price = float(price.replace("₱", "").replace(",", "").strip())
                    total_price_value += numeric_price
                    success_count += 1
                except:
                    fail_count += 1
            elif "No price listed" in price or "Error" in price:
                fail_count += 1
            else:
                success_count += 1

            f.write(f"{item}\t{clean_name}\t{price}\n")
            telegram_message_lines.append(f"{item} → {price}")
            print(f"{item} → {clean_name} → {price}")

            time.sleep(2.5)
            if i % 20 == 0:
                print("⏳ Cooling down for 12 seconds...")
                time.sleep(12)

    # ✅ Build summary
    summary_text = (
        "📊 *Dota 2 Price Summary (PHP)*\n\n"
        + "\n".join(telegram_message_lines[:40])  # Show up to 40 items
        + "\n\n"
        + f"🧾 *Total Items:* {len(items)}\n"
        + f"✅ *Success:* {success_count}\n"
        + f"❌ *Failed:* {fail_count}\n"
        + f"💰 *Total Value:* ₱{total_price_value:,.2f}\n"
    )

    # ✅ Send Telegram message and file
    try:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=summary_text, parse_mode="Markdown")
        send_telegram_file(output_file, BOT_TOKEN, update.effective_chat.id)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Telegram send error: {e}")

# 🚀 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me Dota 2 item names (one per line) to check their prices in PHP!")

# 🏁 Main entry
def main():
    print("🤖 Dota 2 Price Checker Bot is running...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
