AGENT_ROLE = "Food Delivery Customer Support Agent"

BUSINESS_CONTEXT = (
    "A food delivery platform that handles "
    "customer orders and delivery issues."
)

SUPPORTED_TASKS = [
    "order tracking",
    "delivery rescheduling",
    "late delivery complaints",
    "wrong order complaints"
]

LANGUAGE = "Hinglish"

import os
from dotenv import load_dotenv

load_dotenv()

TARGET_AGENT_URL = os.getenv(
    "TARGET_AGENT_URL",
    "http://localhost:8000/chat"
)