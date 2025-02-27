import os
import logging
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsKicked, DocumentAttributeFilename, ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.errors import FloodWaitError, RPCError
import io

# Configuración de logging para Render y Replit 📋
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Carga de variables de entorno 🔑
api_id = os.getenv('API_ID', '23047044')
api_hash = os.getenv('API_HASH', '2efd6bb57df5d0ef23b978825fe2b50e')
bot_token = os.getenv('BOT_TOKEN', '7969250405:AAHMY6ZZyUAVqN4LkppZkYy4SZuapR-yIU0')

# Inicia el cliente de Telegram como bot 🤖
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Función para dividir listas largas en fragmentos ✂️
def split_message(text, max_length=4096):
    """Divide un mensaje largo en partes que Telegram pueda manejar."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# Genera un archivo de texto con la lista de usuarios expulsados 📄
def generate_ban_file(banned_users):
    """Crea un archivo de texto en memoria con la lista de usuarios expulsados."""
    buffer = io.StringIO()
    buffer.write("ID,Username\n")  # Encabezado simple tipo CSV
    for user in banned_users:
        username = f"@{user.username}" if user.username else "N/A"
        buffer.write(f"{user.id},{username}\n")
    buffer.seek(0)
    return io.BytesIO(buffer.getvalue().encode('utf-8')), f"banned_users_{len(banned_users)}.txt"

# Comando /listabn (solo para administradores) 🚫
@client.on(events.NewMessage(pattern=r'^/listabn\s*', incoming=True))
async def listabn_handler(event):
    chat = await event.get_chat()
    chat_id = event.chat_id
    sender = await event.get_sender()

    logger.debug(f"Comando /listabn recibido en chat {chat_id} por {sender.id}: {event.message.text}")

    # Verifica si el usuario es administrador o creador 🔍
    try:
        participant = await client.get_participant(chat, sender.id)
        is_admin = isinstance(participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except Exception as e:
        logger.warning(f"No se pudo verificar permisos de {sender.id} en chat {chat_id}: {str(e)}")
        is_admin = False

    # Respuesta para no administradores 🚷
    if not is_admin:
        await event.reply("⛔ ¡Solo los administradores pueden usar este comando! Contacta a un administrador si necesitas ayuda.")
        logger.warning(f"Usuario no administrador {sender.id} intentó usar /listabn en {chat_id}")
        return

    # Verifica permisos del bot 🔧
    if not hasattr(chat, 'admin_rights') or not chat.admin_rights or not chat.admin_rights.ban_users:
        await event.reply("⚠️ Necesito permisos de administrador para listar usuarios expulsados.")
        logger.warning(f"Intento de /listabn sin permisos de bot en {chat_id}")
        return

    # Notifica que el comando está en ejecución ⏳
    status_msg = await event.reply("⏳ Procesando la lista de usuarios expulsados... Esto puede tomar un momento.")
    logger.info(f"Inicio de /listabn en chat {chat_id} por administrador {sender.id}")

    try:
        # Obtiene usuarios expulsados 👥
        banned_users = []
        logger.info(f"Obteniendo usuarios expulsados en {chat_id}")
        async for user in client.iter_participants(chat, filter=ChannelParticipantsKicked, aggressive=True):
            banned_users.append(user)
            logger.debug(f"Usuario expulsado: ID {user.id}, Username {user.username or 'N/A'}")

        if not banned_users:
            await status_msg.edit("✅ No hay usuarios expulsados en este chat.")
            logger.info(f"Finalizado /listabn en {chat_id}: No hay usuarios expulsados.")
            return

        # Construye la lista para mostrar en el chat 📜
        ban_list = [f"@{user.username}" if user.username else f"ID: {user.id}" for user in banned_users]
        total_banned = len(ban_list)
        ban_text = f"🚫 Usuarios expulsados ({total_banned}):\n" + "\n".join(ban_list[:10])  # Limita a 10
        if total_banned > 10:
            ban_text += f"\n... y {total_banned - 10} más. Descarga el archivo para la lista completa."

        # Divide el mensaje si es muy largo 📏
        messages = split_message(ban_text)
        for i, msg in enumerate(messages):
            if i == 0:
                await status_msg.edit(msg)
            else:
                await event.reply(msg)

        # Genera y envía el archivo descargable 📤
        file_content, file_name = generate_ban_file(banned_users)
        await client.send_file(
            chat_id,
            file=file_content,
            caption=f"📋 Lista completa de {total_banned} usuarios expulsados.",
            file_name=file_name,
            attributes=[DocumentAttributeFilename(file_name)]
        )
        logger.info(f"Finalizado /listabn en {chat_id}: {total_banned} usuarios listados y archivo enviado.")

    except FloodWaitError as e:
        await status_msg.edit(f"⏱️ Demasiadas solicitudes. Espera {e.seconds} segundos.")
        logger.error(f"FloodWaitError en {chat_id}: Espera de {e.seconds} segundos.")
    except RPCError as e:
        await status_msg.edit("❌ Error al procesar la lista. Intenta de nuevo más tarde.")
        logger.error(f"Error RPC en {chat_id}: {str(e)}")
    except Exception as e:
        await status_msg.edit("⚠️ Error inesperado. Contacta al administrador del bot.")
        logger.exception(f"Excepción no manejada en {chat_id}: {str(e)}")

# Función principal para iniciar el bot 🚀
async def main():
    await client.start(bot_token=bot_token)
    me = await client.get_me()
    logger.info(f"Bot iniciado como @{me.username} (ID: {me.id}) 🎉")

# Inicia el bot
if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
        client.run_until_disconnected()