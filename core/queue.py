import json
from dynamodb_json import json_util
import traceback
from classifiers import ForexSignalProcessor
from extension import dynamodb, TO_CHANNEL_ID, Telegram, TG_SIGNAL_BOT_TOKEN
import utils

processor = ForexSignalProcessor()
telegram_bot = Telegram(token=TG_SIGNAL_BOT_TOKEN)

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
            msg_type = message.get("msg_type", "NEW")

            result = processor.process_message(message)
            print("RAW MSG -- \n", message, "\n")
            print("RESULT -- \n", result, "\n")

            prev_msg = dynamodb.get_item(
                TableName="telegram_msgs",
                Key={"chat_id": {"S": chat_id}, "msg_id": {"S": msg_id}},
            ).get("Item", None)

            if msg_type == "NEW":
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
            elif msg_type == "EDITED":
                dynamodb.update_item(
                    TableName="telegram_msgs",
                    Key={"chat_id": {"S": chat_id}, "msg_id": {"S": msg_id}},
                    UpdateExpression="SET #text = :text, #action = :action, #updated_at = :updated_at",
                    ExpressionAttributeNames={
                        "#text": "text",
                        "#action": "action",
                        "#updated_at": "updated_at",
                    },
                    ExpressionAttributeValues=json_util.dumps({
                        ":text": msg_text,
                        ":action": result["action"],
                        ":updated_at": msg_date,
                    }, True),
                )

            if result['action'] == 'OTHER':
                return

            to_reply_id = None
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
                        "leverage": result.get("leverage"),
                        "pnl": 0,
                        "created_at": msg_date,
                        "updated_at": "",
                    }, True)
                )
                message = telegram_bot.make_entry_message(result)
            elif result['action'] in ['TP_HIT', 'SL_HIT']:
                update_res = dynamodb.update_item(
                    TableName="orders",
                    Key={"order_id": {"S": result["order_id"]}},
                    UpdateExpression="SET #status = :status, #updated_at = :updated_at",
                    ExpressionAttributeNames={
                        "#status": "status",
                        "#updated_at": "updated_at",
                    },
                    ExpressionAttributeValues=json_util.dumps({
                        ":status": result["action"],
                        ":updated_at": msg_date,
                    }, True),
                    ReturnValues="ALL_NEW",
                )
                print("update_res : ", update_res)
                to_reply_id = json_util.loads(update_res["Attributes"], True)["to_msg_id"]
                message = telegram_bot.make_tp_message(result) if result['action'] == 'TP_HIT' else telegram_bot.make_sl_message(result)


            if result['action'] in ["TP_HIT", "SL_HIT", "NEW_SIGNAL"]:
                if prev_msg and prev_msg['action'] == 'OTHER':
                response = telegram_bot.send_message(
                    chat_id=TO_CHANNEL_ID,
                    text=message,
                    reply_id=to_reply_id,
                )
                print("response ", response)
                if response['ok'] and result['action'] == 'NEW_SIGNAL':
                    to_msg_id = response['result']['message_id']
                    dynamodb.update_item(
                        TableName="orders",
                        Key={"order_id": {"S": result["order_id"]}},
                        UpdateExpression="SET to_chat_id = :to_chat_id, to_msg_id = :to_msg_id",
                        ExpressionAttributeValues=json_util.dumps({
                            ":to_chat_id": TO_CHANNEL_ID,
                            ":to_msg_id": to_msg_id,
                        }, True)
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