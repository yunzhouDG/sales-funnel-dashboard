import streamlit as st
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="天猫新零售数据看板", page_icon="📊")

# ==================== 精美样式（增强版） ====================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f0f4fc 0%, #e9eef6 100%);
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    }
    .card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(2px);
        border-radius: 28px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.03), 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.25s ease;
        border: 1px solid rgba(255,255,255,0.6);
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f9fcff 100%);
        border-radius: 24px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid rgba(59,130,246,0.15);
        transition: all 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #4b5563;
        letter-spacing: 0.03em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #111827;
        line-height: 1.2;
    }
    .metric-compare {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 0.5rem;
        display: flex;
        gap: 0.8rem;
    }
    .compare-up { color: #10b981; font-weight: 500; }
    .compare-down { color: #ef4444; font-weight: 500; }
    .dashboard-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(120deg, #1e40af, #7c3aed);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin-bottom: 0.2rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1f2937;
        border-left: 5px solid #3b82f6;
        padding-left: 0.8rem;
        margin: 1.2rem 0 1rem 0;
        letter-spacing: -0.01em;
    }
    .stPlotlyChart {
        background: white;
        border-radius: 24px;
        padding: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        border: 1px solid #eef2f6;
    }
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.92);
        backdrop-filter: blur(8px);
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 标准省份列表 & 坐标 ====================
STANDARD_PROVINCES = {
    '北京市', '上海市', '天津市', '重庆市',
    '河北省', '山西省', '辽宁省', '吉林省', '黑龙江省',
    '江苏省', '浙江省', '安徽省', '福建省', '江西省', '山东省',
    '河南省', '湖北省', '湖南省', '广东省', '海南省', '四川省',
    '贵州省', '云南省', '陕西省', '甘肃省', '青海省', '台湾省',
    '内蒙古自治区', '广西壮族自治区', '西藏自治区', '宁夏回族自治区', '新疆维吾尔自治区',
    '香港特别行政区', '澳门特别行政区'
}

PROVINCE_CENTER = {
    '北京市': [116.4074, 39.9042], '上海市': [121.4737, 31.2304],
    '天津市': [117.1902, 39.1256], '重庆市': [106.5044, 29.5582],
    '河北省': [114.4995, 38.1006], '山西省': [112.5624, 37.8735],
    '内蒙古自治区': [111.7510, 40.8415], '辽宁省': [123.4315, 41.8057],
    '吉林省': [125.3235, 43.8171], '黑龙江省': [126.5364, 45.8022],
    '江苏省': [118.7674, 32.0415], '浙江省': [120.1551, 30.2741],
    '安徽省': [117.2272, 31.8206], '福建省': [119.2965, 26.0745],
    '江西省': [115.8582, 28.6820], '山东省': [117.0009, 36.6758],
    '河南省': [113.6254, 34.7466], '湖北省': [114.3055, 30.5931],
    '湖南省': [112.9388, 28.2282], '广东省': [113.2644, 23.1291],
    '广西壮族自治区': [108.3661, 22.8176], '海南省': [110.1999, 20.0440],
    '四川省': [104.0668, 30.5728], '贵州省': [106.6302, 26.6477],
    '云南省': [102.8329, 24.8801], '西藏自治区': [91.1409, 29.6565],
    '陕西省': [108.9402, 34.3416], '甘肃省': [103.8343, 36.0611],
    '青海省': [101.7782, 36.6232], '宁夏回族自治区': [106.2309, 38.4872],
    '新疆维吾尔自治区': [87.6168, 43.8256], '台湾省': [121.5200, 25.0300],
    '香港特别行政区': [114.1700, 22.2700], '澳门特别行政区': [113.5400, 22.1900]
}

# ==================== 辅助函数 ====================
def standardize_brand(brand_val):
    if pd.isna(brand_val):
        return "未知"
    s = str(brand_val).strip().lower()
    if '小天鹅' in s or 'swan' in s:
        return "小天鹅"
    if '东芝' in s or 'toshiba' in s:
        return "东芝"
    if 'colmo' in s or '科摩' in s:
        return "colmo"
    if '美的' in s or 'midea' in s:
        return "美的"
    return brand_val

def apply_brand_filter(df, selected_brands):
    if not selected_brands:
        return df
    cond = pd.Series(False, index=df.index)
    normal_brands = [b for b in selected_brands if b not in ["洗衣机汇总", "美的厨热", "美的冰箱", "美的空调"]]
    if normal_brands:
        cond |= df["品牌"].isin(normal_brands)
    if "洗衣机汇总" in selected_brands:
        cond |= (df["品牌"] == "小天鹅") | ((df["品牌"] == "美的") & (df["品类"] == "洗衣机"))
    if "美的厨热" in selected_brands:
        cond |= (df["品牌"] == "美的") & (df["品类"] == "厨热")
    if "美的冰箱" in selected_brands:
        cond |= (df["品牌"] == "美的") & (df["品类"] == "冰箱")
    if "美的空调" in selected_brands:
        cond |= (df["品牌"] == "美的") & (df["品类"] == "空调")
    return df[cond]

def filter_by_date(df, date_range):
    if "日期" not in df.columns or df["日期"].isna().all():
        return df
    d_start, d_end = date_range
    return df[(df["日期"].dt.date >= d_start) & (df["日期"].dt.date <= d_end)]

def normalize_province_name(name):
    if not name:
        return None
    name = str(name).strip()
    if name in ['北京', '北京市']: return '北京市'
    if name in ['上海', '上海市']: return '上海市'
    if name in ['天津', '天津市']: return '天津市'
    if name in ['重庆', '重庆市']: return '重庆市'
    if name in ['广西', '广西壮族自治区']: return '广西壮族自治区'
    if name in ['内蒙古', '内蒙古自治区']: return '内蒙古自治区'
    if name in ['宁夏', '宁夏回族自治区']: return '宁夏回族自治区'
    if name in ['新疆', '新疆维吾尔自治区']: return '新疆维吾尔自治区'
    if name in ['西藏', '西藏自治区']: return '西藏自治区'
    if name.endswith('省'):
        return name
    common = ['江苏','浙江','广东','山东','河南','四川','湖北','湖南','河北','福建','安徽','辽宁','江西','陕西','山西','云南','贵州','甘肃','青海','吉林','黑龙江','海南','台湾']
    if name in common:
        return name + '省'
    return name

def extract_province_from_raw(province_raw):
    if pd.isna(province_raw) or not province_raw:
        return None
    s = str(province_raw).strip()
    if '-' in s:
        parts = s.split('-')
        if len(parts) == 2:
            province_part = parts[0].strip()
        elif len(parts) >= 3:
            province_part = parts[1].strip()
        else:
            province_part = s
    else:
        province_part = s
    return normalize_province_name(province_part)

def filter_and_compute_metrics(df_main, df_order, start_date, end_date, sel_brand, sel_cat, sel_center, sel_area):
    df_m = filter_by_date(df_main, (start_date, end_date))
    df_m = apply_brand_filter(df_m, sel_brand)
    if sel_cat:
        df_m = df_m[df_m["品类"].isin(sel_cat)]
    if sel_center:
        df_m = df_m[df_m["运营中心"].isin(sel_center)]
    if sel_area:
        df_m = df_m[df_m["片区"].isin(sel_area)]

    df_o = filter_by_date(df_order, (start_date, end_date))
    df_o = apply_brand_filter(df_o, sel_brand)
    if sel_cat:
        df_o = df_o[df_o["品类"].isin(sel_cat)]
    if sel_center:
        df_o = df_o[df_o["运营中心"].isin(sel_center)]

    total_leads = len(df_m)
    valid_mask = df_m["外呼状态"].isin(["高意向", "低意向", "无需外呼"])
    valid_leads = valid_mask.sum()
    order_count = len(df_o)
    total_amount = df_o["订单金额"].sum() if not df_o.empty else 0.0
    return df_m, df_o, total_leads, valid_leads, order_count, total_amount

def get_previous_period_range(start_date, end_date, period='day'):
    days = (end_date - start_date).days
    if period == 'day':
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days)
    elif period == 'month':
        prev_end = start_date - relativedelta(months=1)
        prev_start = prev_end - timedelta(days=days)
    else:
        raise ValueError
    return prev_start, prev_end

def format_compare(current, previous):
    if previous is None or previous == 0:
        return '<span style="color:#94a3b8;">无数据</span>', None
    change = (current - previous) / previous
    arrow = "▲" if change >= 0 else "▼"
    color_class = "compare-up" if change >= 0 else "compare-down"
    percent = f"{abs(change)*100:.1f}%"
    html = f'<span class="{color_class}">{arrow} {percent}</span>'
    return html, change

def get_compare_html(current, prev_day, prev_month):
    day_html, _ = format_compare(current, prev_day)
    month_html, _ = format_compare(current, prev_month)
    return f'<div class="metric-compare"><span>日环比 {day_html}</span><span>月环比 {month_html}</span></div>'

# ==================== 数据加载 ====================
@st.cache_data(ttl=3600)
def load_data():
    if not os.path.exists("data.zip"):
        st.error("❌ 未找到 data.zip 文件，请将数据文件放在应用同目录下")
        st.stop()
    import zipfile
    with zipfile.ZipFile("data.zip", "r") as zf:
        db_files = [f for f in zf.namelist() if f.endswith(".db")]
        if not db_files:
            st.error("❌ 压缩包中未找到 .db 文件")
            st.stop()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            with zf.open(db_files[0]) as f:
                tmp.write(f.read())
            tmp_path = tmp.name

    import sqlite3
    conn = sqlite3.connect(tmp_path)
    try:
        df_main = pd.read_sql("SELECT * FROM 客资明细表", conn)
        df_order = pd.read_sql("SELECT * FROM 订单表", conn)
    except Exception as e:
        st.error(f"数据库读取失败: {e}\n请确保表名分别为 '客资明细表' 和 '订单表'")
        st.stop()
    finally:
        conn.close()
        os.unlink(tmp_path)

    if "获取时间" in df_main.columns:
        df_main["日期"] = pd.to_datetime(df_main["获取时间"], errors="coerce")
        df_main["获取时间_原始"] = df_main["获取时间"]
    elif "日期" in df_main.columns:
        df_main["日期"] = pd.to_datetime(df_main["日期"], errors="coerce")
    else:
        df_main["日期"] = pd.NaT

    if "日期" in df_order.columns:
        df_order["日期"] = pd.to_datetime(df_order["日期"], errors="coerce")
    else:
        df_order["日期"] = pd.NaT

    if "订单金额" in df_order.columns:
        df_order["订单金额"] = pd.to_numeric(df_order["订单金额"], errors="coerce").fillna(0)
    else:
        df_order["订单金额"] = 0.0

    for df in [df_main, df_order]:
        raw_brand = df.get("品牌", df.get("意向品牌", "未知")).fillna("未知")
        df["品牌"] = raw_brand.apply(standardize_brand)
        df["品类"] = df.get("品类", "未知").fillna("未知")
        df["运营中心"] = df.get("运营中心", df.get("运中", "未知")).fillna("未知")
        df["片区"] = df.get("片区", "未知").fillna("未知")

    if "外呼状态" not in df_main.columns:
        df_main["外呼状态"] = ""
    if "最新跟进状态" not in df_main.columns:
        df_main["最新跟进状态"] = ""

    for col in ["省份", "省市"]:
        if col in df_main.columns:
            df_main["省份_raw"] = df_main[col].fillna("").astype(str).str.strip()
            break
    else:
        df_main["省份_raw"] = ""

    for col in ["城市", "市区"]:
        if col in df_main.columns:
            df_main["城市_raw"] = df_main[col].fillna("").astype(str).str.strip()
            break
    else:
        df_main["城市_raw"] = ""

    for col in ["省份", "省市"]:
        if col in df_order.columns:
            df_order["省份_raw"] = df_order[col].fillna("").astype(str).str.strip()
            break
    else:
        df_order["省份_raw"] = ""

    for col in ["城市", "市区"]:
        if col in df_order.columns:
            df_order["城市_raw"] = df_order[col].fillna("").astype(str).str.strip()
            break
    else:
        df_order["城市_raw"] = ""

    return df_main, df_order

# ==================== 主程序 ====================
df_main, df_order = load_data()
if df_main.empty:
    st.error("客资明细表为空")
    st.stop()

df_main["省份_客资"] = df_main["省份_raw"].apply(extract_province_from_raw)
df_main["城市_客资"] = df_main["城市_raw"]
df_order["省份_订单"] = df_order["省份_raw"].apply(extract_province_from_raw)
df_order["城市_订单"] = df_order["城市_raw"]

all_brands = set(df_main["品牌"].dropna().unique()) | set(df_order["品牌"].dropna().unique())
actual_brands = sorted([b for b in all_brands if b and b != "未知"])
actual_cats = sorted([c for c in df_main["品类"].dropna().unique() if c and c != "未知"])
actual_centers = sorted([c for c in df_main["运营中心"].dropna().unique() if c and c != "未知"])
actual_areas = sorted([a for a in df_main["片区"].dropna().unique() if a and a != "未知"])
brand_options = actual_brands + ["洗衣机汇总", "美的厨热", "美的冰箱", "美的空调"]

st.sidebar.markdown("## 🎛️ 筛选面板")
if not df_main["日期"].isna().all():
    min_date = df_main["日期"].min().date()
    max_date = df_main["日期"].max().date()
else:
    min_date = datetime.today().date()
    max_date = datetime.today().date()

start_date = st.sidebar.date_input("开始日期", min_date)
end_date = st.sidebar.date_input("结束日期", max_date)

col1_s, col2_s = st.sidebar.columns(2)
with col1_s:
    sel_brand = st.multiselect("🏷️ 品牌", brand_options, default=[])
    sel_cat = st.multiselect("📦 品类", actual_cats, default=[])
with col2_s:
    sel_area = st.multiselect("🗺️ 片区", actual_areas, default=[])
    sel_center = st.multiselect("📍 运营中心", actual_centers, default=[])

df_m_curr, df_o_curr, total_leads, valid_leads, order_count, total_amount = filter_and_compute_metrics(
    df_main, df_order, start_date, end_date, sel_brand, sel_cat, sel_center, sel_area
)

day_prev_start, day_prev_end = get_previous_period_range(start_date, end_date, 'day')
_, _, total_leads_day_prev, valid_leads_day_prev, order_count_day_prev, amount_day_prev = filter_and_compute_metrics(
    df_main, df_order, day_prev_start, day_prev_end, sel_brand, sel_cat, sel_center, sel_area
)
month_prev_start, month_prev_end = get_previous_period_range(start_date, end_date, 'month')
_, _, total_leads_month_prev, valid_leads_month_prev, order_count_month_prev, amount_month_prev = filter_and_compute_metrics(
    df_main, df_order, month_prev_start, month_prev_end, sel_brand, sel_cat, sel_center, sel_area
)

compare_leads = get_compare_html(total_leads, total_leads_day_prev, total_leads_month_prev)
compare_valid = get_compare_html(valid_leads, valid_leads_day_prev, valid_leads_month_prev)
compare_orders = get_compare_html(order_count, order_count_day_prev, order_count_month_prev)
compare_amount = get_compare_html(total_amount, amount_day_prev, amount_month_prev)

latest_date = max_date.strftime("%Y年%m月%d日") if not df_main["日期"].isna().all() else "未知"
st.markdown('<div class="dashboard-title">🏬 天猫新零售数据看板</div>', unsafe_allow_html=True)
st.markdown(f"<div style='color:#4b5563; margin-bottom:1rem;'>数据更新至 {latest_date}</div>", unsafe_allow_html=True)

# ==================== 【第一部分：你的原始看板】====================
st.markdown("---")
st.markdown("### 📌 基础看板", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">📋 总客资</div>
        <div class="metric-value">{total_leads:,}</div>
        {compare_leads}
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">✅ 有效客资</div>
        <div class="metric-value">{valid_leads:,}</div>
        {compare_valid}
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🛒 成交单量</div>
        <div class="metric-value">{order_count:,}</div>
        {compare_orders}
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💰 总金额（万元）</div>
        <div class="metric-value">{total_amount/10000:.2f} 万</div>
        {compare_amount}
    </div>
    """, unsafe_allow_html=True)

# 日客资数趋势
st.markdown('<div class="section-header">📅 日客资数趋势</div>', unsafe_allow_html=True)
if not df_m_curr.empty and "日期" in df_m_curr:
    daily_leads = df_m_curr.groupby(df_m_curr["日期"].dt.date).size().reset_index(name="客资数")
    daily_leads["日期_中文"] = daily_leads["日期"].apply(lambda d: d.strftime("%m-%d"))
    fig_daily = px.bar(daily_leads, x="日期_中文", y="客资数", text="客资数",
                       color_discrete_sequence=['#3b82f6'], title="每日客资数量")
    fig_daily.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_daily.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_tickangle=-30,
        height=500,
        margin=dict(l=20, r=20, t=40, b=80)
    )
    st.plotly_chart(fig_daily, use_container_width=True)
else:
    st.info("无日期数据")

# 转化漏斗
st.markdown('<div class="section-header">📉 转化漏斗</div>', unsafe_allow_html=True)
valid_mask_curr = df_m_curr["外呼状态"].isin(["高意向", "低意向", "无需外呼"])
assigned = df_m_curr[valid_mask_curr & (df_m_curr["最新跟进状态"] != "未分配")].shape[0] if "最新跟进状态" in df_m_curr else 0
followed = df_m_curr[valid_mask_curr & (~df_m_curr["最新跟进状态"].isin(["未分配", "待查看", "待联系"]))].shape[0] if "最新跟进状态" in df_m_curr else 0
funnel_labels = ["总客资", "有效客资", "已分配", "已跟进", "成交"]
funnel_values = [total_leads, valid_leads, assigned, followed, order_count]
fig_funnel = go.Figure(go.Funnel(
    y=funnel_labels, x=funnel_values,
    marker=dict(color=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd']),
    textinfo="value", texttemplate='%{value:,.0f}', textposition="inside"
))
fig_funnel.update_layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=30, b=10),
    height=400
)
st.plotly_chart(fig_funnel, use_container_width=True)

# 品牌客资与订单金额对比 + 运营中心客资量
col_a, col_b = st.columns(2)
with col_a:
    st.markdown('<div class="section-header">🏷️ 品牌客资量与订单金额对比</div>', unsafe_allow_html=True)
    if not df_m_curr.empty and not df_o_curr.empty:
        brand_leads = df_m_curr.groupby("品牌").size().reset_index(name="客资量")
        brand_amount = df_o_curr.groupby("品牌")["订单金额"].sum().reset_index()
        brand_comp = brand_leads.merge(brand_amount, on="品牌", how="outer").fillna(0)
        brand_comp = brand_comp.sort_values("客资量", ascending=False).head(10)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(x=brand_comp["品牌"], y=brand_comp["客资量"], name="客资量", marker_color='#3b82f6', yaxis="y"))
        fig_comp.add_trace(go.Bar(x=brand_comp["品牌"], y=brand_comp["订单金额"], name="订单金额(元)", marker_color='#f97316', yaxis="y2"))
        fig_comp.update_layout(
            yaxis=dict(title="客资量", side="left"),
            yaxis2=dict(title="订单金额(元)", overlaying="y", side="right"),
            plot_bgcolor='rgba(0,0,0,0)', xaxis_tickangle=-45, barmode='group'
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("数据不足")
with col_b:
    st.markdown('<div class="section-header">🏢 各运营中心客资量 TOP10</div>', unsafe_allow_html=True)
    if not df_m_curr.empty:
        center_leads = df_m_curr.groupby("运营中心").size().reset_index(name="客资量")
        center_leads = center_leads.sort_values("客资量", ascending=False).head(10)
        fig_center_leads = px.bar(center_leads, x="客资量", y="运营中心", orientation='h',
                                  color="客资量", color_continuous_scale="Blues", text="客资量")
        fig_center_leads.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_center_leads.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=400)
        st.plotly_chart(fig_center_leads, use_container_width=True)
    else:
        st.info("无客资数据")

# 品类订单金额占比 + 运营中心订单金额
col_c, col_d = st.columns(2)
with col_c:
    st.markdown('<div class="section-header">🍩 品类订单金额占比</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        cat_sale = df_o_curr.groupby("品类")["订单金额"].sum().reset_index()
        cat_sale["万元"] = cat_sale["订单金额"] / 10000
        fig_cat_pie = px.pie(cat_sale, names="品类", values="订单金额", title="品类销售额占比",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_cat_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat_pie, use_container_width=True)
    else:
        st.info("无订单数据")
with col_d:
    st.markdown('<div class="section-header">💰 各运营中心订单金额 TOP10</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        center_amount = df_o_curr.groupby("运营中心")["订单金额"].sum().reset_index()
        center_amount = center_amount.sort_values("订单金额", ascending=False).head(10)
        center_amount["万元"] = center_amount["订单金额"] / 10000
        fig_center_amount = px.bar(center_amount, x="万元", y="运营中心", orientation='h',
                                   color="万元", color_continuous_scale="Tealgrn", text="万元")
        fig_center_amount.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig_center_amount.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=400)
        st.plotly_chart(fig_center_amount, use_container_width=True)
    else:
        st.info("无订单数据")

# 转化率趋势
st.markdown('<div class="section-header">📈 转化率趋势（面积图）</div>', unsafe_allow_html=True)
if not df_m_curr.empty and "日期" in df_m_curr:
    daily_trend = df_m_curr.groupby(df_m_curr["日期"].dt.date).agg(
        总客资=("品牌", "count"),
        有效客资=("外呼状态", lambda x: x.isin(["高意向", "低意向", "无需外呼"]).sum())
    ).reset_index()
    if not df_o_curr.empty:
        daily_order = df_o_curr.groupby(df_o_curr["日期"].dt.date).size().reset_index(name="成交数")
        daily_trend = daily_trend.merge(daily_order, on="日期", how="left").fillna(0)
    else:
        daily_trend["成交数"] = 0
    daily_trend["转化率"] = daily_trend["成交数"] / daily_trend["有效客资"].replace(0, pd.NA)
    daily_trend["日期_中文"] = daily_trend["日期"].apply(lambda d: d.strftime("%m-%d"))
    fig_area = px.area(daily_trend, x="日期_中文", y="转化率", title="每日转化率趋势",
                       labels={"转化率": "转化率", "日期_中文": "日期"},
                       color_discrete_sequence=['#ef4444'])
    fig_area.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=450)
    st.plotly_chart(fig_area, use_container_width=True)
else:
    st.info("无数据")

# 省份销售额排行 + 帕累托
col_e, col_f = st.columns(2)
with col_e:
    st.markdown('<div class="section-header">🗺️ 省份销售额排行 TOP20</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        province_sale = df_o_curr.groupby("省份_订单")["订单金额"].sum().reset_index()
        province_sale = province_sale[province_sale["省份_订单"].notna() & (province_sale["省份_订单"] != "")]
        province_sale = province_sale[province_sale["省份_订单"].isin(STANDARD_PROVINCES)]
        province_sale["万元"] = province_sale["订单金额"] / 10000
        province_sale = province_sale.sort_values("万元", ascending=False).head(20)
        fig_prov = px.bar(province_sale, x="万元", y="省份_订单", orientation='h',
                          color="万元", color_continuous_scale="Blues", text="万元")
        fig_prov.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig_prov.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_prov, use_container_width=True)
    else:
        st.info("无订单数据")
with col_f:
    st.markdown('<div class="section-header">📊 省份销售额帕累托分析</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        pareto_data = df_o_curr.groupby("省份_订单")["订单金额"].sum().reset_index()
        pareto_data = pareto_data[pareto_data["省份_订单"].notna() & (pareto_data["省份_订单"] != "")]
        pareto_data = pareto_data[pareto_data["省份_订单"].isin(STANDARD_PROVINCES)]
        pareto_data["万元"] = pareto_data["订单金额"] / 10000
        pareto_data = pareto_data.sort_values("万元", ascending=False)
        pareto_data["累计百分比"] = pareto_data["万元"].cumsum() / pareto_data["万元"].sum() * 100
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=pareto_data["省份_订单"], y=pareto_data["万元"], name="销售额(万元)", marker_color='#3b82f6'))
        fig_pareto.add_trace(go.Scatter(x=pareto_data["省份_订单"], y=pareto_data["累计百分比"], name="累计百分比", yaxis="y2", marker_color='#ef4444', mode='lines+markers'))
        fig_pareto.update_layout(
            xaxis=dict(title="省份", tickangle=45),
            yaxis=dict(title="销售额(万元)", side="left"),
            yaxis2=dict(title="累计百分比 (%)", overlaying="y", side="right", range=[0, 110]),
            plot_bgcolor='rgba(0,0,0,0)', height=500
        )
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.info("无数据")

# 城市销售额排行 + 客单价分布
col_g, col_h = st.columns(2)
with col_g:
    st.markdown('<div class="section-header">🏙️ 城市销售额排行 TOP20</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        city_sale = df_o_curr[df_o_curr["城市_订单"] != ""].groupby("城市_订单")["订单金额"].sum().reset_index()
        city_sale["万元"] = city_sale["订单金额"] / 10000
        city_sale = city_sale.sort_values("万元", ascending=False).head(20)
        fig_city = px.bar(city_sale, x="万元", y="城市_订单", orientation='h',
                          color="万元", color_continuous_scale="Oranges", text="万元")
        fig_city.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig_city.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_city, use_container_width=True)
    else:
        st.info("无数据")
with col_h:
    st.markdown('<div class="section-header">💵 客单价分布</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        fig_hist = px.histogram(df_o_curr, x="订单金额", nbins=30, title="订单金额分布（元）",
                                labels={"订单金额": "订单金额（元）"}, color_discrete_sequence=['#10b981'])
        fig_hist.update_layout(plot_bgcolor='rgba(0,0,0,0)', bargap=0.05, height=500)
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("无订单数据")

# 地理热力地图
st.markdown('<div class="section-header">🗺️ 地理热力地图（省份销售额气泡图）</div>', unsafe_allow_html=True)
if not df_o_curr.empty:
    map_prov_sale = df_o_curr.groupby("省份_订单")["订单金额"].sum().reset_index()
    map_prov_sale = map_prov_sale[map_prov_sale["省份_订单"].notna() & (map_prov_sale["省份_订单"] != "")]
    map_prov_sale = map_prov_sale[map_prov_sale["省份_订单"].isin(STANDARD_PROVINCES)]
    map_prov_sale["万元"] = map_prov_sale["订单金额"] / 10000
    map_prov_sale["经度"] = map_prov_sale["省份_订单"].apply(lambda x: PROVINCE_CENTER.get(x, [None, None])[0])
    map_prov_sale["纬度"] = map_prov_sale["省份_订单"].apply(lambda x: PROVINCE_CENTER.get(x, [None, None])[1])
    map_prov_sale = map_prov_sale.dropna(subset=["经度", "纬度"])
    if not map_prov_sale.empty:
        fig_map = px.scatter_geo(map_prov_sale, lon="经度", lat="纬度", size="万元", hover_name="省份_订单",
                                 text="省份_订单", size_max=60, projection="natural earth",
                                 title="气泡大小代表销售额(万元)", color="万元", color_continuous_scale="Viridis")
        fig_map.update_layout(geo=dict(showframe=False, showcoastlines=True), height=500)
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("无法匹配坐标")
else:
    st.info("无省份销售额数据")


# ==================== 【第二部分：追加的新图表】====================
st.markdown("---")
st.markdown("### 📊 数据分析图表（新增）", unsafe_allow_html=True)

# 追加1：月度客资数与订单趋势
st.markdown('<div class="section-header">📅 月度客资数与订单数趋势</div>', unsafe_allow_html=True)
if not df_m_curr.empty and not df_o_curr.empty:
    monthly_leads = df_m_curr.groupby(df_m_curr["日期"].dt.to_period("M").astype(str)).size().reset_index(name="客资数")
    monthly_orders = df_o_curr.groupby(df_o_curr["日期"].dt.to_period("M").astype(str)).size().reset_index(name="订单数")
    monthly = monthly_leads.merge(monthly_orders, on="日期", how="outer").fillna(0)
    monthly = monthly.sort_values("日期")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(x=monthly["日期"], y=monthly["客资数"], name="客资数", marker_color='#3b82f6', yaxis="y"))
    fig_trend.add_trace(go.Bar(x=monthly["日期"], y=monthly["订单数"], name="订单数", marker_color='#f97316', yaxis="y2"))
    fig_trend.update_layout(
        barmode='group',
        yaxis=dict(title="客资数", side="left"),
        yaxis2=dict(title="订单数", overlaying="y", side="right"),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_tickangle=-45,
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=20, r=20, t=40, b=60),
        height=450
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("无数据")

# 追加2：品类客资占比 + 品类订单金额占比
col_i, col_j = st.columns(2)
with col_i:
    st.markdown('<div class="section-header">🍩 品类客资量占比</div>', unsafe_allow_html=True)
    if not df_m_curr.empty:
        cat_leads = df_m_curr.groupby("品类").size().reset_index(name="客资数")
        fig_cat_leads_pie = px.pie(cat_leads, names="品类", values="客资数", title="品类客资占比",
                                    color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_cat_leads_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat_leads_pie, use_container_width=True)
    else:
        st.info("无客资数据")
with col_j:
    st.markdown('<div class="section-header">🍩 品类订单金额占比</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        cat_sale_new = df_o_curr.groupby("品类")["订单金额"].sum().reset_index()
        fig_cat_sale_pie = px.pie(cat_sale_new, names="品类", values="订单金额", title="品类销售额占比",
                                   color_discrete_sequence=px.colors.qualitative.Set3)
        fig_cat_sale_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat_sale_pie, use_container_width=True)
    else:
        st.info("无订单数据")

# 追加3：运营中心客资量 TOP15 + 转化率 TOP15
col_k, col_l = st.columns(2)
with col_k:
    st.markdown('<div class="section-header">🏢 运营中心客资量 TOP15</div>', unsafe_allow_html=True)
    if not df_m_curr.empty:
        center_leads_new = df_m_curr.groupby("运营中心").size().reset_index(name="客资数")
        center_leads_new = center_leads_new.sort_values("客资数", ascending=False).head(15)
        fig_center_leads_new = px.bar(center_leads_new, x="客资数", y="运营中心", orientation='h',
                                      color="客资数", color_continuous_scale="Blues", text="客资数")
        fig_center_leads_new.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_center_leads_new.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_center_leads_new, use_container_width=True)
    else:
        st.info("无客资数据")
with col_l:
    st.markdown('<div class="section-header">📊 运营中心转化率 TOP15</div>', unsafe_allow_html=True)
    if not df_m_curr.empty and not df_o_curr.empty:
        center_leads_all = df_m_curr.groupby("运营中心").size().reset_index(name="客资数")
        center_orders_all = df_o_curr.groupby("运营中心").size().reset_index(name="订单数")
        center_conv = center_leads_all.merge(center_orders_all, on="运营中心", how="left").fillna(0)
        center_conv["转化率"] = center_conv["订单数"] / center_conv["客资数"] * 100
        center_conv = center_conv[center_conv["客资数"] >= 10].sort_values("转化率", ascending=False).head(15)
        fig_conv_new = px.bar(center_conv, x="转化率", y="运营中心", orientation='h',
                              color="转化率", color_continuous_scale="Greens",
                              text=center_conv["转化率"].apply(lambda x: f"{x:.1f}%"))
        fig_conv_new.update_traces(textposition='outside')
        fig_conv_new.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_conv_new, use_container_width=True)
    else:
        st.info("无数据")

# 追加4：品牌客资量 TOP15 + 品牌转化率 TOP15
col_m, col_n = st.columns(2)
with col_m:
    st.markdown('<div class="section-header">🏷️ 品牌客资量 TOP15</div>', unsafe_allow_html=True)
    if not df_m_curr.empty:
        brand_leads_new = df_m_curr.groupby("品牌").size().reset_index(name="客资数")
        brand_leads_new = brand_leads_new.sort_values("客资数", ascending=False).head(15)
        fig_brand_leads_new = px.bar(brand_leads_new, x="客资数", y="品牌", orientation='h',
                                     color="客资数", color_continuous_scale="Purples", text="客资数")
        fig_brand_leads_new.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_brand_leads_new.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_brand_leads_new, use_container_width=True)
    else:
        st.info("无客资数据")
with col_n:
    st.markdown('<div class="section-header">📊 品牌转化率 TOP15</div>', unsafe_allow_html=True)
    if not df_m_curr.empty and not df_o_curr.empty:
        brand_leads_all = df_m_curr.groupby("品牌").size().reset_index(name="客资数")
        brand_orders_all = df_o_curr.groupby("品牌").size().reset_index(name="订单数")
        brand_conv = brand_leads_all.merge(brand_orders_all, on="品牌", how="left").fillna(0)
        brand_conv["转化率"] = brand_conv["订单数"] / brand_conv["客资数"] * 100
        brand_conv = brand_conv[brand_conv["客资数"] >= 10].sort_values("转化率", ascending=False).head(15)
        fig_brand_conv_new = px.bar(brand_conv, x="转化率", y="品牌", orientation='h',
                                    color="转化率", color_continuous_scale="Oranges",
                                    text=brand_conv["转化率"].apply(lambda x: f"{x:.1f}%"))
        fig_brand_conv_new.update_traces(textposition='outside')
        fig_brand_conv_new.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_brand_conv_new, use_container_width=True)
    else:
        st.info("无数据")

# 追加5：月度品类订单数对比
st.markdown('<div class="section-header">📅 月度品类订单数对比</div>', unsafe_allow_html=True)
if not df_o_curr.empty:
    monthly_cat = df_o_curr.groupby([df_o_curr["日期"].dt.to_period("M").astype(str), "品类"]).size().reset_index(name="订单数")
    monthly_cat.columns = ["月份", "品类", "订单数"]
    monthly_cat = monthly_cat.sort_values("月份")
    cats = monthly_cat["品类"].unique()
    colors = px.colors.qualitative.Set2[:len(cats)] if len(cats) > 0 else ['#3b82f6']
    fig_cat_month = go.Figure()
    for i, cat in enumerate(cats):
        sub = monthly_cat[monthly_cat["品类"] == cat]
        fig_cat_month.add_trace(go.Bar(x=sub["月份"], y=sub["订单数"], name=cat, marker_color=colors[i % len(colors)]))
    fig_cat_month.update_layout(
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_tickangle=-45,
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=20, r=20, t=40, b=60),
        height=450
    )
    st.plotly_chart(fig_cat_month, use_container_width=True)
else:
    st.info("无订单数据")

# 追加6：省份客资量排行 + 城市销售额 TOP15
col_o, col_p = st.columns(2)
with col_o:
    st.markdown('<div class="section-header">🗺️ 省份客资量排行 TOP20</div>', unsafe_allow_html=True)
    if not df_m_curr.empty:
        prov_leads = df_m_curr.groupby("省份_客资").size().reset_index(name="客资数")
        prov_leads = prov_leads[prov_leads["省份_客资"].notna() & (prov_leads["省份_客资"] != "")]
        prov_leads = prov_leads[prov_leads["省份_客资"].isin(STANDARD_PROVINCES)]
        prov_leads = prov_leads.sort_values("客资数", ascending=False).head(20)
        fig_prov_leads = px.bar(prov_leads, x="客资数", y="省份_客资", orientation='h',
                                color="客资数", color_continuous_scale="Tealgrn", text="客资数")
        fig_prov_leads.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_prov_leads.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_prov_leads, use_container_width=True)
    else:
        st.info("无客资数据")
with col_p:
    st.markdown('<div class="section-header">🏙️ 城市销售额排行 TOP15</div>', unsafe_allow_html=True)
    if not df_o_curr.empty:
        city_sale_new = df_o_curr[df_o_curr["城市_订单"] != ""].groupby("城市_订单")["订单金额"].sum().reset_index()
        city_sale_new["万元"] = city_sale_new["订单金额"] / 10000
        city_sale_new = city_sale_new.sort_values("万元", ascending=False).head(15)
        fig_city_new = px.bar(city_sale_new, x="万元", y="城市_订单", orientation='h',
                              color="万元", color_continuous_scale="Oranges", text="万元")
        fig_city_new.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig_city_new.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_city_new, use_container_width=True)
    else:
        st.info("无订单数据")

# 追加7：全国运营中心分布热力图（气泡大小=客资数，颜色=转化率）
st.markdown('<div class="section-header">🗺️ 全国运营中心分布热力图（气泡大小=客资数，颜色=转化率）</div>', unsafe_allow_html=True)
if not df_m_curr.empty and not df_o_curr.empty:
    prov_leads_map = df_m_curr.groupby("省份_客资").size().reset_index(name="客资数")
    prov_orders_map = df_o_curr.groupby("省份_订单").size().reset_index(name="订单数")
    map_df = prov_leads_map.merge(prov_orders_map, left_on="省份_客资", right_on="省份_订单", how="left").fillna(0)
    map_df["转化率"] = map_df["订单数"] / map_df["客资数"] * 100
    prov_amount = df_o_curr.groupby("省份_订单")["订单金额"].sum().reset_index()
    prov_amount.columns = ["省份_客资", "订单金额"]
    prov_amount["万元"] = prov_amount["订单金额"] / 10000
    map_df = map_df.merge(prov_amount[["省份_客资", "万元"]], on="省份_客资", how="left").fillna(0)
    map_df.rename(columns={"万元": "销售额_万元"}, inplace=True)
    map_df["经度"] = map_df["省份_客资"].apply(lambda x: PROVINCE_CENTER.get(x, [None, None])[0])
    map_df["纬度"] = map_df["省份_客资"].apply(lambda x: PROVINCE_CENTER.get(x, [None, None])[1])
    map_df = map_df.dropna(subset=["经度", "纬度"])

    if not map_df.empty:
        fig_map_new = px.scatter_geo(
            map_df, lon="经度", lat="纬度",
            size="客资数", hover_name="省份_客资",
            text="省份_客资",
            size_max=60,
            projection="natural earth",
            color="转化率",
            color_continuous_scale="Viridis",
            title="气泡大小=客资数 | 颜色=转化率（越绿越高）"
        )
        fig_map_new.update_layout(
            geo=dict(showframe=False, showcoastlines=True, bgcolor='rgba(0,0,0,0)'),
            plot_bgcolor='rgba(0,0,0,0)',
            height=550
        )
        st.plotly_chart(fig_map_new, use_container_width=True)
    else:
        st.info("无法匹配坐标数据")
else:
    st.info("无足够数据生成地图")

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(f"<div style='text-align:center; color:#9ca3af; font-size:0.85rem;'>📊 天猫新零售数据看板 | 数据截至 {latest_date} | 共 {total_leads:,} 条客资 / {order_count:,} 笔订单 / {total_amount/10000:.2f} 万元</div>", unsafe_allow_html=True)
