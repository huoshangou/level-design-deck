"""test_cross_check.py — 9 条 cross_check 规则覆盖。

6 zone_ref + bubble_phase_summary + check_bubble_zone_ref + check_storyboard_beat_ref
（注：旧 memory 写 7 条是错的；实际 9 条 register）
"""

from tools.tests._common import *  # noqa: F401,F403
import unittest

from lib.protocol.cross_check import CROSS_CHECKS, CrossValidator


def run(fn, specs_by_module):
    v = CrossValidator()
    fn(specs_by_module, v)
    return v.errors, v.reviews


def find_check(desc_prefix):
    for desc, fn in CROSS_CHECKS:
        if desc.startswith(desc_prefix):
            return fn
    raise LookupError(f"no check found for prefix: {desc_prefix}")


SPATIAL_2 = {"layout": {"shapes": [{"label": "玄关"}, {"label": "前殿"}]}}


class TestZoneRefRulesParametrized(unittest.TestCase):
    """6 个 zone_ref 规则走同 make_zone_ref_check 工厂；用 subTest 压成一个测试方法。"""

    CASES = [
        ("lighting_req.ambience_refs", "lighting_req", "ambience_refs", "region_id"),
        ("vfx_req.effects", "vfx_req", "effects", "zone_id"),
        ("audio_req.ambient_sounds", "audio_req", "ambient_sounds", "region_id"),
        ("atmosphere_ref.zones", "atmosphere_ref", "zones", "zone_id"),
        ("asset_list.assets", "asset_list", "assets", "ref_zone_id"),
        ("storyboard.panels[].zone_id", "storyboard", "panels", "zone_id"),
    ]

    def test_each_matched(self):
        for prefix, mod, coll, key in self.CASES:
            with self.subTest(rule=prefix):
                fn = find_check(prefix)
                e, _ = run(fn, {mod: {coll: [{key: "玄关"}]}, "spatial_layout": SPATIAL_2})
                self.assertEqual(e, [], f"{prefix} matched should pass")

    def test_each_broken(self):
        for prefix, mod, coll, key in self.CASES:
            with self.subTest(rule=prefix):
                fn = find_check(prefix)
                e, _ = run(fn, {mod: {coll: [{key: "ghost"}]}, "spatial_layout": SPATIAL_2})
                self.assertTrue(any(x["rule"] == "cross_ref_integrity" for x in e),
                                f"{prefix} broken should ERROR")

    def test_each_skipped_when_spatial_missing(self):
        """spatial_layout 不存在时应跳过（不报错）。"""
        for prefix, mod, coll, key in self.CASES:
            with self.subTest(rule=prefix):
                fn = find_check(prefix)
                e, _ = run(fn, {mod: {coll: [{key: "anything"}]}})
                self.assertEqual(e, [], f"{prefix} without spatial should skip")

    def test_each_skipped_when_source_missing(self):
        for prefix, mod, coll, key in self.CASES:
            with self.subTest(rule=prefix):
                fn = find_check(prefix)
                e, _ = run(fn, {"spatial_layout": SPATIAL_2})
                self.assertEqual(e, [], f"{prefix} without source should skip")


class TestBubblePhaseSummary(unittest.TestCase):
    def test_review_when_phases_present(self):
        fn = find_check("bubble_diagram phase")
        _, r = run(fn, {"bubble_diagram": {"nodes": [{"id": "a", "phase": "Act1"},
                                                     {"id": "b", "phase": "Act2"}]}})
        self.assertTrue(any(x["rule"] == "bubble_phase_summary" for x in r))

    def test_no_review_when_no_phase(self):
        fn = find_check("bubble_diagram phase")
        _, r = run(fn, {"bubble_diagram": {"nodes": [{"id": "a"}, {"id": "b"}]}})
        self.assertEqual(r, [])


class TestBubbleZoneRef(unittest.TestCase):
    def test_matched(self):
        fn = find_check("bubble_diagram nodes[].zone_id")
        e, _ = run(fn, {"bubble_diagram": {"nodes": [{"id": "n1", "zone_id": "玄关"}]},
                        "spatial_layout": SPATIAL_2})
        self.assertEqual(e, [])

    def test_broken(self):
        fn = find_check("bubble_diagram nodes[].zone_id")
        e, _ = run(fn, {"bubble_diagram": {"nodes": [{"id": "n1", "zone_id": "ghost"}]},
                        "spatial_layout": SPATIAL_2})
        self.assertTrue(any(x["rule"] == "cross_ref_integrity" for x in e))


class TestStoryboardBeatRef(unittest.TestCase):
    BUBBLE = {"nodes": [{"id": "beat_entry"}, {"id": "beat_exit"}]}

    def test_matched(self):
        fn = find_check("storyboard.panels[].beat_id")
        e, _ = run(fn, {"bubble_diagram": self.BUBBLE,
                        "storyboard": {"panels": [{"beat_id": "beat_entry"}]}})
        self.assertEqual(e, [])

    def test_broken(self):
        fn = find_check("storyboard.panels[].beat_id")
        e, _ = run(fn, {"bubble_diagram": self.BUBBLE,
                        "storyboard": {"panels": [{"beat_id": "ghost_beat"}]}})
        self.assertTrue(any(x["rule"] == "cross_ref_integrity" for x in e))

    def test_skipped_when_bubble_missing(self):
        fn = find_check("storyboard.panels[].beat_id")
        e, _ = run(fn, {"storyboard": {"panels": [{"beat_id": "anything"}]}})
        self.assertEqual(e, [])


class TestRegistryShape(unittest.TestCase):
    def test_count_is_9(self):
        """Lock：CROSS_CHECKS 应有 9 条 register（6 zone_ref + phase + bubble_zone + storyboard_beat）。
        变 register 数量必须 bump 这个数字 + 加对应测试。"""
        self.assertEqual(len(CROSS_CHECKS), 9, f"got {len(CROSS_CHECKS)}: {[d for d, _ in CROSS_CHECKS]}")


if __name__ == "__main__":
    unittest.main()
