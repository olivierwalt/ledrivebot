import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.environ["TOKEN_TELEGRAM"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE = os.environ["NOTION_DATABASE"]

# Génère une URL d’un code Aztec
def get_aztec_url(data: str) -> str:
    return f"https://barcode.orcascan.com/?type=azteccode&format=png&data={data}"

# Corrige le format pour Notion : 1A04123 → 1 A04.123
def format_emplacement(texte: str) -> str:
    if len(texte) == 7:
        zone = texte[0]           # 1
        rayon = texte[1]          # A
        bloc = texte[2:5]         # 041
        niveau = texte[5:]        # 23
        return f"{zone} {rayon}{bloc}.{niveau}"
    return texte

# Envoie une ligne dans Notion
def send_to_notion(emplacement: str):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": { "database_id": NOTION_DATABASE },
        "properties": {
            "Emplacement": { "title": [{ "text": { "content": emplacement } }] },
            "Demandé par": { "rich_text": [{ "text": { "content": "Bot Telegram" } }] }
        }
    }
    requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut 👋 Je suis prêt ! Utilise /menu pour commencer.")

# /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("📦 /conteneur", callback_data="conteneur")],
        [InlineKeyboardButton("🏷️ /emplacement", callback_data="emplacement")],
        [InlineKeyboardButton("🔁 /gencode", callback_data="gencode")]
    ]
    await update.message.reply_text("Choisis une commande :", reply_markup=InlineKeyboardMarkup(buttons))

# Actions sur boutons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(f"{query.data} ")

# Gestion des boutons "imprimer" ou "pas besoin"
async def print_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("print::"):
        emplacement = data.split("::")[1]
        send_to_notion(emplacement)
        await query.edit_message_caption(caption=f"🖨️ Impression demandée pour : {emplacement}")
    elif data == "skip":
        await query.edit_message_caption(caption="❌ Impression annulée.")

# Commandes générales : conteneur, gencode...
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str, is_emplacement=False):
    if not context.args:
        await update.message.reply_text("Merci d'ajouter un code après la commande.")
        return

    user_input = context.args[0].upper()
    code = prefix + user_input
    url = get_aztec_url(code)

    if is_emplacement:
        formatted = format_emplacement(user_input)
        keyboard = [
            [
                InlineKeyboardButton("🖨️ Imprimer", callback_data=f"print::{formatted}"),
                InlineKeyboardButton("❌ Pas besoin", callback_data="skip")
            ]
        ]
        await update.message.reply_photo(photo=url, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_photo(photo=url)
        await update.message.reply_text(f"Code : {code}")

# Initialise le bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("gencode", lambda u, c: generate(u, c, "")))
app.add_handler(CommandHandler("conteneur", lambda u, c: generate(u, c, "900")))
app.add_handler(CommandHandler("emplacement", lambda u, c: generate(u, c, "902", is_emplacement=True)))
app.add_handler(CallbackQueryHandler(button_handler, pattern="^(conteneur|emplacement|gencode)$"))
app.add_handler(CallbackQueryHandler(print_button, pattern="^(print::|skip)"))

# Webhook pour Render
WEBHOOK_URL = "https://ledrivebot.onrender.com"

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )