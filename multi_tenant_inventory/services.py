from fastapi import Depends, HTTPException
from psycopg import Connection
from typing import List, Dict
import hashlib
from datetime import datetime, timedelta

# Import from db_utils instead of app
from multi_tenant_inventory.db_utils import get_db, get_shard_id

from pydantic import BaseModel

class Product(BaseModel):
    id: int
    name: str
    quantity: int

class Anomaly:
    def __init__(self, id: int, product_id: int, timestamp: datetime, description: str):
        self.id = id
        self.product_id = product_id
        self.timestamp = timestamp
        self.description = description

async def track_product(tenant_id: str, product: Product, db: Connection = Depends(get_db)):
    """Track product movement for a specific tenant"""
    try:
        async with db.cursor() as cur:
            await cur.execute(
                f"INSERT INTO tenant_{tenant_id}.product_tracking (tenant_id, product_id, product_name, quantity) VALUES (%s, %s, %s, %s)",
                (tenant_id, product.id, product.name, product.quantity)
            )
        await db.commit()  # Explicitly commit the transaction
        return {"message": "Product tracked successfully"}
    except Exception as e:
        await db.rollback()  # Rollback in case of an error
        raise HTTPException(status_code=500, detail=str(e))

async def detect_anomaly(tenant_id: str, product_id: int, description: str, db: Connection = Depends(get_db)):
    """Detect anomalies in product movement"""
    try:
        async with db.cursor() as cur:
            # This is a simplified anomaly detection. In a real-world scenario,
            # you'd implement more sophisticated algorithms.
            await cur.execute(
                "SELECT SUM(quantity) FROM product_tracking WHERE tenant_id = %s AND product_id = %s",
                (tenant_id, product_id)
            )
            total_quantity = await cur.fetchone()

            if total_quantity and total_quantity[0] < 0:
                anomaly = Anomaly(
                    id=hashlib.md5(f"{tenant_id}:{product_id}:{datetime.now()}".encode()).hexdigest(),
                    product_id=product_id,
                    timestamp=datetime.now(),
                    description=description
                )
                await cur.execute(
                    "INSERT INTO anomalies (id, tenant_id, product_id, timestamp, description) VALUES (%s, %s, %s, %s, %s)",
                    (anomaly.id, tenant_id, anomaly.product_id, anomaly.timestamp, anomaly.description)
                )
                return {"message": "Anomaly detected and recorded", "description": description}

        return {"message": "No anomalies detected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_product_inventory(tenant_id: str, db: Connection = Depends(get_db)):
    """Get current inventory for a tenant"""
    try:
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT product_id, product_name, SUM(quantity) FROM product_tracking WHERE tenant_id = %s GROUP BY product_id, product_name",
                (tenant_id,)
            )
            inventory = await cur.fetchall()
        return {"tenant_id": tenant_id, "inventory": inventory}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_anomalies(tenant_id: str, db: Connection = Depends(get_db)):
    """Get anomalies for a tenant"""
    try:
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT * FROM anomalies WHERE tenant_id = %s ORDER BY timestamp DESC",
                (tenant_id,)
            )
            anomalies = await cur.fetchall()
        return {"tenant_id": tenant_id, "anomalies": anomalies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def check_license(tenant_id: str, db: Connection = Depends(get_db)):
    """Check license status for a tenant"""
    try:
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT expiration_date, grace_period, status FROM licenses WHERE tenant_id = %s",
                (tenant_id,)
            )
            license_info = await cur.fetchone()
            if not license_info:
                return {"status": "invalid", "message": "No license found"}
            expiration_date, grace_period, status = license_info
            current_date = datetime.now().date()
            if status == "revoked":
                return {"status": "revoked", "message": "License has been revoked"}
            if current_date <= expiration_date:
                return {"status": "active", "message": "License is active"}
            elif current_date <= expiration_date + timedelta(days=grace_period):
                return {"status": "grace", "message": f"License in grace period. Expires in {(expiration_date + timedelta(days=grace_period) - current_date).days} days"}
            else:
                return {"status": "expired", "message": "License has expired"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def validate_license(tenant_id: str, db: Connection = Depends(get_db)):
    """Validate license before allowing access to services"""
    license_status = await check_license(tenant_id, db)
    if license_status["status"] not in ["active", "grace"]:
        raise HTTPException(status_code=403, detail=license_status["message"])
    return license_status
