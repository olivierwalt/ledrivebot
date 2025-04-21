from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
import requests
from notion_client import Client
from datetime import datetime

# 🧠 Notion setup
notion_token = "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"
notion_database_id = "0d858cdd58724beeb5467a9be512bb22"
notion = Client(auth=notion_token)

# Stockage des derniers emplacements formatés à envoyer
last_generated_codes = {}

# 📦 API Aztec
def get_aztec_image(code_data: str) -> BytesIO:
    url = f"https://barcode.orcascan.com/?type=azteccode&format=png&data={code_data}"
    response = requests.get(url)
    buffer = BytesIO(response.content)
    buffer.seek(0)
    return buffer

# 🔤 Formater un emplacement comme demandé
def format_emplacement(raw: str) -> str:
    # Exemple : 1A03203 → 1 A03.203
    return f"{raw[0]} {raw[1]}{raw[2:4]}.{raw[4:]}"

# 🖨️ Envoi dans Notion avec format adapté
def send_to_notion(formatted_code: str):
    try:
        now = datetime.now().isoformat()
        notion.pages.create(
            parent={"database_id": notion_database_id},
            properties={
                "Emplacement": {
                    "title": [
                        {"text": {"content": formatted_code}}
                    ]
                },
                "Demandé par": {
                    "rich_text": [
                        {"text": {"content": "Bot Telegram"}}
                    ]
                },
                "Date": {
                    "date": {
                        "start": now
                    }
                }
            }
        )
    except Exception as e:
        print(f"[ERREUR Notion] {e}")

# 🔘 Boutons Imprimer / Pas besoin
def get_action_buttons() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🖨️ Imprimer", callback_data='print'),
            InlineKeyboardButton("❌ Pas besoin", callback_data='skip')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ✅ Commandes
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenue ! Utilise /gencode, /emplacement ou /conteneur. Tape /menu pour les options.")

async def gencode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ''.join(context.args).upper()
    if not text:
        await update.message.reply_text("Utilise la commande ainsi (exemple) : /gencode 329182763512938")
        return

    buffer = get_aztec_image(text)
    await update.message.reply_photo(photo=buffer, caption=f"Code Aztec : {text}")

async def emplacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ''.join(context.args).upper()
    if not text or len(text) < 7:
        await update.message.reply_text("Utilise la commande ainsi : /emplacement 1A03203 (zone allée échelle emplacement)")
        return

    full_code = f"902{text}"
    formatted = format_emplacement(text)
    buffer = get_aztec_image(full_code)
    last_generated_codes[update.effective_user.id] = formatted
    await update.message.reply_photo(photo=buffer, caption=f"Code Aztec pour emplacement : {formatted}", reply_markup=get_action_buttons())

async def conteneur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ''.join(context.args).upper()
    if not text:
        await update.message.reply_text("Utilise la commande ainsi : /conteneur 12345 (renseigne le numéro complet dans l'infobulle du journal)")
        return

    full_code = f"900{text}"
    buffer = get_aztec_image(full_code)
    await update.message.reply_photo(photo=buffer, caption=f"Code Aztec pour conteneur : {full_code}")

# 🎛️ Menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 Générer un code", callback_data='menu_code')],
        [InlineKeyboardButton("🧱 Code Emplacement", callback_data='menu_emplacement')],
        [InlineKeyboardButton("🛢️ Code Conteneur", callback_data='menu_conteneur')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choisis une action :", reply_markup=reply_markup)

# 🔘 Gestion des boutons
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    if action == 'menu_code':
        await query.message.reply_text("Envoie /gencode suivi du texte (ex : /gencode 3827192039281)")
    elif action == 'menu_emplacement':
        await query.message.reply_text("Envoie /emplacement suivi du code (ex : /emplacement 1A03203)")
    elif action == 'menu_conteneur':
        await query.message.reply_text("Envoie /conteneur suivi du code (ex : /conteneur 2871662738271)")
    elif action == 'print':
        formatted_code = last_generated_codes.get(user_id)
        if formatted_code:
            send_to_notion(formatted_code)
            await query.message.reply_text(f"🖨️ Demande d'impression pour le code {formatted_code} bien envoyée.")
        else:
            await query.message.reply_text("Aucun code emplacement à imprimer trouvé.")
    elif action == 'skip':
        await query.message.reply_text("👍 Pas d'impression, action annulée.")

# 🚀 Lancement du bot
app = ApplicationBuilder().token("7900663906:AAHvwP4jdX_ySu2hiHvPYMV7-0dSyiGkiCQ").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("gencode", gencode))
app.add_handler(CommandHandler("emplacement", emplacement))
app.add_handler(CommandHandler("conteneur", conteneur))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(handle_button))
app.run_polling()