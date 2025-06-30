import json
from dynamodb_json import json_util
from extension import dynamodb
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
    apigw.post_to_connection(ConnectionId=connection_id,
                              Data=json.dumps({'echo': message}).encode('utf-8'))

    return {'statusCode': 200}


def connect_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    dynamodb.put_item(
        TableName="websocket_connections",
        Item=json_util.dumps({
            "connection_id": connection_id,
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
    connections = dynamodb.scan(
        TableName="websocket_connections",
        ProjectionExpression="connection_id"
    ).get('Items', [])
    
    apigw = boto3.client('apigatewaymanagementapi',
                         endpoint_url=f"https://{os.environ['API_DOMAIN']}/{os.environ['API_STAGE']}")
    
    for connection in connections:
        connection_id = connection['connection_id']
        try:
            apigw.post_to_connection(ConnectionId=connection_id,
                                      Data=json.dumps({'message': message}).encode('utf-8'))
        except Exception as e:
            print(f"Failed to send message to {connection_id}: {e}")

def broadcast_message(event, context):
    body = json.loads(event['body'])
    message = body.get('message', 'Hello, everyone!')
    
    send_message_to_all_connections(message)
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Message broadcasted to all connections."})
    }   