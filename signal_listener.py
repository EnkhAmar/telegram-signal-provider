import os
import json
from dotenv import load_dotenv
from telethon import TelegramClient, events
from extension import sqs_client, dynamodb
from dynamodb_json import json_util
from datetime import datetime, timezone

# Load environment variables
load_dotenv()
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_name = os.getenv("TG_SESSION_NAME")

# Source channels as a list of integers
to_channel = int(os.getenv("TO_CHANNEL_ID"))
from_channels = json_util.loads(dynamodb.scan(
    TableName="signal_channels",
).get("Items", []))
print("from_channels", from_channels)
from_chat_ids = [channel['chat_id'] for channel in from_channels if channel.get('status') == 'ACTIVE']
print("from_chat_ids: ", from_chat_ids)

# Initialize the Telegram client
client = TelegramClient(session_name, api_id, api_hash)


# Register the handler for new messages
@client.on(events.NewMessage(chats=from_chat_ids))
async def new_message_handler(event):
    try:
        print("EVENT: \n", event)
        # print("message=: \n", event.stringify())
        # print("message=: \n", dir(event))
        # print("channel_id=: \n", event.chat_id)
        # print("message_id=: \n", event.message.id)
        # print("message_date=: \n", event.message.date)
        # print("reply_to=: \n", event.reply_to.reply_to_msg_id if event.reply_to else None)
        reply_msg_id = event.reply_to.reply_to_msg_id if event.reply_to else None
        signal_type = next(filter(lambda c: c['chat_id'] == event.chat_id, from_channels))['signal_type']
        
        body={
            "chat_id": event.chat_id,
            "msg_id": event.message.id,
            "msg_date": event.message.date.isoformat(),
            "msg_text": event.message.message,
            "reply_msg_id": reply_msg_id,
            "msg_type": "NEW", # "NEW|EDITED"
            "signal_type": signal_type,
        }
        print("body to sent to sqs = ", body, "\n")
        sqs_response = sqs_client.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/549378813718/tg_msg_queue.fifo",
            MessageBody=json.dumps(body),
            MessageGroupId=f'queue-{event.chat_id}',
        )
        print("sqs_response = ", sqs_response, "\n\n")
        # await client.forward_messages(to_channel, event.message)
        # print(f"Forwarded new message from {event.chat_id} to {to_channel}")
    except Exception as e:
        print(f"Failed to forward new message: {e}")


# Register the handler for edited messages
@client.on(events.MessageEdited(chats=from_chat_ids))
async def edited_message_handler(event):
    try:
        print("EDIT EVENT: \n", event)
        reply_msg_id = event.reply_to.reply_to_msg_id if event.reply_to else None
        signal_type = next(filter(lambda c: c['chat_id'] == event.chat_id, from_channels))['signal_type']
        body={
            "chat_id": event.chat_id,
            "msg_id": event.message.id,
            "msg_date": event.message.date.isoformat(),
            "msg_text": event.message.message,
            "reply_msg_id": reply_msg_id,
            "msg_type": "EDITED", # "NEW|EDITED"
            "signal_type": signal_type,
        }
        print("body to sent to sqs ", body)
        sqs_response = sqs_client.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/549378813718/tg_msg_queue.fifo",
            MessageBody=json.dumps(body),
            MessageGroupId=f'queue-{event.chat_id}',
        )
        print("sqs_response = ", sqs_response, "\n\n")

        # print(f"Forwarded edited message from {event.chat_id} to {to_channel}")
    except Exception as e:
        print(f"Failed to forward edited message: {e}")


@client.on(events.MessageDeleted(chats=from_chat_ids))
async def deleted_message_handler(event):
    try:
        print("DELETE EVENT: \n", event.stringify())
        # reply_msg_id = event.reply_to.reply_to_msg_id if event.reply_to else None
        signal_type = next(filter(lambda c: c['chat_id'] == event.chat_id, from_channels))['signal_type']
        body={
            "chat_id": event.chat_id,
            "msg_id": event.deleted_id,
            "msg_date": datetime.now(timezone.utc).isoformat(),
            "msg_text": "",
            "reply_msg_id": None,
            "msg_type": "DELETED", # "NEW|EDITED|DELETED"
            "signal_type": signal_type,
        }
        print("body to sent to sqs ", body)
        sqs_response = sqs_client.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/549378813718/tg_msg_queue.fifo",
            MessageBody=json.dumps(body),
            MessageGroupId=f'queue-{event.chat_id}',
        )
        print("sqs_response = ", sqs_response, "\n\n")
    except Exception as e:
        print(f"Failed to forward deleted message: {e}")


if __name__ == "__main__":
    client.start()
    print("Userbot is running...")
    client.run_until_disconnected()
