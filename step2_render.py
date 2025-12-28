import json
import os
from datetime import datetime

print("正在读取 report_data.json ...")
try:
    with open("report_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("❌ 没找到数据！请先运行 step1_analyze.py")
    exit()

# ===================== 1. 数据准备 =====================
metrics = data.get("metrics", {})
charts = data.get("charts", {})
p_profiles = data.get("private_profiles", [])
g_profiles = data.get("group_profiles", [])
global_charts = data.get("global_charts", {})

try:
    start_date = metrics.get("start", "2025.01.01")
    end_date = metrics.get("end", "2025.12.31")
except:
    start_date = "2025.01.01"
    end_date = "2025.12.31"

# 基础数据
total_msgs = metrics.get("total", 0)
days_span = 365 
metrics["daily_avg"] = int(total_msgs / days_span) if days_span > 0 else 0

total_chars = metrics.get("chars", metrics.get("chars_total", 0))
chars_sent = metrics.get("chars_sent", int(total_chars * 0.5))
chars_recv = metrics.get("chars_recv", int(total_chars * 0.5))

# 日期格式化 (1月16日)
raw_day = metrics.get("craziest_day", "N/A")
try:
    if "-" in raw_day:
        parts = raw_day.split("-")
        craziest_day = f"{int(parts[-2])}月{int(parts[-1])}日"
    else:
        craziest_day = raw_day
except:
    craziest_day = raw_day

craziest_count = metrics.get("craziest_count", 0)
top_contact_name = metrics.get("top_contact_name", "N/A")
top_contact_count = metrics.get("top_contact_count", 0)

# 书本换算
books_written = chars_sent / 253000
books_read = chars_recv / 200000

# ===================== 2. HTML 渲染函数 =====================

def render_profile_list(profile_list):
    if not profile_list: return "<p style='text-align:center; color:#666'>无数据</p>"
    html = ""
    for p in profile_list:
        wc_img = f'<img src="data:image/png;base64,{p["wordcloud"]}">' if p.get("wordcloud") else ""
        
        # 群聊 Top10 发言人图表
        member_bar_html = ""
        if p.get("member_bar"):
            member_bar_html = f"""
            <div class="viz-row-full">
                <div class="viz-label">🏆 群内话痨排行榜 (Top 10)</div>
                <img src="data:image/png;base64,{p["member_bar"]}">
            </div>
            """
        
        html += f"""
        <div class="detail-card">
            <div class="d-header">
                <span class="d-rank">#{p["rank"]}</span>
                <span class="d-name">{p["name"]}</span>
                <span class="d-count">{p["count"]:,} 条</span>
            </div>
            
            <div class="viz-row-full">
                <div class="viz-label">收发对比</div>
                <img src="data:image/png;base64,{p["compare"]}">
            </div>

            {member_bar_html}

            <div class="viz-row-full">
                <div class="viz-label">全年活跃热力图</div>
                <img src="data:image/png;base64,{p["heatmap"]}">
            </div>

            <div class="viz-row-split">
                <div class="viz-half">
                    <div class="viz-label">24小时作息</div>
                    <img src="data:image/png;base64,{p["hourly"]}">
                </div>
                <div class="viz-half">
                    <div class="viz-label">专属关键词</div>
                    {wc_img}
                </div>
            </div>
        </div>
        """
    return html

# ===================== 3. HTML 主体 =====================

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2025 微信年度报告</title>
<style>
    /* 隐藏滚动条 */
    ::-webkit-scrollbar {{
        display: none; 
    }}

    :root {{
        --bg: #000000;
        --text: #ffffff;
        --accent-blue: #00f2ff;
        --accent-purple: #bd00ff;
        --accent-red: #ff3366;
        --accent-gold: #ffd700;
        --accent-green: #00ff88;
    }}

    * {{ box-sizing: border-box; }}
    
    body {{
        margin: 0; padding: 0;
        font-family: 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
        background: var(--bg);
        color: var(--text);
        overflow: hidden; 
    }}

    .snap-container {{
        height: 100vh; width: 100vw;
        overflow-y: scroll;
        overflow-x: hidden; /* 关键：防止横向溢出 */
        scroll-snap-type: y mandatory;
        scroll-behavior: smooth;
    }}

    .section {{
        height: 100vh; width: 100%;
        scroll-snap-align: start;
        position: relative;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        padding: 20px;
        border-bottom: 1px solid #1a1a1a;
        overflow: hidden;
    }}

    /* === 动画系统 === */
    .anim-fade {{ opacity: 0; transform: translateY(40px); transition: all 0.8s ease-out; }}
    .anim-scale {{ opacity: 0; transform: scale(0.9); transition: all 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
    
    .section.active .anim-fade {{ opacity: 1; transform: translateY(0); }}
    .section.active .anim-scale {{ opacity: 1; transform: scale(1); }}

    /* === UI 样式 === */
    
    .intro-title {{
        font-size: 5rem; font-weight: 900; line-height: 1.1; text-align: center;
        background: linear-gradient(135deg, #ff3366 0%, #ffffff 50%, #00f2ff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }}

    .floating-stat {{
        text-align: center;
        width: 100%;
        max-width: 800px;
        padding: 0 20px;
    }}
    
    .stat-label {{
        font-size: 1.8rem; color: #fff; font-weight: bold; margin-bottom: 10px;
        opacity: 0.9;
        letter-spacing: 2px;
    }}
    
    .stat-val {{
        font-family: 'Segoe UI', sans-serif;
        font-size: 6rem;
        font-weight: 800; 
        line-height: 1; 
        margin: 20px 0;
        letter-spacing: -2px;
    }}

    .stat-desc {{ font-size: 1.2rem; color: #888; letter-spacing: 1px; margin-top: 10px; }}
    .unit {{ font-size: 2rem; font-weight: normal; margin-left: 10px; color: #bbb; }}

    .c-blue .stat-val {{ color: var(--accent-blue); text-shadow: 0 0 40px rgba(0,242,255,0.4); }}
    .c-green .stat-val {{ color: var(--accent-green); text-shadow: 0 0 40px rgba(0,255,136,0.4); }}
    .c-gold .stat-val {{ color: var(--accent-gold); text-shadow: 0 0 40px rgba(255,215,0,0.4); }}
    .c-fire .stat-val {{ 
        background: linear-gradient(to top, #ff0000, #ff8800);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 20px rgba(255,50,50,0.5));
    }}

    .text-split-container {{
        display: flex; justify-content: center; align-items: center;
        width: 100%; max-width: 900px; gap: 60px;
    }}
    .text-col {{ flex: 1; text-align: left; }}
    .text-col.right {{ text-align: right; }}
    .divider-line {{ width: 1px; height: 150px; background: linear-gradient(to bottom, transparent, #333, transparent); }}
    .col-label {{ font-size: 1.5rem; font-weight: bold; margin-bottom: 15px; color: #fff; }}
    .col-num {{ font-size: 4rem; font-weight: 800; line-height: 1; margin-bottom: 15px; font-family: 'Segoe UI', sans-serif; }}
    .col-desc {{ font-size: 1rem; color: #888; line-height: 1.5; }}
    .col-highlight {{ color: #fff; font-weight: bold; font-size: 1.1em; }}

    .chart-box {{
        width: 100%; max-width: 1000px;
        background: #111; padding: 20px; border-radius: 16px; border: 1px solid #222;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }}
    .page-title {{ font-size: 2rem; margin-bottom: 30px; font-weight: bold; color: #fff; text-align: center; }}
    img {{ width: 100%; height: auto; border-radius: 8px; display: block; }}

/* === 修复长列表页黑屏/显示不全的核心代码 === */
    .section.scrollable {{
    /* 仍然是一整页 */
    height: 100vh !important;
    min-height: 100vh;

    /* 保持 snap（这是关键） */
    scroll-snap-align: start !important;

    /* 不用 flex，避免垂直居中 */
    display: block !important;

    /* 👉 关键：页内滚动 */
    overflow-y: auto !important;
    overflow-x: hidden;

    padding-top: 80px;
    padding-bottom: 120px;
    background: var(--bg);
    }}
        .detail-card {{ 
        background: #161616; border: 1px solid #222; padding: 25px; 
        border-radius: 16px; margin: 0 auto 40px; max-width: 900px; 
    }}
    .d-header {{ display: flex; align-items: center; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 20px; }}
    .d-rank {{ background: #333; padding: 4px 10px; border-radius: 6px; margin-right: 15px; font-weight: bold; }}
    .d-name {{ font-weight: bold; font-size: 1.4rem; flex: 1; color: #fff; }}
    .d-count {{ color: var(--accent-blue); font-weight: bold; font-size: 1.2rem; }}
    
    .viz-label {{ color: #666; font-size: 0.9rem; margin-bottom: 8px; text-align: center; }}
    .viz-row-full {{ margin-bottom: 25px; background: #0b0b0b; padding: 15px; border-radius: 10px; }}
    .viz-row-split {{ display: flex; gap: 20px; }}
    .viz-half {{ flex: 1; background: #0b0b0b; padding: 15px; border-radius: 10px; }}

    .arrow {{ position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); font-size: 1.5rem; color: #444; animation: float 2s infinite; }}
    @keyframes float {{ 0%,100%{{transform:translate(-50%,0)}} 50%{{transform:translate(-50%,10px)}} }}

    /* GitHub 按钮和免责声明 */
    .github-btn {{
        display: inline-block; margin: 40px 0; padding: 15px 30px;
        background: #222; border: 1px solid #444; color: #fff;
        text-decoration: none; border-radius: 30px; font-weight: bold;
        transition: all 0.3s;
    }}
    .github-btn:hover {{
        background: #fff; color: #000;
        transform: translateY(-3px); box-shadow: 0 10px 20px rgba(255,255,255,0.2);
    }}
    .disclaimer-box {{
        font-size: 0.85rem; color: #444; line-height: 1.6; text-align: center; max-width: 600px;
    }}

</style>
</head>
<body>

<div class="snap-container">

    <section class="section">
        <div class="intro-title anim-scale">2025<br>微信年度报告</div>
        <div class="stat-desc anim-fade" style="transition-delay:0.2s">{start_date} - {end_date}</div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="floating-stat c-blue anim-scale">
            <div class="stat-label">年度总消息</div>
            <div class="stat-val">{total_msgs:,}<span class="unit">条</span></div>
            <div class="stat-desc">无论废话还是情话，都是回忆</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="floating-stat c-green anim-scale">
            <div class="stat-label">平均每天发送</div>
            <div class="stat-val">{metrics["daily_avg"]:,}<span class="unit">条</span></div>
            <div class="stat-desc">这就是你生活的节奏</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade" style="margin-bottom: 60px;">文字产出量</div>
        <div class="text-split-container">
            <div class="text-col right anim-fade" style="transition-delay: 0s;">
                <div class="col-label">📤 我发送的</div>
                <div class="col-num" style="color:var(--accent-purple)">{chars_sent:,}<span class="unit">字</span></div>
                <div class="col-desc">相当于写了<br><span class="col-highlight">{books_written:.1f}</span> 本《围城》</div>
            </div>
            <div class="divider-line anim-scale"></div>
            <div class="text-col anim-fade" style="transition-delay: 0.1s;">
                <div class="col-label">📥 我接收的</div>
                <div class="col-num" style="color:var(--accent-blue)">{chars_recv:,}<span class="unit">字</span></div>
                <div class="col-desc">相当于读了<br><span class="col-highlight">{books_read:.1f}</span> 本《三体》</div>
            </div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="floating-stat c-fire anim-scale">
            <div class="stat-label">🔥 消息最爆炸的一天</div>
            <div class="stat-val" style="font-size: 7rem;">{craziest_count:,}<span class="unit">条</span></div>
            <div class="stat-label" style="font-size: 1.5rem; margin-top:0;">{craziest_day}</div>
            <div class="stat-desc" style="margin-top:20px;">这一天，你的手指一定很累吧</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="floating-stat c-gold anim-scale">
            <div class="stat-label">❤️ 年度最亲密</div>
            <div class="stat-val" style="font-size: 5rem;">{top_contact_name}</div>
            <div class="stat-desc">你们一共互动了 <span style="color:#fff; font-weight:bold;">{top_contact_count:,}</span> 条消息</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">全年活跃热力图</div>
        <div class="chart-box anim-scale" style="transition-delay:0.1s">
            <img src="data:image/png;base64,{charts.get("heatmap","")}">
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">你的作息规律</div>
        <div class="chart-box anim-scale" style="transition-delay:0.1s">
            <img src="data:image/png;base64,{global_charts.get("my_hourly","")}">
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">你的年度关键词</div>
        <div class="chart-box anim-scale" style="transition-delay:0.1s">
            <img src="data:image/png;base64,{global_charts.get("my_wordcloud","")}">
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">Top 10 好友排行</div>
        <div class="chart-box anim-scale" style="transition-delay:0.1s">
            <img src="data:image/png;base64,{charts.get("rank_p","")}">
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">Top 10 群聊排行</div>
        <div class="chart-box anim-scale" style="transition-delay:0.1s">
            <img src="data:image/png;base64,{charts.get("rank_g","")}">
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section scrollable">
        <div style="text-align:center; margin-bottom:40px;">
            <div class="page-title anim-fade">📋 深度分析报告</div>
            <div class="stat-desc anim-fade">向下滚动查看所有人详情</div>
        </div>

        <div class="anim-fade" style="transition-delay:0.2s">
            <h3 style="text-align:center; color:var(--accent-blue)">👤 好友详情</h3>
            {render_profile_list(p_profiles)}
            
            <h3 style="text-align:center; color:var(--accent-green); margin-top:80px;">👥 群聊详情</h3>
            {render_profile_list(g_profiles)}
        </div>
        <div class="arrow">﹀</div>
    </section>

<section class="section">
    <div class="intro-title" style="font-size: 3rem;">关于本项目</div>

    <div class="floating-stat" style="margin-top: 30px;">
        <div class="stat-label" style="font-size: 1.2rem; color:#888;">作者</div>
        <div class="stat-val" style="font-size: 2.5rem; margin: 10px 0;">JTST</div>

        <div class="stat-label" style="font-size: 1.2rem; color:#888; margin-top: 20px;">
            开发时间
        </div>
        <div class="stat-val" style="font-size: 2.5rem; margin: 10px 0;">3 天</div>
    </div>

    <div style="text-align:center; margin-top:30px;">
        <a href="https://github.com/Jintian-JTST/WeChat-Annual-Report-Generation"
           target="_blank"
           class="github-btn">
            🔗 Jintian-JTST / WeChat-Annual-Report-Generation
        </a>
    </div>

    <div class="disclaimer-box" style="margin: 30px auto;">
        <div style="font-weight:bold; margin-bottom:10px; color:#666;">免责声明</div>
        <p style="color:#ff0000;">
            本项目为开源工具，仅供个人娱乐与数据回顾使用。<br>
            所有数据分析均在本地设备运行，不涉及任何云端上传。
        </p>
    </div>
</section>

</div>

<script>
    const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                entry.target.classList.add('active');
            }}
        }});
    }}, {{ threshold: 0.5 }});

    document.querySelectorAll('.section').forEach(section => {{
        observer.observe(section);
    }});
</script>

</body>
</html>
"""
with open("Final_Report.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Step 2 完成！")
print(f"报告已生成：Final_Report.html")
# 打开报告
os.startfile("Final_Report.html")