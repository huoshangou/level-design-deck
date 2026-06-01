"""test_mechanical_check.py — Validator + SEMANTIC checks 覆盖。

跑：python3 -m unittest tools.tests.test_mechanical_check -v
"""

from tools.tests._common import *  # noqa: F401,F403
import unittest

from lib.protocol.mechanical_check import Validator, SEMANTIC_CHECKS


def errs(schema, instance):
    v = Validator(schema)
    v.check(instance)
    return v.errors, v.reviews


class TestRequired(unittest.TestCase):
    def test_required_missing(self):
        e, _ = errs({"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}, {})
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["rule"], "required")
        self.assertEqual(e[0]["field_path"], "a")

    def test_required_present(self):
        e, _ = errs({"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}, {"a": "x"})
        self.assertEqual(e, [])

    def test_all_errors_not_first_fail(self):
        """关键：多个 required 缺失应一次性全报，不 first-fail。"""
        e, _ = errs({"type": "object", "required": ["a", "b", "c"],
                     "properties": {"a": {"type": "string"}, "b": {"type": "string"}, "c": {"type": "string"}}}, {})
        self.assertEqual(len(e), 3)


class TestTypes(unittest.TestCase):
    def test_string_when_int(self):
        e, _ = errs({"type": "object", "properties": {"x": {"type": "string"}}}, {"x": 1})
        self.assertEqual(e[0]["rule"], "type")

    def test_int_when_string(self):
        e, _ = errs({"type": "object", "properties": {"x": {"type": "integer"}}}, {"x": "1"})
        self.assertEqual(e[0]["rule"], "type")

    def test_bool_not_int(self):
        """bool 不能当 int（mechanical_check 显式排除 isinstance(x, bool)）。"""
        e, _ = errs({"type": "object", "properties": {"x": {"type": "integer"}}}, {"x": True})
        self.assertEqual(e[0]["rule"], "type")


class TestStringConstraints(unittest.TestCase):
    def test_min_length(self):
        e, _ = errs({"type": "object", "properties": {"x": {"type": "string", "minLength": 10}}}, {"x": "hi"})
        self.assertEqual(e[0]["rule"], "minLength")

    def test_pattern(self):
        e, _ = errs({"type": "object", "properties": {"x": {"type": "string", "pattern": "^foo_"}}}, {"x": "bar"})
        self.assertEqual(e[0]["rule"], "pattern")

    def test_enum(self):
        e, _ = errs({"type": "object", "properties": {"x": {"type": "string", "enum": ["a", "b"]}}}, {"x": "c"})
        self.assertEqual(e[0]["rule"], "enum")


class TestAdditionalProperties(unittest.TestCase):
    def test_extra_field_rejected(self):
        e, _ = errs({"type": "object", "additionalProperties": False,
                     "properties": {"a": {"type": "string"}}}, {"a": "x", "b": "y"})
        self.assertEqual(e[0]["rule"], "additionalProperties")

    def test_extra_field_allowed(self):
        e, _ = errs({"type": "object", "properties": {"a": {"type": "string"}}}, {"a": "x", "b": "y"})
        self.assertEqual(e, [])


class TestReviews(unittest.TestCase):
    def test_placeholder_TBD(self):
        _, r = errs({"type": "object", "properties": {"x": {"type": "string", "minLength": 5}}}, {"x": "TBD later"})
        self.assertTrue(any(x["rule"] == "placeholder_residue" for x in r))

    def test_caveat(self):
        _, r = errs({"type": "object", "properties": {"x": {"type": "string", "minLength": 5}}},
                    {"x": "用某某代替（待确认）"})
        self.assertTrue(any(x["rule"] == "ai_caveat" for x in r))

    def test_short_id_not_flagged(self):
        """minLength < 5 的字段不查 placeholder（避免误伤短 ID）。"""
        _, r = errs({"type": "object", "properties": {"x": {"type": "string", "minLength": 3}}}, {"x": "TBD"})
        self.assertEqual(r, [])


class TestNested(unittest.TestCase):
    def test_nested_object_required(self):
        schema = {"type": "object", "properties": {
            "m": {"type": "object", "required": ["k"], "properties": {"k": {"type": "string"}}}}}
        e, _ = errs(schema, {"m": {}})
        self.assertEqual(e[0]["field_path"], "m.k")

    def test_array_items(self):
        schema = {"type": "object", "properties": {
            "xs": {"type": "array", "items": {"type": "object", "required": ["k"],
                                              "properties": {"k": {"type": "string"}}}}}}
        e, _ = errs(schema, {"xs": [{"k": "ok"}, {}]})
        self.assertEqual(e[0]["field_path"], "xs[1].k")


class TestBubbleDiagramSemantic(unittest.TestCase):
    def _run(self, spec):
        v = Validator({"type": "object"})
        SEMANTIC_CHECKS["bubble_diagram"](spec, v)
        return v.errors, v.reviews

    def test_unique_id_dup(self):
        e, _ = self._run({"nodes": [{"id": "a", "type": "entry"}, {"id": "a", "type": "exit"}], "edges": []})
        self.assertTrue(any(x["rule"] == "unique_id" for x in e))

    def test_edge_ref_integrity(self):
        e, _ = self._run({"nodes": [{"id": "a", "type": "entry"}, {"id": "b", "type": "exit"}],
                          "edges": [{"from": "a", "to": "ghost"}]})
        self.assertTrue(any(x["rule"] == "ref_integrity" for x in e))

    def test_no_entry(self):
        e, _ = self._run({"nodes": [{"id": "a", "type": "scene"}], "edges": []})
        self.assertTrue(any(x["rule"] == "graph_entry" for x in e))

    def test_no_exit_is_review(self):
        e, r = self._run({"nodes": [{"id": "a", "type": "entry"}], "edges": []})
        self.assertTrue(any(x["rule"] == "graph_exit" for x in r))

    def test_isolated_review(self):
        _, r = self._run({"nodes": [{"id": "a", "type": "entry"}, {"id": "b", "type": "exit"},
                                    {"id": "lonely", "type": "scene"}],
                          "edges": [{"from": "a", "to": "b"}]})
        self.assertTrue(any(x["rule"] == "isolated" for x in r))

    def test_requires_ref(self):
        e, _ = self._run({"nodes": [{"id": "a", "type": "entry"}, {"id": "b", "type": "exit"}],
                          "edges": [{"from": "a", "to": "b", "requires": ["ghost_key"]}]})
        self.assertTrue(any(x["rule"] == "ref_integrity" and "requires" in x["field_path"] for x in e))

    def test_phase_mixed_review(self):
        _, r = self._run({"nodes": [{"id": "a", "type": "entry", "phase": "Act1"},
                                    {"id": "b", "type": "exit"}],
                          "edges": [{"from": "a", "to": "b"}]})
        self.assertTrue(any(x["rule"] == "phase_mixed" for x in r))


class TestSpatialLayoutSemantic(unittest.TestCase):
    def _run(self, spec):
        v = Validator({"type": "object"})
        SEMANTIC_CHECKS["spatial_layout"](spec, v)
        return v.errors, v.reviews

    def test_shape_id_dup(self):
        e, _ = self._run({"layout": {"layers": [{"id": "L1"}],
                                     "shapes": [{"id": "s1", "layerId": "L1", "label": "玄关"},
                                                {"id": "s1", "layerId": "L1", "label": "前殿"}]}})
        self.assertTrue(any(x["rule"] == "unique_id" for x in e))

    def test_shape_layerId_ref(self):
        e, _ = self._run({"layout": {"layers": [{"id": "L1"}],
                                     "shapes": [{"id": "s1", "layerId": "GHOST", "label": "X"}]}})
        self.assertTrue(any(x["rule"] == "ref_integrity" for x in e))

    def test_label_missing_review(self):
        _, r = self._run({"layout": {"layers": [{"id": "L1"}],
                                     "shapes": [{"id": "s1", "layerId": "L1", "label": ""}]}})
        self.assertTrue(any(x["rule"] == "label_missing" for x in r))


if __name__ == "__main__":
    unittest.main()
