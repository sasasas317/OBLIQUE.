"""ORM-модели: таблицы каталога, заказов и учётных записей администратора."""

from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class Brand(db.Model):
    """Дизайнер/бренд; связь products содержит его товары."""
    __tablename__ = "brands"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    country = db.Column(db.String(80))
    description = db.Column(db.Text)
    logo_path = db.Column(db.String(255))
    products = db.relationship("Product", back_populates="brand")


class Category(db.Model):
    """Категория каталога: обувь, верхняя одежда и т. д."""
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(140), nullable=False, unique=True, index=True)
    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    """Товар с ценой, статусом публикации, фото и размерами."""
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum("published", "hidden", name="product_status"), nullable=False, default="published", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    brand = db.relationship("Brand", back_populates="products")
    category = db.relationship("Category", back_populates="products")
    images = db.relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position")
    sizes = db.relationship("ProductSize", back_populates="product", cascade="all, delete-orphan", order_by="ProductSize.size")

    @property
    def available(self):
        """Общее число единиц на складе по всем размерам."""
        return sum(item.stock for item in self.sizes)

    @property
    def cover(self):
        """Главная фотография, либо первое фото по порядку загрузки."""
        return next((image for image in self.images if image.is_primary), self.images[0] if self.images else None)


class ProductImage(db.Model):
    """Пути относительно static/; миниатюра нужна для быстрого каталога."""
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    path = db.Column(db.String(255), nullable=False)
    thumb_path = db.Column(db.String(255))
    position = db.Column(db.Integer, default=0, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    product = db.relationship("Product", back_populates="images")


class ProductSize(db.Model):
    """Остаток конкретного размера; пара товар/размер уникальна."""
    __tablename__ = "product_sizes"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    size = db.Column(db.String(30), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    product = db.relationship("Product", back_populates="sizes")
    __table_args__ = (db.UniqueConstraint("product_id", "size", name="uq_product_size"),)


class Order(db.Model):
    """Заказ покупателя; total сохраняется на момент оформления."""
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    status = db.Column(db.Enum("new", "paid", "shipped", "delivered", "cancelled", name="order_status"), nullable=False, default="new", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    """Снимок названия, размера и цены товара на момент покупки."""
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name = db.Column(db.String(180), nullable=False)
    size = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")


class Admin(UserMixin, db.Model):
    """Администратор Flask-Login; пароль в БД хранится только в виде хэша."""
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AdminLog(db.Model):
    """Журнал действий администратора с типом сущности и её ID."""
    __tablename__ = "admin_logs"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"))
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    admin = db.relationship("Admin")
