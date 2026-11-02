# 技术流水线：从 PDF 到可交付文件

## 一、PDF 文本提取

Windows 环境用内置的 `workbuddy-pdf`：

```bash
sh "D:/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/workbuddy-pdf/scripts/run.sh" \
   "论文.pdf" "out.md" -f md -q
```

- `-f md` 保留标题层级；`-f txt` 更干净但丢结构
- 产物落到工作区临时目录（如 `pdfmd/`），同一批论文统一命名：`p<简称>.md`

### 双栏论文的坑（必须知道）

双栏排版提取后，**段落顺序会错乱**：左栏下半段可能跑到右栏上半段后面，表格数字会和正文混行。

引用前必须按关键词定位核对，不要按行号顺序读：

```bash
grep -n -o -E ".{0,80}(ASTM|gauge length|thermocouple|quenched).{0,160}" p12cr13.md
grep -n -E "Table [0-9]|Conclusion" p12cr13.md
```

看表格时优先搜数字串（`551.83`、`24845`），比搜单位可靠。

## 二、A4 HTML 交付件

### 必须的骨架

```html
<style>
  .page { width: 210mm; padding: 18mm 20mm 16mm; background: #fff; margin: 16px auto; }
  @media print {
    body { background: #fff; }
    .page { margin: 0; box-shadow: none; width: auto; padding: 0; }
    @page { size: A4; margin: 16mm 17mm 14mm; }
    h2 { page-break-after: avoid; }
    table, .why, .key { page-break-inside: avoid; }
  }
</style>
```

### 版式取值（已验证可读）

| 元素 | 字号 / 行高 |
|---|---|
| 正文 | 9.9–10pt / 1.85 |
| 表格 | 8.7pt / 1.55，表头浅底 `#EEF2F7` |
| 章节标题 h2 | 12pt，左侧 4px 竖线 `#1F3B57` |
| 说明框 | 9.3pt / 1.78，浅底 `#F6F8FB` + 左侧竖线 |
| 核心结论框 | 9.6pt / 1.8，米色底 `#FBF3E4` + 棕色竖线 `#8A6A3B` |
| 页脚 | 8.2pt，`#8B8B85` |

配色：主色 `#1F3B57`（深蓝）、强调 `#8A6A3B`（棕）、正文 `#1A1A1A`。三色足够，不要再加。

### 中文排版注意

- HTML 属性用 ASCII 直引号；正文中文引号用「」或""
- 数学符号直接写 Unicode：σ、ε、Δ、±、℃、×10⁻³、−（负号用 U+2212 而非连字符）
- 上下标用 `<sub>` / `<sup>`，不要用下划线模拟

### 交付前校验

```bash
python scripts/check_html.py 交付文件.html
```

检查标签闭合、裸 `&`、表格是否有 `thead/tbody`、统计字数与表格数。

## 三、PPT（可选，需 slidep）

```bash
export SWC_NATIVE_BINDING_CACHE="C:\\ProgramData\\swc-cache"
slidep create "deck.pptx"
slidep upsert-dsl "deck.pptx" --dsl-file "slides/01.slide" --page-index 0
slidep lint "deck.pptx" --dsl-file "slides/01.slide" --page-index 0
```

### 三个坑

1. **`SWC_NATIVE_BINDING_CACHE` 必须设**。`@swc` 原生绑定会校验缓存目录 ACL，若 `C:\Users\<name>` 对 Everyone 开放，加载会失败。做法：建 `C:\ProgramData\swc-cache`，ACL 只留 SYSTEM + 本人。
2. **JSX 文本里不能出现 `<` 和 `>`**。写成"10% 内""D 超过 0.3"，否则 upsert 静默失败、页面不落盘。
3. **safe-delete 会拦截删除**，且 PPT 常被编辑器占用。覆盖用「原位 upsert 补页」，不要删文件重建。

### 页序核对

```python
import zipfile, re
z = zipfile.ZipFile("deck.pptx")
names = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
               key=lambda x: int(re.findall(r"\d+", x)[0]))
for n in names:
    x = z.read(n).decode("utf-8")
    print(n, re.findall(r"<a:t>([^<]*)</a:t>", x)[0][:30])
```

## 四、Word 交付（可选）

若需 .docx，走 `workbuddy-docx` 插件，不要用 python-docx 手搓：

1. S2 排版：产出 HTML，需过 `review_html.py` 门禁（单文档仅一个 `h1`、表格必须有 `thead/tbody`、样式值走 CSS 变量）
2. S3 转换：`convert_doc.py` 转 docx，自动加目录域与页码域

## 五、文件与记忆

- 交付件一律放用户桌面，用户会直接双击打开
- 工作区保留源工程（模板 + 内容 JSON/脚本），便于批量改版
- 每次实质工作后追加到 `.workbuddy/memory/YYYY-MM-DD.md`，只记结论与坑，不记过程
