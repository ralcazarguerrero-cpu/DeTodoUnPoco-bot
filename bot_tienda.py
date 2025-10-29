import os
import logging
import sqlite3
from dotenv import load_dotenv
from contextlib import contextmanager
from typing import Optional, List, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===============================
# CONFIGURACIÓN INICIAL
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno (.env)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Debes configurar BOT_TOKEN en el archivo .env")

# ===============================
# DATOS DE EJEMPLO
# ===============================
CUENTAS = [
    {"id": 1, "nombre": "Netflix", "precio": 15, "clave": "PREM-1MES-123"},
    {"id": 2, "nombre": "HBO Max", "precio": 15.99, "clave": "CURSO-VID-456"},
    {"id": 3, "nombre": "Crunchyroll", "precio": 9.99, "clave": "TPL-789"},
    {"id": 4, "nombre": "Disney+", "precio": 20, "clave": "TPL-789"},
    {"id": 5, "nombre": "VPN para móviles", "precio": 5.99, "clave": "TPL-789"}
]

PROVEEDORES = [
    {"id": 101, "nombre": "Tecnología", "precio": 30, "clave": "+86 180 3810 041"},
    {"id": 102, "nombre": "Zapatos", "precio": 35, "clave": "+86 177 5078 0580"},
    {"id": 103, "nombre": "Ropa", "precio": 40, "clave": "+86 180 0607 6717"},
    {"id": 104, "nombre": "Vapers", "precio": 40, "clave": "+86 136 5969 4101"},
    {"id": 105, "nombre": "Perfumes", "precio": 30, "clave": "+86 158 1870 9179"}
]

DB_PATH = "pedidos.db"


# ===============================
# BASE DE DATOS
# ===============================
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    def __init__(self):
        self.inicializar_db()

    def inicializar_db(self):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    producto TEXT,
                    precio REAL,
                    estado TEXT
                )
            """)
            conn.commit()
        logger.info("✅ Base de datos inicializada correctamente.")

    def registrar_pedido(self, user_id: int, producto: str, precio: float, estado: str) -> bool:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO pedidos (user_id, producto, precio, estado)
                    VALUES (?, ?, ?, ?)
                """, (user_id, producto, precio, estado))
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al registrar pedido: {str(e)}")
            return False


# ===============================
# BOT DE LA TIENDA
# ===============================
class TiendaBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.modo_demo = True
        self.currency = "EUR"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        keyboard = [
            [InlineKeyboardButton("🧾 Cuentas", callback_data="categoria_cuentas")],
            [InlineKeyboardButton("🏪 Proveedores", callback_data="categoria_proveedores")]
        ]
        await update.message.reply_text(
            "👋 ¡Bienvenido a la tienda!\n\nElige una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def mostrar_productos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra los productos según la categoría"""
        query = update.callback_query
        await query.answer()

        categoria = "cuentas" if query.data == "categoria_cuentas" else "proveedores"
        productos = CUENTAS if categoria == "cuentas" else PROVEEDORES

        keyboard = [
            [InlineKeyboardButton(
                f"{p['nombre']} - {p['precio']} {self.currency}",
                callback_data=f"comprar_{categoria}_{p['id']}"
            )] for p in productos
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu")])

        await query.edit_message_text(
            f"🛍 *Productos de {categoria.capitalize()}:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def comprar_producto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simula la compra de un producto"""
        query = update.callback_query
        await query.answer()

        _, categoria, pid = query.data.split("_")
        producto_id = int(pid)

        lista = CUENTAS if categoria == "cuentas" else PROVEEDORES
        producto = next((p for p in lista if p["id"] == producto_id), None)

        if not producto:
            await query.edit_message_text("❌ Producto no encontrado.")
            return

        self.db.registrar_pedido(query.from_user.id, producto["nombre"], producto["precio"], "pagado")

        await query.edit_message_text(
            f"✅ *Compra completada (modo demo)*\n\n"
            f"🛒 *{producto['nombre']}*\n"
            f"💰 *Precio:* {producto['precio']} {self.currency}\n\n"
            f"🔑 *Clave / Contacto:*\n`{producto['clave']}`",
            parse_mode="Markdown"
        )

    async def volver_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vuelve al menú principal"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("🧾 Cuentas", callback_data="categoria_cuentas")],
            [InlineKeyboardButton("🏪 Proveedores", callback_data="categoria_proveedores")]
        ]

        await query.edit_message_text(
            "👋 ¡Bienvenido nuevamente!\n\nElige una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ===============================
# MAIN (modo polling)
# ===============================
def main():
    bot = TiendaBot()
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.mostrar_productos, pattern="^categoria_"))
    app.add_handler(CallbackQueryHandler(bot.comprar_producto, pattern="^comprar_"))
    app.add_handler(CallbackQueryHandler(bot.volver_menu, pattern="^volver_menu$"))

    logger.info("🚀 Bot iniciado en modo polling (manual).")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
