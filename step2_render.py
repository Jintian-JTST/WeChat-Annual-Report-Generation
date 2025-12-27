import json
import webbrowser
import os

# 读取数据
print("正在读取 report_data.json ...")
try:
    with open("report_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("❌ 没找到数据文件！请先运行 step1_analyze.py")
    exit()

metrics = data["metrics"]
charts = data["charts"]
profiles = data["profiles"]

# ===================== HTML 模板 (在这里改 CSS) =====================
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>WeChat Analysis Report</title>
<style>
    /* 全局变量 */
    :root {{
        --bg-color: #0d0d0d;
        --card-bg: #1a1a1a;
        --text-main: #e0e0e0;
        --accent: #00f2ea;
        --highlight: #ff0050;
    }}

    body {{
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        background-color: var(--bg-color);
        color: var(--text-main);
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
    }}

    /* 标题样式 */
    h1 {{ text-align: center; font-size: 3em; margin-bottom: 10px; text-shadow: 0 0 20px rgba(0, 242, 234, 0.3); }}
    .subtitle {{ text-align: center; color: #666; margin-bottom: 50px; letter-spacing: 2px; }}
    
    /* 卡片通用样式 */
    .card {{
        background: var(--card-bg);
        border: 1px solid #333;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    
    h2 {{ border-left: 4px solid var(--accent); padding-left: 15px; margin-top: 0; color: #fff; }}

    /* 顶部数据网格 */
    .hero-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }}
    .hero-box {{ 
        background: linear-gradient(145deg, #1f1f1f, #151515); 
        padding: 30px; border-radius: 12px; text-align: center; border: 1px solid #333; 
    }}
    .hero-val {{ font-size: 3em; font-weight: bold; color: #fff; }}
    .hero-lbl {{ color: #888; text-transform: uppercase; font-size: 0.9em; margin-bottom: 5px; }}

    /* 深度画像样式 */
    .profile-item {{
        background: #111;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 40px;
    }}
    .profile-header {{
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 15px;
    }}
    .rank-badge {{ background: #333; color: #fff; padding: 5px 10px; border-radius: 6px; font-weight: bold; }}
    .viz-block {{ margin-bottom: 20px; }}
    
    img {{ max-width: 100%; display: block; margin: 0 auto; border-radius: 8px; }}
</style>
</head>
<body>

    <h1>2025 年度总结</h1>
    <div class="subtitle">{metrics['start']} ~ {metrics['end']}</div>

    <div class="hero-grid">
        <div class="hero-box">
            <div class="hero-lbl">Total Messages</div>
            <div class="hero-val" style="color:var(--accent)">{metrics['total']:,}</div>
        </div>
        <div class="hero-box">
            <div class="hero-lbl">Total Characters</div>
            <div class="hero-val" style="color:var(--highlight)">{metrics['chars']:,}</div>
        </div>
    </div>

    <div class="card">
        <h2>📅 活跃度热力图</h2>
        <img src="data:image/png;base64,{charts['heatmap']}">
    </div>

    <div class="card">
        <h2>🏆 好友排行榜 (Top 10)</h2>
        <img src="data:image/png;base64,{charts['rank_p']}">
    </div>
    
    <div class="card">
        <h2>📢 群聊排行榜 (Top 10)</h2>
        <img src="data:image/png;base64,{charts['rank_g']}">
    </div>

    <h2 style="margin-top: 60px; text-align:center; border:none;">🔍 核心好友深度解析</h2>
    
    { "".join([f'''
    <div class="profile-item">
        <div class="profile-header">
            <div>
                <span class="rank-badge">#{p['rank']}</span>
                <span style="font-size: 1.4em; margin-left: 10px; font-weight: bold;">{p['name']}</span>
            </div>
            <div style="font-family: monospace; font-size: 1.2em; color: var(--accent);">{p['count']:,} 条</div>
        </div>
        
        <div class="viz-block">
            <div style="color:#666; font-size:0.8em; margin-bottom:5px;">💬 话痨程度对比 (条数 & 字数)</div>
            <img src="data:image/png;base64,{p['compare']}">
        </div>
        
        <div class="viz-block">
            <div style="color:#666; font-size:0.8em; margin-bottom:5px;">📅 交互热力图</div>
            <img src="data:image/png;base64,{p['heatmap']}">
        </div>
    </div>
    ''' for p in profiles]) }

</body>
</html>
"""

# 保存并自动打开
filename = "Final_Report.html"
with open(filename, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 网页已生成: {filename}")
# 自动在浏览器打开 (可选)
# webbrowser.open('file://' + os.path.realpath(filename))