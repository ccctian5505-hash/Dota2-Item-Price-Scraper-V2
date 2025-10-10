import requests
import time
import unicodedata
from datetime import datetime
import pytz
import os
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ Load from Railway environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 🔤 Clean up item name
def clean_item_name(name):
    name = name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    name = unicodedata.normalize("NFKC", name)
    return name

# 🏷️ Steam price scraper function (PHP)
def get_price(item_name, retries=3):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {"country": "PH", "currency": 12, "appid": 570, "market_hash_name": item_name}
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}

    for _ in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    price = data.get("lowest_price") or data.get("median_price") or "No price listed"
                    if isinstance(price, str):
                        price = price.replace("₱", "").replace("P", "").replace(",", "").strip()
                    return price
        except Exception:
            pass
        time.sleep(2)
    return "Error fetching price"

# 🧮 Calculate numeric value
def parse_price(price_str):
    try:
        return float(price_str)
    except:
        return 0.0

# 🛎️ Telegram file sender
async def send_telegram_file(file_path, chat_id, context):
    with open(file_path, "rb") as doc:
        await context.bot.send_document(chat_id=chat_id, document=doc)

# 🚀 Telegram command handler
async def scrape_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("⚠️ Please provide item names separated by commas.\n\nExample:\n`/scrape Malefic Drake’s Hood, Profane Union`", parse_mode="Markdown")
        return

    items = [x.strip() for x in user_input.split(",") if x.strip()]
    total_items = len(items)

    # Send loading message
    progress_msg = await update.message.reply_text(f"🔍 Starting scrape for {total_items} items... Please wait.")

    ph_time = datetime.now(pytz.timezone("Asia/Manila"))
    now = ph_time.strftime("%Y-%m-%d_%H-%M")
    output_file = f"Price_Checker_Dota2_{now}.txt"

    success_count = 0
    fail_count = 0
    total_value = 0.0
    results = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source Name\tScraped Name\tPrice (PHP)\n")

        for i, item in enumerate(items, start=1):
            clean_name = clean_item_name(item)
            price = get_price(clean_name)

            if "Error" not in price and "No price" not in price:
                success_count += 1
                total_value += parse_price(price)
            else:
                fail_count += 1

            results.append((item, clean_name, price))
            f.write(f"{item}\t{clean_name}\t{price}\n")
            time.sleep(2.5)

            # 🔁 Progress updates every 20 items
            if i % 20 == 0 or i == total_items:
                await progress_msg.edit_text(f"⏳ Scraping progress: {i}/{total_items} items done...")

    # ✅ Summary
    summary_lines = [f"{src} → {price}" for src, _, price in results]
    summary_text = "\n".join(summary_lines[:30])  # limit message length
    summary = (
        f"✅ Scraping complete!\n\n"
        f"📄 Total items: {total_items}\n"
        f"✅ Success: {success_count}\n"
        f"❌ Failed: {fail_count}\n"
        f"💰 Total Value: ₱{total_value:,.2f}\n\n"
        f"📋 Sample Results:\n{summary_text}"
    )

    await progress_msg.edit_text(summary)
    await send_telegram_file(output_file, update.message.chat_id, context)

# 🧩 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Dota 2 Price Checker!\n"
        "Use this command to start scraping:\n\n"
        "`/scrape Malefic Drake’s Hood, Profane Union`",
        parse_mode="Markdown"
    )

# 🚀 Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scrape", scrape_items))
    print("🤖 Dota 2 Price Checker Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
