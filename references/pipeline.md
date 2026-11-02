# 技术流水线：从材料到可复现交付

## 一、前置检查

先确认原文、补充材料、图表和已有汇报是否可读。记录缺失页、扫描质量、无法提取的表格和需要人工查看的图。任何缺失都进入任务卡，不用猜测掩盖。

## 二、PDF 提取与原文核对

在 WorkBuddy 中优先调用官方 `workbuddy-pdf` 技能；其他环境使用当前可用的 PDF 解析器。不要写死某台机器的安装路径。

- Markdown 适合保留标题层级，纯文本适合关键词检索。
- 双栏论文可能出现栏序错乱、表格混行和公式拆分，引用前必须回到页面对照。
- 图表数值应同时检查坐标、单位、图注和表头，不能只匹配数字字符串。
- 扫描件需要 OCR 或页面图像核对；低置信度内容标为待确认。

检索时使用当前环境提供的专用搜索工具；没有专用工具时再使用 `grep` 等命令。检索定位不等于完成原文核对。

## 三、建立证据与内容 JSON

1. 按 `references/evidence.md` 建 `evidence.json`。
2. 将来源数字写为 `{{E001}}` 令牌，并人工回到 PDF 核对。
3. 按 `examples/*.content.json` 建讲解稿或讲述提纲的内容 JSON。
4. 先检查数字引用，再渲染 HTML。

```bash
python scripts/check_numbers.py evidence.json content.json
python scripts/render_html.py content.json --evidence evidence.json -o deliverable.html
python scripts/check_html.py deliverable.html
```

`render_html.py` 只使用 Python 标准库，自动选择 `assets/explainer.html` 或 `assets/outline.html`，转义文本并注入证据显示值。模板中的 `{{...}}` 是渲染占位符，不应直接作为最终交付件。

数字脚本的通过含义是：**声明的证据引用和显示值一致**。它不证明 OCR、人工录入或原文解读一定正确。

## 四、A4 HTML

模板包含以下打印基础样式：

```html
@media print {
  body { background: #fff; }
  .page { margin: 0; box-shadow: none; width: auto; padding: 0; }
  @page { size: A4; margin: 16mm 17mm 14mm; }
  h2 { break-after: avoid; page-break-after: avoid; }
  table, .why, .key { break-inside: avoid; page-break-inside: avoid; }
}
```

- 正文使用 Unicode 数学符号，负号使用 U+2212。
- 内容 JSON 中的文本按纯文本转义；需要上下标时使用 Unicode 上下标，不注入原始 HTML。
- HTML 校验通过后仍要实际打开并检查打印预览；脚本不能发现所有分页和视觉溢出问题。

检查模板本身时可允许占位符：

```bash
python scripts/check_html.py assets/explainer.html assets/outline.html --allow-placeholders
```

## 五、PPT 制作

在 WorkBuddy 中统一走官方 `workbuddy-pptx` 技能。其他工具只作为可选适配器，先确认命令、版本和输入格式，不把某个内部命令当成所有环境的必需品。

每页按以下闭环执行：

1. 从确认后的结构提纲读取标题、核心结论、证据和视觉绑定。
2. 制作页面并保存源文件。
3. 检查溢出、遮挡、字体、图表数值和页脚。
4. 更新对应的逐页详解与模拟追问。
5. 通过后再进入下一页。

全部完成后核对页数、页序和标题链，并实际渲染或打开 PPT 检查。不要只凭源文件存在就宣称 PPT 已成功生成。

## 六、Word 与其他格式

在 WorkBuddy 中需要 `.docx` 时走官方 `workbuddy-docx` 路由；需要编辑现有 Office 文件时使用对应的本地编辑能力。不要在不了解当前工具链时写死转换脚本路径。

## 七、文件与来源工程

- 输出到用户指定目录或当前工作区，不强制写桌面。
- 保留内容 JSON、证据 JSON、模板版本和生成文件，便于复改。
- 不覆盖用户已有文件；同名输出使用清晰的新版本名。
- 对外分享前检查原文图片、未公开数据和引用材料的授权与隐私要求。
