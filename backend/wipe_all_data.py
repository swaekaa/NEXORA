import asyncio
from sqlalchemy import delete
from app.database.connection import AsyncSessionLocal
from app.models.payment import Payment
from app.models.approval_request import ApprovalRequest
from app.models.audit_event import AuditEvent
from app.models.agreement import Agreement
from app.models.negotiation_message import NegotiationMessage
from app.models.negotiation import Negotiation
from app.models.inventory_reservation import InventoryReservation

async def wipe_all():
    async with AsyncSessionLocal() as session:
        try:
            print("Wiping Payments...")
            await session.execute(delete(Payment))
            
            print("Wiping Approval Requests...")
            await session.execute(delete(ApprovalRequest))
            
            print("Wiping Audit Events...")
            await session.execute(delete(AuditEvent))
            
            print("Wiping Inventory Reservations...")
            await session.execute(delete(InventoryReservation))
            
            print("Wiping Agreements...")
            await session.execute(delete(Agreement))
            
            print("Wiping Negotiation Messages...")
            await session.execute(delete(NegotiationMessage))
            
            print("Wiping Negotiations...")
            await session.execute(delete(Negotiation))
            
            await session.commit()
            print("All previous deals and negotiations have been successfully wiped from the database!")
        except Exception as e:
            await session.rollback()
            print(f"Failed to wipe data: {e}")

if __name__ == "__main__":
    asyncio.run(wipe_all())
