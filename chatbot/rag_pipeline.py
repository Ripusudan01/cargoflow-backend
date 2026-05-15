import re
import os
from typing import Dict, Any

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from app.database import SessionLocal
from app.models import Shipment, TrackingUpdate

from .embeddings import build_and_save, load, retrieve, get_model

load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


SYSTEM_PROMPT = """You are an AI logistics assistant for CargoFlow.

You must:
- Answer only based on provided context
- Be concise, clear, and professional
- Use bullet points when helpful
- If answer is not in context, say you don't know

You can help with:
- shipment tracking
- delivery services
- pricing
- logistics

If the question is unrelated, reply:
"Sorry, I can only help with CargoFlow logistics queries."
"""


# ---------------- HELPERS ---------------- 

def extract_tracking_id(text: str):
    match = re.search(r"CF-\d{8}-\d{4}", text)
    return match.group(0) if match else None


def extract_weight(text: str):
    match = re.search(r"(\d+)\s*kg", text.lower())
    return int(match.group(1)) if match else None


# ---------------- FEATURES ---------------- 

def handle_tracking(tracking_id: str):
    db = SessionLocal()

    try:
        shipment = db.query(Shipment).filter(
            Shipment.tracking_number == tracking_id
        ).first()

        if not shipment:
            return "Tracking ID not found"

        progress_map = {
            "CREATED": 10,
            "ASSIGNED": 40,
            "OUT_FOR_DELIVERY": 80,
            "DELIVERED": 100
        }

        progress = progress_map.get(shipment.status.value, 0)

        pickup_city = shipment.pickup_address.city if shipment.pickup_address else "N/A"
        delivery_city = shipment.delivery_address.city if shipment.delivery_address else "N/A"

        latest_tracking = db.query(TrackingUpdate)\
            .filter(TrackingUpdate.shipment_id == shipment.id)\
            .order_by(TrackingUpdate.timestamp.desc())\
            .first()

        if latest_tracking:
            lat = latest_tracking.latitude
            lng = latest_tracking.longitude
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
        else:
            lat, lng, map_url = "Not available", "Not available", "Location not available"

        return (
            f"Tracking ID: {shipment.tracking_number}\n"
            f"Status: {shipment.status.value}\n"
            f"From: {pickup_city}\n"
            f"To: {delivery_city}\n"
            f"Progress: {progress}%\n"
            f"Current Location: {lat}, {lng}\n"
            f"Map: {map_url}"
        )

    finally:
        db.close()


def handle_price(weight: int):
    return f"Estimated cost for {weight} kg is ₹{weight * 45}"


# ---------------- LLM ---------------- 

def call_llm(context: str, question: str):
    try:
        client = InferenceClient(token=HF_API_TOKEN)

        response = client.chat_completion(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nQuestion: {question}"}
            ],
            max_tokens=200,
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception:
        return "Sorry, I'm unable to respond right now. Please try again later."


# ---------------- MAIN CLASS ---------------- 

class CargoFlowRAG:

    def __init__(self):
        if not os.path.exists("chatbot/vector_store/index.faiss"):
            self.index, self.chunks, self.model = build_and_save()
        else:
            self.index, self.chunks = load()
            self.model = get_model()

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:

        q = question.lower()

        if any(word in q for word in ["contact", "support", "helpline", "email", "customer care", "help", "call", "complain", "query", "complaint"]):
            return {
                "question": question,
                "answer": (
                    "You can contact CargoFlow support:\n\n"
                    "Helpline: +91-9876543210\n"
                    "Email: support@cargoflow.com"
                ),
                "sources": [],
                "found_in_kb": False
            }

        # Greeting
        if re.search(r"\b(hi|hello|hey|hii|helo|good morning|good evening)\b", q):
            return {
                "question": question,
                "answer": "Hello! 👋 I can help you with tracking shipments, pricing, and delivery info.",
                "sources": [],
                "found_in_kb": False
            }

        # Tracking
        tracking_id = extract_tracking_id(question)
        if tracking_id:
            return {
                "question": question,
                "answer": handle_tracking(tracking_id),
                "sources": [],
                "found_in_kb": False
            }

        # Pricing
        weight = extract_weight(question)
        if any(word in q for word in ["cost", "price", "charge", "fee"]) and weight:
            return {
                "question": question,
                "answer": handle_price(weight),
                "sources": [],
                "found_in_kb": False
            }


        LOGISTICS_KEYWORDS = [
            "shipment", "delivery", "track", "tracking", "parcel",
            "logistics", "courier", "price", "cost", "kg",
            "pickup", "cargo", "shipping",
            "package", "delay", "delayed", "failed", "order"
        ]

        if not any(word in q for word in LOGISTICS_KEYWORDS):
            return {
                "question": question,
                "answer": "Sorry, I can only help with CargoFlow logistics queries.",
                "sources": [],
                "found_in_kb": False
            }


        sources = retrieve(question, self.index, self.chunks, self.model, top_k)

        if not sources:
            return {
                "question": question,
                "answer": "Sorry, I couldn’t find relevant information in CargoFlow knowledge base.",
                "sources": [],
                "found_in_kb": False
            }

        context = "\n\n".join([c for c, _ in sources])


        if len(context) < 50:
            return {
                "question": question,
                "answer": "Sorry, I can only answer based on CargoFlow knowledge base.",
                "sources": [],
                "found_in_kb": False
            }

        answer = call_llm(context, question)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "found_in_kb": True
        }

    def rebuild(self):
        self.index, self.chunks, self.model = build_and_save()