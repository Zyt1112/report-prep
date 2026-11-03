import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_html
import check_numbers
import render_html


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.evidence = render_html.load_evidence(ROOT / "examples" / "evidence.json")

    def test_examples_render_and_validate(self):
        for name in ("explainer", "outline"):
            with self.subTest(name=name):
                data = render_html.load_json(ROOT / "examples" / ("%s.content.json" % name))
                rendered = render_html.render(data, self.evidence)
                self.assertNotIn("{{E001}}", rendered)
                self.assertIn("24,845", rendered)
                self.assertNotIn("{{TITLE}}", rendered)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / (name + ".html")
                    path.write_text(rendered, encoding="utf-8")
                    errors, _, stats = check_html.check(path)
                self.assertEqual([], errors)
                self.assertGreater(stats["text_chars"], 50)

    def test_outline_beat_count_is_dynamic(self):
        data = render_html.load_json(ROOT / "examples" / "outline.content.json")
        rendered = render_html.render(data, self.evidence)
        self.assertEqual(4, rendered.count('class="beat"'))

    def test_text_is_escaped(self):
        data = {
            "kind": "outline",
            "title": "<script>alert('x')</script> & safe",
            "beats": [{"title": "A < B", "detail": "5 > 3", "note": "plain"}],
        }
        rendered = render_html.render(data, {})
        self.assertNotIn("<script>alert", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("A &lt; B", rendered)
        self.assertIn("5 &gt; 3", rendered)

    def test_unknown_evidence_token_fails(self):
        data = {"kind": "outline", "title": "Demo", "beats": [{"title": "Value {{E999}}"}]}
        with self.assertRaises(render_html.ContentError):
            render_html.render(data, self.evidence)

    def test_unverified_evidence_cannot_render(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["E001"]["status"] = "unverified"
        data = render_html.load_json(ROOT / "examples" / "outline.content.json")
        with self.assertRaises(render_html.ContentError):
            render_html.render(data, evidence)

    def test_table_row_width_is_checked(self):
        data = {
            "kind": "outline",
            "title": "Demo",
            "beats": [{"title": "One"}],
            "mapping": {"headers": ["A", "B"], "rows": [["only one"]]},
        }
        with self.assertRaises(render_html.ContentError):
            render_html.render(data, {})


class NumberTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT / "examples" / "evidence.json").read_text(encoding="utf-8"))
        self.content = json.loads((ROOT / "examples" / "outline.content.json").read_text(encoding="utf-8"))

    def test_examples_pass(self):
        errors, warnings, stats, _ = check_numbers.audit(self.evidence, self.content)
        self.assertEqual([], errors)
        # 示例里 25 ℃ / 250 ℃ 是试验条件、未入台账，会被裸数字扫描提示；其余警告应为 0
        self.assertEqual([], [item for item in warnings if "裸数字" not in item])
        self.assertEqual(2, stats["references"])
        self.assertEqual(2, stats["used"])

    def test_display_value_mismatch_fails(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"][0]["display"] = "24,854"
        errors, _, _, _ = check_numbers.audit(evidence, self.content)
        self.assertTrue(any("display/value mismatch" in error for error in errors))

    def test_unverified_reference_fails(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"][0]["status"] = "unverified"
        errors, _, _, _ = check_numbers.audit(evidence, self.content)
        self.assertTrue(any("status unverified" in error for error in errors))

    def test_unknown_reference_fails(self):
        content = copy.deepcopy(self.content)
        content["closing"] = "Unknown {{E999}}"
        errors, _, _, _ = check_numbers.audit(self.evidence, content)
        self.assertTrue(any("unknown E999" in error for error in errors))

    def test_duplicate_id_fails(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"].append(copy.deepcopy(evidence["items"][0]))
        errors, _, _, _ = check_numbers.audit(evidence, self.content)
        self.assertTrue(any("Duplicate evidence id" in error for error in errors))

    def test_derived_item_requires_note(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"][0]["status"] = "derived"
        evidence["items"][0].pop("note")
        errors, _, _, _ = check_numbers.audit(evidence, self.content)
        self.assertTrue(any("derived item needs a note" in error for error in errors))

    def test_unicode_minus_and_grouping_match(self):
        self.assertEqual(
            check_numbers.parse_decimal("−1,234.5"),
            check_numbers.parse_decimal(-1234.5),
        )

    def test_bare_number_with_unit_is_reported(self):
        content = copy.deepcopy(self.content)
        content["beats"][0]["detail"] = "峰值 650 MPa 出现在 50 µm 深处。"
        errors, warnings, stats, _ = check_numbers.audit(self.evidence, content)
        self.assertEqual([], errors)
        self.assertTrue(any("650MPa" in item for item in warnings))
        self.assertTrue(any("50µm" in item for item in warnings))
        self.assertGreaterEqual(stats["bare"], 2)

    def test_bare_number_reuses_existing_evidence_id(self):
        content = copy.deepcopy(self.content)
        content["beats"][0]["detail"] = "过渡寿命 24845 cycles。"
        _, warnings, _, _ = check_numbers.audit(self.evidence, content)
        self.assertTrue(any("应改用 {{E001}}" in item for item in warnings))

    def test_bare_number_strict_upgrades_to_error(self):
        content = copy.deepcopy(self.content)
        content["beats"][0]["detail"] = "峰值 650 MPa。"
        errors, _, _, _ = check_numbers.audit(self.evidence, content, strict=True)
        self.assertTrue(any("650MPa" in error for error in errors))

    def test_qualitative_item_passes_without_value(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"].append(
            {
                "id": "E009",
                "display": "Masing 行为成立",
                "value": None,
                "unit": "—",
                "source": "demo-source.txt",
                "locator": "line 5",
                "quote": "Masing behaviour was observed.",
                "status": "verified",
                "kind": "author_result",
                "qualitative": True,
            }
        )
        errors, _, stats, _ = check_numbers.audit(evidence, self.content)
        self.assertEqual([], [error for error in errors if "E009" in error])
        self.assertEqual(1, stats["qualitative"])

    def test_qualitative_item_must_not_carry_value(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["items"].append(
            {
                "id": "E010",
                "display": "Masing 行为成立",
                "value": 1,
                "unit": "—",
                "source": "demo-source.txt",
                "locator": "line 5",
                "quote": "Masing behaviour was observed.",
                "status": "verified",
                "kind": "author_result",
                "qualitative": True,
            }
        )
        errors, _, _, _ = check_numbers.audit(evidence, self.content)
        self.assertTrue(any("E010 qualitative must use value null" in error for error in errors))

    def test_source_quote_found(self):
        source = "\n".join(item["quote"] for item in self.evidence["items"])
        errors, warnings, stats, _ = check_numbers.audit(self.evidence, self.content, source_text=source)
        self.assertFalse(any("quote 未在" in item for item in warnings))
        self.assertEqual(2, stats["quotes"])

    def test_source_quote_missing_is_reported(self):
        errors, warnings, stats, _ = check_numbers.audit(
            self.evidence, self.content, source_text="A different sentence entirely."
        )
        self.assertTrue(any("quote 未在" in item for item in warnings))
        self.assertEqual(2, stats["quotes"])

    def test_source_quote_missing_strict_is_error(self):
        errors, _, _, _ = check_numbers.audit(
            self.evidence, self.content, source_text="A different sentence entirely.", strict=True
        )
        self.assertTrue(any("quote 未在" in error for error in errors))


class HtmlTests(unittest.TestCase):
    def document(self, body, style="@page { size: A4; } table { break-inside: avoid; }"):
        return (
            "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">"
            "<title>Test</title><style>" + style + "</style></head><body>" + body + "</body></html>"
        )

    def audit(self, source, allow_placeholders=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.html"
            path.write_text(source, encoding="utf-8")
            return check_html.check(path, allow_placeholders=allow_placeholders)

    def test_valid_named_entity(self):
        errors, _, _ = self.audit(self.document("<p>&sigma; &lt; &amp;</p>"))
        self.assertEqual([], errors)

    def test_unknown_entity_and_bare_amp_fail(self):
        errors, _, _ = self.audit(self.document("<p>&definitelybogus; A & B</p>"))
        self.assertTrue(any("unknown HTML entity" in error for error in errors))
        self.assertTrue(any("unescaped &" in error for error in errors))

    def test_escaped_amp_in_attribute_is_not_false_positive(self):
        errors, _, _ = self.audit(self.document('<p><a href="?a=1&amp;b=2">link</a></p>'))
        self.assertEqual([], errors)

    def test_misnested_tags_fail(self):
        errors, _, _ = self.audit(self.document("<div><span>text</div></span>"))
        self.assertTrue(errors)

    def test_comment_does_not_fake_page_style(self):
        source = self.document("<!-- @page { size: A4; } --><p>text</p>", style="p { color: black; }")
        errors, _, _ = self.audit(source)
        self.assertTrue(any("missing @page" in error for error in errors))

    def test_table_requires_head_and_body(self):
        errors, _, _ = self.audit(self.document("<table><tr><td>A</td></tr></table>"))
        self.assertTrue(any("missing <thead>" in error for error in errors))
        self.assertTrue(any("missing <tbody>" in error for error in errors))

    def test_template_placeholders_are_opt_in(self):
        source = self.document("<p>{{TITLE}}</p>")
        errors, _, _ = self.audit(source)
        self.assertTrue(any("unresolved placeholder" in error for error in errors))
        errors, _, _ = self.audit(source, allow_placeholders=True)
        self.assertEqual([], errors)

    def test_warning_does_not_count_as_error(self):
        source = self.document("<p>text</p>", style="@page { size: A4; }")
        errors, warnings, _ = self.audit(source)
        self.assertEqual([], errors)
        self.assertTrue(any("break-inside" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
