"""
Initialize SQLite database with tables
"""
import asyncio
from app.services.database import init_db

async def main():
    """Initialize database"""
    await init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
