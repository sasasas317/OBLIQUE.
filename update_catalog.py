"""Import product images named in task.md into the local catalog.

Run with `venv/Scripts/python.exe update_catalog.py`. Existing product images and
admin-edited prices are left alone. Sources are user-supplied; usage rights need
to be checked with their respective publishers before any public deployment.
"""
import io
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from app import app
from models import Product, ProductImage, db
from seed import PRODUCT_TYPES, SEED_PRICES

TASK = Path(__file__).with_name("image_sources.md")
IMAGE_LINE = re.compile(r"^(https?://\S+)\s+\(([^()]+)\)\s*$")
KINDS = {kind.lower(): kind for kind, _ in PRODUCT_TYPES}
BRANDS = sorted(SEED_PRICES, key=len, reverse=True)


def image_sources():
    """Разобрать image_sources.md и сопоставить подпись ссылки с товаром."""
    """Match the description in parentheses, accepting minor title typos."""
    sources = {}
    for line in TASK.read_text(encoding="utf-8").splitlines():
        match = IMAGE_LINE.match(line.strip())
        if not match:
            continue
        url, caption = match.groups()
        brand = next((name for name in BRANDS if caption.lower().startswith(name.lower() + " ")), None)
        if not brand:
            raise ValueError(f"Unknown brand in task.md: {caption}")
        caption_kind = caption[len(brand):].lower().strip()
        kind = KINDS.get(caption_kind)
        if not kind:
            if "troust" in caption_kind or "trouser" in caption_kind:
                kind = "Archive Trouser"
            elif "sneaker" in caption_kind:
                kind = "Sculpted Sneaker"
        if not kind:
            raise ValueError(f"Unknown product in task.md: {caption}")
        name = f"{brand} {kind}"
        if name in sources:
            raise ValueError(f"Duplicate image mapping in task.md: {name}")
        sources[name] = url
    return sources


def download(name, url):
    """Проверить контент Pillow, с fallback на curl для проблемных CDN."""
    errors = []
    for attempt in range(3):
        try:
            request = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            })
            with urlopen(request, timeout=22) as response:
                content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise ValueError("image exceeds 8 MB")
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in ("JPEG", "PNG", "WEBP", "AVIF"):
                    raise ValueError(f"unsupported image format: {source.format}")
                image = source.convert("RGB")
            image.thumbnail((1800, 1800))
            return image
        except (HTTPError, URLError, TimeoutError, OSError, UnidentifiedImageError) as exc:
            errors.append(str(exc))
            time.sleep(attempt + 1)
    # Some image CDNs respond to curl while urllib times out during negotiation.
    result = subprocess.run(
        ["curl.exe", "--fail", "--silent", "--show-error", "--location", "--max-time", "35", url],
        capture_output=True, timeout=40,
    )
    if result.returncode == 0 and len(result.stdout) <= 8 * 1024 * 1024:
        try:
            with Image.open(io.BytesIO(result.stdout)) as source:
                if source.format not in ("JPEG", "PNG", "WEBP", "AVIF"):
                    raise ValueError(f"unsupported image format: {source.format}")
                image = source.convert("RGB")
            image.thumbnail((1800, 1800))
            return image
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            errors.append(str(exc))
    raise RuntimeError(f"{name}: {result.stderr.decode('utf-8', errors='replace').strip() or '; '.join(errors)}")


def update():
    """Загрузить отсутствующие фото, не создавая дубликаты ProductImage."""
    sources = image_sources()
    if len(sources) != len(BRANDS) * len(PRODUCT_TYPES):
        raise ValueError(f"Expected 28 image links in task.md, got {len(sources)}")

    failures = []
    with app.app_context():
        for name, url in sources.items():
            product = Product.query.filter_by(name=name).one_or_none()
            if product is None:
                failures.append(f"{name}: product not found in DB")
                continue
            if product.images:
                print(f"Already present: {name}")
                continue
            try:
                image = download(name, url)
                folder = Path(app.static_folder) / "img" / "products" / product.brand.slug
                folder.mkdir(parents=True, exist_ok=True)
                filename = f"{product.slug}-task-reference.webp"
                original = folder / filename
                thumb_path = folder / f"{product.slug}-task-reference-thumb.webp"
                image.save(original, "WEBP", quality=88)
                thumb = image.copy()
                thumb.thumbnail((640, 760))
                thumb.save(thumb_path, "WEBP", quality=82)
                record = ProductImage(
                    product_id=product.id,
                    path=f"img/products/{product.brand.slug}/{filename}",
                    thumb_path=f"img/products/{product.brand.slug}/{thumb_path.name}",
                    position=0, is_primary=True,
                )
                db.session.add(record)
                db.session.commit()
                print(f"Added: {name} ({image.width}x{image.height})")
            except (RuntimeError, ValueError, OSError) as exc:
                db.session.rollback()
                failures.append(str(exc))

        print(f"Images: {ProductImage.query.count()} across {Product.query.count()} products")
    if failures:
        print("Could not import:")
        for error in failures:
            print(" -", error)
        raise SystemExit(1)


if __name__ == "__main__":
    update()
