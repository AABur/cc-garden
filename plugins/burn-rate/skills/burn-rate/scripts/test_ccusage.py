# test_ccusage.py
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ccusage  # noqa: E402


class TestCcusage(unittest.TestCase):
    def test_parses_json_on_success(self):
        fake = json.dumps({"daily": [{"date": "2026-06-10", "totalCost": 1.23}]})
        with mock.patch.object(ccusage, "_run", return_value=(0, fake, "")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(err)
        self.assertEqual(data["daily"][0]["totalCost"], 1.23)

    def test_graceful_when_missing(self):
        with mock.patch.object(ccusage, "_run", return_value=(127, "", "not found")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(data)
        self.assertIn("ccusage", err.lower())

    def test_graceful_on_bad_json(self):
        with mock.patch.object(ccusage, "_run", return_value=(0, "not json", "")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(data)
        self.assertIn("parse", err.lower())


if __name__ == "__main__":
    unittest.main()
