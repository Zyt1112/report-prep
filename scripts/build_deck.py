#!/usr/bin/env python3
"""Build SlideDSL pages from a structured deck outline JSON.

The generator owns repeated master/layout code. Content, visual choices and
source evidence remain explicit in the input JSON.
"""

import argparse
import json
from pathlib import Path
import re
import sys


TOKEN = re.compile(r"\{\{(E\d+)\}\}")
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}")
SAFE_ASSET = re.compile(r"^[A-Za-z0-9_./-]+$")
ALIASES = {
    "cover": "P1",
    "cards": "P2",
    "two-column": "P3",
    "table": "P4",
    "steps": "P5",
    "boundary": "P6",
}
ROMAN = ("Ⅰ", "Ⅱ", "Ⅲ")


class DeckError(ValueError):
    pass


def load_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeckError("cannot read %s: %s" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise DeckError("root JSON value must be an object")
    return data


def load_evidence(path):
    if not path:
        return {}
    data = load_json(path)
    items = data.get("items")
    if not isinstance(items, list):
        raise DeckError("evidence JSON must contain an items array")
    evidence = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise DeckError("each evidence item needs a string id")
        evidence[item["id"]] = item
    return evidence


def js_string(value):
    """Return an injection-safe JSX string expression."""
    encoded = json.dumps(value, ensure_ascii=False)
    return (
        encoded.replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
    )


def resolve_text(value, evidence, field="text"):
    if not isinstance(value, str):
        raise DeckError("%s must be a string" % field)

    def replace(match):
        evidence_id = match.group(1)
        item = evidence.get(evidence_id)
        if item is None:
            raise DeckError("%s uses unknown evidence %s" % (field, evidence_id))
        if item.get("status") not in ("verified", "derived"):
            raise DeckError("%s uses non-verified evidence %s" % (field, evidence_id))
        display = item.get("display")
        if not isinstance(display, str) or not display:
            raise DeckError("evidence %s has no display value" % evidence_id)
        return display

    resolved = TOKEN.sub(replace, value)
    leftover = PLACEHOLDER.search(resolved)
    if leftover:
        raise DeckError("%s contains unresolved placeholder %s" % (field, leftover.group(0)))
    return resolved


def text(lines, indent, value, evidence, size=17, color="#1A2230", bold=False, extra="", field="text"):
    padding = " " * indent
    weight = ", fontWeight: 'bold'" if bold else ""
    suffix = ", " + extra if extra else ""
    lines.append(
        "%s<Text style={{ fontSize: %s, color: '%s'%s%s }}>{%s}</Text>"
        % (padding, size, color, weight, suffix, js_string(resolve_text(value, evidence, field)))
    )


def asset_path(value):
    if not isinstance(value, str) or not value or not SAFE_ASSET.fullmatch(value):
        raise DeckError("logo must be a relative ASCII asset path")
    parts = Path(value).parts
    if value.startswith("/") or ".." in parts:
        raise DeckError("logo must stay inside the deck project")
    return value


def inherited(page, deck, key, default=""):
    value = page.get(key, deck.get(key, default))
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DeckError("%s must be a string" % key)
    return value


def slide_start(lines):
    lines.append("<Slide style={{ width: 1280, height: 720, background: '#FFFFFF', flexDirection: 'column' }}>")


def render_cover(page, deck, evidence):
    lines = []
    slide_start(lines)
    logo = inherited(page, deck, "logo")
    kicker = inherited(page, deck, "kicker", "文 献 精 读")
    lines.append("    <Box style={{ height: 232, background: '#0024B3', padding: '0 72px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>")
    if logo:
        lines.append('        <Image src="%s" style={{ width: 300, height: 61 }} />' % asset_path(logo))
    else:
        text(lines, 8, inherited(page, deck, "brand", "report-prep"), evidence, 20, "#FFFFFF", True, field="brand")
    text(lines, 8, kicker, evidence, 15, "#BFD0F5", extra="letterSpacing: 3", field="kicker")
    lines.append("    </Box>")
    lines.append("    <Box style={{ flex: 1, padding: '56px 72px 0', flexDirection: 'column', gap: 18 }}>")
    title_lines = page.get("title_lines")
    if title_lines is None:
        title_lines = [inherited(page, deck, "title")]
    if not isinstance(title_lines, list) or not title_lines or len(title_lines) > 2:
        raise DeckError("P1 title_lines must contain 1 or 2 strings")
    for index, value in enumerate(title_lines):
        text(lines, 8, value, evidence, 42, "#1A2230", True, "lineHeight: 1.35", "title_lines[%d]" % index)
    text(lines, 8, inherited(page, deck, "subtitle"), evidence, 19, "#4A5568", extra="marginTop: 6", field="subtitle")
    lines.append("        <Box style={{ height: 3, width: 96, background: '#0024B3', marginTop: 4 }} />")
    lines.append("    </Box>")
    lines.append("    <Box style={{ padding: '0 72px 40px', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>")
    lines.append("        <Box style={{ flexDirection: 'column', gap: 6 }}>")
    text(lines, 12, inherited(page, deck, "citation"), evidence, 15, "#4A5568", field="citation")
    text(lines, 12, inherited(page, deck, "scene"), evidence, 14, "#8B97A8", field="scene")
    lines.append("        </Box>")
    organization = inherited(page, deck, "organization")
    if organization:
        text(lines, 8, organization, evidence, 14, "#8B97A8", field="organization")
    else:
        lines.append("        <Box />")
    lines.append("    </Box>")
    lines.append("</Slide>")
    return "\n".join(lines) + "\n"


def master_start(lines, page, deck, index, total, evidence):
    slide_start(lines)
    logo = inherited(page, deck, "logo")
    lines.append("    <Box style={{ height: 56, background: '#0024B3', padding: '0 40px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>")
    if logo:
        lines.append('        <Image src="%s" style={{ width: 118, height: 24 }} />' % asset_path(logo))
    else:
        text(lines, 8, inherited(page, deck, "brand", "report-prep"), evidence, 12, "#BFD0F5", field="brand")
    text(lines, 8, "%d / %d" % (index, total), evidence, 12, "#BFD0F5", field="page_number")
    lines.append("    </Box>")
    lines.append("    <Box style={{ flex: 1, padding: '22px 40px 0', flexDirection: 'column', gap: 12 }}>")
    text(lines, 8, page.get("section"), evidence, 22, "#0024B3", True, field="section")
    text(lines, 8, page.get("conclusion"), evidence, 19, "#1A2230", extra="lineHeight: 1.5", field="conclusion")


def master_end(lines, page, evidence):
    lines.append("    </Box>")
    lines.append("    <Box style={{ height: 62, padding: '0 40px', borderTop: '1px solid #D6DCE5', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 }}>")
    text(lines, 8, page.get("footer_left", ""), evidence, 12, "#8B97A8", field="footer_left")
    text(lines, 8, page.get("footer_right", ""), evidence, 12, "#8B97A8", field="footer_right")
    lines.append("    </Box>")
    lines.append("</Slide>")


def body_paragraphs(card, key="body"):
    value = card.get(key, "")
    values = value if isinstance(value, list) else [value]
    if not values or any(not isinstance(item, str) for item in values):
        raise DeckError("card %s must be a string or string array" % key)
    return values


def render_cards(page, deck, index, total, evidence, page_type):
    expected = {"P2": 3, "P3": 2, "P6": 3}[page_type]
    cards = page.get("cards")
    if not isinstance(cards, list) or len(cards) != expected or any(not isinstance(card, dict) for card in cards):
        raise DeckError("%s requires exactly %d card objects" % (page_type, expected))
    lines = []
    master_start(lines, page, deck, index, total, evidence)
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 18, alignItems: 'stretch' }}>")
    for card_index, card in enumerate(cards):
        lines.append("            <Box style={{ flex: 1, padding: 18, border: '1px solid #D6DCE5', flexDirection: 'column', gap: 10 }}>")
        if expected == 3:
            text(lines, 16, ROMAN[card_index], evidence, 13, "#8B97A8", extra="letterSpacing: 2", field="card_number")
        text(lines, 16, card.get("title"), evidence, 21, "#1E4FA8", True, field="cards[%d].title" % card_index)
        for body_index, value in enumerate(body_paragraphs(card)):
            text(lines, 16, value, evidence, 17, "#1A2230", extra="lineHeight: 1.6", field="cards[%d].body[%d]" % (card_index, body_index))
        if card.get("emphasis"):
            text(lines, 16, card["emphasis"], evidence, 16, "#D9534F", field="cards[%d].emphasis" % card_index)
        lines.append("            </Box>")
    lines.append("        </Box>")
    if page.get("note"):
        lines.append("        <Box style={{ marginTop: 4, padding: '10px 14px', background: '#FFF8E1' }}>")
        text(lines, 12, page["note"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="note")
        lines.append("        </Box>")
    master_end(lines, page, evidence)
    return "\n".join(lines) + "\n"


def validate_matrix(page):
    headers = page.get("headers")
    rows = page.get("rows")
    if not isinstance(headers, list) or not headers or any(not isinstance(item, str) for item in headers):
        raise DeckError("P4 headers must be a non-empty string array")
    if not isinstance(rows, list) or not rows:
        raise DeckError("P4 rows must be a non-empty array")
    for row in rows:
        if not isinstance(row, list) or len(row) != len(headers) or any(not isinstance(cell, str) for cell in row):
            raise DeckError("every P4 row must match headers and contain only strings")
    widths = page.get("widths")
    if widths is not None and (
        not isinstance(widths, list)
        or len(widths) != len(headers)
        or any(not isinstance(width, (int, float)) or isinstance(width, bool) or width <= 0 for width in widths)
    ):
        raise DeckError("P4 widths must be positive numbers matching headers")
    highlights = set()
    for item in page.get("highlights", []):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in item)
        ):
            raise DeckError("P4 highlights must contain [row, column] integer pairs")
        row, column = item
        if not (0 <= row < len(rows) and 0 <= column < len(headers)):
            raise DeckError("P4 highlight [%d, %d] is outside the table" % (row, column))
        highlights.add((row, column))
    return headers, rows, widths, highlights


def render_table(page, deck, index, total, evidence):
    headers, rows, widths, highlights = validate_matrix(page)
    lines = []
    master_start(lines, page, deck, index, total, evidence)

    def row(values, row_index=None):
        header = row_index is None
        lines.append("        <Box style={{ flexDirection: 'row', alignItems: 'center', padding: '10px 14px', %s }}>" % ("background: '#F7F9FC', borderBottom: '1px solid #D6DCE5'" if header else "borderBottom: '1px solid #E5E7EB'"))
        for column, value in enumerate(values):
            sizing = "width: %s" % widths[column] if widths else "flex: 1"
            lines.append("            <Box style={{ %s }}>" % sizing)
            highlighted = not header and (row_index, column) in highlights
            if highlighted:
                lines.append("                <Box style={{ alignSelf: 'flex-start', borderBottom: '2px solid #D9534F', paddingBottom: 2 }}>")
            text(
                lines,
                20 if highlighted else 16,
                value,
                evidence,
                18 if highlighted else (15 if header else 16),
                "#D9534F" if highlighted else "#4A5568" if header else "#1A2230",
                bold=header or highlighted,
                field="table[%s,%d]" % ("header" if header else row_index, column),
            )
            if highlighted:
                lines.append("                </Box>")
            lines.append("            </Box>")
        lines.append("        </Box>")

    row(headers)
    for row_index, values in enumerate(rows):
        row(values, row_index)
    if page.get("reading"):
        lines.append("        <Box style={{ marginTop: 12, padding: '10px 14px', background: '#FFF8E1' }}>")
        text(lines, 12, page["reading"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="reading")
        lines.append("        </Box>")
    master_end(lines, page, evidence)
    return "\n".join(lines) + "\n"


def render_steps(page, deck, index, total, evidence):
    steps = page.get("steps")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 5 or any(not isinstance(step, dict) for step in steps):
        raise DeckError("P5 requires 3 to 5 step objects")
    lines = []
    master_start(lines, page, deck, index, total, evidence)
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 14, alignItems: 'stretch' }}>")
    for step_index, step in enumerate(steps):
        lines.append("            <Box style={{ flex: 1, padding: 16, border: '1px solid #D6DCE5', flexDirection: 'column', gap: 10 }}>")
        text(lines, 16, "%02d" % (step_index + 1), evidence, 13, "#8B97A8", extra="letterSpacing: 2", field="step_number")
        text(lines, 16, step.get("title"), evidence, 20, "#1E4FA8", True, field="steps[%d].title" % step_index)
        text(lines, 16, step.get("body"), evidence, 16, "#1A2230", extra="lineHeight: 1.6", field="steps[%d].body" % step_index)
        lines.append("            </Box>")
    lines.append("        </Box>")
    if page.get("note"):
        lines.append("        <Box style={{ marginTop: 4, padding: '10px 14px', background: '#FFF8E1' }}>")
        text(lines, 12, page["note"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="note")
        lines.append("        </Box>")
    master_end(lines, page, evidence)
    return "\n".join(lines) + "\n"


def render_page(page, deck, index, total, evidence):
    if not isinstance(page, dict):
        raise DeckError("each page must be an object")
    page_type = page.get("type")
    page_type = ALIASES.get(page_type, page_type)
    if page_type == "P1":
        if index != 1:
            raise DeckError("P1 cover must be the first page")
        return render_cover(page, deck, evidence)
    if page_type not in ("P2", "P3", "P4", "P5", "P6"):
        raise DeckError("page %d has unsupported type %r" % (index, page_type))
    if not isinstance(page.get("section"), str) or not page.get("section"):
        raise DeckError("page %d needs section" % index)
    if not isinstance(page.get("conclusion"), str) or not page.get("conclusion"):
        raise DeckError("page %d needs conclusion" % index)
    if page_type == "P4":
        return render_table(page, deck, index, total, evidence)
    if page_type == "P5":
        return render_steps(page, deck, index, total, evidence)
    return render_cards(page, deck, index, total, evidence, page_type)


def build(deck, evidence=None):
    if deck.get("kind") != "deck":
        raise DeckError("deck outline JSON must use kind: deck")
    pages = deck.get("pages")
    if not isinstance(pages, list) or not pages:
        raise DeckError("deck outline needs a non-empty pages array")
    if not pages or not isinstance(pages[0], dict) or ALIASES.get(pages[0].get("type"), pages[0].get("type")) != "P1":
        raise DeckError("the first page must be P1 cover")
    if sum(1 for page in pages if isinstance(page, dict) and ALIASES.get(page.get("type"), page.get("type")) == "P1") != 1:
        raise DeckError("deck must contain exactly one P1 cover")
    evidence = evidence or {}
    return [render_page(page, deck, index, len(pages), evidence) for index, page in enumerate(pages, 1)]


def write_deck(deck, output, evidence=None, force=False):
    output = Path(output)
    slides = build(deck, evidence)
    slide_dir = output / "slides"
    targets = [slide_dir / ("%02d.slide" % index) for index in range(1, len(slides) + 1)]
    existing = [str(path) for path in targets if path.exists()]
    if existing and not force:
        raise DeckError("output already contains slides; use --force to replace: %s" % ", ".join(existing))
    slide_dir.mkdir(parents=True, exist_ok=True)
    for path, source in zip(targets, slides):
        path.write_text(source, encoding="utf-8")
    return targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("content", help="deck outline JSON (kind: deck)")
    parser.add_argument("-o", "--output", required=True, help="deck project directory")
    parser.add_argument("--evidence", help="evidence JSON used to replace {{E001}} tokens")
    parser.add_argument("--force", action="store_true", help="replace same-numbered .slide files")
    args = parser.parse_args(argv)
    try:
        targets = write_deck(
            load_json(args.content),
            args.output,
            load_evidence(args.evidence),
            force=args.force,
        )
    except DeckError as exc:
        print("FAIL", exc, file=sys.stderr)
        return 1
    print("OK built %d slides in %s" % (len(targets), Path(args.output) / "slides"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
