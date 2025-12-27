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

warnings.filterwarnings("ignore")

# ===================== 🎨 你的调色盘 (在这里改颜色) =====================
CONFIG = {
    # 1. 基础配置
    "TARGET_YEAR": 2025,
    "CSV_PATH": "messages.csv",
    
    # 2. 图表配色 (Hex颜色码)
    "BG_COLOR": "#1a1a1a",       # 图表背景色 (深灰)
    "TEXT_COLOR": "#ffffff",     # 文字颜色
    "AXIS_COLOR": "#888888",     # 坐标轴颜色
    
    # 3. 核心主题色
    "MAIN_COLOR": "#00f2ea",     # 主色 (通常代表'我'，或者趋势线)
    "ACCENT_COLOR": "#ff0050",   # 强调色 (通常代表'对方')
    
    # 4. 热力图渐变 (从 无数据 -> 少量 -> 大量)
    "HEATMAP_GRADIENT": ["#000000", "#164d16", "#00ff00"], # 黑 -> 深绿 -> 亮绿
    
    # 5. 词云配色方案 (可选: 'viridis', 'plasma', 'inferno', 'magma', 'cividis', 'cool', 'spring')
    "WORDCLOUD_COLORMAP": "summer" 
}

# ===================== 核心逻辑 =====================

def set_style():
    """应用你的配色配置"""
    plt.style.use('dark_background')
    
    # 字体设置
    os_name = platform.system()
    font = ["WenQuanYi Micro Hei"]
    if os_name == "Windows": font = ["Microsoft YaHei", "SimHei"]
    elif os_name == "Darwin": font = ["PingFang SC", "Arial Unicode MS"]
    plt.rcParams["font.sans-serif"] = font + plt.rcParams["font.sans-serif"]
    
    # 应用颜色
    plt.rcParams['figure.facecolor'] = CONFIG["BG_COLOR"]
    plt.rcParams['axes.facecolor'] = CONFIG["BG_COLOR"]
    plt.rcParams['text.color'] = CONFIG["TEXT_COLOR"]
    plt.rcParams['axes.labelcolor'] = CONFIG["AXIS_COLOR"]
    plt.rcParams['xtick.color'] = CONFIG["AXIS_COLOR"]
    plt.rcParams['ytick.color'] = CONFIG["AXIS_COLOR"]
    plt.rcParams['axes.edgecolor'] = "#333333"
    plt.rcParams['grid.color'] = "#222222"
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
    print(f"🚀 [1/4] 正在读取 {CONFIG['CSV_PATH']} (请确保未被Excel占用)...")
    try:
        df = pd.read_csv(CONFIG['CSV_PATH'], encoding="utf-8", on_bad_lines="skip", low_memory=False, dtype=str)
    except:
        df = pd.read_csv(CONFIG['CSV_PATH'], encoding="gbk", on_bad_lines="skip", low_memory=False, dtype=str)
    
    if "Type" in df.columns: df = df[df["Type"] == "1"].copy()
    
    df["dt"] = pd.to_datetime(df["StrTime"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df = df[df["dt"].dt.year == CONFIG["TARGET_YEAR"]]
    
    # 转换字段
    df["IsSender"] = pd.to_numeric(df["IsSender"], errors='coerce').fillna(0).astype(int)
    df["Date"] = df["dt"].dt.date
    df["Month"] = df["dt"].dt.month
    df["Hour"] = df["dt"].dt.hour
    df["SenderType"] = df["IsSender"].map({1: "Me", 0: "Other"})
    df["StrContent"] = df["StrContent"].fillna("")
    df["NickName"] = df["NickName"].fillna("Unknown").str.strip()
    
    # === 🕵️‍♂️ 群聊识别逻辑修正 ===
    print("🚀 [2/4] 正在识别群聊...")
    df["ChatType"] = "Private"
    
    # 1. 强制匹配 @chatroom (包含你说的 '数字+@chatroom')
    # 检查 TalkerId (标准字段)
    if "TalkerId" in df.columns:
        df.loc[df["TalkerId"].str.contains(r"@chatroom", na=False), "ChatType"] = "Group"
        
    # 2. 有些时候 ID 会错位跑到 NickName 或者是 StrTalker 里，我们也检查一下
    if "StrTalker" in df.columns:
        df.loc[df["StrTalker"].str.contains(r"@chatroom", na=False), "ChatType"] = "Group"
    
    # 3. 关键词补漏
    keywords = ["群", "Group", "Team", "2025", "25fall"]
    pattern = "|".join(keywords)
    df.loc[df["NickName"].str.contains(pattern, case=False, na=False), "ChatType"] = "Group"

    # 4. 逻辑补漏 (单聊里出现多人说话)
    private_df = df[df["ChatType"] == "Private"]
    sender_counts = private_df[private_df["IsSender"]==0].groupby("NickName")["Sender"].nunique()
    real_groups = sender_counts[sender_counts > 1].index
    df.loc[df["NickName"].isin(real_groups), "ChatType"] = "Group"
    
    print(f"✅ 识别结果: 单聊 {len(df[df['ChatType']=='Private'])} | 群聊 {len(df[df['ChatType']=='Group'])}")
    return df

# ===================== 画图函数 (使用配置色) =====================

def draw_heatmap(df):
    set_style()
    dates = df.groupby("Date").size()
    full_range = pd.date_range(f"{CONFIG['TARGET_YEAR']}-01-01", f"{CONFIG['TARGET_YEAR']}-12-31")
    
    # 构建数据矩阵
    chart_data = pd.DataFrame({"Date": full_range})
    chart_data["count"] = chart_data["Date"].map(dates).fillna(0).astype(int)
    chart_data["week"] = chart_data["Date"].dt.isocalendar().week
    chart_data["weekday"] = chart_data["Date"].dt.weekday
    pivot = chart_data.pivot(index="weekday", columns="week", values="count")
    
    fig, ax = plt.subplots(figsize=(12, 2.5))
    # 自定义渐变色
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", CONFIG["HEATMAP_GRADIENT"], N=256)
    sns.heatmap(pivot, cmap=cmap, cbar=False, ax=ax, linewidths=0.5, linecolor=CONFIG["BG_COLOR"])
    
    # 标签
    ax.set_yticks([0.5, 3.5, 6.5])
    ax.set_yticklabels(["Mon", "Thu", "Sun"], rotation=0, fontsize=9)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_xticks([]) # 简化X轴
    
    return fig_to_base64(fig)

def draw_bars(df, title):
    set_style()
    top = df.groupby("NickName").size().sort_values(ascending=False).head(10)
    names = [clean_text(n) for n in top.index]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(top)), top.values, color=CONFIG["MAIN_COLOR"])
    ax.invert_yaxis()
    
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=11)
    
    # 去边框
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)
    ax.set_xticks([])
    
    # 标数字
    for bar in bars:
        ax.text(bar.get_width()+2, bar.get_y()+bar.get_height()/2, 
                f"{int(bar.get_width()):,}", va='center', fontsize=10, color=CONFIG["AXIS_COLOR"])
        
    ax.set_title(title, pad=10)
    return fig_to_base64(fig)

def draw_compare(df):
    """字数 vs 消息数 对比"""
    set_style()
    me = df[df["IsSender"]==1]
    other = df[df["IsSender"]==0]
    
    m_count = len(me)
    o_count = len(other)
    m_chars = me["StrContent"].str.len().sum()
    o_chars = other["StrContent"].str.len().sum()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 2))
    
    # 1. 消息数
    ax1.barh([0], [m_count], color=CONFIG["MAIN_COLOR"], label="Me")
    ax1.barh([0], [o_count], left=[m_count], color=CONFIG["ACCENT_COLOR"], label="Ta")
    ax1.text(m_count/2, 0, str(m_count), ha='center', va='center', color='black', fontweight='bold')
    ax1.text(m_count+o_count/2, 0, str(o_count), ha='center', va='center', color='white', fontweight='bold')
    ax1.set_title("Messages", fontsize=10, color=CONFIG["AXIS_COLOR"])
    ax1.axis('off')
    
    # 2. 字数
    ax2.barh([0], [m_chars], color=CONFIG["MAIN_COLOR"])
    ax2.barh([0], [o_chars], left=[m_chars], color=CONFIG["ACCENT_COLOR"])
    ax2.set_title(f"Characters (Total: {m_chars+o_chars:,})", fontsize=10, color=CONFIG["AXIS_COLOR"])
    ax2.axis('off')
    
    return fig_to_base64(fig)

# ===================== 执行流 =====================

if __name__ == "__main__":
    df = load_data()
    
    if not df.empty:
        print("🚀 [3/4] 正在计算统计数据 & 绘制图表...")
        
        # 1. 基础指标
        total_chars = df["StrContent"].str.len().sum()
        metrics = {
            "total": len(df),
            "start": df["dt"].min().strftime("%Y.%m.%d"),
            "end": df["dt"].max().strftime("%Y.%m.%d"),
            "chars": int(total_chars)
        }
        
        # 2. 生成图表数据包
        data_package = {
            "metrics": metrics,
            "charts": {},
            "profiles": [] # 只存 Top 10 私聊
        }
        
        # 全局图
        df_p = df[df["ChatType"] == "Private"]
        df_g = df[df["ChatType"] == "Group"]
        
        data_package["charts"]["heatmap"] = draw_heatmap(df)
        data_package["charts"]["rank_p"] = draw_bars(df_p, "Top 10 Friends")
        data_package["charts"]["rank_g"] = draw_bars(df_g, "Top 10 Groups")
        
        # 深度画像 (Top 10 私聊)
        top_ppl = df_p.groupby("NickName").size().sort_values(ascending=False).head(10).index
        
        for rank, name in enumerate(top_ppl, 1):
            sub = df[df["NickName"] == name]
            profile = {
                "rank": rank,
                "name": clean_text(name),
                "count": len(sub),
                "heatmap": draw_heatmap(sub),
                "compare": draw_compare(sub)
                # 你可以在这里加更多图表
            }
            data_package["profiles"].append(profile)
            
        # 3. 保存到文件
        print("🚀 [4/4] 正在保存数据到 report_data.json ...")
        with open("report_data.json", "w", encoding="utf-8") as f:
            json.dump(data_package, f)
            
        print("\n✅ 完成！请运行 'step2_render.py' 来生成网页。")
        print("💡 提示：如果觉得颜色丑，修改 step1 代码顶部的 CONFIG 字典，然后重跑这个脚本即可。")