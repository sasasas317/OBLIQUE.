"""Local integration smoke test; creates a temporary brand, product and order."""
"""Интеграционная проверка основных покупательских и админских сценариев."""

import io
import os
import re
import uuid
from PIL import Image
from app import app
from models import AdminLog, Brand, Order, Product, ProductSize, db


def token(response):
    """Достать CSRF из HTML-мета или скрытого поля формы."""
    return re.search(r'(?:name="csrf-token" content="|name="csrf_token" value=")([^"]+)', response.get_data(as_text=True)).group(1)


def run():
    """Проверить и затем удалить только тестовые записи, созданные этим запуском."""
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert client.get('/brand/maison-margiela').status_code == 200
    assert client.get('/product/maison-margiela-edition-coat').status_code == 200
    assert client.get('/admin').status_code == 302
    csrf = token(client.get('/'))
    response = client.post('/api/cart', json={'product_id': 1, 'size': 'M', 'quantity': 1}, headers={'X-CSRFToken': csrf})
    assert response.status_code == 200, response.get_data(as_text=True)
    with app.app_context():
        stock_before = ProductSize.query.filter_by(product_id=1, size='M').one().stock
    response = client.post('/checkout', data={'csrf_token': csrf, 'customer_name': 'Test Buyer', 'email': 'buyer@example.com', 'address': 'Test address'})
    assert response.status_code == 200, response.get_data(as_text=True)
    with app.app_context():
        order = Order.query.filter_by(email='buyer@example.com').order_by(Order.id.desc()).first()
        assert order and order.items
        order_id = order.id
        assert ProductSize.query.filter_by(product_id=1, size='M').one().stock == stock_before - 1
    csrf = token(client.get('/admin/login'))
    response = client.post('/admin/login', data={'csrf_token': csrf, 'email': 'admin@example.com', 'password': 'admin12345'})
    assert response.status_code == 302
    csrf = token(client.get('/admin/'))
    for path in ('/admin/', '/admin/brands', '/admin/categories', '/admin/products', '/admin/orders', '/admin/logs', '/admin/orders/export'):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code, response.get_data(as_text=True)[:500])
    suffix = uuid.uuid4().hex[:8]
    response = client.post('/admin/brands', data={'csrf_token': csrf, 'name': 'Smoke ' + suffix}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        brand = Brand.query.filter_by(name='Smoke ' + suffix).one()
        brand_id = brand.id
    image = Image.new('RGB', (40, 40), '#641f2d')
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    response = client.post('/admin/products', data={'csrf_token': csrf, 'brand_id': str(brand_id), 'category_id': '1', 'name': 'Smoke Product ' + suffix, 'price': '55.00', 'size': 'M', 'stock': '2', 'images': (output, 'test.png')}, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200, response.get_data(as_text=True)
    with app.app_context():
        product = Product.query.filter_by(name='Smoke Product ' + suffix).one()
        assert product.images and product.images[0].thumb_path
    response = client.post(f'/admin/orders/{order_id}/status', data={'csrf_token': csrf, 'status': 'cancelled'})
    assert response.status_code == 302
    with app.app_context():
        assert ProductSize.query.filter_by(product_id=1, size='M').one().stock == stock_before
        assert db.session.get(Order, order_id).status == 'cancelled'
        # Remove only records created by this smoke run.
        order = db.session.get(Order, order_id)
        db.session.delete(order)
        product = Product.query.filter_by(name='Smoke Product ' + suffix).one()
        for image in product.images:
            for path in (image.path, image.thumb_path):
                if path:
                    os.remove(os.path.join(app.static_folder, path))
        db.session.delete(product)
        db.session.flush()
        db.session.delete(db.session.get(Brand, brand_id))
        AdminLog.query.filter_by(entity="product", entity_id=product.id).delete()
        AdminLog.query.filter_by(entity="brand", entity_id=brand_id).delete()
        db.session.commit()
    print('Smoke tests passed')


if __name__ == '__main__':
    run()
