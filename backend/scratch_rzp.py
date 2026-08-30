import sys
import os
import asyncio
from dotenv import load_dotenv
import razorpay

load_dotenv("c:/Users/Ekaansh/OneDrive/Desktop/AB/projects/NEXORA/.env")

key_id = os.environ.get("RAZORPAY_KEY_ID")
key_secret = os.environ.get("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(key_id, key_secret))

try:
    order = client.order.create({
        "amount": 120000000,  # 1,200,000 INR
        "currency": "INR",
        "receipt": "test_receipt",
        "notes": {}
    })
    print("Success!", order)
except Exception as e:
    print("Error:", str(e))
