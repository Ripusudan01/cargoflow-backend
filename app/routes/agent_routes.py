from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import requests
from ..database import get_db
from ..models import *
from ..auth import require_role
from ..schemas import LocationUpdate, AgentUpdateShipmentStatus, DutyStatusUpdate

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Routes"])


# ---------------- DASHBOARD ----------------

@router.get("/dashboard", status_code=200)
def agent_dashboard(db: Session = Depends(get_db),
                    current_user: User = Depends(require_role(UserRole.DELIVERY_AGENT))):

    total_assigned = db.query(Shipment).filter(
        Shipment.assigned_agent_id == current_user.id
    ).count()

    completed = db.query(Shipment).filter(
        Shipment.assigned_agent_id == current_user.id,
        Shipment.status == ShipmentStatus.DELIVERED
    ).count()

    pending = db.query(Shipment).filter(
        Shipment.assigned_agent_id == current_user.id,
        Shipment.status.in_([
            ShipmentStatus.ASSIGNED,
            # ShipmentStatus.OUT_FOR_DELIVERY,
            # ShipmentStatus.CREATED
        ])
    ).count()

    earnings = db.query(func.sum(Shipment.price)).filter(
        Shipment.assigned_agent_id == current_user.id,
        Shipment.payment_status == PaymentStatus.PAID
    ).scalar() or 0

    # active_shipment = db.query(Shipment).filter(
    #     Shipment.assigned_agent_id == current_user.id,
    #     Shipment.status.in_([
    #         ShipmentStatus.ASSIGNED,
    #         ShipmentStatus.OUT_FOR_DELIVERY
    #     ])
    # ).order_by(Shipment.updated_at.desc()).first()
    active_shipment = db.query(Shipment).filter(
    Shipment.assigned_agent_id == current_user.id,
    Shipment.status == ShipmentStatus.OUT_FOR_DELIVERY
).first()

    active_delivery = None

    if active_shipment:
        progress_map = {
            ShipmentStatus.CREATED: 10,
            ShipmentStatus.ASSIGNED: 40,
            ShipmentStatus.OUT_FOR_DELIVERY: 80,
            ShipmentStatus.DELIVERED: 100
        }

        active_delivery = {
            "tracking_id": active_shipment.tracking_number,
            "status": active_shipment.status.value,
            "progress": progress_map.get(active_shipment.status, 0),

            "customer": {
                "name": active_shipment.receiver_name,
                "phone": active_shipment.receiver_phone
            },

            "pickup_address": {
                "line": active_shipment.pickup_address.line1 if active_shipment.pickup_address else None,
                "city": active_shipment.pickup_address.city if active_shipment.pickup_address else None,
                "pincode": active_shipment.pickup_address.pincode if active_shipment.pickup_address else None,
                "latitude": active_shipment.pickup_address.latitude if active_shipment.pickup_address else None,
                "longitude": active_shipment.pickup_address.longitude if active_shipment.pickup_address else None
            },

            "delivery_address": {
                "line": active_shipment.delivery_address.line1 if active_shipment.delivery_address else None,
                "city": active_shipment.delivery_address.city if active_shipment.delivery_address else None,
                "pincode": active_shipment.delivery_address.pincode if active_shipment.delivery_address else None,
                "latitude": active_shipment.delivery_address.latitude if active_shipment.delivery_address else None,
                "longitude": active_shipment.delivery_address.longitude if active_shipment.delivery_address else None
            },

            "package": {
                "weight": active_shipment.weight,
                "price": active_shipment.price
            },

            "eta": active_shipment.eta_end_time
        }

    # ---------------- METRICS ----------------

    total_distance = 0
    rating = 4.8

    shipments = db.query(Shipment).filter(
        Shipment.assigned_agent_id == current_user.id
    ).order_by(Shipment.updated_at.desc()).all()

    shipment_list = []

    for s in shipments:
       shipment_list.append({
    "id": s.id,
    "tracking_number": s.tracking_number,
    "receiver_name": s.receiver_name,
    "receiver_phone": s.receiver_phone,

    "status": s.status.value,

    "weight": s.weight,
    "price": s.price,

    "pickup_address": {
        "line": s.pickup_address.line1 if s.pickup_address else None,
        "city": s.pickup_address.city if s.pickup_address else None,
        "latitude": s.pickup_address.latitude if s.pickup_address else None,
        "longitude": s.pickup_address.longitude if s.pickup_address else None
    },

    "delivery_address": {
        "line": s.delivery_address.line1 if s.delivery_address else None,
        "city": s.delivery_address.city if s.delivery_address else None,
        "latitude": s.delivery_address.latitude if s.delivery_address else None,
        "longitude": s.delivery_address.longitude if s.delivery_address else None
    }
})

    return {
        "agent": {
            "name": current_user.name,
            "phone": current_user.phone,
            "duty_status": current_user.duty_status.value,
            "pending_duty_status": current_user.pending_duty_status.value if current_user.pending_duty_status else None
        },
        "summary": {
            "completed": completed,
            "pending": pending,
            "total": total_assigned,
            "earnings": earnings,
            "distance": total_distance,
            "rating": rating
        },
        "active_delivery": active_delivery,
        "shipments": shipment_list
    }


# ---------------- UPDATE SHIPMENT STATUS ----------------

@router.patch("/shipments/{id}/status")
def update_shipment_status(id: int,
                           data: AgentUpdateShipmentStatus,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(require_role(UserRole.DELIVERY_AGENT))):

    shipment = db.query(Shipment).filter(Shipment.id == id).first()

    if not shipment:
        raise HTTPException(404, "Shipment not found")

    if shipment.assigned_agent_id != current_user.id:
        raise HTTPException(403, "Not allowed")

    if shipment.status == ShipmentStatus.DELIVERED:
        raise HTTPException(400, "Shipment already completed")

    VALID_TRANSITIONS = {
        ShipmentStatus.ASSIGNED: [ShipmentStatus.OUT_FOR_DELIVERY],
        ShipmentStatus.OUT_FOR_DELIVERY: [
            ShipmentStatus.DELIVERED,
            ShipmentStatus.FAILED
        ],
    }
    if data.status == ShipmentStatus.OUT_FOR_DELIVERY:
        existing_active = db.query(Shipment).filter(
            Shipment.assigned_agent_id == current_user.id,
            Shipment.status == ShipmentStatus.OUT_FOR_DELIVERY
        ).first()

        if existing_active:
            raise HTTPException(400, "Complete current delivery first")

    if shipment.status not in VALID_TRANSITIONS or data.status not in VALID_TRANSITIONS[shipment.status]:
        raise HTTPException(400, "Invalid status transition")

    shipment.status = data.status

    # -------- PAYMENT --------

    if data.status == ShipmentStatus.DELIVERED:
        if shipment.payment_status == PaymentStatus.PAID:
            raise HTTPException(400, "Payment already completed")

        if not data.payment_method:
            raise HTTPException(400, "Payment method required")

        shipment.payment_status = PaymentStatus.PAID
        shipment.payment_method = data.payment_method

    elif data.status == ShipmentStatus.FAILED:
        shipment.payment_status = PaymentStatus.FAILED

    # -------- LOG --------

    db.add(ShipmentStatusLog(
        shipment_id=shipment.id,
        status=data.status,
        updated_by=current_user.id,
        remarks=data.remarks
    ))

    # -------- TRACKING --------

    # if current_user.current_lat and current_user.current_lng:
    #     db.add(TrackingUpdate(
    #         shipment_id=shipment.id,
    #         agent_id=current_user.id,
    #         latitude=current_user.current_lat,
    #         longitude=current_user.current_lng,
    #         status=data.status
    #     ))

    db.commit()
    db.refresh(shipment)

    return {"message": "Shipment Status updated successfully"}


# ---------------- UPDATE LOCATION ----------------
def get_lat_lng_from_pincode(pincode: str):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "postalcode": pincode,
        "countrycodes": "in",
        "format": "json",
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "CargoFlow-App"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None, None
    
    if not data:
        return None, None

    lat = float(data[0]["lat"])
    lng = float(data[0]["lon"])

    return lat, lng


@router.post("/update/live-location")
def update_location(data: LocationUpdate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(require_role(UserRole.DELIVERY_AGENT))):

    lat, lng = get_lat_lng_from_pincode(data.pincode)

    if lat is None or lng is None:
        raise HTTPException(400, "Invalid pincode")

    current_user.current_lat = lat
    current_user.current_lng = lng
    current_user.last_location_update = datetime.now(timezone.utc)

    if data.shipment_id is not None:
        shipment = db.query(Shipment).filter(Shipment.id == data.shipment_id).first()

        if not shipment:
            raise HTTPException(404, "Shipment not found")

        if shipment.assigned_agent_id != current_user.id:
            raise HTTPException(403, "Not assigned")

        db.add(TrackingUpdate(
            shipment_id=data.shipment_id,
            agent_id=current_user.id,
            latitude=lat,
            longitude=lng,
            status=shipment.status
        ))

    db.commit()

    return {
        "message": "Location updated via pincode",
        "lat": lat,
        "lng": lng
    }


# ---------------- DUTY STATUS ----------------

@router.patch("/update/duty-status")
def request_duty_status_update(data: DutyStatusUpdate,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(require_role(UserRole.DELIVERY_AGENT))):

    if current_user.pending_duty_status:
        raise HTTPException(400, "Duty status request already pending")

    if current_user.duty_status == data.status:
        raise HTTPException(400, "Already in this duty status")

    current_user.pending_duty_status = data.status

    db.commit()

    return {
        "message": "Duty status request sent for approval",
        "requested_status": data.status.value
    }