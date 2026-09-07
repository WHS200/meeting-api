import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        for key in ("href", "src"):
            value = values.get(key)
            if value and value.startswith("/static/"):
                self.assets.append(value)


class FrontendContractTest(unittest.TestCase):
    def test_local_assets_exist_and_ids_are_unique(self):
        for page in STATIC.rglob("*.html"):
            parser = AssetParser()
            parser.feed(page.read_text(encoding="utf-8"))
            self.assertEqual(len(parser.ids), len(set(parser.ids)), page)
            for value in parser.assets:
                path = urlsplit(value).path.removeprefix("/static/")
                self.assertTrue((STATIC / path).is_file(), f"{page}: {value}")

    def test_generated_markup_has_no_malformed_option_close(self):
        for script in (STATIC / "js").glob("*.js"):
            content = script.read_text(encoding="utf-8")
            self.assertNotRegex(content, re.compile(r"</option\s+value="), script)
