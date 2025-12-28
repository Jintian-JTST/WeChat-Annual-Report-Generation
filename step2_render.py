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
    s_d = datetime.strptime(metrics.get("start", "2025.01.01"), "%Y.%m.%d")
    e_d = datetime.strptime(metrics.get("end", "2025.12.31"), "%Y.%m.%d")
    start_date = metrics.get("start")
    end_date = metrics.get("end")
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

craziest_day = metrics.get("craziest_day", "N/A")
craziest_count = metrics.get("craziest_count", 0)
top_contact_name = metrics.get("top_contact_name", "N/A")
top_contact_count = metrics.get("top_contact_count", 0)

# 书本换算
books_written = chars_sent / 730000
books_read = chars_recv / 200000

# ===================== 2. HTML 渲染函数 (深度分析布局重构) =====================

def render_profile_list(profile_list):
    if not profile_list: return "<p style='text-align:center; color:#666'>无数据</p>"
    html = ""
    for p in profile_list:
        # 下方左右分栏逻辑：如果有词云，右边放词云；没有词云，左边的图表稍微居中一点
        wc_img = f'<img src="data:image/png;base64,{p["wordcloud"]}">' if p.get("wordcloud") else ""
        
        # 布局结构：
        # Row 1: Compare (饼图/对比图)
        # Row 2: Heatmap (热力图)
        # Row 3: Split (左:Hourly, 右:Wordcloud)
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
    :root {{
        --bg: #000000;
        --card-bg: #111;
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
        height: 100vh; width: 100%;
        overflow-y: scroll;
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

    /* 动画 */
    .anim-fade {{ opacity: 0; transform: translateY(40px); transition: all 0.8s ease-out; }}
    .anim-scale {{ opacity: 0; transform: scale(0.9); transition: all 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
    
    .section.active .anim-fade {{ opacity: 1; transform: translateY(0); }}
    .section.active .anim-scale {{ opacity: 1; transform: scale(1); }}

    /* Title 渐变回归 */
    .intro-title {{
        font-size: 4.5rem; font-weight: 900; line-height: 1.1; text-align: center;
        background: linear-gradient(135deg, #ff3366 0%, #ffffff 50%, #00f2ff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }}
    .sub-text {{ color: #888; font-size: 1.2rem; margin-top: 10px; letter-spacing: 2px; }}

    /* 字体优化 */
    .hero-val, .split-num {{
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; /* 统一字体 */
        font-weight: 800;
    }}

    /* 卡片通用 */
    .hero-card {{
        background: rgba(20,20,20,0.9);
        border: 1px solid #333; border-radius: 24px;
        padding: 30px; width: 100%; max-width: 500px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }}
    
    .hero-lbl {{ font-size: 1.6rem; color: #ffffff; font-weight: bold; margin-bottom: 10px; }}
    .hero-val {{ font-size: 4.5rem; line-height: 1; margin: 15px 0; }}
    .unit {{ font-size: 1.5rem; margin-left: 5px; color: #ccc; font-weight: normal; }}

    /* 颜色变体 */
    .c-blue .hero-val {{ color: var(--accent-blue); text-shadow: 0 0 25px rgba(0,242,255,0.4); }}
    .c-green .hero-val {{ color: var(--accent-green); text-shadow: 0 0 25px rgba(0,255,136,0.4); }}
    .c-gold .hero-val {{ color: var(--accent-gold); text-shadow: 0 0 25px rgba(255,215,0,0.4); }}
    
    /* 双卡片布局 */
    .dual-wrapper {{ display: flex; flex-direction: column; gap: 20px; width: 100%; max-width: 500px; }}
    .split-card {{
        background: #111; border: 1px solid #333; border-radius: 20px;
        padding: 25px; display: flex; flex-direction: column; justify-content: center;
        flex: 1; text-align: left; position: relative; overflow: hidden;
    }}
    .split-card::after {{
        content: ''; position: absolute; right: -20px; top: -20px; width: 100px; height: 100px;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0) 70%); border-radius: 50%;
    }}
    .split-label {{ font-size: 1.4rem; color: #fff; margin-bottom: 5px; font-weight: bold; }}
    .split-num {{ font-size: 3rem; margin-bottom: 5px; position: relative; z-index: 2; }}
    .split-desc {{ font-size: 1rem; color: #888; position: relative; z-index: 2; }}

    /* 疯狂日 */
    .crazy-box {{ text-align: center; }}
    .crazy-date {{ font-size: 2rem; color: #fff; margin-bottom: 10px; }}
    .crazy-count {{ 
        font-size: 7rem; font-weight: 900; line-height: 1; margin: 10px 0;
        background: linear-gradient(to top, #ff0000, #ff8800);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 15px rgba(255,50,50,0.5));
        font-family: 'Segoe UI', sans-serif;
    }}

    /* 图表页：尺寸放大 */
    .chart-box {{
        width: 100%; 
        max-width: 1000px; /* 放大到 1000px */
        background: #111; padding: 20px; border-radius: 16px; border: 1px solid #222;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }}
    .page-title {{ font-size: 2rem; margin-bottom: 25px; font-weight: bold; color: #fff; text-align: center; }}
    img {{ width: 100%; height: auto; border-radius: 8px; display: block; }}

    /* 详细列表页新布局 */
    .section.scrollable {{ display: block; overflow-y: auto; padding-top: 80px; padding-bottom: 100px; }}
    
    .detail-card {{ 
        background: #161616; border: 1px solid #222; padding: 25px; 
        border-radius: 16px; margin: 0 auto 40px; max-width: 900px; /* 列表卡片也宽一点 */
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
</style>
</head>
<body>

<div class="snap-container">

    <section class="section">
        <div class="intro-title anim-scale">2025<br>微信年度报告</div>
        <div class="sub-text anim-fade" style="transition-delay:0.2s">{start_date} - {end_date}</div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="hero-card c-blue anim-scale">
            <div class="hero-lbl">年度总消息</div>
            <div class="hero-val">{total_msgs:,}<span class="unit">条</span></div>
            <div class="sub-text">无论废话还是情话，都是回忆</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="hero-card c-green anim-scale">
            <div class="hero-lbl">平均每天发送</div>
            <div class="hero-val">{metrics["daily_avg"]:,}<span class="unit">条</span></div>
            <div class="sub-text">这就是你生活的节奏</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="page-title anim-fade">文字产出量</div>
        <div class="dual-wrapper">
            <div class="split-card anim-scale" style="border-left: 5px solid var(--accent-purple);">
                <div class="split-label">📤 我发送的</div>
                <div class="split-num" style="color:var(--accent-purple)">
                    {chars_sent:,} <span class="unit" style="font-size:1rem">字</span>
                </div>
                <div class="split-desc">相当于写了 <span style="color:#fff; font-weight:bold;">{books_written:.1f}</span> 本《红楼梦》</div>
            </div>

            <div class="split-card anim-scale" style="border-left: 5px solid var(--accent-blue); transition-delay: 0.1s;">
                <div class="split-label">📥 我接收的</div>
                <div class="split-num" style="color:var(--accent-blue)">
                    {chars_recv:,} <span class="unit" style="font-size:1rem">字</span>
                </div>
                <div class="split-desc">相当于读了 <span style="color:#fff; font-weight:bold;">{books_read:.1f}</span> 本《三体》</div>
            </div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="hero-card anim-scale" style="border:none; background:none; box-shadow:none;">
            <div class="hero-lbl">🔥 消息最爆炸的一天</div>
            <div class="crazy-box">
                <div class="crazy-count">{craziest_count:,}</div>
                <div class="crazy-date">{craziest_day}</div>
            </div>
            <div class="sub-text">这一天，你的手指一定很累吧</div>
        </div>
        <div class="arrow">﹀</div>
    </section>

    <section class="section">
        <div class="hero-card c-gold anim-scale">
            <div class="hero-lbl">❤️ 年度最亲密</div>
            <div class="hero-val" style="font-size: 3.5rem;">{top_contact_name}</div>
            <div class="sub-text">你们一共互动了 <span style="color:#fff; font-weight:bold;">{top_contact_count:,}</span> 条消息</div>
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
            <div class="sub-text anim-fade">向下滚动查看所有人详情</div>
        </div>

        <div class="anim-fade" style="transition-delay:0.2s">
            <h3 style="text-align:center; color:var(--accent-blue)">👤 好友详情</h3>
            {render_profile_list(p_profiles)}
            
            <h3 style="text-align:center; color:var(--accent-green); margin-top:80px;">👥 群聊详情</h3>
            {render_profile_list(g_profiles)}
        </div>

        <div style="text-align:center; padding: 60px 0; color: #444;">— End —</div>
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

print(f"✅ 完美版报告已生成！")
print("1. 标题已恢复红蓝渐变。")
print("2. 字体统一为粗圆体。")
print("3. 中间图表（作息/词云/Rank）已放大到巨幕尺寸。")
print("4. 已新增第10页：群聊 Top 10 排行榜。")
print("5. 深度分析已改为：上饼图、中热力、下左右分栏结构。")
print("👉 双击 Final_Report.html 即可体验。")