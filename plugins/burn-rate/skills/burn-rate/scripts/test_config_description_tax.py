# test_config_description_tax.py
"""Tests for description-tax measurement (config_inspector.measure_descriptions)
and the config_description_tax detector."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

import config_inspector
from detectors import config_description_tax


# --- helpers ---------------------------------------------------------------

def _write_skill(cache: Path, marketplace: str, plugin: str, version: str,
                 skill: str, description_block: str) -> None:
    skill_dir = cache / marketplace / plugin / version / "skills" / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(description_block, encoding="utf-8")


def _write_plugin_json(cache: Path, marketplace: str, plugin: str, version: str,
                       description: str) -> None:
    pdir = cache / marketplace / plugin / version / ".claude-plugin"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "plugin.json").write_text(
        json.dumps({"name": plugin, "description": description}), encoding="utf-8")


# --- frontmatter extractor -------------------------------------------------

def test_extract_inline_description():
    text = "---\nname: foo\ndescription: A short tool.\n---\nbody"
    assert config_inspector.extract_description(text) == "A short tool."


def test_extract_folded_block_scalar():
    text = (
        "---\n"
        "name: foo\n"
        "description: >-\n"
        "  This is a folded\n"
        "  multi-line description\n"
        "  that spans several lines.\n"
        "tools: all\n"
        "---\n"
        "body\n"
    )
    out = config_inspector.extract_description(text)
    assert "folded" in out
    assert "several lines." in out
    assert ">-" not in out
    assert "tools:" not in out


def test_extract_no_frontmatter():
    assert config_inspector.extract_description("just a body, no fm") == ""


def test_extract_frontmatter_no_description():
    assert config_inspector.extract_description("---\nname: foo\n---\nbody") == ""


# --- measure_descriptions --------------------------------------------------

def test_measure_descriptions(tmp_path):
    cache = tmp_path / "cache"

    # Plugin alpha: inline description skill.
    alpha_skill_desc = "Alpha skill that does alpha things for testing."
    _write_skill(cache, "mkt", "alpha", "1.0.0", "doer",
                 f"---\nname: doer\ndescription: {alpha_skill_desc}\n---\nbody")
    alpha_plugin_desc = "Alpha plugin description text here."
    _write_plugin_json(cache, "mkt", "alpha", "1.0.0", alpha_plugin_desc)

    # Plugin beta: folded block scalar skill (proves parser).
    beta_lines = ["This is a long folded description", "that wraps onto multiple",
                  "lines for the beta skill."]
    beta_block = (
        "---\nname: helper\ndescription: >-\n"
        + "".join(f"  {ln}\n" for ln in beta_lines)
        + "tools: all\n---\nbody\n"
    )
    _write_skill(cache, "mkt", "beta", "2.0.0", "helper", beta_block)
    beta_plugin_desc = "Beta plugin does beta work and more."
    _write_plugin_json(cache, "mkt", "beta", "2.0.0", beta_plugin_desc)

    result = config_inspector.measure_descriptions(cache)

    # Expected skill tokens.
    alpha_skill_tokens = len(alpha_skill_desc) // 4
    beta_extracted = config_inspector.extract_description(beta_block)
    beta_skill_tokens = len(beta_extracted) // 4
    assert result["skill_description_tokens"] == alpha_skill_tokens + beta_skill_tokens

    # Expected plugin tokens.
    alpha_plugin_tokens = len(alpha_plugin_desc) // 4
    beta_plugin_tokens = len(beta_plugin_desc) // 4
    assert result["plugin_description_tokens"] == alpha_plugin_tokens + beta_plugin_tokens

    # Per-plugin weight = skill descs + plugin own desc.
    weights = result["description_weight_by_plugin"]
    assert weights["alpha"] == alpha_skill_tokens + alpha_plugin_tokens
    assert weights["beta"] == beta_skill_tokens + beta_plugin_tokens

    # beta has the larger folded description -> top plugin.
    top = max(weights.items(), key=lambda kv: kv[1])[0]
    assert top == "beta"

    assert result["plugin_count"] == 2


def test_measure_descriptions_defensive(tmp_path):
    cache = tmp_path / "cache"
    # Skill with no frontmatter.
    _write_skill(cache, "mkt", "p1", "1.0.0", "s1", "no frontmatter here at all")
    # Skill with frontmatter but no description.
    _write_skill(cache, "mkt", "p2", "1.0.0", "s2", "---\nname: s2\n---\nbody")
    result = config_inspector.measure_descriptions(cache)
    assert result["skill_description_tokens"] == 0
    assert result["plugin_description_tokens"] == 0


def test_measure_descriptions_missing_cache(tmp_path):
    result = config_inspector.measure_descriptions(tmp_path / "does_not_exist")
    assert result["skill_description_tokens"] == 0
    assert result["plugin_description_tokens"] == 0
    assert result["description_weight_by_plugin"] == {}


# --- detector --------------------------------------------------------------

@dataclass
class _FakeConfig:
    skill_description_tokens: int = 0
    plugin_description_tokens: int = 0
    skill_count: int = 0
    plugin_count: int = 0
    description_weight_by_plugin: dict = field(default_factory=dict)


@dataclass
class _FakeSession:
    n_turns: int = 0

    @property
    def deduped_turn_count(self) -> int:
        return self.n_turns


def test_detector_above_threshold_emits_leak():
    config = _FakeConfig(
        skill_description_tokens=1800,
        plugin_description_tokens=600,
        skill_count=40,
        plugin_count=8,
        description_weight_by_plugin={"alpha": 1200, "beta": 700, "gamma": 300, "delta": 100},
    )
    sessions = [_FakeSession(10), _FakeSession(5)]  # 15 turns
    leaks = config_description_tax.detect(sessions, [], config, None)
    assert len(leaks) == 1
    leak = leaks[0]
    assert leak.id == "config:skill_description_tax"
    assert leak.basis == "mixed"
    assert leak.overlap_group == "config_tax"
    assert leak.additive is False
    assert leak.severity == "suggestion"
    assert leak.category == "config"

    total_per_turn = 1800 + 600
    assert leak.est_weekly_tokens == total_per_turn * 15

    blob = " ".join(leak.evidence)
    assert "Tool-search does NOT defer" in blob
    # top 3 plugins present, delta (4th) absent.
    assert "alpha" in blob and "beta" in blob and "gamma" in blob
    assert "delta" not in blob


def test_detector_below_threshold_empty():
    config = _FakeConfig(skill_description_tokens=500, plugin_description_tokens=400)
    leaks = config_description_tax.detect([_FakeSession(5)], [], config, None)
    assert leaks == []


def test_detector_zero_turns():
    config = _FakeConfig(skill_description_tokens=2500, plugin_description_tokens=0,
                         description_weight_by_plugin={"alpha": 2500})
    leaks = config_description_tax.detect([], [], config, None)
    assert len(leaks) == 1
    assert leaks[0].est_weekly_tokens == 0


def test_detector_none_config():
    assert config_description_tax.detect([], [], None, None) == []


def test_detector_registered():
    from detectors import DETECTOR_MODULES
    assert "detectors.config_description_tax" in DETECTOR_MODULES
