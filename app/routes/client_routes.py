from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..auth import require_role
from ..schemas import ClientShipmentCreate, BusinessCreate
from .admin_routes import generate_tracking_number
from app.utils.email import send_email

router = APIRouter(prefix="/api/v1/client", tags=["Client Routes"])

@router.get("/dashboard", status_code=200)
def client_dashboard(db: Session = Depends(get_db),
                     current_user: User = Depends(require_role(UserRole.BUSINESS_CLIENT))):

    # ------------------ COUNTS ------------------

    active_shipments = db.query(Shipment).filter(
        Shipment.sender_id == current_user.id,
        Shipment.status.in_([
            ShipmentStatus.CREATED,
            ShipmentStatus.ASSIGNED,
            ShipmentStatus.OUT_FOR_DELIVERY
        ])
    ).count()

    delivered = db.query(Shipment).filter(
        Shipment.sender_id == current_user.id,
        Shipment.status == ShipmentStatus.DELIVERED
    ).count()

    pending_pickup = db.query(Shipment).filter(
        Shipment.sender_id == current_user.id,
        Shipment.status == ShipmentStatus.CREATED
    ).count()

    open_invoices = db.query(func.sum(Shipment.price)).filter(
        Shipment.sender_id == current_user.id,
        Shipment.status != ShipmentStatus.DELIVERED
    ).scalar() or 0

    # ------------------ ACTIVE SHIPMENT ------------------

    active_shipment = db.query(Shipment)\
        .filter(
            Shipment.sender_id == current_user.id,
            Shipment.status != ShipmentStatus.DELIVERED
        )\
        .order_by(Shipment.created_at.desc())\
        .first()

    active_shipment_data = None

    if active_shipment:
        progress_map = {
            ShipmentStatus.CREATED: 10,
            ShipmentStatus.ASSIGNED: 40,
            ShipmentStatus.OUT_FOR_DELIVERY: 80,
            ShipmentStatus.DELIVERED: 100
        }

        progress = progress_map.get(active_shipment.status, 0)

        active_shipment_data = {
            "tracking_id": active_shipment.tracking_number,
            "origin": active_shipment.pickup_address.city,
            "destination": active_shipment.delivery_address.city,
            "status": active_shipment.status.value,
            "progress": progress,
            "eta": active_shipment.eta_end_time,
            "agent": active_shipment.assigned_agent.name if active_shipment.assigned_agent else None
        }

    # ------------------ DELIVERY TIMELINE ------------------

    timeline = []

    if active_shipment:
        logs = db.query(ShipmentStatusLog)\
            .filter(ShipmentStatusLog.shipment_id == active_shipment.id)\
            .order_by(ShipmentStatusLog.timestamp.asc())\
            .all()

        timeline = [
            {
                "status": log.status.value,
                "timestamp": log.timestamp,
                "remarks": log.remarks
            }
            for log in logs
        ]

    # ------------------ RECENT SHIPMENTS ------------------

    recent_shipments_query = db.query(Shipment)\
        .filter(Shipment.sender_id == current_user.id)\
        .order_by(Shipment.created_at.desc())\
        .limit(5)\
        .all()

    recent_shipments = []

    for s in recent_shipments_query:

        progress_map = {
            ShipmentStatus.CREATED: 10,
            ShipmentStatus.ASSIGNED: 40,
            ShipmentStatus.OUT_FOR_DELIVERY: 80,
            ShipmentStatus.DELIVERED: 100
        }

        recent_shipments.append({
            "tracking_id": s.tracking_number,
            "route": f"{s.pickup_address.city} → {s.delivery_address.city}",
            "agent": s.assigned_agent.name if s.assigned_agent else "Unassigned",
            "progress": progress_map.get(s.status, 0),
            "status": s.status.value,
            "eta": s.eta_end_time
        })

    business = current_user.owned_business or current_user.business
    business_data = None
    if business:
        business_data = {
            "id": business.id,
            "name": business.name,
            "type": business.type,
            "created_at": business.created_at
        }

    return {
        "business": business_data,
        "summary": {
            "active_shipments": active_shipments,
            "delivered": delivered,
            "pending_pickup": pending_pickup,
            "open_invoices": open_invoices
        },
        "active_shipment": active_shipment_data,
        "timeline": timeline,
        "recent_shipments": recent_shipments
    }

@router.post("/shipments", status_code=201)
def create_shipment(data: ClientShipmentCreate,
                    background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(require_role(UserRole.BUSINESS_CLIENT))):

    business = current_user.owned_business or current_user.business

    if not business:
        raise HTTPException(
            status_code=400,
            detail="Please create a business before creating shipment"
        )

    if data.weight <= 0 or data.price <= 0:
        raise HTTPException(400, "Invalid weight or price")

    if data.pickup_date and data.pickup_date < datetime.now(timezone.utc):
        raise HTTPException(400, "Pickup date cannot be in the past")

    pickup = Address(
        line1=data.pickup_line1,
        city=data.pickup_city,
        state=data.pickup_state,
        pincode=data.pickup_pincode,
        latitude=data.pickup_lat,
        longitude=data.pickup_lng
    )

    delivery = Address(
        line1=data.delivery_line1,
        city=data.delivery_city,
        state=data.delivery_state,
        pincode=data.delivery_pincode,
        latitude=data.delivery_lat,
        longitude=data.delivery_lng
    )

    db.add_all([pickup, delivery])
    db.flush()

    shipment = Shipment(
        tracking_number=generate_tracking_number(db),

        sender_id=current_user.id,

        receiver_name=data.receiver_name,
        receiver_phone=data.receiver_phone,
        receiver_email=data.receiver_email,

        pickup_address_id=pickup.id,
        delivery_address_id=delivery.id,

        weight=data.weight,
        price=data.price,

        category=business.type,
        fragile=data.fragile,
        pickup_date=data.pickup_date,
        priority=data.priority,

        status=ShipmentStatus.CREATED
    )

    db.add(shipment)
    db.flush()

    log = ShipmentStatusLog(
        shipment_id=shipment.id,
        status=ShipmentStatus.CREATED,
        updated_by=current_user.id,
        remarks="Shipment created by client",
        timestamp=datetime.utcnow()
    )

    db.add(log)

    db.commit()
    db.refresh(shipment)

    # ---------------- EMAIL PART ---------------- 

    html_content= f"""
        <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7fa; padding: 40px 20px; line-height: 1.6;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
            
            <div style="background-color: #0f172a; padding: 40px 30px; text-align: center; border-bottom: 4px solid #2563eb;">
                <span style="color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; text-transform: none;">
                    Cargo<span style="color: #2563eb;">Flow</span>
                </span>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px;">Smart Logistics for SMEs</p>
            </div>

            <div style="padding: 50px 40px;">
                <h2 style="color: #1e293b; margin-top: 0; font-size: 26px; font-weight: 700;">Shipment Created</h2>
                <p style="color: #64748b; font-size: 16px; margin-bottom: 30px;">
                    A new shipment has been successfully registered in our system. Below are the details for your reference.
                </p>

                <div style="background: #f8fafc; border-left: 4px solid #2563eb; padding: 25px; border-radius: 4px; margin: 30px 0;">
                    <table width="100%" cellspacing="0" cellpadding="0">
                        <tr>
                            <td colspan="2" style="padding-bottom: 15px;">
                                <div style="color: #475569; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Tracking ID</div>
                                <div style="color: #2563eb; font-size: 22px; font-weight: 800;">{shipment.tracking_number}</div>
                            </td>
                        </tr>
                        <tr>
                            <td style="width: 45%; padding-top: 10px;">
                                <div style="color: #94a3b8; font-size: 11px; text-transform: uppercase;">From</div>
                                <div style="color: #1e293b; font-weight: 600; font-size: 15px;">{pickup.city}</div>
                            </td>
                            <td style="width: 10%; padding-top: 15px; text-align: center; color: #cbd5e1; font-size: 20px;">➔</td>
                            <td style="width: 45%; padding-top: 10px; text-align: right;">
                                <div style="color: #94a3b8; font-size: 11px; text-transform: uppercase;">To</div>
                                <div style="color: #1e293b; font-weight: 600; font-size: 15px;">{delivery.city}</div>
                            </td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin-top: 40px;">
                    <a href="http://localhost:5173/" style="background-color: #2563eb; color: #ffffff; padding: 18px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);">
                        Track Shipment
                    </a>
                </div>
            </div>

            <div style="background-color: #f1f5f9; padding: 25px; text-align: center; border-top: 1px solid #e2e8f0;">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td align="center" style="width: 33%;">
                            <div style="font-weight: 800; color: #1e293b; font-size: 18px;">99.8%</div>
                            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Uptime</div>
                        </td>
                        <td align="center" style="width: 33%; border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1;">
                            <div style="font-weight: 800; color: #1e293b; font-size: 18px;">250K+</div>
                            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Delivered</div>
                        </td>
                        <td align="center" style="width: 33%;">
                            <div style="font-weight: 800; color: #1e293b; font-size: 18px;">24/7</div>
                            <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Support</div>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="padding: 30px; text-align: center; background-color: #0f172a;">
                <p style="font-size: 12px; color: #64748b; margin: 0;">
                    © 2026 CargoFlow Inc. All rights reserved.
                </p>
            </div>
        </div>
    </div>
    """
    background_tasks.add_task(
        send_email,
        current_user.email,
        f"Shipment {shipment.tracking_number} Created",
        html_content
    )

    if shipment.receiver_email and shipment.receiver_email.strip():
        background_tasks.add_task(
            send_email,
            shipment.receiver_email,
            f"You have a Shipment {shipment.tracking_number}",
            html_content
        )

    return {
        "tracking_number": shipment.tracking_number,
        "status": shipment.status.value,
        "sender": current_user.name,
        "receiver": shipment.receiver_name,
        "pickup_city": pickup.city,
        "delivery_city": delivery.city,
        "priority": shipment.priority.value,
        "fragile": shipment.fragile
    }

@router.get("/track/{tracking_id}", status_code=200)
def track_shipment_public(tracking_id: str,
                         db: Session = Depends(get_db)):

    if not tracking_id.startswith("CF-"):
        raise HTTPException(status_code=400, detail="Invalid tracking format")

    shipment = db.query(Shipment).filter(
        Shipment.tracking_number == tracking_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Invalid tracking ID")

    # ---------------- PROGRESS ----------------

    progress_map = {
        ShipmentStatus.CREATED: 10,
        ShipmentStatus.ASSIGNED: 40,
        ShipmentStatus.OUT_FOR_DELIVERY: 80,
        ShipmentStatus.DELIVERED: 100
    }

    progress = progress_map.get(shipment.status, 0)

    # ---------------- LIVE LOCATION ----------------

    latest_tracking = db.query(TrackingUpdate)\
        .filter(TrackingUpdate.shipment_id == shipment.id)\
        .order_by(TrackingUpdate.timestamp.desc())\
        .first()

    current_location = {
        "lat": latest_tracking.latitude,
        "lng": latest_tracking.longitude
    } if latest_tracking else None

    # ---------------- TIMELINE ----------------

    logs = db.query(ShipmentStatusLog)\
        .filter(ShipmentStatusLog.shipment_id == shipment.id)\
        .order_by(ShipmentStatusLog.timestamp.asc())\
        .all()

    timeline = [
        {
            "status": log.status.value,
            "timestamp": log.timestamp,
            "remarks": log.remarks
        }
        for log in logs
    ]

    pickup_address = shipment.pickup_address
    delivery_address = shipment.delivery_address

    return {
        "tracking_id": shipment.tracking_number,
        "status": shipment.status.value,
        "progress": progress,

        "current_location": current_location,

        "pickup_coords": {
            "lat": pickup_address.latitude if pickup_address else None,
            "lng": pickup_address.longitude if pickup_address else None
        },
        "delivery_coords": {
            "lat": delivery_address.latitude if delivery_address else None,
            "lng": delivery_address.longitude if delivery_address else None
        },

        "route": {
            "origin": pickup_address.city if pickup_address else None,
            "destination": delivery_address.city if delivery_address else None
        },

        "pickup_address": {
            "line1": pickup_address.line1 if pickup_address else None,
            "city": pickup_address.city if pickup_address else None
        },
        "delivery_address": {
            "line1": delivery_address.line1 if delivery_address else None,
            "city": delivery_address.city if delivery_address else None
        },

        "receiver_name": shipment.receiver_name,
        "receiver_phone": (
            "****" + shipment.receiver_phone[-4:]
            if shipment.receiver_phone else None
        ),

        "weight": shipment.weight,
        "price": shipment.price,
        "created_at": shipment.created_at,
        "eta": shipment.eta_end_time,

        "agent": {
            "name": shipment.assigned_agent.name if shipment.assigned_agent else "Not Assigned",
            "phone": shipment.assigned_agent.phone if shipment.assigned_agent else None
        },

        "timeline": timeline
    }

@router.get("/shipments", status_code=200)
def client_shipments(db: Session = Depends(get_db),
                     current_user: User = Depends(require_role(UserRole.BUSINESS_CLIENT))):

    shipments = db.query(Shipment)\
        .filter(Shipment.sender_id == current_user.id)\
        .order_by(Shipment.created_at.desc())\
        .all()

    # ------------------ COUNTS ------------------

    total = len(shipments)

    in_transit = sum(
        1 for s in shipments
        if s.status in [ShipmentStatus.ASSIGNED, ShipmentStatus.OUT_FOR_DELIVERY]
    )

    delivered = sum(
        1 for s in shipments
        if s.status == ShipmentStatus.DELIVERED
    )

    pending = sum(
        1 for s in shipments
        if s.status == ShipmentStatus.CREATED
    )

    delayed = sum(
        1 for s in shipments
        if s.status == ShipmentStatus.FAILED
    )

    # ------------------ TABLE DATA ------------------

    progress_map = {
        ShipmentStatus.CREATED: 10,
        ShipmentStatus.ASSIGNED: 40,
        ShipmentStatus.OUT_FOR_DELIVERY: 80,
        ShipmentStatus.DELIVERED: 100,
        ShipmentStatus.FAILED: 0
    }

    shipment_list = []

    for s in shipments:
        shipment_list.append({
            "tracking_id": s.tracking_number,
            "route": f"{s.pickup_address.city} → {s.delivery_address.city}",
            "agent": s.assigned_agent.name if s.assigned_agent else "Unassigned",
            "weight": f"{s.weight} kg",
            "price": s.price,
            "date": s.created_at,
            "progress": progress_map.get(s.status, 0),
            "status": s.status.value,
            "client": s.sender.business.name if s.sender and s.sender.business else "Business Client"
        })


    return {
        "counts": {
            "all": total,
            "in_transit": in_transit,
            "delivered": delivered,
            "pending": pending,
            "delayed": delayed
        },
        "shipments": shipment_list
    }

@router.post("/business", status_code=201)
def create_business(data: BusinessCreate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(require_role(UserRole.BUSINESS_CLIENT))):

    if current_user.business or current_user.owned_business:
        raise HTTPException(status_code=400, detail="User already has a business")

    business = Business(name=data.name,
                        type=data.type,
                        owner_id=current_user.id)

    db.add(business)
    db.flush()

    current_user.business_id = business.id

    db.commit()
    db.refresh(business)

    return {
        "message": "Business created successfully",
        "business_id": business.id,
        "name": business.name
    }

@router.put("/business", status_code=200)
def update_business(data: BusinessCreate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(require_role(UserRole.BUSINESS_CLIENT))):

    business = current_user.owned_business or current_user.business

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if data.name:
        business.name = data.name

    if data.type:
        business.type = data.type

    db.commit()
    db.refresh(business)

    return {
        "message": "Business updated successfully",
        "business_id": business.id,
        "name": business.name,
        "type": business.type
    }