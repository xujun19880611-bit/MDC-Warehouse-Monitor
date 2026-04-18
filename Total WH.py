import streamlit as st
import pandas as pd
import os
from io import BytesIO

# --- 1. 页面配置与 UI 样式 ---
st.set_page_config(page_title="MDC 智能仓储监控中心", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .total-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 15px; border-radius: 10px; color: white; text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    .wh-stat-card {
        background: white; padding: 10px; border-radius: 8px;
        border: 1px solid #e0e0e0; text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .wh-stat-title { font-weight: bold; color: #1e3c72; font-size: 16px; margin-bottom: 5px; }
    .wh-stat-val { color: #2ecc71; font-weight: bold; font-size: 18px; }

    /* 图例说明样式 */
    .legend-container {
        display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;
        background: white; padding: 12px; border-radius: 8px;
        border: 1px solid #eee; margin-bottom: 20px; font-size: 13px;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; }

    /* 货架结构与横梁/立柱 */
    .shelf-container {
        display: flex; flex-wrap: nowrap; justify-content: flex-start;
        gap: 0px; padding: 15px; overflow-x: auto; background: white;
        border-radius: 10px; border: 1px solid #eee; margin-bottom: 30px;
    }
    .bay-unit { display: flex; flex-direction: row; align-items: flex-start; }
    .bin-column { display: flex; flex-direction: column; align-items: center; width: 42px; flex-shrink: 0; }
    
    .bin-box {
        width: 36px; height: 30px; margin: 0px 0;
        display: flex; align-items: center; justify-content: center;
        border-radius: 2px; font-size: 10px; font-weight: bold;
        border: 1px solid #eee; z-index: 2; background-color: white;
    }
    
    .orange-beam-row {
        width: 100%; height: 4px; background-color: #ff9800; 
        margin: 2px 0; box-shadow: 0 1px 2px rgba(0,0,0,0.1); z-index: 5;
    }
    
    .pillar-tech-blue {
        width: 0; height: 210px; border-left: 4px dotted #3498db; 
        margin: 0 10px; opacity: 0.9; align-self: flex-start; margin-top: 5px;
    }

    .status-used { background-color: #3498db !important; color: white; border: none; }
    .status-empty { background-color: #2ecc71 !important; color: white; border: none; }
    .status-disabled { background-color: #95a5a6 !important; color: white; border: none; }
    .status-aisle { background-color: #f1c40f !important; color: #333; border: none; }
    .status-pillar { background-color: #7f8c8d !important; color: white; border: none; }

    .aisle-title { 
        background: #e9ecef; padding: 5px 15px; border-radius: 5px; 
        font-weight: bold; color: #495057; margin-top: 15px; margin-bottom: 8px; display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据处理引擎 ---
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("SGF.csv"):
        return None, None
    try:
        raw_df = pd.read_csv("SGF.csv", low_memory=False)
        df = raw_df.iloc[:, [0, 6, 9, 11, 12, 13, 14]].copy()
        df.columns = ['SKU', 'Loc', 'Qty', 'L', 'W', 'H', 'Status']
        
        df['Loc'] = df['Loc'].astype(str).str.strip()
        df['Status'] = df['Status'].astype(str).str.strip()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        for c in ['L','W','H']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Vol'] = (df['L'] * df['W'] * df['H']) / 1000000

        m_mask = (~df['Loc'].str.contains('-', na=False)) & (df['Loc'].str.startswith(('A','B','C','D','E'))) & (df['L']>0)
        master = df[m_mask].drop_duplicates('Loc')
        
        l_map, stats = {}, {wh: {'t_v':0.0, 'u_v':0.0, 'total_bins':0, 'used_bins':0} for wh in 'ABCDE'}
        
        for _, r in master.iterrows():
            wh = r['Loc'][0].upper()
            l_map[r['Loc']] = {
                'Items':[], 'Status':r['Status'], 'Vol':r['Vol'], 'WH':wh, 
                'Aisle':r['Loc'][0:3], 'Col':r['Loc'][3:5], 'Lvl':r['Loc'][5:7]
            }
            if r['Status'] == "可用": 
                stats[wh]['t_v'] += r['Vol']
                stats[wh]['total_bins'] += 1
        
        # 填充实时库存货物
        inv = df[df['Qty'] > 0]
        for _, r in inv.iterrows():
            if r['Loc'] in l_map: 
                l_map[r['Loc']]['Items'].append(f"{r['SKU']}:{int(r['Qty'])}")
        
        for k, v in l_map.items():
            if len(v['Items']) > 0 and v['Status'] == "可用": 
                stats[v['WH']]['u_v'] += v['Vol']
                stats[v['WH']]['used_bins'] += 1
                
        return l_map, stats
    except Exception as e:
        st.error(f"数据处理出错: {e}")
        return None, None

l_map, wh_stats = load_data()

# --- 3. 页面渲染逻辑 ---
if l_map:
    st.markdown('<h2 style="text-align:center; color:#1e3c72;">MDC 仓库实时监控看板</h2>', unsafe_allow_html=True)
    
    t_all = sum(s['t_v'] for s in wh_stats.values())
    u_all = sum(s['u_v'] for s in wh_stats.values())
    r_all = (u_all/t_all*100) if t_all>0 else 0
    st.markdown(f'<div class="total-card">全库容积利用率: <b>{r_all:.1f}%</b> &nbsp;&nbsp; | &nbsp;&nbsp; 已用: {u_all:.1f} m³ / 总可用: {t_all:.1f} m³</div>', unsafe_allow_html=True)

    # --- 侧边栏功能区 ---
    st.sidebar.header("⚙️ 监控工具")
    wh_sel = st.sidebar.selectbox("切换库房视图", ['A','B','C','D','E'])
    
    curr_data = wh_stats[wh_sel]
    st.sidebar.divider()
    st.sidebar.subheader(f"📊 {wh_sel}库 状态统计")
    st.sidebar.markdown(f"总可用库位数: **{curr_data['total_bins']}**")
    st.sidebar.markdown(f"当前已用库位: **{curr_data['used_bins']}**")
    
    # 功能扩展：异常库位导出 (不可用但有货)
    st.sidebar.divider()
    st.sidebar.subheader("⚠️ 数据异常核查")
    
    # 筛选：状态为“不可用”且Items不为空的库位
    error_bins = []
    for loc, info in l_map.items():
        if info['Status'] == "不可用" and len(info['Items']) > 0:
            error_bins.append({
                "库位号": loc,
                "当前状态": info['Status'],
                "存放货物": ", ".join(info['Items'])
            })
    
    if error_bins:
        error_df = pd.DataFrame(error_bins)
        
        # 导出为 Excel 格式 (使用 BytesIO)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            error_df.to_excel(writer, index=False, sheet_name='异常库位清单')
        excel_data = output.getvalue()
        
        st.sidebar.warning(f"检测到 {len(error_bins)} 个异常库位 (状态禁用但有货)")
        st.sidebar.download_button(
            label="📥 导出异常库位 (Excel)",
            data=excel_data,
            file_name="MDC_System_Error_Bins.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.sidebar.success("未检测到状态冲突库位")

    # 侧边栏：空库位导出
    st.sidebar.divider()
    st.sidebar.subheader("📥 报表导出")
    empty_locs = [k for k, v in l_map.items() if v['WH'] == wh_sel and v['Status'] == "可用" and len(v['Items']) == 0]
    
    if empty_locs:
        csv_df = pd.DataFrame(empty_locs, columns=['Empty_Location_ID'])
        st.sidebar.download_button(
            label=f"导出 {wh_sel}库 空库位清单",
            data=csv_df.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"MDC_{wh_sel}_Empty_Locs.csv",
            mime='text/csv'
        )

    # 主页渲染
    cols_stats = st.columns(5)
    for i, wh_key in enumerate(['A', 'B', 'C', 'D', 'E']):
        s = wh_stats[wh_key]
        r = (s['u_v']/s['t_v']*100) if s['t_v']>0 else 0
        with cols_stats[i]:
            st.markdown(f'<div class="wh-stat-card"><div class="wh-stat-title">{wh_key} 库</div><div class="wh-stat-val">{r:.1f}%</div><div style="font-size:11px; color:#888;">{s["u_v"]:.1f}/{s["t_v"]:.1f} m³</div></div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="legend-container">
            <div class="legend-item"><div class="bin-box status-empty">层</div> 可用空位</div>
            <div class="legend-item"><div class="bin-box status-used">层</div> 有货占用</div>
            <div class="legend-item"><div class="bin-box status-disabled">❌</div> 不可用库位</div>
            <div class="legend-item" style="color:#ff9800; font-weight:bold;">━ 橙色横梁</div>
            <div class="legend-item" style="color:#3498db; font-weight:bold;">⫶ 蓝色立柱</div>
        </div>
    """, unsafe_allow_html=True)

    levels = ["50","40","30","20","10","00"] if wh_sel=='A' else ["40","30","20","10","00"]
    split_size = 3 if wh_sel=='A' else 2
    aisles = sorted(list(set(v['Aisle'] for v in l_map.values() if v['WH']==wh_sel)))

    for a_id in aisles:
        st.markdown(f'<div class="aisle-title">📍 货道: {a_id}</div>', unsafe_allow_html=True)
        all_cols = sorted(list(set(v['Col'] for v in l_map.values() if v['Aisle']==a_id)), reverse=True)
        h_str = '<div class="shelf-container"><div class="pillar-tech-blue"></div>'
        for i in range(0, len(all_cols), split_size):
            bay_cols = all_cols[i : i + split_size]
            h_str += '<div class="bay-unit">'
            col_html_list = ["" for _ in bay_cols]
            for l_idx, lvl in enumerate(levels):
                for c_idx, cid in enumerate(bay_cols):
                    f_id = f"{a_id}{cid}{lvl}"
                    d = l_map.get(f_id)
                    cls, sym = "status-unknown", lvl
                    if d:
                        if len(d['Items']) > 0: cls = "status-used"
                        elif d['Status'] == "可用": cls = "status-empty"
                        elif d['Status'] == "不可用": cls, sym = "status-disabled", "❌"
                        elif d['Status'] == "通道": cls, sym = "status-aisle", "↔️"
                        elif d['Status'] == "柱子": cls, sym = "status-pillar", "█"
                    tip = " | ".join(d['Items']) if d and d['Items'] else (d['Status'] if d else "")
                    col_html_list[c_idx] += f'<div class="bin-box {cls}" title="{tip}">{sym}</div>'
                if l_idx < len(levels) - 1:
                    for c_idx in range(len(bay_cols)): col_html_list[c_idx] += '<div class="orange-beam-row"></div>'
            for idx, c_html in enumerate(col_html_list):
                h_str += f'<div class="bin-column">{c_html}<div style="font-size:10px;color:#888;margin-top:2px;">{bay_cols[idx]}</div></div>'
            h_str += '</div><div class="pillar-tech-blue"></div>'
        st.markdown(h_str + '</div>', unsafe_allow_html=True)