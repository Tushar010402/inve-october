import hashlib
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg
from psycopg_pool import AsyncConnectionPool
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta
from . import services
from .services import track_product, detect_anomaly, get_product_inventory, get_anomalies, Product
from .db_utils import get_db, get_shard_id, initialize_shard_pools, close_shard_pools

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Sharding configuration
SHARD_COUNT = 3
shard_pools: Dict[int, AsyncConnectionPool] = {}

# Initialize connection pools for each shard
for shard_id in range(SHARD_COUNT):
    try:
        shard_pools[shard_id] = AsyncConnectionPool(f"postgres://user_ubsresmsag:O9O9qLi7smQUeogRXWOt@devinapps-backend-prod.cluster-clussqewa0rh.us-west-2.rds.amazonaws.com/db_fpfaynxpjd?sslmode=require")
    except Exception as e:
        print(f"Error initializing connection pool for shard {shard_id}: {str(e)}")
        shard_pools[shard_id] = None

def get_shard_id(tenant_id: str) -> int:
    """Determine shard ID based on tenant ID"""
    return int(hashlib.md5(tenant_id.encode()).hexdigest(), 16) % SHARD_COUNT

async def get_db(tenant_id: str):
    """Get database connection for the given tenant"""
    shard_id = get_shard_id(tenant_id)
    async with shard_pools[shard_id].connection() as conn:
        async with conn.cursor() as cur:
            try:
                schema_name = f"tenant_{tenant_id.replace('-', '_')}"
                await cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                await cur.execute(f"SET search_path TO {schema_name}, public")
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.product_tracking (
                        id SERIAL PRIMARY KEY,
                        tenant_id VARCHAR(255),
                        product_id INT,
                        product_name VARCHAR(255),
                        quantity INT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.anomalies (
                        id VARCHAR(255) PRIMARY KEY,
                        tenant_id VARCHAR(255),
                        product_id INT,
                        timestamp TIMESTAMP,
                        description TEXT
                    )
                """)
                await conn.commit()
                # Debug: Print current schema setting
                await cur.execute("SHOW search_path")
                current_schema = await cur.fetchone()
                print(f"Current schema for tenant {tenant_id}: {current_schema[0]}")
            except Exception as e:
                print(f"Error setting up schema and tables for tenant {tenant_id}: {str(e)}")
                await conn.rollback()
        yield conn

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/tenant")
async def register_tenant(tenant_data: dict):
    """Register a new tenant"""
    try:
        shard_id = get_shard_id(tenant_data['name'])  # Use tenant name as a unique identifier
        async with shard_pools[shard_id].connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO tenants (name, email) VALUES (%s, %s) RETURNING id", (tenant_data['name'], tenant_data['email']))
                tenant_id = await cur.fetchone()
        return {"tenant_id": tenant_id[0], "message": "Tenant registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tenant/{tenant_id}")
async def get_tenant_data(tenant_id: str, db: psycopg.Connection = Depends(get_db)):
    """Fetch data for a specific tenant"""
    try:
        async with db.cursor() as cur:
            await cur.execute("SELECT * FROM tenants WHERE id = %s", (tenant_id,))
            data = await cur.fetchone()
        if data:
            return {"tenant_id": tenant_id, "data": data}
        else:
            raise HTTPException(status_code=404, detail="Tenant not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    """Initialize database connections on startup"""
    connection_strings = {
        shard_id: f"postgres://user_ubsresmsag:O9O9qLi7smQUeogRXWOt@devinapps-backend-prod.cluster-clussqewa0rh.us-west-2.rds.amazonaws.com/db_fpfaynxpjd?sslmode=require"
        for shard_id in range(SHARD_COUNT)
    }
    await initialize_shard_pools(connection_strings)

@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown"""
    for pool in shard_pools.values():
        if pool is not None:
            await pool.close()

# New endpoints for product tracking and anomaly detection will be added below

@app.post("/tenant/{tenant_id}/track_product")
async def track_product(tenant_id: str, product: Product, db = Depends(get_db)):
    """Track a product for a specific tenant"""
    await services.validate_license(tenant_id, db)
    return await services.track_product(tenant_id, product, db)

@app.post("/tenant/{tenant_id}/detect_anomaly")
async def detect_anomaly(tenant_id: str, anomaly: dict, db = Depends(get_db)):
    """Detect anomalies in product movement for a specific tenant"""
    await services.validate_license(tenant_id, db)
    return await services.detect_anomaly(tenant_id, anomaly['product_id'], anomaly['description'], db)

@app.get("/tenant/{tenant_id}/inventory")
async def get_inventory(tenant_id: str, db = Depends(get_db)):
    """Get current inventory for a specific tenant"""
    await services.validate_license(tenant_id, db)
    return await services.get_product_inventory(tenant_id, db)

@app.get("/tenant/{tenant_id}/anomalies")
async def get_anomalies(tenant_id: str, db = Depends(get_db)):
    """Get detected anomalies for a specific tenant"""
    await services.validate_license(tenant_id, db)
    return await services.get_anomalies(tenant_id, db)
