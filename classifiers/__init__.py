from classifiers.LordForex import LordForexClassifier
from classifiers.WolfForex import WolfForexClassifier
from typing import Dict, Optional


class ForexSignalProcessor:
    """Main processor that routes messages to appropriate classifiers"""
    
    def __init__(self):
        self.classifiers = {
            'wolf': WolfForexClassifier(),
            'lord': LordForexClassifier()
        }
    
    def process_message(self, message_data: dict) -> Optional[Dict]:
        """Determine which classifier to use and process the message"""
        # Detect signal source
        if message_data['chat_id'] == -1002643902459:
            classifier = self.classifiers['wolf']
        elif message_data['chat_id'] == -1002643902460:
            classifier = self.classifiers['lord']
        else:
            return None
            
        return classifier.process_message(message_data)
