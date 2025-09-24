import json
from dynamodb_json import json_util
from extension import dynamodb
from extension import apigw_client, API_DOMAIN, API_STAGE
import boto3
import json
import os


def handler(event, context):
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    connection_id = event['requestContext']['connectionId']

    apigw = boto3.client('apigatewaymanagementapi',
                         endpoint_url=f"https://{domain}/{stage}")

    body = json.loads(event['body'])
    message = body.get('message', 'Hello!')

    # Echo the message back to the client
    apigw_client.post_to_connection(ConnectionId=connection_id,
                              Data=json.dumps({'echo': message}).encode('utf-8'))

    return {'statusCode': 200}


def connect_handler(event, context):
    token = event['queryStringParameters'].get('token')
    channel_id = event['queryStringParameters'].get('channel_id')
    if token != 'TOKEN':
        return {'statusCode': 403, 'body': 'Unauthorized'}
    
    connection_id = event['requestContext']['connectionId']
    
    dynamodb.put_item(
        TableName="websocket_connections",
        Item=json_util.dumps({
            "connection_id": connection_id,
            "status": 1,
            "channel_id": channel_id,
            "connected_at": event['requestContext']['requestTimeEpoch']
        }, True)
    )
    
    return {
        "statusCode": 200,
        "body": "Connected."
    }


def disconnect_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    dynamodb.delete_item(
        TableName="websocket_connections",
        Key=json_util.dumps({"connection_id": connection_id}, True)
    )
    
    return {
        "statusCode": 200,
        "body": "Disconnected."
    }


def send_message_to_all_connections(message):
    connections = json_util.loads(dynamodb.query(
        TableName="websocket_connections",
        IndexName="status-connected_at-index",
        KeyConditionExpression="#status = :status",
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues=json_util.dumps({
            ":status": 1,
        }, True),
        ProjectionExpression="connection_id"
    ).get('Items', []), True)
    
    for connection in connections:
        connection_id = connection['connection_id']
        try:
            apigw_client.post_to_connection(ConnectionId=connection_id,
                                      Data=json.dumps({'message': message}).encode('utf-8'))
        except Exception as e:
            print(f"Failed to send message to {connection_id}: {e}")


def send_message_to_connections(channel_id, message):
    connections = json_util.loads(dynamodb.query(
        TableName="websocket_connections",
        IndexName="status-connected_at-index",
        KeyConditionExpression="#status = :status",
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues=json_util.dumps({
            ":status": 1,
        }, True),
        ProjectionExpression="connection_id, channel_id"
    ).get('Items', []), True)

    for connection in connections:
        if connection['channel_id'] == channel_id:
            connection_id = connection['connection_id']
            try:
                apigw_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps({'message': message}).encode('utf-8'))
            except Exception as e:
                print(f"Failed to send message to {connection_id}: {e}")


def broadcast_message(event, context):
    body = event['body']
    message = body.get('message', 'Hello, everyone!')
    print("broadcast message", message)
    print("broadcast message type", type(message))

    channel_id = message.get('chat_id')
    if channel_id:
        send_message_to_connections(str(channel_id), message)
    else:
        send_message_to_all_connections(message)
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Message broadcasted to all connections."})
    }


def message_handler(event, context):
    connection_id = event['requestContext']['connectionId']

    try:
        body = json.loads(event.get('body', '{}'))
        msg = body.get('message', 'No message sent')
    except Exception as e:
        msg = 'Invalid JSON'

    try:
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"echo": msg}).encode('utf-8')
        )
    except apigw_client.exceptions.GoneException:
        dynamodb.delete_item(TableName="websocket_connections", Key=json_util.dumps({'connectionId': connection_id}, True))

    return {'statusCode': 200}


def ping_handler(event, context):
    connection_id = event['requestContext']['connectionId']

    # Optionally send back a pong
    try:
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"pong": True}).encode('utf-8')
        )
    except apigw_client.exceptions.GoneException:
        dynamodb.delete_item(TableName="websocket_connections" ,Key={'connectionId': connection_id})

    return {'statusCode': 200}