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

# === 1. 数据容错与自动计算 (关键修复) ===
metrics = data.get("metrics", {})
charts = data.get("charts", {})
p_profiles = data.get("private_profiles", [])
g_profiles = data.get("group_profiles", [])

# 1. 计算天数跨度 (days_span)
try:
    start_date = datetime.strptime(metrics.get('start', '2025.01.01'), "%Y.%m.%d")
    end_date = datetime.strptime(metrics.get('end', '2025.12.31'), "%Y.%m.%d")
    days_span = (end_date - start_date).days + 1
except:
    days_span = 365 # 保底

# 2. 计算日均 (daily_avg)
total_msgs = metrics.get('total', 0)
if 'daily_avg' not in metrics:
    metrics['daily_avg'] = int(total_msgs / days_span) if days_span > 0 else 0

# 3. 处理字数 (兼容 chars 或 chars_total)
total_chars = metrics.get('chars', metrics.get('chars_total', 0))
# 如果没有分发送/接收，就粗略对半显示，或者显示未知，避免报错
chars_sent = metrics.get('chars_sent', int(total_chars * 0.5)) 
chars_recv = metrics.get('chars_recv', int(total_chars * 0.5))

# 4. 处理疯狂一天 & 最亲密联系人 (如果没有就显示 N/A)
craziest_day = metrics.get('craziest_day', 'N/A')
craziest_count = metrics.get('craziest_count', 0)
top_contact_name = metrics.get('top_contact_name', 'N/A')
top_contact_count = metrics.get('top_contact_count', 0)

# ===================== 2. HTML 生成函数 =====================

def render_profiles(profile_list, title):
    if not profile_list: return ""
    html_block = f'<h2 class="section-header">{title}</h2>'
    
    for p in profile_list:
        wc_html = f'<div class="viz-block"><img src="data:image/png;base64,{p["wordcloud"]}"></div>' if p.get("wordcloud") else ""
        
        # === 🟢 新增：如果有成员图，就显示 ===
        member_html = ""
        if p.get("member_bar"):
            member_html = f"""
            <div class="viz-block">
                <div class="viz-label">🏆 群活跃榜 Top 10</div>
                <img src="data:image/png;base64,{p['member_bar']}">
            </div>
            """
        # ==================================
        
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
            
            {member_html}
            
            <div class="viz-block">
                <img src="data:image/png;base64,{p['heatmap']}">
            </div>
            
            <div class="grid-2">
                <div class="viz-block"><img src="data:image/png;base64,{p['hourly']}"></div>
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
    :root {{ --bg: #0d0d0d; --card: #161616; --accent: #00f2ea; --highlight: #ff0050; --text: #ccc; }}
    body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: var(--bg); color: var(--text); max-width: 900px; margin: 0 auto; padding: 40px; }}
    
    h1 {{ text-align: center; color: #fff; text-shadow: 0 0 15px rgba(0,242,234,0.4); font-size: 2.5em; margin-bottom: 5px; }}
    .sub {{ text-align: center; color: #666; margin-bottom: 50px; font-size: 0.9em; letter-spacing: 1px; }}
    
    /* === 核心统计卡片 (垂直堆叠布局) === */
    .hero-grid {{ 
        display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; 
    }}
    
    .stat-box {{ 
        background: #111; border: 1px solid #333; border-radius: 12px; padding: 25px; 
        /* 改为垂直排列 */
        display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }}
    
    .stat-item {{ width: 100%; text-align: center; }}
    
    /* 分割线 */
    .stat-item:first-child {{
        border-bottom: 1px dashed #333;
        padding-bottom: 20px;
    }}
    
    /* 数字样式：统统变大 */
    .stat-val {{ font-size: 2em; font-weight: bold; color: #fff; margin-bottom: 5px; line-height: 1.1; }}
    
    /* 标签样式 */
    .stat-lbl {{ font-size: 0.9em; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
    
    /* 颜色修饰 */
    .cyan {{ color: var(--accent); }}
    .pink {{ color: var(--highlight); }}
    .white {{ color: #fff; }}

    /* 图表区域 */
    .card {{ background: var(--card); border: 1px solid #222; padding: 20px; border-radius: 12px; margin-bottom: 30px; }}
    .card h3 {{ margin-top: 0; color: #fff; border-left: 3px solid var(--accent); padding-left: 10px; font-size: 1.2em; }}
    
    .section-header {{ text-align: center; margin: 60px 0 30px 0; color: #fff; border-bottom: 2px solid #222; padding-bottom: 10px; }}
    
    .profile-item {{ background: #111; border: 1px solid #222; padding: 20px; border-radius: 12px; margin-bottom: 50px; }}
    .profile-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; padding-bottom: 15px; margin-bottom: 15px; }}
    .rank-badge {{ background: #333; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em; }}
    .name-label {{ font-size: 1.3em; font-weight: bold; color: #fff; margin-left: 10px; }}
    .count-label {{ font-family: monospace; color: var(--accent); font-size: 1.1em; }}
    
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .viz-block {{ margin-bottom: 10px; }}

    /* === 新增成员榜单样式 === */
    .member-list {{
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }}
    .member-row {{
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #2a2a2a;
        font-size: 0.9em;
    }}
    .member-row:last-child {{ border-bottom: none; }}
    .m-rank {{ color: #666; width: 25px; font-family: monospace; }}
    .m-name {{ color: #ccc; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .m-count {{ color: var(--accent); font-weight: bold; }}
    .member-row.highlight .m-name {{ color: var(--accent); font-weight: bold; }}
    img {{ width: 100%; display: block; border-radius: 6px; }}
</style>
</head>
<body>

    <h1>2025 REWIND</h1>
    <div class="sub">{metrics.get('start', 'N/A')} - {metrics.get('end', 'N/A')} • DATA MATRIX</div>

    <div class="hero-grid">
        <div class="stat-box">
            <div class="stat-item">
                <div class="stat-val white">{total_msgs:,}</div>
                <div class="stat-lbl">Total Messages (年度总数)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val cyan">{metrics['daily_avg']}</div>
                <div class="stat-lbl">Daily Average (日均消息)</div>
            </div>
        </div>

        <div class="stat-box">
            <div class="stat-item">
                <div class="stat-val cyan">{chars_sent:,}</div>
                <div class="stat-lbl">Chars Sent (发送字数)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val pink">{chars_recv:,}</div>
                <div class="stat-lbl">Chars Received (接收字数)</div>
            </div>
        </div>

        <div class="stat-box">
            <div class="stat-item">
                <div class="stat-val white">{craziest_day}</div>
                <div class="stat-lbl">Craziest Date (最疯一天)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val pink">{craziest_count:,}</div>
                <div class="stat-lbl">Msgs that Day (当日消息)</div>
            </div>
        </div>

        <div class="stat-box">
            <div class="stat-item">
                <div class="stat-val cyan" style="font-size: 1.6em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px; display:block; margin:0 auto;">
                    {top_contact_name}
                </div>
                <div class="stat-lbl">Top Contact (最密联系)</div>
            </div>
            <div class="stat-item">
                <div class="stat-val white">{top_contact_count:,}</div>
                <div class="stat-lbl">Messages (消息总数)</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>📅 Annual Heatmap</h3>
        <img src="data:image/png;base64,{charts.get('heatmap', '')}">
    </div>

    <div class="card">
        <h3>🏆 Top 10 Friends</h3>
        <img src="data:image/png;base64,{charts.get('rank_p', '')}">
    </div>
    
    <div class="card">
        <h3>📢 Top 10 Groups</h3>
        <img src="data:image/png;base64,{charts.get('rank_g', '')}">
    </div>

    {render_profiles(p_profiles, "👤 Top Friends Analysis")}
    
    {render_profiles(g_profiles, "👥 Top Groups Analysis")}

</body>
</html>
"""

with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 网页已生成: Final_Report.html")