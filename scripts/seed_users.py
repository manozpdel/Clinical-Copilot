"""Development utility that seeds a demo local user account."""

import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from auth.security import hash_password
from database.crud import create_user, get_user_by_email
from database.session import SessionLocal

_DEMO_EMAIL = "demo@clinicalcopilot.local"
_DEMO_PASSWORD = "demo-password-123"


async def seed_demo_user() -> None:
    """Create a demo user account if one does not already exist."""
    async with SessionLocal() as db:
        existing = await get_user_by_email(db, _DEMO_EMAIL)
        if existing is not None:
            print(f"Demo user already exists: {_DEMO_EMAIL}")
            return

        await create_user(
            db,
            email=_DEMO_EMAIL,
            hashed_password=hash_password(_DEMO_PASSWORD),
            full_name="Demo User",
            provider="local",
        )
        print(f"Seeded demo user: {_DEMO_EMAIL} / {_DEMO_PASSWORD}")


def main() -> None:
    """Seed the demo user account."""
    configure_logging()
    get_logger(__name__)
    get_settings()
    asyncio.run(seed_demo_user())


if __name__ == "__main__":
    main()
