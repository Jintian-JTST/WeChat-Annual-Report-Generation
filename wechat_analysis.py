"""
WeChat Annual Report (Final Fixed Edition)
-----------------------------------
- 核心修复：增加【说话人数检测】，强制识别群聊（解决群聊为0的问题）
- 修复：移除图表标题中的 Emoji，解决微软雅黑报错
- 优化：屏蔽烦人的 UserWarning 红色日志
- 布局：群聊/单聊 完美分离
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import jieba
import re
from wordcloud import WordCloud
from io import BytesIO
import base64
import matplotlib.font_manager as fm
import platform
import warnings

# ===================== 0. 屏蔽警告 =====================
# 这一行会把那些 "Glyph missing" 的红色报错全部闭嘴
warnings.filterwarnings("ignore")

# ===================== 1. 配置区域 =====================
TARGET_YEAR = 2025
CSV_PATH = "messages.csv" # 如果你的文件叫 messages1.csv，请改这里
MIN_MSG_THRESHOLD = 100 

# ===================== 2. 核心工具函数 =====================

def clean_text_for_plot(text):
    """移除文本中的 Emoji 和非 BMP 字符"""
    if not isinstance(text, str): return str(text)
    emoji_pattern = re.compile(u'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    return text.strip()

def get_chinese_font():
    os_name = platform.system()
    font_list = []
    if os_name == "Windows":
        font_list = ["Microsoft YaHei", "SimHei"]
    elif os_name == "Darwin":
        font_list = ["PingFang SC", "Arial Unicode MS"]
    else:
        font_list = ["WenQuanYi Micro Hei"]
    return font_list

# ===================== 3. 风格设置 =====================
def set_dark_style():
    plt.style.use('dark_background')
    plt.rcParams["font.sans-serif"] = get_chinese_font() + plt.rcParams["font.sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False 
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['#00f2ea', '#ff0050', '#f9f871', '#00ff87', '#bd00ff'])
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['grid.color'] = '#222222'

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return img

# ===================== 4. 数据加载 (超级增强版) =====================
def load_data():
    print(f"正在加载数据: {CSV_PATH} ...")
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(CSV_PATH, encoding="gbk", on_bad_lines="skip")
        except:
            print("❌ 无法读取 CSV")
            return pd.DataFrame()

    if "Type" in df.columns:
        df = df[df["Type"] == 1].copy()
        
    df["dt"] = pd.to_datetime(df["StrTime"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df = df[df["dt"].dt.year == TARGET_YEAR]
    
    df["Date"] = df["dt"].dt.date
    df["Month"] = df["dt"].dt.month
    df["Hour"] = df["dt"].dt.hour
    df["SenderType"] = df["IsSender"].map({1: "我", 0: "对方"})
    df["StrContent"] = df["StrContent"].fillna("")
    df["NickName"] = df["NickName"].fillna("Unknown").str.strip()

    if "Sender" not in df.columns:
        df["Sender"] = df["SenderType"]
    else:
        df["Sender"] = df["Sender"].fillna("Unknown")
        df.loc[df["IsSender"] == 1, "Sender"] = "我"

    # === 【核心修复】智能识别群聊 ===
    # 策略1：看 TalkerId 是否以 @chatroom 结尾 (标准微信)
    # 策略2：看这个 NickName 下面，有多少个不同的 Sender (排除"我")
    # 如果 Sender 数量 > 1，那这绝对是个群
    
    # 1. 初始化全为 Private
    df["ChatType"] = "Private"
    
    # 2. 应用策略 1
    if "TalkerId" in df.columns:
        mask_chatroom = df["TalkerId"].astype(str).str.endswith("@chatroom")
        df.loc[mask_chatroom, "ChatType"] = "Group"
        
    # 3. 应用策略 2 (人数检测) - 这是解决你问题的关键
    print("正在进行群聊智能检测 (基于发言人数)...")
    # 只看对方发的消息
    incoming = df[df["IsSender"] == 0]
    # 统计每个会话有多少个不同的发送者
    sender_counts = incoming.groupby("NickName")["Sender"].nunique()
    # 如果超过1个人说话，标记为群聊
    detected_groups = sender_counts[sender_counts > 1].index.tolist()
    
    # 更新标记
    df.loc[df["NickName"].isin(detected_groups), "ChatType"] = "Group"
    
    # 4. 强制修正一些关键词 (保底)
    keywords = ["群", "Group", "Offer", "指南", "team", "Team", "2025", "25fall"]
    for kw in keywords:
        df.loc[df["NickName"].str.contains(kw, case=False, na=False), "ChatType"] = "Group"

    # 统计
    c_counts = df["ChatType"].value_counts()
    print(f"📊 识别结果: 单聊 {c_counts.get('Private', 0)} 条, 群聊 {c_counts.get('Group', 0)} 条")
    
    return df

# ===================== 5. 全局图表 =====================

def monthly_trend(df):
    set_dark_style()
    data = df.groupby("Month").size().reindex(range(1, 13), fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(data.index, data.values, marker="o", color="#00f2ea", linewidth=2)
    ax.fill_between(data.index, data.values, color="#00f2ea", alpha=0.1)
    ax.set_ylim(bottom=0)
    ax.set_title("Total Monthly Trend", color="white") # 去掉中文/Emoji防止报错
    ax.set_xticks(range(1, 13))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return fig_to_base64(fig)

def generate_global_wordcloud(text):
    text = re.sub(r"[A-Za-z0-9]+", "", text)
    stopwords = {"的","了","我","是","在","也","有","就","不","人","我们","哈哈","哈哈哈","图片","视频","啊","吗","吧","可以","你","他","她","它","这","那","和","与","但","如果","因为","所以","还","要","说","会","都","很","还要","给","上","去","来","就是","那个","然后","觉得","其实","嗯","哦"}
    words = [w for w in jieba.cut(text) if len(w) > 1 and w not in stopwords]
    clean_words = [clean_text_for_plot(w) for w in words]
    if not clean_words: return ""
    
    font_path = "msyh.ttc"
    if platform.system() == "Darwin": font_path = "/System/Library/Fonts/PingFang.ttc"
    
    try:
        wc = WordCloud(font_path=font_path, width=900, height=400, 
                       background_color="black", colormap="cool", max_words=100).generate(" ".join(clean_words))
    except:
        wc = WordCloud(width=900, height=400, background_color="black").generate(" ".join(clean_words))

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor('black')
    ax.imshow(wc)
    ax.axis("off")
    return fig_to_base64(fig)

def generate_global_heatmap(df):
    set_dark_style()
    year_start = pd.Timestamp(f"{TARGET_YEAR}-01-01")
    year_end = pd.Timestamp(f"{TARGET_YEAR}-12-31")
    full_range = pd.date_range(year_start, year_end, freq="D")
    
    daily_counts = df.groupby("Date").size()
    full = pd.DataFrame({"Date": full_range})
    full["count"] = full["Date"].dt.date.map(daily_counts).fillna(0).astype(int)
    full["week"] = (full["Date"] - year_start).dt.days // 7
    full["weekday"] = full["Date"].dt.weekday
    heatmap_data = full.pivot(index="weekday", columns="week", values="count")
    
    fig, ax = plt.subplots(figsize=(16, 3.5))
    vmax = heatmap_data.max().max() or 1
    sns.heatmap(heatmap_data, cmap="mako", vmin=0, vmax=vmax, cbar=False, ax=ax)
    ax.axis('off')
    ax.set_title("2025 Activity Heatmap", color='white', fontsize=14, pad=10) # 英文标题防报错
    return fig_to_base64(fig)

def generate_rank_bar(df, title="Ranking"):
    set_dark_style()
    top_data = df.groupby("NickName").size().sort_values(ascending=False).head(10)
    # 清洗 Label 的 Emoji
    clean_names = [clean_text_for_plot(name) for name in top_data.index]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(top_data)), top_data.values, color="#00ff87")
    ax.invert_yaxis()
    
    ax.set_yticks(range(len(top_data)))
    ax.set_yticklabels(clean_names, fontsize=12, color="white") 
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([]) 

    # 这里的 title 也要清洗 Emoji，或者干脆用英文
    clean_title = clean_text_for_plot(title)
    ax.set_title(clean_title, color="white", fontsize=14, pad=20)
    
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                f'{int(bar.get_width()):,}', 
                va='center', fontsize=10, color="#ccc")
                
    return fig_to_base64(fig)

# ===================== 6. 个人/小组件图表 =====================
def generate_mini_heatmap(sub_df):
    set_dark_style()
    year_start = pd.Timestamp(f"{TARGET_YEAR}-01-01")
    year_end = pd.Timestamp(f"{TARGET_YEAR}-12-31")
    full_range = pd.date_range(year_start, year_end, freq="D")
    daily_counts = sub_df.groupby("Date").size()
    full = pd.DataFrame({"Date": full_range})
    full["count"] = full["Date"].dt.date.map(daily_counts).fillna(0).astype(int)
    full["week"] = (full["Date"] - year_start).dt.days // 7
    full["weekday"] = full["Date"].dt.weekday
    heatmap_data = full.pivot(index="weekday", columns="week", values="count")
    
    fig, ax = plt.subplots(figsize=(12, 2.5))
    vmax = heatmap_data.max().max() or 1
    sns.heatmap(heatmap_data, cmap="mako", vmin=0, vmax=vmax, cbar=False, ax=ax)
    ax.axis('off')
    return fig_to_base64(fig)

def generate_mini_hourly(sub_df):
    set_dark_style()
    hourly = sub_df.groupby(["Hour", "SenderType"]).size().unstack().fillna(0).reindex(range(24), fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 4))
    if "对方" not in hourly.columns: hourly["对方"] = 0
    if "我" not in hourly.columns: hourly["我"] = 0
    
    ax.bar(hourly.index, hourly["对方"], color="#ff0050", alpha=0.9, width=0.8, label="Others")
    ax.bar(hourly.index, hourly["我"], bottom=hourly["对方"], color="#00f2ea", alpha=0.9, width=0.8, label="Me")
    
    ax.set_title("24H Activity", fontsize=12, color="#ccc") # 英文
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["0", "6", "12", "18", "23"], fontsize=10)
    ax.legend(loc='upper right', frameon=False, labelcolor='white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_yaxis().set_visible(False)
    return fig_to_base64(fig)

def generate_sender_rank(sub_df):
    set_dark_style()
    top_senders = sub_df["Sender"].value_counts().head(8)
    clean_names = [clean_text_for_plot(name) for name in top_senders.index]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#ff0050' if idx == 0 else '#444' for idx in range(len(top_senders))]
    if "我" in top_senders.index:
         try:
            my_idx = list(top_senders.index).index("我")
            colors[my_idx] = "#00f2ea"
         except: pass

    bars = ax.barh(range(len(top_senders)), top_senders.values, color=colors)
    ax.invert_yaxis()
    ax.set_title("Top Speakers", fontsize=12, color="#ccc") # 英文
    ax.set_yticks(range(len(top_senders)))
    ax.set_yticklabels(clean_names, fontsize=11, color="white")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([])
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                str(int(bar.get_width())), va='center', fontsize=10, color="#ccc")
    return fig_to_base64(fig)

def generate_mini_wordcloud(text):
    text = re.sub(r"[A-Za-z0-9]+", "", text)
    stopwords = {"的","了","我","是","在","也","有","就","不","人","我们","哈哈","哈哈哈","图片","视频","啊","吗","吧","可以","你","他","她","它","这","那","和","与","但","如果","因为","所以","还","要","说","会","都","很","还要","给","上","去","来","就是","那个","然后","觉得","其实","嗯","哦"}
    words = [w for w in jieba.cut(text) if len(w) > 1 and w not in stopwords]
    clean_words = [clean_text_for_plot(w) for w in words]
    if not clean_words: return ""
    
    font_path = "msyh.ttc"
    if platform.system() == "Darwin": font_path = "/System/Library/Fonts/PingFang.ttc"

    try:
        wc = WordCloud(font_path=font_path, width=800, height=400, 
                       background_color="#1a1a1a", colormap="cool", max_words=60).generate(" ".join(clean_words))
    except:
        wc = WordCloud(width=800, height=400, background_color="#1a1a1a").generate(" ".join(clean_words))
        
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc)
    ax.set_title("Keywords", fontsize=12, color="#ccc", pad=10)
    ax.axis("off")
    return fig_to_base64(fig)

# ===================== 7. 深度分析循环 =====================
def analyze_relationships_deep(df, top_n=10):
    counts = df.groupby("NickName").size().sort_values(ascending=False)
    valid_counts = counts[counts >= MIN_MSG_THRESHOLD]
    top_names = valid_counts.head(top_n).index.tolist()
    
    profiles = []
    for i, name in enumerate(top_names):
        print(f"  分析: {name}")
        sub_df = df[df["NickName"] == name]
        total_msgs = len(sub_df)
        
        profiles.append({
            "rank": i+1,
            "name": name,
            "count": total_msgs,
            "heatmap": generate_mini_heatmap(sub_df),
            "hourly": generate_mini_hourly(sub_df),
            "sender": generate_sender_rank(sub_df),
            "wordcloud": generate_mini_wordcloud(" ".join(sub_df["StrContent"].tolist()))
        })
    return profiles

# ===================== 8. HTML 生成 =====================
def generate_html(metrics, global_charts, private_profiles, group_profiles):
    
    def render_profiles(profiles):
        if not profiles: return "<div style='text-align:center;color:#666'>暂无数据</div>"
        html_str = ""
        for p in profiles:
            html_str += f"""
            <div class="profile-card">
                <div class="profile-header">
                    <div class="rank">#{p['rank']}</div>
                    <div class="info"><h3>{p['name']}</h3></div>
                    <div class="msg-count">{p['count']:,}</div>
                </div>
                <div class="viz-block">
                    <div class="viz-label">Activity Timeline</div>
                    <img class="full-width-img" src="data:image/png;base64,{p['heatmap']}">
                </div>
                <div class="viz-block"><img class="full-width-img" src="data:image/png;base64,{p['hourly']}"></div>
                <div class="viz-block"><img class="full-width-img" src="data:image/png;base64,{p['sender']}"></div>
                <div class="viz-block"><img class="full-width-img" src="data:image/png;base64,{p['wordcloud']}"></div>
            </div>
            """
        return html_str

    html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <title>{TARGET_YEAR} 微信年度报告</title>
    <style>
    body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background-color: #0d0d0d; color: #e0e0e0; max-width: 900px; margin: 0 auto; padding: 40px; }}
    .card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 25px; margin-bottom: 30px; }}
    h1 {{ text-align: center; color: #fff; text-shadow: 0 0 20px rgba(0, 242, 234, 0.5); margin-bottom: 10px; font-size: 2.5em; }}
    .subtitle {{ text-align:center; color:#666; margin-bottom:50px; font-size: 1.1em; }}
    .hero-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; }}
    .hero-box {{ background: linear-gradient(135deg, #1f1f1f 0%, #151515 100%); border: 1px solid #333; border-radius: 12px; padding: 25px; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden; }}
    .hero-label {{ font-size: 0.9em; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
    .hero-value {{ font-size: 2.8em; color: #fff; font-weight: bold; line-height: 1.1; }}
    .hero-sub {{ font-size: 1em; color: #00f2ea; margin-top: 5px; }}
    .highlight {{ color: #ff0050; }}
    .profile-card {{ background: #222; border: 1px solid #333; border-radius: 15px; padding: 30px; margin-bottom: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
    .profile-header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 20px; }}
    .rank {{ font-size: 2em; font-weight: bold; color: #444; width: 60px; }}
    .info h3 {{ margin: 0; font-size: 1.6em; color: #fff; }}
    .msg-count {{ font-size: 1.5em; color: #00ff87; font-family: monospace; }}
    .viz-block {{ margin-bottom: 30px; border: 1px solid #2a2a2a; background: #1a1a1a; border-radius: 8px; padding: 15px; }}
    .viz-label {{ font-size: 0.8em; color: #666; text-transform: uppercase; margin-bottom: 10px; }}
    .full-width-img {{ width: 100%; height: auto; display: block; border-radius: 4px; }}
    img {{ display: block; margin: 0 auto; max-width: 100%; }}
    h2 {{ color: #fff; border-left: 4px solid #ff0050; padding-left: 10px; }}
    .section-divider {{ margin: 60px 0 30px 0; text-align: center; border-bottom: 1px solid #333; line-height: 0.1em; color: #888; font-size: 1.2em; }} 
    .section-divider span {{ background: #0d0d0d; padding: 0 10px; }}
    </style>
    </head>
    <body>
    
    <h1>{TARGET_YEAR} REWIND</h1>
    <p class="subtitle">{metrics['start']} - {metrics['end']} • WeChat Analysis</p>
    
    <div class="hero-grid">
        <div class="hero-box">
            <div class="hero-label">年度消息总数</div>
            <div class="hero-value">{metrics["total"]:,}</div>
            <div class="hero-sub">日均 <span style="color:#fff">{int(metrics["avg_active"])}</span> 条</div>
        </div>
        <div class="hero-box">
            <div class="hero-label">总字数统计</div>
            <div class="hero-value">{metrics["total_chars"]:,}</div>
            <div class="hero-sub"><span style="color:#00f2ea">发 {metrics["sent_chars"]:,}</span> | <span style="color:#ff0050">收 {metrics["received_chars"]:,}</span></div>
        </div>
        <div class="hero-box">
            <div class="hero-label">最疯狂的一天</div>
            <div class="hero-value">{metrics["busiest_date"]}</div>
            <div class="hero-sub"><span class="highlight">{metrics["busiest_count"]:,}</span> 条消息</div>
        </div>
        <div class="hero-box">
            <div class="hero-label">最亲密联系人</div>
            <div class="hero-value" style="font-size: 2.2em;">{metrics["top_contact"]}</div>
            <div class="hero-sub"><span class="highlight">{metrics["top_contact_count"]:,}</span> 条</div>
        </div>
    </div>
    
    <div class="card"><h2>📅 年度活跃热力图</h2><img src="data:image/png;base64,{global_charts['heatmap']}"></div>
    <div class="card"><h2>📈 月度趋势图</h2><img src="data:image/png;base64,{global_charts['monthly']}"></div>
    <div class="card"><h2>☁️ 全年度词云</h2><img src="data:image/png;base64,{global_charts['wordcloud']}"></div>
    
    <h2 class="section-divider"><span>🏆 年度排行榜</span></h2>
    <div class="card"><h2>👤 Top 10 私聊排行榜</h2><img src="data:image/png;base64,{global_charts['private_rank']}"></div>
    <div class="card"><h2>👥 Top 10 群聊排行榜</h2><img src="data:image/png;base64,{global_charts['group_rank']}"></div>
    
    <h2 class="section-divider"><span>👤 私聊深度画像 (Top 10)</span></h2>
    {render_profiles(private_profiles)}
    
    <h2 class="section-divider"><span>👥 群聊深度画像 (Top 10)</span></h2>
    {render_profiles(group_profiles)}
    
    </body>
    </html>
    """
    
    with open(f"WeChat_Report_{TARGET_YEAR}_Final.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 最终版报告已生成：WeChat_Report_{TARGET_YEAR}_Final.html")

# ===================== 主入口 =====================
if __name__ == "__main__":
    df = load_data()
    if not df.empty:
        daily_counts = df.groupby("Date").size()
        max_day = daily_counts.idxmax()
        
        if not df.empty:
            top_contact_name = df["NickName"].mode()[0]
            top_contact_count = len(df[df["NickName"] == top_contact_name])
        else:
            top_contact_name = "N/A"
            top_contact_count = 0

        df["char_len"] = df["StrContent"].astype(str).apply(len)
        metrics = {
            "total": len(df),
            "sent": len(df[df["IsSender"]==1]),
            "received": len(df[df["IsSender"]==0]),
            "avg_active": round(len(df)/df["Date"].nunique(), 1) if df["Date"].nunique() > 0 else 0,
            "start": df["dt"].min().strftime("%Y.%m.%d"),
            "end": df["dt"].max().strftime("%Y.%m.%d"),
            "top_contact": top_contact_name,
            "top_contact_count": top_contact_count,
            "busiest_date": max_day.strftime("%m-%d"),
            "busiest_count": daily_counts.max(),
            "total_chars": df["char_len"].sum(),
            "sent_chars": df[df["IsSender"] == 1]["char_len"].sum(),
            "received_chars": df[df["IsSender"] == 0]["char_len"].sum()
        }
        
        # 分离数据
        df_private = df[df["ChatType"] == "Private"]
        df_group = df[df["ChatType"] == "Group"]
        
        print("🎨 正在生成图表...")
        global_charts = {
            "monthly": monthly_trend(df),
            "wordcloud": generate_global_wordcloud(" ".join(df["StrContent"])),
            "heatmap": generate_global_heatmap(df),
            "private_rank": generate_rank_bar(df_private, "Top 10 Private Chats"), # 英文标题防报错
            "group_rank": generate_rank_bar(df_group, "Top 10 Group Chats")
        }
        
        print(f"🔍 正在分析 Top 10 好友 (池子: {len(df_private)} 条)...")
        private_profiles = analyze_relationships_deep(df_private, top_n=10)
        
        print(f"🔍 正在分析 Top 10 群聊 (池子: {len(df_group)} 条)...")
        group_profiles = analyze_relationships_deep(df_group, top_n=10)
        
        generate_html(metrics, global_charts, private_profiles, group_profiles)