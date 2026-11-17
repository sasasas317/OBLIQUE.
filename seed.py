# Seed создаёт недостающие записи и не сбрасывает пароль администратора.
"""Первичное наполнение: схема, товары, аксессуары и первый администратор."""

import os
from decimal import Decimal
from pathlib import Path
import pymysql
from sqlalchemy.engine import make_url
from app import app
from models import Accessory, Admin, Brand, Category, Product, ProductImage, ProductSize, db
from utils import slugify


# NOTE: prices are approximate, verify on official brand sites before production use
# Этот набор содержит только девять украшений из исходного задания.
BRANDS = ["Chrome Hearts", "Maison Margiela", "Prada"]

JEWELRY = (
    {
        "id": 1,
        "brand": "Chrome Hearts",
        "name": "Baby Fat Cross Pendant",
        "price": Decimal("1000"),
        "category": "Jewelry",
        "description": "Cross pendant in .925 sterling silver with the brand's signature gothic styling.",
        "imageUrl": "/assets/chrome-hearts/baby-fat-cross-pendant.jpg",
    },
    {
        "id": 2,
        "brand": "Chrome Hearts",
        "name": "Paper Chain Bracelet",
        "price": Decimal("900"),
        "category": "Jewelry",
        "description": "Link bracelet in .925 sterling silver, one of the label's best-known chain designs.",
        "imageUrl": "/assets/chrome-hearts/paper-chain-bracelet.jpg",
    },
    {
        "id": 3,
        "brand": "Chrome Hearts",
        "name": "Dagger Ring",
        "price": Decimal("750"),
        "category": "Jewelry",
        "description": "Sterling silver ring with the dagger motif.",
        "imageUrl": "/assets/chrome-hearts/dagger-ring.jpg",
    },
    {
        "id": 4,
        "brand": "Chrome Hearts",
        "name": "Scroll Band Ring",
        "price": Decimal("600"),
        "category": "Jewelry",
        "description": "Sterling silver band ring with the scroll pattern.",
        "imageUrl": "/assets/chrome-hearts/scroll-band-ring.jpg",
    },
    {
        "id": 5,
        "brand": "Maison Margiela",
        "name": "Numerical Logo Ring",
        "price": Decimal("250"),
        "category": "Jewelry",
        "description": "Ring engraved with the house's signature numbers (0-23).",
        "imageUrl": "/assets/maison-margiela/numerical-logo-ring.jpg",
    },
    {
        "id": 6,
        "brand": "Maison Margiela",
        "name": "Numerical Logo Bracelet",
        "price": Decimal("300"),
        "category": "Jewelry",
        "description": "Bracelet featuring the Margiela numerical logo.",
        "imageUrl": "/assets/maison-margiela/numerical-logo-bracelet.jpg",
    },
    {
        "id": 7,
        "brand": "Prada",
        "name": "Eternal Gold Pendant Necklace",
        "price": Decimal("2000"),
        "category": "Jewelry",
        "description": "Gold pendant necklace from the Prada Fine Jewelry Eternal Gold collection with the triangle logo.",
        "imageUrl": "/assets/prada/eternal-gold-pendant-necklace.jpg",
    },
    {
        "id": 8,
        "brand": "Prada",
        "name": "Eternal Gold Ring",
        "price": Decimal("1500"),
        "category": "Jewelry",
        "description": "Gold ring from the Eternal Gold collection with the triangle logo.",
        "imageUrl": "/assets/prada/eternal-gold-ring.jpg",
    },
    {
        "id": 9,
        "brand": "Prada",
        "name": "Eternal Gold Earrings",
        "price": Decimal("1800"),
        "category": "Jewelry",
        "description": "Gold earrings from the Eternal Gold collection with the triangle logo.",
        "imageUrl": "/assets/prada/eternal-gold-earrings.jpg",
    },
)

# NOTE: prices are approximate, verify on official brand sites before production use
# Эти пять позиций создаются как аксессуары, а не как товары коллекции.
ACCESSORIES = (
    {
        "id": 10,
        "brand": "Chrome Hearts",
        "name": "See You In Tea Sunglasses",
        "price": Decimal("1200"),
        "category": "Accessories",
        "description": "Солнцезащитные очки Chrome Hearts с массивными дужками, украшенными серебряными деталями.",
        "imageUrl": "/assets/chrome-hearts/see-you-in-tea-sunglasses.jpg",
    },
    {
        "id": 11,
        "brand": "Maison Margiela",
        "name": "Four-Stitch Card Holder",
        "price": Decimal("250"),
        "category": "Accessories",
        "description": "Кожаный картхолдер с фирменной белой строчкой в четыре стежка.",
        "imageUrl": "/assets/maison-margiela/four-stitch-card-holder.jpg",
    },
    {
        "id": 12,
        "brand": "Prada",
        "name": "Saffiano Leather Card Holder",
        "price": Decimal("300"),
        "category": "Accessories",
        "description": "Картхолдер из кожи Saffiano с эмалированным металлическим логотипом-треугольником.",
        "imageUrl": "/assets/prada/saffiano-leather-card-holder.jpg",
    },
    {
        "id": 13,
        "brand": "Off-White",
        "name": "Industrial Belt",
        "price": Decimal("280"),
        "category": "Accessories",
        "description": "Ремень из жёлтой ленты с надписью INDUSTRIAL и металлической пряжкой, один из символов бренда.",
        "imageUrl": "/assets/off-white/industrial-belt.jpg",
    },
    {
        "id": 14,
        "brand": "Ray-Ban",
        "name": "Wayfarer RB2140",
        "price": Decimal("170"),
        "category": "Accessories",
        "description": "Классические солнцезащитные очки Wayfarer в оправе из ацетата.",
        "imageUrl": "/assets/ray-ban/wayfarer-rb2140.jpg",
    },
)

# Ссылки на изображения прежних аксессуаров обновляются отдельно от новых позиций.
ACCESSORY_IMAGES = {
    "See You In Tea Sunglasses": "https://th.bing.com/th/id/OIP.3lQF1YsMFylrJf1XF9Ud8gHaHa?w=174&h=180&c=7&r=0&o=7&pid=1.7&rm=3",
    "Four-Stitch Card Holder": "https://th.bing.com/th/id/OIP.UoTFM1kiRCTaBx5D--7-jwHaJQ?w=199&h=249&c=7&r=0&o=7&pid=1.7&rm=3",
    "Saffiano Leather Card Holder": "https://th.bing.com/th/id/OIP.0eMl2qiSZCqZtYplV0YVHQHaIa?w=199&h=226&c=7&r=0&o=7&pid=1.7&rm=3",
    "Industrial Belt": "https://th.bing.com/th/id/OIP.JAEpivhai3p8dRjv3p46rwHaIX?w=176&h=199&c=7&r=0&o=7&pid=1.7&rm=3",
    "Wayfarer RB2140": "https://th.bing.com/th/id/OIP.Bevyy_eo5Ct9c0QsYsTLjgHaDt?w=314&h=175&c=7&r=0&o=7&pid=1.7&rm=3",
    "Cemetery Cross Ring": "https://th.bing.com/th/id/OIP.mfazgxci6B-OpZf2YTLf7AHaJQ?w=162&h=203&c=7&r=0&o=7&pid=1.7&rm=3",
    "CH Plus Bracelet": "https://th.bing.com/th/id/R.21261eae8955d699310df75713b179e0?rik=K1XyxER7VpqTtQ&riu=http%3a%2f%2fypcollective.com%2fcdn%2fshop%2ffiles%2ftiny-ch-plus-bracelet-sapphire.jpg%3fv%3d1761860420&ehk=W925BE37%2f7rBLeTZeXHcIjj9m9hnWVwu8uNN9dUq1MA%3d&risl=&pid=ImgRaw&r=0",
    "Four Stitches Card Holder": "https://tse1.mm.bing.net/th/id/OIP.lKLSNtHVrHQS44ZvI0W-wQHaLH?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "Re-Nylon Bucket Hat": "https://media.johnlewiscontent.com/i/JohnLewis/114424702?fmt=auto&$background-off-white$",
    "Saffiano Card Holder": "https://media.neimanmarcus.com/f_auto,q_auto:low,ar_4:5,c_fill,dpr_2.0,w_790/01/nm_5052773_100426_a",
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
        # Для Product сохраняется единственная актуальная категория Jewelry.
        category = Category.query.filter_by(slug="jewelry").first()
        if not category:
            category = Category(name="Jewelry", slug="jewelry")
            db.session.add(category)
        db.session.flush()
        # Удаляем только пустую устаревшую категорию, не затрагивая товары.
        stale_category = Category.query.filter_by(slug="accessories").first()
        if stale_category and not stale_category.products:
            db.session.delete(stale_category)
            db.session.flush()
        # Украшения остаются обычными Product, чтобы работать с коллекцией и размерами.
        for brand_name in BRANDS:
            brand = Brand.query.filter_by(slug=slugify(brand_name)).first()
            if not brand:
                brand = Brand(name=brand_name, slug=slugify(brand_name), country="International", description="A considered study in silhouette, material and movement.")
                db.session.add(brand)
                db.session.flush()
            for data in (item for item in JEWELRY if item["brand"] == brand_name):
                slug = slugify(data["name"])
                if not Product.query.filter_by(slug=slug).first():
                    product_kwargs = {
                        "brand_id": brand.id,
                        "category_id": category.id,
                        "name": data["name"],
                        "slug": slug,
                        "price": data["price"],
                        "description": data["description"],
                    }
                    if not db.session.get(Product, data["id"]):
                        product_kwargs["id"] = data["id"]
                    product = Product(**product_kwargs)
                    db.session.add(product)
                    db.session.flush()
                    db.session.add(ProductSize(product_id=product.id, size="One size", stock=5))
                    db.session.add(ProductImage(product_id=product.id, path=data["imageUrl"].lstrip("/"), thumb_path=data["imageUrl"].lstrip("/"), is_primary=True))
        # Если аксессуар ранее ошибочно попал в products, сначала удаляем его запись.
        accessory_names = {item["name"] for item in ACCESSORIES}
        for product in Product.query.filter(Product.name.in_(accessory_names)).all():
            db.session.delete(product)
        db.session.flush()
        # Новые позиции task.md сохраняются в отдельной таблице accessories.
        for data in ACCESSORIES:
            brand = Brand.query.filter_by(slug=slugify(data["brand"])).first()
            if not brand:
                brand = Brand(name=data["brand"], slug=slugify(data["brand"]), country="International")
                db.session.add(brand)
                db.session.flush()
            accessory = Accessory.query.filter_by(name=data["name"]).first()
            if not accessory:
                accessory = Accessory(
                    name=data["name"],
                    price=data["price"],
                    image=data["imageUrl"],
                    description=data["description"],
                    designer=brand,
                )
                db.session.add(accessory)
        # Старым аксессуарам назначаются внешние ссылки из task.md.
        for name, image_url in ACCESSORY_IMAGES.items():
            accessory = Accessory.query.filter_by(name=name).first()
            if accessory:
                accessory.image = image_url
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
