"""Create a restorable SQL snapshot of all atelier tables for the public repo.

The dump keeps IDs and relationships, but replaces buyer contact details and
the administrator's password hash. Run restore_admin.py after importing it.
"""

import secrets
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pymysql.converters import escape_string
from werkzeug.security import generate_password_hash

from app import app
from models import Admin, AdminLog, Brand, Category, Order, OrderItem, Product, ProductImage, ProductSize, db


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "database_dump.sql"


def sql_value(value):
    """Format a value as a MariaDB SQL literal (including Unicode text)."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        value = value.strftime("%Y-%m-%d %H:%M:%S")
    return "'" + escape_string(str(value)) + "'"


def insert_rows(model, columns, transform=None):
    rows = db.session.query(model).order_by(model.id).all()
    table = model.__tablename__
    result = [f"-- {table}: {len(rows)} rows"]
    names = ", ".join(f"`{column}`" for column in columns)
    for row in rows:
        values = {column: getattr(row, column) for column in columns}
        if transform:
            transform(values)
        serialized = ", ".join(sql_value(values[column]) for column in columns)
        result.append(f"INSERT INTO `{table}` ({names}) VALUES ({serialized});")
    return result


def anonymize_order(values):
    """Preserve order totals/status, remove buyer contact information."""
    values["customer_name"] = f"Покупатель #{values['id']}"
    values["email"] = f"buyer-{values['id']}@example.invalid"
    values["phone"] = None
    values["address"] = "Адрес скрыт"


def anonymize_admin(values):
    """Do not publish a usable password hash for the local administrator."""
    values["password_hash"] = generate_password_hash(secrets.token_urlsafe(48))
    values["last_login"] = None


def export():
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8").rstrip()
    lines = [
        "-- OBLIQUE: полный снимок девяти таблиц atelier для публичного репозитория.",
        "-- Личные данные покупателей и пароль администратора заменены.",
        "-- Импортируйте в ПУСТУЮ базу: HeidiSQL -> Файл -> Загрузить SQL-файл -> F9.",
        "-- После импорта запустите python restore_admin.py для задания локального пароля.",
        "-- Не импортируйте поверх существующих записей: их ID совпадают.",
        schema,
        "",
        "START TRANSACTION;",
    ]
    with app.app_context():
        for model, columns, transform in (
            (Brand, ("id", "name", "slug", "country", "description", "logo_path"), None),
            (Category, ("id", "name", "slug"), None),
            (Product, ("id", "brand_id", "category_id", "name", "slug", "price", "description", "status", "created_at"), None),
            (ProductImage, ("id", "product_id", "path", "thumb_path", "position", "is_primary"), None),
            (ProductSize, ("id", "product_id", "size", "stock"), None),
            (Order, ("id", "customer_name", "email", "phone", "address", "total", "status", "created_at"), anonymize_order),
            (OrderItem, ("id", "order_id", "product_id", "product_name", "size", "quantity", "unit_price"), None),
            (Admin, ("id", "email", "password_hash", "created_at", "last_login"), anonymize_admin),
            (AdminLog, ("id", "admin_id", "action", "entity", "entity_id", "created_at"), None),
        ):
            lines.extend(insert_rows(model, columns, transform))
    lines.extend(("COMMIT;", ""))
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported all nine tables to {OUTPUT.name}")


if __name__ == "__main__":
    export()
