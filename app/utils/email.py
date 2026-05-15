import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BREVO_API_KEY")

def send_email(to_email: str, subject: str, body: str):
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
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 201:
            print("Email failed:", response.text)
    except Exception as e:
        print("Email exception:", str(e))