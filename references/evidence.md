# 证据台账与数字引用

## 目的

让讲解稿、讲述提纲、PPT 和逐页详解共享同一份来源数据，避免同一数字在不同产物中漂移。

自动脚本能检查“引用是否存在、状态是否可用、显示值是否与台账一致”，**不能替代人工核对 PDF 原文、图表刻度和上下文**。

## 一、证据项格式

每条来源数据或关键论断建立一个对象：

```json
{
  "id": "E001",
  "display": "24,845",
  "value": 24845,
  "unit": "cycles",
  "source": "paper.pdf",
  "locator": "PDF p. 8, Table 6, row 25 C",
  "quote": "The transition life at 25 C was 24845 cycles.",
  "status": "verified",
  "kind": "author_result",
  "note": "数值和单位已回原文核对"
}
```

字段约定：

| 字段 | 要求 |
|---|---|
| `id` | 使用 `E` 加数字的唯一 ID，在内容 JSON 中用 `{{E001}}` 引用 |
| `display` | 产物中显示的数字，不含单位；千分位、科学计数法均可 |
| `value` | 与 `display` 等价的 JSON 数值，用于一致性检查 |
| `unit` | 原文单位；换算时另建派生项并记录公式 |
| `source` | 实际来源文件名，不写空泛的“论文” |
| `locator` | 尽量精确到 PDF 页码、Table/Figure、行列或段落 |
| `quote` | 能覆盖该数值与上下文的原文摘录 |
| `status` | `verified` / `unverified` / `derived` / `reported_missing` |
| `kind` | `author_result` / `author_interpretation` / `inference` / `recommendation` / `demo` |
| `note` | 可选，记录换算、不确定度或核对说明 |

## 二、使用流程

1. 从原文提取候选数字与论断，先标为 `unverified`。
2. 回到 PDF 页面、表格或图注核对数值、单位、条件和指代对象。
3. 核对完成后改为 `verified`；原文没有的信息使用 `reported_missing`，不要创建虚构数值。
4. 在讲解稿或提纲 JSON 的文本中写 `{{E001}}`，不要把同一来源数字手工复制到多个文件。
5. 先运行数字检查，再渲染 HTML。

```bash
python scripts/check_numbers.py evidence.json content.json
python scripts/render_html.py content.json --evidence evidence.json -o deliverable.html
```

渲染器会替换证据令牌并转义 HTML。使用未登记 ID、引用非 `verified`/`derived` 项，或 `display` 与 `value` 不一致时，检查失败。

## 三、派生值与换算

单位换算、误差计算和跨表比较属于派生结果：

- `status` 使用 `derived`。
- `kind` 按实际用途标为 `inference` 或 `author_result`。
- `note` 写明公式、输入证据 ID、舍入规则和换算方向。
- 在产物中写“据此计算”或“换算得到”，不要伪装成原文直接给出的值。

## 四、非数值论断

机制、因果和适用边界同样需要来源，但可以不用数字令牌。至少在结构提纲或逐页详解中记录：

- 论断 ID；
- 来源文件与精确位置；
- 原文摘录或图注；
- 类型：作者解释 / 本次推断 / 工程建议。

多条证据共同支撑一个推断时，列出全部 ID，并写清推理步骤。证据不足时使用“可能”“与……一致”，不要写成已证明的因果关系。

## 五、图表证据

- 优先引用原图编号、子图编号和 PDF 页码。
- 从图片估读的数据必须标为“图上估读”，不能与原文表格的精确值混用。
- 没有原始数值时，可以描述趋势或绘制明确标注的机制示意图，但不能生成貌似真实的定量曲线。
- 裁切原图时保留坐标轴、单位、图例和必要图注。

## 六、检查边界

`check_numbers.py` 只检查内容 JSON 中显式写出的证据令牌。章节编号、用户指定时长等结构性数字可以普通书写；所有来源科研数据应使用令牌。交付前仍需人工检查是否存在绕过令牌手写的来源数字。
