from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import os
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_name = 'session'

source_chat_id = -1001972505443
target_chat_id = -1002539120057

download_path = './downloads/'
os.makedirs(download_path, exist_ok=True)

with TelegramClient(session_name, api_id, api_hash) as client:
    source = client.get_entity(source_chat_id)
    target = client.get_entity(target_chat_id)

    for msg in client.iter_messages(source, reverse=True):
        try:
            # CASE 1: Just text message
            if msg.text and not msg.media:
                client.send_message(target, msg.text)
                print(f"✅ Copied text message ID {msg.id}")

            # CASE 2: Photo or document with optional caption
            elif msg.media:
                file_path = client.download_media(msg, file=download_path)
                if file_path:
                    client.send_file(target, file_path, caption=msg.text or "")
                    print(f"📁 Sent media from message ID {msg.id}")

        except Exception as e:
            print(f"❌ Error on message ID {msg.id}: {e}")
