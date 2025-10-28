import os
import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# -----------------------------
# Cargar variables de entorno
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MODO_PAGO_DEMO = True
CURRENCY = "EUR"

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ Debes configurar BOT_TOKEN y WEBHOOK_URL en las variables de entorno.")

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Datos de ejemplo
# -----------------------------
CUENTAS = [
    {"id": 1, "nombre": "Netflix", "precio": 15, "clave": "PREM-1MES-123"},
    {"id": 2, "nombre": "HBO Max", "precio": 15.99, "clave": "CURSO-VID-456"},
    {"id": 3, "nombre": "Crunchyroll", "precio": 9.99, "clave": "TPL-789"},
    {"id": 4, "nombre": "Disney+", "precio": 20, "clave": "TPL-789"},
    {"id": 5, "nombre": "VPN para móviles", "precio": 5.99, "clave": "TPL-789"},
]

PROVEEDORES = [
    {"id": 101, "nombre": "Tecnología", "precio": 30, "clave": "+86 180 3810 041"},
    {"id": 102, "nombre": "Zapatos", "precio": 35, "clave": "+86 177 5078 0580"},
    {"id": 103, "nombre": "Ropa", "precio": 40, "clave": "+86 180 0607 6717"},
    {"id": 104, "nombre": "Vapers", "precio": 40, "clave": "+86 136 5969 4101"},
    {"id": 105, "nombre": "Perfumes", "precio": 30, "clave": "+86 158 1870 9179"},
]

# -----------------------------
# Base de datos
# -----------------------------
def inicializar_db():
    if not os.path.exists("pedidos.db"):
        conn = sqlite3.connect("pedidos.db")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                producto TEXT,
                precio REAL,
                estado TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("✅ Base de datos creada correctamente.")
    else:
        logger.info("📂 Base de datos ya existe.")

def registrar_pedido(user_id, producto, precio, estado):
    conn = sqlite3.connect("pedidos.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO pedidos (user_id, producto, precio, estado) VALUES (?, ?, ?, ?)",
        (user_id, producto, precio, estado)
    )
    conn.commit()
    conn.close()

# -----------------------------
# Handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧾 Cuentas", callback_data="categoria_cuentas")],
        [InlineKeyboardButton("🏪 Proveedores", callback_data="categoria_proveedores")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 ¡Bienvenido a la tienda!\n\nElige una categoría:", reply_markup=reply_markup)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Estoy vivo y funcionando correctamente!")

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "categoria_cuentas":
        keyboard = [[InlineKeyboardButton(f"{p['nombre']} - €{p['precio']}", callback_data=f"comprar_cuenta_{p['id']}")] for p in CUENTAS]
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu")])
        await query.edit_message_text("🧾 *Cuentas disponibles:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == "categoria_proveedores":
        keyboard = [[InlineKeyboardButton(f"{p['nombre']} - €{p['precio']}", callback_data=f"comprar_proveedor_{p['id']}")] for p in PROVEEDORES]
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu")])
        await query.edit_message_text("🏪 *Proveedores disponibles:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data.startswith("comprar_"):
        _, tipo, pid = data.split("_")
        producto_id = int(pid)
        producto = None
        if tipo == "cuenta":
            producto = next((p for p in CUENTAS if p["id"] == producto_id), None)
        elif tipo == "proveedor":
            producto = next((p for p in PROVEEDORES if p["id"] == producto_id), None)
        if not producto:
            await query.edit_message_text("❌ Producto no encontrado.")
            return
        if MODO_PAGO_DEMO:
            registrar_pedido(user_id, producto["nombre"], producto["precio"], "pagado")
            await query.edit_message_text(f"✅ *Compra completada (modo demo)*\n\n🛒 *{producto['nombre']}*\n💰 Precio: {producto['precio']} {CURRENCY}\n\n🔑 Tu clave o contacto:\n`{producto['clave']}`", parse_mode="Markdown")
        else:
            await query.edit_message_text("💳 Aquí iría el enlace de pago real (por implementar).")

    elif data == "volver_menu":
        keyboard = [
            [InlineKeyboardButton("🧾 Cuentas", callback_data="categoria_cuentas")],
            [InlineKeyboardButton("🏪 Proveedores", callback_data="categoria_proveedores")]
        ]
        await query.edit_message_text("👋 ¡Bienvenido nuevamente!\n\nElige una categoría:", reply_markup=InlineKeyboardMarkup(keyboard))

# -----------------------------
# Main
# -----------------------------
def main():
    inicializar_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(boton_callback))

    PORT = int(os.environ.get("PORT", 5000))
    WEBHOOK_FULL = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    logger.info(f"🚀 Bot arrancando con webhook: {WEBHOOK_FULL}")
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=WEBHOOK_FULL)

if __name__ == "__main__":
    main()

