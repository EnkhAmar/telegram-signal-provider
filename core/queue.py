import json
from dynamodb_json import json_util
import traceback
from classifiers import ForexSignalProcessor
from extension import dynamodb, TO_CHANNEL_FOREX, TO_CHANNEL_CRYPTO, Telegram, TG_SIGNAL_BOT_TOKEN, lambda_client
import utils

processor = ForexSignalProcessor()
telegram_bot = Telegram(token=TG_SIGNAL_BOT_TOKEN)


def handler(event, context):
    print("---RECORDS---\n", event['Records'])
    for record in event['Records']:
        message_body = record['body']
        
        try:
            message = json.loads(message_body)
            
            chat_id = message['chat_id']
            msg_id = message['msg_id']
            msg_date = message['msg_date']
            msg_text = message.get('msg_text', "")
            reply_msg_id = message['reply_msg_id']
            msg_type = message.get("msg_type", "NEW")
            signal_type = message['signal_type']
            TO_CHANNEL_ID = TO_CHANNEL_FOREX if signal_type == "forex" else TO_CHANNEL_CRYPTO
            if chat_id in [-1002643902459, -1002587201256]:
                TO_CHANNEL_ID = -1002665107295
                
            prev_msg = None

            result = processor.process_message(message)
            print("RAW MSG -- \n", message, "\n")
            print("RESULT -- \n", result, "\n")

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
                        "result": result,
                    }, True)
                )
            elif msg_type == "EDITED":
                prev_msg = json_util.loads(dynamodb.get_item(
                    TableName="telegram_msgs",
                    Key=json_util.dumps({"chat_id": chat_id, "msg_id": msg_id}, True),
                ).get("Item", None), True)
                print("prev_msg : ", prev_msg)

                dynamodb.update_item(
                    TableName="telegram_msgs",
                    Key=json_util.dumps({"chat_id": chat_id, "msg_id": msg_id}, True),
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
            elif msg_type == "DELETED":
                prev_msg = json_util.loads(dynamodb.get_item(
                    TableName="telegram_msgs",
                    Key=json_util.dumps({"chat_id": chat_id, "msg_id": msg_id}, True),
                ).get("Item", None), True)
                print("prev_msg to delete : ", prev_msg)
                # if prev_msg:
                #     prev_order = json_util.loads(dynamodb.get_item(
                #         TableName="orders",
                #         Key=json_util.dumps({
                #             "order_id": prev_msg['result']['order_id']
                #         }, True)
                #     ).get("Item", None), True)
                #     delete_resp = telegram_bot.delete_message(prev_order["to_chat_id"], prev_order["to_msg_id"])
                #     print("delete_resp ", delete_resp)
                return

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
                        "extracted": result,
                    }, True)
                )
                message = telegram_bot.make_entry_message(result)
            elif result['action'] in ['TP_HIT', 'SL_HIT', 'CANCELLED', 'IN_PROFIT_UPDATE']:
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
                if result['action'] == 'TP_HIT':
                    message = telegram_bot.make_tp_message(result)
                elif result['action'] == 'SL_HIT':
                    message = telegram_bot.make_sl_message(result)
                elif result['action'] == 'CANCELLED':
                    message = telegram_bot.make_cancel_message(result)
                elif result['action'] == 'IN_PROFIT_UPDATE':
                    message = telegram_bot.make_in_profit_update_message(result)

            should_send = False
            if result['action'] == "NEW_SIGNAL":
                should_send = True
            elif result['action'] in ["TP_HIT", "SL_HIT"]:
                if prev_msg and prev_msg['action'] in ["TP_HIT", "SL_HIT"]:
                    should_send = False
                else:
                    # No previous message, safe to send
                    should_send = True
            elif result['action'] in ["CANCELLED", "IN_PROFIT_UPDATE"]:
                should_send = True

            if should_send:
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

            if chat_id in [-1002587201256, -1001338521686] and result['action'] == 'NEW_SIGNAL':
                lambda_client.invoke(
                    # FunctionName="tg-signal-service-prod-BinanceTradeHandler",
                    FunctionName="binance-trade-handler",
                    InvocationType="Event",
                    Payload=json.dumps(result).encode("utf-8"),
                )
            if chat_id in [] and result['action'] == 'NEW_SIGNAL':
                lambda_client.invoke(
                    FunctionName='tg-signal-service-prod-broadcastMessageHandler',
                    InvocationType='Event',
                    Payload=json.dumps({'body': {'message': result}}).encode("utf-8")
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
    for record in event['Records']:
        message_body = record['body']
        print("Dead message body : ", message_body)