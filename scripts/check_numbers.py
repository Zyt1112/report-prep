#!/usr/bin/env python3
"""校验证据台账与内容 JSON 的一致性。

三类检查：

1. **声明式**：每个 `{{E001}}` 令牌必须指向存在的、可用的证据；`display` 与 `value` 数值等价。
2. **裸数字**：正文里绕过令牌手写的数字会被提示出来——带单位的一律报；纯数字字段只在
   恰好等于某条证据值时提示“改用令牌”。默认 WARN，`--strict` 升级为 ERROR。
3. **原文核对**（可选）：`--source` 指向从 PDF 提取的 md/txt，核对每条 `quote` 是否真在其中。

它不能证明 OCR 或手工转录与 PDF 完全一致；`--source` 只能证明“这句话在给定文本里出现过”。

用法：
    python scripts/check_numbers.py evidence.json content.json
    python scripts/check_numbers.py evidence.json content.json --source pdfs/p2.md
    python scripts/check_numbers.py evidence.json content.json --source pdfs/p2.md --strict
    python scripts/check_numbers.py evidence.json content.json --no-bare
"""

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
import unicodedata

ID_PATTERN = re.compile(r"E\d+")
TOKEN_PATTERN = re.compile(r"\{\{(E\d+)\}\}")
STATUSES = {"verified", "unverified", "derived", "reported_missing"}
KINDS = {"author_result", "author_interpretation", "inference", "recommendation", "demo"}
USABLE_STATUSES = {"verified", "derived"}
TEXT_FIELDS = ("display", "unit", "source", "locator", "quote", "status", "kind")

# 带单位的数字：几乎一定是来源数据或推断数据，必须能回到台账
UNIT_PATTERN = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:±\s*\d+(?:\.\d+)?\s*)?"
    r"(MPa|GPa|µm|μm|nm|mm|°C|℃|HV\d*|HRC|%|kHz|Hz|cycles|min|次|倍)"
)
# 纯数字字段（表格单元格、短文本），只在等于某条证据值时提示
BARE_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")


def parse_decimal(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("not a number")
    if isinstance(value, str):
        value = value.strip().replace("−", "-").replace("–", "-")
        value = re.sub(r"[\s,\u00a0\u202f]", "", value)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("not a number")
    if not number.is_finite():
        raise ValueError("not finite")
    return number


def iter_strings(value, path="$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(item, "%s.%s" % (path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, "%s[%d]" % (path, index))


# PDF 提取常见的字符变体：度符号被抽成 ◦ / ˚ / º，引号变弯引号，微符号两种写法
CHAR_EQUIVALENTS = str.maketrans(
    {
        "◦": "°",
        "˚": "°",
        "º": "°",
        "μ": "µ",
        "−": "-",
        "–": "-",
        "—": "-",
        "‒": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
)


def normalize_source(text):
    """原文与 quote 的归一化：全半角、字符变体、Markdown 噪声、空白、大小写。

    `###` 是 PDF 提取时插在行尾的段落标记，`\\*` 是转义符，都不属于正文内容，
    留着会让跨行句子永远匹配不上。
    """
    text = unicodedata.normalize("NFKC", text).translate(CHAR_EQUIVALENTS)
    text = re.sub(r"[#\\]", "", text)
    return re.sub(r"\s+", "", text).lower()


def scan_bare_numbers(content_data, evidence, strict=False):
    """找绕过令牌手写的数字。返回 (warnings, 命中数)。"""
    findings = []
    values = {}
    for evidence_id, item in evidence.items():
        try:
            values[evidence_id] = parse_decimal(item.get("value"))
        except (ValueError, TypeError):
            continue

    for path, text in iter_strings(content_data):
        if not isinstance(text, str):
            continue
        stripped_tokens = TOKEN_PATTERN.sub(" ", text)

        for match in UNIT_PATTERN.finditer(stripped_tokens):
            number_text, unit = match.group(1), match.group(2)
            try:
                number = parse_decimal(number_text)
            except ValueError:
                continue
            same = [eid for eid, val in values.items() if val == number]
            if same:
                findings.append("%s 裸数字 %s%s 与 %s 同值，应改用 {{%s}}" % (path, number_text, unit, same[0], same[0]))
            else:
                findings.append("%s 裸数字 %s%s 无对应证据，应入台账或标为推断" % (path, number_text, unit))

        bare = stripped_tokens.strip()
        if BARE_NUMBER_PATTERN.fullmatch(bare):
            try:
                number = parse_decimal(bare)
            except ValueError:
                continue
            same = [eid for eid, val in values.items() if val == number]
            if same:
                findings.append("%s 纯数字 %s 与 %s 同值，应改用 {{%s}}" % (path, bare, same[0], same[0]))

    # 同一页同一数字重复出现时只报一次，避免刷屏
    unique = []
    seen = set()
    for item in findings:
        key = re.sub(r"^\$[^ ]+ ", "", item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique, len(unique)


def check_quotes(evidence, source_text):
    """核对 quote 是否出现在原文里。返回 (缺失列表, 核对条数)。

    `status: derived` 跳过：它的 quote 记的是推导依据，不是原文原句；
    这类项的 note 必须写清公式与输入。
    """
    haystack = normalize_source(source_text)
    missing = []
    checked = 0
    for evidence_id in sorted(evidence):
        item = evidence[evidence_id]
        if item.get("status") == "derived":
            continue
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            continue
        checked += 1
        # 省略号表示 quote 由多段拼接，逐段核对
        parts = [part for part in re.split(r"…|\.\.\.", quote) if len(part.strip()) >= 6]
        if not parts:
            parts = [quote]
        for part in parts:
            if normalize_source(part) not in haystack:
                missing.append((evidence_id, part.strip()[:48]))
                break
    return missing, checked


def audit(evidence_data, content_data, source_text=None, strict=False, scan_bare=True):
    errors = []
    warnings = []
    items = evidence_data.get("items") if isinstance(evidence_data, dict) else None
    if not isinstance(items, list):
        return ["Evidence JSON must contain an items array"], warnings, {}, []

    evidence = {}
    for index, item in enumerate(items):
        label = "items[%d]" % index
        if not isinstance(item, dict):
            errors.append("%s must be an object" % label)
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not ID_PATTERN.fullmatch(evidence_id):
            errors.append("%s has an invalid id" % label)
            continue
        label = evidence_id
        if evidence_id in evidence:
            errors.append("Duplicate evidence id: %s" % evidence_id)
            continue
        evidence[evidence_id] = item

        for field in TEXT_FIELDS:
            if not isinstance(item.get(field), str) or not item.get(field).strip():
                errors.append("%s needs non-empty %s" % (label, field))
        status = item.get("status")
        if status not in STATUSES:
            errors.append("%s has unsupported status %r" % (label, status))
        if item.get("kind") not in KINDS:
            errors.append("%s has unsupported kind %r" % (label, item.get("kind")))

        qualitative = item.get("qualitative") is True
        if status == "reported_missing":
            if item.get("value") is not None:
                errors.append("%s reported_missing must use value null" % label)
            if qualitative:
                errors.append("%s cannot be both reported_missing and qualitative" % label)
        elif qualitative:
            # 定性证据：display 放论断原文，value 必须为 null，不做数值比对
            if item.get("value") is not None:
                errors.append("%s qualitative must use value null" % label)
        else:
            try:
                display_number = parse_decimal(item.get("display"))
                value_number = parse_decimal(item.get("value"))
                if display_number != value_number:
                    errors.append(
                        "%s display/value mismatch: %s != %s" % (label, item.get("display"), item.get("value"))
                    )
            except ValueError:
                errors.append(
                    "%s display and value must be finite equivalent numbers "
                    "(定性论断请加 \"qualitative\": true 并把 value 设为 null)" % label
                )
        if status == "derived" and not isinstance(item.get("note"), str):
            errors.append("%s derived item needs a note with formula/inputs" % label)

    references = []
    for path, value in iter_strings(content_data):
        for match in TOKEN_PATTERN.finditer(value):
            evidence_id = match.group(1)
            references.append((path, evidence_id))
            if evidence_id not in evidence:
                errors.append("%s references unknown %s" % (path, evidence_id))
                continue
            status = evidence[evidence_id].get("status")
            if status not in USABLE_STATUSES:
                errors.append("%s uses %s with status %s" % (path, evidence_id, status))

    used_ids = {item[1] for item in references}
    unused = sorted(set(evidence) - used_ids)
    if unused:
        warnings.append("Unused evidence: %s" % ", ".join(unused))

    qualitative_count = sum(1 for item in evidence.values() if item.get("qualitative") is True)
    bare_count = 0
    if scan_bare:
        bare_findings, bare_count = scan_bare_numbers(content_data, evidence, strict)
        target = errors if strict else warnings
        target.extend(bare_findings)

    checked_quotes = 0
    if source_text is not None:
        missing, checked_quotes = check_quotes(evidence, source_text)
        for evidence_id, fragment in missing:
            message = "%s quote 未在 --source 文本中找到：%s" % (evidence_id, fragment)
            (errors if strict else warnings).append(message)

    stats = {
        "evidence": len(evidence),
        "references": len(references),
        "used": len(used_ids),
        "unused": len(unused),
        "qualitative": qualitative_count,
        "bare": bare_count,
        "quotes": checked_quotes,
    }
    return errors, warnings, stats, references


def load_object(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object: %s" % path)
    return data


def load_source(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def check(evidence_path, content_path, source_path=None, strict=False, scan_bare=True):
    source_text = load_source(source_path) if source_path else None
    return audit(load_object(evidence_path), load_object(content_path), source_text, strict, scan_bare)


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验证据台账与内容 JSON 的一致性")
    parser.add_argument("evidence", help="Evidence JSON path")
    parser.add_argument("content", help="Content JSON path")
    parser.add_argument("--source", help="原文文本（md/txt），用于核对 quote 是否真实出现")
    parser.add_argument("--strict", action="store_true", help="把裸数字与 quote 缺失升级为 ERROR")
    parser.add_argument("--no-bare", action="store_true", help="跳过裸数字扫描")
    args = parser.parse_args(argv)

    try:
        errors, warnings, stats, _ = check(
            args.evidence, args.content, args.source, args.strict, not args.no_bare
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("FAIL %s" % exc, file=sys.stderr)
        return 1

    flag = "FAIL" if errors else "OK  "
    print("%s %s" % (flag, args.content))
    print(
        "     evidence {evidence} | references {references} | used {used} | unused {unused}"
        " | qualitative {qualitative} | bare {bare} | quotes {quotes}".format(**stats)
    )
    for warning in warnings:
        print("     ! WARN %s" % warning)
    for error in errors:
        print("     ! ERROR %s" % error)
    if not errors:
        print("     Scope: 令牌与台账一致性" + ("+ quote 出现性" if args.source else "") + "；原文数值仍需人工核对。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
