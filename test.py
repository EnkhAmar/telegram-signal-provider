from classifiers import ForexSignalProcessor

# Example Usage
if __name__ == "__main__":
    processor = ForexSignalProcessor()
    
    wolf_signal = """
    XAUUSD 📉 SELL 3133.50
    💰TP1 3131.50
    💰TP2 3128.50
    💰TP3 3123.50
    🚫SL 3142.00
    WOLFXSIGNALS.COM
    """
    
    lord_signal = """
    🔔 NEW ORDER - USDJPY - Buy 🔔
    Entry: 149.298
    TP @ 149.802
    SL @ 148.813
    ID: 976546156
    """
    
    print("Processing Wolf Forex Signal:")
    print(processor.process_message(wolf_signal))
    
    print("\nProcessing Lord Forex Signal:")
    print(processor.process_message(lord_signal))