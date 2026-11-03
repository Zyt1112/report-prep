# 标准样张：4340M 文献汇报（6 页）

这是 v1.4 版式的**参考实现**。抄的是版式与标注方式，不是内容。

## 六页各自示范什么

| 页 | 文件 | 示范点 |
|---|---|---|
| 01 封面 | `slides/01.slide` | 深蓝 232px 顶块 + 校徽 300×61 + 大标题两行 + 问句副标 + 3px 短横 + 出处 |
| 02 实验设计 | `slides/02.slide` | **五状态控制变量表**；`246 °C` 用红字 + 2px 短下划线，底注写清出处 |
| 03 喷丸作用 | `slides/03.slide` | 三读数表；`650` 放大到 26px、`50 µm` 到 18px，红字短下划线；底带注解 HV 定义 |
| 04 实验结果 | `slides/04.slide` | 5×4 拉伸表；红字标 `1619 ± 12`，右侧读法写“比基体高 259 MPa” |
| 05 起裂源 | `slides/05.slide` | 同心结构示意（夹杂 → FGA → 鱼眼 → 瞬断）+ 红框 + 图例 |
| 06 实验结论（疲劳） | `slides/06.slide` | 左条件 / 右断口应力-寿命表；红字标 `920 MPa`；底注声明“非疲劳极限” |

共同点：**顶带 56px 深蓝（校徽 + 页码）、内容带 56–658、底带 62px（术语 + 图注）**，三带全篇不变。

## 怎么复现

```bash
cd examples/deck-v3-4340m

# Windows：若 slidep 报原生模块失败，先跑
#   powershell -ExecutionPolicy Bypass -File ../../scripts/setup_env.ps1 -UseVirtualDrive
export SWC_NATIVE_BINDING_CACHE="X:/cache"     # 上一步设置过可省略

slidep create 复现.pptx
for n in 01 02 03 04 05 06; do
  slidep upsert-dsl 复现.pptx --dsl-file "slides/$n.slide"
done
```

也可以直接打开 `4340M_样张.pptx` 看渲染结果——它就是这 6 个 `.slide` 生成的。

## 数据来源

Ahn et al., *Materials* **13** (2020) 5711（CC BY 4.0，开放获取）。

数值取自原文 Table 1 / Table 3 与 Fig. 5 / 7 / 8 / 9。原文只给趋势未给数值的地方（如疲劳极限），样张里写“原文未报告”，**没有补数**。

## 一次自检

```bash
python ../../scripts/doctor.py
```

应显示 `slidep` PASS、校徽 420×86、字体 PASS。
