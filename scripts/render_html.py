#!/usr/bin/env python3
"""Render report-prep content JSON into escaped, printable HTML.

Usage:
    python scripts/render_html.py content.json -o output.html
    python scripts/render_html.py content.json --evidence evidence.json -o output.html

Only Python's standard library is required. Source-derived numbers should use
{{E001}}-style evidence tokens instead of being copied between deliverables.
"""

import argparse
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_TOKEN = re.compile(r"\{\{(E\d+)\}\}")
TEMPLATE_TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
ANY_TOKEN = re.compile(r"\{\{[^{}]+\}\}")
ALLOWED_EVIDENCE_STATUSES = {"verified", "derived"}


class ContentError(ValueError):
    """Raised when content or evidence data cannot be rendered safely."""


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ContentError("JSON root must be an object: %s" % path)
    return data


def load_evidence(path):
    if path is None:
        return {}
    data = load_json(path)
    items = data.get("items")
    if not isinstance(items, list):
        raise ContentError("Evidence JSON must contain an items array")
    result = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ContentError("Evidence item %d must be an object" % index)
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not re.fullmatch(r"E\d+", evidence_id):
            raise ContentError("Evidence item %d has an invalid id" % index)
        if evidence_id in result:
            raise ContentError("Duplicate evidence id: %s" % evidence_id)
        display = item.get("display")
        if not isinstance(display, str) or not display.strip():
            raise ContentError("%s needs a non-empty display string" % evidence_id)
        result[evidence_id] = item
    return result


def require_string(value, label, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ContentError("%s must be a %sstring" % (label, "" if allow_empty else "non-empty "))
    return value


def text(value, evidence, label="text"):
    """Escape plain text and replace evidence tokens without recursing."""
    value = require_string(value, label, allow_empty=True)
    output = []
    position = 0
    for match in EVIDENCE_TOKEN.finditer(value):
        output.append(escape(value[position:match.start()], quote=False))
        evidence_id = match.group(1)
        if evidence_id not in evidence:
            raise ContentError("%s references unknown evidence %s" % (label, evidence_id))
        item = evidence[evidence_id]
        status = item.get("status")
        if status not in ALLOWED_EVIDENCE_STATUSES:
            raise ContentError("%s uses %s with status %s" % (label, evidence_id, status))
        output.append(escape(item["display"], quote=False))
        position = match.end()
    output.append(escape(value[position:], quote=False))
    rendered = "".join(output)
    unresolved = ANY_TOKEN.search(rendered)
    if unresolved:
        raise ContentError("%s contains unresolved token %s" % (label, unresolved.group(0)))
    return rendered.replace("\n", "<br>\n")


def table(headers, rows, evidence, label="table"):
    if not isinstance(headers, list) or not headers:
        raise ContentError("%s.headers must be a non-empty array" % label)
    if not isinstance(rows, list):
        raise ContentError("%s.rows must be an array" % label)
    header_html = "".join("<th>%s</th>" % text(cell, evidence, label + ".headers") for cell in headers)
    body_html = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(headers):
            raise ContentError("%s row %d must have %d cells" % (label, row_index, len(headers)))
        cells = "".join(
            "<td>%s</td>" % text(cell, evidence, "%s.rows[%d]" % (label, row_index))
            for cell in row
        )
        body_html.append("<tr>%s</tr>" % cells)
    return "<table>\n<thead><tr>%s</tr></thead>\n<tbody>\n%s\n</tbody>\n</table>" % (
        header_html, "\n".join(body_html)
    )


def block(block_data, evidence, label):
    if not isinstance(block_data, dict):
        raise ContentError("%s must be an object" % label)
    block_type = block_data.get("type")
    if block_type == "paragraph":
        return "<p>%s</p>" % text(block_data.get("text"), evidence, label + ".text")
    if block_type == "heading":
        return "<h3>%s</h3>" % text(block_data.get("text"), evidence, label + ".text")
    if block_type in {"key", "why"}:
        return '<div class="%s">%s</div>' % (
            block_type, text(block_data.get("text"), evidence, label + ".text")
        )
    if block_type == "list":
        items = block_data.get("items")
        if not isinstance(items, list) or not items:
            raise ContentError("%s.items must be a non-empty array" % label)
        tag = "ol" if block_data.get("ordered", False) else "ul"
        body = "".join(
            "<li>%s</li>" % text(item, evidence, "%s.items[%d]" % (label, index))
            for index, item in enumerate(items)
        )
        return "<%s>%s</%s>" % (tag, body, tag)
    if block_type == "table":
        return table(block_data.get("headers"), block_data.get("rows"), evidence, label)
    raise ContentError("%s has unsupported type %r" % (label, block_type))


def explainer_mapping(data, evidence):
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ContentError("explainer.sections must be a non-empty array")
    rendered_sections = []
    for index, section in enumerate(sections):
        label = "sections[%d]" % index
        if not isinstance(section, dict):
            raise ContentError("%s must be an object" % label)
        heading = text(section.get("title"), evidence, label + ".title")
        note = section.get("note", "")
        note_html = "<span>%s</span>" % text(note, evidence, label + ".note") if note else ""
        blocks = section.get("blocks", [])
        if not isinstance(blocks, list):
            raise ContentError("%s.blocks must be an array" % label)
        body = "\n".join(
            block(item, evidence, "%s.blocks[%d]" % (label, block_index))
            for block_index, item in enumerate(blocks)
        )
        rendered_sections.append("<h2>%s%s</h2>\n%s" % (heading, note_html, body))
    profile = data.get("profile", "")
    profile_html = '<div class="profile">%s</div>' % text(profile, evidence, "profile") if profile else ""
    return {
        "TITLE": text(data.get("title"), evidence, "title"),
        "KICKER": text(data.get("kicker", "讲 解 稿"), evidence, "kicker"),
        "SUBTITLE": text(data.get("subtitle", ""), evidence, "subtitle"),
        "PROFILE_BLOCK": profile_html,
        "SECTIONS": "\n".join(rendered_sections),
        "FOOTER": text(data.get("footer", "report-prep"), evidence, "footer"),
        "PAGE_LABEL": text(data.get("page_label", ""), evidence, "page_label"),
    }


def outline_mapping(data, evidence):
    beats = data.get("beats")
    if not isinstance(beats, list) or not beats:
        raise ContentError("outline.beats must be a non-empty array")
    rendered_beats = []
    for index, beat in enumerate(beats):
        label = "beats[%d]" % index
        if not isinstance(beat, dict):
            raise ContentError("%s must be an object" % label)
        rendered_beats.append(
            '<div class="beat"><div class="n">%d</div><div class="b">\n'
            '<div class="t">%s</div>\n<div class="d">%s</div>\n<div class="h">%s</div>\n'
            "</div></div>" % (
                index + 1,
                text(beat.get("title"), evidence, label + ".title"),
                text(beat.get("detail", ""), evidence, label + ".detail"),
                text(beat.get("note", ""), evidence, label + ".note"),
            )
        )
    mapping_html = ""
    if "mapping" in data:
        mapping_data = data["mapping"]
        if not isinstance(mapping_data, dict):
            raise ContentError("mapping must be an object")
        mapping_html = "<h2>%s</h2>\n%s" % (
            text(mapping_data.get("title", "压缩关系"), evidence, "mapping.title"),
            table(mapping_data.get("headers"), mapping_data.get("rows"), evidence, "mapping"),
        )
    closing = data.get("closing", "")
    closing_html = '<h2>一句话总纲</h2>\n<div class="say">%s</div>' % text(
        closing, evidence, "closing"
    ) if closing else ""
    notes = data.get("notes", [])
    if not isinstance(notes, list):
        raise ContentError("notes must be an array")
    notes_html = ""
    if notes:
        notes_html = "<h2>讲述提醒</h2>\n<ul>%s</ul>" % "".join(
            "<li>%s</li>" % text(item, evidence, "notes[%d]" % index)
            for index, item in enumerate(notes)
        )
    return {
        "TITLE": text(data.get("title"), evidence, "title"),
        "KICKER": text(data.get("kicker", "讲 述 提 纲"), evidence, "kicker"),
        "SUBTITLE": text(data.get("subtitle", ""), evidence, "subtitle"),
        "BEATS": "\n".join(rendered_beats),
        "MAPPING_BLOCK": mapping_html,
        "CLOSING_BLOCK": closing_html,
        "NOTES_BLOCK": notes_html,
        "FOOTER": text(data.get("footer", "report-prep"), evidence, "footer"),
        "PAGE_LABEL": text(data.get("page_label", ""), evidence, "page_label"),
    }


def render(data, evidence=None):
    evidence = evidence or {}
    kind = data.get("kind")
    if kind not in {"explainer", "outline"}:
        raise ContentError("kind must be 'explainer' or 'outline'")
    mapping = explainer_mapping(data, evidence) if kind == "explainer" else outline_mapping(data, evidence)
    template_path = ROOT / "assets" / (kind + ".html")
    template = template_path.read_text(encoding="utf-8")

    def replace(match):
        name = match.group(1)
        if name not in mapping:
            raise ContentError("Template %s has no value for %s" % (template_path, name))
        return mapping[name]

    rendered = TEMPLATE_TOKEN.sub(replace, template)
    unresolved = ANY_TOKEN.search(rendered)
    if unresolved:
        raise ContentError("Unresolved output token: %s" % unresolved.group(0))
    return rendered


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("content", help="Content JSON path")
    parser.add_argument("--evidence", help="Evidence JSON path")
    parser.add_argument("-o", "--output", required=True, help="Output HTML path")
    args = parser.parse_args(argv)
    try:
        data = load_json(args.content)
        evidence = load_evidence(args.evidence)
        rendered = render(data, evidence)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
    except (OSError, ContentError, json.JSONDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    print("OK %s -> %s" % (args.content, output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
