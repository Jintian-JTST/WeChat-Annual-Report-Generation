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

# ===================== 🎨 调色盘 =====================
CONFIG = {
    "TARGET_YEAR": 2025,
    "CSV_PATH": "messages.csv",
    "BG_COLOR": "#1a1a1a",
    "TEXT_COLOR": "#ffffff",
    "AXIS_COLOR": "#888888",
    "MAIN_COLOR": "#00aba5",     # 我 (青色)
    "ACCENT_COLOR": "#ff0050",   # 对方 (洋红)
    "HEATMAP_GRADIENT": ["#111111", "#0d330d", "#00ff41"], 
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

# ===================== 核心：绘图函数 =====================

def draw_donut_pair(df):
    """画两个并排的环形图：左边Msg，右边Char"""
    set_style()
    
    # 数据准备
    me = df[df["IsSender"]==1]
    other = df[df["IsSender"]==0]
    
    m_count = len(me)
    o_count = len(other)
    m_chars = me["StrContent"].str.len().sum()
    o_chars = other["StrContent"].str.len().sum()
    
    # 避免全0报错
    if m_count + o_count == 0: m_count = 1
    if m_chars + o_chars == 0: m_chars = 1
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    colors = [CONFIG["MAIN_COLOR"], CONFIG["ACCENT_COLOR"]] # 青色 vs 洋红
    labels = ["Me", "Ta"]
    
    # --- 辅助函数：画单个甜甜圈 ---
    def plot_donut(ax, data, total_val, title):
        wedges, texts, autotexts = ax.pie(
            data, 
            labels=labels, 
            colors=colors, 
            autopct='%1.1f%%', 
            startangle=90, 
            pctdistance=0.85, # 百分比距离圆心的距离
            wedgeprops=dict(width=0.3, edgecolor=CONFIG["BG_COLOR"]), # width=0.3 变成环形
            textprops=dict(color="white", fontsize=10)
        )
        
        # 修改字体颜色
        for text in texts: text.set_color(CONFIG["AXIS_COLOR"])
        for autotext in autotexts: autotext.set_color("white"); autotext.set_fontsize(9)
        
        # 中心写总量
        ax.text(0, 0, f"{total_val:,}", ha='center', va='center', fontsize=12, fontweight='bold', color='white')
        ax.set_title(title, pad=10, color=CONFIG["AXIS_COLOR"], fontsize=11)

    # 1. Msg Count Donut
    plot_donut(ax1, [m_count, o_count], m_count+o_count, "Messages")
    
    # 2. Char Count Donut
    plot_donut(ax2, [m_chars, o_chars], m_chars+o_chars, "Characters")
    
    return fig_to_base64(fig)


def draw_heatmap(df, label="Activity"):
    set_style()
    dates = df.groupby("Date").size()
    full_range = pd.date_range(f"{CONFIG['TARGET_YEAR']}-01-01", f"{CONFIG['TARGET_YEAR']}-12-31")
    
    chart_data = pd.DataFrame({"Timestamp": full_range})
    chart_data["count"] = chart_data["Timestamp"].dt.date.map(dates).fillna(0).astype(int)
    chart_data["week"] = (chart_data["Timestamp"] - pd.Timestamp(f"{CONFIG['TARGET_YEAR']}-01-01")).dt.days // 7
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
    ax.set_title(label, loc='right', fontsize=10, color=CONFIG["AXIS_COLOR"], pad=10)
    
    return fig_to_base64(fig)

def draw_hourly_curve(df):
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
    text = " ".join(df["StrContent"].tolist())
    text = re.sub(r"[A-Za-z0-9\[\]]", "", text) 
    words = [w for w in jieba.cut(text) if len(w) > 1]
    if not words: return None
    
    font_path = "msyh.ttc"
    if platform.system() == "Darwin": font_path = "/System/Library/Fonts/PingFang.ttc"
    
    try:
        wc = WordCloud(font_path=font_path, width=800, height=300, 
                       background_color=CONFIG["BG_COLOR"], colormap="summer", max_words=40).generate(" ".join(words))
    except: return None
        
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    ax.set_title("Keywords", loc='right', fontsize=10, color="#666")
    return fig_to_base64(fig)

def draw_rank_bar(df, title):
    set_style()
    top = df.groupby("NickName").size().sort_values(ascending=False).head(10)
    names = [clean_text(n)[:12] for n in top.index]
    
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
        ax.text(bar.get_width(), bar.get_y()+bar.get_height()/2, 
                f" {int(bar.get_width()):,}", va='center', fontsize=10, color="#888")
                
    ax.set_title(title, loc='right', pad=10, color="white", fontsize=12)
    return fig_to_base64(fig)

# ===================== 严格分类逻辑 =====================
def apply_strict_classification(df):
    print("   执行严格分类 (ID + 人数 + 关键词)...")
    
    # 1. 默认全单聊
    df["ChatType"] = "Private"
    
    # 2. 标记所有明确的群聊 (ID含@chatroom)
    if "TalkerId" in df.columns:
        df.loc[df["TalkerId"].astype(str).str.contains("chatroom"), "ChatType"] = "Group"
    if "StrTalker" in df.columns:
        df.loc[df["StrTalker"].astype(str).str.contains("chatroom"), "ChatType"] = "Group"
        
    # 2.5 兜底：NickName 本身是 chatroom ID 的，一律视为群聊
    df.loc[
        df["NickName"].astype(str).str.contains(r"@chatroom", na=False),
        "ChatType"
    ] = "Group"


    # 3. 标记所有多人说话的会话
    # 逻辑：如果一个 NickName 下面，除去 'Me' 和 'Unknown'，还有超过1个不同的 Sender，那就是群
    senders_per_chat = df[df["IsSender"]==0].groupby("NickName")["Sender"].nunique()
    group_names = senders_per_chat[senders_per_chat > 1].index
    df.loc[df["NickName"].isin(group_names), "ChatType"] = "Group"
    
    # 4. 关键词兜底 (解决漏网之鱼)
    keywords = ["群", "Group", "Team", "Offer", "指南", "2025", "25fall", "表白墙", "二手"]
    pattern = "|".join(keywords)
    df.loc[df["NickName"].str.contains(pattern, case=False, na=False), "ChatType"] = "Group"

    return df

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
    
    df["IsSender"] = pd.to_numeric(df["IsSender"], errors='coerce').fillna(0).astype(int)
    df["Date"] = df["dt"].dt.date
    df["Hour"] = df["dt"].dt.hour
    df["StrContent"] = df["StrContent"].fillna("")
    df["NickName"] = df["NickName"].fillna("Unknown").str.strip()

    if "Sender" not in df.columns:
        df["Sender"] = df["IsSender"].map({1: "Me", 0: "Other"})
    else:
        df["Sender"] = df["Sender"].fillna("Unknown")
        df.loc[df["IsSender"] == 1, "Sender"] = "Me"

    # 执行分类
    df = apply_strict_classification(df)

    print(f"✅ 分类结果: 单聊 {len(df[df['ChatType']=='Private'])} | 群聊 {len(df[df['ChatType']=='Group'])}")
    return df


def draw_member_bar(sub_df):
    set_style()
    # 排除空名，统计前10
    member_counts = sub_df[sub_df["Sender"] != ""].groupby("Sender").size().sort_values(ascending=False).head(10)
    
    if member_counts.empty: return None
    
    names = [clean_text(n)[:10] for n in member_counts.index]
    
    # === 🟢 修改点：给“Me”单独上色 ===
    # 如果名字是 "Me" 或者 "我"，就用 MAIN_COLOR (蓝/青)，否则用 ACCENT_COLOR (红/粉)
    colors = []
    for name in member_counts.index:
        if name == "Me" or name == "我": 
            colors.append(CONFIG["MAIN_COLOR"]) # <--- 你的颜色
        else:
            colors.append(CONFIG["ACCENT_COLOR"]) # <--- 别人的颜色
    # ================================

    fig, ax = plt.subplots(figsize=(10, 4))
    
    # 把 colors 列表传进去
    bars = ax.barh(range(len(member_counts)), member_counts.values, color=colors)
    ax.invert_yaxis()
    
    ax.set_yticks(range(len(member_counts)))
    ax.set_yticklabels(names, fontsize=10)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([])
    
    # 标数字
    for bar in bars:
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f"{int(bar.get_width())}", va='center', fontsize=9, color="#ccc")
                
    ax.set_title("Top 10 Active Members", loc='right', fontsize=10, color="#666")
    return fig_to_base64(fig)


# === 🟡 更新：分析循环 ===
def analyze_subset(subset_df, limit=10, is_group=False): # 多了个 is_group 参数
    top_names = subset_df.groupby("NickName").size().sort_values(ascending=False).head(limit).index
    results = []
    
    for rank, name in enumerate(top_names, 1):
        sub = subset_df[subset_df["NickName"] == name]
        print(f"    Processing #{rank}: {name}...")
        
        # 只对群聊生成成员榜单图
        member_bar = None
        if is_group:
            member_bar = draw_member_bar(sub)

        item = {
            "rank": rank,
            "name": clean_text(name),
            "count": len(sub),
            "compare": draw_donut_pair(sub),
            "heatmap": draw_heatmap(sub, "Activity"),
            "hourly": draw_hourly_curve(sub),
            "wordcloud": draw_wordcloud(sub),
            "member_bar": member_bar # <--- 把图存进去
        }
        results.append(item)
    return results

if __name__ == "__main__":
    df = load_data()
    
    if df.empty:
        exit()

    print("🚀 [3/5] 计算全局统计...")

    # ========= 时间范围 =========
    start_date = df["dt"].min().date()
    end_date = df["dt"].max().date()
    days = (end_date - start_date).days + 1

    # ========= 消息量 =========
    total_msgs = len(df)
    daily_avg = total_msgs // days

    # ========= 最疯狂的一天 =========
    daily_counts = df.groupby("Date").size()
    craziest_day = daily_counts.idxmax()
    craziest_count = int(daily_counts.max())

    # ========= 字数统计 =========
    sent_chars = int(df[df["IsSender"] == 1]["StrContent"].str.len().sum())
    recv_chars = int(df[df["IsSender"] == 0]["StrContent"].str.len().sum())
    total_chars = sent_chars + recv_chars

    # ========= 主动性 =========
    sent_msgs = int((df["IsSender"] == 1).sum())
    recv_msgs = int((df["IsSender"] == 0).sum())
    sent_ratio = round(sent_msgs / (sent_msgs + recv_msgs) * 100)
    recv_ratio = 100 - sent_ratio

    # ========= 最亲密联系人（仅单聊） =========
    df_private = df[df["ChatType"] == "Private"]
    top_contact_series = df_private.groupby("NickName").size().sort_values(ascending=False)

    top_contact_name = clean_text(top_contact_series.index[0])
    top_contact_count = int(top_contact_series.iloc[0])

    # ========= metrics 总包 =========
    metrics = {
        "total": total_msgs,
        "daily_avg": daily_avg,

        "start": start_date.strftime("%Y.%m.%d"),
        "end": end_date.strftime("%Y.%m.%d"),

        "craziest_day": craziest_day.strftime("%m-%d"),
        "craziest_count": craziest_count,

        "chars_total": total_chars,
        "chars_sent": sent_chars,
        "chars_recv": recv_chars,

        "top_contact_name": top_contact_name,
        "top_contact_count": top_contact_count,

        "sent_ratio": sent_ratio,
        "recv_ratio": recv_ratio
    }

# ... 上面的代码保持不变 ...

    # ========= 图表数据准备 =========
    df_p = df[df["ChatType"] == "Private"]
    
    # --- 🔴 修改开始：增加群聊过滤逻辑 ---
    raw_df_g = df[df["ChatType"] == "Group"]
    
    # 1. 统计我在每个群发了多少条 (IsSender=1)
    my_sent_counts = raw_df_g[raw_df_g["IsSender"] == 1].groupby("NickName").size()
    
    # 2. 找出那些我发言超过 10 条的群名
    active_group_names = my_sent_counts[my_sent_counts >= 10].index
    
    # 3. 只保留这些活跃群
    df_g = raw_df_g[raw_df_g["NickName"].isin(active_group_names)]
    
    print(f"🧹 过滤潜水群聊: 原有 {len(raw_df_g['NickName'].unique())} 个 -> 剩余 {len(active_group_names)} 个 (我发言>=10条)")
    # --- 🔴 修改结束 ---

    charts = {
        "heatmap": draw_heatmap(df, "Annual Activity"),
        "rank_p": draw_rank_bar(df_p, "Top 10 Friends"),
        "rank_g": draw_rank_bar(df_g, "Top 10 Groups") # 这里用的就是过滤后的 df_g
    }

    print("🚀 [4/5] 生成【单聊】深度画像...")
    p_profiles = analyze_subset(df_p, 10, is_group=False) # 传 False
    
    print("🚀 [5/5] 生成【群聊】深度画像...")
    g_profiles = analyze_subset(df_g, 10, is_group=True)  # 传 True

    # ... 下面的保存代码保持不变 ...
    data_package = {
        "metrics": metrics,
        "charts": charts,
        "private_profiles": p_profiles,
        "group_profiles": g_profiles
    }

    print("💾 保存数据到 report_data.json ...")
    with open("report_data.json", "w", encoding="utf-8") as f:
        json.dump(data_package, f, ensure_ascii=False)

    print("\n✅ 完成！请运行 step2_render.py")