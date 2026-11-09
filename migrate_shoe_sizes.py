"""Разовая идемпотентная замена буквенных размеров обуви на EU 39–43.

Меняем размер в той же строке product_sizes, поэтому складской остаток
сохраняется. Размеры, уже использованные в заказе, не переименовываем:
исторический заказ должен и дальше ссылаться на проданный размер.
"""

from app import app
from models import OrderItem, Product, ProductSize, db
from catalog_constants import CLOTHING_SIZES, SHOE_SIZES


def migrate():
    with app.app_context():
        shoes = Product.query.filter(Product.category.has(slug="shoes")).all()
        pending = []
        for product in shoes:
            sizes = {entry.size: entry for entry in product.sizes}
            for old, new in zip(CLOTHING_SIZES, SHOE_SIZES):
                entry = sizes.get(old)
                if entry is None:
                    continue
                if new in sizes:
                    raise ValueError(f"{product.name}: размеры {old} и {new} уже сосуществуют")
                if OrderItem.query.filter_by(product_id=product.id, size=old).first():
                    raise ValueError(f"{product.name}: размер {old} уже встречается в заказе")
                pending.append((entry, new))
        for entry, new in pending:
            entry.size = new
        db.session.commit()
        print(f"Updated {len(pending)} shoe sizes across {len(shoes)} products")


if __name__ == "__main__":
    migrate()
