import re
from typing import Dict, List, Optional

class WolfForexClassifier:
    """
    Robust classifier for Wolf Forex signals that handles:
    - Entry signals with multiple TPs
    - TP hit notifications in various formats
    - SL hit notifications in various formats
    """
    
    def __init__(self):
        # Entry pattern
        self.entry_pattern = re.compile(
            r'(?P<pair>[A-Z]{2,6}(?:[A-Z0-9]{2})?)\s*[📈📉↗↘]\s*(?P<side>BUY|SELL)\s*(?P<entry>\d+\.\d+)\s*'
            r'(.*?(?:TP|Take Profit)\s*(?P<tps>[\d\s\.]+).*?'
            r'(?:SL|Stop Loss)\s*(?P<sl>\d+\.\d+))',
            re.IGNORECASE | re.DOTALL
        )
        
        # TP hit detection patterns
        self.tp_keywords = ['TP', 'Take Profit', 'Profit Taken', '✅', '💚']
        
        # SL hit detection patterns
        self.sl_keywords = ['SL', 'Stop Loss', '✖', '❌', 'stopped out']

    def process_message(self, message_data: Dict) -> Optional[Dict]:
        msg_text = self._clean_message(message_data.get('msg_text', ''))
        reply_msg_id = message_data.get('reply_msg_id')
        
        # Process entry signal (no reply)
        if not reply_msg_id:
            if entry := self._extract_entry(msg_text):
                return {
                    **message_data,
                    **entry,
                    "action": "NEW_SIGNAL",
                    "type": "MARKET",
                    "order_id": f"{message_data['chat_id']}_{message_data['msg_id']}"
                }
        
        # Process TP/SL hits (replies to original signal)
        if reply_msg_id:
            if self._is_tp_message(msg_text):
                if tp := self._extract_tp(msg_text):
                    return {
                        **message_data,
                        **tp,
                        "action": "TP_HIT",
                        "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                    }
            
            if self._is_sl_message(msg_text):
                if sl := self._extract_sl(msg_text):
                    return {
                        **message_data,
                        **sl,
                        "action": "SL_HIT",
                        "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                    }
        
        return None

    def _extract_entry(self, message: str) -> Optional[Dict]:
        """Extract entry signal with TP array"""
        match = self.entry_pattern.search(message)
        if not match:
            return None
            
        # Extract all TP prices
        tps = re.findall(r'(?:💰TP|TP|Take Profit)\s*\d*\s*(\d+\.\d+)', message)
        return {
            "pair": match.group('pair'),
            "side": match.group('side'),
            "entry": float(match.group('entry')),
            "stop_loss": float(match.group('sl')),
            "take_profit": [float(tp) for tp in tps]  # Always array
        }

    def _is_tp_message(self, message: str) -> bool:
        """Check if message is a TP notification"""
        return any(keyword in message for keyword in self.tp_keywords)

    def _is_sl_message(self, message: str) -> bool:
        """Check if message is an SL notification"""
        return any(keyword in message for keyword in self.sl_keywords)

    def _extract_tp(self, message: str) -> Optional[Dict]:
        """Extract TP hit details"""
        # Get TP level (default to 1 if not specified)
        level_match = re.search(r'(?:TP|Take Profit)\s*(\d+)', message, re.IGNORECASE)
        tp_level = int(level_match.group(1)) if level_match else 1
        
        # Try to get exit price (optional)
        price_match = re.search(r'@\s*(\d+\.\d+)', message)
        exit_price = float(price_match.group(1)) if price_match else None
        
        return {
            "tp_level": tp_level,
            "exit_price": exit_price
        }

    def _extract_sl(self, message: str) -> Optional[Dict]:
        """Extract SL hit details"""
        # Try to get exit price (optional)
        price_match = re.search(r'@\s*(\d+\.\d+)', message)
        exit_price = float(price_match.group(1)) if price_match else None
        
        return {
            "exit_price": exit_price
        }

    def _clean_message(self, message: str) -> str:
        """Normalize message text"""
        return ' '.join(message.strip().split())

# Example Usage
if __name__ == "__main__":
    classifier = WolfForexClassifier()
    
    # Test Entry Signal
    entry_msg = {
        "chat_id": -100123456,
        "msg_id": 111,
        "msg_text": """
        XAUUSD 📈 BUY 3105.50

💰TP1 3107.50
💰TP2 3110.50
💰TP3 3115.50
🚫SL 3097.00

WOLFXSIGNALS.COM content
        """,
        "reply_msg_id": None
    }
    
    # Test TP Hit (multiple formats)
    tp_msgs = [
        {
            "chat_id": -100123456,
            "msg_id": 112,
            "msg_text": """💚💚💚💚💚💚💚💚💚💚💚💚

✅✅ GOLD Take Profit 1 ✅✅

📊 Profit Made: 20 PIPS🔥""",
            "reply_msg_id": 111
        },
        {
            "chat_id": -100123456,
            "msg_id": 113,
            "msg_text": "TP1 hit @ 3107.50",
            "reply_msg_id": 111
        },
        {
            "chat_id": -100123456,
            "msg_id": 114,
            "msg_text": "Take Profit 2 reached ✅",
            "reply_msg_id": 111
        }
    ]
    
    # Test SL Hit (multiple formats)
    sl_msgs = [
        {
            "chat_id": -100123456,
            "msg_id": 115,
            "msg_text": """Hit SL, sorry guys! -84 PIPS✖️""",
            "reply_msg_id": 111
        },
        {
            "chat_id": -100123456,
            "msg_id": 116,
            "msg_text": "Stop Loss triggered @ 3097.00",
            "reply_msg_id": 111
        },
        {
            "chat_id": -100123456,
            "msg_id": 117,
            "msg_text": "❌ SL hit ❌",
            "reply_msg_id": 111
        }
    ]
    
    print("=== Entry Signal ===")
    print(classifier.process_message(entry_msg))
    
    print("\n=== TP Hit Signals ===")
    for msg in tp_msgs:
        print(classifier.process_message(msg))
    
    print("\n=== SL Hit Signals ===")
    for msg in sl_msgs:
        print(classifier.process_message(msg))

    print(classifier.process_message({
        "chat_id": 123,
        "msg_id": 1,
        "msg_text": """#XAUUSD Gold Market Update – Key Structure Levels in Play

Gold continues to respect the current box range, consolidating between key support and resistance zones.

📊 Price action is forming a clear accumulation pattern between 3290–3360.
🔍 A breakout above 3360 would confirm bullish momentum, with potential continuation toward the 3490 zone.
🔻 On the other hand, if gold fails to break resistance and retraces below 3290 again, we may see a move back to 3250 and possibly the 3200 region.""",
    }))