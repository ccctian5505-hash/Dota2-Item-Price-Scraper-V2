import os
import time
import random
import requests
import unicodedata
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import traceback

# === ENVIRONMENT VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === CLEAN ITEM NAME ===
def clean_item_name(name):
    name = (
        name.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .strip()
    )
    name = unicodedata.normalize("NFKC", name)
    return name


# === SCRAPE PRICE FUNCTION (Dota 2, PHP) ===
def get_price(item_name, retries=3):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "country": "PH",
        "currency": 12,  # PHP
        "appid": 570,    # Dota 2 App ID
        "market_hash_name": item_name,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return (
                        data.get("lowest_price")
                        or data.get("median_price")
                        or "No price listed"
                    )
        except Exception:
            pass
        time.sleep(3)
    return "Error fetching price"


# === /start COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Dota 2 Price Checker Bot!\n\n"
        "Send me a list of Dota 2 item names (one per line), and I’ll scrape their Steam Market prices in PHP.\n\n"
        "Example:\n"
        "```\nMalefic Drake’s Hood\nProfane Union\nShatterblast Core\n```",
        parse_mode="Markdown",
    )


# === SCRAPE ITEMS FROM TELEGRAM ===
async def scrape_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        items_text = update.message.text.strip()
        items = [line.strip() for line in items_text.splitlines() if line.strip()]

        if not items:
            await update.message.reply_text("⚠️ Please send valid item names (one per line).")
            return

        start_time = time.time()
        loading_msg = await update.message.reply_text(f"⏳ Starting scrape for {len(items)} items...")

        # Prepare output filename
        ph_time = datetime.now(pytz.timezone("Asia/Manila"))
        now = ph_time.strftime("%Y-%m-%d_%H-%M")
        output_file = f"Price_Checker_Dota2_{now}.txt"

        results = []
        success_count = 0
        fail_count = 0
        total_value = 0.0

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("Source Name\tScraped Name\tPrice (PHP)\n")

            for i, item in enumerate(items, start=1):
                clean_name = clean_item_name(item)
                price = get_price(clean_name)

                # Clean numeric PHP for total calculation
                price_num = 0.0
                if isinstance(price, str):
                    clean_price = (
                        price.replace("₱", "")
                        .replace("P", "")
                        .replace(",", "")
                        .replace(" ", "")
                        .strip()
                    )
                    try:
                        price_num = float(clean_price)
                        total_value += price_num
                    except ValueError:
                        pass

                if price not in ["Error fetching price", "No price listed"]:
                    success_count += 1
                else:
                    fail_count += 1

                results.append(f"{item} → {price}")
                f.write(f"{item}\t{clean_name}\t{price}\n")

                # Random delay per item (3–6s)
                delay = random.uniform(3, 6)
                time.sleep(delay)

                # Progress updates every 20 items
                if i % 20 == 0 or i == len(items):
                    await update.message.reply_text(f"📊 Progress: {i}/{len(items)} items scraped...")
                    cooldown = random.randint(30, 50)
                    await update.message.reply_text(f"😴 Cooling down for {cooldown}s to avoid Steam rate limits...")
                    time.sleep(cooldown)

        await loading_msg.delete()

        # Send results (split long messages)
        result_text = "\n".join(results)
        chunk_size = 3500
        for i in range(0, len(result_text), chunk_size):
            await update.message.reply_text(result_text[i:i + chunk_size])

        elapsed = time.time() - start_time
        mins, secs = divmod(int(elapsed), 60)
        summary = (
            f"\n✅ *Scraping complete!*\n"
            f"📦 Total Items: {len(items)}\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {fail_count}\n"
            f"💰 Total Value: ₱{total_value:,.2f}\n"
            f"⏱ Duration: {mins}m {secs}s"
        )
        await update.message.reply_text(summary, parse_mode="Markdown")

        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(output_file, "rb"))

    except Exception:
        error_message = f"❌ An error occurred:\n```\n{traceback.format_exc()}\n```"
        await update.message.reply_text(error_message, parse_mode="Markdown")


# === MAIN ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scrape_items))
    print("🤖 Dota 2 Price Checker Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
