import asyncio
from typing import Any, Optional
import mongomock
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from backend.core.config import settings
from backend.core.logger import logger

_mongo_client: Any = None
_mongo_db: Any = None
_is_mock: bool = False


class AsyncCursor:
    def __init__(self, sync_cursor):
        self._cursor = sync_cursor

    def sort(self, *args, **kwargs):
        self._cursor = self._cursor.sort(*args, **kwargs)
        return self

    def limit(self, n: int):
        self._cursor = self._cursor.limit(n)
        return self

    async def to_list(self, length: Optional[int] = None):
        items = list(self._cursor)
        return items[:length] if length is not None else items


class AsyncCollection:
    def __init__(self, sync_coll):
        self._coll = sync_coll

    async def insert_one(self, doc: dict):
        return self._coll.insert_one(doc)

    async def insert_many(self, docs: list):
        return self._coll.insert_many(docs)

    async def find_one(self, *args, **kwargs):
        return self._coll.find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        return AsyncCursor(self._coll.find(*args, **kwargs))

    async def update_one(self, *args, **kwargs):
        return self._coll.update_one(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        return self._coll.count_documents(*args, **kwargs)

    async def create_index(self, *args, **kwargs):
        try:
            return self._coll.create_index(*args, **kwargs)
        except Exception:
            return None


class AsyncDatabase:
    def __init__(self, sync_db):
        self._db = sync_db
        self.client = sync_db.client

    def __getattr__(self, name: str):
        return AsyncCollection(self._db[name])

    def __getitem__(self, name: str):
        return AsyncCollection(self._db[name])


async def connect_to_mongodb():
    global _mongo_client, _mongo_db, _is_mock
    if settings.USE_MOCK_DB or settings.ENVIRONMENT == "test":
        mock_client = mongomock.MongoClient()
        _mongo_client = mock_client
        _mongo_db = AsyncDatabase(mock_client[settings.MONGODB_DATABASE])
        _is_mock = True
        logger.info("Using in-memory mock MongoDB for test environment")
        await init_indexes(_mongo_db)
        return _mongo_db

    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=2000
        )
        await client.admin.command('ping')
        _mongo_client = client
        _mongo_db = client[settings.MONGODB_DATABASE]
        _is_mock = False
        logger.info(f"Connected to live MongoDB at {settings.MONGODB_URI}")
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB ({e}). Falling back to in-memory mock MongoDB...")
        mock_client = mongomock.MongoClient()
        _mongo_client = mock_client
        _mongo_db = AsyncDatabase(mock_client[settings.MONGODB_DATABASE])
        _is_mock = True

    await init_indexes(_mongo_db)
    return _mongo_db


async def close_mongodb_connection():
    global _mongo_client
    if _mongo_client and hasattr(_mongo_client, "close"):
        _mongo_client.close()
        logger.info("MongoDB connection closed")


def get_database():
    global _mongo_db
    if _mongo_db is None:
        raise RuntimeError("MongoDB is not initialized. Call connect_to_mongodb() first.")
    return _mongo_db


def is_mongodb_mock() -> bool:
    return _is_mock


async def init_indexes(db):
    try:
        await db.users.create_index("email", unique=True)
        await db.services.create_index("name", unique=True)
        await db.incidents.create_index("fingerprint")
        await db.incidents.create_index([("status", 1), ("detected_at", -1)])
        await db.evidence.create_index([("incident_id", 1), ("observed_at", -1)])
        await db.investigations.create_index([("incident_id", 1), ("created_at", -1)])
        await db.approvals.create_index([("incident_id", 1), ("status", 1)])
        await db.remediation_executions.create_index([("incident_id", 1), ("status", 1)])
        await db.audit_logs.create_index([("timestamp", -1), ("action", 1)])
    except Exception as e:
        logger.warning(f"Index creation notice: {e}")
