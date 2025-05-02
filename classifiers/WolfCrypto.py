import re
from typing import Optional, Dict, List, Union

class WolfCryptoClassifier:
    def process_message(self, msg: dict) -> Optional[dict]:
        """Process a Telegram message and extract trading signal information."""
        text = msg["msg_text"]
        action = None

        # Normalize text
        text = self._normalize_text(text)

        # Detect signal type
        if self._is_tp_hit(text):
            action = "TP_HIT"
        elif self._is_sl_hit(text):
            action = "SL_HIT"
        elif self._is_cancelled(text):
            action = "CANCELLED"
        elif self._is_new_signal(text):
            action = "NEW_SIGNAL"
        else:
            return None  # Not a relevant message

        # Generate order_id - use reply_msg_id for TP/SL hits if available
        order_id = self._generate_order_id(msg, action)

        # Base result with all possible fields in correct order
        result = {
            "chat_id": msg["chat_id"],
            "msg_id": msg["msg_id"],
            "msg_text": msg["msg_text"],
            "reply_msg_id": msg.get("reply_msg_id"),
            "pair": None,
            "side": None,
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "action": action,
            "type": "LIMIT",
            "order_id": order_id,
            "leverage": None,
            "tp_level": None,  # Only for TP_HIT
            "profit_percent": None  # Only for TP_HIT/SL_HIT
        }

        # Extract additional data based on action type
        if action == "NEW_SIGNAL":
            result.update(self._extract_new_signal_data(text))
        elif action in ["TP_HIT", "SL_HIT"]:
            result.update(self._extract_outcome_data(text))
        elif action == "CANCELLED":
            result.update(self._extract_cancelled_data(text))

        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}

    def _generate_order_id(self, msg: dict, action: str) -> str:
        """Generate order ID using reply_msg_id for TP/SL hits if available."""
        if action in ["TP_HIT", "SL_HIT"] and msg.get("reply_msg_id"):
            return f"{msg['chat_id']}_{msg['reply_msg_id']}"
        return f"{msg['chat_id']}_{msg['msg_id']}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing."""
        text = text.strip()
        text = re.sub(r'[\xa0\u200b\u202f]', ' ', text)  # Replace special spaces
        text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
        text = text.replace('💰', '').replace('🚫', '').replace('✅', '').replace('🔹', '')
        return text

    def _is_tp_hit(self, text: str) -> bool:
        """Check if message indicates a take profit hit."""
        text_lower = text.lower()
        return (
            ("tp" in text_lower and any(word in text_lower for word in ["hit", "reached", "completed"])) or
            ("take profit" in text_lower and any(word in text_lower for word in ["hit", "reached", "completed"])) or
            bool(re.search(r"✅+\s*[A-Z]{2,10}/USDT\s*TP\d", text)) or
            bool(re.search(r"BTC/USDT TP\d", text, re.IGNORECASE))
        )

    def _is_sl_hit(self, text: str) -> bool:
        """Check if message indicates a stop loss hit."""
        text_lower = text.lower()
        return (
            ("sl" in text_lower and any(word in text_lower for word in ["hit", "reached", "triggered"])) or
            ("stop loss" in text_lower and any(word in text_lower for word in ["hit", "reached", "triggered"])) or
            bool(re.search(r"BTC hit Stop Loss", text, re.IGNORECASE))
        )

    def _is_cancelled(self, text: str) -> bool:
        """Check if message indicates a cancelled order."""
        text_lower = text.lower()
        return (
            "cancelled" in text_lower or
            bool(re.search(r"#\w+/USDT\s+Manually\s+Cancelled", text))
        )

    def _is_new_signal(self, text: str) -> bool:
        """Check if message is a new trading signal."""
        has_pair = re.search(r"\b([A-Z]{2,10}/USDT)\b", text) is not None
        has_signal_keywords = any(
            phrase in text.lower() 
            for phrase in ['entry', 'enter', 'buy', 'sell', 'long', 'short']
        )
        has_tp_sl = (
            ('tp' in text.lower() or 'take profit' in text.lower()) and
            ('sl' in text.lower() or 'stop loss' in text.lower())
        )
        return has_pair and has_signal_keywords and has_tp_sl

    def _extract_new_signal_data(self, text: str) -> Dict:
        """Extract trading details from new signal message."""
        data = {}
        text_lower = text.lower()
        
        # Extract pair
        pair_match = re.search(r"\b([A-Z]{2,10}/USDT)\b", text)
        data["pair"] = pair_match.group(1) if pair_match else None
        
        # Extract side
        if 'buy' in text_lower or 'long' in text_lower:
            data["side"] = "buy"
        elif 'sell' in text_lower or 'short' in text_lower:
            data["side"] = "sell"
        
        # Extract entry price
        entry_match = re.search(
            r"(?:entry|enter|price)[: ]+([\d.,]+)|"
            r"enter (?:above|below):\s*([\d.,]+)",
            text_lower
        )
        if entry_match:
            entry_str = next(g for g in entry_match.groups() if g is not None)
            data["entry"] = float(entry_str.replace(',', ''))
        
        # Extract stop loss
        sl_match = re.search(
            r"(?:sl|stop loss)[: ]+([\d.,]+)|"
            r"🚫sl\s*([\d.,]+)",
            text_lower
        )
        if sl_match:
            sl_str = next(g for g in sl_match.groups() if g is not None)
            data["stop_loss"] = float(sl_str.replace(',', ''))
        
        # Extract take profits
        tps = re.findall(
            r"(?:tp|take profit)\d*[: ]+([\d.,]+)|"
            r"💰tp\d*\s*([\d.,]+)",
            text_lower
        )
        data["take_profit"] = [float(tp.replace(',', '')) for match in tps for tp in match if tp]
        
        # Extract leverage
        lev_match = re.search(
            r"(?:leverage|lev|〽️leverage)[: ]*\s*(\d+)x",
            text,
            re.IGNORECASE
        )
        if lev_match and lev_match.group(1):
            try:
                data["leverage"] = int(lev_match.group(1))
            except (ValueError, TypeError):
                data["leverage"] = 1
        else:
            data["leverage"] = 1  # Default leverage
        
        return data

    def _extract_outcome_data(self, text: str) -> Dict:
        """Extract data from TP/SL hit messages."""
        data = {}
        
        # Extract pair
        pair_match = re.search(r"\b([A-Z]{2,10}/USDT)\b", text)
        if pair_match:
            data["pair"] = pair_match.group(1)
        
        # Extract TP level (for TP_HIT only)
        tp_num_match = re.search(r"TP\s?(\d+)", text, re.IGNORECASE)
        tp_word_match = re.search(r"Take Profit\s(\d+)", text, re.IGNORECASE)
        tp_ordinal_match = re.search(r"(first|1st|second|2nd|third|3rd)\s(?:take profit|tp)", text, re.IGNORECASE)
        
        if tp_num_match:
            data["tp_level"] = int(tp_num_match.group(1))
        elif tp_word_match:
            data["tp_level"] = int(tp_word_match.group(1))
        elif tp_ordinal_match:
            ordinal_map = {
                'first': 1, '1st': 1,
                'second': 2, '2nd': 2,
                'third': 3, '3rd': 3
            }
            data["tp_level"] = ordinal_map.get(tp_ordinal_match.group(1).lower(), 1)
        
        # Extract profit percentage
        profit_match = re.search(r"Profit(?: Made)?:\s*([\d.]+)%", text, re.IGNORECASE) or \
                     re.search(r"([\d.]+)%\s*profit", text, re.IGNORECASE)
        if profit_match:
            data["profit_percent"] = float(profit_match.group(1))
        
        return data

    def _extract_cancelled_data(self, text: str) -> Dict:
        """Extract data from cancelled messages."""
        data = {}
        pair_match = re.search(r"#(\w+)/USDT", text)
        if pair_match:
            data["pair"] = f"{pair_match.group(1)}/USDT"
        return data
    

# classifier = WolfCryptoClassifier()

# classifier = WolfCryptoClassifier()

# # New signal
# entry_msg = {
#     "chat_id": 123,
#     "msg_id": 1,
#     "msg_text": """BTC/USDT 📈 BUY\n\n🔹Enter above: 93540.6\n💰TP1 93729.2\n💰TP2 94008.4\n🚫SL 93022.8\n〽️Leverage 20x"""
# }
# print(classifier.process_message(entry_msg))

# # TP hit (reply to original signal)
# tp_hit_msg = {
#     "chat_id": 123,
#     "msg_id": 2,
#     "reply_msg_id": 1,
#     "msg_text": """✅✅ BTC/USDT TP2 ✅✅\nProfit Made: 10.006%"""
# }
# print(classifier.process_message(tp_hit_msg))

# # Cancelled order
# cancelled_msg = {
#     "chat_id": 123,
#     "msg_id": 3,
#     "msg_text": "#LINK/USDT Manually Cancelled"
# }
# print(classifier.process_message(cancelled_msg))


# other_msg = {
#     "chat_id": 123,
#     "msg_id": 123,
#     "msg_text": """📍APRIL 29TH, 2025 - CRYPTO ANALYSIS👇

# •Bitcoin (BTC): Consolidating Before the Next Big Move
# ——————————————————

# •BTC is currently consolidating inside a 4-day price range on the daily chart, awaiting a breakout to decide the next major move.

# 📌 Technical Outlook:

# • A breakout above $95.7K would likely trigger a continuation toward the $100K liquidity zone.
# • A breakdown below $92.7K could lead to a visit into the Fair Value Gap (FVG) before resuming the uptrend — a perfect opportunity to position for longs.
# • Market momentum remains bullish overall, but patience is key until confirmation.

# 📊 Key Levels to Watch:

# • Resistance: $95.7K (range high), $100K (liquidity target)
# • Support: $92.7K (range low), FVG zone below (potential long setup)

# 📈 Trading Strategy:

# • We will stay patient until a confirmed breakout occurs.
# • Planning to enter long positions if we fill the FVG after a breakdown.
# • A clean breakout above $95.7K would also trigger bullish continuation setups.

# Staying focused — the real opportunity is coming soon.

# ——————————————————
# ✅ OTHER WOLFX SERVICES ✅

# 📌TRADING ACADEMY: HERE 🟢

# ✅ACCOUNT MANAGEMENT HERE

# 📨 FEEDBACK: @WOLFX_SIGNALS"""
# }
# print(classifier.process_message(other_msg))