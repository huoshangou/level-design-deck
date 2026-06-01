"""test_template_diff.py — SKIP_PREFIXES + mapped/missing/extra 路径覆盖。"""

from tools.tests._common import *  # noqa: F401,F403
import unittest

from lib.protocol.template_diff import build_diff_payload, SKIP_PREFIXES, SPEC_TO_WORKDOC_LIGHTING

WORK_DOCS = {"poi_lighting_fields": [{"name": n} for n in SPEC_TO_WORKDOC_LIGHTING.values()]}
TEMPLATE_FIELDS = {"fields": [{"name": "light_requirement"}]}


def diff(spec):
    return build_diff_payload(spec, WORK_DOCS, TEMPLATE_FIELDS)


class TestSkipPrefixes(unittest.TestCase):
    def test_all_skip_prefixes_short_circuit(self):
        """所有 SKIP_PREFIXES 走的 spec 都应返回 stats 全 0 + 有 rationale。"""
        for prefix in SKIP_PREFIXES:
            with self.subTest(prefix=prefix):
                d = diff({"meta": {"spec_id": f"{prefix}some_level"}})
                self.assertEqual(d["stats"], {"mapped": 0, "missing": 0, "extra": 0})
                self.assertIn("rationale", d)


class TestLightingDiff(unittest.TestCase):
    def _full_mapped_spec(self):
        spec = {"meta": {"spec_id": "lighting_req_x"}, "concept_art": {}}
        for path in SPEC_TO_WORKDOC_LIGHTING:
            head, _, sub = path.partition(".")
            if sub:
                spec.setdefault(head, {})[sub] = "v"
            else:
                spec[path] = "v"
        return spec

    def test_full_mapped_no_missing_no_extra(self):
        d = diff(self._full_mapped_spec())
        self.assertEqual(d["stats"]["mapped"], len(SPEC_TO_WORKDOC_LIGHTING))
        self.assertEqual(d["stats"]["missing"], 0)
        self.assertEqual(d["stats"]["extra"], 0)

    def test_missing_when_path_absent(self):
        spec = {"meta": {"spec_id": "lighting_req_x"}}
        d = diff(spec)
        self.assertGreater(d["stats"]["missing"], 0)

    def test_extra_when_spec_has_unmapped(self):
        spec = self._full_mapped_spec()
        spec["unmapped_field"] = "v"
        d = diff(spec)
        self.assertTrue(any(e["spec_path"] == "unmapped_field" for e in d["extra"]))

    def test_gameplay_consistency_flag(self):
        d = diff(self._full_mapped_spec())
        self.assertIsNotNone(d["gameplay_consistency"])
        self.assertEqual(d["gameplay_consistency"]["status"], "expected")

    def test_workdoc_unmapped_reports_missing(self):
        wd = {"poi_lighting_fields": list(WORK_DOCS["poi_lighting_fields"]) + [{"name": "新字段_未映射"}]}
        d = build_diff_payload(self._full_mapped_spec(), wd, TEMPLATE_FIELDS)
        self.assertTrue(any(m["workdoc_name"] == "新字段_未映射" for m in d["missing"]))


if __name__ == "__main__":
    unittest.main()
