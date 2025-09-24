import re
from typing import Dict, List, Optional

class FxGoldKillerClassifier:
    def __init__(self):
        # Entry signal patterns for FxGoldKiller
        self.entry_pattern = re.compile(
            r'📣(?P<pair>XAUUSD)\s+(?P<side>BUY|SELL)(?:\s+(?:NOW|LIMIT))?\s*📣.*?'
            r'🔊\s*PRICE\s*:\s*(?P<entry>\d+)\s*'
            r'(?:.*?✅\s*TP1\s*(?P<tp1>\d+).*?'
            r'✅\s*TP2\s*(?P<tp2>\d+).*?'
            r'✅\s*TP3\s*(?P<tp3>\d+).*?'
            r'✅\s*TP4\s*(?P<tp4>\d+).*?'
            r'✅\s*TP5\s*(?P<tp5>\d+).*?)?'
            r'❌\s*SL:\s*(?P<sl>\d+)',
            re.IGNORECASE | re.DOTALL
        )
        
        # TP hit detection patterns
        self.tp_keywords = ['TP', 'HIT', '✅', 'DONE', '🤑', '💰']
        
        # SL hit detection patterns  
        self.sl_keywords = ['SL', 'HIT', '❌']
        
        # Cancel detection patterns
        self.cancel_keywords = ['Delete', 'limit', '✅']

    def process_message(self, message_data: Dict) -> Optional[Dict]:
        """Main method to process FxGoldKiller messages"""
        msg_text = self._clean_message(message_data.get('msg_text', ''))
        reply_msg_id = message_data.get('reply_msg_id')
        
        # Process entry signal (no reply)
        if not reply_msg_id:
            if entry := self._extract_entry(msg_text):
                return {
                    **message_data,
                    **entry,
                    "action": "NEW_SIGNAL",
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

    def _extract_entry(self, message: str) -> Optional[Dict]:
        """Extract entry signal details from FxGoldKiller messages"""
        match = self.entry_pattern.search(message)
        if not match:
            return None
        
        # Build take_profit list from captured groups
        take_profits = []
        for tp_num in ['tp1', 'tp2', 'tp3', 'tp4', 'tp5']:
            tp_value = match.group(tp_num)
            if tp_value:
                take_profits.append(float(tp_value))
        
        # Determine order type based on the signal text
        order_type = "MARKET"  # default
        if "LIMIT" in message.upper():
            order_type = "LIMIT"
        elif "NOW" in message.upper():
            order_type = "MARKET"
        
        return {
            "pair": match.group('pair'),
            "side": match.group('side').upper(),
            "entry": float(match.group('entry')),
            "stop_loss": float(match.group('sl')),
            "take_profit": take_profits if take_profits else None,
            "type": order_type
        }

    def _is_tp_message(self, message: str) -> bool:
        """Check if message is a TP hit notification"""
        message_upper = message.upper()
        return ('TP' in message_upper and 'HIT' in message_upper and 
                any(keyword in message for keyword in ['✅', 'DONE', '🤑', '💰']))

    def _is_sl_message(self, message: str) -> bool:
        """Check if message is an SL hit notification"""
        message_upper = message.upper()
        return ('SL' in message_upper and 'HIT' in message_upper and '❌' in message)

    def _is_cancel_message(self, message: str) -> bool:
        """Check if message is a cancel notification"""
        message_upper = message.upper()
        return ('DELETE' in message_upper and 'LIMIT' in message_upper and '✅' in message)

    def _extract_tp(self, message: str) -> Optional[Dict]:
        """Extract TP hit details from FxGoldKiller messages"""
        # Extract TP level (TP1, TP2, etc.)
        tp_match = re.search(r'TP(\d+)', message, re.IGNORECASE)
        tp_level = int(tp_match.group(1)) if tp_match else 1
        
        # Extract pips information if available
        pips_match = re.search(r'([+-]?\d+)\s*PIPS', message, re.IGNORECASE)
        pips = int(pips_match.group(1)) if pips_match else None
        
        return {
            "tp_level": tp_level,
            "pips": pips
        }

    def _extract_sl(self, message: str) -> Optional[Dict]:
        """Extract SL hit details from FxGoldKiller messages"""
        # Extract pips information if available
        pips_match = re.search(r'([+-]?\d+)\s*PIPS', message, re.IGNORECASE)
        pips = int(pips_match.group(1)) if pips_match else None
        
        return {
            "pips": pips
        }

    def _clean_message(self, message: str) -> str:
        """Normalize message text"""
        return ' '.join(message.strip().split())



entry_msgs = [{
    "chat_id": -100123456,
    "msg_id": 111,
    "msg_text": """📣XAUUSD BUY NOW 📣

🔊 PRICE : 3775

✅ TP1 3777 (+20 PIPS)

✅ TP2  3779 (+40 PIPS)

✅ TP3 3781 (+60 PIPS)

✅ TP4 3783 (+80 PIPS)

✅ TP5 3785 (+100 PIPS)

❌ SL: 3771   (40 PIPS)

🔷 Take only 2% risk 
COPYRIGHT ©️ reserved from
 💰VIP💰FX_GØLD_KÏLLÊR"""
},
{
    "chat_id": -100123456,
    "msg_id": 112,
    "msg_text": """📣XAUUSD BUY LIMIT📣

🔊 PRICE : 3736

✅ TP1 3738 (+20 PIPS)

✅ TP2  3740 (+40 PIPS)

✅ TP3 3742 (+60 PIPS)

✅ TP4 3744 (+80 PIPS)

✅ TP5 3746 (+100 PIPS)

❌ SL: 3732   (40 PIPS)

🔷 Take only 2% risk 
COPYRIGHT ©️ reserved from
 💰VIP💰FX_GØLD_KÏLLÊR"""}
 ,
]

tp_msgs = [{
    "chat_id": -100123456,
    "msg_id": 113,
    "msg_text": """✅TP1 HIT +20 PIPS DONE 🤑💰""",
    "reply_msg_id": 111
},
{
    "chat_id": -100123456,
    "msg_id": 114,
    "msg_text": """✅TP2 HIT +40 PIPS DONE 🤑💰""",
    "reply_msg_id": 111
},
{
    "chat_id": -100123456,
    "msg_id": 115,
    "msg_text": """✅TP3 HIT +60 PIPS DONE 🤑💰""",
    "reply_msg_id": 111
},
{
    "chat_id": -100123456,
    "msg_id": 116,
    "msg_text": """✅TP4 HIT +80 PIPS DONE 🤑💰""",
    "reply_msg_id": 111
},
{
    "chat_id": -100123456,
    "msg_id": 117,
    "msg_text": """✅TP5 HIT +100 PIPS DONE 🤑💰""",
    "reply_msg_id": 111
}
]

sl_msgs = [{
    "chat_id": -100123456,
    "msg_id": 118,
    "msg_text": """❌ SL HIT -40 PIPS""",
    "reply_msg_id": 111
}]

cancel_msgs = [{
    "chat_id": -100123456,
    "msg_id": 113,
    "msg_text": """✅ Delete limit""",
    "reply_msg_id": 112
}]

