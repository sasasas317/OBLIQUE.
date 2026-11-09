"""Общие функции магазина и админки: slug, журнал и обработка загрузок."""

import os
import re
import secrets
from functools import wraps
from PIL import Image
from flask import current_app, redirect, request, url_for
from flask_login import current_user
from models import AdminLog, db


def slugify(value):
    """Преобразовать название в URL-slug, сохраняя буквы Unicode."""
    value = re.sub(r"[^\w\s-]", "", value.lower(), flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", value).strip("-")


def admin_log(action, entity, entity_id=None):
    """Добавить запись в текущую транзакцию; commit делает вызывающий маршрут."""
    if current_user.is_authenticated:
        db.session.add(AdminLog(admin_id=current_user.id, action=action, entity=entity, entity_id=entity_id))


def admin_required(view):
    """Переадресовать гостя на вход (в маршрутах также применяется login_required)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def save_image(file, brand_slug, product_slug, index):
    """Проверить реальный тип, сохранить WebP и миниатюру, вернуть пути от static/."""
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise ValueError("Разрешены только JPG, PNG и WebP")
    image = Image.open(file.stream)
    if image.format not in ("JPEG", "PNG", "WEBP"):
        raise ValueError("Неверный тип изображения")
    # verify() читает файл до конца; для конвертации открываем поток заново.
    image.verify()
    file.stream.seek(0)
    image = Image.open(file.stream).convert("RGB")
    folder = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"], brand_slug)
    os.makedirs(folder, exist_ok=True)
    suffix = secrets.token_hex(4)
    filename = f"{product_slug}-{index}-{suffix}.webp"
    full = os.path.join(folder, filename)
    image.thumbnail((1800, 1800))
    image.save(full, "WEBP", quality=88)
    rel = os.path.relpath(full, os.path.join(current_app.root_path, "static")).replace("\\", "/")
    thumb = os.path.join(folder, f"{product_slug}-{index}-{suffix}-thumb.webp")
    image.thumbnail((640, 760))
    image.save(thumb, "WEBP", quality=82)
    thumb_rel = os.path.relpath(thumb, os.path.join(current_app.root_path, "static")).replace("\\", "/")
    return rel, thumb_rel
