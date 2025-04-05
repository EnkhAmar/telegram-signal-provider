import json
from dynamodb_json import json_util
import traceback
from classifiers import ForexSignalProcessor
from extension import dynamodb, telegram_bot, TO_CHANNEL_ID
import utils

processor = ForexSignalProcessor()

# handle sqs duplicate message
##
def handler(event, context):
    # Loop through the records in the event
    for record in event['Records']:
        # The message body is stored in the 'body' key
        message_body = record['body']
        
        # Parse the message body as JSON
        try:
            message = json.loads(message_body)
            
            chat_id = message['chat_id']
            msg_id = message['msg_id']
            msg_date = message['msg_date']
            msg_text = message['msg_text']
            reply_msg_id = message['reply_msg_id']

            result = processor.process_message(message)

            dynamodb.put_item(
                TableName="telegram_msgs",
                Item=json_util.dumps({
                    "chat_id": chat_id,
                    "msg_id": msg_id,
                    "reply_msg_id": reply_msg_id,
                    "text": msg_text,
                    "action": result["action"],
                    "created_at": msg_date,
                }, True)
            )

            if result['action'] == 'NEW_SIGNAL':
                dynamodb.put_item(
                    TableName="orders",
                    Item=json_util.dumps({
                        "order_id": result["order_id"],
                        "status": "PENDING",
                        "chat_id": chat_id,

                        "pair": result["pair"],
                        "side": result["side"],
                        "type": result["type"],
                        "entry": result["entry"],
                        "stop_loss": result["stop_loss"],
                        "take_profit": result["take_profit"],
                        "pnl": 0,
                        "created_at": msg_date,
                        "updated_at": "",
                    }, True)
                )
            telegram_bot.send_message(
                chat_id=TO_CHANNEL_ID,
                text=json.dumps(result)
            )


            
        except json.JSONDecodeError as e:
            print(f"Failed to decode message body: {message_body} due to {str(e)}")
            continue
        except Exception as e:
            print(e)
            traceback_str = traceback.format_exc()
            print(traceback_str)
            continue
    
    return {
        "success": True,
    }


def dead_letter_handler(event, context):
    # Loop through the records in the event
    for record in event['Records']:
        # The message body is stored in the 'body' key
        message_body = record['body']
        print("Dead message body : ", message_body)