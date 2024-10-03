import hashlib
import logging
from psycopg_pool import AsyncConnectionPool
from typing import Dict
from fastapi import HTTPException

# Initialize shard pools
shard_pools: Dict[int, AsyncConnectionPool] = {}

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_shard_id(tenant_id: str) -> int:
    """Get shard ID for a given tenant"""
    return int(hashlib.md5(tenant_id.encode()).hexdigest(), 16) % len(shard_pools)

async def get_db(tenant_id: str):
    """Get database connection for the given tenant"""
    shard_id = get_shard_id(tenant_id)
    logger.debug(f"Getting database connection for tenant {tenant_id} on shard {shard_id}")
    try:
        async with shard_pools[shard_id].connection() as conn:
            logger.debug(f"Acquired connection for tenant {tenant_id}")
            async with conn.transaction():
                logger.debug(f"Started transaction for tenant {tenant_id}")
                yield conn
                logger.debug(f"Transaction completed for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Error in database transaction for tenant {tenant_id}: {str(e)}")
        await conn.rollback()
        logger.debug(f"Transaction rolled back for tenant {tenant_id}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        logger.debug(f"Database connection closed for tenant {tenant_id}")

async def initialize_shard_pools(connection_strings: Dict[int, str]):
    """Initialize connection pools for each shard"""
    global shard_pools
    for shard_id, conn_string in connection_strings.items():
        logger.info(f"Initializing connection pool for shard {shard_id}")
        shard_pools[shard_id] = AsyncConnectionPool(conn_string)
    logger.info("All shard connection pools initialized")

async def close_shard_pools():
    """Close all shard connection pools"""
    for shard_id, pool in shard_pools.items():
        logger.info(f"Closing connection pool for shard {shard_id}")
        await pool.close()
    logger.info("All shard connection pools closed")
