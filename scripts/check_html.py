#!/usr/bin/env python3
"""交付前校验 A4 HTML：标签闭合、裸 &、表格结构、篇幅统计。

用法：
    python check_html.py 文件1.html [文件2.html ...]
    python check_html.py *.html

退出码：0 全部通过；1 存在问题。
"""
import io
import re
import sys

# 这些标签允许自闭合或成对，检查时按出现次数比对开闭
PAIRED = ["html", "head", "body", "style", "div", "table", "thead", "tbody",
          "tr", "th", "td", "p", "ol", "ul", "li", "h1", "h2", "h3", "h4",
          "span", "b", "i", "em", "strong", "sub", "sup", "title"]

VOID = ["br", "hr", "img", "meta", "link", "input"]


def check(path):
    s = io.open(path, encoding="utf-8").read()
    problems = []

    # 1) 标签闭合
    for t in PAIRED:
        opened = len(re.findall(r"<%s[\s>]" % t, s, re.I))
        closed = len(re.findall(r"</%s>" % t, s, re.I))
        if opened != closed:
            problems.append("标签不闭合 <%s>：开 %d / 闭 %d" % (t, opened, closed))

    # 2) 裸 & （HTML 实体除外）
    raw_amp = re.findall(r"&(?!amp;|lt;|gt;|nbsp;|quot;|#\d+;|#x[0-9a-fA-F]+;)", s)
    if raw_amp:
        problems.append("裸 & 共 %d 处，应写成 &amp;" % len(raw_amp))

    # 3) 表格必须有 thead
    tables = re.findall(r"<table[\s>].*?</table>", s, re.S | re.I)
    no_head = sum(1 for t in tables if "<thead" not in t.lower())
    if no_head:
        problems.append("%d 张表缺 <thead>（Word 转换与打印会丢表头）" % no_head)

    # 4) 打印样式
    if "@page" not in s:
        problems.append("缺 @page 打印样式，Ctrl+P 会跑版")
    if "page-break-inside" not in s:
        problems.append("缺 page-break-inside，表格会被撕成两页（建议）")

    # 5) 统计
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    stats = {
        "正文字数": len(text),
        "章节 h2": len(re.findall(r"<h2[\s>]", s, re.I)),
        "表格": len(tables),
        "承接/说明框": len(re.findall(r'class="(why|key)"', s)),
    }
    return problems, stats


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    bad = 0
    for path in argv[1:]:
        try:
            problems, stats = check(path)
        except FileNotFoundError:
            print("[缺失] %s" % path)
            bad += 1
            continue
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        flag = "OK  " if not problems else "FAIL"
        print("%s %s" % (flag, name))
        print("     " + " | ".join("%s %s" % (k, v) for k, v in stats.items()))
        for p in problems:
            print("     ! " + p)
        if problems:
            bad += 1
    print("\n%d 个文件，%d 个有问题" % (len(argv) - 1, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
