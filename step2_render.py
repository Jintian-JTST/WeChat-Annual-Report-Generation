import json
import os
import webbrowser

print("正在读取 report_data.json ...")
try:
    with open("report_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("❌ 没找到数据！请先运行 step1。")
    exit()

metrics = data["metrics"]
charts = data["charts"]
p_profiles = data.get("private_profiles", [])
g_profiles = data.get("group_profiles", [])


def render_profiles(profile_list, title):
    if not profile_list:
        return ""

    html_block = f'<h2 class="section-header">{title}</h2>'

    for p in profile_list:
        wc_html = (
            f'<div class="viz-block"><img src="data:image/png;base64,{p["wordcloud"]}"></div>'
            if p.get("wordcloud")
            else ""
        )

        html_block += f"""
        <div class="profile-item">
            <div class="profile-header">
                <div>
                    <span class="rank-badge">#{p['rank']}</span>
                    <span class="name-label">{p['name']}</span>
                </div>
                <div class="count-label">{p['count']:,} Msgs</div>
            </div>

            <div class="viz-block" style="background:none; border:none; padding:0;">
                <img src="data:image/png;base64,{p['compare']}">
            </div>

            <div class="viz-block">
                <img src="data:image/png;base64,{p['heatmap']}">
            </div>

            <div class="grid-2">
                <div class="viz-block">
                    <img src="data:image/png;base64,{p['hourly']}">
                </div>
                {wc_html}
            </div>
        </div>
        """
    return html_block


html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>WeChat Report 2025</title>

<style>
:root {{
    --bg: #0b0e11;
    --card: #12161c;
    --accent: #00d1c1;
    --accent-2: #ff4d6d;
    --text: #cfd3dc;
    --muted: #7a8392;
}}

body {{
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    background: radial-gradient(circle at top, #111820, var(--bg));
    color: var(--text);
    max-width: 900px;
    margin: 0 auto;
    padding: 48px 40px;
}}

h1 {{
    text-align: center;
    color: #fff;
    font-size: 2.8em;
    margin-bottom: 8px;
}}

.sub {{
    text-align: center;
    color: #7a8392;
    margin-bottom: 64px;
    font-size: 0.9em;
    letter-spacing: 1.5px;
}}

/* ===== 年度总览纵向布局 ===== */
.hero {{
    display: flex;
    flex-direction: column;
    gap: 28px;
    margin-bottom: 80px;
}}

/* ===== 单张统计卡片 ===== */
.stat-box {{
    background: linear-gradient(180deg, #151a21, #0f1318);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 22px;
    padding: 38px 42px;
}}

/* 主数字 */
.stat-val {{
    font-size: 4.4em;
    font-weight: 900;
    line-height: 1.05;
    color: var(--accent);
    letter-spacing: -0.03em;
}}

/* 副高亮（名字 / 次数字） */
.stat-sub {{
    margin-top: 12px;
    font-size: 1.3em;
    font-weight: 600;
    color: #e6fefc;
}}

.stat-sub .highlight {{
    color: var(--accent);
    letter-spacing: 0.05em;
}}

/* 说明文字 */
.stat-lbl {{
    margin-top: 14px;
    font-size: 0.85em;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

/* 其余保持原样 */
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
}}

.section-header {{
    text-align: center;
    margin: 70px 0 30px;
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
    padding-bottom: 12px;
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
    font-family: monospace;
    color: var(--accent);
    font-size: 1.1em;
}}

.grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}}

.viz-block {{
    margin-bottom: 10px;
}}

img {{
    width: 100%;
    display: block;
    border-radius: 6px;
}}
</style>
</head>

<body>

<h1>2025 REWIND</h1>
<div class="sub">{metrics['start']} – {metrics['end']} · WECHAT DATA</div>

<!-- ===== 年度总览 ===== -->
<div class="hero">

    <div class="stat-box">
        <div class="stat-val">{metrics['total']:,}</div>
        <div class="stat-lbl">年度消息总数 · 日均 {metrics['daily_avg']} 条</div>
    </div>

    <div class="stat-box">
        <div class="stat-val">{metrics['craziest_day']}</div>
        <div class="stat-lbl">最疯狂的一天 · {metrics['craziest_count']:,} 条消息</div>
    </div>

    <div class="stat-box">
        <div class="stat-val">{metrics['chars_total']:,}</div>
        <div class="stat-lbl">
            发送 {metrics['chars_sent']:,} ｜ 接收 {metrics['chars_recv']:,}
        </div>
    </div>

    <div class="stat-box">
        <div class="stat-val">{metrics['top_contact_count']:,}</div>
        <div class="stat-lbl">最亲密联系人 · {metrics['top_contact_name']}</div>
    </div>

    <div class="stat-box">
        <div class="stat-val">
            {metrics['sent_ratio']}% vs {metrics['recv_ratio']}%
        </div>
        <div class="stat-lbl">对话主动性 · 发送 vs 接收</div>
    </div>

</div>

<div class="card">
    <h3>📅 Annual Heatmap</h3>
    <img src="data:image/png;base64,{charts['heatmap']}">
</div>

<div class="card">
    <h3>🏆 Top 10 Friends</h3>
    <img src="data:image/png;base64,{charts['rank_p']}">
</div>

<div class="card">
    <h3>📢 Top 10 Groups</h3>
    <img src="data:image/png;base64,{charts['rank_g']}">
</div>

{render_profiles(p_profiles, "👤 Private Chat Analysis")}

{render_profiles(g_profiles, "👥 Group Chat Analysis")}

</body>
</html>
"""

with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 网页已生成: Final_Report.html")

webbrowser.open("file://" + os.path.abspath("Final_Report.html"))
