from telethon.sync import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_name = 'session'

print(api_id, api_hash)

source_chat_id = -1001338521686

with TelegramClient(session_name, api_id, api_hash) as client:
    # source = client.get_entity(source_chat_id)
    # print("Source : ", source)

    messages = client.get_messages(source_chat_id, limit=20)
    for message in messages:
        print("\n\n", "==="*50)
        print(f"{message.id}: {message.text or '[Non-text message]'}")
