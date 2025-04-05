import boto3
from os import getenv
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
AWS_ACCESS_KEY = getenv("MY_AWS_ACCESS_KEY")
AWS_SECRET_KEY = getenv("MY_AWS_SECRET_KEY")
AWS_REGION = getenv("MY_AWS_REGION")
TG_SIGNAL_BOT_TOKEN = getenv("TG_SIGNAL_BOT_TOKEN")
TO_CHANNEL_ID = getenv("TO_CHANNEL_ID")

dynamodb = boto3.client('dynamodb', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)
telegram_bot = Bot(token=TG_SIGNAL_BOT_TOKEN)
sqs_client = boto3.client("sqs", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)

SELL = 'SELL|sell|SHORT|short'
BUY = 'BUY|buy|LONG|long'
ORDER_TYPE = 'LIMIT|limit|now|NOW|market|MARKET'
EDIT = 'EDIT|UPDATE|MOVE TO|MOVE|EDITING|MOVING|MOVING TO|edit|editing|move|moving|PUT|put'
CLOSE = 'CLOSE|close|CLOSING|closing|TAKE HALF PROFIT|TAKE PROFIT'
DELETE = 'DELETE|DELETING|delete|deleting'
STOP_LOSS = 'sl|SL|stop loss|STOP LOSS'
TAKE_PROFIT = 'tp|TP|take profit|TAKE PROFIT'

ORDER_TYPE_BUY = 'ORDER_TYPE_BUY'
ORDER_TYPE_SELL = 'ORDER_TYPE_SELL'
ORDER_TYPE_BUY_LIMIT = 'ORDER_TYPE_BUY_LIMIT'
ORDER_TYPE_SELL_LIMIT = 'ORDER_TYPE_SELL_LIMIT'

DB_TABLE_STATUSES = 'statuses'
DB_TABLE_ORDERS = 'orders'

class MsgType:
    DEFAULT = 'DEFAULT'
    ORDER = 'ORDER'
    EDIT = 'EDIT'
    CLOSE = 'CLOSE'
    CANCEL = 'CANCEL'

class Status:
    PLACED = 1
    ACTIVE = 2
    CLOSED_BY_BOT = 3
    CLOSED_BY_TP = 4
    CLOSED_BY_SL = 5
    CLOSED_BY_USER = 6
    DELETED_BY_BOT = 7
    DELETED_BY_USER = 8 

class Regex:
    INT_OR_FLOAT = '(\d+\.?\d+)'

    def __init__(self, pair, order, entry, stop_loss, take_profit, order_type, close_pair, edit_pair, edit_order, edit_position, delete_pair):
        self._pair = pair
        self._order = order
        self._order_type = order_type
        self._entry = entry
        self._stop_loss = stop_loss
        self._take_profit = take_profit
        self._close_pair = close_pair
        self._edit_pair = edit_pair
        self._edit_order = edit_order
        self._edit_position = edit_position
        self._delete_pair = delete_pair

    @property
    def pair_pattern(self) -> str:
        return self._pair['pattern']
    
    @property
    def pair_group(self) -> int:
        return int(self._pair['group'])

    @property
    def order_pattern(self) -> str:
        return self._order['pattern']

    @property
    def order_group(self) -> int:
        return int(self._order['group'])

    @property
    def order_type_pattern(self) -> str:
        return self._order_type['pattern']

    @property
    def order_type_group(self) -> int:
        return int(self._order_type['group'])

    @property
    def entry_pattern(self) -> str:
        return self._entry['pattern']
    
    @property
    def entry_group(self) -> int:
        return int(self._entry['group'])

    @property
    def sl_pattern(self) -> str:
        return self._stop_loss['pattern']

    @property
    def sl_group(self) -> int:
        return int(self._stop_loss['group'])

    @property
    def tp_pattern(self) -> str:
        return self._take_profit['pattern']

    @property
    def tp_group(self) -> int:
        return int(self._take_profit['group'])

    @property
    def close_pair_pattern(self) -> str:
        return self._close_pair['pattern']

    @property
    def close_pair_group(self) -> int:
        return self._close_pair['group']

    @property
    def edit_pair_pattern(self) -> str:
        return self._edit_pair['pattern']

    @property
    def edit_pair_group(self) -> int:
        return self._edit_pair['group']

    @property
    def edit_order_pattern(self) -> str:
        return self._edit_order['pattern']

    @property
    def edit_order_group(self) -> int:
        return self._edit_order['group']

    @property
    def edit_position_pattern(self) -> str:
        return self._edit_position['pattern']

    @property
    def edit_position_group(self) -> int:
        return self._edit_position['group']

    @property
    def delete_pair_pattern(self) -> str:
        return self._delete_pair['pattern']

    @property
    def delete_pair_group(self) -> int:
        return self._delete_pair['group']

CHANNELS = [
    {
        'id': 1830404615,
        'name': 'MetaBear',
        'link': 'https://t.me/+jg4d5Up8Fkg2YjJl',
        'regex': {
            'pair': {
                'pattern': f"^🔥🐻(.+?)\s+({SELL}|{BUY})\s*(.+?|)🐻🔥\n",
                'group': 1,
            },
            'order': {
                'pattern': f"^🔥🐻(.+?)\s+({SELL}|{BUY})\s*(.+?|)🐻🔥\n",
                'group': 2,
            },
            'order_type': {
                'pattern': f"^🔥🐻(.+?)\s+({SELL}|{BUY})\s*(.+?|)🐻🔥\n",
                'group': 3,
            },
            'entry': {
                'pattern': f"🔰ENTRY:\s+({Regex.INT_OR_FLOAT})\n",
                'group': 1,
            },
            'sl': {
                'pattern': f"SL:\s+({Regex.INT_OR_FLOAT})\n",
                'group': 1,
            },
            'tp': {
                'pattern': f"TP:\s+({Regex.INT_OR_FLOAT})\n",
                'group': 1,
            },
            'close_pair': {
                'pattern': f'🔵🤑([A-Z|a-z]+)\s+([A-Z]{4,6})\s+(.+?\d+\.?\d+) PIPS!',
                'group': 2,
            },
            'edit_pair': {
                'pattern': str(None),
                'group': 0,
            },
            'edit_order': {
                'pattern': f'✅(PUT)\s+(SL|TP)\s+IN:\s+({Regex.INT_OR_FLOAT})',
                'group': 2,
            },
            'edit_position': {
                'pattern': f'✅(PUT)\s+(SL|TP)\s+IN:\s+({Regex.INT_OR_FLOAT})',
                'group': 3,
            },
            'delete_pair': {
                'pattern': str(None),
                'group': 0,
            }
        }
    },
    {
        'id': 1602291705,
        'name': 'WFX',
        'link': 'https://t.me/wfxtestt',
        'regex': {
            'pair': {
                'pattern': f'^([A-Z|a-z]{{4,6}})\s({SELL}|{BUY})\s({ORDER_TYPE}|)\s(@|)(\s|)(\d+\.?\d+)\n',
                'group': 1,
            },
            'order': {
                'pattern': f'^([A-Z|a-z]{{4,6}})\s({SELL}|{BUY})\s({ORDER_TYPE}|)\s(@|)(\s|)(\d+\.?\d+)\n',
                'group': 2,
            },
            'order_type': {
                'pattern': f'^([A-Z|a-z]{{4,6}})\s({SELL}|{BUY})\s({ORDER_TYPE}|)\s(@|)(\s|)(\d+\.?\d+)\n',
                'group': 3,
            },
            'entry': {
                'pattern': f'^([A-Z|a-z]{{4,6}})\s({SELL}|{BUY})\s({ORDER_TYPE}|)\s(@|)(\s|)(\d+\.?\d+)\n',
                'group': 6,
            },
            'sl': {
                'pattern': f'(sl|SL|Sl)(\s+(@|)(\s|))(\d+\.?\d+)',
                'group': 5,
            },
            'tp': {
                'pattern': f'(tp|TP|Tp)(\s+(@|)(\s|))(\d+\.?\d+)',
                'group': 5,
            },
            'close_pair': {
                'pattern': f'([A-Z]{{4,6}})',
                'group': 1,
            },
            'edit_pair': {
                'pattern': f'([A-Z]{{4,6}})\s+({STOP_LOSS}|{TAKE_PROFIT})\s+({EDIT})\s+(\d+\.?\d+)',
                'group': 1,
            },
            'edit_order': {
                'pattern': f'([A-Z]{{4,6}})\s+({STOP_LOSS}|{TAKE_PROFIT})\s+({EDIT})\s+(\d+\.?\d+)',
                'group': 2,
            },
            'edit_position': {
                'pattern': f'([A-Z]{{4,6}})\s+({STOP_LOSS}|{TAKE_PROFIT})\s+({EDIT})\s+(\d+\.?\d+)',
                'group': 4,
            },
            'delete_pair': {
                'pattern': f'',
                'group': 0,
            }
        }
    },
]
