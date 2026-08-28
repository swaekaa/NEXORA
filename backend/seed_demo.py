import asyncio
import uuid
import sys
import os

# Add the backend dir to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import AsyncSessionLocal
from app.models.merchant import Merchant
from app.models.buyer import Buyer
from app.models.product import Product
from app.models.policy import Policy

async def seed():
    async with AsyncSessionLocal() as session:
        # Create Buyer
        buyer_id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
        b = await session.get(Buyer, buyer_id)
        if not b:
            b = Buyer(
                id=buyer_id, 
                name="Demo Buyer Corp", 
                email="buyer@demo.com", 
                organization="Demo Org"
            )
            session.add(b)
            
        # Create Merchant
        merchant_id = uuid.UUID("987f6543-e21b-34c5-b678-426614174999")
        m = await session.get(Merchant, merchant_id)
        if not m:
            m = Merchant(
                id=merchant_id, 
                name="Demo Electronics Ltd", 
                email="merchant@demo.com"
            )
            session.add(m)
            
        # Create Product (if not exists for this merchant)
        from sqlalchemy import select
        existing_p = await session.execute(
            select(Product).where(Product.merchant_id == merchant_id).where(Product.sku == "DELL-24-IPS")
        )
        if not existing_p.scalar_one_or_none():
            p = Product(
                id=uuid.uuid4(), 
                merchant_id=merchant_id, 
                name="Dell 24 inch monitor", 
                description="1080p IPS panel office monitor", 
                sku="DELL-24-IPS", 
                price=15000.00, 
                currency="INR", 
                inventory=1000
            )
            session.add(p)
            
        # Create Policy
        existing_pol = await session.execute(
            select(Policy).where(Policy.merchant_id == merchant_id)
        )
        if not existing_pol.scalars().first():
            pol = Policy(
                id=uuid.uuid4(), 
                merchant_id=merchant_id, 
                name="Demo Policy", 
                minimum_price=10000.00,
                maximum_discount_percent=20.00,
                maximum_autonomous_transaction=500000.00,
                human_approval_required=False, 
                is_active=True
            )
            session.add(pol)

        await session.commit()
        print("✅ Seed successful! Buyer, Merchant, Product, and Policy created.")
        
if __name__ == "__main__":
    asyncio.run(seed())
