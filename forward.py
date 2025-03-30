import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

# Load environment variables
load_dotenv()
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_name = os.getenv("TG_SESSION_NAME")

# Source channels as a list of integers
to_channel = int(os.getenv("TO_CHANNEL_ID"))
from_channels = [
    int(channel.strip()) for channel in os.getenv("FROM_CHANNEL_IDS").split(",")
]

# Initialize the Telegram client
client = TelegramClient(session_name, api_id, api_hash)


# Register the handler for new messages
@client.on(events.NewMessage(chats=from_channels))
async def new_message_handler(event):
    try:
        await client.forward_messages(to_channel, event.message)
        print(f"Forwarded new message from {event.chat_id} to {to_channel}")
    except Exception as e:
        print(f"Failed to forward new message: {e}")


# Register the handler for edited messages
@client.on(events.MessageEdited(chats=from_channels))
async def edited_message_handler(event):
    try:
        await client.forward_messages(to_channel, event.message)
        print(f"Forwarded edited message from {event.chat_id} to {to_channel}")
    except Exception as e:
        print(f"Failed to forward edited message: {e}")


if __name__ == "__main__":
    client.start()
    print("Userbot is running...")
    client.run_until_disconnected()
