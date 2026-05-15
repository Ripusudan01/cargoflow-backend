from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base


# -------------------- ENUMS --------------------

class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    DELIVERY_AGENT = "DELIVERY_AGENT"
    BUSINESS_CLIENT = "BUSINESS_CLIENT"


class ShipmentStatus(enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETURN_TO_ORIGIN = "RETURN_TO_ORIGIN"

class PriorityLevel(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class AgentDutyStatus(enum.Enum):
    ON_DUTY = "ON_DUTY"
    OFF_DUTY = "OFF_DUTY"

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"

class PaymentMethod(enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"

# -------------------- Business --------------------

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_business"
    )

    users = relationship(
        "User",
        foreign_keys="User.business_id",
        back_populates="business",
        cascade="all, delete"
    )


# -------------------- User --------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    city = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.BUSINESS_CLIENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime, default=datetime.utcnow)
    duty_status = Column(Enum(AgentDutyStatus), default=AgentDutyStatus.ON_DUTY, nullable=True)
    pending_duty_status = Column(Enum(AgentDutyStatus), nullable=True)

    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    business = relationship("Business", foreign_keys=[business_id], back_populates="users")
    owned_business = relationship("Business", foreign_keys="Business.owner_id", back_populates="owner", uselist=False)

# -------------------- Address --------------------

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    line1 = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

# -------------------- Shipment --------------------

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    tracking_number = Column(String, unique=True, index=True, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_name = Column(String, nullable=False)
    receiver_phone = Column(String, nullable=False)
    receiver_email = Column(String)

    pickup_address_id = Column(Integer, ForeignKey("addresses.id", ondelete="CASCADE"), nullable=False)
    delivery_address_id = Column(Integer, ForeignKey("addresses.id", ondelete="CASCADE"), nullable=False)

    weight = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)

    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.CREATED, nullable=False)

    assigned_agent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    eta_start_time = Column(DateTime)
    eta_end_time = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    category = Column(String)
    fragile = Column(Boolean, default=False)
    pickup_date = Column(DateTime)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM)

    sender = relationship("User", foreign_keys=[sender_id])

    pickup_address = relationship("Address", foreign_keys=[pickup_address_id])
    delivery_address = relationship("Address", foreign_keys=[delivery_address_id])

    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])

    status_logs = relationship(
        "ShipmentStatusLog",
        back_populates="shipment",
        cascade="all, delete-orphan"
    )

    tracking_updates = relationship(
        "TrackingUpdate",
        back_populates="shipment",
        cascade="all, delete-orphan"
    )

    assignments = relationship(
        "ShipmentAssignment",
        back_populates="shipment",
        cascade="all, delete-orphan"
    )


# -------------------- Shipment Assignment --------------------

class ShipmentAssignment(Base):
    __tablename__ = "shipment_assignments"

    id = Column(Integer, primary_key=True)

    shipment_id = Column(
        Integer,
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agent_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    assigned_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="assignments")

    agent = relationship("User", foreign_keys=[agent_id])


# -------------------- Tracking Updates --------------------

class TrackingUpdate(Base):
    __tablename__ = "tracking_updates"

    id = Column(Integer, primary_key=True)

    shipment_id = Column(
        Integer,
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    agent_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    status = Column(Enum(ShipmentStatus), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    shipment = relationship("Shipment", back_populates="tracking_updates")

    agent = relationship("User")


# -------------------- Shipment Status Logs --------------------

class ShipmentStatusLog(Base):
    __tablename__ = "shipment_status_logs"

    id = Column(Integer, primary_key=True)

    shipment_id = Column(
        Integer,
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status = Column(Enum(ShipmentStatus), nullable=False)

    updated_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    remarks = Column(String)

    shipment = relationship("Shipment", back_populates="status_logs")

    updater = relationship("User")