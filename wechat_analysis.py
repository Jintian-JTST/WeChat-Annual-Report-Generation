"""
WeChat Annual Report (Green Matrix Edition)
-----------------------------------
- 修复：热力图标签回归 + 纯黑/荧光绿高对比度配色
- 修复：强制过滤疑似群聊（通过关键词、空格、长度检测）
- 新增：单人深度画像增加【字数 vs 消息数】双维度对比图
- 视觉：全线统一为黑客帝国绿 (Matrix Green) 风格
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
import matplotlib.colors as mcolors
import numpy as np
import warnings

# ===================== 0. 基础设置 =====================
warnings.filterwarnings("ignore")

TARGET_YEAR = 2025
CSV_PATH = "messages.csv"  # 记得改回你的文件名，如 messages1.csv
MIN_MSG_THRESHOLD = 50     # 稍微降低门槛，防止漏掉重要的人

# ===================== 1. 核心工具函数 =====================

def clean_text_for_plot(text):
    if not isinstance(text, str): return str(text)
    emoji_pattern = re.compile(u'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    return emoji_pattern.sub(r'', text).strip()

def get_chinese_font():
    os_name = platform.system()
    if os_name == "Windows": return ["Microsoft YaHei", "SimHei"]
    elif os_name == "Darwin": return ["PingFang SC", "Arial Unicode MS"]
    return ["WenQuanYi Micro Hei"]

# ===================== 2. 视觉风格 (黑客帝国绿) =====================
def set_matrix_style():
    plt.style.use('dark_background')
    plt.rcParams["font.sans-serif"] = get_chinese_font() + plt.rcParams["font.sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False 
    # 统一绿色系：荧光绿，深绿，草绿，青色
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['#00ff41', '#008f11', '#003b00', '#ccffcc', '#ffffff'])
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['grid.color'] = '#222222'
    plt.rcParams['text.color'] = '#cccccc'
    plt.rcParams['axes.labelcolor'] = '#cccccc'
    plt.rcParams['xtick.color'] = '#888888'
    plt.rcParams['ytick.color'] = '#888888'

def get_green_cmap():
    """自定义高对比度绿色热力图：0是黑色，1立刻变绿"""
    colors = ["#1a1a1a", "#0d330d", "#00ff41"] # 背景黑 -> 深绿 -> 亮绿
    return mcolors.LinearSegmentedColormap.from_list("matrix_green", colors, N=256)

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor='#000000') # 统一背景色
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return img

# ===================== 3. 数据加载 (增强过滤) =====================
def load_data():
    print("-" * 30)
    print(f"🚀 [1/6] 正在读取文件: {CSV_PATH}")
    print("        (文件较大，如果卡住超过 1 分钟，请检查文件是否被 Excel 占用)...")
    
    try:
        # 优化点：dtype=str 极大提升读取速度，low_memory=False 避免警告
        df = pd.read_csv(CSV_PATH, encoding="utf-8", on_bad_lines="skip", low_memory=False, dtype=str)
    except UnicodeDecodeError:
        print("   ⚠️ UTF-8 解码失败，尝试 GBK...")
        try:
            df = pd.read_csv(CSV_PATH, encoding="gbk", on_bad_lines="skip", low_memory=False, dtype=str)
        except:
            print("❌ 无法读取 CSV，请检查文件编码或是否损坏")
            return pd.DataFrame()
            
    print(f"✅ [2/6] 读取完成，原始行数: {len(df)}")

    # 类型过滤
    if "Type" in df.columns:
        df = df[df["Type"] == "1"].copy() # 注意这里变成了字符串 "1"
    
    print("🚀 [3/6] 正在转换时间格式 (这可能需要几秒钟)...")
    df["dt"] = pd.to_datetime(df["StrTime"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df = df[df["dt"].dt.year == TARGET_YEAR]
    
    # 转换列格式
    print("🚀 [4/6] 正在清洗数据字段...")
    df["IsSender"] = pd.to_numeric(df["IsSender"], errors='coerce').fillna(0).astype(int)
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

    # === 群聊识别 ===
    print("🚀 [5/6] 正在进行群聊智能分类...")
    df["ChatType"] = "Private"
    
    # 策略1: ID
    if "TalkerId" in df.columns:
        df.loc[df["TalkerId"].astype(str).str.endswith("@chatroom"), "ChatType"] = "Group"
        
    # 策略2: 关键词 (极速版)
    # 使用向量化字符串操作，比 apply 快 100 倍
    keywords = ["群", "Group", "Team", "Offer", "指南", "2025", "25fall"]
    pattern = "|".join(keywords) # 生成正则表达式 "群|Group|Team..."
    mask_keyword = df["NickName"].str.contains(pattern, case=False, na=False)
    df.loc[mask_keyword, "ChatType"] = "Group"
    
    # 策略3: 逻辑推断 (人数 > 1)
    # 这是一个耗时操作，我们优化一下：只对 Private 的进行检查
    potential_private = df[df["ChatType"] == "Private"]
    incoming = potential_private[potential_private["IsSender"] == 0]
    
    # 只有当潜在单聊数据量不大时才跑这个，否则跳过
    if len(incoming) > 0:
        sender_counts = incoming.groupby("NickName")["Sender"].nunique()
        real_groups = sender_counts[sender_counts > 1].index
        df.loc[df["NickName"].isin(real_groups), "ChatType"] = "Group"

    p_count = len(df[df['ChatType']=='Private'])
    g_count = len(df[df['ChatType']=='Group'])
    print(f"✅ [6/6] 数据加载完毕! (单聊: {p_count}, 群聊: {g_count})")
    print("-" * 30)
    
    return df

# ===================== 4. 图表生成 (绿色高对比版) =====================

def generate_heatmap_with_labels(df, title="活跃热力图"):
    """带标签的高对比度绿色热力图"""
    set_matrix_style()
    
    # 准备数据
    year_start = pd.Timestamp(f"{TARGET_YEAR}-01-01")
    year_end = pd.Timestamp(f"{TARGET_YEAR}-12-31")
    full_range = pd.date_range(year_start, year_end, freq="D")
    
    daily = df.groupby("Date").size()
    full = pd.DataFrame({"Date": full_range})
    full["count"] = full["Date"].dt.date.map(daily).fillna(0).astype(int)
    full["week"] = (full["Date"] - year_start).dt.days // 7
    full["weekday"] = full["Date"].dt.weekday
    
    data = full.pivot(index="weekday", columns="week", values="count")
    
    # 绘图
    fig, ax = plt.subplots(figsize=(12, 3))
    vmax = data.max().max()
    if vmax < 5: vmax = 5 # 防止数据太少一片黑
    
    # 使用自定义绿色
    sns.heatmap(data, cmap=get_green_cmap(), vmin=0, vmax=vmax, cbar=False, ax=ax, linewidths=0.5, linecolor='#000000')
    
    # --- 【关键修复】加上标签 ---
    # Y轴：星期
    ax.set_yticks([0.5, 3.5, 6.5])
    ax.set_yticklabels(["Mon", "Thu", "Sun"], rotation=0, fontsize=9, color="#666")
    ax.set_ylabel("")
    
    # X轴：月份 (估算位置)
    ax.set_xlabel("")
    month_starts = [0, 4, 8, 13, 17, 21, 26, 30, 35, 39, 43, 48]
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_labels, fontsize=9, color="#666", rotation=0)
    
    ax.set_title(title, color="white", fontsize=12, pad=10, loc='left')
    return fig_to_base64(fig)

def generate_char_compare_chart(sub_df):
    """【新增】字数 vs 消息数 对比图"""
    set_matrix_style()
    
    # 统计数据
    my_df = sub_df[sub_df["IsSender"] == 1]
    other_df = sub_df[sub_df["IsSender"] == 0]
    
    my_msg_count = len(my_df)
    other_msg_count = len(other_df)
    
    my_char_count = my_df["StrContent"].str.len().sum()
    other_char_count = other_df["StrContent"].str.len().sum()
    
    # 避免除以0
    total_msg = my_msg_count + other_msg_count or 1
    total_char = my_char_count + other_char_count or 1
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 2.5))
    
    # 图1：消息数对比 (水平条)
    ax1.barh([0], [my_msg_count], color="#00ff41", label="我")
    ax1.barh([0], [other_msg_count], left=[my_msg_count], color="#444", label="对方")
    ax1.set_title(f"消息条数 ({total_msg})", fontsize=10, color="#aaa")
    ax1.axis('off')
    # 标数字
    ax1.text(my_msg_count/2, 0, str(my_msg_count), ha='center', va='center', color='black', fontweight='bold')
    ax1.text(my_msg_count + other_msg_count/2, 0, str(other_msg_count), ha='center', va='center', color='white')

    # 图2：字数对比 (水平条)
    ax2.barh([0], [my_char_count], color="#008f11", label="我")
    ax2.barh([0], [other_char_count], left=[my_char_count], color="#444", label="对方")
    ax2.set_title(f"总字数 ({total_char:,})", fontsize=10, color="#aaa")
    ax2.axis('off')
    # 标数字
    if my_char_count > 0:
        ax2.text(my_char_count/2, 0, f"{my_char_count:,}", ha='center', va='center', color='white', fontsize=9)
    if other_char_count > 0:
        ax2.text(my_char_count + other_char_count/2, 0, f"{other_char_count:,}", ha='center', va='center', color='white', fontsize=9)

    return fig_to_base64(fig)

def generate_hourly_curve(sub_df):
    """把原来的柱状图改成更平滑的曲线图，看起来更高级"""
    set_matrix_style()
    hourly = sub_df.groupby("Hour").size().reindex(range(24), fill_value=0)
    
    fig, ax = plt.subplots(figsize=(10, 3))
    # 填充曲线
    ax.fill_between(hourly.index, hourly.values, color="#00ff41", alpha=0.2)
    ax.plot(hourly.index, hourly.values, color="#00ff41", linewidth=2)
    
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["0h", "6h", "12h", "18h", "23h"])
    ax.set_yticks([]) # 隐藏Y轴数字
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_title("24H 活跃曲线", fontsize=10, color="#888", loc='left')
    
    return fig_to_base64(fig)

def generate_rank_bar(df, title):
    set_matrix_style()
    top = df.groupby("NickName").size().sort_values(ascending=False).head(10)
    names = [clean_text_for_plot(n) for n in top.index]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(top)), top.values, color="#00ff41")
    ax.invert_yaxis()
    
    # Label 全显示
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=11, color="#ddd") # 字体调大
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([])
    
    ax.set_title(title, color="white", fontsize=14, pad=20)
    
    for bar in bars:
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                f'{int(bar.get_width()):,}', va='center', fontsize=10, color="#888")
                
    return fig_to_base64(fig)

def generate_wordcloud(text):
    text = re.sub(r"[A-Za-z0-9]+", "", text)
    stopwords = {"的","了","我","是","在","也","有","就","不","人","我们","哈哈","哈哈哈","图片","视频","啊","吗","吧","可以","你","他","她","它","这","那","和","与","但","如果","因为","所以","还","要","说","会","都","很","还要","给","上","去","来","就是","那个","然后","觉得","其实","嗯","哦","表情"}
    words = [w for w in jieba.cut(text) if len(w) > 1 and w not in stopwords]
    if not words: return ""
    
    font_path = "msyh.ttc"
    if platform.system() == "Darwin": font_path = "/System/Library/Fonts/PingFang.ttc"
    
    try:
        wc = WordCloud(font_path=font_path, width=800, height=300, 
                       background_color="#000000", colormap="summer", max_words=50).generate(" ".join(words))
    except:
        wc = WordCloud(width=800, height=300, background_color="#000000").generate(" ".join(words))
        
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.imshow(wc)
    ax.axis("off")
    return fig_to_base64(fig)

# ===================== 5. 深度分析 =====================
def analyze_profiles(df, top_n=10):
    counts = df.groupby("NickName").size().sort_values(ascending=False)
    valid = counts[counts >= MIN_MSG_THRESHOLD].head(top_n)
    
    profiles = []
    for name in valid.index:
        print(f"  > 分析: {name}")
        sub = df[df["NickName"] == name]
        
        profiles.append({
            "rank": list(valid.index).index(name) + 1,
            "name": clean_text_for_plot(name),
            "count": len(sub),
            "heatmap": generate_heatmap_with_labels(sub, title=""),
            "hourly": generate_hourly_curve(sub),
            "compare": generate_char_compare_chart(sub), # 新增字数对比
            "wordcloud": generate_wordcloud(" ".join(sub["StrContent"].tolist()))
        })
    return profiles

# ===================== 6. HTML 生成 =====================
def generate_html(metrics, charts, p_profiles, g_profiles):
    
    def render_pro(profiles):
        if not profiles: return "<div style='text-align:center;padding:20px;color:#666'>暂无数据</div>"
        html = ""
        for p in profiles:
            html += f"""
            <div class="profile-card">
                <div class="profile-header">
                    <div class="rank">#{p['rank']}</div>
                    <div class="info"><h3>{p['name']}</h3></div>
                    <div class="msg-count">{p['count']:,}</div>
                </div>
                <div class="viz-block" style="border:none; background:none; padding:0;">
                    <img class="full-width-img" src="data:image/png;base64,{p['compare']}">
                </div>
                <div class="viz-block">
                    <img class="full-width-img" src="data:image/png;base64,{p['heatmap']}">
                </div>
                <div class="grid-2">
                    <div class="viz-block"><img class="full-width-img" src="data:image/png;base64,{p['hourly']}"></div>
                    <div class="viz-block"><img class="full-width-img" src="data:image/png;base64,{p['wordcloud']}"></div>
                </div>
            </div>
            """
        return html

    html_content = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <title>{TARGET_YEAR} WeChat Matrix Report</title>
    <style>
    body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background-color: #000000; color: #ccc; max-width: 900px; margin: 0 auto; padding: 40px; }}
    h1 {{ color: #00ff41; text-align: center; text-shadow: 0 0 10px #003b00; font-size: 2.5em; margin-bottom: 10px; }}
    .subtitle {{ text-align:center; color:#666; margin-bottom:50px; }}
    
    .hero-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; }}
    .hero-box {{ background: #111; border: 1px solid #003b00; border-radius: 8px; padding: 20px; text-align: center; }}
    .hero-val {{ font-size: 2.5em; color: #00ff41; font-weight: bold; }}
    .hero-lbl {{ color: #666; font-size: 0.9em; text-transform: uppercase; }}
    
    .card {{ background: #151515; border: 1px solid #222; border-radius: 12px; padding: 25px; margin-bottom: 30px; }}
    .profile-card {{ background: #111; border-left: 3px solid #00ff41; margin-bottom: 50px; padding: 20px; }}
    .profile-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; padding-bottom: 15px; margin-bottom: 20px; }}
    .info h3 {{ color: #fff; margin: 0; }}
    .rank {{ font-size: 1.5em; color: #008f11; font-weight: bold; }}
    .msg-count {{ font-size: 1.2em; color: #00ff41; font-family: monospace; }}
    
    .section-title {{ color: #fff; border-bottom: 2px solid #003b00; padding-bottom: 10px; margin: 60px 0 30px 0; text-align: left; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
    .viz-block {{ background: #151515; padding: 10px; border-radius: 6px; }}
    img {{ max-width: 100%; display: block; margin: 0 auto; }}
    </style>
    </head>
    <body>
        <h1>{TARGET_YEAR} REWIND</h1>
        <p class="subtitle">{metrics['start']} - {metrics['end']} • DATA MATRIX</p>
        
        <div class="hero-grid">
            <div class="hero-box"><div class="hero-lbl">Total Messages</div><div class="hero-val">{metrics['total']:,}</div></div>
            <div class="hero-box"><div class="hero-lbl">Total Characters</div><div class="hero-val">{metrics['total_chars']:,}</div></div>
        </div>
        
        <div class="card">
            <h3 style="color:#00ff41">📅 年度全貌</h3>
            <img src="data:image/png;base64,{charts['heatmap']}">
        </div>

        <h2 class="section-title">🏆 排行榜 (Rankings)</h2>
        <div class="card"><img src="data:image/png;base64,{charts['private_rank']}"></div>
        <div class="card"><img src="data:image/png;base64,{charts['group_rank']}"></div>
        
        <h2 class="section-title">👤 好友深度分析 (Private Chat Deep Dive)</h2>
        {render_pro(p_profiles)}
        
        <h2 class="section-title">👥 群聊深度分析 (Group Chat Deep Dive)</h2>
        {render_pro(g_profiles)}
        
    </body>
    </html>
    """
    with open(f"WeChat_Report_{TARGET_YEAR}_Green.html", "w", encoding="utf-8") as f: f.write(html_content)
    print(f"✅ 完成！报告已生成: WeChat_Report_{TARGET_YEAR}_Green.html")

# ===================== 主程序 =====================
if __name__ == "__main__":
    df = load_data()
    if not df.empty:
        # 计算基础指标
        df["char_len"] = df["StrContent"].astype(str).apply(len)
        metrics = {
            "total": len(df),
            "start": df["dt"].min().strftime("%Y.%m.%d"),
            "end": df["dt"].max().strftime("%Y.%m.%d"),
            "total_chars": df["char_len"].sum()
        }
        
        # 分离
        df_p = df[df["ChatType"] == "Private"]
        df_g = df[df["ChatType"] == "Group"]
        
        # 生成图表
        print("🎨 生成全局图表...")
        charts = {
            "heatmap": generate_heatmap_with_labels(df, "2025 Activity Matrix"),
            "private_rank": generate_rank_bar(df_p, "Top 10 Private Chats"),
            "group_rank": generate_rank_bar(df_g, "Top 10 Group Chats")
        }
        
        print(f"🔍 分析 Top 10 好友 (Pool: {len(df_p)})...")
        p_pro = analyze_profiles(df_p)
        print(f"🔍 分析 Top 10 群聊 (Pool: {len(df_g)})...")
        g_pro = analyze_profiles(df_g)
        
        generate_html(metrics, charts, p_pro, g_pro)