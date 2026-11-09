"""Закрытая админка: CRUD каталога, изображения, заказы и отчёты."""

import csv
import io
import os
from datetime import datetime, timedelta
from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from models import Admin, AdminLog, Brand, Category, Order, OrderItem, Product, ProductImage, ProductSize, db
from utils import admin_log, save_image, slugify
from extensions import limiter

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Вход с общим сообщением об ошибке и лимитом 5 POST в минуту на IP."""
    if request.method == "POST":
        user = Admin.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=False)
            session.permanent = True
            next_url = request.args.get("next", "")
            return redirect(next_url if next_url.startswith("/") and not next_url.startswith("//") else url_for("admin.dashboard"))
        flash("Неверные данные для входа", "error")
    return render_template("admin/login.html")


@admin.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin.get("/", strict_slashes=False)
@login_required
def dashboard():
    """Сводка продаж, остатки, топ товаров и данные для SVG-графика."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    revenue = db.session.query(db.func.sum(Order.total)).filter(Order.status != "cancelled").scalar() or 0
    low_stock = [p for p in Product.query.all() if p.available < 3]
    periods = [("Сегодня", today), ("7 дней", today - timedelta(days=6)), ("30 дней", today - timedelta(days=29))]
    stats = [(label, Order.query.filter(Order.created_at >= start).count()) for label, start in periods]
    top = db.session.query(Product.name, func.sum(OrderItem.quantity).label("sold")).join(OrderItem, OrderItem.product_id == Product.id).join(Order, Order.id == OrderItem.order_id).filter(Order.status != "cancelled").group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    daily = db.session.query(func.date(Order.created_at), func.sum(Order.total)).filter(Order.created_at >= today - timedelta(days=29), Order.status != "cancelled").group_by(func.date(Order.created_at)).all()
    chart = [float(dict((str(date), value) for date, value in daily).get(str((today + timedelta(days=day)).date()), 0)) for day in range(-29, 1)]
    return render_template("admin/dashboard.html", orders=orders, revenue=revenue, low_stock=low_stock, product_count=Product.query.count(), stats=stats, top=top, chart=chart)


@admin.route("/brands", methods=["GET", "POST"])
@login_required
def brands():
    """Список и создание брендов; уникальность имени/slug контролирует БД."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            brand = Brand(name=name, slug=slugify(request.form.get("slug") or name), country=request.form.get("country"), description=request.form.get("description"))
            db.session.add(brand)
            admin_log("create", "brand")
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Название или slug уже существует", "error")
                return redirect(url_for("admin.brands"))
            flash("Бренд создан", "success")
        return redirect(url_for("admin.brands"))
    return render_template("admin/brands.html", brands=Brand.query.order_by(Brand.name).all())


@admin.route("/brands/<int:brand_id>/edit", methods=["GET", "POST"])
@login_required
def edit_brand(brand_id):
    brand = db.get_or_404(Brand, brand_id)
    if request.method == "POST":
        brand.name = request.form.get("name", "").strip()
        brand.slug = slugify(request.form.get("slug") or brand.name)
        brand.country = request.form.get("country", "").strip()
        brand.description = request.form.get("description", "").strip()
        if not brand.name or not brand.slug:
            flash("Укажите название и slug", "error")
        else:
            try:
                admin_log("update", "brand", brand.id)
                db.session.commit()
                flash("Бренд сохранён", "success")
                return redirect(url_for("admin.brands"))
            except IntegrityError:
                db.session.rollback()
                flash("Название или slug уже существует", "error")
    return render_template("admin/brand_edit.html", brand=brand)


@admin.post("/brands/<int:brand_id>/delete")
@login_required
def delete_brand(brand_id):
    brand = db.get_or_404(Brand, brand_id)
    if brand.products:
        flash("Нельзя удалить бренд с товарами", "error")
    else:
        db.session.delete(brand)
        admin_log("delete", "brand", brand.id)
        db.session.commit()
    return redirect(url_for("admin.brands"))


@admin.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    """Список и создание категорий каталога."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            db.session.add(Category(name=name, slug=slugify(name)))
            admin_log("create", "category")
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Категория уже существует", "error")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html", categories=Category.query.order_by(Category.name).all())


@admin.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    if request.method == "POST":
        category.name = request.form.get("name", "").strip()
        category.slug = slugify(request.form.get("slug") or category.name)
        try:
            admin_log("update", "category", category.id)
            db.session.commit()
            return redirect(url_for("admin.categories"))
        except IntegrityError:
            db.session.rollback()
            flash("Категория уже существует", "error")
    return render_template("admin/category_edit.html", category=category)


@admin.post("/categories/<int:category_id>/delete")
@login_required
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    if category.products:
        flash("Нельзя удалить категорию с товарами", "error")
    else:
        db.session.delete(category)
        admin_log("delete", "category", category.id)
        db.session.commit()
    return redirect(url_for("admin.categories"))


@admin.route("/products", methods=["GET", "POST"])
@login_required
def products():
    """Создание товара с размерами и несколькими изображениями."""
    if request.method == "POST":
        brand = db.get_or_404(Brand, int(request.form["brand_id"]))
        product = Product(brand_id=brand.id, category_id=int(request.form["category_id"]), name=request.form["name"].strip(), slug=slugify(request.form.get("slug") or request.form["name"]), price=request.form["price"], description=request.form.get("description"), status=request.form.get("status", "published"))
        db.session.add(product)
        db.session.flush()
        for size, stock in zip(request.form.getlist("size"), request.form.getlist("stock")):
            if size.strip():
                db.session.add(ProductSize(product_id=product.id, size=size.strip(), stock=max(0, int(stock or 0))))
        try:
            add_images(product, brand, request.files.getlist("images"))
        except (ValueError, OSError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(url_for("admin.products"))
        admin_log("create", "product", product.id)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Проверьте уникальность slug и значения формы", "error")
            return redirect(url_for("admin.products"))
        flash("Товар создан", "success")
        return redirect(url_for("admin.products"))
    query = Product.query
    if request.args.get("q"):
        query = query.filter(Product.name.ilike(f"%{request.args['q']}%"))
    for field in ("brand_id", "category_id", "status"):
        if request.args.get(field):
            query = query.filter(getattr(Product, field) == request.args[field])
    page = query.order_by(Product.created_at.desc()).paginate(page=request.args.get("page", 1, type=int), per_page=15, error_out=False)
    return render_template("admin/products.html", products=page.items, pagination=page, brands=Brand.query.all(), categories=Category.query.all())


def add_images(product, brand, uploads):
    """Добавить новые файлы после существующих, сохранив порядок фотографий."""
    existing_count = ProductImage.query.filter_by(product_id=product.id).count()
    for offset, image in enumerate(uploads):
        if image and image.filename:
            index = existing_count + offset
            path, thumb_path = save_image(image, brand.slug, product.slug, index)
            db.session.add(ProductImage(product_id=product.id, path=path, thumb_path=thumb_path, is_primary=index == 0, position=index))


@admin.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    """Редактировать данные, остатки, порядок, главное фото и добавить изображения."""
    product = db.get_or_404(Product, product_id)
    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.slug = slugify(request.form.get("slug") or product.name)
        product.brand_id = int(request.form["brand_id"])
        product.category_id = int(request.form["category_id"])
        product.price = request.form["price"]
        product.description = request.form.get("description", "")
        product.status = request.form.get("status", "hidden")
        for size in product.sizes:
            stock = request.form.get(f"stock_{size.id}")
            if stock is not None:
                size.stock = max(0, int(stock))
        for size, stock in zip(request.form.getlist("new_size"), request.form.getlist("new_stock")):
            if size.strip():
                db.session.add(ProductSize(product=product, size=size.strip(), stock=max(0, int(stock or 0))))
        try:
            add_images(product, db.get_or_404(Brand, product.brand_id), request.files.getlist("images"))
            primary_id = request.form.get("primary_image", type=int)
            if primary_id:
                for image in product.images:
                    image.is_primary = image.id == primary_id
            for image in product.images:
                image.position = request.form.get(f"position_{image.id}", image.position, type=int)
            admin_log("update", "product", product.id)
            db.session.commit()
            flash("Товар обновлён", "success")
            return redirect(url_for("admin.products"))
        except (ValueError, OSError, IntegrityError) as exc:
            db.session.rollback()
            flash("Не удалось сохранить товар: " + str(exc), "error")
    return render_template("admin/product_edit.html", product=product, brands=Brand.query.all(), categories=Category.query.all())


@admin.post("/images/<int:image_id>/delete")
@login_required
def delete_image(image_id):
    """Удалить запись и оба локальных файла изображения после подтверждения в UI."""
    image = db.get_or_404(ProductImage, image_id)
    product_id = image.product_id
    for path in (image.path, image.thumb_path):
        if path:
            full = os.path.join(current_app.static_folder, path)
            if os.path.isfile(full):
                os.remove(full)
    db.session.delete(image)
    admin_log("delete", "image", image.id)
    db.session.commit()
    return redirect(url_for("admin.edit_product", product_id=product_id))


@admin.post("/products/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    if OrderItem.query.filter_by(product_id=product.id).first():
        flash("Товар в заказах: скройте его вместо удаления", "error")
    else:
        db.session.delete(product)
        admin_log("delete", "product", product.id)
        db.session.commit()
    return redirect(url_for("admin.products"))


@admin.get("/orders")
@login_required
def orders():
    query = Order.query
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("date"):
        try:
            day = datetime.strptime(request.args["date"], "%Y-%m-%d")
            query = query.filter(Order.created_at >= day, Order.created_at < day + timedelta(days=1))
        except ValueError:
            pass
    return render_template("admin/orders.html", orders=query.order_by(Order.created_at.desc()).all())


@admin.post("/orders/<int:order_id>/status")
@login_required
def order_status(order_id):
    """Сменить статус; переход в cancelled возвращает позиции на склад один раз."""
    order = db.get_or_404(Order, order_id)
    status = request.form.get("status")
    if status not in ("new", "paid", "shipped", "delivered", "cancelled"):
        flash("Недопустимый статус", "error")
        return redirect(url_for("admin.orders"))
    if order.status == "cancelled" and status != "cancelled":
        flash("Отменённый заказ нельзя восстановить", "error")
        return redirect(url_for("admin.orders"))
    if status == "cancelled" and order.status != "cancelled":
        for item in order.items:
            size = ProductSize.query.filter_by(product_id=item.product_id, size=item.size).first()
            if size:
                size.stock += item.quantity
    order.status = status
    admin_log("update", "order", order.id)
    db.session.commit()
    return redirect(url_for("admin.orders"))


@admin.get("/orders/export")
@login_required
def export_orders():
    """Сформировать CSV без SQL: все строки выбираются через ORM."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "customer", "email", "total", "status", "created_at"])
    for order in Order.query.order_by(Order.created_at.desc()).all():
        writer.writerow([order.id, order.customer_name, order.email, order.total, order.status, order.created_at.isoformat()])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


@admin.get("/logs")
@login_required
def logs():
    return render_template("admin/logs.html", logs=AdminLog.query.order_by(AdminLog.created_at.desc()).limit(200).all())
