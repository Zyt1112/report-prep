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
HIGHLIGHT = re.compile(r"\[\[([^\[\]]+)\]\]")
SAFE_ASSET = re.compile(r"^[A-Za-z0-9_./-]+$")
ALIASES = {
    "cover": "P1",
    "cards": "P2",
    "two-column": "P3",
    "table": "P4",
    "steps": "P5",
    "boundary": "P6",
    "chart": "P7",
    "structure": "P8",
}
PAGE_LABELS = {
    "P2": "三栏卡片",
    "P3": "两栏卡片",
    "P4": "结果表",
    "P5": "流程链",
    "P6": "边界页",
    "P7": "数据图",
    "P8": "结构示意",
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


def rich_text(lines, indent, value, evidence, size=17, color="#1A2230", bold=False, extra="", field="text"):
    """v1.8: 渲染含 [[重点]] 内联标注的文本。

    证据令牌先解析，[[...]] 段渲染为红色加粗 + 2px 红下边框（与 P4 表格高亮
    同一视觉语言）。无标注时退化为单条 Text，与 text() 输出兼容。
    """
    resolved = resolve_text(value, evidence, field)
    segments = HIGHLIGHT.split(resolved)
    if len(segments) == 1:
        text(lines, indent, value, evidence, size, color, bold=bold, extra=extra, field=field)
        return
    padding = " " * indent
    weight = ", fontWeight: 'bold'" if bold else ""
    suffix = ", " + extra if extra else ""
    lines.append("%s<Box style={{ flexDirection: 'row', alignItems: 'baseline', flexWrap: 'wrap'%s }}>" % (padding, suffix))
    for index, segment in enumerate(segments):
        if not segment:
            continue
        if index % 2 == 1:
            lines.append(
                "%s    <Box style={{ alignSelf: 'flex-start', borderBottom: '2px solid #D9534F', paddingBottom: 2, marginLeft: 2, marginRight: 2 }}>"
                % padding
            )
            lines.append(
                "%s        <Text style={{ fontSize: %s, color: '#D9534F', fontWeight: 'bold' }}>{%s}</Text>"
                % (padding, size + 1, js_string(segment))
            )
            lines.append("%s    </Box>" % padding)
        else:
            lines.append(
                "%s    <Text style={{ fontSize: %s, color: '%s'%s }}>{%s}</Text>"
                % (padding, size, color, weight, js_string(segment))
            )
    lines.append("%s</Box>" % padding)


def asset_path(value, field="logo"):
    if not isinstance(value, str) or not value or not SAFE_ASSET.fullmatch(value):
        raise DeckError("%s must be a relative ASCII asset path" % field)
    parts = Path(value).parts
    if value.startswith("/") or ".." in parts:
        raise DeckError("%s must stay inside the deck project" % field)
    return value


DEFAULT_LOGO = "assets/tyust-logo.png"
SKILL_ASSETS = Path(__file__).resolve().parent.parent / "assets"


def resolve_logo(deck, output):
    """v1.8: logo 默认启用机构母版。

    deck.json 不写 logo 时，自动把 Skill 内置校徽复制到输出目录并引用；
    写 "none" 显式关闭；写路径则按原样校验（输出目录内必须存在该文件）。
    """
    value = deck.get("logo")
    if isinstance(value, str) and value.strip().lower() == "none":
        return ""
    if value is None or value == "":
        target = Path(output) / DEFAULT_LOGO
        if not target.exists():
            source = SKILL_ASSETS / Path(DEFAULT_LOGO).name
            if not source.exists():
                return ""  # Skill 安装缺文件时降级为无 logo，不阻塞出稿
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        return DEFAULT_LOGO
    return asset_path(value)


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
        brand = inherited(page, deck, "brand")
        if brand:
            text(lines, 8, brand, evidence, 20, "#FFFFFF", True, field="brand")
        else:
            lines.append("        <Box />")
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


BANNED_FOOTER = ("数值由证据令牌解析", "证据令牌", "令牌解析")

def master_start(lines, page, deck, index, total, evidence, page_type=None):
    slide_start(lines)
    logo = inherited(page, deck, "logo")
    lines.append("    <Box style={{ height: 56, background: '#0024B3', padding: '0 40px', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>")
    if logo:
        lines.append('        <Image src="%s" style={{ width: 118, height: 24 }} />' % asset_path(logo))
    else:
        brand = inherited(page, deck, "brand")
        if brand:
            text(lines, 8, brand, evidence, 12, "#BFD0F5", field="brand")
        else:
            lines.append("        <Box />")
    text(lines, 8, "%d / %d" % (index, total), evidence, 12, "#BFD0F5", field="page_number")
    lines.append("    </Box>")
    lines.append("    <Box style={{ flex: 1, padding: '22px 40px 0', flexDirection: 'column', gap: 12 }}>")
    text(lines, 8, page.get("section"), evidence, 22, "#0024B3", True, field="section")
    rich_text(lines, 8, page.get("conclusion"), evidence, 19, "#1A2230", extra="lineHeight: 1.5", field="conclusion")


def master_end(lines, page, evidence, page_type=None):
    footer_right = page.get("footer_right")
    if footer_right is None and page_type in PAGE_LABELS:
        footer_right = "%s · %s" % (page_type, PAGE_LABELS[page_type])
    master_end_with_footer(lines, page, evidence, page_type, footer_right)


def master_end_with_footer(lines, page, evidence, page_type, footer_right):
    lines.append("    </Box>")
    footer_left = page.get("footer_left", "")
    for banned in BANNED_FOOTER:
        if banned and banned in footer_left:
            raise DeckError(
                "footer_left 含内部话术「%s」——观众不需要知道令牌机制；"
                "改写为术语注解或数据来源（如「数据：原文 Table 3」）" % banned
            )
    lines.append("    <Box style={{ height: 62, padding: '0 40px', borderTop: '1px solid #D6DCE5', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 }}>")
    text(lines, 8, footer_left, evidence, 12, "#8B97A8", field="footer_left")
    text(lines, 8, footer_right or "", evidence, 12, "#8B97A8", field="footer_right")
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
    master_start(lines, page, deck, index, total, evidence, page_type)
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 18, alignItems: 'stretch' }}>")
    for card_index, card in enumerate(cards):
        lines.append("            <Box style={{ flex: 1, padding: 18, border: '1px solid #D6DCE5', flexDirection: 'column', gap: 10 }}>")
        if expected == 3:
            text(lines, 16, ROMAN[card_index], evidence, 13, "#8B97A8", extra="letterSpacing: 2", field="card_number")
        text(lines, 16, card.get("title"), evidence, 21, "#1E4FA8", True, field="cards[%d].title" % card_index)
        for body_index, value in enumerate(body_paragraphs(card)):
            rich_text(lines, 16, value, evidence, 17, "#1A2230", extra="lineHeight: 1.6", field="cards[%d].body[%d]" % (card_index, body_index))
        if card.get("emphasis"):
            lines.append("            <Box style={{ alignSelf: 'flex-start', padding: '8px 12px', borderLeft: '3px solid #D9534F', background: '#FFF8F1', marginTop: 'auto' }}>")
            text(lines, 16, card["emphasis"], evidence, 15, "#D9534F", extra="lineHeight: 1.5", field="cards[%d].emphasis" % card_index)
            lines.append("            </Box>")
        lines.append("            </Box>")
    lines.append("        </Box>")
    if page.get("note"):
        lines.append("        <Box style={{ marginTop: 4, padding: '10px 14px', background: '#FFF8E1' }}>")
        text(lines, 12, page["note"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="note")
        lines.append("        </Box>")
    master_end(lines, page, evidence, page_type)
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
    master_start(lines, page, deck, index, total, evidence, "P4")

    def row(values, row_index=None):
        header = row_index is None
        lines.append("        <Box style={{ flexDirection: 'row', alignItems: 'center', padding: '10px 14px', %s }}>" % ("background: '#F7F9FC', borderBottom: '1px solid #D6DCE5'" if header else "borderBottom: '1px solid #E5E7EB'"))
        for column, value in enumerate(values):
            sizing = "width: %s" % widths[column] if widths else "flex: 1"
            lines.append("            <Box style={{ %s }}>" % sizing)
            highlighted = not header and (row_index, column) in highlights
            if highlighted:
                lines.append("                <Box style={{ alignSelf: 'flex-start', borderBottom: '2px solid #D9534F', paddingBottom: 2 }}>")
            rich_text(
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
    master_end(lines, page, evidence, "P4")
    return "\n".join(lines) + "\n"


def render_steps(page, deck, index, total, evidence):
    steps = page.get("steps")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 5 or any(not isinstance(step, dict) for step in steps):
        raise DeckError("P5 requires 3 to 5 step objects")
    lines = []
    master_start(lines, page, deck, index, total, evidence, "P5")
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 0, alignItems: 'stretch' }}>")
    for step_index, step in enumerate(steps):
        if step_index > 0:
            lines.append("            <Box style={{ width: 34, alignItems: 'center', justifyContent: 'center' }}>")
            lines.append("                <Text style={{ fontSize: 22, color: '#8B97A8' }}>{\"›\"}</Text>")
            lines.append("            </Box>")
        lines.append("            <Box style={{ flex: 1, padding: 16, border: '1px solid #D6DCE5', flexDirection: 'column', gap: 10 }}>")
        lines.append("            <Box style={{ alignSelf: 'flex-start', width: 30, height: 30, borderRadius: 15, background: '#0024B3', alignItems: 'center', justifyContent: 'center' }}>")
        text(lines, 16, "%02d" % (step_index + 1), evidence, 13, "#FFFFFF", True, field="step_number")
        lines.append("            </Box>")
        text(lines, 16, step.get("title"), evidence, 20, "#1E4FA8", True, field="steps[%d].title" % step_index)
        rich_text(lines, 16, step.get("body"), evidence, 16, "#1A2230", extra="lineHeight: 1.6", field="steps[%d].body" % step_index)
        lines.append("            </Box>")
    lines.append("        </Box>")
    if page.get("note"):
        lines.append("        <Box style={{ marginTop: 4, padding: '10px 14px', background: '#FFF8E1' }}>")
        text(lines, 12, page["note"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="note")
        lines.append("        </Box>")
    master_end(lines, page, evidence, "P5")
    return "\n".join(lines) + "\n"


def validate_chart(page, evidence):
    series = page.get("series")
    if not isinstance(series, list) or not 2 <= len(series) <= 4:
        raise DeckError("P7 series must contain 2 to 4 groups")
    bars = []
    for group_index, group in enumerate(series):
        if not isinstance(group, dict):
            raise DeckError("P7 series[%d] must be an object" % group_index)
        label = group.get("label")
        values = group.get("values")
        if not isinstance(label, str) or not label:
            raise DeckError("P7 series[%d].label must be a non-empty string" % group_index)
        if not isinstance(values, list) or not values or len(values) > 6:
            raise DeckError("P7 series[%d].values must contain 1 to 6 bars" % group_index)
        row = []
        for bar_index, bar in enumerate(values):
            if not isinstance(bar, dict):
                raise DeckError("P7 series[%d].values[%d] must be an object" % (group_index, bar_index))
            caption = bar.get("caption")
            value = bar.get("value")
            display = bar.get("display", str(value) if value is not None else "")
            if not isinstance(caption, str) or not caption:
                raise DeckError("P7 bar caption must be a non-empty string")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise DeckError("P7 bar value must be a number")
            if not isinstance(display, str):
                raise DeckError("P7 bar display must be a string")
            evidence_id = bar.get("evidence")
            if evidence_id is not None:
                if not isinstance(evidence_id, str):
                    raise DeckError("P7 bar evidence must be an evidence id string")
                item = evidence.get(evidence_id)
                if item is None:
                    raise DeckError("P7 bar uses unknown evidence %s" % evidence_id)
                if item.get("status") not in ("verified", "derived"):
                    raise DeckError("P7 bar uses non-verified evidence %s" % evidence_id)
                item_value = item.get("value")
                if not isinstance(item_value, (int, float)) or isinstance(item_value, bool) or abs(item_value - value) > 1e-9:
                    raise DeckError(
                        "P7 bar value %s does not match evidence %s value %s — 柱高必须与台账同源"
                        % (value, evidence_id, item_value)
                    )
            row.append({"caption": caption, "value": value, "display": display, "highlight": bool(bar.get("highlight"))})
        bars.append({"label": label, "bars": row})
    axis = page.get("axis")
    if not isinstance(axis, str) or not axis:
        raise DeckError("P7 needs axis (量与单位，如「UTS / MPa」)")
    source_note = page.get("source_note")
    if not isinstance(source_note, str) or not source_note:
        raise DeckError("P7 needs source_note (数据来源，如「数据：原文 Table 3」)")
    return bars, axis, source_note


def render_chart(page, deck, index, total, evidence):
    bars, axis, source_note = validate_chart(page, evidence)
    lines = []
    master_start(lines, page, deck, index, total, evidence, "P7")
    colors = ("#0024B3", "#4A5568", "#8B97A8")
    max_value = max(bar["value"] for group in bars for bar in group["bars"])
    plot_height = 150 if len(bars) < 3 else 110
    plot_scale = plot_height - 24  # 顶部留出数值标签空间，防止 child-containment 溢出
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 40, alignItems: 'stretch' }}>")
    lines.append("            <Box style={{ flex: 1, flexDirection: 'column', justifyContent: 'flex-end' }}>")
    for group_index, group in enumerate(bars):
        color = colors[group_index % len(colors)]
        if group_index > 0:
            lines.append("            <Box style={{ height: 14 }} />")
        lines.append("            <Box style={{ flexDirection: 'row', alignItems: 'flex-end', height: %d, borderBottom: '2px solid #4A5568' }}>" % plot_height)
        for bar in group["bars"]:
            height = max(14, int(round(plot_scale * bar["value"] / max_value)))
            bar_color = "#D9534F" if bar["highlight"] else color
            display = resolve_text(bar["display"], evidence, "series[%d].values.display" % group_index)
            lines.append("                <Box style={{ flex: 1, alignItems: 'center', justifyContent: 'flex-end', height: '100%' }}>")
            lines.append("                    <Box style={{ alignItems: 'center' }}>")
            if bar["highlight"]:
                lines.append("                    <Box style={{ borderBottom: '2px solid #D9534F', paddingBottom: 2, marginBottom: 4 }}>")
                lines.append("                        <Text style={{ fontSize: 17, color: '#D9534F', fontWeight: 'bold' }}>{%s}</Text>" % js_string(display))
                lines.append("                    </Box>")
            else:
                lines.append("                        <Text style={{ fontSize: 15, color: '#1A2230', marginBottom: 4 }}>{%s}</Text>" % js_string(display))
            lines.append("                    <Box style={{ width: 56, height: %d, background: '%s' }} />" % (height, bar_color))
            lines.append("                    </Box>")
            lines.append("                </Box>")
        lines.append("            </Box>")
        lines.append("            <Box style={{ flexDirection: 'row', marginTop: 6 }}>")
        for bar in group["bars"]:
            lines.append("                <Box style={{ flex: 1, alignItems: 'center' }}>")
            lines.append("                    <Text style={{ fontSize: 13, color: '#4A5568' }}>{%s}</Text>" % js_string(resolve_text(bar["caption"], evidence, "series[%d].values.caption" % group_index)))
            lines.append("                </Box>")
        lines.append("            </Box>")
    lines.append("                <Text style={{ fontSize: 12, color: '#8B97A8', marginTop: 4 }}>{%s}</Text>" % js_string(axis))
    lines.append("            </Box>")
    lines.append("            <Box style={{ width: 300, flexDirection: 'column', gap: 14, justifyContent: 'center' }}>")
    for group_index, group in enumerate(bars):
        color = colors[group_index % len(colors)]
        lines.append("            <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>")
        lines.append("                <Box style={{ width: 14, height: 14, background: '%s' }} />" % color)
        text(lines, 16, group["label"], evidence, 16, "#1A2230", field="series[%d].label" % group_index)
        lines.append("            </Box>")
    if page.get("note"):
        lines.append("            <Box style={{ padding: '10px 14px', borderLeft: '3px solid #D9534F', background: '#FFF8F1' }}>")
        text(lines, 16, page["note"], evidence, 15, "#1A2230", extra="lineHeight: 1.6", field="note")
        lines.append("            </Box>")
    lines.append("                <Text style={{ fontSize: 12, color: '#8B97A8' }}>{%s}</Text>" % js_string(source_note))
    lines.append("            </Box>")
    lines.append("        </Box>")
    footer_right = page.get("footer_right") or ("P7 · 数据图（%s）" % axis)
    master_end_with_footer(lines, page, evidence, "P7", footer_right)
    return "\n".join(lines) + "\n"


def validate_structure(page):
    rings = page.get("rings")
    if not isinstance(rings, list) or not 2 <= len(rings) <= 4:
        raise DeckError("P8 rings must contain 2 to 4 layers")
    layers = []
    for ring_index, ring in enumerate(rings):
        if not isinstance(ring, dict):
            raise DeckError("P8 rings[%d] must be an object" % ring_index)
        label = ring.get("label")
        note = ring.get("note")
        if not isinstance(label, str) or not label:
            raise DeckError("P8 rings[%d].label must be a non-empty string" % ring_index)
        if not isinstance(note, str) or not note:
            raise DeckError("P8 rings[%d].note must be a non-empty string" % ring_index)
        layers.append({"label": label, "note": note, "caption": ring.get("caption", "")})
    caption = page.get("caption")
    if not isinstance(caption, str) or not caption:
        raise DeckError("P8 needs caption (图注，必须注明「示意」)")
    if "示意" not in caption:
        raise DeckError("P8 caption 必须包含「示意」二字——结构页不得伪装成实测图")
    return layers, caption


def render_structure(page, deck, index, total, evidence):
    layers, caption = validate_structure(page)
    lines = []
    master_start(lines, page, deck, index, total, evidence, "P8")
    fills = ("#F1EFE8", "#D3D1C7", "#FFFFFF", "#B4B2A9")
    count = len(layers)
    diameter = 260
    step = 60
    lines.append("        <Box style={{ flex: 1, flexDirection: 'row', gap: 40, alignItems: 'center' }}>")
    lines.append("            <Box style={{ width: 320, alignItems: 'center', justifyContent: 'center' }}>")
    lines.append("                <Box style={{ width: %d, height: %d, borderRadius: 999, background: '%s', justifyContent: 'center', alignItems: 'center' }}>" % (diameter, diameter, fills[0]))
    for layer_index in range(1, count):
        size = diameter - step * layer_index
        fill = fills[layer_index % len(fills)]
        border = ", border: '1px solid #B4B2A9'" if fill == "#FFFFFF" else ""
        lines.append("                <Box style={{ width: %d, height: %d, borderRadius: 999, background: '%s'%s, justifyContent: 'center', alignItems: 'center' }}>" % (size, size, fill, border))
    for layer_index in range(count - 1, -1, -1):
        lines.append("                </Box>")
    lines.append("            </Box>")
    lines.append("            <Box style={{ flex: 1, flexDirection: 'column', gap: 12, justifyContent: 'center' }}>")
    for layer_index, layer in enumerate(layers):
        lines.append("                <Box style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>")
        lines.append("                    <Box style={{ width: 12, height: 12, background: '%s'%s }} />" % (fills[layer_index % len(fills)], ", border: '1px solid #B4B2A9'" if fills[layer_index % len(fills)] == "#FFFFFF" else ""))
        text(lines, 20, layer["label"], evidence, 17, "#1A2230", field="rings[%d].label" % layer_index)
        lines.append("                </Box>")
        text(lines, 20, layer["note"], evidence, 15, "#4A5568", extra="marginTop: -6, paddingLeft: 22, lineHeight: 1.5", field="rings[%d].note" % layer_index)
    lines.append("            </Box>")
    lines.append("        </Box>")
    master_end_with_footer(lines, page, evidence, "P8", caption)
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
    if page_type not in ("P2", "P3", "P4", "P5", "P6", "P7", "P8"):
        raise DeckError("page %d has unsupported type %r" % (index, page_type))
    if not isinstance(page.get("section"), str) or not page.get("section"):
        raise DeckError("page %d needs section" % index)
    if not isinstance(page.get("conclusion"), str) or not page.get("conclusion"):
        raise DeckError("page %d needs conclusion" % index)
    if page_type == "P4":
        return render_table(page, deck, index, total, evidence)
    if page_type == "P5":
        return render_steps(page, deck, index, total, evidence)
    if page_type == "P7":
        return render_chart(page, deck, index, total, evidence)
    if page_type == "P8":
        return render_structure(page, deck, index, total, evidence)
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


def write_deck(deck, evidence=None, output=None, force=False):
    output = Path(output) if output else Path(".")
    deck = dict(deck)
    deck["logo"] = resolve_logo(deck, output)
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
            output=args.output,
            evidence=load_evidence(args.evidence),
            force=args.force,
        )
    except DeckError as exc:
        print("FAIL", exc, file=sys.stderr)
        return 1
    print("OK built %d slides in %s" % (len(targets), Path(args.output) / "slides"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
