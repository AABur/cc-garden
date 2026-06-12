# test_pricing.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pricing  # noqa: E402


class TestPricing(unittest.TestCase):
    def test_resolve_known_families(self):
        self.assertEqual(pricing.resolve_family("claude-opus-4-8"), "opus")
        self.assertEqual(pricing.resolve_family("claude-sonnet-4-6"), "sonnet")
        self.assertEqual(pricing.resolve_family("claude-haiku-4-5-20251001"), "haiku")
        self.assertEqual(pricing.resolve_family("claude-fable-5"), "fable")

    def test_synthetic_and_unknown_are_not_opus(self):
        self.assertEqual(pricing.resolve_family("<synthetic>"), "synthetic")
        self.assertIsNone(pricing.resolve_family("gpt-5.4"))
        self.assertIsNone(pricing.resolve_family(None))

    def test_estimate_cost_per_bucket(self):
        b = pricing.TokenBreakdown(
            input_tokens=1_000_000, output_tokens=1_000_000,
            cache_write_5m_tokens=1_000_000, cache_write_1h_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )
        # opus: 5 + 25 + 6.25 + 10 + 0.5 = 46.75
        self.assertAlmostEqual(pricing.estimate_cost(b, "claude-opus-4-8"), 46.75, places=2)

    def test_synthetic_costs_zero(self):
        b = pricing.TokenBreakdown(input_tokens=1_000_000)
        self.assertEqual(pricing.estimate_cost(b, "<synthetic>"), 0.0)

    def test_unknown_costs_zero(self):
        b = pricing.TokenBreakdown(input_tokens=1_000_000)
        self.assertEqual(pricing.estimate_cost(b, "gpt-5.4"), 0.0)

    def test_cacheable_minimum(self):
        self.assertEqual(pricing.cacheable_minimum("claude-opus-4-8"), 4096)
        self.assertEqual(pricing.cacheable_minimum("claude-sonnet-4-6"), 2048)
        self.assertEqual(pricing.cacheable_minimum("claude-sonnet-4-5-20250101"), 1024)

    def test_sonnet45_resolves_separately(self):
        self.assertEqual(pricing.resolve_family("claude-sonnet-4-5-20250101"), "sonnet45")
        self.assertEqual(pricing.resolve_family("claude-sonnet-4-6"), "sonnet")


if __name__ == "__main__":
    unittest.main()
