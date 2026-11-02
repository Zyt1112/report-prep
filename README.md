# report-prep · 汇报前准备

> 仓库：https://github.com/Zyt1112/report-prep

把论文、技术资料或现有汇报组织成**一条能讲、能问、能回溯证据的链**。支持讲解稿、讲述提纲、PPT 结构、PPT 制作、逐页详解和模拟追问，也支持只修复现有材料的页序与逻辑。

优先服务实验、建模、仿真、器件/方法设计类工科材料；不符合这些类型时按真实问题链自定义，不强套模板。

## v1.2 的变化

- 增加四种任务入口，不再要求所有请求都从长讲解稿开始。
- 统一“问句标题 + 核心结论句”和第一张内容页结论先行规则。
- 页数、拍数改为由时长与必要问题数决定，取消七页下限。
- 区分多篇独立、多篇综合和论文对比三种模式。
- 新增证据台账、来源数字令牌和一致性检查。
- 新增 JSON 驱动 HTML 渲染、逐页详解、模拟追问和 Visual–Claim 绑定。
- 新增器件/方法设计类骨架、阶段资源路由和 WorkBuddy 环境适配。
- 升级 HTML 结构校验并增加自动化测试。

## 安装

将整个目录复制到任一位置：

```text
~/.workbuddy/skills/report-prep/        # 用户级
<项目>/.workbuddy/skills/report-prep/    # 项目级
```

也可以克隆：

```bash
git clone https://github.com/Zyt1112/report-prep.git
cp -r report-prep ~/.workbuddy/skills/
```

Windows 上 `~` 通常为 `C:\Users\<用户名>`。安装后新开会话即可使用。

## 用法示例

- “帮我把这篇论文讲明白，我要跟导师汇报。”
- “只要讲述提纲，15 分钟组会，听众是大同行。”
- “这份现有 PPT 页与页之间没关联，直接诊断并重排，不要重写讲解稿。”
- “先出 PPT 结构让我确认，确认后再做 PPT 和逐页追问。”
- “对比这三篇论文的假设、证据和边界，不要分别做三份摘要。”

也可以显式调用：`/report-prep 精读这篇，出一套汇报材料`。

## 标准流程

```text
0 任务卡与材料盘点
  ↓
1 讲解稿（可独立交付）
  ↓
2 讲述提纲 + 压缩关系表
  ↓
3 PPT 结构：问句标题 + 核心结论 + 证据 + 视觉绑定
  ↓ 用户确认
4 PPT 制作与逐页渲染检查
  ↓
5 逐页详解 + 模拟追问
```

修复现有材料时可直接进入步骤 3；用户只要中间产物时做到该层即停。

## 可复现 HTML 工作流

来源数字放入证据 JSON，在内容 JSON 中用 `{{E001}}` 引用：

```bash
python scripts/check_numbers.py examples/evidence.json examples/outline.content.json
python scripts/render_html.py examples/outline.content.json \
  --evidence examples/evidence.json -o outline.generated.html
python scripts/check_html.py outline.generated.html
```

讲解稿使用 `examples/explainer.content.json`，渲染器会按 `kind` 自动选择模板。

**自动数字检查只保证已声明的引用、状态和显示值一致，不替代人工回 PDF 核对。** HTML 校验通过后仍需实际打开并检查打印预览。

## 自动化测试

只依赖 Python 3 标准库：

```bash
python -m unittest discover -s tests -v
python scripts/check_html.py assets/explainer.html assets/outline.html --allow-placeholders
```

## 目录

```text
report-prep/
├── SKILL.md
├── references/
│   ├── register.md
│   ├── structure.md
│   ├── deck-skeletons.md
│   ├── evidence.md
│   ├── page-notes.md
│   ├── ppt-build.md
│   └── pipeline.md
├── assets/
│   ├── explainer.html
│   ├── outline.html
│   └── content.schema.json
├── scripts/
│   ├── render_html.py
│   ├── check_numbers.py
│   └── check_html.py
├── examples/
│   ├── demo-source.txt
│   ├── evidence.json
│   ├── explainer.content.json
│   ├── outline.content.json
│   └── 12Cr13-ppt-outline.html
└── tests/
    └── test_scripts.py
```

## 许可

MIT，见 [LICENSE](LICENSE)。
