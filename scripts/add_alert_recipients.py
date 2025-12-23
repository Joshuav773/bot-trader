"""
Script to add alert recipients (emails and phone numbers) to the database.

Usage:
    python scripts/add_alert_recipients.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import select, Session
from api.db import engine, create_db_and_tables
from api.models import AlertRecipient


def add_recipient(
    email: str = None,
    phone: str = None,
    name: str = None,
    email_enabled: bool = True,
    sms_enabled: bool = True,
) -> AlertRecipient:
    """Add a single recipient to the database."""
    with Session(engine) as session:
        # Check for duplicates
        if email:
            existing = session.exec(
                select(AlertRecipient).where(AlertRecipient.email == email)
            ).first()
            if existing:
                print(f"⚠ Email {email} already exists (ID: {existing.id})")
                return existing
        
        if phone:
            existing = session.exec(
                select(AlertRecipient).where(AlertRecipient.phone == phone)
            ).first()
            if existing:
                print(f"⚠ Phone {phone} already exists (ID: {existing.id})")
                return existing
        
        recipient = AlertRecipient(
            email=email,
            phone=phone,
            name=name,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
        )
        session.add(recipient)
        session.commit()
        session.refresh(recipient)
        
        print(f"✅ Added recipient: {recipient}")
        return recipient


def main():
    """Main function to add recipients."""
    print("=" * 70)
    print("📧 Adding Alert Recipients")
    print("=" * 70)
    print()
    
    # Create tables if needed
    create_db_and_tables()
    
    print("Enter recipient information. Press Enter to skip.")
    print()
    
    recipients = []
    
    # Add first email
    print("📧 Email Recipient #1:")
    email1 = input("  Email address: ").strip()
    name1 = input("  Name (optional): ").strip() or None
    if email1:
        recipient = add_recipient(email=email1, name=name1, sms_enabled=False)
        recipients.append(recipient)
    print()
    
    # Add second email
    print("📧 Email Recipient #2:")
    email2 = input("  Email address: ").strip()
    name2 = input("  Name (optional): ").strip() or None
    if email2:
        recipient = add_recipient(email=email2, name=name2, sms_enabled=False)
        recipients.append(recipient)
    print()
    
    # Add first phone
    print("📱 SMS Recipient #1:")
    phone1 = input("  Phone number (e.g., +1234567890 or 1234567890): ").strip()
    name3 = input("  Name (optional): ").strip() or None
    if phone1:
        # Clean phone number (remove spaces, dashes, etc.)
        phone1_clean = "".join(filter(str.isdigit, phone1.replace("+", "")))
        if not phone1_clean.startswith("1") and len(phone1_clean) == 10:
            phone1_clean = "1" + phone1_clean  # Add US country code if missing
        recipient = add_recipient(phone=phone1_clean, name=name3, email_enabled=False)
        recipients.append(recipient)
    print()
    
    # Add second phone
    print("📱 SMS Recipient #2:")
    phone2 = input("  Phone number (e.g., +1234567890 or 1234567890): ").strip()
    name4 = input("  Name (optional): ").strip() or None
    if phone2:
        # Clean phone number
        phone2_clean = "".join(filter(str.isdigit, phone2.replace("+", "")))
        if not phone2_clean.startswith("1") and len(phone2_clean) == 10:
            phone2_clean = "1" + phone2_clean
        recipient = add_recipient(phone=phone2_clean, name=name4, email_enabled=False)
        recipients.append(recipient)
    print()
    
    # Summary
    print("=" * 70)
    print("✅ Summary")
    print("=" * 70)
    
    with Session(engine) as session:
        all_recipients = session.exec(select(AlertRecipient)).all()
        print(f"\nTotal recipients in database: {len(all_recipients)}")
        print()
        
        emails = [r for r in all_recipients if r.email and r.email_enabled]
        phones = [r for r in all_recipients if r.phone and r.sms_enabled]
        
        print(f"📧 Email recipients ({len(emails)}):")
        for r in emails:
            print(f"   - {r.email} ({r.name or 'No name'})")
        
        print()
        print(f"📱 SMS recipients ({len(phones)}):")
        for r in phones:
            print(f"   - {r.phone} ({r.name or 'No name'})")
    
    print()
    print("=" * 70)
    print("✅ Done! Recipients are now configured to receive alerts.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

