import streamlit as st
import pandas as pd
import os
from io import BytesIO

# --- 1. 页面配置与高端 UI 样式 ---
st.set_page_config(page_title="MDC 智能仓储数智看板V1", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .total-card {
        background: linear-gradient(135deg, #3A1C71 0%, #D76D77 50%, #FFAF7B 100%);
        padding: 25px; border-radius: 15px; color: white; text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2); margin-bottom: 20px;
    }
    .wh-card {
        background: linear-gradient(135deg, #1D976C 0%, #93F9B9 100%);
        padding: 15px; border-radius: 12px; color: #1a1a1a; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s;
    }
    .wh-card:hover { transform: translateY(-5px); }
    .pillar-line {
        border-left: 2px dashed #999; height: 500px; 
        margin: 0 auto; opacity: 0.6;
    }
    /* 侧边栏统计样式 */
    .sidebar-stat {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1D976C;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 高性能数据加载引擎 ---
@st.cache_data(ttl=600)
def load_optimized_data():
    file_name = "SGF.csv" 
    if not os.path.exists(file_name):
        return None, None
    try:
        df_raw = pd.read_csv(file_name, usecols=[0, 6, 9, 11, 12, 13, 14], low_memory=False)
        df_raw.columns = ['SKU', 'RawLoc', 'Qty', 'L', 'W', 'H', 'Status']
        
        df = df_raw[df_raw['RawLoc'].str.len() >= 6].copy()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        df['Vol_m3'] = (pd.to_numeric(df['L'], errors='coerce').fillna(0) * pd.to_numeric(df['W'], errors='coerce').fillna(0) * pd.to_numeric(df['H'], errors='coerce').fillna(0)) / 1_000_000
        
        loc_map = {}
        for _, row in df.iterrows():
            raw_val = str(row['RawLoc'])
            loc = f"{raw_val[0:3]}-{raw_val[3:5]}-{raw_val[5:7]}"
            if loc not in loc_map:
                loc_map[loc] = {
                    'WH': raw_val[0].upper(),
                    'Aisle': raw_val[0:3],
                    'Col': raw_val[3:5],
                    'Vol': row['Vol_m3'],
                    'Status': row['Status'],
                    'Items': []
                }
            if row['Qty'] > 0:
                loc_map[loc]['Items'].append(f"• {row['SKU']}: {int(row['Qty'])}")
        return loc_map, df
    except Exception as e:
        st.error(f"数据解析错误: {e}")
        return None, None

loc_map, raw_df = load_optimized_data()

# --- 3. 渲染引擎 ---
def render_optimized_shelf(cols, title, split_size, wh):
    if not cols: return
    st.markdown(f"#### 📍 {title}")
    levels = ["50", "40", "30", "20", "10", "00"] if wh == 'A' else ["40", "30", "20", "10", "00"]
    dseq = ["PILLAR"]
    for i, c in enumerate(cols):
        dseq.append(c)
        if (i + 1) % split_size == 0: dseq.append("PILLAR")
    if dseq[-1] != "PILLAR": dseq.append("PILLAR")

    st_cols = st.columns(len(dseq))
    for i, item in enumerate(dseq):
        with st_cols[i]:
            if item == "PILLAR":
                st.markdown('<div class="pillar-line"></div>', unsafe_allow_html=True)
            else:
                for lvl in levels:
                    loc_id = f"{sel_aisle}-{item}-{lvl}"
                    data = loc_map.get(loc_id)
                    if not data:
                        st.button("➖", key=loc_id, disabled=True, use_container_width=True)
                    elif data['Status'] in ['柱子', '消防栓']:
                        st.button("🚫", key=loc_id, help=data['Status'], disabled=True, use_container_width=True)
                    elif len(data['Items']) > 0:
                        st.button(f"🟦{lvl}", key=loc_id, help="\n".join(data['Items']), use_container_width=True)
                    else:
                        st.button(f"🟩{lvl}", key=loc_id, help=f"容积: {data['Vol']:.3f}m³\n状态: 空闲", use_container_width=True)
                st.markdown(f'<div style="text-align:center;font-weight:bold;font-size:13px;padding-top:8px;">{item}位</div>', unsafe_allow_html=True)

# --- 4. 页面主体渲染 ---
if loc_map:
    all_locs_list = list(loc_map.values())
    unique_available = [item for item in all_locs_list if item['Status'] == '可用']
    
    # 顶部统计
    grand_total_v = sum(item['Vol'] for item in unique_available)
    grand_used_v = sum(item['Vol'] for item in unique_available if len(item['Items']) > 0)
    grand_ratio = (grand_used_v / grand_total_v * 100) if grand_total_v > 0 else 0

    st.markdown('<h1 style="color:#2c3e50;">MDC 全仓库总体库容监控中心</h1>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.markdown(f'<div class="total-card"><div style="font-size:1.2rem;">全库总占比</div><div style="font-size:3.5rem;font-weight:800;">{grand_ratio:.1f}%</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="total-card"><div style="font-size:1.2rem;">容积统计 (m³)</div><div style="font-size:2.2rem;font-weight:700;margin-top:10px;">{grand_used_v:.1f} / {grand_total_v:.1f}</div><div style="font-size:0.9rem;">已用 / 总可用</div></div>', unsafe_allow_html=True)

    # 仓库卡片展示
    wh_list = ['A', 'B', 'C', 'D', 'E']
    h_cols = st.columns(5)
    for i, wh in enumerate(wh_list):
        wh_data = [item for item in unique_available if item['WH'] == wh]
        t_v = sum(item['Vol'] for item in wh_data)
        u_v = sum(item['Vol'] for item in wh_data if len(item['Items']) > 0)
        r = (u_v / t_v * 100) if t_v > 0 else 0
        with h_cols[i]:
            st.markdown(f'<div class="wh-card"><div style="font-weight:800;">{wh} 库</div><div style="font-size:1.8rem;font-weight:700;color:#0d47a1;">{r:.1f}%</div><div style="font-size:0.8rem;border-top:1px solid rgba(0,0,0,0.1);padding-top:5px;">{u_v:.1f} / {t_v:.1f} m³</div></div>', unsafe_allow_html=True)

    st.divider()

    # --- 5. 侧边栏：控制与实时统计 ---
    st.sidebar.header("⚙️ 控制面板")
    
    # --- A. 库区筛选 ---
    sel_wh = st.sidebar.selectbox("📂 选择库房", wh_list)
    
    # --- B. 实时动态统计板块 (新增) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"📊 {sel_wh} 库实时统计")
    
    # 计算当前选中库的数据
    curr_wh_locs = [item for item in unique_available if item['WH'] == sel_wh]
    total_loc_count = len(curr_wh_locs)
    used_loc_count = len([item for item in curr_wh_locs if len(item['Items']) > 0])
    empty_loc_count = total_loc_count - used_loc_count
    loc_utilization = (used_loc_count / total_loc_count * 100) if total_loc_count > 0 else 0
    
    # 在侧边栏渲染精美小卡片
    st.sidebar.markdown(f"""
        <div class="sidebar-stat">
            <div style="font-size:0.85rem;color:#666;">可用库位总数</div>
            <div style="font-size:1.4rem;font-weight:bold;color:#1E3A8A;">{total_loc_count} <span style="font-size:0.8rem;">个</span></div>
        </div>
        <div class="sidebar-stat" style="border-left-color: #D76D77;">
            <div style="font-size:0.85rem;color:#666;">已使用库位</div>
            <div style="font-size:1.4rem;font-weight:bold;color:#D76D77;">{used_loc_count} <span style="font-size:0.8rem;">个</span></div>
        </div>
        <div class="sidebar-stat" style="border-left-color: #93F9B9;">
            <div style="font-size:0.85rem;color:#666;">空闲库位</div>
            <div style="font-size:1.4rem;font-weight:bold;color:#1D976C;">{empty_loc_count} <span style="font-size:0.8rem;">个</span></div>
        </div>
        <div class="sidebar-stat" style="border-left-color: #FFAF7B;">
            <div style="font-size:0.85rem;color:#666;">库位利用率</div>
            <div style="font-size:1.4rem;font-weight:bold;color:#2c3e50;">{loc_utilization:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

    # --- C. 导出与货道选择 ---
    st.sidebar.markdown("---")
    aisles = sorted(list(set(item['Aisle'] for item in all_locs_list if item['WH'] == sel_wh)))
    sel_aisle = st.sidebar.selectbox("🛣️ 选择货道", aisles)

    # 导出按钮
    empty_locs_data = [{'库位名称': k, '仓库': v['WH']} for k, v in loc_map.items() if v['Status'] == '可用' and len(v['Items']) == 0]
    if empty_locs_data:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(empty_locs_data).sort_values(by=['仓库', '库位名称']).to_excel(writer, index=False, sheet_name='空库位')
        st.sidebar.download_button(label="📥 导出全库空位 (Excel)", data=output.getvalue(), file_name="MDC_空库位清单.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- 6. 货架视图展示 ---
    current_cols = sorted(list(set(item['Col'] for item in all_locs_list if item['Aisle'] == sel_aisle)))
    if sel_wh == 'A':
        render_optimized_shelf([c for c in current_cols if int(c) <= 24], "东区", 3, 'A')
        render_optimized_shelf([c for c in current_cols if 25 <= int(c) <= 48], "中区", 3, 'A')
        render_optimized_shelf([c for c in current_cols if 49 <= int(c) <= 72], "西区", 3, 'A')
    elif sel_wh == 'B':
        render_optimized_shelf([c for c in current_cols if int(c) <= 20], "东区", 2, 'B')
        render_optimized_shelf([c for c in current_cols if 21 <= int(c) <= 40], "中区", 2, 'B')
        render_optimized_shelf([c for c in current_cols if 41 <= int(c) <= 60], "西区", 2, 'B')
    else:
        render_optimized_shelf([c for c in current_cols if int(c) <= 22], "东区", 2, sel_wh)
        render_optimized_shelf([c for c in current_cols if int(c) > 22], "西区", 2, sel_wh)
else:
    st.warning("⚠️ 无法加载数据。")