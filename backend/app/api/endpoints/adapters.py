import random
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas import schemas
from backend.app.models.models import Application, Payment, AuditLog
from backend.app.adapters.channel_adapter import WhatsAppAdapter, IVRAdapter
from backend.app.adapters.payment_adapter import MockPaymentAdapter

router = APIRouter()
wa_adapter = WhatsAppAdapter()

@router.post("/whatsapp/message")
async def receive_whatsapp_message(
    phone_number: str = Form(...),
    message_text: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Webhook simulation for WhatsApp incoming message.
    """
    response = await wa_adapter.receive_message(db, phone_number, message_text)
    return response

@router.post("/ivr/call")
def handle_ivr_call(
    caller_id: str = Form(...),
    app_no: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Webhook simulation for IVR status checking.
    """
    response = IVRAdapter.handle_call_status_check(db, caller_id, app_no)
    return response

@router.post("/payment/initiate", response_model=schemas.PaymentOut)
def initiate_payment(
    payload: schemas.PaymentInitiate,
    db: Session = Depends(get_db)
):
    """
    Initiates payment for an application.
    """
    app = db.query(Application).filter(Application.id == payload.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    tx_no, status = MockPaymentAdapter.initiate_payment(payload.amount, payload.payment_method)
    
    # Save Payment row
    payment = Payment(
        application_id=app.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        status=status,
        transaction_no=tx_no
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Log payment initiated
    audit = AuditLog(
        actor="citizen",
        action="PAYMENT_INITIATED",
        application_id=app.id,
        channel=app.channel,
        result="SUCCESS",
        metadata_json={"amount": payload.amount, "method": payload.payment_method}
    )
    db.add(audit)
    db.commit()

    # Update app state
    app_state = app.states
    if app_state:
        state_data = dict(app_state.state_data)
        state_data["payment_status"] = "INITIATED"
        state_data["payment_tx"] = tx_no
        app_state.state_data = state_data
        db.commit()

    return payment

@router.post("/payment/{payment_id}/confirm", response_model=schemas.PaymentOut)
def confirm_payment(
    payment_id: int,
    payload: schemas.PaymentConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirms/resolves an initiated payment transaction.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Evaluate mock status using adapter
    resolved_status, err = MockPaymentAdapter.process_payment_outcome(
        payment.transaction_no, outcome=payload.status
    )
    
    payment.status = resolved_status
    payment.error_message = err
    db.commit()

    # Update state machine payment tracker
    app = db.query(Application).filter(Application.id == payment.application_id).first()
    if app and app.states:
        app_state = app.states
        state_data = dict(app_state.state_data)
        state_data["payment_status"] = resolved_status
        app_state.state_data = state_data
        db.commit()

        # Log payment outcome
        audit = AuditLog(
            actor="payment_gateway",
            action=f"PAYMENT_{resolved_status}",
            application_id=app.id,
            channel=app.channel,
            result="SUCCESS" if resolved_status == "SUCCESS" else "FAILED",
            metadata_json={"error": err}
        )
        db.add(audit)
        db.commit()

        # Check if state machine can progress to SUBMISSION
        from backend.app.services.state_machine import StateMachineOrchestrator
        StateMachineOrchestrator.process_state_transition(db, app_state, app, {}, app.channel)

    return payment
