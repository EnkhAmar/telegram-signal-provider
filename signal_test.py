import os
import json
import argparse
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from extension import sqs_client, dynamodb
from dynamodb_json import json_util
from datetime import datetime, timezone
import uuid

# ----------------------
# Logging configuration
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("telegram_forwarder.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("TGForwarder")

# ----------------------
# Load environment
# ----------------------
load_dotenv()
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_name = os.getenv("TG_SESSION_NAME")

# Initialize Telegram client
client = TelegramClient(session_name, api_id, api_hash)


def load_channels(owner_key: str):
    """Query DynamoDB for active channels belonging to the given owner."""
    logger.info("Loading channels for owner='%s'", owner_key)
    from_channels = json_util.loads(
        dynamodb.query(
            TableName="signal_channels",
            IndexName="owner-status-index",
            KeyConditionExpression="#owner = :owner AND #status = :status",
            ExpressionAttributeNames={
                "#owner": "owner",
                "#status": "status"
            },
            ExpressionAttributeValues=json_util.dumps({
                ":owner": owner_key,
                ":status": "ACTIVE"
            }, True)
        ).get("Items", [])
    )
    from_chat_ids = [ch['chat_id'] for ch in from_channels if ch.get('status') == 'ACTIVE']
    logger.info("Loaded %d active channels", len(from_chat_ids))
    return from_channels, from_chat_ids


async def handle_message(event, msg_type: str, from_channels):
    """Helper to send message events (NEW, EDITED, DELETED) to SQS."""
    try:
        reply_msg_id = event.reply_to.reply_to_msg_id if event.reply_to else None
        signal_type = next(filter(lambda c: c['chat_id'] == event.chat_id, from_channels))['signal_type']

        body = {
            "uuid": str(uuid.uuid4()),
            "chat_id": event.chat_id,
            "msg_id": getattr(event, "deleted_id", event.message.id),
            "msg_date": (
                datetime.now(timezone.utc).isoformat()
                if msg_type == "DELETED"
                else event.message.date.isoformat()
            ),
            "msg_text": "" if msg_type == "DELETED" else event.message.message,
            "reply_msg_id": reply_msg_id if msg_type != "DELETED" else None,
            "msg_type": msg_type,
            "signal_type": signal_type,
        }

        logger.info("[%s] chat_id=%s msg_id=%s", msg_type, event.chat_id, body["msg_id"])
        logger.debug("Payload: %s", json.dumps(body, ensure_ascii=False, indent=2))

        sqs_response = sqs_client.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/549378813718/tg_msg_queue.fifo",
            MessageBody=json.dumps(body),
            MessageGroupId=f'queue-{event.chat_id}',
            MessageDeduplicationId=str(uuid.uuid4()),
        )
        logger.info("[%s] Sent to SQS (MessageId=%s)", msg_type, sqs_response.get("MessageId"))

    except Exception as e:
        logger.exception("Failed to forward %s message: %s", msg_type, str(e))


def parse_args():
    p = argparse.ArgumentParser(description="Telegram SQS forwarder")
    p.add_argument("--owner", dest="owner", type=str, required=True, help="owner key")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    owner_key = args.owner

    from_channels, from_chat_ids = load_channels(owner_key)
    logger.info("From channels: %s", from_channels)
    logger.info("From chat_ids: %s", from_chat_ids)

    # Register handlers after channels are known
    @client.on(events.NewMessage(chats=from_chat_ids))
    async def new_message_handler(event):
        await handle_message(event, "NEW", from_channels)

    @client.on(events.MessageEdited(chats=from_chat_ids))
    async def edited_message_handler(event):
        await handle_message(event, "EDITED", from_channels)

    @client.on(events.MessageDeleted(chats=from_chat_ids))
    async def deleted_message_handler(event):
        await handle_message(event, "DELETED", from_channels)

    client.start()
    logger.info("Userbot is running...")
    client.run_until_disconnected()
