import os
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, init_db
from app.models.user import User, UserRole, AccountStatus
from app.models.address import Address, AddressType, LocationScope, AddressVisibility
from app.core.security import hash_password, hash_edit_id
from app.services.edit_id_service import EditIdService
from app.services.address_formatter import AddressFormatter
from app.core.logging import logger


def seed_database():
    """Seeds the database with default administrator and initial verification records."""
    init_db()
    db: Session = SessionLocal()
    try:
        # Check if an admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            dob = date(1985, 1, 1)
            raw_edit_id = EditIdService.generate_edit_id(
                public_id="ab1226",
                father_name="Muhammad",
                mother_name="Amina",
                cnic_or_id_card="786",
                date_of_birth=dob
            )
            admin = User(
                username="admin",
                email="admin@universaladdress.local",
                public_id="ab1226",
                full_name="Platform Administrator",
                father_name="Muhammad",
                mother_name="Amina",
                cnic_or_id_card="786",
                date_of_birth=dob,
                password_hash=hash_password("Admin123456!"),
                edit_id_hash=hash_edit_id(raw_edit_id),
                role=UserRole.SUPER_ADMIN,
                account_status=AccountStatus.ACTIVE,
                created_at=datetime.now(timezone.utc)
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info(f"Default admin user created: admin (Edit ID: {raw_edit_id})")

        # Check if demo address exists
        demo_addr = db.query(Address).filter(Address.public_id == "ab1226").first()
        if not demo_addr:
            demo_addr = Address(
                public_id="ab1226",
                user_id=admin.id,
                address_type="DELIVERY",
                location_scope="LOCAL",
                visibility="PUBLIC",
                recipient_name="Muhammad Bilal",
                country="Pakistan",
                country_code="PK",
                province_state="Punjab",
                region_division="Dera Ghazi Khan Division",
                district="Dera Ghazi Khan",
                tehsil="Taunsa Sharif",
                city="Taunsa Sharif",
                house_number="25",
                street="Street 4",
                landmark="Near Main Market",
                latitude=30.7031,
                longitude=70.6500,
                destination_url="https://www.google.com/maps/dir/?api=1&destination=30.7031,70.6500&travelmode=driving",
                redirect_seconds=3,
                is_active=True,
                address_text="House 25, Street 4, Near Main Market, Taunsa Sharif, Dera Ghazi Khan, Punjab, Pakistan"
            )
            db.add(demo_addr)
            db.commit()
            logger.info("Demo address created: ab1226")

        print("Database seeded successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
