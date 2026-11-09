"""Check the seven editorial links and the single shared preview."""
from html.parser import HTMLParser

from app import app
from models import Brand


EXPECTED = [
    "Balenciaga",
    "Carol Christian Poell",
    "Comme des Garçons",
    "Maison Margiela",
    "Raf Simons",
    "Rick Owens",
    "Yohji Yamamoto",
]


class DesignerParser(HTMLParser):
    """Минимальный parser проверяет DOM, не требуя браузера или BeautifulSoup."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.previews = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if "designer-row" in classes:
            self.rows.append((attrs.get("data-name"), attrs.get("href")))
        if "brand-preview" in classes:
            self.previews += 1


if __name__ == "__main__":
    client = app.test_client()
    home = client.get("/")
    assert home.status_code == 200
    parser = DesignerParser()
    parser.feed(home.get_data(as_text=True))
    assert [name for name, _ in parser.rows] == EXPECTED, parser.rows
    assert parser.previews == 1
    for name, link in parser.rows:
        assert client.get(link).status_code == 200, (name, link)
    for path in ("/static/css/designers.css", "/static/js/designers.js", "/catalog"):
        assert client.get(path).status_code == 200, path
    print("Seven designers, links, single preview and assets: OK")
