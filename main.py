import os
import time
import requests
import unicodedata
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

# ✅ Environment Variables (set in Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found. Set it in Railway → Variables tab.")

# 🌏 PH Time
def ph_time_now():
    ph_time = datetime.now(pytz.timezone("Asia/Manila"))
    return ph_time.strftime("%Y-%m-%d_%H-%M")

# 🧼 Clean item name
def clean_item_name(name):
    name = name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    name = unicodedata.normalize("NFKC", name)
    return name

# 💰 Steam price fetcher (PHP)
def get_price(item_name, retries=3):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "country": "PH",
        "currency": 12,  # PHP
        "appid": 570,    # Dota 2
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
                    return data.get("lowest_price") or data.get("median_price") or "No price listed"
        except Exception:
            pass
        time.sleep(2)

    return "Error fetching price"

# 📁 Scraping core logic
async def scrape_items(items, chat_id, context: ContextTypes.DEFAULT_TYPE):
    now = ph_time_now()
    output_file = f"Price_Checker_Dota2_{now}.txt"
    total_items = len(items)
    success, failed, total_value = 0, 0, 0.0

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source Name\tScraped Name\tPrice (PHP)\n")
        for i, item in enumerate(items, start=1):
            clean_name = clean_item_name(item)
            price = get_price(clean_name)

            print(f"{item} → {clean_name} → {price}")

            if price not in ["Error fetching price", "No price listed"]:
                success += 1
                try:
                    num = float(price.replace("₱", "").replace(",", "").strip())
                    total_value += num
                except:
                    pass
            else:
                failed += 1

            f.write(f"{item}\t{clean_name}\t{price}\n")
            time.sleep(2.5)

            if i % 20 == 0:
                print("⏳ Cooling down for 12 seconds...")
                time.sleep(12)

    summary = (
        f"✅ Dota 2 Price Scraping Complete!\n\n"
        f"📄 File: {output_file}\n"
        f"📦 Total Items: {total_items}\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"💸 Total Value: ₱{round(total_value, 2)}"
    )

    # Send Telegram message summary
    await context.bot.send_message(chat_id=chat_id, text=summary)

    # Send result file
    with open(output_file, "rb") as doc:
        await context.bot.send_document(chat_id=chat_id, document=doc)

# 🚀 Commands and handlers
user_items = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📝 Input Item Names", callback_data="input_items")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome to Dota 2 Price Scraper!\n\nPress the button below to begin:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "input_items":
        await query.message.reply_text("🧾 Send me the item names (one per line).")
        context.user_data["awaiting_items"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_items"):
        text = update.message.text.strip()
        items = [line.strip() for line in text.split("\n") if line.strip()]
        user_items[update.effective_chat.id] = items
        context.user_data["awaiting_items"] = False

        keyboard = [[InlineKeyboardButton("🚀 Start Scraping", callback_data="start_scraping")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"✅ Got {len(items)} items!\nPress below to start scraping:", reply_markup=reply_markup)

    else:
        await update.message.reply_text("⚠️ Please use /start first.")

async def handle_scrape_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    items = user_items.get(chat_id)

    if not items:
        await query.message.reply_text("⚠️ No items found. Please send item names first.")
        return

    await query.message.reply_text("⏳ Scraping in progress, please wait...")
    await scrape_items(items, chat_id, context)

# 🏁 Run bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="^input_items$"))
    app.add_handler(CallbackQueryHandler(handle_scrape_button, pattern="^start_scraping$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
