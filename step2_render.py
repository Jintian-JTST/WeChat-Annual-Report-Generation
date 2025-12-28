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

# ===================== 1. 数据计算逻辑 =====================
metrics = data.get("metrics", {})
charts = data.get("charts", {})
p_profiles = data.get("private_profiles", [])
g_profiles = data.get("group_profiles", [])
global_charts = data.get("global_charts", {})

try:
    start_date = metrics.get("start", "2025.01.01")
    end_date = metrics.get("end", "2025.12.31")
    s_d = datetime.strptime(start_date, "%Y.%m.%d")
    e_d = datetime.strptime(end_date, "%Y.%m.%d")
    days_span = (e_d - s_d).days + 1
except:
    start_date = "2025.01.01"
    end_date = "2025.12.31"
    days_span = 365

total_msgs = metrics.get("total", 0)
if "daily_avg" not in metrics:
    metrics["daily_avg"] = int(total_msgs / days_span) if days_span > 0 else 0

total_chars = metrics.get("chars", metrics.get("chars_total", 0))
chars_sent = metrics.get("chars_sent", int(total_chars * 0.5))
chars_recv = metrics.get("chars_recv", int(total_chars * 0.5))

craziest_day = metrics.get("craziest_day", "N/A")
craziest_count = metrics.get("craziest_count", 0)
top_contact_name = metrics.get("top_contact_name", "N/A")
top_contact_count = metrics.get("top_contact_count", 0)

# ===================== 2. HTML 渲染函数 =====================

def render_profiles(profile_list, title):
    if not profile_list:
        return ""
    html_block = f'<h2 class="section-header scroll-item">{title}</h2>'
    for p in profile_list:
        wc_html = (
            f'<div class="viz-block"><img src="data:image/png;base64,{p["wordcloud"]}"></div>'
            if p.get("wordcloud") else ""
        )
        member_html = ""
        if p.get("member_bar"):
            member_html = f"""
            <div class="viz-block">
                <div class="viz-label">🏆 群内最活跃成员</div>
                <img src="data:image/png;base64,{p["member_bar"]}">
            </div>
            """
        html_block += f"""
        <div class="profile-item scroll-item">
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
            <div class="viz-block"><img src="data:image/png;base64,{p["heatmap"]}"></div>
            <div class="grid-2">
                <div class="viz-block"><img src="data:image/png;base64,{p["hourly"]}"></div>
                {wc_html}
            </div>
        </div>
        """
    return html_block

# ===================== 3. HTML 主体 (视差滚动版) =====================

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2025 微信年度报告</title>
<style>
    :root {{
        --bg: #0b0b0b;
        --card-bg: #141414;
        --blue-accent: #00e5ff;
        --red-accent: #ff4d6d;
        --text-main: #ffffff;
        --text-sub: rgba(255,255,255,0.6);
    }}

    body {{
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        background: var(--bg);
        color: var(--text-main);
        margin: 0;
        padding: 0;
        overflow-x: hidden;
    }}

    /* === 核心布局：视差效果 === */
    
    /* 1. 封面层：固定在背后，不动 */
    .intro-screen {{
        position: fixed; /* 关键：固定定位 */
        top: 0;
        left: 0;
        width: 100%;
        height: 100vh;
        z-index: 1; /* 层级最低 */
        
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        background: radial-gradient(circle at center, #1a1a1a 0%, #000000 100%);
    }}

    /* 2. 内容层：背景不透明，初始位置在屏幕下方 */
    .main-wrapper {{
        position: relative;
        z-index: 10; /* 层级高，盖住封面 */
        background-color: var(--bg); /* 必须有背景色，否则是透明的 */
        margin-top: 100vh; /* 关键：把内容顶到第二屏 */
        
        padding-top: 60px; /* 内容顶部的留白 */
        padding-bottom: 100px;
        min-height: 100vh;
        
        /* 顶部阴影，增加层次感，像一张纸盖上来 */
        box-shadow: 0 -20px 50px rgba(0,0,0, 1); 
        border-top: 1px solid #333;
        border-radius: 24px 24px 0 0; /* 顶部圆角 */
    }}

    .container {{
        max-width: 900px;
        margin: 0 auto;
        padding: 0 20px;
    }}

    /* === 封面动画元素 === */
    .intro-title {{
        font-size: 4.5em;
        font-weight: 900;
        margin: 0;
        background: linear-gradient(45deg, var(--blue-accent), #fff, var(--red-accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: fadeInDown 1.5s ease-out;
    }}

    .intro-sub {{
        font-size: 1.3em;
        color: var(--text-sub);
        margin-top: 20px;
        letter-spacing: 5px;
        animation: fadeInUp 1.5s ease-out;
    }}

    .scroll-hint {{
        position: absolute;
        bottom: 50px;
        color: var(--text-sub);
        font-size: 0.9em;
        animation: bounce 2s infinite;
        opacity: 0.8;
    }}

    /* === 滚动触发动画 (Scroll Reveal) === */
    .scroll-item {{
        opacity: 0;
        transform: translateY(60px) scale(0.98); /* 稍微缩小一点，更有弹出的感觉 */
        transition: all 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
    }}

    .scroll-item.visible {{
        opacity: 1;
        transform: translateY(0) scale(1);
    }}

    /* === 卡片与图表样式 === */
    .hero-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 25px;
        margin-bottom: 80px;
    }}

    .stat-card {{
        display: flex;
        flex-direction: column;
        min-height: 320px;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #222;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        background: var(--card-bg);
    }}

    .card-top {{
        flex: 1;
        background: linear-gradient(180deg, rgba(0,229,255,0.1), rgba(0,0,0,0));
        border-bottom: 1px solid rgba(255,255,255,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }}

    .card-bottom {{
        flex: 1;
        background: linear-gradient(0deg, rgba(255,77,109,0.1), rgba(0,0,0,0));
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }}

    .stat-val {{ font-size: 2.2em; font-weight: bold; margin-bottom: 8px; color: #fff; text-align: center; }}
    .stat-lbl {{ font-size: 0.9em; color: var(--text-sub); letter-spacing: 1px; text-transform: uppercase; }}

    .card {{
        background: var(--card-bg);
        border: 1px solid #222;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 40px;
    }}
    .card h3 {{
        margin-top: 0; color: #fff; border-left: 4px solid var(--blue-accent);
        padding-left: 12px; font-size: 1.3em; margin-bottom: 20px;
    }}

    .section-header {{ text-align: center; margin: 80px 0 40px 0; color: #fff; font-size: 2em; font-weight: bold; }}
    
    .profile-item {{
        background: #111; border: 1px solid #222; padding: 25px; border-radius: 16px; margin-bottom: 50px;
    }}
    .profile-header {{
        display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; padding-bottom: 15px; margin-bottom: 20px;
    }}
    .rank-badge {{ background: #333; color: #fff; padding: 4px 10px; border-radius: 6px; font-weight: bold; }}
    .name-label {{ font-size: 1.4em; font-weight: bold; color: #fff; margin-left: 10px; }}
    .count-label {{ color: var(--blue-accent); font-size: 1.2em; font-family: monospace; font-weight: bold; }}
    
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
    .viz-block {{ margin-bottom: 15px; background: #0f0f0f; border-radius: 8px; padding: 10px; border: 1px solid #1a1a1a; }}
    .viz-label {{ font-size: 0.85em; color: #666; margin-bottom: 8px; text-align: center; }}
    img {{ width: 100%; border-radius: 6px; display: block; }}

    /* 动画定义 */
    @keyframes bounce {{ 0%, 20%, 50%, 80%, 100% {{transform: translateY(0);}} 40% {{transform: translateY(-10px);}} 60% {{transform: translateY(-5px);}} }}
    @keyframes fadeInDown {{ from {{opacity:0; transform:translateY(-30px);}} to {{opacity:1; transform:translateY(0);}} }}
    @keyframes fadeInUp {{ from {{opacity:0; transform:translateY(30px);}} to {{opacity:1; transform:translateY(0);}} }}
</style>
</head>

<body>

<div class="intro-screen" id="intro">
    <div class="intro-title">2025<br>微信年度报告</div>
    <div class="intro-sub">{start_date} - {end_date}</div>
    <div class="scroll-hint">向下滑动查看详情 ▼</div>
</div>

<div class="main-wrapper">
    <div class="container">
        
        <div class="hero-grid">
            <div class="stat-card scroll-item" style="transition-delay: 0s;">
                <div class="card-top blue">
                    <div class="stat-val">{total_msgs:,}</div>
                    <div class="stat-lbl">📨 年度消息总数</div>
                </div>
                <div class="card-bottom red">
                    <div class="stat-val">{metrics["daily_avg"]:,}</div>
                    <div class="stat-lbl">📅 日均消息数</div>
                </div>
            </div>

            <div class="stat-card scroll-item" style="transition-delay: 0.1s;">
                <div class="card-top blue">
                    <div class="stat-val">{chars_sent:,}</div>
                    <div class="stat-lbl">📤 我发送的字数</div>
                </div>
                <div class="card-bottom red">
                    <div class="stat-val">{chars_recv:,}</div>
                    <div class="stat-lbl">📥 接收的字数</div>
                </div>
            </div>

            <div class="stat-card scroll-item" style="transition-delay: 0.2s;">
                <div class="card-top blue">
                    <div class="stat-val">{craziest_day}</div>
                    <div class="stat-lbl">🔥 消息最密集的一天</div>
                </div>
                <div class="card-bottom red">
                    <div class="stat-val">{craziest_count:,}</div>
                    <div class="stat-lbl">当日消息数</div>
                </div>
            </div>

            <div class="stat-card scroll-item" style="transition-delay: 0.3s;">
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

        <div class="card scroll-item">
            <h3>🕒 我发消息的时间分布（全年）</h3>
            <img src="data:image/png;base64,{global_charts.get("my_hourly","")}">
        </div>

        <div class="card scroll-item">
            <h3>☁️ 我这一年的关键词</h3>
            <img src="data:image/png;base64,{global_charts.get("my_wordcloud","")}">
        </div>

        <div class="card scroll-item">
            <h3>📅 全年活跃热力图</h3>
            <img src="data:image/png;base64,{charts.get("heatmap","")}">
        </div>

        <div class="card scroll-item">
            <h3>🏆 聊天最频繁的 10 位好友</h3>
            <img src="data:image/png;base64,{charts.get("rank_p","")}">
        </div>

        <div class="card scroll-item">
            <h3>📢 最活跃的 10 个群聊</h3>
            <img src="data:image/png;base64,{charts.get("rank_g","")}">
        </div>

        {render_profiles(p_profiles, "👤 好友聊天深度分析")}
        {render_profiles(g_profiles, "👥 群聊活跃度分析")}

        <div style="height: 100px; text-align:center; color:#555; padding-top:50px;">
            <p>Generated by WeChat Report 2025</p>
        </div>
    </div>
</div>

<script>
    // 1. 滚动显现动画
    const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }}
        }});
    }}, {{ threshold: 0.1, rootMargin: "0px 0px -50px 0px" }});

    document.querySelectorAll('.scroll-item').forEach((el) => {{
        observer.observe(el);
    }});

    // 2. 封面淡出效果（可选：为了更丝滑，让封面在被盖住时变暗）
    window.addEventListener('scroll', () => {{
        const scrollY = window.scrollY;
        const intro = document.getElementById('intro');
        if (scrollY < window.innerHeight) {{
            // 随着滚动，封面透明度降低，且轻微缩小
            const opacity = 1 - (scrollY / window.innerHeight);
            const scale = 1 - (scrollY / window.innerHeight) * 0.1; 
            intro.style.opacity = opacity;
            intro.style.transform = `scale(${{scale}})`;
        }}
    }});
</script>

</body>
</html>
"""

with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 视差覆盖风格报告已生成！")
print("👉 请打开 Final_Report.html 体验效果：封面固定，内容从底部覆盖滑入。")