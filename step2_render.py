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
        --bg: #0b0b0b;
        --card-bg: #141414;
        --blue-accent: #00e5ff;
        --red-accent: #ff4d6d;
        --text-main: #ffffff;
        --text-sub: rgba(255,255,255);
    }}

    body {{
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        background: var(--bg);
        color: var(--text-main);
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
    }}

    h1 {{
        text-align: center;
        color: #fff;
        text-shadow: 0 0 20px rgba(0,229,255,0.3);
        font-size: 2.8em;
        margin-bottom: 10px;
    }}

    .sub {{
        text-align: center;
        color: var(--text-sub);
        margin-bottom: 60px;
        font-size: 1em;
        letter-spacing: 2px;
    }}

    /* ============ 核心修改：竖直双色卡片样式 ============ */
    .hero-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr); /* 两列布局 */
        gap: 30px;
        margin-bottom: 80px;
    }}

    .stat-card {{
        display: flex;
        flex-direction: column;
        min-height: 340px;       /* 拉长高度 */
        border-radius: 16px;
        overflow: hidden;        /* 保证圆角 */
        border: 1px solid #222;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}

    /* 上半部分：蓝色 */
    .card-top {{
        flex: 1;
        background: linear-gradient(180deg, rgba(0,229,255,0.15), rgba(0,229,255,0.02));
        border-bottom: 1px solid rgba(255,255,255,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }}

    /* 下半部分：红色 */
    .card-bottom {{
        flex: 1;
        background: linear-gradient(180deg, rgba(255,77,109,0.02), rgba(255,77,109,0.15));
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }}

    .stat-val {{
        font-size: 2.4em;
        font-weight: bold;
        margin-bottom: 8px;
        color: #fff;
        line-height: 1.1;
        text-align: center;
    }}

    .card-top .stat-val {{ text-shadow: 0 0 15px rgba(0,229,255,0.3); }}
    .card-bottom .stat-val {{ text-shadow: 0 0 15px rgba(255,77,109,0.3); }}

    .stat-lbl {{
        font-size: 1.2em;
        color: var(--text-sub);
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    /* ================================================= */

    .card {{
        background: var(--card-bg);
        border: 1px solid #222;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 40px;
    }}

    .card h3 {{
        margin-top: 0;
        color: #fff;
        border-left: 4px solid var(--blue-accent);
        padding-left: 12px;
        font-size: 1.3em;
        margin-bottom: 20px;
    }}

    .section-header {{
        text-align: center;
        margin: 80px 0 40px 0;
        color: #fff;
        border-bottom: 1px solid #333;
        padding-bottom: 20px;
        font-size: 1.8em;
    }}

    .profile-item {{
        background: #111;
        border: 1px solid #222;
        padding: 25px;
        border-radius: 16px;
        margin-bottom: 50px;
    }}

    .profile-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #222;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }}

    .rank-badge {{
        background: #333;
        color: #fff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.9em;
    }}

    .name-label {{
        font-size: 1.4em;
        font-weight: bold;
        color: #fff;
        margin-left: 10px;
    }}

    .count-label {{
        color: var(--blue-accent);
        font-size: 1.2em;
        font-family: monospace;
        font-weight: bold;
    }}

    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
    }}

    .viz-block {{
        margin-bottom: 15px;
        background: #0f0f0f;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #1a1a1a;
    }}
    
    .viz-label {{
        font-size: 0.85em;
        color: #666;
        margin-bottom: 8px;
        text-align: center;
    }}

    img {{
        width: 100%;
        border-radius: 6px;
        display: block;
    }}
</style>
</head>

<body>

<h1>2025 年度微信回顾</h1>
<div class="sub">{metrics.get("start","N/A")} - {metrics.get("end","N/A")}</div>

<div class="hero-grid">
    
    <div class="stat-card">
        <div class="card-top blue">
            <div class="stat-val">{total_msgs:,}</div>
            <div class="stat-lbl">📨 年度消息总数</div>
        </div>
        <div class="card-bottom red">
            <div class="stat-val">{metrics["daily_avg"]:,}</div>
            <div class="stat-lbl">📅 日均消息数</div>
        </div>
    </div>

    <div class="stat-card">
        <div class="card-top blue">
            <div class="stat-val">{chars_sent:,}</div>
            <div class="stat-lbl">📤 我发送的字数</div>
        </div>
        <div class="card-bottom red">
            <div class="stat-val">{chars_recv:,}</div>
            <div class="stat-lbl">📥 接收的字数</div>
        </div>
    </div>

    <div class="stat-card">
        <div class="card-top blue">
            <div class="stat-val">{craziest_day}</div>
            <div class="stat-lbl">🔥 消息最密集的一天</div>
        </div>
        <div class="card-bottom red">
            <div class="stat-val">{craziest_count:,}</div>
            <div class="stat-lbl">当日消息数</div>
        </div>
    </div>

    <div class="stat-card">
        <div class="card-top blue">
            <div class="stat-val" style="font-size: 1.8em;">{top_contact_name}</div>
            <div class="stat-lbl">❤️ 联系最频繁的人</div>
        </div>
        <div class="card-bottom red">
            <div class="stat-val">{top_contact_count:,}</div>
            <div class="stat-lbl">你和 Ta 的消息总数</div>
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

print(f"✅ 竖版卡片风格报告已生成！包含 {len(p_profiles)} 位好友和 {len(g_profiles)} 个群聊的详细数据。")
print("👉 请双击打开 Final_Report.html 查看效果")