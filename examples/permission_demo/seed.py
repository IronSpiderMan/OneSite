#!/usr/bin/env python3
"""Seed the permission_demo database with comprehensive test data.

Creates users for each role plus sample records for every model,
so you can exercise every permission boundary through the API.

Usage:
    cd examples/permission_demo
    python seed.py          # fresh seed (deletes existing db)
    python seed.py --reset  # same as above
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure backend modules are importable
BACKEND_DIR = str(Path(__file__).resolve().parent / "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole
from app.models.public_article import PublicArticle
from app.models.member_only_post import MemberOnlyPost
from app.models.premium_content import PremiumContent
from app.models.admin_config import AdminConfig
from app.models.secret_config import SecretConfig
from app.models.user_profile import UserProfile
from app.core.security import get_password_hash

DB_PATH = Path(__file__).resolve().parent / "app.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


async def seed():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("🗑️  Removed existing database")

    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Created tables")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ──── Users ───────────────────────────────────────────────────
        users = [
            User(
                email="alice@example.com",
                full_name="Alice User",
                hashed_password=get_password_hash("password123"),
                role=UserRole.USER,
                is_active=True,
            ),
            User(
                email="bob@example.com",
                full_name="Bob Admin",
                hashed_password=get_password_hash("password123"),
                role=UserRole.ADMIN,
                is_active=True,
            ),
            User(
                email="carol@example.com",
                full_name="Carol Developer",
                hashed_password=get_password_hash("password123"),
                role=UserRole.DEVELOPER,
                is_active=True,
            ),
            User(
                email="inactive@example.com",
                full_name="Inactive User",
                hashed_password=get_password_hash("password123"),
                role=UserRole.USER,
                is_active=False,
            ),
        ]
        for u in users:
            session.add(u)
        await session.commit()
        for u in users:
            await session.refresh(u)
        print(f"✅ Created {len(users)} users")
        for u in users:
            status = "active" if u.is_active else "inactive"
            print(f"   [{status}]  {u.email}  ({u.role.value})  id={u.id}")

        # ──── PublicArticles (default rcud for all) ───────────────────
        articles = [
            PublicArticle(
                title="Getting Started Guide",
                content="Welcome to the platform! This guide covers the basics.",
                is_published=True,
            ),
            PublicArticle(
                title="Public Announcement",
                content="System maintenance scheduled for this weekend.",
                is_published=True,
            ),
            PublicArticle(
                title="Community Guidelines",
                content="Please follow these guidelines when posting.",
                is_published=True,
            ),
            PublicArticle(
                title="Unpublished Draft",
                content="This is a draft that is not yet published.",
                is_published=False,
            ),
        ]
        for a in articles:
            session.add(a)
        await session.commit()
        print(f"✅ Created {len(articles)} public articles")

        # ──── MemberOnlyPosts (user=r, admin=rcu, developer=rcud) ────
        posts = [
            MemberOnlyPost(
                title="Gold Member Benefits",
                content="Exclusive benefits for gold members include priority support.",
                member_level="gold",
            ),
            MemberOnlyPost(
                title="Silver Member Tips",
                content="Tips and tricks to get the most out of your membership.",
                member_level="silver",
            ),
            MemberOnlyPost(
                title="Member Lounge News",
                content="The member lounge has been renovated with new seating.",
                member_level="gold",
            ),
            MemberOnlyPost(
                title="Bronze Welcome",
                content="Welcome to our bronze tier members!",
                member_level="bronze",
            ),
        ]
        for p in posts:
            session.add(p)
        await session.commit()
        print(f"✅ Created {len(posts)} member-only posts")

        # ──── PremiumContent (admin+ only) ────────────────────────────
        premium_items = [
            PremiumContent(
                title="Advanced Trading Strategies",
                body="Detailed analysis of market trends and trading patterns.",
                price=99.99,
            ),
            PremiumContent(
                title="Executive Summary Q1",
                body="Financial results and projections for the quarter.",
                price=149.99,
            ),
            PremiumContent(
                title="Premium Research Report",
                body="In-depth industry analysis with expert commentary.",
                price=199.99,
            ),
        ]
        for c in premium_items:
            session.add(c)
        await session.commit()
        print(f"✅ Created {len(premium_items)} premium contents")

        # ──── AdminConfig (singleton, admin+ only) ────────────────────
        admin_cfg = AdminConfig(
            site_name="Permission Demo",
            max_upload_size=50,
            enable_registration=True,
        )
        session.add(admin_cfg)
        await session.commit()
        print("✅ Created admin config singleton")

        # ──── SecretConfig (singleton, developer only) ────────────────
        secret_cfg = SecretConfig(
            api_key="sk-demo-secret-key-12345",
            internal_url="https://internal.permission-demo.example.com",
            debug_mode=False,
        )
        session.add(secret_cfg)
        await session.commit()
        print("✅ Created secret config singleton")

        # ──── UserProfiles (user=rcu, admin=rcu, developer=rcud) ─────
        profiles_data = [
            {
                "display_name": "Alice User",
                "bio": "Just a regular user exploring the platform.",
                "phone": "555-0100",
                "ssn": "XXX-XX-0001",
                "internal_note": "Standard user, no special privileges.",
                "loyalty_points": 100,
            },
            {
                "display_name": "Bob Admin",
                "bio": "Platform administrator keeping things running.",
                "phone": "555-0101",
                "ssn": "XXX-XX-0002",
                "internal_note": "Admin user — can manage most resources.",
                "loyalty_points": 500,
            },
            {
                "display_name": "Carol Developer",
                "bio": "Senior developer with full system access.",
                "phone": "555-0102",
                "ssn": "XXX-XX-0003",
                "internal_note": "Developer — has unrestricted access.",
                "loyalty_points": 1000,
            },
        ]
        profiles = [UserProfile(**pd) for pd in profiles_data]
        for p in profiles:
            session.add(p)
        await session.commit()
        print(f"✅ Created {len(profiles)} user profiles")

    await engine.dispose()
    print("\n" + "=" * 60)
    print("🎉  Seed complete!")
    print("=" * 60)
    print()
    print("📋  Test accounts:")
    print("   alice@example.com     / password123   (user)")
    print("   bob@example.com       / password123   (admin)")
    print("   carol@example.com     / password123   (developer)")
    print("   inactive@example.com  / password123   (inactive user)")
    print()
    print("🔑  Permission boundaries to test:")
    print()
    print("   PublicArticle    — all roles: full crud")
    print("   MemberOnlyPost   — user=r | admin=cru | developer=crud")
    print("   PremiumContent   — admin+ only (visible_roles hides from users)")
    print("   AdminConfig      — admin+ only, singleton (visible_roles hides from users)")
    print("   SecretConfig     — developer only, singleton (visible_roles hides from others)")
    print("   UserProfile      — user=cru | admin=cru | developer=crud")
    print()
    print("   User field-level permissions:")
    print("     phone           — admin+ can read/write")
    print("     ssn             — developer can read only")
    print("     internal_note   — admin can update, developer full")
    print("     loyalty_points  — user can read only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed permission_demo database")
    parser.add_argument("--reset", action="store_true", help="Reset database (default)")
    args = parser.parse_args()
    asyncio.run(seed())
