"""Первичное наполнение: схема, 7 брендов, товары и первый администратор."""

import os
from decimal import Decimal
from pathlib import Path
import pymysql
from sqlalchemy.engine import make_url
from app import app
from models import Brand, Category, Product, ProductSize, Admin, db
from utils import slugify
from catalog_constants import CLOTHING_SIZES, SHOE_SIZES


BRANDS = ["Maison Margiela", "Balenciaga", "Rick Owens", "Yohji Yamamoto", "Raf Simons", "Comme des Garçons", "Carol Christian Poell"]
PRODUCT_TYPES = [("Edition Coat", "outerwear"), ("Archive Trouser", "trousers"), ("Sculpted Sneaker", "shoes"), ("Studio Shirt", "shirts")]
# Порядок нужен и для новых товаров, и для разового переноса старых остатков.
# Учебные цены различаются по дизайнерам; это не заявленные розничные цены.
SEED_PRICES = {
    "Maison Margiela": (1280, 690, 795, 425),
    "Balenciaga": (2190, 1150, 1090, 790),
    "Rick Owens": (1890, 930, 1175, 620),
    "Yohji Yamamoto": (1650, 760, 680, 510),
    "Raf Simons": (1450, 850, 970, 580),
    "Comme des Garçons": (1320, 715, 640, 490),
    "Carol Christian Poell": (2890, 1480, 1590, 940),
}


def seed():
    """Повторный запуск добавляет недостающие записи, не сбрасывая существующие."""
    # Тот же schema.sql можно исполнить вручную в HeidiSQL.
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    with pymysql.connect(host=url.host, port=url.port or 3306, user=url.username, password=url.password, charset="utf8mb4", autocommit=True) as connection:
        with connection.cursor() as cursor:
            for statement in Path(__file__).with_name("schema.sql").read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    cursor.execute(statement)
    with app.app_context():
        categories = {}
        for _, category_slug in PRODUCT_TYPES:
            category = Category.query.filter_by(slug=category_slug).first()
            if not category:
                category = Category(name=category_slug.title(), slug=category_slug)
                db.session.add(category)
            categories[category_slug] = category
        db.session.flush()
        for brand_name in BRANDS:
            brand = Brand.query.filter_by(slug=slugify(brand_name)).first()
            if not brand:
                brand = Brand(name=brand_name, slug=slugify(brand_name), country="International", description="A considered study in silhouette, material and movement.")
                db.session.add(brand)
                db.session.flush()
            for offset, (kind, category_slug) in enumerate(PRODUCT_TYPES, 1):
                slug = slugify(f"{brand_name} {kind}")
                if not Product.query.filter_by(slug=slug).first():
                    product = Product(brand_id=brand.id, category_id=categories[category_slug].id, name=f"{brand_name} {kind}", slug=slug, price=Decimal(SEED_PRICES[brand_name][offset - 1]), description="A quiet, precise object designed for an intentional wardrobe.")
                    db.session.add(product)
                    db.session.flush()
                    for size in (SHOE_SIZES if category_slug == "shoes" else CLOTHING_SIZES):
                        db.session.add(ProductSize(product_id=product.id, size=size, stock=5 + offset))
        # Пароль записывается только при первом создании админа и не сбрасывается seed.
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            admin = Admin(email=email)
            admin.set_password(os.getenv("ADMIN_PASSWORD", "admin12345"))
            db.session.add(admin)
        db.session.commit()
        print(f"Seeded {Brand.query.count()} brands, {Product.query.count()} products and admin {email}")


if __name__ == "__main__":
    seed()
