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
            action = "OTHER"

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
            signal_data = self._extract_new_signal_data(text)
            result.update(signal_data)
            # Convert empty take_profit list to None
            if "take_profit" in result and isinstance(result["take_profit"], list) and not result["take_profit"]:
                result["take_profit"] = None
        elif action in ["TP_HIT", "SL_HIT"]:
            result.update(self._extract_outcome_data(text))
        elif action == "CANCELLED":
            result.update(self._extract_cancelled_data(text))

        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}

    def _generate_order_id(self, msg: dict, action: str) -> str:
        """Generate order ID using reply_msg_id for TP/SL hits if available."""
        if action in ["OTHER"]:
            return None
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
        return has_pair and (has_signal_keywords or has_tp_sl)

    def _extract_new_signal_data(self, text: str) -> Dict:
        """Extract trading details from new signal message."""
        data = {}
        text_lower = text.lower()
        
        # Extract pair
        pair_match = re.search(r"\b([A-Z]{2,10}/USDT)\b", text)
        data["pair"] = pair_match.group(1) if pair_match else None
        
        # Extract side (default to sell if not specified)
        if 'buy' in text_lower or 'long' in text_lower:
            data["side"] = "BUY"
        elif 'sell' in text_lower or 'short' in text_lower:
            data["side"] = "SELL"
        else:
            # Default to sell if not specified (common in some signal formats)
            data["side"] = "None"
        
        # Extract entry price
        entry_match = re.search(
            r"(?:entry|enter|below|above|price)[: ]+([\d.,]+)|"
            r"enter (?:above|below):\s*([\d.,]+)|"
            r"🔹Enter (?:below|above):\s*([\d.,]+)",
            text_lower
        )
        if entry_match:
            entry_str = next(g for g in entry_match.groups() if g is not None)
            data["entry"] = float(entry_str.replace(',', ''))
        
        # Extract stop loss - improved pattern
        sl_match = re.search(
            r"(?:sl|stop loss|🚫sl)[: ]+([\d.,]+)|"
            r"🚫sl\s*([\d.,]+)|"
            r"sl\s*[:=]?\s*([\d.,]+)",
            text,
            re.IGNORECASE
        )
        if sl_match:
            sl_str = next(g for g in sl_match.groups() if g is not None)
            data["stop_loss"] = float(sl_str.replace(',', ''))
        
        # Extract take profits - improved pattern
        tps = re.findall(
            r"(?:tp|take profit|💰tp)\d*[: ]+([\d.,]+)|"
            r"💰tp\d*\s*([\d.,]+)|"
            r"tp\d*\s*[:=]?\s*([\d.,]+)",
            text,
            re.IGNORECASE
        )
        if tps:
            data["take_profit"] = [float(tp.replace(',', '')) for match in tps for tp in match if tp]
        else:
            data["take_profit"] = None
        
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
    

# Example Usage
if __name__ == "__main__":
    classifier = WolfCryptoClassifier()

    test_cases = [
        {
            "chat_id": -100123,
            "msg_id": 101,
            "msg_text": """AAVE/USDT

🔹Enter below:167.04(with a minimum value of 166.90)

📉SELL 

💰TP1 166.71
💰TP2 166.21
💰TP3 164.53
🚫SL 168.01

〽️Leverage 20x

⚠️Respect the entry zone. Check the bio of the channel for all the info required to follow our signals"""
        },
        {
            "chat_id": -123123,
            "msg_id": 123,
            "msg_text": """SOL/USDT

🔹Enter below:148.50(with a minimum value of 148.40)

📉SELL 

💰TP1 148.20
💰TP2 147.76
💰TP3 146.27
🚫SL 149.18

〽️Leverage 20x

⚠️Respect the entry zone. Check the bio of the channel for all the info required to follow our signals"""
        },
        {
            "chat_id": -100123,
            "msg_id": 124,
            "reply_msg_id": 123,
            "msg_text": """📣 Yes, SOL hit Stop Loss: -9.158%

👉 In general terms, April is being a good month. We expect to have a very positive week, so let’s continue🟢

➡️New Signals coming soon, so pay attention, activate notifications and let’s go for it!✅

🎁 WE HAVE A NEW SURPRISE COMING FOR CRYPTO VIP MEMBERS IN MAY 2025 🎁

———————————————————
⚠️Best sites follow our Signals (BONUS FOR VIPS) 👉🏻 {HERE}"""
        },
        {
            "chat_id": -100123,
            "msg_id": 103,
            "reply_msg_id": 101,
            "msg_text": """💚💚💚💚💚💚💚💚💚💚💚💚

✅ AAVE/USDT Take Profit 1 ✅

📊 Profit Made: 3.9511%🔥

•AAVE hit a value of 166.420 in BYBIT, completing the first take profit!""",
        },
        {
            "chat_id": -100123,
            "msg_id": 104,
            "msg_text": """📍APRIL 27TH, 2025 - CRYPTO ANALYSIS👇

#Bitcoin (#BTC): Setting Up for a Bullish Week Ahead

$BTC is showing strong signs of continuation as we prepare to close the week with the first green trend bar on the weekly chart in a while. The bullish structure looks intact heading into next week.

📌 Technical Outlook:
• We expect $BTC to take out last week’s high first before forming the weekly low.
• A pullback into the Fair Value Gap (FVG) is anticipated — offering a great long opportunity.
• Momentum remains strong, with $100K–$101K resistance being the next barrier before aiming for the $110K ATH.

📊 Key Levels to Watch:
• Resistance: $100K–$101K (short-term resistance), $110K (ATH)
• Support: FVG zone below (entry zone for new longs)

📈 Trading Strategy:
• Planning to enter new long positions inside the FVG on Monday.
• Will also start looking for long setups on outperforming altcoins.
• Preparing for a bullish continuation throughout the week — staying patient but ready to act.

A bullish week ahead is setting up nicely — we are ready!

——————————————————""",
        },
        {
            "chat_id": -100123,
            "msg_id": 104,
            "msg_text": """📍APRIL 29TH, 2025 - CRYPTO ANALYSIS👇

•Bitcoin (BTC): Consolidating Before the Next Big Move
——————————————————

•BTC is currently consolidating inside a 4-day price range on the daily chart, awaiting a breakout to decide the next major move.

📌 Technical Outlook:

• A breakout above $95.7K would likely trigger a continuation toward the $100K liquidity zone.
• A breakdown below $92.7K could lead to a visit into the Fair Value Gap (FVG) before resuming the uptrend — a perfect opportunity to position for longs.
• Market momentum remains bullish overall, but patience is key until confirmation.

📊 Key Levels to Watch:

• Resistance: $95.7K (range high), $100K (liquidity target)
• Support: $92.7K (range low), FVG zone below (potential long setup)

📈 Trading Strategy:

• We will stay patient until a confirmed breakout occurs.
• Planning to enter long positions if we fill the FVG after a breakdown.
• A clean breakout above $95.7K would also trigger bullish continuation setups.

Staying focused — the real opportunity is coming soon.

——————————————————
✅ OTHER WOLFX SERVICES ✅

📌TRADING ACADEMY: HERE 🟢

✅ACCOUNT MANAGEMENT HERE

📨 FEEDBACK: @WOLFX_SIGNALS"""
        },
        {
            "chat_id": -100123,
            "msg_id": 105,
            "msg_text": """✅️CRYPTO MARKET UPDATE✅️

•As we approach the end of the month, both Bitcoin and the broader market remain within a consolidation range. Before initiating any new trading strategies, it is essential to wait for a confirmed breakout from this range to determine the next directional move with greater confidence.

•We have a long week ahead, so be patient. New signals are coming really soon family.

Wolfxsignals Team"""
        }
    ]

    classifier = WolfCryptoClassifier()
    for case in test_cases:
        print("\n" + "="*50)
        print("Input Message:")
        print(case["msg_text"])
        result = classifier.process_message(case)
        print("\nOutput:")
        print(f"Action: {result['action']}")
        print(f"Result: {result}")
        print(f"Order ID: {result.get('order_id', 'N/A')}")
        print(f"Details: { {k:v for k,v in result.items() if k not in ['action', 'msg_text', 'chat_id', 'msg_id', 'order_id']} }")
