# Цены обновляются только у существующих аксессуаров по точному названию.
"""Обновить учебные цены каталога до реалистичного luxury-диапазона."""

from decimal import Decimal

from app import app
from models import Accessory, Product, db
# Цены аксессуаров берутся из единого набора данных seed.py.
from seed import ACCESSORIES


def update_prices():
    """Обновить существующие записи по точным названиям и брендам."""
    with app.app_context():
        for data in ACCESSORIES:
            # Обновляем отдельную сущность аксессуара, а не товар коллекции.
            accessory = Accessory.query.filter_by(name=data["name"]).first()
            if accessory:
                accessory.price = data["price"]

        db.session.commit()


if __name__ == "__main__":
    update_prices()
    print("Luxury prices updated")
