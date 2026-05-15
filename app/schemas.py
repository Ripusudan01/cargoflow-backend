from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from .models import PriorityLevel, ShipmentStatus, AgentDutyStatus, PaymentMethod

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    city: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None

class DeliveryAgentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    city: str

class AdminShipmentCreate(BaseModel):
    sender_id: int
    receiver_name: str
    receiver_phone: str
    receiver_email: EmailStr

    pickup_line1: str
    pickup_city: str
    pickup_state: str
    pickup_pincode: str

    delivery_line1: str
    delivery_city: str
    delivery_state: str
    delivery_pincode: str

    pickup_lat: float
    pickup_lng: float
    delivery_lat: float
    delivery_lng: float

    weight: float
    price: float

    category: Optional[str] = None
    fragile: Optional[bool] = False
    pickup_date: Optional[datetime] = None
    priority: Optional[PriorityLevel] = PriorityLevel.MEDIUM

class ClientShipmentCreate(BaseModel):
    receiver_name: str
    receiver_phone: str
    receiver_email: EmailStr

    pickup_line1: str
    pickup_city: str
    pickup_state: str
    pickup_pincode: str

    delivery_line1: str
    delivery_city: str
    delivery_state: str
    delivery_pincode: str

    pickup_lat: float
    pickup_lng: float
    delivery_lat: float
    delivery_lng: float

    weight: float
    price: float

    category: Optional[str] = None
    fragile: Optional[bool] = False
    pickup_date: Optional[datetime] = None
    priority: Optional[PriorityLevel] = PriorityLevel.MEDIUM

class LocationUpdate(BaseModel):
    pincode: str
    shipment_id: Optional[int] = None

class BusinessCreate(BaseModel):
    name: str
    type: str

class AgentUpdateShipmentStatus(BaseModel):
    status: ShipmentStatus
    remarks: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None

class UpdateDeliveryAgent(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None

class UpdateClient(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None

class DutyStatusUpdate(BaseModel):
    status: AgentDutyStatus