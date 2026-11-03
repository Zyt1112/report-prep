#!/usr/bin/env python3
"""report-prep 环境自检。

检查本 Skill 能不能在当前机器上直接跑：Python 版本、文件完整性、
脚本可编译、输出目录可写、可选工具（slidep / PDF 取文）是否就位。

用法：
    python scripts/doctor.py
    python scripts/doctor.py --fix-hint     # 附带修复建议
    python scripts/doctor.py --json         # 机器可读

退出码：0 = 必需项全过；1 = 有必需项失败。
只用标准库，Python 3.9+。
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_PY = (3, 9)

# 必需文件：缺任何一个，Skill 都跑不完整
REQUIRED = [
    "SKILL.md",
    "README.md",
    "HANDOVER.md",
    "CHANGELOG.md",
    "references/pipeline.md",
    "references/structure.md",
    "references/deck-skeletons.md",
    "references/deck-style.md",
    "references/ppt-build.md",
    "references/register.md",
    "references/evidence.md",
    "references/page-notes.md",
    "references/environment.md",
    "scripts/check_html.py",
    "scripts/check_numbers.py",
    "scripts/render_html.py",
    "assets/explainer.html",
    "assets/outline.html",
    "assets/content.schema.json",
    "assets/tyust-logo.png",
    "examples/evidence.json",
    "examples/explainer.content.json",
    "examples/outline.content.json",
]

RESULTS = []


def add(level, name, detail, hint=""):
    """level: ok / warn / fail"""
    RESULTS.append({"level": level, "name": name, "detail": detail, "hint": hint})


def check_python():
    v = sys.version_info
    if v[:2] >= MIN_PY:
        add("ok", "Python", "%d.%d.%d" % (v[0], v[1], v[2]))
    else:
        add(
            "fail",
            "Python",
            "%d.%d.%d 低于要求" % (v[0], v[1], v[2]),
            "升级到 Python %d.%d 或更高" % MIN_PY,
        )


def check_files():
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if not missing:
        add("ok", "文件完整性", "%d 个必需文件齐全" % len(REQUIRED))
    else:
        add(
            "fail",
            "文件完整性",
            "缺少 %d 个：%s" % (len(missing), "、".join(missing[:6])),
            "重新 clone 仓库，或从压缩包补齐：git clone https://github.com/Zyt1112/report-prep",
        )


def check_syntax():
    import py_compile

    bad = []
    for py in sorted((ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(py), doraise=True)
        except Exception as exc:  # noqa: BLE001 - 需要原始报错信息
            bad.append("%s: %s" % (py.name, exc))
    if bad:
        add("fail", "脚本语法", "；".join(bad[:3]), "文件可能被截断，重新拉取仓库")
    else:
        add("ok", "脚本语法", "scripts/*.py 全部可编译")


def check_writable():
    target = ROOT / ".doctor-tmp"
    try:
        target.mkdir(exist_ok=True)
        probe = target / "probe.txt"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        target.rmdir()
        add("ok", "目录可写", str(ROOT))
    except OSError as exc:
        add(
            "fail",
            "目录可写",
            "%s（%s）" % (ROOT, exc),
            "检查目录权限，或把 Skill 放到用户目录下（如 ~/.workbuddy/skills/）",
        )


def check_logo():
    png = ROOT / "assets" / "tyust-logo.png"
    if not png.is_file():
        return  # 已在文件完整性里报过
    data = png.read_bytes()[:33]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        add("fail", "机构校徽", "assets/tyust-logo.png 不是有效 PNG", "从官网重新下载，或删掉该文件改用无校徽母版")
        return
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width < 200 or height < 40:
        add("warn", "机构校徽", "%dx%d 偏小，投影可能发虚" % (width, height), "换 300px 以上宽度的白色透明版")
    else:
        add("ok", "机构校徽", "%dx%d" % (width, height))


def _run(cmd, timeout=25):
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            shell=False,
        )
        return proc.returncode, proc.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def find_slidep():
    found = shutil.which("slidep")
    if found:
        return found
    roots = [Path.home() / ".workbuddy" / "binaries" / "node" / "versions"]
    local = os.environ.get("LOCALAPPDATA")
    if local:  # Windows 独有；Linux/macOS 上 Path("") 会退化成当前目录
        roots.append(Path(local) / "Programs")
    for base in roots:
        if not base.is_dir():
            continue
        for cand in sorted(base.glob("*/slidep")) + sorted(base.glob("*/bin/slidep*")):
            if cand.is_file():
                return str(cand)
    return None


def check_slidep():
    exe = find_slidep()
    if not exe:
        add(
            "warn",
            "slidep（PPTX 生成）",
            "未找到",
            "PPT 阶段可改用 python-pptx，或安装 WorkBuddy workbuddy-pptx 技能后重试",
        )
        return
    code, out = _run([exe, "--version"])
    if code == 0:
        add("ok", "slidep（PPTX 生成）", out.splitlines()[0][:60] if out else exe)
        return
    if "native binding" in out.lower() or "Failed to load" in out:
        add(
            "fail",
            "slidep（PPTX 生成）",
            "原生模块加载失败",
            "Windows 运行 scripts/setup_env.ps1；其他平台看 references/environment.md",
        )
    else:
        add("warn", "slidep（PPTX 生成）", (out or "退出码 %d" % code)[:120], "运行 slidep --help 自查")


def find_pdf_tool():
    """找 WorkBuddy 的 PDF 技能：缓存目录与内置目录都试。"""
    patterns = [
        Path.home() / ".workbuddy" / "plugins" / "cache" / "workbuddy-builtin" / "workbuddy-pdf",
        Path("D:/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/workbuddy-pdf"),
        Path("/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/workbuddy-pdf"),
    ]
    for base in patterns:
        if not base.is_dir():
            continue
        hits = list(base.glob("*/skills/workbuddy-pdf/scripts/run.sh")) + list(base.glob("scripts/run.sh"))
        if hits:
            return hits[0]
    return None


def check_pdf():
    runner = find_pdf_tool()
    if runner:
        add("ok", "PDF 取文", str(runner))
        return
    try:
        import pypdf  # noqa: F401

        add("ok", "PDF 取文", "pypdf 已安装")
    except ImportError:
        add(
            "warn",
            "PDF 取文",
            "既没有 workbuddy-pdf 也没有 pypdf",
            "pip install pypdf，或在 WorkBuddy 中直接调用 workbuddy-pdf 技能",
        )


def check_fonts():
    system = platform.system()
    if system == "Windows":
        cands = [Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")]
        name = "微软雅黑 / 黑体"
    elif system == "Darwin":
        cands = [Path("/System/Library/Fonts/PingFang.ttc"), Path("/System/Library/Fonts/STHeiti Medium.ttc")]
        name = "苹方 / 华文黑体"
    else:
        cands = [Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
        name = "Noto Sans CJK"
    if any(p.exists() for p in cands):
        add("ok", "中文字体", name)
    else:
        add("warn", "中文字体", "未检测到 %s" % name, "安装中文字体，否则生成的 PPTX 可能显示方框")


def check_swc_permission():
    if platform.system() != "Windows":
        return
    swc = Path(os.environ.get("LOCALAPPDATA", "")) / "swc"
    if not swc.exists():
        add("ok", "SWC 缓存目录", "尚未创建，首次运行 slidep 时自动生成")
        return
    code, out = _run(["icacls", str(swc)])
    if code != 0:
        add("warn", "SWC 缓存目录", "无法读取权限", "手动运行 scripts/setup_env.ps1")
        return
    risky = [line.strip() for line in out.splitlines() if re.search(r"(Everyone|Authenticated Users)", line)]
    if risky:
        add(
            "warn",
            "SWC 缓存目录",
            "存在宽松 ACE（%s）" % risky[0][:60],
            "运行 scripts/setup_env.ps1 收紧权限，否则 slidep 会报 Failed to load native binding",
        )
    else:
        add("ok", "SWC 缓存目录", "权限正常")


def _display_width(text):
    """中文按 2 列算，避免终端里对不齐。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _pad(text, width):
    return text + " " * max(1, width - _display_width(text))


def check_version():
    """三处版本号必须一致：SKILL.md 的当前版本、CHANGELOG 最新条目、README 最新版本行。"""
    found = {}
    skill = ROOT / "SKILL.md"
    if skill.is_file():
        match = re.search(r"当前\s*\*\*([\d.]+)\*\*", skill.read_text(encoding="utf-8"))
        if match:
            found["SKILL.md"] = match.group(1)
    changelog = ROOT / "CHANGELOG.md"
    if changelog.is_file():
        match = re.search(r"^##\s+([\d.]+)", changelog.read_text(encoding="utf-8"), re.M)
        if match:
            found["CHANGELOG.md"] = match.group(1)
    readme = ROOT / "README.md"
    if readme.is_file():
        match = re.search(r"^-\s+\*\*([\d.]+)\*\*", readme.read_text(encoding="utf-8"), re.M)
        if match:
            found["README.md"] = match.group(1)

    if not found:
        add("warn", "版本号", "未找到版本标记", "在 SKILL.md 写「当前 **x.y**」，README 写「- **x.y**（日期）」")
        return
    unique = set(found.values())
    if len(unique) == 1:
        add("ok", "版本号", "%s（%d 处一致）" % (unique.pop(), len(found)))
    else:
        detail = "、".join("%s=%s" % (key, value) for key, value in sorted(found.items()))
        add("fail", "版本号", "不一致：%s" % detail, "把三处改成同一个版本号")


def render(as_json, show_hint):
    counts = {"ok": 0, "warn": 0, "fail": 0}
    for item in RESULTS:
        counts[item["level"]] += 1
    if as_json:
        print(json.dumps({"ok": counts["fail"] == 0, "counts": counts, "results": RESULTS}, ensure_ascii=False, indent=2))
        return counts["fail"] == 0

    icons = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}
    width = max(_display_width(r["name"]) for r in RESULTS) + 2
    print("report-prep 环境自检  |  %s  |  %s" % (platform.system(), ROOT))
    print("-" * 78)
    for item in RESULTS:
        print("[%s] %s%s" % (icons[item["level"]], _pad(item["name"], width), item["detail"]))
        if show_hint and item["hint"]:
            print("%s-> %s" % (" " * 7, item["hint"]))
    print("-" * 78)
    print("结果：%d 通过 / %d 警告 / %d 失败" % (counts["ok"], counts["warn"], counts["fail"]))
    if counts["fail"]:
        print("必需项未通过，先按上面的提示修复；加 --fix-hint 看建议。")
    elif counts["warn"]:
        print("核心可用；警告项只影响 PPT/PDF 环节，按需处理。")
    else:
        print("全部通过，可以直接跑完整流程。")
    return counts["fail"] == 0


def main():
    parser = argparse.ArgumentParser(description="report-prep 环境自检")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--fix-hint", action="store_true", help="打印修复建议")
    args = parser.parse_args()

    check_python()
    check_files()
    check_version()
    check_syntax()
    check_writable()
    check_logo()
    check_slidep()
    check_pdf()
    check_fonts()
    check_swc_permission()

    ok = render(args.json, args.fix_hint)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
