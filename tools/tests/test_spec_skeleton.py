"""test_spec_skeleton.py — iter_fields / classify / cross_ref 注入 / 端到端 abandoned_temple。"""

from tools.tests._common import *  # noqa: F401,F403
import unittest

from lib.protocol.spec_skeleton import (
    iter_fields, classify, collect_cross_refs, build_skeleton, discover_specs,
    CROSS_REF_RULES, KNOWN_MODULES,
)


class TestClassify(unittest.TestCase):
    def test_empty_required(self):
        self.assertEqual(classify("", True), "required_missing")
        self.assertEqual(classify(None, True), "required_missing")
        self.assertEqual(classify([], True), "required_missing")

    def test_empty_optional(self):
        self.assertEqual(classify("", False), "empty")
        self.assertEqual(classify([], False), "empty")

    def test_placeholder_TBD(self):
        self.assertEqual(classify("TBD 后面补", False), "placeholder")
        self.assertEqual(classify("待定", False), "placeholder")

    def test_tbd_pending(self):
        self.assertEqual(classify("[待对接]", False), "tbd_pending")
        self.assertEqual(classify("待对接", False), "tbd_pending")

    def test_filled(self):
        self.assertEqual(classify("玄关", False), "filled")
        self.assertEqual(classify(42, False), "filled")


class TestIterFields(unittest.TestCase):
    def test_flat_object(self):
        schema = {"type": "object", "required": ["a"],
                  "properties": {"a": {"type": "string", "title": "A"},
                                 "b": {"type": "integer"}}}
        spec = {"a": "x", "b": 1}
        out = list(iter_fields(schema, spec))
        paths = [p for p, _, _, _ in out]
        self.assertIn("a", paths)
        self.assertIn("b", paths)
        # required flag 正确传递
        a_entry = next(x for x in out if x[0] == "a")
        self.assertTrue(a_entry[3])
        b_entry = next(x for x in out if x[0] == "b")
        self.assertFalse(b_entry[3])

    def test_nested_array(self):
        schema = {"type": "object", "properties": {
            "xs": {"type": "array", "items": {"type": "object",
                                              "properties": {"k": {"type": "string"}}}}}}
        spec = {"xs": [{"k": "v1"}, {"k": "v2"}]}
        out = list(iter_fields(schema, spec))
        paths = [p for p, _, _, _ in out]
        self.assertIn("xs[0].k", paths)
        self.assertIn("xs[1].k", paths)

    def test_empty_array_yields_placeholder(self):
        schema = {"type": "object", "properties": {
            "xs": {"type": "array", "items": {"type": "string"}}}}
        out = list(iter_fields(schema, {"xs": []}))
        paths = [p for p, _, _, _ in out]
        self.assertIn("xs", paths)


class TestCrossRefs(unittest.TestCase):
    def test_matched_spatial_label(self):
        refs = collect_cross_refs({
            "spatial_layout": {"layout": {"shapes": [{"label": "玄关"}]}},
            "lighting_req": {"ambience_refs": [{"region_id": "玄关"}]},
        })
        self.assertTrue(any(r["status"] == "matched" and r["from_value"] == "玄关" for r in refs))

    def test_broken_spatial_label(self):
        refs = collect_cross_refs({
            "spatial_layout": {"layout": {"shapes": [{"label": "玄关"}]}},
            "lighting_req": {"ambience_refs": [{"region_id": "ghost"}]},
        })
        self.assertTrue(any(r["status"] == "broken" for r in refs))

    def test_target_missing_when_no_spatial(self):
        refs = collect_cross_refs({
            "lighting_req": {"ambience_refs": [{"region_id": "anything"}]},
        })
        self.assertTrue(any(r["status"] == "target_missing" for r in refs))

    def test_storyboard_beat_ref(self):
        refs = collect_cross_refs({
            "bubble_diagram": {"nodes": [{"id": "beat_entry"}]},
            "storyboard": {"panels": [{"beat_id": "beat_entry"}]},
        })
        self.assertTrue(any(r["status"] == "matched" and r["to_module"] == "bubble_diagram" for r in refs))


class TestRulesShape(unittest.TestCase):
    def test_rules_match_cross_check(self):
        """spec_skeleton CROSS_REF_RULES 必须跟 cross_check.py 对齐。变其一必须同步。"""
        from lib.protocol.cross_check import CROSS_CHECKS
        # cross_check 有 9 register；spec_skeleton CROSS_REF_RULES 应是 zone_ref 子集 + storyboard_beat
        # 6 zone_ref + storyboard_beat = 7（不含 bubble_phase_summary REVIEW 和 bubble_zone）
        self.assertEqual(len(CROSS_REF_RULES), 7,
                         f"CROSS_REF_RULES 当前 {len(CROSS_REF_RULES)}；改 cross_check register 需同步")

    def test_known_modules_is_9(self):
        self.assertEqual(len(KNOWN_MODULES), 9)


class TestEndToEndAbandonedTemple(unittest.TestCase):
    """abandoned_temple 是公开发布案例，9 module 完整 + 0 broken；用作回归基线。"""

    @classmethod
    def setUpClass(cls):
        spec_paths = discover_specs("abandoned_temple")
        cls.skel = build_skeleton("abandoned_temple", spec_paths)

    def test_9_modules_present(self):
        self.assertEqual(self.skel["summary"]["modules_present"], 9)

    def test_no_broken_cross_refs(self):
        self.assertEqual(self.skel["summary"]["cross_refs_broken"], 0)

    def test_cross_refs_count_reasonable(self):
        """至少 40 条 cross_refs（实测 48），低于这个数说明有 module 丢字段。"""
        self.assertGreaterEqual(self.skel["summary"]["cross_refs_total"], 40)

    def test_each_module_has_fields(self):
        for m in self.skel["modules"]:
            self.assertGreater(m["stats"]["total"], 0, f"{m['module']} has 0 fields")

    def test_cross_ref_injected_into_field(self):
        """spec_skeleton 应把 cross_ref 注入到 lighting_req.ambience_refs[*].region_id 字段。"""
        lighting = next(m for m in self.skel["modules"] if m["module"] == "lighting_req")
        ref_fields = [f for f in lighting["fields"]
                      if "ambience_refs" in f["path"] and "region_id" in f["path"]
                      and "cross_ref" in f]
        self.assertGreater(len(ref_fields), 0)


class TestPhaseFilter(unittest.TestCase):
    """M5.4: build_skeleton 支持 phase_filter 折叠。"""

    @classmethod
    def setUpClass(cls):
        cls.spec_paths = discover_specs("abandoned_temple")

    def _filter(self, phase):
        return build_skeleton("abandoned_temple", self.spec_paths, phase_filter=phase)

    def test_phase_L0_has_3_modules(self):
        skel = self._filter("L0")
        names = {m["module"] for m in skel["modules"]}
        self.assertEqual(names, {"level_overview", "atmosphere_ref", "bubble_diagram"})

    def test_phase_whitebox_has_only_spatial(self):
        skel = self._filter("whitebox")
        names = [m["module"] for m in skel["modules"]]
        self.assertEqual(names, ["spatial_layout"])

    def test_phase_docified_has_5_modules(self):
        skel = self._filter("docified")
        names = {m["module"] for m in skel["modules"]}
        self.assertEqual(names, {"lighting_req", "vfx_req", "audio_req", "asset_list", "storyboard"})

    def test_phase_sums_to_all_modules(self):
        """L0 + whitebox + docified 模块数 = 全集（守门：phase 归属不重不漏）。"""
        n_l0 = len(self._filter("L0")["modules"])
        n_wb = len(self._filter("whitebox")["modules"])
        n_doc = len(self._filter("docified")["modules"])
        n_all = len(build_skeleton("abandoned_temple", self.spec_paths)["modules"])
        self.assertEqual(n_l0 + n_wb + n_doc, n_all)

    def test_cross_refs_filtered_by_phase(self):
        """phase=L0 时不该出现 docified module 的 cross_refs。"""
        skel = self._filter("L0")
        for r in skel["cross_refs"]:
            src_mod = r["from"].split(".")[0]
            self.assertIn(src_mod, {"level_overview", "atmosphere_ref", "bubble_diagram"})

    def test_phase_attached_to_module(self):
        skel = self._filter("docified")
        for m in skel["modules"]:
            self.assertEqual(m["phase"], "docified")


if __name__ == "__main__":
    unittest.main()
