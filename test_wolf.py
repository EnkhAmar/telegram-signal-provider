import re
from enum import Enum
from typing import Optional, Dict, Union

class SignalType(Enum):
    ENTRY = 1
    TAKE_PROFIT = 2
    STOP_LOSS = 3

class WolfForexClassifier:
    """
    A focused classifier for forex trading signals that only processes order-related messages:
    - Entry signals (BUY/SELL with price and targets)
    - Take profit hits (TP reached)
    - Stop loss hits (SL reached)
    """
    
    def __init__(self):
        # Entry signal patterns (order opening)
        self.entry_patterns = [
            # Format: SYMBOL 📈/📉 BUY/SELL @ PRICE
            r'(?P<symbol>[A-Z]{6})\s*[📈📉↗↘]\s*(?P<direction>BUY|SELL)\s*(?P<price>\d+\.\d+)',
            # Format: BUY/SELL SYMBOL @ PRICE
            r'(?P<direction>BUY|SELL)\s*(?P<symbol>[A-Z]{6})\s*@?\s*(?P<price>\d+\.\d+)',
            # Format with SL/TP on same line
            r'(?P<symbol>[A-Z]{6})\s*(?P<direction>BUY|SELL)\s*(?P<price>\d+\.\d+)\s*SL\s*(?P<sl>\d+\.\d+)\s*TP\s*(?P<tp>\d+\.\d+)'
        ]
        
        # Take profit patterns
        self.tp_patterns = [
            r'(TP|Take Profit|Profit Take|TakeProfit)\s*(\d+)\s*(✅|✔|hit|reached|made)',
            r'✅.*(TP|Take Profit)\s*(\d+).*✅',
            r'📊\s*Profit\s*Made:\s*\+\d+\s*PIPS'
        ]
        
        # Stop loss patterns
        self.sl_patterns = [
            r'(SL|Stop Loss|stoploss|StopLoss)\s*(✖|❌|hit|reached)',
            r'💎Profit:\s*-\d+\s*PIPS',
            r'Stop\s*Loss\s*triggered'
        ]
        
        # Ignore patterns (messages containing these will be skipped)
        self.ignore_patterns = [
            r'ACCOUNT MANAGEMENT',
            r'copy trading',
            r'promotion',
            r'summary',
            r'analysis',
            r'www\.|\.com|\.io',
            r'👇👇👇|⚜️|👉|➡️'
        ]

    def classify(self, message: str) -> Optional[SignalType]:
        """Classify the message and return SignalType if it's an order-related message"""
        message = self._clean_message(message)
        
        # Skip if message matches ignore patterns
        if any(re.search(pattern, message, re.IGNORECASE) for pattern in self.ignore_patterns):
            return None
        
        # Check for TP hits
        if any(re.search(pattern, message, re.IGNORECASE) for pattern in self.tp_patterns):
            return SignalType.TAKE_PROFIT
        
        # Check for SL hits
        if any(re.search(pattern, message, re.IGNORECASE) for pattern in self.sl_patterns):
            return SignalType.STOP_LOSS
        
        # Check for entry signals
        for pattern in self.entry_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return SignalType.ENTRY
        
        return None

    def extract_signal(self, message: str) -> Optional[Dict[str, Union[str, float, Dict]]]:
        """Extract signal details if it's an entry order"""
        message = self._clean_message(message)
        signal_type = self.classify(message)
        
        if signal_type != SignalType.ENTRY:
            return None
        
        for pattern in self.entry_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                symbol = groups.get('symbol')
                direction = groups.get('direction')
                price = float(groups.get('price'))
                
                # Extract TP/SL from the full message if not in the pattern
                tps = self._extract_take_profits(message)
                sl = self._extract_stop_loss(message) if not groups.get('sl') else float(groups.get('sl'))
                
                return {
                    'type': 'ENTRY',
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': price,
                    'take_profits': tps,
                    'stop_loss': sl,
                    'raw_message': message
                }
        return None

    def _clean_message(self, message: str) -> str:
        """Clean the message by removing extra spaces and line breaks"""
        return ' '.join(message.strip().split())

    def _extract_take_profits(self, message: str) -> Dict[str, float]:
        """Extract all take profit levels from message"""
        tps = {}
        tp_matches = re.findall(r'(?:💰TP|TP|Take Profit)\s*(\d+)\s*(\d+\.\d+)', message)
        for level, price in tp_matches:
            tps[f"TP{level}"] = float(price)
        return tps

    def _extract_stop_loss(self, message: str) -> Optional[float]:
        """Extract stop loss level from message"""
        sl_match = re.search(r'(?:🚫SL|SL|Stop Loss)\s*(\d+\.\d+)', message)
        return float(sl_match.group(1)) if sl_match else None

# Example Usage
if __name__ == "__main__":
    classifier = WolfForexClassifier()
    
    # Test signals
    test_signals = [
        """
        XAUUSD 📉 SELL 3133.50

        💰TP1 3131.50
        💰TP2 3128.50
        💰TP3 3123.50
        🚫SL 3142.00
        """,
        
        "BUY EURUSD @1.0850 SL 1.0820 TP 1.0900",
        
        """
        💚💚💚💚💚💚💚💚💚💚💚💚
        ✅✅ GOLD Take Profit 1 ✅✅
        📊 Profit Made: 20 PIPS🔥
        """,
        
        """
        EURJPY SELL 158.50 SL 159.00 TP1 158.00 TP2 157.50
        """,
        
        """
        #XAUUSD 🏆📉 Short-Term Correction, Long-Term Bullish
        (This should be ignored)
        """
    ]
    
    for signal in test_signals:
        print("="*50)
        print("Original Message:")
        print(signal.strip())
        print("\nClassification Result:")
        
        signal_type = classifier.classify(signal)
        if signal_type:
            print(f"Detected Signal Type: {signal_type.name}")
            if signal_type == SignalType.ENTRY:
                details = classifier.extract_signal(signal)
                print("Signal Details:")
                for k, v in details.items():
                    if k != 'raw_message':
                        print(f"{k}: {v}")
        else:
            print("IGNORED (not a trading signal)")
        
        print("="*50)
        print("\n")