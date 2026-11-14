"""Публичная витрина: каталог, карточки, корзина и checkout."""

from decimal import Decimal
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from models import Accessory, Brand, Category, Order, OrderItem, Product, ProductSize, db
from catalog_constants import CLOTHING_SIZES, SHOE_SIZES

shop = Blueprint("shop", __name__)


def cart_items():
    """Собрать актуальные товары и аксессуары из session."""
    cart = session.get("cart", {})
    items, total = [], Decimal("0")
    for key, data in cart.items():
        quantity = data.get("quantity", 0)
        if data.get("type") == "accessory":
            accessory = db.session.get(Accessory, int(data["accessory_id"]))
            if accessory:
                line = accessory.price * quantity
                items.append({
                    "accessory": accessory,
                    "quantity": quantity,
                    "line": line,
                    "key": key,
                    "type": "accessory",
                })
                total += line
            continue

        product = db.session.get(Product, int(data["product_id"]))
        size = (
            ProductSize.query.filter_by(
                product_id=product.id,
                size=data["size"],
            ).first()
            if product
            else None
        )
        if product and size and product.status == "published":
            line = product.price * quantity
            items.append({
                "product": product,
                "size": size,
                "quantity": quantity,
                "line": line,
                "key": key,
                "type": "product",
            })
            total += line
    return items, total


@shop.get("/")
def home():
    """Главная показывает только опубликованные товары и бренды из БД."""
    brands = Brand.query.order_by(Brand.name).all()
    featured = Product.query.filter_by(status="published").order_by(Product.created_at.desc()).limit(8).all()
    return render_template("shop/home.html", brands=brands, products=featured)


@shop.get("/catalog")
def catalog():
    """Каталог применяет фильтры ORM-запросом, без ручной сборки SQL."""
    query = Product.query.filter_by(status="published")
    if request.args.get("brand"):
        query = query.join(Brand).filter(Brand.slug == request.args["brand"])
    if request.args.get("category"):
        query = query.join(Category).filter(Category.slug == request.args["category"])
    if request.args.get("q"):
        term = f"%{request.args['q']}%"
        query = query.filter(or_(Product.name.ilike(term), Product.description.ilike(term)))
    if request.args.get("max_price"):
        try:
            query = query.filter(Product.price <= Decimal(request.args["max_price"]))
        except (ValueError, ArithmeticError):
            pass
    if request.args.get("size"):
        query = query.join(ProductSize).filter(ProductSize.size == request.args["size"], ProductSize.stock > 0)
    return render_template("shop/catalog.html", products=query.order_by(Product.created_at.desc()).all(), brands=Brand.query.all(), categories=Category.query.all(), clothing_sizes=CLOTHING_SIZES, shoe_sizes=SHOE_SIZES)


@shop.get("/brand/<slug>")
def brand(slug):
    brand = Brand.query.filter_by(slug=slug).first_or_404()
    return render_template("shop/brand.html", brand=brand, products=Product.query.filter_by(brand_id=brand.id, status="published").all())


@shop.get("/product/<slug>")
def product(slug):
    item = Product.query.filter_by(slug=slug, status="published").first_or_404()
    return render_template("shop/product.html", product=item)


@shop.get("/accessories")
def accessories():
    """Показать аксессуары и применить серверный фильтр максимальной цены."""
    query = Accessory.query.order_by(Accessory.name)
    max_price = request.args.get("max_price", "").strip()
    if max_price:
        try:
            query = query.filter(Accessory.price <= Decimal(max_price))
        except (ValueError, ArithmeticError):
            max_price = ""
    return render_template(
        "shop/accessories.html",
        accessories=query.all(),
        max_price=max_price,
    )


@shop.get("/accessories/<int:accessory_id>")
def accessory_detail(accessory_id):
    """Показать отдельную страницу аксессуара из ORM-записи."""
    accessory = db.get_or_404(Accessory, accessory_id)
    return render_template("shop/accessory.html", accessory=accessory)


@shop.get("/cart")
def cart():
    items, total = cart_items()
    return render_template("shop/cart.html", items=items, total=total)


@shop.post("/api/cart")
def add_cart():
    """Добавить товар или аксессуар в корзину после серверной проверки."""
    payload = request.get_json(silent=True) or request.form
    try:
        quantity = int(payload.get("quantity", 1))
    except (ValueError, TypeError):
        return jsonify(error="Неверные параметры"), 400

    if quantity < 1:
        return jsonify(error="Неверное количество"), 400

    accessory_id = payload.get("accessory_id")
    if accessory_id:
        try:
            accessory_id = int(accessory_id)
        except (ValueError, TypeError):
            return jsonify(error="Неверные параметры"), 400
        accessory = db.session.get(Accessory, accessory_id)
        if not accessory:
            return jsonify(error="Аксессуар недоступен"), 400
        cart = session.setdefault("cart", {})
        key = f"accessory:{accessory.id}"
        desired = cart.get(key, {}).get("quantity", 0) + quantity
        cart[key] = {
            "type": "accessory",
            "accessory_id": accessory.id,
            "quantity": desired,
        }
        session.modified = True
        return jsonify(ok=True, count=sum(x["quantity"] for x in cart.values()))

    try:
        product_id = int(payload.get("product_id", 0))
    except (ValueError, TypeError):
        return jsonify(error="Неверные параметры"), 400
    product = db.session.get(Product, product_id)
    size = ProductSize.query.filter_by(product_id=product.id if product else 0, size=payload.get("size", "")).first()
    if not product or product.status != "published" or not size or quantity > size.stock:
        return jsonify(error="Товар или размер недоступен"), 400
    cart = session.setdefault("cart", {})
    key = f"{product.id}:{size.size}"
    desired = cart.get(key, {}).get("quantity", 0) + quantity
    if desired > size.stock:
        return jsonify(error="Недостаточно товара на складе"), 400
    cart[key] = {
        "type": "product",
        "product_id": product.id,
        "size": size.size,
        "quantity": desired,
    }
    session.modified = True
    return jsonify(ok=True, count=sum(x["quantity"] for x in cart.values()))


@shop.post("/api/cart/<key>")
def update_cart(key):
    """Изменить или удалить строку корзины через JSON/form POST."""
    cart = session.get("cart", {})
    if key not in cart:
        return jsonify(error="Позиция не найдена"), 404
    try:
        quantity = int((request.get_json(silent=True) or request.form).get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify(error="Неверное количество"), 400
    if quantity <= 0:
        cart.pop(key)
    elif cart[key].get("type") == "accessory":
        cart[key]["quantity"] = quantity
    else:
        size = ProductSize.query.filter_by(product_id=cart[key]["product_id"], size=cart[key]["size"]).first()
        if not size or quantity > size.stock:
            return jsonify(error="Недостаточно товара на складе"), 400
        cart[key]["quantity"] = quantity
    session.modified = True
    return jsonify(ok=True)


@shop.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Создать заказ и атомарно уменьшить остаток заблокированной строки размера."""
    items, total = cart_items()
    if not items:
        return redirect(url_for("shop.cart"))
    if request.method == "POST":
        form = request.form
        if not form.get("customer_name") or not form.get("email") or not form.get("address"):
            flash("Заполните обязательные поля", "error")
            return render_template("shop/checkout.html", items=items, total=total)
        order = Order(customer_name=form["customer_name"].strip(), email=form["email"].strip(), phone=form.get("phone"), address=form["address"].strip(), total=total)
        db.session.add(order)
        # FOR UPDATE защищает от ситуации, когда два checkout одновременно продают один остаток.
        for item in items:
            if item["type"] == "accessory":
                db.session.add(
                    OrderItem(
                        order=order,
                        accessory_id=item["accessory"].id,
                        product_name=item["accessory"].name,
                        size="One size",
                        quantity=item["quantity"],
                        unit_price=item["accessory"].price,
                    )
                )
                continue
            size = ProductSize.query.filter_by(product_id=item["product"].id, size=item["size"].size).with_for_update().one()
            if item["quantity"] > size.stock:
                db.session.rollback()
                flash("Остаток товара изменился, обновите корзину", "error")
                return redirect(url_for("shop.cart"))
            size.stock -= item["quantity"]
            db.session.add(OrderItem(order=order, product_id=item["product"].id, product_name=item["product"].name, size=item["size"].size, quantity=item["quantity"], unit_price=item["product"].price))
        db.session.commit()
        session.pop("cart", None)
        return render_template("shop/success.html", order=order)
    return render_template("shop/checkout.html", items=items, total=total)
