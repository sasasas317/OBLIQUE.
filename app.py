"""Точка входа: создание Flask-приложения и подключение общих расширений."""

from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from extensions import limiter
from models import Admin, db

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    """Собрать приложение, зарегистрировать маршруты и общие обработчики."""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    limiter.init_app(app)
    csrf.init_app(app)

    # Flask-Login хранит в cookie только ID, пользователя ищем в БД на каждом запросе.
    @login_manager.user_loader
    def load_admin(admin_id):
        return db.session.get(Admin, int(admin_id))

    # Заголовки добавляются и к обычным ответам, и к страницам ошибок.
    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data:; connect-src 'self'"
        return response

    # Доступен в каждом Jinja-шаблоне, включая шапку и выдвижную корзину.
    @app.context_processor
    def inject_cart_count():
        from flask import session
        return {"cart_count": sum(item.get("quantity", 0) for item in session.get("cart", {}).values())}

    @app.errorhandler(404)
    def not_found(error):
        return render_template("shop/404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return "Изображение превышает лимит 8 МБ", 413

    # Поздний импорт позволяет блюпринтам пользоваться уже созданными расширениями.
    from blueprints.shop import shop
    from blueprints.admin import admin
    app.register_blueprint(shop)
    app.register_blueprint(admin)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
