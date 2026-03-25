"""
MongoDB connection module using Motor (async driver)
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from config.settings import settings


class Database:
    """MongoDB database connection manager"""

    client: AsyncIOMotorClient = None # type: ignore
    db = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            # Extract database name from URI or use default
            db_name = settings.MONGODB_URI.split("/")[-1].split("?")[0] or "eva_db"
            self.db = self.client[db_name]
            # Verify connection
            await self.client.admin.command("ping")
            print(f"[MongoDB] Connected to {db_name}")
            return True
        except ConnectionFailure as e:
            print(f"[MongoDB] Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("[MongoDB] Disconnected")

    async def health_check(self) -> bool:
        """Check if MongoDB connection is healthy"""
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False


# Singleton instance
database = Database()


# Helper function to get database instance
def get_db():
    """Get database instance"""
    return database.db
