"""Добавить таблицу аксессуаров и связь аксессуаров с позициями заказов."""

from sqlalchemy import inspect, text

from app import app
from models import db


def migrate():
    """Выполнить только отсутствующие изменения схемы MySQL."""
    with app.app_context():
        inspector = inspect(db.engine)
        with db.engine.begin() as connection:
            if not inspector.has_table("accessories"):
                connection.execute(
                    text(
                        """
                        CREATE TABLE accessories (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(120) NOT NULL,
                            price DECIMAL(10, 2) NOT NULL,
                            image VARCHAR(200),
                            description TEXT,
                            designer_id INT NULL,
                            INDEX idx_accessories_designer (designer_id),
                            FOREIGN KEY (designer_id)
                                REFERENCES brands(id) ON DELETE SET NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                        """
                    )
                )

            columns = {
                column["name"] for column in inspector.get_columns("order_items")
            }
            if "accessory_id" not in columns:
                connection.execute(
                    text(
                        """
                        ALTER TABLE order_items
                        ADD COLUMN accessory_id INT NULL,
                        ADD INDEX idx_items_accessory (accessory_id),
                        ADD CONSTRAINT fk_items_accessory
                            FOREIGN KEY (accessory_id) REFERENCES accessories(id)
                        """
                    )
                )

            if "product_id" in columns:
                connection.execute(
                    text("ALTER TABLE order_items MODIFY product_id INT NULL")
                )


if __name__ == "__main__":
    migrate()
    print("Accessory migration completed")
