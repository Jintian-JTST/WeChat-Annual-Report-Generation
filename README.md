# 微信年度报告生成器  
*WeChat Annual Report Generator @JTST*

> 把一整年的微信聊天记录，变成一份可滚动、可分享的年度报告。

---

## 📌 项目说明（请务必阅读）

**本项目仅用于个人学习、数据分析与可视化研究用途。**  
**禁止用于任何商业用途、隐私泄露、数据贩卖等行为。**

使用本项目即代表你确认：
- 所有数据均来自你**本人可合法访问的聊天记录**
- 所有分析与渲染过程**仅在本地进行**
- 作者不对任何数据来源或使用后果承担责任

---

## ✨ 项目亮点

- 📊 **支持单聊 & 群聊**
  - 消息量、字符量、收发对比
  - 群聊 Top 发言人排行
- 🔥 **多维可视化**
  - 全年活跃热力图（GitHub-style）
  - 24 小时作息分布
  - 关键词词云（中文分词）
- 🎞️ **沉浸式年度报告**
  - 深色主题
  - 全屏滚动（类似 Apple / Spotify Wrapped）
  - 输出为单个 `HTML` 文件，直接打开即可
- 🧠 **分析 & 渲染解耦**
  - 数据分析与页面生成分离，便于二次开发

---

## 🚀 快速开始（已拥有 CSV 聊天记录）

如果你已经有 `messages.csv`，请先将其放入项目根目录，确保文件名正确、按照 UTF-8 编码保存。然后运行：

```bash
pip install -r requirements.txt
python wechat_analysis.py
```

生成结果：

* `Final_Report.html` —— 微信年度报告（直接打开）
* `report_data.json` —— 中间统计数据（可复用）

注意，词云生成可能需要几分钟时间。参考本人 416,849 行聊天记录，生成时间约 6 分钟。

---

## 🧠 程序流程说明

本项目采用 **两阶段流水线设计**：

```text
wechat_analysis.py
├─ step1_analyze.py   # 解析 CSV → 统计指标 → report_data.json
└─ step2_render.py    # JSON → 可视化渲染 → Final_Report.html
```

这样做的好处：

* 数据分析与视觉渲染解耦
* 改样式 / 动画无需重新跑分析
* 后续可扩展为 Web / API / 多年份对比

---

## 📂 项目结构

```text
WeChat-Annual-Report-Generator
├── .gitattributes
├── .gitignore
├── README.md
├── requirements.txt
│
├── wechat_analysis.py     # 主入口（串联分析与渲染）
├── step1_analyze.py       # 数据分析
├── step2_render.py        # HTML 渲染
│
├── report_data.json       # 中间数据（自动生成）
├── Final_Report.html      # 最终年度报告（自动生成）
│
├── messages.csv           # 微信聊天记录（用户提供）
└── MemoTrace/             # 聊天记录解析工具（见下文）
```

---

## 📥 如何导出微信聊天记录

> 这一步每年都需要**复用流程**。

### 1️⃣ 准备微信电脑版

* **必须使用 3.x 版本微信**
* ❌ 微信 4.x 版本无法导出数据库
* ✅ 推荐版本：`3.9.12`



### 2️⃣ 迁移聊天记录到电脑

1. 登录 **电脑微信**
2. 左下角 → 聊天 → 聊天记录迁移
3. 将 **全部聊天记录** 迁移到电脑
   （数据量大时可能需要数小时）


### 3️⃣ 使用 MemoTrace 导出 CSV

1. 打开 `MemoTrace.exe`
2. 点击「获取信息」，等待分析完成
3. 点击「设置微信路径」，确认路径正确
4. 点击「解析数据」
5. 解析完成后：

   * 数据 → 导出聊天记录（全部）
   * 选择 **CSV 格式**
6. 将导出的 `messages.csv` 放入项目根目录

> 说明：
>
> * MemoTrace 原项目在 [此链接](https://github.com/shixiaogaoya/MemoTrace)，原作者为shixiaogaoya，
> * 本仓库仅保留学习用途的历史版本备份，不提供任何技术支持。

---

## ⚠️ 注意事项 & 常见问题

* ⚠️ **CSV 文件需为 UTF-8 编码**
* ⚠️ 大型聊天记录（>10 万行）：

  * 首次分析可能需要数分钟
* ⚠️ 项目默认依赖字段：

  * `StrContent`（消息内容）
  * `IsSender`（是否本人）
  * `Date` / `Timestamp`
* 🔒 所有数据处理均在本地完成，不会联网、不上传

---

## 🛠️ 依赖环境

* Python ≥ 3.9

主要依赖：

```text
pandas
matplotlib
seaborn
jieba
wordcloud
numpy
pillow
```

---

## 📜 License & Disclaimer

本项目不提供任何形式的担保。
请遵守当地法律法规，合理、合法使用。

**Made for reflection, not surveillance.**

