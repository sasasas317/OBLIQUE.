"""Первичное наполнение: схема, 7 брендов, товары и первый администратор."""

import os
from decimal import Decimal
from pathlib import Path
import pymysql
from sqlalchemy.engine import make_url
from app import app
from models import Accessory, Admin, Brand, Category, Product, ProductSize, db
from utils import slugify
from catalog_constants import CLOTHING_SIZES, SHOE_SIZES


BRANDS = ["Maison Margiela", "Balenciaga", "Rick Owens", "Yohji Yamamoto", "Raf Simons", "Comme des Garçons", "Carol Christian Poell"]
ACCESSORY_BRANDS = ["Chrome Hearts", "Prada"]
PRODUCT_TYPES = [("Edition Coat", "outerwear"), ("Archive Trouser", "trousers"), ("Sculpted Sneaker", "shoes"), ("Studio Shirt", "shirts")]
# Порядок нужен и для новых товаров, и для разового переноса старых остатков.
# Ориентировочные розничные цены в евро для luxury-сегмента.
SEED_PRICES = {
    "Maison Margiela": (3200, 1250, 980, 620),
    "Balenciaga": (4500, 2100, 1450, 950),
    "Rick Owens": (3900, 1800, 1650, 850),
    "Yohji Yamamoto": (3500, 1550, 1200, 760),
    "Raf Simons": (3100, 1700, 1350, 820),
    "Comme des Garçons": (2800, 1350, 1050, 690),
    "Carol Christian Poell": (5200, 2400, 2100, 1200),
}

# Узнаваемые модели и линейки реальных брендов; цены ориентировочные и нужны для демо-каталога.
ACCESSORIES = (
    {
        "brand": "Chrome Hearts",
        "name": "CH Plus Bracelet",
        "price": Decimal("3200"),
        "description": "Серебряный браслет с фирменным мотивом CH Plus.",
    },
    {
        "brand": "Chrome Hearts",
        "name": "Cemetery Cross Ring",
        "price": Decimal("2400"),
        "description": "Кольцо из стерлингового серебра с мотивом Cemetery Cross.",
    },
    {
        "brand": "Maison Margiela",
        "name": "Four Stitches Card Holder",
        "price": Decimal("680"),
        "description": "Кожаный кардхолдер с четырьмя белыми стежками Maison Margiela.",
    },
    {
        "brand": "Prada",
        "name": "Re-Nylon Bucket Hat",
        "price": Decimal("1150"),
        "description": "Лаконичная панама из фирменного переработанного Re-Nylon.",
    },
    {
        "brand": "Prada",
        "name": "Saffiano Card Holder",
        "price": Decimal("820"),
        "description": "Кардхолдер из фактурной кожи Saffiano с эмблемой Prada.",
    },
)


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

        # Бренды аксессуаров не получают одежду: они нужны только для связей карточек аксессуаров.
        accessory_brands = {}
        for brand_name in ACCESSORY_BRANDS:
            brand = Brand.query.filter_by(slug=slugify(brand_name)).first()
            if not brand:
                brand = Brand(
                    name=brand_name,
                    slug=slugify(brand_name),
                    country="International",
                    description="Signature accessories and considered objects.",
                )
                db.session.add(brand)
                db.session.flush()
            accessory_brands[brand_name] = brand

        for data in ACCESSORIES:
            if not Accessory.query.filter_by(name=data["name"]).first():
                db.session.add(
                    Accessory(
                        name=data["name"],
                        price=data["price"],
                        description=data["description"],
                        designer=accessory_brands.get(data["brand"])
                        or Brand.query.filter_by(name=data["brand"]).one(),
                    )
                )
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
