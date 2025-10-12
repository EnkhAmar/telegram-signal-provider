import re
from typing import Optional, Dict, List, Union

class VipCryptoClassifier:
    def __init__(self):
        # Entry signal patterns
        self.entry_pattern = re.compile(
            r'🟢\s*(?P<side>Long|Short)\s*'
            r'Name:\s*(?P<pair>[A-Z]+/USDT)\s*'
            r'Margin\s+mode:\s*(?P<margin_info>.*?)\s*'
            r'↪️\s*Entry\s+price\(USDT\):\s*'
            r'(?P<entry>[\d.]+)\s*'
            r'Targets\(USDT\):\s*'
            r'(?P<targets>.*?)(?=\n|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        # TP hit pattern
        self.tp_hit_pattern = re.compile(
            r'💸\s*(?P<pair>[A-Z]+/USDT)\s*'
            r'✅\s*Target\s*#(?P<tp_level>\d+)\s*Done\s*'
            r'Current\s+profit:\s*(?P<profit_percent>\d+)%',
            re.IGNORECASE | re.DOTALL
        )

    def process_message(self, msg: dict) -> Optional[dict]:
        """Process a Telegram message and extract VipCrypto trading signal information."""
        text = msg["msg_text"]
        action = None

        # Normalize text
        text = self._normalize_text(text)

        # Detect signal type
        if self._is_tp_hit(text):
            action = "TP_HIT"
        elif self._is_new_signal(text):
            action = "NEW_SIGNAL"
        else:
            action = "OTHER"

        # Generate order_id - use reply_msg_id for TP hits if available
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
            "profit_percent": None  # Only for TP_HIT
        }

        # Extract additional data based on action type
        if action == "NEW_SIGNAL":
            signal_data = self._extract_new_signal_data(text)
            result.update(signal_data)
        elif action == "TP_HIT":
            result.update(self._extract_tp_data(text))

        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}

    def _generate_order_id(self, msg: dict, action: str) -> str:
        """Generate order ID using reply_msg_id for TP hits if available."""
        if action == "OTHER":
            return None
        if action == "TP_HIT" and msg.get("reply_msg_id"):
            return f"{msg['chat_id']}_{msg['reply_msg_id']}"
        return f"{msg['chat_id']}_{msg['msg_id']}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing."""
        text = text.strip()
        text = re.sub(r'[\xa0\u200b\u202f]', ' ', text)  # Replace special spaces
        text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
        return text

    def _is_tp_hit(self, text: str) -> bool:
        """Check if message indicates a take profit hit."""
        return bool(self.tp_hit_pattern.search(text))

    def _is_new_signal(self, text: str) -> bool:
        """Check if message is a new trading signal."""
        return bool(self.entry_pattern.search(text))

    def _extract_new_signal_data(self, text: str) -> Dict:
        """Extract trading details from new signal message."""
        data = {}
        
        match = self.entry_pattern.search(text)
        if not match:
            return data
        
        # Extract basic signal info
        data["pair"] = match.group("pair")
        data["side"] = "BUY" if match.group("side").upper() == "LONG" else "SELL"
        data["entry"] = float(match.group("entry"))
        
        # Extract leverage from margin info (e.g., "Cross (75X)")
        margin_info = match.group("margin_info")
        leverage_match = re.search(r'\((\d+)X\)', margin_info, re.IGNORECASE)
        if leverage_match:
            data["leverage"] = int(leverage_match.group(1))
        else:
            data["leverage"] = 1
        
        # Extract targets
        targets_text = match.group("targets")
        targets = self._extract_targets(targets_text)
        if targets:
            data["take_profit"] = targets
        
        return data

    def _extract_targets(self, targets_text: str) -> List[float]:
        """Extract target prices from targets section."""
        targets = []
        
        # Pattern for targets like "1) 0.3836"
        target_matches = re.findall(r'\d+\)\s*([\d.]+)', targets_text)
        for target in target_matches:
            try:
                targets.append(float(target))
            except ValueError:
                continue
        
        return targets

    def _extract_tp_data(self, text: str) -> Dict:
        """Extract data from TP hit messages."""
        data = {}
        
        match = self.tp_hit_pattern.search(text)
        if not match:
            return data
        
        data["pair"] = match.group("pair")
        data["tp_level"] = int(match.group("tp_level"))
        data["profit_percent"] = float(match.group("profit_percent"))
        
        return data


# Example Usage
if __name__ == "__main__":
    classifier = VipCryptoClassifier()

    test_cases = [
        {
            "chat_id": -100123,
            "msg_id": 101,
            "msg_text": """🟢 Long
Name: APE/USDT
Margin mode: Cross (75X)

↪️ Entry price(USDT):
0.3798

Targets(USDT):
1) 0.3836
2) 0.3874
3) 0.3912
4) 0.3950
5) 🔝 unlimited"""
        },
        {
            "chat_id": -100123,
            "msg_id": 102,
            "msg_text": """🟢 Long
Name: ALT/USDT
Margin mode: Cross (20X)

↪️ Entry price(USDT):
0.01969

Targets(USDT):
1) 0.01989
2) 0.02008
3) 0.02028
4) 0.02048
5) 🔝 unlimited"""
        },
        {
            "chat_id": -100123,
            "msg_id": 103,
            "reply_msg_id": 101,
            "msg_text": """💸 APE/USDT
✅ Target #1 Done
Current profit: 75%"""
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
        print(f"Details: {dict((k, v) for k, v in result.items() if k not in ['action', 'msg_text', 'chat_id', 'msg_id', 'order_id'])}")
        print("-" * 50)


