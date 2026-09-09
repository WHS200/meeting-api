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

    def test_meeting_forms_use_dual_time_range_with_legacy_hidden_fields(self):
        for page_name in ("create.html", "edit.html"):
            content = (STATIC / page_name).read_text(encoding="utf-8")
            self.assertEqual(content.count('data-time-range'), 1, page_name)
            self.assertIn('data-start-range', content)
            self.assertIn('data-end-range', content)
            self.assertIn('name="meeting_time"', content)
            self.assertIn('name="end_time"', content)
            self.assertNotIn('name="meeting_time" type="time"', content)
            self.assertIn('max="95"', content)
            self.assertIn('step="1"', content)
            self.assertIn(">00:00</span><span>23:45<", content)
        script = (STATIC / "js" / "meeting-form.js").read_text(encoding="utf-8")
        self.assertIn("TIME_STEP_MINUTES = 15", script)
        self.assertIn("TIME_MAX_INDEX = 95", script)
        self.assertIn("MIN_DURATION_STEPS = 2", script)
        self.assertIn("MAX_DURATION_STEPS = 48", script)
        self.assertIn("index * TIME_STEP_MINUTES", script)
        self.assertIn("startPct = (startValue / TIME_MAX_INDEX) * 100", script)
        self.assertIn("fill.style.width", script)
