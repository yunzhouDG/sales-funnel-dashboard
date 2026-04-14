"""
天猫新零售数据看板 - ECharts集成版
集成Plotly + ECharts双图表引擎，打造更美观的数据可视化
"""
import streamlit as st
import pandas as pd
import sqlite3
import zipfile
import tempfile
import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from streamlit_echarts import st_echarts

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
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #3b82f6, #7c3aed);
        border-radius: 4px 0 0 4px;
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
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(120deg, #1e40af, #7c3aed, #ec4899);
        background-size: 200% auto;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin-bottom: 0.2rem;
        animation: gradient_shift 3s ease infinite;
    }
    @keyframes gradient_shift {
        0% { background-position: 0% center; }
        50% { background-position: 100% center; }
        100% { background-position: 0% center; }
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1f2937;
        border-left: 5px solid;
        border-image: linear-gradient(180deg, #3b82f6, #7c3aed) 1;
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
    /* ECharts 容器样式 */
    .echarts-container {
        background: white;
        border-radius: 24px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        border: 1px solid #eef2f6;
    }
    /* 分隔线样式 */
    .section-divider {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    }
    .section-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .badge-plotly {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    .badge-echarts {
        background: linear-gradient(135deg, #f093fb, #f5576c);
        color: white;
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

CITY_CENTER = {
    '杭州市': [120.1551, 30.2741], '宁波市': [121.5495, 29.8683],
    '温州市': [120.6998, 28.0006], '成都市': [104.0668, 30.5728],
    '南京市': [118.7969, 32.0603], '苏州市': [120.5853, 31.2990],
    '广州市': [113.2644, 23.1291], '深圳市': [114.0579, 22.5431],
    '武汉市': [114.3055, 30.5931], '长沙市': [112.9388, 28.2282],
    '郑州市': [113.6254, 34.7466], '青岛市': [120.3826, 36.0671],
    '济南市': [117.0009, 36.6758], '天津市': [117.1902, 39.1256],
    '西安市': [108.9402, 34.3416], '重庆市': [106.5044, 29.5582],
    '福州市': [119.2965, 26.0745], '厦门市': [118.0894, 24.4798],
    '合肥市': [117.2272, 31.8206], '南昌市': [115.8582, 28.6820],
    '石家庄市': [114.4995, 38.1006], '太原市': [112.5624, 37.8735],
    '昆明市': [102.8329, 24.8801], '贵阳市': [106.6302, 26.6477],
    '南宁市': [108.3661, 22.8176], '海口市': [110.1999, 20.0440],
    '沈阳市': [123.4315, 41.8057], '大连市': [121.6147, 38.9140],
    '长春市': [125.3235, 43.8171], '哈尔滨市': [126.5364, 45.8022],
    '北京市': [116.4074, 39.9042], '上海市': [121.4737, 31.2304],
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

# ==================== 数据加载 ====================
@st.cache_data(ttl=3600)
def load_data():
    if not os.path.exists("data.zip"):
        st.error("❌ 未找到 data.zip 文件，请将数据文件放在应用同目录下")
        st.stop()
    with zipfile.ZipFile("data.zip", "r") as zf:
        db_files = [f for f in zf.namelist() if f.endswith(".db")]
        if not db_files:
            st.error("❌ 压缩包中未找到 .db 文件")
            st.stop()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            with zf.open(db_files[0]) as f:
                tmp.write(f.read())
            tmp_path = tmp.name

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

# ==================== ECharts 图表构建函数 ====================
def get_category_pie_option(title, data, colors=None):
    """品类饼图 ECharts 配置"""
    if colors is None:
        colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3fb950', '#f7ba5e', '#9a60b4']
    option = {
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}
        },
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"bottom": 5, "textStyle": {"color": "#6b7280"}},
        "color": colors,
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": False,
            "itemStyle": {"borderRadius": 8, "borderColor": "#fff", "borderWidth": 2},
            "label": {"show": False},
            "emphasis": {
                "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
            },
            "labelLine": {"show": False},
            "data": [{"value": int(v), "name": k} for k, v in data.items()]
        }]
    }
    return option

def get_bar_line_option(title, x_data, series_data, y_names, colors=None):
    """柱状+折线组合图 ECharts 配置"""
    if colors is None:
        colors = ['#4a90e2', '#27ae60', '#e07050']
    series = []
    for i, (y_name, data) in enumerate(series_data.items()):
        if i == len(series_data) - 1:
            series.append({
                "name": y_name, "type": "line", "yAxisIndex": 1,
                "data": data, "smooth": True,
                "lineStyle": {"width": 3, "color": colors[i]},
                "itemStyle": {"color": colors[i]},
                "symbol": "circle", "symbolSize": 6
            })
        else:
            series.append({
                "name": y_name, "type": "bar",
                "data": data, "itemStyle": {"color": colors[i], "borderRadius": [4, 4, 0, 0]}
            })
    option = {
        "title": {
            "text": title, "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 0, "data": list(y_names), "textStyle": {"color": "#6b7280"}},
        "grid": {"left": 50, "right": 30, "bottom": 30, "top": 45},
        "xAxis": {
            "type": "category", "data": x_data,
            "axisLabel": {"color": "#4a4e57", "rotate": 30 if len(x_data) > 6 else 0}
        },
        "yAxis": [
            {"type": "value", "axisLabel": {"color": "#606776"}, "splitLine": {"lineStyle": {"color": "#ebeef5"}}},
            {"type": "value", "axisLabel": {"color": "#606776", "formatter": "{value}%"}, "splitLine": {"show": False}}
        ],
        "series": series
    }
    return option

def get_bar_horizontal_option(title, data, value_name, color_start="#4a90e2", color_end="#7c3aed"):
    """横向柱状图 ECharts 配置"""
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:15]
    categories = [item[0] for item in sorted_data]
    values = [int(item[1]) for item in sorted_data]
    option = {
        "title": {
            "text": title, "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": f"{{b}}: {{c}} {value_name}"},
        "grid": {"left": 120, "right": 60, "bottom": 20, "top": 30},
        "xAxis": {
            "type": "value",
            "axisLabel": {"color": "#606776"},
            "splitLine": {"lineStyle": {"color": "#ebeef5"}}
        },
        "yAxis": {
            "type": "category", "data": list(reversed(categories)),
            "axisLabel": {"color": "#4a4e57", "fontSize": 11}
        },
        "series": [{
            "type": "bar", "data": values,
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [{"offset": 0, "color": color_start}, {"offset": 1, "color": color_end}]
                },
                "borderRadius": [0, 4, 4, 0]
            },
            "barMaxWidth": 24
        }]
    }
    return option

def get_map_option(title, map_data, size_key, color_key):
    """地图热力图 ECharts 配置"""
    geo_coord_map = {**PROVINCE_CENTER, **CITY_CENTER}
    convert_data = []
    for name, val in map_data.items():
        if name in geo_coord_map:
            convert_data.append({
                "name": name,
                "value": geo_coord_map[name] + [val.get(size_key, 0), val.get(color_key, 0)]
            })
    option = {
        "title": {
            "text": title, "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}
        },
        "tooltip": {
            "trigger": "item",
            "formatter": lambda p: f"{p.name}<br/>客资数: {p.value[2]}<br/>转化率: {p.value[3]}%" if len(p.value) > 3 else p.name
        },
        "geo": {
            "map": "china",
            "roam": True,
            "zoom": 1.2,
            "itemStyle": {
                "areaColor": "#e8f4ff",
                "borderColor": "#a0c4e8",
                "borderWidth": 1
            },
            "emphasis": {
                "itemStyle": {"areaColor": "#c8e6ff"}
            },
            "label": {"show": False}
        },
        "series": [{
            "type": "effectScatter",
            "coordinateSystem": "geo",
            "data": convert_data,
            "symbolSize": lambda v: max(8, min(40, v[2] / 100)),
            "itemStyle": {
                "color": {
                    "type": "radial",
                    "x": 0.5, "y": 0.5, "r": 0.5,
                    "colorStops": [
                        {"offset": 0, "color": "#27ae60"},
                        {"offset": 1, "color": "#0d6e3f"}
                    ]
                }
            },
            "emphasis": {"scale": 1.5},
            "rippleEffect": {"brushType": "stroke", "scale": 3}
        }]
    }
    return option

def get_funnel_option(title, data):
    """漏斗图 ECharts 配置"""
    colors = ['#4a90e2', '#73c0de', '#3fb950', '#f7ba5e', '#ee6666']
    option = {
        "title": {
            "text": title, "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}
        },
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
        "legend": {"bottom": 5, "textStyle": {"color": "#6b7280"}},
        "color": colors,
        "series": [{
            "type": "funnel",
            "left": "10%", "top": 30, "bottom": 50, "width": "80%",
            "min": 0, "max": data[0][1] if data else 1,
            "minSize": "0%", "maxSize": "100%",
            "gap": 3,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2, "borderRadius": 4},
            "label": {"show": True, "position": "inside", "formatter": "{b}\n{c}", "fontSize": 12},
            "data": [{"value": int(v), "name": n} for n, v in data]
        }]
    }
    return option

# ==================== 主程序 ====================
df_main, df_order = load_data()
if df_main.empty:
    st.error("客资明细表为空")
    st.stop()

df_main["省份_客资"] = df_main["省份_raw"].apply(extract_province_from_raw)
df_main["城市_客资"] = df_main["城市_raw"]
df_order["省份_订单"] = df_order["省份_raw"].apply(extract_province_from_raw)
df_order["城市_订单"] = df_order["城市_raw"]

# 筛选器选项
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

# 应用筛选
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
conversion_rate = (order_count / valid_leads * 100) if valid_leads > 0 else 0

# 页面标题
latest_date = max_date.strftime("%Y年%m月%d日") if not df_main["日期"].isna().all() else "未知"
st.markdown('<div class="dashboard-title">🏬 天猫新零售数据看板</div>', unsafe_allow_html=True)
st.markdown(f"<div style='color:#4b5563; margin-bottom:1rem;'>数据更新至 {latest_date} · <span class='section-badge badge-echarts'>✨ ECharts</span></div>", unsafe_allow_html=True)

# KPI 卡片
total_wan = total_amount / 10000
c1, c2, c3, c4 = st.columns(4)
kpi_data = [
    ("📋 总客资", f"{total_leads:,}", c1),
    ("✅ 有效客资", f"{valid_leads:,}", c2),
    ("🛒 成交单量", f"{order_count:,}", c3),
    ("💰 总金额", f"{total_wan:.2f} 万", c4),
]
for label, value, col in kpi_data:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

# ==================== 第一部分：Plotly 图表 ====================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown(f'### 📊 Plotly 图表 <span class="section-badge badge-plotly">经典版</span>', unsafe_allow_html=True)

# 日客资趋势
st.markdown('<div class="section-header">📅 日客资数趋势</div>', unsafe_allow_html=True)
if not df_m.empty and "日期" in df_m.columns:
    daily_leads = df_m.groupby(df_m["日期"].dt.date).size().reset_index(name="客资数")
    daily_leads["日期_中文"] = daily_leads["日期"].apply(lambda d: d.strftime("%m-%d"))
    fig_daily = px.bar(daily_leads, x="日期_中文", y="客资数", text="客资数",
                       color_discrete_sequence=['#3b82f6'], title="每日客资数量")
    fig_daily.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_daily.update_layout(plot_bgcolor='rgba(0,0,0,0)', xaxis_tickangle=-30, height=400,
                           margin=dict(l=20, r=20, t=40, b=80))
    st.plotly_chart(fig_daily, use_container_width=True)

# 品牌对比 + 运营中心客资
col_a, col_b = st.columns(2)
with col_a:
    st.markdown('<div class="section-header">🏷️ 品牌客资量与订单金额对比</div>', unsafe_allow_html=True)
    if not df_m.empty and not df_o.empty:
        brand_leads = df_m.groupby("品牌").size().reset_index(name="客资量")
        brand_amount = df_o.groupby("品牌")["订单金额"].sum().reset_index()
        brand_comp = brand_leads.merge(brand_amount, on="品牌", how="outer").fillna(0)
        brand_comp = brand_comp.sort_values("客资量", ascending=False).head(10)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(x=brand_comp["品牌"], y=brand_comp["客资量"], name="客资量", marker_color='#3b82f6'))
        fig_comp.add_trace(go.Bar(x=brand_comp["品牌"], y=brand_comp["订单金额"], name="订单金额", marker_color='#f97316'))
        fig_comp.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', xaxis_tickangle=-45)
        st.plotly_chart(fig_comp, use_container_width=True)
with col_b:
    st.markdown('<div class="section-header">🏢 运营中心客资量 TOP10</div>', unsafe_allow_html=True)
    if not df_m.empty:
        center_leads = df_m.groupby("运营中心").size().reset_index(name="客资量")
        center_leads = center_leads.sort_values("客资量", ascending=False).head(10)
        fig_center = px.bar(center_leads, x="客资量", y="运营中心", orientation='h',
                           color="客资量", color_continuous_scale="Blues")
        fig_center.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=400)
        st.plotly_chart(fig_center, use_container_width=True)

# ==================== 第二部分：ECharts 图表 ====================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown(f'### 🎨 ECharts 图表 <span class="section-badge badge-echarts">精美增强版</span>', unsafe_allow_html=True)

# 月度客资与订单趋势
st.markdown('<div class="section-header">📈 月度客资与订单趋势</div>', unsafe_allow_html=True)
if not df_m.empty and "日期" in df_m.columns:
    df_m["年月"] = df_m["日期"].dt.to_period("M").astype(str)
    df_o["年月"] = df_o["日期"].dt.to_period("M").astype(str)
    monthly_leads = df_m.groupby("年月").size()
    monthly_orders = df_o.groupby("年月").size()
    all_months = sorted(set(monthly_leads.index) | set(monthly_orders.index))
    leads_vals = [monthly_leads.get(m, 0) for m in all_months]
    orders_vals = [monthly_orders.get(m, 0) for m in all_months]
    conversion_vals = [round(orders_vals[i] / leads_vals[i] * 100, 2) if leads_vals[i] > 0 else 0 for i in range(len(all_months))]
    month_chart = get_bar_line_option(
        "月度客资数与订单数趋势",
        all_months,
        {"客资数": leads_vals, "订单数": orders_vals, "转化率(%)": conversion_vals},
        ["客资数", "订单数", "转化率(%)"],
        ["#4a90e2", "#27ae60", "#e07050"]
    )
    st_echarts(month_chart, height="400px")

# 品类饼图
col_e1, col_e2 = st.columns(2)
with col_e1:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_m.empty:
        cat_leads = df_m.groupby("品类").size().to_dict()
        pie_option = get_category_pie_option("品类客资量占比", cat_leads)
        st_echarts(pie_option, height="350px")
    st.markdown('</div>', unsafe_allow_html=True)
with col_e2:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_o.empty:
        cat_amount = df_o.groupby("品类")["订单金额"].sum().to_dict()
        pie_option2 = get_category_pie_option("品类订单金额占比", cat_amount,
                                               ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'])
        st_echarts(pie_option2, height="350px")
    st.markdown('</div>', unsafe_allow_html=True)

# 运营中心分析
col_e3, col_e4 = st.columns(2)
with col_e3:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_m.empty:
        center_data = df_m.groupby("运营中心").size().to_dict()
        bar_opt = get_bar_horizontal_option("运营中心客资量 TOP15", center_data, "客资", "#4a90e2", "#7c3aed")
        st_echarts(bar_opt, height="400px")
    st.markdown('</div>', unsafe_allow_html=True)
with col_e4:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_m.empty and not df_o.empty:
        center_leads2 = df_m.groupby("运营中心").size()
        center_orders2 = df_o.groupby("运营中心").size()
        center_conv = {}
        for c in center_leads2.index:
            l = center_leads2.get(c, 0)
            o = center_orders2.get(c, 0)
            center_conv[c] = round(o / l * 100, 2) if l > 0 else 0
        sorted_conv = dict(sorted(center_conv.items(), key=lambda x: x[1], reverse=True)[:15])
        bar_opt2 = get_bar_horizontal_option("运营中心转化率 TOP15", sorted_conv, "%", "#27ae60", "#10b981")
        st_echarts(bar_opt2, height="400px")
    st.markdown('</div>', unsafe_allow_html=True)

# 品牌分析
col_e5, col_e6 = st.columns(2)
with col_e5:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_m.empty:
        brand_data = df_m.groupby("品牌").size().to_dict()
        bar_opt3 = get_bar_horizontal_option("品牌客资量 TOP15", brand_data, "客资", "#f093fb", "#f5576c")
        st_echarts(bar_opt3, height="400px")
    st.markdown('</div>', unsafe_allow_html=True)
with col_e6:
    st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
    if not df_m.empty and not df_o.empty:
        brand_leads2 = df_m.groupby("品牌").size()
        brand_orders2 = df_o.groupby("品牌").size()
        brand_conv = {}
        for b in brand_leads2.index:
            l = brand_leads2.get(b, 0)
            o = brand_orders2.get(b, 0)
            brand_conv[b] = round(o / l * 100, 2) if l > 0 else 0
        sorted_brand_conv = dict(sorted(brand_conv.items(), key=lambda x: x[1], reverse=True)[:15])
        bar_opt4 = get_bar_horizontal_option("品牌转化率 TOP15", sorted_brand_conv, "%", "#e07050", "#ee6666")
        st_echarts(bar_opt4, height="400px")
    st.markdown('</div>', unsafe_allow_html=True)

# 转化漏斗
st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">📉 转化漏斗</div>', unsafe_allow_html=True)
valid_mask_curr = df_m["外呼状态"].isin(["高意向", "低意向", "无需外呼"])
assigned = df_m[valid_mask_curr & (df_m["最新跟进状态"] != "未分配")].shape[0] if "最新跟进状态" in df_m.columns else 0
followed = df_m[valid_mask_curr & (~df_m["最新跟进状态"].isin(["未分配", "待查看", "待联系"]))].shape[0] if "最新跟进状态" in df_m.columns else 0
funnel_data = [
    ("总客资", total_leads), ("有效客资", valid_leads), ("已分配", assigned), ("已跟进", followed), ("成交", order_count)
]
funnel_opt = get_funnel_option("客户转化漏斗", funnel_data)
st_echarts(funnel_opt, height="400px")
st.markdown('</div>', unsafe_allow_html=True)

# 省份客资 TOP20
st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">🗺️ 省份客资量排行 TOP20</div>', unsafe_allow_html=True)
if not df_m.empty:
    province_data = df_m.groupby("省份_客资").size()
    province_data = province_data[province_data.index.isin(STANDARD_PROVINCES)]
    province_dict = province_data.to_dict()
    bar_opt5 = get_bar_horizontal_option("省份客资量 TOP20", province_dict, "客资", "#4facfe", "#00f2fe")
    st_echarts(bar_opt5, height="500px")
st.markdown('</div>', unsafe_allow_html=True)

# 城市销售额 TOP15
st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">🏙️ 城市销售额 TOP15</div>', unsafe_allow_html=True)
if not df_o.empty:
    city_amount = df_o.groupby("城市_订单")["订单金额"].sum()
    city_amount = city_amount[city_amount.index != ""].sort_values(ascending=False).head(15)
    city_dict = (city_amount / 10000).round(1).to_dict()
    bar_opt6 = get_bar_horizontal_option("城市销售额(万元) TOP15", city_dict, "万元", "#f7ba5e", "#f093fb")
    st_echarts(bar_opt6, height="400px")
st.markdown('</div>', unsafe_allow_html=True)

# 地理热力地图
st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">🌍 全国运营中心分布热力图</div>', unsafe_allow_html=True)
if not df_m.empty and not df_o.empty:
    center_leads3 = df_m.groupby("运营中心").size()
    center_orders3 = df_o.groupby("运营中心").size()
    map_data = {}
    for c in center_leads3.index:
        l = center_leads3.get(c, 0)
        o = center_orders3.get(c, 0)
        if l > 0 and c in CITY_CENTER:
            map_data[c] = {"客资数": int(l), "转化率": round(o / l * 100, 2)}
    if map_data:
        map_opt = get_map_option("全国运营中心客资热力（气泡大小=客资，颜色=转化率）", map_data, "客资数", "转化率")
        st_echarts(map_opt, height="500px")
    else:
        st.info("无有效的运营中心地理位置数据")
else:
    st.info("无数据")
st.markdown('</div>', unsafe_allow_html=True)

# 月度品类对比
st.markdown('<div class="echarts-container">', unsafe_allow_html=True)
st.markdown('<div class="section-header">📊 月度品类订单对比</div>', unsafe_allow_html=True)
if not df_o.empty and "年月" in df_o.columns:
    cats = df_o["品类"].dropna().unique()
    months = sorted(df_o["年月"].unique())
    series_data = {}
    for cat in cats:
        series_data[cat] = [int(df_o[(df_o["年月"] == m) & (df_o["品类"] == cat)].shape[0]) for m in months]
    cat_bar_opt = {
        "title": {"text": "月度品类订单数对比", "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "600", "color": "#1f2937"}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 0, "data": list(cats), "textStyle": {"color": "#6b7280"}},
        "grid": {"left": 50, "right": 20, "bottom": 30, "top": 45},
        "xAxis": {"type": "category", "data": months, "axisLabel": {"color": "#4a4e57"}},
        "yAxis": {"type": "value", "axisLabel": {"color": "#606776"}, "splitLine": {"lineStyle": {"color": "#ebeef5"}}},
        "series": [
            {"name": cat, "type": "bar", "data": vals, "stack": "total",
             "itemStyle": {"borderRadius": [0, 0, 0, 0]}}
            for cat, vals in series_data.items()
        ]
    }
    st_echarts(cat_bar_opt, height="400px")
st.markdown('</div>', unsafe_allow_html=True)

# 页脚
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
     border-radius: 20px; color: white; margin-top: 2rem;">
    <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">📊 天猫新零售数据看板</div>
    <div style="font-size: 0.85rem; opacity: 0.9;">整合 Plotly + ECharts 双引擎 · 数据驱动决策</div>
</div>
""", unsafe_allow_html=True)
