import json
import webbrowser
import os

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

# ===================== HTML 生成逻辑 =====================

def render_profiles(profile_list, title):
    if not profile_list: return ""
    
    html_block = f'<h2 class="section-header">{title}</h2>'
    
    for p in profile_list:
        # 处理可能缺失的词云
        wc_html = f'<div class="viz-block"><img src="data:image/png;base64,{p["wordcloud"]}"></div>' if p.get("wordcloud") else ""
        
        html_block += f"""
        <div class="profile-item">
            <div class="profile-header">
                <div>
                    <span class="rank-badge">#{p['rank']}</span>
                    <span class="name-label">{p['name']}</span>
                </div>
                <div class="count-label">{p['count']:,} Msgs</div>
            </div>
            
            <div class="viz-block">
                <img src="data:image/png;base64,{p['compare']}">
            </div>
            
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
    :root {{ --bg: #0d0d0d; --card: #161616; --accent: #00f2ea; --text: #ccc; }}
    body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: var(--bg); color: var(--text); max-width: 800px; margin: 0 auto; padding: 40px; }}
    
    h1 {{ text-align: center; color: #fff; text-shadow: 0 0 15px rgba(0,242,234,0.4); font-size: 2.5em; margin-bottom: 5px; }}
    .sub {{ text-align: center; color: #666; margin-bottom: 40px; font-size: 0.9em; letter-spacing: 1px; }}
    
    .hero {{ display: flex; justify-content: space-between; gap: 20px; margin-bottom: 40px; }}
    .stat-box {{ flex: 1; background: #111; border: 1px solid #333; padding: 20px; text-align: center; border-radius: 8px; }}
    .stat-val {{ font-size: 2em; font-weight: bold; color: #fff; }}
    .stat-lbl {{ font-size: 0.8em; color: #888; text-transform: uppercase; }}
    
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
    img {{ width: 100%; display: block; border-radius: 6px; }}
</style>
</head>
<body>

    <h1>2025 REWIND</h1>
    <div class="sub">{metrics['start']} - {metrics['end']} • WECHAT DATA</div>

    <div class="hero">
        <div class="stat-box"><div class="stat-lbl">Total Messages</div><div class="stat-val" style="color:#00f2ea">{metrics['total']:,}</div></div>
        <div class="stat-box"><div class="stat-lbl">Total Characters</div><div class="stat-val" style="color:#ff0050">{metrics['chars']:,}</div></div>
    </div>

    <div class="card">
        <h3>📅 Activity Heatmap</h3>
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

    {render_profiles(p_profiles, "👤 Top Friends Analysis")}
    
    {render_profiles(g_profiles, "👥 Top Groups Analysis")}

</body>
</html>
"""

with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 网页已生成: Final_Report.html")
# webbrowser.open('file://' + os.path.realpath("Final_Report.html"))