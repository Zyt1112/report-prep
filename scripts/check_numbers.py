#!/usr/bin/env python3
"""Check declared evidence references and numeric display consistency.

This validates the evidence ledger and every {{E001}} token in content JSON.
It does not prove that OCR or manual transcription matches the original PDF.

Usage:
    python scripts/check_numbers.py evidence.json content.json
"""

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys

ID_PATTERN = re.compile(r"E\d+")
TOKEN_PATTERN = re.compile(r"\{\{(E\d+)\}\}")
STATUSES = {"verified", "unverified", "derived", "reported_missing"}
KINDS = {"author_result", "author_interpretation", "inference", "recommendation", "demo"}
USABLE_STATUSES = {"verified", "derived"}
REQUIRED_TEXT = ("display", "unit", "source", "locator", "quote", "status", "kind")


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


def audit(evidence_data, content_data):
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
        for field in REQUIRED_TEXT:
            if not isinstance(item.get(field), str) or not item.get(field).strip():
                errors.append("%s needs non-empty %s" % (label, field))
        status = item.get("status")
        if status not in STATUSES:
            errors.append("%s has unsupported status %r" % (label, status))
        if item.get("kind") not in KINDS:
            errors.append("%s has unsupported kind %r" % (label, item.get("kind")))
        if status == "reported_missing":
            if item.get("value") is not None:
                errors.append("%s reported_missing must use value null" % label)
        else:
            try:
                display_number = parse_decimal(item.get("display"))
                value_number = parse_decimal(item.get("value"))
                if display_number != value_number:
                    errors.append(
                        "%s display/value mismatch: %s != %s" % (label, item.get("display"), item.get("value"))
                    )
            except ValueError:
                errors.append("%s display and value must be finite equivalent numbers" % label)
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
    stats = {
        "evidence": len(evidence),
        "references": len(references),
        "used": len(used_ids),
        "unused": len(unused),
    }
    return errors, warnings, stats, references


def load_object(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object: %s" % path)
    return data


def check(evidence_path, content_path):
    return audit(load_object(evidence_path), load_object(content_path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", help="Evidence JSON path")
    parser.add_argument("content", help="Content JSON path")
    args = parser.parse_args(argv)
    try:
        errors, warnings, stats, _ = check(args.evidence, args.content)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("FAIL %s" % exc, file=sys.stderr)
        return 1
    flag = "FAIL" if errors else "OK  "
    print("%s %s" % (flag, args.content))
    print("     evidence {evidence} | references {references} | used {used} | unused {unused}".format(**stats))
    for warning in warnings:
        print("     ! WARN %s" % warning)
    for error in errors:
        print("     ! ERROR %s" % error)
    if not errors:
        print("     Scope: declared references only; original-PDF verification remains required.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
