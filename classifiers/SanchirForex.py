import re
from enum import Enum
from typing import Dict, Optional


class SignalAction(Enum):
    NEW_SIGNAL = "NEW_SIGNAL"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"
    BREAKEVEN = "BREAKEVEN"
    

class SanchirForexClassifier:
    def __init__(self):
        pass
    
    def process_message(self, message_data: Dict) -> Optional[Dict]:
        msg_text = message_data.get('msg_text', '')
        reply_msg_id = message_data.get('reply_msg_id')
        
        if not reply_msg_id:
            if entry := self._extract_entry(msg_text):
                order_type = entry['order_type'].upper()
                return {
                    **message_data,
                    **entry,
                    "action": SignalAction.NEW_SIGNAL.value,
                    "type": order_type,
                    "side": "BUY" if order_type.startswith("BUY") else "SELL",
                    "order_id": f"{message_data['chat_id']}_{message_data['msg_id']}",
                }
                
        if reply_msg_id:
            if self._is_cancel_message(msg_text):
                return {
                    **message_data,
                    "action": SignalAction.CANCELLED.value,
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}"
                }
            elif self._is_close_message(msg_text):
                return {
                    **message_data,
                    "action": SignalAction.CLOSED.value,
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}",
                }
            elif self._is_breakeven_message(msg_text):
                return {
                    **message_data,
                    "action": SignalAction.BREAKEVEN.value,
                    "order_id": f"{message_data['chat_id']}_{reply_msg_id}",
                }
                
        return None
    
    def _extract_entry(self, message: str) -> Optional[Dict]:
        """
        Extracts trading entry info from messages like:
        
        pair: XAUUSDm
        side: Buy
        price: 3300
        """
        # Regex to match pair, side, and price (supports Buy, Sell, Buy_Limit, Sell_Limit)
        pattern = re.compile(
            r"pair:\s*(?P<pair>\w+)\s*[\r\n]+"
            r"side:\s*(?P<side>BUY|SELL|BUY_LIMIT|SELL_LIMIT|Buy|Sell|Buy_Limit|Sell_Limit)\s*[\r\n]+"
            r"price:\s*(?P<price>\d+(?:\.\d+)?)",
            re.IGNORECASE
        )

        match = pattern.search(message)
        if match:
            pair = match.group("pair").upper()
            order_type = match.group("side").upper().replace(" ", "_")
            price = float(match.group("price"))

            return {
                "pair": pair,
                "order_type": order_type,
                "entry": price,
                "stop_loss": None,
                "take_profit": [],
            }
        return None

    # Dummy placeholders (you can refine later)
    def _is_cancel_message(self, text: str) -> bool:
        return "cancel" in text.lower()

    def _is_close_message(self, text: str) -> bool:
        return "close" in text.lower()

    def _is_breakeven_message(self, text: str) -> bool:
        return "breakeven" in text.lower()
