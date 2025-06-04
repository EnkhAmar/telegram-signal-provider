import re
from typing import Dict, List, Optional

class RussianForexClassifier:
    """
    Classifier for Russian Forex signals that handles:
    - Entry signals with BuyStop/SellStop/BuyLimit/SellLimit orders
    - TP hit notifications in various Russian formats
    - SL hit notifications in Russian
    - Order cancellations
    """
    
    def __init__(self):
        # Entry pattern for various order types
        self.entry_pattern = re.compile(
            r'(?P<order_type>BuyStop|SellStop|BuyLimit|SellLimit)\s*'
            r'#(?P<pair>[A-Z]{6})\s*\((?P<timeframe>[a-z0-9]+)\)\s*.*?\n'
            r'Price:\s*(?P<entry>\d+\.\d+)\n'
            r'SL:\s*(?P<sl>\d+\.\d+)\n'
            r'TP:\s*(?P<tp>\d+\.\d+)',
            re.IGNORECASE
        )
        
        # TP hit detection patterns (Russian)
        self.tp_keywords = [
            'фикс', 'бу', 'безубыток', 'TakeProfit', 
            'пункта', 'пунктов', '✅', '🔥'
        ]
        
        # SL hit detection patterns (Russian)
        self.sl_keywords = ['SL', '❌', 'пункта', 'пунктов']
        
        # Cancellation patterns
        self.cancel_keywords = ['Delete', 'Отмена', 'Слом']
        self.cancel_pattern = re.compile(r'(Delete|Отмена)\s*❌')

    def process_message(self, message_data: Dict) -> Optional[Dict]:
        msg_text = self._clean_message(message_data.get('msg_text', ''))
        reply_msg_id = message_data.get('reply_msg_id')
        
        # Process entry signal (no reply)
        if not reply_msg_id:
            if entry := self._extract_entry(msg_text):
                order_type = entry['order_type'].upper()
                return {
                    **message_data,
                    **entry,
                    "action": "NEW_SIGNAL",
                    "type": self._normalize_order_type(order_type),
                    "side": "BUY" if order_type.startswith('BUY') else "SELL",
                    "order_id": f"{message_data['chat_id']}_{message_data['msg_id']}"
                }
        
        # Process TP/SL/Cancel hits (replies to original signal)
        if reply_msg_id:
            if self._is_cancel_message(msg_text):
                return {
                    **message_data,
                    "action": "CANCELLED",
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                }
            elif self._is_tp_message(msg_text):
                if tp := self._extract_tp(msg_text):
                    return {
                        **message_data,
                        **tp,
                        "action": "TP_HIT",
                        "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                    }
            elif self._is_sl_message(msg_text):
                if sl := self._extract_sl(msg_text):
                    return {
                        **message_data,
                        **sl,
                        "action": "SL_HIT",
                        "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                    }
        
        return None

    def _normalize_order_type(self, order_type: str) -> str:
        """Convert order type to standardized format"""
        order_type = order_type.upper()
        if order_type == "BUYSTOP":
            return "BUY_STOP"
        elif order_type == "SELLSTOP":
            return "SELL_STOP"
        elif order_type == "BUYLIMIT":
            return "BUY_LIMIT"
        elif order_type == "SELLLIMIT":
            return "SELL_LIMIT"
        return order_type

    def _extract_entry(self, message: str) -> Optional[Dict]:
        """Extract entry signal with order type, price, SL and TP"""
        # Normalize line endings and clean the message
        message = self._clean_message(message.replace('\r\n', '\n'))
        
        # More flexible pattern to handle variations in the format
        pattern = re.compile(
            r'(?P<order_type>BuyStop|SellStop|BuyLimit|SellLimit)\s*'
            r'#(?P<pair>[A-Z]{6})\s*\((?P<timeframe>[a-z0-9]+)\)[^\n]*\n'
            r'(?:.*\n)?.*Price:\s*(?P<entry>\d+\.\d+)\s*\n'
            r'.*SL:\s*(?P<sl>\d+\.\d+)\s*\n'
            r'.*TP:\s*(?P<tp>\d+\.\d+)',
            re.IGNORECASE
        )
        
        match = pattern.search(message)
        if not match:
            return None
            
        return {
            "pair": match.group('pair'),
            "order_type": match.group('order_type'),
            "entry": float(match.group('entry')),
            "stop_loss": float(match.group('sl')),
            "take_profit": [float(match.group('tp'))],
            "timeframe": match.group('timeframe')
        }

    def _is_tp_message(self, message: str) -> bool:
        """Check if message is a TP notification (Russian)"""
        message_lower = message.lower()
        
        # Explicitly exclude these status messages
        excluded_phrases = [
            'если пропустили уведомление',
            'в работе',
            'переведите в бу'  # Without TP hit context
        ]
        
        if any(phrase in message_lower for phrase in excluded_phrases):
            return False
            
        # Positive indicators
        tp_indicators = [
            'фикс', 
            'take profit',
            'пункта', 
            'пунктов', 
            '✅', 
            '🔥',
            # Only count "бу" when combined with profit indicators
            ('бу', 'пункт')  # Both words must be present
        ]
        
        # Check for positive indicators
        has_tp_indicator = False
        for indicator in tp_indicators:
            if isinstance(indicator, tuple):
                # All parts of tuple must be present
                if all(part in message_lower for part in indicator):
                    has_tp_indicator = True
                    break
            elif indicator in message_lower:
                has_tp_indicator = True
                break
                
        return (
            has_tp_indicator
            and '❌' not in message_lower  # avoid classifying SL or cancel as TP
            and not self._is_cancel_message(message)
        )

    def _is_sl_message(self, message: str) -> bool:
        """Check if message is an SL notification (Russian)"""
        message_lower = message.lower()
        return (
            '❌' in message_lower
            and any(kw in message_lower for kw in self.sl_keywords)
            and not self._is_cancel_message(message)
            and not self._is_tp_message(message)  # ensure not a TP
        )

    def _is_cancel_message(self, message: str) -> bool:
        """Check if message is an order cancellation"""
        return self.cancel_pattern.search(message) is not None

    def _extract_tp(self, message: str) -> Optional[Dict]:
        """Extract TP hit details from Russian messages"""
        # Extract pips (пунктов)
        pips_match = re.search(r'([+-]?\d+)\s*пункт[аов]*', message)
        pips = int(pips_match.group(1)) if pips_match else None
        
        # Determine if partial TP or full TP
        is_partial = 'фикс' in message.lower() or 'часть' in message.lower()
        
        return {
            "pips": pips,
            "is_partial": is_partial,
            "is_breakeven": any(word in message.lower() for word in ['бу', 'безубыток'])
        }

    def _extract_sl(self, message: str) -> Optional[Dict]:
        """Extract SL hit details from Russian messages"""
        # Extract pips (пунктов)
        pips_match = re.search(r'([+-]?\d+)\s*пункт[аов]*', message)
        pips = int(pips_match.group(1)) if pips_match else None
        
        return {
            "pips": pips
        }

    def _clean_message(self, message: str) -> str:
        # Keep line breaks, clean extra spaces
        return '\n'.join(' '.join(line.strip().split()) for line in message.strip().split('\n'))


# Example Usage
if __name__ == "__main__":
    classifier = RussianForexClassifier()
    
    # Test Entry Signals
    entry_msgs = [
        {
            "chat_id": -1000,
            "msg_id": 1,
            "msg_text": """BuyStop #GBPUSD (D1) ПГиП
Price: 1.36099
SL: 1.34239
TP: 1.39459
(FX)""",
            "reply_msg_id": None,
        },
        {
            "chat_id": -1000,
            "msg_id": 2,
            "msg_text": """SellStop #AUDJPY (D1) ГиП
Price: 91.851
SL: 93.233
TP: 88.947
(FX)""",
            "reply_msg_id": None,
        },
        {
            "chat_id": -1000,
            "msg_id": 3,
            "msg_text": """BuyLimit #EURNZD (h1) ПГиП
Price: 1.90778
SL: 1.89800
TP: 1.93333
(FX)""",
            "reply_msg_id": None,
        }
    ]
    
    # Test TP Hit Signals
    tp_msgs = [
        {
            "chat_id": -1000,
            "msg_id": 4,
            "msg_text": """Часть сделки фикс, остаток в бу ✅🔥 +34 пункта""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 5,
            "msg_text": """Перевожу в безубыток ✅🔥
+17 пунктов""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 6,
            "msg_text": """TakeProfit ✅🔥
+156 пунктов""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 6,
            "msg_text": """Если пропустили уведомление 📣 
Переведите в бу ✅""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 6,
            "msg_text": """В работе ✅""",
            "reply_msg_id": 1,
        },
    ]
    
    # Test SL Hit Signals
    sl_msgs = [
        {
            "chat_id": -1000,
            "msg_id": 7,
            "msg_text": """SL ❌
-32 пункта""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 8,
            "msg_text": """SL ❌
-105 пунктов""",
            "reply_msg_id": 1,
        }
    ]
    
    # Test Cancel Signals
    cancel_msgs = [
        {
            "chat_id": -1000,
            "msg_id": 9,
            "msg_text": """Delete ❌
(Отмена)""",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 10,
            "msg_text": """Отмена ❌""",
            "reply_msg_id": 1,
        }
    ]
    
    print("=== Entry Signals ===")
    for msg in entry_msgs:
        result = classifier.process_message(msg)
        print(result)
    
    print("\n=== TP Hit Signals ===")
    for msg in tp_msgs:
        print(classifier.process_message(msg))
    
    print("\n=== SL Hit Signals ===")
    for msg in sl_msgs:
        print(classifier.process_message(msg))
    
    print("\n=== Cancel Signals ===")
    for msg in cancel_msgs:
        print(classifier.process_message(msg))