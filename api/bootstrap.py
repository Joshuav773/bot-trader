from sqlmodel import select, Session

from api.db import engine
from api.models import User
from api.security import hash_password
from config.settings import ADMIN_EMAIL, ADMIN_PASSWORD


def ensure_single_admin_user() -> None:
    # Open a direct session for startup/bootstrapping
    with Session(engine) as session:
        existing_users = session.exec(select(User)).all()
        if existing_users:
            return  # Do not modify if any user exists; single-account policy
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            return
        user = User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), is_master=True)
        session.add(user)
        session.commit()
