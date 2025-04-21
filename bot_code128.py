import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.environ["TOKEN_TELEGRAM"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE = os.environ["NOTION_DATABASE"]

# Générer une URL de code Aztec
def get_aztec_url(data: str) -> str:
    return f"https://barcode.orcascan.com/?type=azteccode&format=png&data={data}"

# Formater un emplacement type 1A03203 -> 1 A03.203
def format_emplacement(texte: str) -> str:
    if len(texte) >= 7:
        zone = texte[0]
        rayon = texte[1]
        bloc = texte[2:5]
        niveau = texte[5:]
        return f"{zone} {rayon}{bloc}.{niveau}"
    return texte

# Commande /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("📦 /conteneur", callback_data="conteneur")],
        [InlineKeyboardButton("🏷️ /emplacement", callback_data="emplacement")],
        [InlineKeyboardButton("🔁 /gencode", callback_data="gencode")]
    ]
    await update.message.reply_text("Choisis une commande :", reply_markup=InlineKeyboardMarkup(buttons))

# Boutons de raccourci
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(f"{query.data} ")

# Envoi à Notion
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

# Commande générique
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str, is_emplacement=False):
    if not context.args:
        await update.message.reply_text("Envoie un code après la commande.")
        return

    user_input = context.args[0].upper()
    code = prefix + user_input
    url = get_aztec_url(code)

    # Format spécial pour Notion
    if is_emplacement:
        notion_format = format_emplacement(user_input)
        keyboard = [
            [
                InlineKeyboardButton("🖨️ Imprimer", callback_data=f"print::{notion_format}"),
                InlineKeyboardButton("❌ Pas besoin", callback_data="skip")
            ]
        ]
        await update.message.reply_photo(photo=url, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text(f"Code pour emplacement : {code}")
    else:
        await update.message.reply_photo(photo=url)
        await update.message.reply_text(f"Code : {code}")

# Gestion des impressions
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

# Lancement
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("gencode", lambda u, c: generate(u, c, "")))
app.add_handler(CommandHandler("conteneur", lambda u, c: generate(u, c, "900")))
app.add_handler(CommandHandler("emplacement", lambda u, c: generate(u, c, "902", is_emplacement=True)))
app.add_handler(CallbackQueryHandler(button_handler, pattern="^(conteneur|emplacement|gencode)$"))
app.add_handler(CallbackQueryHandler(print_button, pattern="^(print::|skip)"))

# Démarrage via webhook
WEBHOOK_URL = "https://ledrivebot.onrender.com"

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )