from classifiers.LordForex import LordForexClassifier
from classifiers.WolfForex import WolfForexClassifier
from classifiers.WolfCrypto import WolfCryptoClassifier
from typing import Dict, Optional


class ForexSignalProcessor:
    """Main processor that routes messages to appropriate classifiers"""
    
    def __init__(self):
        self.classifiers = {
            'wolf_forex': WolfForexClassifier(),
            'lord_forex': LordForexClassifier(),
            'wolf_crypto': WolfCryptoClassifier(),
        }
    
    def process_message(self, message_data: dict) -> Optional[Dict]:
        """Determine which classifier to use and process the message"""
        # Detect signal source
        if message_data['chat_id'] == -1001485605405:
            classifier = self.classifiers['wolf_forex']
        # elif message_data['chat_id'] == -1002587201256:
        #     classifier = self.classifiers['lord_forex']
        elif message_data['chat_id'] == -1001338521686:
            classifier = self.classifiers['wolf_crypto']
            
        elif message_data['chat_id'] == -1002643902459:
            classifier = self.classifiers['wolf_forex']
        elif message_data['chat_id'] == -1002587201256:
            classifier = self.classifiers['wolf_crypto']
        else:
            return None
            
        return classifier.process_message(message_data)
