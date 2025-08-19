import pandas as pd
import datetime
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# Load timetable
df = pd.read_csv("timetable.csv")

# Store chat IDs of users
subscribed_users = set()

# Your Telegram ID (for admin rights)
ADMIN_ID = 123456789  # Replace with your Telegram numeric ID

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_users.add(chat_id)
    await update.message.reply_text(
        "Hello! 👋\n"
        "Type a day name (e.g., Monday) to get that day's timetable.\n"
        "Type 'My timetable' to see the full week's schedule.\n"
        "You'll also get your daily timetable automatically at 8:00 AM."
    )

# Handle timetable requests
async def get_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().lower()

    if user_text == "my timetable":
        reply = ""
        for day in df['Day'].unique():
            day_schedule = df[df['Day'] == day]
            schedule_text = "\n".join([f"{row['Time']}: {row['Subject']}" for _, row in day_schedule.iterrows()])
            reply += f"📅 {day}:\n{schedule_text}\n\n"
        await update.message.reply_text(reply.strip())
    else:
        day = user_text.capitalize()
        filtered = df[df['Day'] == day]
        if filtered.empty:
            await update.message.reply_text("❌ No timetable found for that day.")
        else:
            timetable = "\n".join([f"{row['Time']}: {row['Subject']}" for _, row in filtered.iterrows()])
            await update.message.reply_text(f"📅 Timetable for {day}:\n{timetable}")

# Auto daily reminder
async def send_daily_timetable(app):
    today = datetime.datetime.now().strftime("%A")
    filtered = df[df['Day'] == today]
    
    if not filtered.empty:
        timetable = "\n".join([f"{row['Time']}: {row['Subject']}" for _, row in filtered.iterrows()])
        message = f"⏰ Good morning! Here is your timetable for {today}:\n{timetable}"
        for chat_id in subscribed_users:
            try:
                await app.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")

# Broadcast (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <your message>")
        return
    
    message = "📢 ANNOUNCEMENT:\n" + " ".join(context.args)
    sent_count = 0
    for chat_id in subscribed_users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            sent_count += 1
        except:
            pass
    await update.message.reply_text(f"✅ Sent to {sent_count} users.")

# Run bot
TOKEN = os.getenv("BOT_TOKEN")  # From environment variable
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))  # New admin command
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_timetable))

# Schedule daily reminders
scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_timetable, "cron", hour=8, minute=0, args=[app])
scheduler.start()

print("Bot with auto reminders + broadcast is running...")
app.run_polling()