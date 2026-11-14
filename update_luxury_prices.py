"""Обновить учебные цены каталога до реалистичного luxury-диапазона."""

from decimal import Decimal

from app import app
from models import Accessory, Product, db
from seed import ACCESSORIES, SEED_PRICES


def update_prices():
    """Обновить существующие записи по точным названиям и брендам."""
    with app.app_context():
        for brand_name, prices in SEED_PRICES.items():
            kinds = ("Edition Coat", "Archive Trouser", "Sculpted Sneaker", "Studio Shirt")
            for kind, price in zip(kinds, prices):
                product = Product.query.filter_by(name=f"{brand_name} {kind}").first()
                if product:
                    product.price = Decimal(str(price))

        for data in ACCESSORIES:
            accessory = Accessory.query.filter_by(name=data["name"]).first()
            if accessory:
                accessory.price = data["price"]

        db.session.commit()


if __name__ == "__main__":
    update_prices()
    print("Luxury prices updated")
