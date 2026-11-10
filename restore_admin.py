"""Set the local administrator password from .env after importing database_dump.sql."""

import os

from app import app
from models import Admin, db


def restore():
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("Set ADMIN_EMAIL and ADMIN_PASSWORD in .env before running restore_admin.py")
    with app.app_context():
        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            admin = Admin(email=email)
            db.session.add(admin)
        admin.set_password(password)
        db.session.commit()
    print("Local administrator credentials restored from .env")


if __name__ == "__main__":
    restore()
