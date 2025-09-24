#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from classifiers.FxGoldKiller import FxGoldKillerClassifier

def test_fx_gold_killer():
    classifier = FxGoldKillerClassifier()
    
    # Test data from the file
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
 💰VIP💰FX_GØLD_KÏLLÊR"""
    }]

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
    }]

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

    print("=== Testing Entry Signals ===")
    for i, msg in enumerate(entry_msgs, 1):
        print(f"\nEntry Signal {i}:")
        print(f"Input: {msg['msg_text'][:50]}...")
        result = classifier.process_message(msg)
        if result:
            print(f"Action: {result['action']}")
            print(f"Pair: {result.get('pair')}")
            print(f"Side: {result.get('side')}")
            print(f"Type: {result.get('type')}")
            print(f"Entry: {result.get('entry')}")
            print(f"Stop Loss: {result.get('stop_loss')}")
            print(f"Take Profits: {result.get('take_profit')}")
            print(f"Order ID: {result.get('order_id')}")
        else:
            print("No result - signal not recognized")

    print("\n=== Testing TP Hit Signals ===")
    for i, msg in enumerate(tp_msgs, 1):
        print(f"\nTP Hit {i}:")
        print(f"Input: {msg['msg_text']}")
        result = classifier.process_message(msg)
        if result:
            print(f"Action: {result['action']}")
            print(f"TP Level: {result.get('tp_level')}")
            print(f"Pips: {result.get('pips')}")
            print(f"Order ID: {result.get('order_id')}")
        else:
            print("No result - signal not recognized")

    print("\n=== Testing SL Hit Signals ===")
    for i, msg in enumerate(sl_msgs, 1):
        print(f"\nSL Hit {i}:")
        print(f"Input: {msg['msg_text']}")
        result = classifier.process_message(msg)
        if result:
            print(f"Action: {result['action']}")
            print(f"Pips: {result.get('pips')}")
            print(f"Order ID: {result.get('order_id')}")
        else:
            print("No result - signal not recognized")

    print("\n=== Testing Cancel Signals ===")
    for i, msg in enumerate(cancel_msgs, 1):
        print(f"\nCancel Signal {i}:")
        print(f"Input: {msg['msg_text']}")
        result = classifier.process_message(msg)
        if result:
            print(f"Action: {result['action']}")
            print(f"Order ID: {result.get('order_id')}")
        else:
            print("No result - signal not recognized")

if __name__ == "__main__":
    test_fx_gold_killer()
