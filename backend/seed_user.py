#!/usr/bin/env python3
"""
Seed script to add Otis Duncan with all roles
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_db_session
from app.models.user import User
from app.models import auth  # Import auth models to avoid relationship issues
from app.core.security import get_password_hash

async def seed_otis_duncan():
    """Seed Otis Duncan user with all roles."""
    
    # User data
    email = "otiseduncan@gmail.com"
    full_name = "Otis Duncan"
    password = "oed1234!"
    roles = "admin,shop_manager,field_manager,shop_cmr,mobile_cmr,shop_parts_manager,field_tech"
    
    print("🚀 Starting user seeding process...")
    
    try:
        async with get_db_session() as session:
            # Check if user already exists
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"✅ User {email} already exists, updating roles...")
                existing_user.roles = roles
                existing_user.is_superuser = True
                existing_user.is_active = True
                existing_user.is_verified = True
                await session.commit()
                await session.refresh(existing_user)
                print(f"✅ Updated user {email} with all roles!")
            else:
                print(f"➕ Creating new user {email}...")
                
                # Create new user
                user = User(
                    email=email,
                    full_name=full_name,
                    hashed_password=get_password_hash(password),
                    is_active=True,
                    is_superuser=True,
                    is_verified=True,
                    roles=roles
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                print(f"✅ Successfully created user {email} with all roles!")
            
            # Print user details
            print("\n📋 User Details:")
            print(f"   ID: {user.id if 'user' in locals() else existing_user.id}")
            print(f"   Email: {email}")
            print(f"   Full Name: {full_name}")
            print(f"   Active: {user.is_active if 'user' in locals() else existing_user.is_active}")
            print(f"   Superuser: {user.is_superuser if 'user' in locals() else existing_user.is_superuser}")
            print(f"   Verified: {user.is_verified if 'user' in locals() else existing_user.is_verified}")
            print(f"   Roles: {roles}")
            
            # Show available roles
            print("\n🎭 Available Roles:")
            for role in roles.split(','):
                print(f"   - {role}")
            
            print(f"\n🔐 Login Credentials:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"\n🎯 This user can now login as any of the above roles!")
            
    except Exception as e:
        print(f"❌ Error seeding user: {str(e)}")
        raise

async def main():
    """Main function."""
    print("🔧 Seeding Otis Duncan user with all roles...")
    await seed_otis_duncan()
    print("🏁 User seeding completed!")

if __name__ == "__main__":
    asyncio.run(main())