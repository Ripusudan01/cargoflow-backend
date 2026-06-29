import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

API_KEY = os.getenv("BREVO_API_KEY")
logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str):
    if not API_KEY:
        logger.error("BREVO_API_KEY is not configured; email not sent to %s", to_email)
        return False

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "name": "CargoFlow",
            "email": "ripusudankumarjha05@gmail.com"
        },
        "to": [
            {"email": to_email}
        ],
        "subject": subject,
        "htmlContent": body
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Email send failed for %s", to_email)
        return False
