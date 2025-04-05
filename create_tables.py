from extension import dynamodb

# signal_channels
response = dynamodb.create_table(
    TableName="signal_channels",
    AttributeDefinitions=[
        {
            'AttributeName': 'chat_id',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'signal_type',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'name',
            'AttributeType': 'S'
        },
    ],
    KeySchema=[
        {
            'AttributeName': 'chat_id',
            'KeyType': 'HASH'
        },
    ],
    GlobalSecondaryIndexes=[
        {
            'IndexName': 'signal_type-name-index',
            'KeySchema': [
                {
                    'AttributeName': 'signal_type',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'name',
                    'KeyType': 'RANGE'
                },
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
        },
    ],
    BillingMode='PAY_PER_REQUEST',
    Tags=[
        {
            'Key': 'Description',
            'Value': 'signal_channels chat_id signal_type name'
        },
    ],
    TableClass='STANDARD',
    DeletionProtectionEnabled=False
)


# telegram_msgs
response = dynamodb.create_table(
    TableName="telegram_msgs",
    AttributeDefinitions=[
        {
            'AttributeName': 'chat_id',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'msg_id',
            'AttributeType': 'N'
        },
    ],
    KeySchema=[
        {
            'AttributeName': 'chat_id',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'msg_id',
            'KeyType': 'RANGE'
        }
    ],
    BillingMode='PAY_PER_REQUEST',
    Tags=[
        {
            'Key': 'Description',
            'Value': 'telegram_msgs chat_id msg_id reply_msg_id text action' # action= NEW_SIGNAL | TP_HIT | SL_HIT | CANCELLED | OTHER 
        },
    ],
    TableClass='STANDARD',
    DeletionProtectionEnabled=False
)


# orders
response = dynamodb.create_table(
    TableName="orders",
    AttributeDefinitions=[
        {
            'AttributeName': 'order_id', # chat_id _ msg_id
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'status', # PENDING, ACTIVATED, TP_HIT, SL_HIT, CANCELLED
            'AttributeType': 'S'
        },
        # {
        #     'AttributeName': 'side', # BUY, SELL
        #     'AttributeType': 'S'
        # },
        # {
        #     'AttributeName': 'type', # LIMIT, MARKET
        #     'AttributeType': 'S'
        # },
        # {
        #     'AttributeName': 'created_at',
        #     'AttributeType': 'S'
        # },
        {
            'AttributeName': 'chat_id',
            'AttributeType': 'N',
        }
    ],
    KeySchema=[
        {
            'AttributeName': 'order_id',
            'KeyType': 'HASH'
        },
    ],
    GlobalSecondaryIndexes=[
        {
            'IndexName': 'chat_id-status-index',
            'KeySchema': [
                {
                    'AttributeName': 'chat_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'status',
                    'KeyType': 'RANGE'
                },
            ],
            'Projection': {
                'ProjectionType': 'ALL',
            },
        },
    ],
    BillingMode='PAY_PER_REQUEST',
    Tags=[
        {
            'Key': 'Description',
            'Value': 'orders order_id status pair side type entry stop_loss take_profit pnl created_at updated_at'
        },
    ],
    TableClass='STANDARD',
    DeletionProtectionEnabled=False
)