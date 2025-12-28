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
    """画两个并排的环形图：左边消息数，右边字数"""
    set_style()
    
    # 数据准备
    me = df[df["IsSender"]==1]
    other = df[df["IsSender"]==0]
    
    m_count = len(me)
    o_count = len(other)
    m_chars = me["StrContent"].str.len().sum()
    o_chars = other["StrContent"].str.len().sum()
    
    if m_count + o_count == 0: m_count = 1
    if m_chars + o_chars == 0: m_chars = 1
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    colors = [CONFIG["MAIN_COLOR"], CONFIG["ACCENT_COLOR"]] 
    labels = ["我", "对方"]  # 汉化
    
    # --- 辅助函数 ---
    def plot_donut(ax, data, total_val, title):
        wedges, texts, autotexts = ax.pie(
            data, 
            labels=labels, 
            colors=colors, 
            autopct='%1.1f%%', 
            startangle=90, 
            pctdistance=0.85, 
            wedgeprops=dict(width=0.3, edgecolor=CONFIG["BG_COLOR"]), 
            textprops=dict(color="white", fontsize=10)
        )
        for text in texts: text.set_color(CONFIG["AXIS_COLOR"])
        for autotext in autotexts: autotext.set_color("white"); autotext.set_fontsize(9)
        
        ax.text(0, 0, f"{total_val:,}", ha='center', va='center', fontsize=12, fontweight='bold', color='white')
        ax.set_title(title, pad=10, color=CONFIG["AXIS_COLOR"], fontsize=11)

    plot_donut(ax1, [m_count, o_count], m_count+o_count, "消息条数")
    plot_donut(ax2, [m_chars, o_chars], m_chars+o_chars, "总字符数")
    
    return fig_to_base64(fig)


def draw_heatmap(df, label="活跃度"):
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
    
    sns.heatmap(
        pivot,
        cmap=cmap,
        vmin=0,
        vmax=vmax,
        cbar=False,
        square=True,
        ax=ax,
        linewidths=0.5,
        linecolor=CONFIG["BG_COLOR"]
    )

    # 月份刻度汉化
    month_starts = (
        chart_data
        .groupby(chart_data["Timestamp"].dt.to_period("M"))["week"]
        .min()
    )

    ax.set_xticks(month_starts.values + 0.5)
    # 使用数字月份，如 "1月"
    month_labels = [f"{m}月" for m in range(1, 13)]
    # 如果数据不满一年，需要截断，这里简单处理直接用 index 的月份
    real_months = chart_data["Timestamp"].dt.month.unique()
    month_labels = [f"{m}月" for m in real_months]
    
    ax.set_xticklabels(month_labels, fontsize=9)

    ax.set_yticks([0.5, 3.5, 6.5])
    ax.set_yticklabels(["周一", "周四", "周日"], rotation=0, fontsize=9) # 汉化
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
    ax.set_xticklabels(["0点", "6点", "12点", "18点", "23点"]) # 汉化
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_yticks([])
    ax.set_title("24小时活跃分布", loc='right', fontsize=10, color="#666") # 汉化
    return fig_to_base64(fig)

def draw_wordcloud(df):
    text = " ".join(df["StrContent"].astype(str).tolist())
    text = re.sub(r"[A-Za-z0-9\[\]]", "", text)

    # === 1. 停用词 ===
    stopwords = set([
        "这个","那个","不是","没有","然后","怎么","现在","知道","我们",
        "你们","他们","一个","一下","这样","那样","如果","因为","所以",
        "今天","明天","昨天","已经","还是","可能","出来","什么","看看",
        "哈哈","哈哈哈","感觉","好像","自己","其实","应该","需要","就是",
        "还有","还有个","还有一个","然后呢","然后就","然后我","然后你","然后他","然后她","然后他们","然后我们",
        "然后大家","收到","收到吗","收到没","收到没有","收到没有？","收到没有！","收到没有！","知道吗","知道没","知道没有","知道没有？","知道没有！",
        "知道没有！","了解","了解吗","了解没","了解没有","了解没有？","了解没有！","了解没有！","明白","明白吗","明白没","明白没有","明白没有？","明白没有！","明白没有！",
        "好的","好的吧","好的啊","好的呀","好的哦","好的呢","好的！","好的！","谢谢","谢谢你","谢谢您","谢谢大家","感谢","感谢你","感谢您","感谢大家",
        "再见","拜拜","晚安","早安","午安","早上好","中午好","下午好","晚上好","节日快乐","生日快乐","新年快乐","圣诞快乐","元旦快乐","春节快乐","国庆快乐","劳动节快乐","儿童节快乐","的","了","我","是","在","也","有","就","不","人","我们",
        "你","他","她","它","你们","他们","她们","它们",
        "这","那","这个","那个","这种","那种",
        "和","与","但","如果","因为","所以","而","及","或者","并且","但是","不过","虽然","确实","为什么","怎么样","怎么了","一样",
        "要","会","说","都","很","给","上","去","来",

        # —— 口语 / 语气 —— #
        "啊","吗","吧","哈哈","哈哈哈哈","真的","觉得","感觉","东西","这么","那么","这样","那个","这个",
        "就是","就是说","就是说呢","就是说吧","就是说啊","就是说吗","比较","的话","的话呢","的话吧","的话啊","的话吗",
        "可以","行","还","还好","有点","其实","可能","应该",
        "然后","反正","毕竟","就是说","所以说",

        # —— 否定 & 泛动词（重点） —— #
        "不要","不能","不会","不行","不用","不想","不太",
        "开始","出来","直接","看看","想要","喜欢","知道","想","看","好",

        # —— 时间 / 范围 —— #
        "现在","今天","昨天","明天","今年","去年",
        "之前","以后","当时","刚","刚刚","已经","正在","将要",
        "一些","一点","很多","几个","每个","每次","部分",

        # —— 泛名词 / 废词 —— #
        "个人","所有人","有人","别人","大家",
        "方面","情况","问题","内容","结果","过程","原因",
        "相关","进行","表示","认为","发现","说明","指出",

        # —— 地点 / 指代 —— #
        "这里","那里","哪里","时候","什么","怎么","怎么了","怎么会",

        # —— 媒体 —— #
        "图片","视频",

        # —— 符号 —— #
        "，","。","！","？","、","：","；","“","”","‘","’",
        "（","）","【","】","…","—"
    ])

    words = []
    for w in jieba.cut(text):
        if len(w) < 2 or w in stopwords: continue
        if re.fullmatch(r"[这那什怎没不还已]*", w): continue
        words.append(w)

    if not words: return None

    font_path = "msyh.ttc"
    if platform.system() == "Darwin":
        font_path = "/System/Library/Fonts/PingFang.ttc"

    wc = WordCloud(
        font_path=font_path,
        width=900,
        height=350,
        background_color=CONFIG["BG_COLOR"],
        colormap="summer",
        max_words=50
    ).generate(" ".join(words))

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("年度关键词", loc="right", fontsize=10, color="#666") # 汉化

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
    print("   🔍 执行严格分类 (ID + 人数 + 关键词)...")
    df["ChatType"] = "Private"
    
    if "TalkerId" in df.columns:
        df.loc[df["TalkerId"].astype(str).str.contains("chatroom"), "ChatType"] = "Group"
    if "StrTalker" in df.columns:
        df.loc[df["StrTalker"].astype(str).str.contains("chatroom"), "ChatType"] = "Group"
    df.loc[df["NickName"].astype(str).str.contains(r"@chatroom", na=False), "ChatType"] = "Group"

    senders_per_chat = df[df["IsSender"]==0].groupby("NickName")["Sender"].nunique()
    group_names = senders_per_chat[senders_per_chat > 1].index
    df.loc[df["NickName"].isin(group_names), "ChatType"] = "Group"
    
    keywords = ["群", "Group", "Team", "Offer", "指南", "2025", "25fall", "表白墙", "二手"]
    pattern = "|".join(keywords)
    df.loc[df["NickName"].str.contains(pattern, case=False, na=False), "ChatType"] = "Group"

    return df

def load_data():
    print(f"🚀 [1/4] 读取数据: {CONFIG['CSV_PATH']} ...")
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

    df = apply_strict_classification(df)

    print(f"✅ 分类结果: 单聊 {len(df[df['ChatType']=='Private'])} | 群聊 {len(df[df['ChatType']=='Group'])}")
    return df

# === 趋势图 ===
def draw_line_chart(df, title):
    set_style()
    daily_counts = df.groupby("Date").size()
    idx = pd.date_range(f"{CONFIG['TARGET_YEAR']}-01-01", f"{CONFIG['TARGET_YEAR']}-12-31")
    daily_counts = daily_counts.reindex(idx, fill_value=0)
    
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(daily_counts.index, daily_counts.values, color=CONFIG["MAIN_COLOR"], linewidth=1.5)
    ax.fill_between(daily_counts.index, daily_counts.values, color=CONFIG["MAIN_COLOR"], alpha=0.1)
    ax.axis('off')
    ax.set_title(title, loc='left', fontsize=12, color="white", pad=10)
    return fig_to_base64(fig)

# === 群成员条形图 ===
def draw_member_bar(sub_df):
    set_style()
    member_counts = sub_df[sub_df["Sender"] != ""].groupby("Sender").size().sort_values(ascending=False).head(10)
    if member_counts.empty: return None
    
    names = [clean_text(n)[:10] for n in member_counts.index]
    
    colors = []
    for name in member_counts.index:
        if "Me" in name or "我" in name: colors.append(CONFIG["MAIN_COLOR"])
        else: colors.append(CONFIG["ACCENT_COLOR"])

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.barh(range(len(member_counts)), member_counts.values, color=colors)
    ax.invert_yaxis()
    ax.set_yticks(range(len(member_counts)))
    ax.set_yticklabels(names, fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xticks([])
    
    for bar in bars:
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f"{int(bar.get_width())}", va='center', fontsize=9, color="#ccc")
                
    ax.set_title("活跃成员 Top 10", loc='right', fontsize=10, color="#666") # 汉化
    return fig_to_base64(fig)

# === 分析循环 ===
def analyze_subset(subset_df, limit=10, is_group=False):
    top_names = subset_df.groupby("NickName").size().sort_values(ascending=False).head(limit).index
    results = []
    
    for rank, name in enumerate(top_names, 1):
        sub = subset_df[subset_df["NickName"] == name]
        print(f"    处理中 #{rank}: {name}") # 汉化
        
        member_bar = None
        if is_group:
            member_bar = draw_member_bar(sub)

        item = {
            "rank": rank,
            "name": clean_text(name),
            "count": len(sub),
            "compare": draw_donut_pair(sub),
            "heatmap": draw_heatmap(sub, "活跃热力图"),
            "hourly": draw_hourly_curve(sub),
            "wordcloud": draw_wordcloud(sub),
            "member_bar": member_bar
        }
        results.append(item)
    return results

if __name__ == "__main__":
    df = load_data()
    if df.empty: exit()

    print("🚀 [2/4] 计算全局统计...")

    start_date = df["dt"].min().date()
    end_date = df["dt"].max().date()
    days = (end_date - start_date).days + 1

    total_msgs = len(df)
    daily_avg = total_msgs // days

    daily_counts = df.groupby("Date").size()
    craziest_day = daily_counts.idxmax()
    craziest_count = int(daily_counts.max())

    sent_chars = int(df[df["IsSender"] == 1]["StrContent"].str.len().sum())
    recv_chars = int(df[df["IsSender"] == 0]["StrContent"].str.len().sum())
    total_chars = sent_chars + recv_chars

    df_private = df[df["ChatType"] == "Private"]
    top_contact_series = df_private.groupby("NickName").size().sort_values(ascending=False)
    top_contact_name = clean_text(top_contact_series.index[0])
    top_contact_count = int(top_contact_series.iloc[0])

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
        "top_contact_count": top_contact_count
    }

    df_p = df[df["ChatType"] == "Private"]
    raw_df_g = df[df["ChatType"] == "Group"]
    df_me = df[df["IsSender"] == 1]

    global_charts = {
        "my_hourly": draw_hourly_curve(df_me),
        "my_wordcloud": draw_wordcloud(df_me)
    }

    my_sent_counts = raw_df_g[raw_df_g["IsSender"] == 1].groupby("NickName").size()
    active_group_names = my_sent_counts[my_sent_counts >= 10].index
    df_g = raw_df_g[raw_df_g["NickName"].isin(active_group_names)]
    
    print(f"🧹 过滤潜水群聊: 原有 {len(raw_df_g['NickName'].unique())} 个 -> 剩余 {len(active_group_names)} 个 (我发言>=10条)")

    print("📊 正在绘制年度趋势 & 全局词云...")
    chart_me_trend = draw_line_chart(df[df["IsSender"]==1], "我的发言趋势（仅发送）") # 汉化
    chart_global_wc = draw_wordcloud(df)

    charts = {
        "heatmap": draw_heatmap(df, "年度活跃热力图"),
        "rank_p": draw_rank_bar(df_p, "好友 Top 10"),
        "rank_g": draw_rank_bar(df_g, "群聊 Top 10"),
        "trend_me": chart_me_trend,
        "wordcloud_global": chart_global_wc
    }

    print("🚀 [3/4] 生成【单聊】深度画像...")
    p_profiles = analyze_subset(df_p, 10, is_group=False)
    
    print("🚀 [4/4] 生成【群聊】深度画像...")
    g_profiles = analyze_subset(df_g, 10, is_group=True)

    data_package = {
        "metrics": metrics,
        "charts": charts,
        "global_charts": global_charts,
        "private_profiles": p_profiles,
        "group_profiles": g_profiles
    }

    print("💾 保存数据到 report_data.json ...")
    with open("report_data.json", "w", encoding="utf-8") as f:
        json.dump(data_package, f, ensure_ascii=False)

    print("\n✅ 完成！请运行 step2_render.py")