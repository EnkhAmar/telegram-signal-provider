import re
from typing import Dict, List, Optional

class RussianForexClassifier:
    def __init__(self):
        self.cancel_pattern = re.compile(r'(Delete|Отмена)\s*❌', re.IGNORECASE)

    def process_message(self, message_data: Dict) -> Optional[Dict]:
        msg_text = self._clean_message(message_data.get('msg_text', ''))
        reply_msg_id = message_data.get('reply_msg_id')

        if not reply_msg_id:
            if entry := self._extract_entry(msg_text):
                order_type = entry['order_type'].upper()
                return {
                    **message_data,
                    **entry,
                    "action": "NEW_SIGNAL",
                    "type": self._normalize_order_type(order_type),
                    "side": "BUY" if order_type.startswith("BUY") else "SELL",
                    "order_id": f"{message_data['chat_id']}_{message_data['msg_id']}"
                }

        if reply_msg_id:
            if self._is_cancel_message(msg_text):
                return {
                    **message_data,
                    "action": "CANCELLED",
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                }
            elif self._is_tp_message(msg_text):
                return {
                    **message_data,
                    "action": "TP_HIT",
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                }
            elif self._is_sl_message(msg_text):
                return {
                    **message_data,
                    "action": "SL_HIT",
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                }
            elif self._is_in_profit_update(msg_text):
                pips = self._extract_pips(msg_text)
                return {
                    **message_data,
                    "action": "IN_PROFIT_UPDATE",
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}",
                    "pips": pips
                }

        return None

    def _normalize_order_type(self, order_type: str) -> str:
        return {
            "BUYSTOP": "BUY_STOP",
            "SELLSTOP": "SELL_STOP",
            "BUYLIMIT": "BUY_LIMIT",
            "SELLLIMIT": "SELL_LIMIT"
        }.get(order_type.upper(), order_type)

    def _extract_entry(self, message: str) -> Optional[Dict]:
        pattern = re.compile(
            r'(?P<order_type>BuyStop|SellStop|BuyLimit|SellLimit)\s*'
            r'#(?P<pair>[A-Za-z]+\d*)\s*\((?P<timeframe>[a-z0-9]+)\)[^\n]*\n'
            r'(?:.*\n)?.*Price:\s*(?P<entry>[\d,.]+)\s*\n'
            r'.*SL:\s*(?P<sl>[\d,.]+)\s*\n'
            r'.*TP:\s*(?P<tp>[\d,.]+)',
            re.IGNORECASE
        )
        match = pattern.search(message)
        if not match:
            return None

        return {
            "pair": match.group("pair"),
            "order_type": match.group("order_type"),
            "entry": float(match.group("entry").replace(',', '')),
            "stop_loss": float(match.group("sl").replace(',', '')),
            "take_profit": [float(match.group("tp").replace(',', ''))],
            "timeframe": match.group("timeframe")
        }

    def _is_tp_message(self, message: str) -> bool:
        message_lower = message.lower()

        # Skip common working/neutral messages
        if any(phrase in message_lower for phrase in ['в работе', 'если пропустили']):
            return False

        # Strong TP confirmation keywords
        tp_phrases = [
            'takeprofit', 'tp1 hit', 'tp2 hit', 'tp3 hit',
            'tp1 выполнен', 'tp достигнут'
        ]

        return any(tp in message_lower for tp in tp_phrases) and not self._is_cancel_message(message)


    def _is_sl_message(self, message: str) -> bool:
        message = message.lower()
        return '❌' in message and 'sl' in message

    def _is_cancel_message(self, message: str) -> bool:
        return self.cancel_pattern.search(message) is not None

    def _is_in_profit_update(self, message: str) -> bool:
        message_lower = message.lower()

        if self._is_tp_message(message) or self._is_sl_message(message) or self._is_cancel_message(message):
            return False

        # Consider any message with profit-related phrasing as IN_PROFIT_UPDATE
        indicators = ['фикс', 'бу', 'безубыток', 'плюс', 'profit', 'профит', 'вышли в +']

        has_indicator = any(ind in message_lower for ind in indicators)
        has_pips = re.search(r'(\+|плюс)\s*\d+\s*пункт[аов]*', message_lower)

        return has_indicator and has_pips is not None

    def _extract_pips(self, message: str) -> Optional[int]:
        match = re.search(r'(\+|\bплюс\s*)(\d+)\s*пункт[аов]*', message.lower())
        if match:
            return int(match.group(2))
        return None

    def _clean_message(self, message: str) -> str:
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
        },
        {
            "chat_id": -1000,
            "msg_id": 3,
            "msg_text": """BuyStop #NaturalGas (h4) ПГиП
Price: 3784.2
SL: 3667.8
TP: 4061.0
(Commodity)""",
            "reply_msg_id": None,
        },
        {'chat_id': -1001297727353, 'msg_id': 18608, 'msg_date': '2025-06-05T08:54:22+00:00', 'msg_text': 'BuyStop #AUDNZD (D1) ПГиП\nPrice: 1.08881\nSL: 1.07888\nTP: 111885\n(FX)', 'reply_msg_id': None, 'msg_type': 'NEW', 'signal_type': 'forex'},
        {'chat_id': -1001297727353, 'msg_id': 18612, 'msg_date': '2025-06-05T08:59:05+00:00', 'msg_text': 'SellStop #EURGBP (h4) ГиП\nPrice: 0.84032\nSL: 0.84302\nTP: 0.83652\n(FX)', 'reply_msg_id': None, 'msg_type': 'NEW', 'signal_type': 'forex'} 
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

    profit_msgs = [
        {
            "chat_id": -1000,
            "msg_id": 11,
            "msg_text": "+34 пункта ✅",
            "reply_msg_id": 1,
        },
        {
            "chat_id": -1000,
            "msg_id": 12,
            "msg_text": "Плюс 80 пунктов 🔥",
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
        },
        {'chat_id': -1001297727353, 'msg_id': 18610, 'msg_date': '2025-06-05T08:55:43+00:00', 'msg_text': 'Delete ❌\n(Слом паттерна)', 'reply_msg_id': None, 'msg_type': 'NEW', 'signal_type': 'forex'},
        {'chat_id': -1001297727353, 'msg_id': 18611, 'msg_date': '2025-06-05T08:55:59+00:00', 'msg_text': 'Delete ❌\n(Слом паттерна)', 'reply_msg_id': 18580, 'msg_type': 'NEW', 'signal_type': 'forex'} 
    ]
    
    print("=== Entry Signals ===")
    for msg in entry_msgs:
        result = classifier.process_message(msg)
        print(result)
    
    print("\n=== TP Hit Signals ===")
    for msg in tp_msgs:
        print(classifier.process_message(msg))

    print("\n=== In Profit Update ===")
    for msg in profit_msgs:
        print(classifier.process_message(msg))
    
    print("\n=== SL Hit Signals ===")
    for msg in sl_msgs:
        print(classifier.process_message(msg))
    
    print("\n=== Cancel Signals ===")
    for msg in cancel_msgs:
        print(classifier.process_message(msg))