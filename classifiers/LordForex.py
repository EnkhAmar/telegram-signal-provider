import re
from typing import Dict, Optional
from enum import Enum

class SignalAction(Enum):
    NEW_SIGNAL = "NEW_SIGNAL"
    TP_HIT = "TP_HIT"
    SL_HIT = "SL_HIT"
    CANCELLED = "CANCELLED"
    OTHER = "OTHER"

class LordForexClassifier:
    """
    Final corrected classifier for Lord Forex signals with:
    - Proper order ID handling ("lord" + original ID)
    - Accurate pattern matching for all message types
    """
    
    def __init__(self):
        # NEW ORDER pattern with flexible symbol matching
        self.new_order_pattern = re.compile(
            r'🔔\s*NEW\s+ORDER\s*-\s*(?P<pair>[A-Z]{2,6}(?:[A-Z0-9]{2,4})?)\s*-\s*(?P<side>Buy|Sell)\s*🔔\s*'
            r'Entry:\s*(?P<entry>\d+\.\d+)\s*'
            r'TP\s*@\s*(?P<tp>\d+\.\d+)\s*'
            r'SL\s*@\s*(?P<sl>\d+\.\d+)\s*'
            r'ID:\s*(?P<id>\d+)',
            re.IGNORECASE
        )
        
        # CLOSED trade pattern with ID capture
        self.closed_pattern = re.compile(
            r'📥\s*CLOSED\s*-\s*(?P<pair>[A-Z]{2,6}(?:[A-Z0-9]{2,4})?)\s*-\s*(?P<side>Buy|Sell)\s*📥\s*'
            r'Entry:\s*(?P<entry>\d+\.\d+)\s*'
            r'Exit:\s*(?P<exit>\d+\.\d+)\s*'
            r'Result:\s*(?P<result>[+-]?\d+\.\d+%)\s*'
            r'ID:\s*(?P<id>\d+)',
            re.IGNORECASE
        )
        
        # CANCELLED order pattern
        self.cancelled_pattern = re.compile(
            r'❌\s*ORDER\s+CANCELLED\s*❌|'
            r'🚫\s*POSITION\s+CLOSED\s+MANUALLY',
            re.IGNORECASE
        )

    def process_message(self, message_data: Dict) -> Dict:
        """
        Process message and return standardized signal with:
        - Proper "lord{id}" order IDs
        - Correct action types
        """
        msg_text = self._clean_message(message_data.get('msg_text', ''))
        
        # Process NEW ORDER messages
        if new_order := self._process_new_order(msg_text):
            return {
                **message_data,
                **new_order,
                "action": SignalAction.NEW_SIGNAL.value,
                "type": "MARKET",
                "order_id": f"lord{new_order['order_id']}"  # Add prefix here
            }
        
        # Process CLOSED trades (TP/SL)
        if closed_trade := self._process_closed_trade(msg_text):
            result = closed_trade['result']
            is_profit = not result.startswith('-')
            action = SignalAction.TP_HIT.value if is_profit else SignalAction.SL_HIT.value
            
            return {
                **message_data,
                **closed_trade,
                "action": action,
                "order_id": f"lord{closed_trade['order_id']}"  # Add prefix here
            }
        
        # Process CANCELLED orders
        if self.cancelled_pattern.search(msg_text):
            return {
                **message_data,
                "action": SignalAction.CANCELLED.value,
                "message": msg_text
            }
        
        # Default for unrecognized messages
        return {
            **message_data,
            "action": SignalAction.OTHER.value,
            "message": msg_text
        }

    def _process_new_order(self, message: str) -> Optional[Dict]:
        """Process NEW ORDER messages with ID extraction"""
        if match := self.new_order_pattern.search(message):
            return {
                "pair": match.group('pair').upper(),
                "side": match.group('side').upper(),
                "entry": float(match.group('entry')),
                "stop_loss": float(match.group('sl')),
                "take_profit": [float(match.group('tp'))],
                "order_id": match.group('id')  # Raw ID (will be prefixed later)
            }
        return None

    def _process_closed_trade(self, message: str) -> Optional[Dict]:
        """Process CLOSED trade messages with ID extraction"""
        if match := self.closed_pattern.search(message):
            return {
                "pair": match.group('pair').upper(),
                "side": match.group('side').upper(),
                "entry_price": float(match.group('entry')),
                "exit_price": float(match.group('exit')),
                "result": match.group('result'),
                "is_profit": not match.group('result').startswith('-'),
                "order_id": match.group('id')  # Raw ID (will be prefixed later)
            }
        return None

    def _clean_message(self, message: str) -> str:
        """Normalize message text"""
        return ' '.join(message.strip().split())

# Example Usage
if __name__ == "__main__":
    classifier = LordForexClassifier()
    
    test_cases = [
        {
            "chat_id": -100123,
            "msg_id": 101,
            "msg_text": "🔔 NEW ORDER - NAS100 - Sell 🔔\nEntry: 183.542\nTP @ 182.900\nSL @ 184.250\nID: 987654321"
        },
        {
            "chat_id": -100123,
            "msg_id": 102,
            "msg_text": "📥 CLOSED - US100 - Sell 📥\nEntry: 183.542\nExit: 182.900\nResult: 3.50%\nID: 987654321"
        },
        {
            "chat_id": -100123,
            "msg_id": 103,
            "msg_text": "📥 CLOSED - GBPUSD - Buy 📥\nEntry: 1.30977\nExit: 1.30032\nResult: -1.41%\nID: 982142569"
        },
        {
            "chat_id": -100123,
            "msg_id": 104,
            "msg_text": "❌ ORDER CANCELLED ❌"
        }
    ]
    
    for case in test_cases:
        print("\n" + "="*50)
        print("Input Message:")
        print(case["msg_text"])
        result = classifier.process_message(case)
        print("\nOutput:")
        print(f"Action: {result['action']}")
        print(f"Result: {result}")
        if result['action'] != SignalAction.OTHER.value:
            print(f"Order ID: {result.get('order_id', 'N/A')}")
            print(f"Details: { {k:v for k,v in result.items() if k not in ['action', 'msg_text', 'chat_id', 'msg_id', 'order_id']} }")