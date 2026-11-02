#!/usr/bin/env python3
"""Validate generated A4 HTML with structural parsing and scoped diagnostics.

Usage:
    python scripts/check_html.py file1.html [file2.html ...]
    python scripts/check_html.py assets/*.html --allow-placeholders

Exit code 1 is reserved for errors. Warnings do not fail the check.
Only Python's standard library is required.
"""

import argparse
from html import entities
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}")
BRACKET_PLACEHOLDER = re.compile(r"【[^】]*】")


class AuditParser(HTMLParser):
    def __init__(self, allow_placeholders=False):
        super().__init__(convert_charrefs=False)
        self.allow_placeholders = allow_placeholders
        self.errors = []
        self.warnings = []
        self.stack = []
        self.tables = []
        self.completed_tables = []
        self.style_depth = 0
        self.script_depth = 0
        self.style_parts = []
        self.text_parts = []
        self.h2_count = 0
        self.box_count = 0
        self.has_lang = False
        self.has_charset = False
        self.has_doctype = False

    def line_message(self, message):
        return "line %d: %s" % (self.getpos()[0], message)

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype html"):
            self.has_doctype = True

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "html" and attributes.get("lang"):
            self.has_lang = True
        if tag == "meta" and (attributes.get("charset") or attributes.get("http-equiv", "").lower() == "content-type"):
            self.has_charset = True
        if tag == "style":
            self.style_depth += 1
        if tag == "script":
            self.script_depth += 1
        if tag == "h2":
            self.h2_count += 1
        classes = attributes.get("class", "").split()
        if "why" in classes or "key" in classes:
            self.box_count += 1
        if tag == "table":
            self.tables.append({"thead": 0, "tbody": 0, "line": self.getpos()[0]})
        elif tag in {"thead", "tbody"} and self.tables:
            self.tables[-1][tag] += 1
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag in VOID:
            self.handle_starttag(tag, attrs)
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(self.line_message("unexpected closing </%s>" % tag))
            return
        if self.stack[-1][0] != tag:
            open_names = [item[0] for item in self.stack]
            if tag not in open_names:
                self.errors.append(self.line_message("closing </%s> without matching open tag" % tag))
                return
            while self.stack and self.stack[-1][0] != tag:
                open_tag, line = self.stack.pop()
                self.errors.append(self.line_message("<%s> from line %d closed by </%s>" % (open_tag, line, tag)))
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        if tag == "style":
            self.style_depth = max(0, self.style_depth - 1)
        if tag == "script":
            self.script_depth = max(0, self.script_depth - 1)
        if tag == "table" and self.tables:
            self.completed_tables.append(self.tables.pop())

    def handle_data(self, data):
        if self.style_depth:
            self.style_parts.append(data)
            return
        if self.script_depth:
            return
        self.text_parts.append(data)
        if "&" in data:
            self.errors.append(self.line_message("unescaped & in text"))
        if not self.allow_placeholders:
            token = PLACEHOLDER.search(data)
            if token:
                self.errors.append(self.line_message("unresolved placeholder %s" % token.group(0)))
            if BRACKET_PLACEHOLDER.search(data):
                self.warnings.append(self.line_message("possible 【...】 placeholder remains"))

    def handle_entityref(self, name):
        if name + ";" not in entities.html5 and name not in entities.html5:
            self.errors.append(self.line_message("unknown HTML entity &%s;" % name))
        if not self.style_depth and not self.script_depth:
            self.text_parts.append(" ")

    def handle_charref(self, name):
        try:
            value = int(name[1:], 16) if name.lower().startswith("x") else int(name)
            if value < 0 or value > 0x10FFFF:
                raise ValueError
        except ValueError:
            self.errors.append(self.line_message("invalid character reference &#%s;" % name))
        if not self.style_depth and not self.script_depth:
            self.text_parts.append(" ")

    def finish(self):
        self.close()
        for tag, line in self.stack:
            self.errors.append("line %d: unclosed <%s>" % (line, tag))
        all_tables = self.completed_tables + self.tables
        for table in all_tables:
            if not table["thead"]:
                self.errors.append("line %d: table missing <thead>" % table["line"])
            if not table["tbody"]:
                self.errors.append("line %d: table missing <tbody>" % table["line"])
        style = "\n".join(self.style_parts)
        if "@page" not in style:
            self.errors.append("missing @page in actual <style> content")
        if "page-break-inside" not in style and "break-inside" not in style:
            self.warnings.append("missing break-inside/page-break-inside print protection")
        if not self.has_doctype:
            self.warnings.append("missing HTML5 doctype")
        if not self.has_lang:
            self.warnings.append("missing html lang attribute")
        if not self.has_charset:
            self.warnings.append("missing charset declaration")
        stats = {
            "text_chars": len(re.sub(r"\s+", "", "".join(self.text_parts))),
            "h2": self.h2_count,
            "tables": len(all_tables),
            "note_boxes": self.box_count,
        }
        return self.errors, self.warnings, stats


def check(path, allow_placeholders=False):
    source = Path(path).read_text(encoding="utf-8")
    parser = AuditParser(allow_placeholders=allow_placeholders)
    parser.feed(source)
    return parser.finish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="HTML files to validate")
    parser.add_argument("--allow-placeholders", action="store_true", help="Allow template placeholders")
    args = parser.parse_args(argv)
    failed = 0
    for path in args.paths:
        try:
            errors, warnings, stats = check(path, allow_placeholders=args.allow_placeholders)
        except (OSError, UnicodeError) as exc:
            print("FAIL %s: %s" % (path, exc))
            failed += 1
            continue
        print("%s %s" % ("FAIL" if errors else "OK  ", Path(path).name))
        print("     text {text_chars} | h2 {h2} | tables {tables} | note boxes {note_boxes}".format(**stats))
        for warning in warnings:
            print("     ! WARN %s" % warning)
        for error in errors:
            print("     ! ERROR %s" % error)
        if errors:
            failed += 1
    print("\n%d files, %d failed" % (len(args.paths), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
