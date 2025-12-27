import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import jieba
import re
from wordcloud import WordCloud
from io import BytesIO
import base64
import platform
import warnings
import json
import matplotlib.colors as mcolors
import numpy as np

warnings.filterwarnings("ignore")

# ===================== 🎨 调色盘配置 =====================
CONFIG = {
    "TARGET_YEAR": 2025,
    "CSV_PATH": "messages.csv", # 确保文件名对
    "BG_COLOR": "#1a1a1a",
    "TEXT_COLOR": "#ffffff",
    "AXIS_COLOR": "#888888",
    "MAIN_COLOR": "#00f2ea",     # 我 (青色)
    "ACCENT_COLOR": "#ff0050",   # 对方 (洋红)
    "HEATMAP_GRADIENT": ["#111111", "#0d330d", "#00ff41"], # 黑->深绿->荧光绿
}

# ===================== 基础函数 =====================

def set_style():
    plt.style.use('dark_background')
    os_name = platform.system()
    font = ["WenQuanYi Micro Hei"]
    if os_name == "Windows": font = ["Microsoft YaHei", "SimHei"]
    elif os_name == "Darwin": font = ["PingFang SC", "Arial Unicode MS"]
    plt.rcParams["font.sans-serif"] = font + plt.rcParams["font.sans-serif"]
    plt.rcParams['figure.facecolor'] = CONFIG["BG_COLOR"]
    plt.rcParams['axes.facecolor'] = CONFIG["BG_COLOR"]
    plt.rcParams['text.color'] = CONFIG["TEXT_COLOR"]
    plt.rcParams['axes.labelcolor'] = CONFIG["AXIS_COLOR"]
    plt.rcParams["axes.unicode_minus"] = False 

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return re.sub(r'[\U00010000-\U0010ffff]', '', text).strip()

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=CONFIG["BG_COLOR"])
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return img

def load_data():
    print(f"🚀 [1/5] 读取数据: {CONFIG['CSV_PATH']} ...")
    try:
        df = pd.read_csv(CONFIG['CSV_PATH'], encoding="utf-8", on_bad_lines="skip", low_memory=False, dtype=str)
    except:
        df = pd.read_csv(CONFIG['CSV_PATH'], encoding="gbk", on_bad_lines="skip", low_memory=False, dtype=str)
    
    if "Type" in df.columns: df = df[df["Type"] == "1"].copy()
    
    df["dt"] = pd.to_datetime(df["StrTime"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df = df[df["dt"].dt.year == CONFIG["TARGET_YEAR"]]
    
    # 转换
    df["IsSender"] = pd.to_numeric(df["IsSender"], errors='coerce').fillna(0).astype(int)
    df["Date"] = df["dt"].dt.date
    df["Hour"] = df["dt"].dt.hour
    df["StrContent"] = df["StrContent"].fillna("")
    df["NickName"] = df["NickName"].fillna("Unknown").str.strip()

    # === 🕵️‍♂️ 强力群聊识别 (修复 Chatroom 问题) ===
    print("🚀 [2/5] 正在分类 (单聊 vs 群聊)...")
    df["ChatType"] = "Private"
    
    # 1. ID 结尾检测 (最准) - 只要是 @chatroom 结尾，必须是群
    if "TalkerId" in df.columns:
        df.loc[df["TalkerId"].str.endswith("@chatroom"), "ChatType"] = "Group"
        
    # 2. 关键词检测
    keywords = ["群", "Group", "Team", "Offer", "指南"]
    pattern = "|".join(keywords)
    df.loc[df["NickName"].str.contains(pattern, case=False, na=False), "ChatType"] = "Group"
    
    # 3. 逻辑检测 (单聊里如果不止一个人说话，那是群)
    # 先只看目前的 Private
    pot_private = df[df["ChatType"] == "Private"]
    incoming = pot_private[pot_private["IsSender"] == 0]
    if not incoming.empty:
        sender_counts = incoming.groupby("NickName")["Sender"].nunique() if "Sender" in df.columns else incoming.groupby("NickName")["StrTalker"].nunique()
        # 这里简化处理：如果在所谓的单聊里，对方ID变来变去，大概率是群
        # 由于数据源可能没有 Sender 列，我们依赖 TalkerId 判定即可，上面的 @chatroom 其实已经覆盖了99%
        pass 

    print(f"✅ 单聊: {len(df[df['ChatType']=='Private'])} | 群聊: {len(df[df['ChatType']=='Group'])}")
    return df

# ===================== 绘图全家桶 =====================

def draw_heatmap(df, label="Activity"):
    set_style()
    dates = df.groupby("Date").size()
    start_str = f"{CONFIG['TARGET_YEAR']}-01-01"
    end_str = f"{CONFIG['TARGET_YEAR']}-12-31"
    full_range = pd.date_range(start_str, end_str)
    
    chart_data = pd.DataFrame({"Timestamp": full_range})
    chart_data["count"] = chart_data["Timestamp"].dt.date.map(dates).fillna(0).astype(int)
    # 修复跨年周问题
    chart_data["week"] = (chart_data["Timestamp"] - pd.Timestamp(start_str)).dt.days // 7
    chart_data["weekday"] = chart_data["Timestamp"].dt.weekday
    
    pivot = chart_data.pivot(index="weekday", columns="week", values="count")
    
    fig, ax = plt.subplots(figsize=(12, 2.5))
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", CONFIG["HEATMAP_GRADIENT"], N=256)
    vmax = pivot.max().max()
    if vmax < 5: vmax = 5
    
    sns.heatmap(pivot, cmap=cmap, vmin=0, vmax=vmax, cbar=False, ax=ax, linewidths=0.5, linecolor=CONFIG["BG_COLOR"])
    
    ax.set_yticks([0.5, 3.5, 6.5])
    ax.set_yticklabels(["Mon", "Thu", "Sun"], rotation=0, fontsize=9)
    ax.set_xticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    # Label 在右上角
    ax.set_title(label, loc='right', fontsize=10, color=CONFIG["AXIS_COLOR"], pad=10)
    
    return fig_to_base64(fig)

def draw_compare_detailed(df):
    """详细对比图：带数字，带 Who is Who"""
    set_style()
    me = df[df["IsSender"]==1]
    other = df[df["IsSender"]==0]
    
    m_count = len(me)
    o_count = len(other)
    m_chars = me["StrContent"].str.len().sum()
    o_chars = other["StrContent"].str.len().sum()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 2.5))
    
    # --- 图1: 消息数 ---
    ax1.barh([0], [m_count], color=CONFIG["MAIN_COLOR"], height=0.6)
    ax1.barh([0], [o_count], left=[m_count], color=CONFIG["ACCENT_COLOR"], height=0.6)
    # 标注数字
    ax1.text(m_count/2, 0, f"{m_count}", ha='center', va='center', color='black', fontweight='bold')
    ax1.text(m_count+o_count/2, 0, f"{o_count}", ha='center', va='center', color='white', fontweight='bold')
    # 标注身份 (上方)
    ax1.text(0, 0.6, "Me", color=CONFIG["MAIN_COLOR"], fontsize=10, fontweight='bold')
    ax1.text(m_count+o_count, 0.6, "Ta", color=CONFIG["ACCENT_COLOR"], fontsize=10, fontweight='bold', ha='right')
    
    ax1.set_title("Msg Count", loc='right', fontsize=10, color="#666")
    ax1.axis('off')
    
    # --- 图2: 字数 (修复：加上数字) ---
    ax2.barh([0], [m_chars], color=CONFIG["MAIN_COLOR"], alpha=0.8, height=0.6)
    ax2.barh([0], [o_chars], left=[m_chars], color=CONFIG["ACCENT_COLOR"], alpha=0.8, height=0.6)
    # 标注数字 (防止重叠，如果数字太小就不标)
    if m_chars > 0:
        ax2.text(m_chars/2, 0, f"{m_chars}", ha='center', va='center', color='black', fontsize=9)
    if o_chars > 0:
        ax2.text(m_chars+o_chars/2, 0, f"{o_chars}", ha='center', va='center', color='white', fontsize=9)
        
    ax2.set_title("Char Count", loc='right', fontsize=10, color="#666")
    ax2.axis('off')
    
    return fig_to_base64(fig)

def draw_hourly_curve(df):
    """24小时活跃曲线 (回归)"""
    set_style()
    hourly = df.groupby("Hour").size().reindex(range(24), fill_value=0)
    
    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.plot(hourly.index, hourly.values, color=CONFIG["MAIN_COLOR"], linewidth=2)
    ax.fill_between(hourly.index, hourly.values, color=CONFIG["MAIN_COLOR"], alpha=0.2)
    
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["0h", "6h", "12h", "18h", "23h"])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_yticks([])
    ax.set_title("24H Trend", loc='right', fontsize=10, color="#666")
    
    return fig_to_base64(fig)

def draw_wordcloud(df):
    """词云 (回归)"""
    text = " ".join(df["StrContent"].tolist())
    # 简单清洗
    text = re.sub(r"[A-Za-z0-9\[\]]", "", text) 
    words = [w for w in jieba.cut(text) if len(w) > 1]
    if not words: return None # 无词可画
    
    # 字体
    font_path = "msyh.ttc"
    if platform.system() == "Darwin": font_path = "/System/Library/Fonts/PingFang.ttc"
    
    try:
        wc = WordCloud(font_path=font_path, width=800, height=300, 
                       background_color=CONFIG["BG_COLOR"], colormap="summer", max_words=40).generate(" ".join(words))
    except:
        return None
        
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    ax.set_title("Keywords", loc='right', fontsize=10, color="#666")
    return fig_to_base64(fig)

def draw_rank_bar(df, title):
    set_style()
    top = df.groupby("NickName").size().sort_values(ascending=False).head(10)
    names = [clean_text(n)[:12] for n in top.index] # 名字太长截断
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(top)), top.values, color=CONFIG["MAIN_COLOR"])
    ax.invert_yaxis()
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([])
    
    for bar in bars:
        ax.text(bar.get_width()+5, bar.get_y()+bar.get_height()/2, 
                f"{int(bar.get_width()):,}", va='center', fontsize=10, color="#888")
                
    ax.set_title(title, loc='right', pad=10, color="white", fontsize=12)
    return fig_to_base64(fig)

# ===================== 主逻辑 =====================

def analyze_subset(subset_df, limit=10):
    """通用的分析循环，用于 Private 和 Group"""
    top_names = subset_df.groupby("NickName").size().sort_values(ascending=False).head(limit).index
    results = []
    
    for rank, name in enumerate(top_names, 1):
        sub = subset_df[subset_df["NickName"] == name]
        print(f"    Processing #{rank}: {name} ({len(sub)} msgs)...")
        
        item = {
            "rank": rank,
            "name": clean_text(name),
            "count": len(sub),
            "heatmap": draw_heatmap(sub, "Activity Map"),
            "compare": draw_compare_detailed(sub),
            "hourly": draw_hourly_curve(sub),
            "wordcloud": draw_wordcloud(sub) # 可能为 None
        }
        results.append(item)
    return results

if __name__ == "__main__":
    df = load_data()
    
    if not df.empty:
        print("🚀 [3/5] 计算全局统计...")
        metrics = {
            "total": len(df),
            "start": df["dt"].min().strftime("%Y.%m.%d"),
            "end": df["dt"].max().strftime("%Y.%m.%d"),
            "chars": int(df["StrContent"].str.len().sum())
        }
        
        df_p = df[df["ChatType"] == "Private"]
        df_g = df[df["ChatType"] == "Group"]
        
        charts = {
            "heatmap": draw_heatmap(df, "Annual Activity"),
            "rank_p": draw_rank_bar(df_p, "Top 10 Friends"),
            "rank_g": draw_rank_bar(df_g, "Top 10 Groups")
        }
        
        print("🚀 [4/5] 生成【单聊】深度画像...")
        p_profiles = analyze_subset(df_p, 10)
        
        print("🚀 [5/5] 生成【群聊】深度画像...")
        g_profiles = analyze_subset(df_g, 10)
        
        data_package = {
            "metrics": metrics,
            "charts": charts,
            "private_profiles": p_profiles,
            "group_profiles": g_profiles
        }
        
        print("💾 保存数据到 report_data.json ...")
        with open("report_data.json", "w", encoding="utf-8") as f:
            json.dump(data_package, f)
            
        print("\n✅ 数据分析完成！请运行 step2_render.py 生成网页。")