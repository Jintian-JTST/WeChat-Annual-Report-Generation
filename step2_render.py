import json
import webbrowser
import os
from datetime import datetime

print("正在读取 report_data.json ...")
try:
    with open("report_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("❌ 没找到数据！请先运行 step1_analyze.py")
    exit()

# ===================== 1. 数据容错与自动计算 =====================
metrics = data.get("metrics", {})
charts = data.get("charts", {})
p_profiles = data.get("private_profiles", [])
g_profiles = data.get("group_profiles", [])
global_charts = data.get("global_charts", {})

# 1. 计算天数跨度
try:
    start_date = datetime.strptime(metrics.get("start", "2025.01.01"), "%Y.%m.%d")
    end_date = datetime.strptime(metrics.get("end", "2025.12.31"), "%Y.%m.%d")
    days_span = (end_date - start_date).days + 1
except:
    days_span = 365

# 2. 日均消息
total_msgs = metrics.get("total", 0)
if "daily_avg" not in metrics:
    metrics["daily_avg"] = int(total_msgs / days_span) if days_span > 0 else 0

# 3. 字数统计
total_chars = metrics.get("chars", metrics.get("chars_total", 0))
chars_sent = metrics.get("chars_sent", int(total_chars * 0.5))
chars_recv = metrics.get("chars_recv", int(total_chars * 0.5))

# 4. 关键指标
craziest_day = metrics.get("craziest_day", "N/A")
craziest_count = metrics.get("craziest_count", 0)
top_contact_name = metrics.get("top_contact_name", "N/A")
top_contact_count = metrics.get("top_contact_count", 0)

# ===================== 2. HTML 模块渲染 =====================

def render_profiles(profile_list, title):
    if not profile_list:
        return ""
    html_block = f'<h2 class="section-header">{title}</h2>'

    for p in profile_list:
        wc_html = (
            f'<div class="viz-block"><img src="data:image/png;base64,{p["wordcloud"]}"></div>'
            if p.get("wordcloud") else ""
        )

        member_html = ""
        if p.get("member_bar"):
            member_html = f"""
            <div class="viz-block">
                <div class="viz-label">🏆 群内最活跃成员（前 10）</div>
                <img src="data:image/png;base64,{p["member_bar"]}">
            </div>
            """

        html_block += f"""
        <div class="profile-item">
            <div class="profile-header">
                <div>
                    <span class="rank-badge">#{p["rank"]}</span>
                    <span class="name-label">{p["name"]}</span>
                </div>
                <div class="count-label">{p["count"]:,} 条消息</div>
            </div>

            <div class="viz-block" style="background:none; border:none; padding:0;">
                <img src="data:image/png;base64,{p["compare"]}">
            </div>

            {member_html}

            <div class="viz-block">
                <img src="data:image/png;base64,{p["heatmap"]}">
            </div>

            <div class="grid-2">
                <div class="viz-block">
                    <img src="data:image/png;base64,{p["hourly"]}">
                </div>
                {wc_html}
            </div>
        </div>
        """
    return html_block

# ===================== 3. HTML 主体 =====================

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>2025 微信年度报告</title>
<style>
    :root {{
        --bg: #0d0d0d;
        --card: #161616;
        --accent: #00f2ea;
        --highlight: #ff0050;
        --text: #ccc;
    }}

    body {{
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        background: var(--bg);
        color: var(--text);
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
    }}

    h1 {{
        text-align: center;
        color: #fff;
        text-shadow: 0 0 15px rgba(0,242,234,0.4);
        font-size: 2.5em;
        margin-bottom: 5px;
    }}

    .sub {{
        text-align: center;
        color: #666;
        margin-bottom: 50px;
        font-size: 0.9em;
        letter-spacing: 1px;
    }}

    .hero-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-bottom: 40px;
    }}

    .stat-box {{
        background: #111;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 25px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
    }}

    .stat-item {{
        width: 100%;
        text-align: center;
    }}

    .stat-item:first-child {{
        border-bottom: 1px dashed #333;
        padding-bottom: 20px;
    }}

    .stat-val {{
        font-size: 2em;
        font-weight: bold;
        color: #fff;
        margin-bottom: 5px;
    }}

    .stat-lbl {{
        font-size: 0.9em;
        color: #666;
        letter-spacing: 1px;
    }}

    .card {{
        background: var(--card);
        border: 1px solid #222;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 30px;
    }}

    .card h3 {{
        margin-top: 0;
        color: #fff;
        border-left: 3px solid var(--accent);
        padding-left: 10px;
        font-size: 1.2em;
    }}

    .section-header {{
        text-align: center;
        margin: 60px 0 30px 0;
        color: #fff;
        border-bottom: 2px solid #222;
        padding-bottom: 10px;
    }}

    .profile-item {{
        background: #111;
        border: 1px solid #222;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 50px;
    }}

    .profile-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #222;
        padding-bottom: 15px;
        margin-bottom: 15px;
    }}

    .rank-badge {{
        background: #333;
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }}

    .name-label {{
        font-size: 1.3em;
        font-weight: bold;
        color: #fff;
        margin-left: 10px;
    }}

    .count-label {{
        color: var(--accent);
        font-size: 1.1em;
        font-family: monospace;
    }}

    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }}

    img {{
        width: 100%;
        border-radius: 6px;
    }}
</style>
</head>

<body>

<h1>2025 年度回顾</h1>
<div class="sub">{metrics.get("start","N/A")} - {metrics.get("end","N/A")} · 数据总览</div>

<div class="hero-grid">
    <div class="stat-box">
        <div class="stat-item">
            <div class="stat-val">{total_msgs:,}</div>
            <div class="stat-lbl">年度消息总数</div>
        </div>
        <div class="stat-item">
            <div class="stat-val">{metrics["daily_avg"]}</div>
            <div class="stat-lbl">日均消息数</div>
        </div>
    </div>

    <div class="stat-box">
        <div class="stat-item">
            <div class="stat-val">{chars_sent:,}</div>
            <div class="stat-lbl">发送字数</div>
        </div>
        <div class="stat-item">
            <div class="stat-val">{chars_recv:,}</div>
            <div class="stat-lbl">接收字数</div>
        </div>
    </div>

    <div class="stat-box">
        <div class="stat-item">
            <div class="stat-val">{craziest_day}</div>
            <div class="stat-lbl">消息最密集的一天</div>
        </div>
        <div class="stat-item">
            <div class="stat-val">{craziest_count:,}</div>
            <div class="stat-lbl">当日消息数</div>
        </div>
    </div>

    <div class="stat-box">
        <div class="stat-item">
            <div class="stat-val">{top_contact_name}</div>
            <div class="stat-lbl">联系最频繁的人</div>
        </div>
        <div class="stat-item">
            <div class="stat-val">{top_contact_count:,}</div>
            <div class="stat-lbl">消息总数</div>
        </div>
    </div>
</div>

<div class="card">
    <h3>🕒 我发消息的时间分布（全年）</h3>
    <img src="data:image/png;base64,{global_charts.get("my_hourly","")}">
</div>

<div class="card">
    <h3>☁️ 我这一年的关键词</h3>
    <img src="data:image/png;base64,{global_charts.get("my_wordcloud","")}">
</div>

<div class="card">
    <h3>📅 全年活跃热力图</h3>
    <img src="data:image/png;base64,{charts.get("heatmap","")}">
</div>

<div class="card">
    <h3>🏆 聊天最频繁的 10 位好友</h3>
    <img src="data:image/png;base64,{charts.get("rank_p","")}">
</div>

<div class="card">
    <h3>📢 最活跃的 10 个群聊</h3>
    <img src="data:image/png;base64,{charts.get("rank_g","")}">
</div>

{render_profiles(p_profiles, "👤 好友聊天深度分析")}
{render_profiles(g_profiles, "👥 群聊活跃度分析")}

</body>
</html>
"""

with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 中文版网页已生成：Final_Report.html")
