import os
import json
from dotenv import load_dotenv
from telethon import TelegramClient, events
from extension import sqs_client

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
        print("EVENT: \n", event)
        print("message=: \n", event.stringify())
        # print("message=: \n", dir(event))
        # print("channel_id=: \n", event.chat_id)
        # print("message_id=: \n", event.message.id)
        # print("message_date=: \n", event.message.date)
        print("reply_to=: \n", event.reply_to.reply_to_msg_id if event.reply_to else None)
        reply_msg_id = event.reply_to.reply_to_msg_id if event.reply_to else None
        body={
            "chat_id": event.chat_id,
            "msg_id": event.message.id,
            "msg_date": event.message.date.isoformat(),
            "msg_text": event.message.message,
            "reply_msg_id": reply_msg_id,
        }
        print("body to sent to sqs ", body)
        sqs_client.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/549378813718/tg_msg_queue.fifo",
            MessageBody=json.dumps(body),
            MessageGroupId=f'queue-{event.chat_id}',
        )
        # await client.forward_messages(to_channel, event.message)
        # print(f"Forwarded new message from {event.chat_id} to {to_channel}")
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
