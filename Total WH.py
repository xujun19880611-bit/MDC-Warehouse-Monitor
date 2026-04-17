import streamlit as st
import pandas as pd
import os
from io import BytesIO

# --- 1. 页面配置 ---
st.set_page_config(page_title="MDC Warehouse Monitor", layout="wide")

# --- 2. 语言字典 ---
lang_dict = {
    "CN": {
        "title": "MDC 全仓库总体库容监控中心",
        "total_ratio": "全库总占比",
        "total_vol": "容积统计 (m³)",
        "used_total": "已用 / 总可用",
        "sidebar_ctrl": "⚙️ 控制面板",
        "sel_wh": "📂 选择库房",
        "sel_aisle": "🛣️ 选择货道",
        "stat_title": "📊 实时统计",
        "loc_total": "可用库位总数",
        "loc_used": "已使用库位",
        "loc_empty": "空闲库位",
        "loc_util": "库位利用率",
        "export_btn": "📥 导出全库空位 (Excel)",
        "unit": "个",
        "free": "空闲",
        "vol_tip": "容积",
        "status_tip": "状态",
        "east": "东半段",
        "mid": "中段",
        "west": "西半段"
    },
    "PT": {
        "title": "Centro de Monitoramento de Armazém MDC",
        "total_ratio": "Ocupação Total",
        "total_vol": "Estatística de Volume (m³)",
        "used_total": "Usado / Total Disp.",
        "sidebar_ctrl": "⚙️ Painel de Controlo",
        "sel_wh": "📂 Selecionar Armazém",
        "sel_aisle": "🛣️ Selecionar Corredor",
        "stat_title": "📊 Estatísticas em Tempo Real",
        "loc_total": "Total de Locais Disp.",
        "loc_used": "Locais Ocupados",
        "loc_empty": "Locais Livres",
        "loc_util": "Taxa de Utilização",
        "export_btn": "📥 Exportar Locais Livres (Excel)",
        "unit": "un",
        "free": "Livre",
        "vol_tip": "Volume",
        "status_tip": "Estado",
        "east": "Zona Este",
        "mid": "Zona Central",
        "west": "Zona Oeste"
    }
}

# --- 3. 语言切换 ---
st.sidebar.markdown("### 🌐 Idioma / 语言")
lang_choice = st.sidebar.radio("", ["Português", "中文"], horizontal=True)
L = lang_dict["PT"] if lang_choice == "Português" else lang_dict["CN"]

# --- 4. 样式配置 ---
st.markdown(f"""
    <style>
    .total-card {{
        background: linear-gradient(135deg, #3A1C71 0%, #D76D77 50%, #FFAF7B 100%);
        padding: 20px; border-radius: 15px; color: white; text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1); margin-bottom: 20px;
    }}
    .wh-card {{
        background: linear-gradient(135deg, #1D976C 0%, #93F9B9 100%);
        padding: 15px; border-radius: 12px; color: #1a1a1a; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }}
    .sidebar-stat {{
        background-color: #ffffff; padding: 12px; border-radius: 10px;
        border-left: 5px solid #1D976C; margin-bottom: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .section-header {{
        background-color: #e9ecef; padding: 5px 15px; border-radius: 5px;
        color: #495057; font-weight: bold; margin-top: 20px; border-left: 5px solid #3A1C71;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 数据加载 ---
@st.cache_data(ttl=600)
def load_data():
    file_name = "SGF.csv" 
    if not os.path.exists(file_name): return None, None
    try:
        # 严格引用：0:SKU, 6:库位, 9:数量, 11-13:尺寸, 14:状态
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
                loc_map[loc] = {'WH': raw_val[0].upper(), 'Aisle': raw_val[0:3], 'Col': raw_val[3:5], 'Vol': row['Vol_m3'], 'Status': row['Status'], 'Items': []}
            if row['Qty'] > 0:
                loc_map[loc]['Items'].append(f"• {row['SKU']}: {int(row['Qty'])}")
        return loc_map, df
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None

loc_map, _ = load_data()

# --- 6. 渲染引擎 ---
def render_shelf(cols, title, split_size, wh):
    if not cols: return
    st.markdown(f'<div class="section-header">📍 {title}</div>', unsafe_allow_html=True)
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
                st.markdown('<div style="border-left:2px dashed #bbb;height:380px;margin:0 auto;width:1px;opacity:0.5;"></div>', unsafe_allow_html=True)
            else:
                for lvl in levels:
                    loc_id = f"{sel_aisle}-{item}-{lvl}"
                    data = loc_map.get(loc_id)
                    if not data:
                        st.button("➖", key=loc_id, disabled=True, use_container_width=True)
                    elif data['Status'] in ['柱子', '消防栓', 'Pilar']:
                        st.button("🚫", key=loc_id, help=data['Status'], disabled=True, use_container_width=True)
                    elif len(data['Items']) > 0:
                        st.button(f"🟦{lvl}", key=loc_id, help="\n".join(data['Items']), use_container_width=True)
                    else:
                        st.button(f"🟩{lvl}", key=loc_id, help=f"{L['vol_tip']}: {data['Vol']:.3f}m³\n{L['status_tip']}: {L['free']}", use_container_width=True)
                st.markdown(f'<div style="text-align:center;font-weight:bold;font-size:11px;color:#666;">{item}</div>', unsafe_allow_html=True)

# --- 7. 主界面 ---
if loc_map:
    all_locs = list(loc_map.values())
    unique_av = [i for i in all_locs if i['Status'] == '可用']
    
    gv = sum(i['Vol'] for i in unique_av)
    uv = sum(i['Vol'] for i in unique_av if len(i['Items']) > 0)
    ratio = (uv / gv * 100) if gv > 0 else 0

    st.markdown(f'# {L["title"]}')
    c1, c2 = st.columns([1, 1.2])
    with c1: st.markdown(f'<div class="total-card"><div style="font-size:1rem;">{L["total_ratio"]}</div><div style="font-size:3rem;font-weight:800;">{ratio:.1f}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="total-card"><div style="font-size:1rem;">{L["total_vol"]}</div><div style="font-size:2rem;font-weight:700;margin-top:5px;">{uv:.1f} / {gv:.1f}</div><div style="font-size:0.8rem;">{L["used_total"]}</div></div>', unsafe_allow_html=True)

    # 仓库详情卡片
    wh_list = ['A', 'B', 'C', 'D', 'E']
    h_cols = st.columns(5)
    for i, wh in enumerate(wh_list):
        wh_d = [j for j in unique_av if j['WH'] == wh]
        tv_w = sum(j['Vol'] for j in wh_d); uv_w = sum(j['Vol'] for j in wh_d if len(j['Items']) > 0)
        r_w = (uv_w / tv_w * 100) if tv_w > 0 else 0
        with h_cols[i]: st.markdown(f'<div class="wh-card"><div style="font-weight:bold;">{wh}</div><div style="font-size:1.5rem;font-weight:700;color:#0d47a1;">{r_w:.1f}%</div></div>', unsafe_allow_html=True)

    st.divider()

    # --- 8. 侧边栏 ---
    st.sidebar.header(L["sidebar_ctrl"])
    sel_wh = st.sidebar.selectbox(L["sel_wh"], wh_list)
    
    curr_locs = [i for i in unique_av if i['WH'] == sel_wh]
    t_cnt = len(curr_locs); u_cnt = len([i for i in curr_locs if len(i['Items']) > 0])
    e_cnt = t_cnt - u_cnt; util = (u_cnt / t_cnt * 100) if t_cnt > 0 else 0
    
    st.sidebar.markdown(f"""
        <div class="sidebar-stat"><small>{L['loc_total']}</small><br><b>{t_cnt} {L['unit']}</b></div>
        <div class="sidebar-stat" style="border-left-color:#D76D77"><small>{L['loc_used']}</small><br><b>{u_cnt} {L['unit']}</b></div>
        <div class="sidebar-stat" style="border-left-color:#93F9B9"><small>{L['loc_empty']}</small><br><b>{e_cnt} {L['unit']}</b></div>
        <div class="sidebar-stat" style="border-left-color:#FFAF7B"><small>{L['loc_util']}</small><br><b>{util:.1f}%</b></div>
    """, unsafe_allow_html=True)

    aisles = sorted(list(set(i['Aisle'] for i in all_locs if i['WH'] == sel_wh)))
    sel_aisle = st.sidebar.selectbox(L["sel_aisle"], aisles)

    # 导出功能
    empty_data = [{'Loc': k, 'WH': v['WH']} for k, v in loc_map.items() if v['Status'] == '可用' and len(v['Items']) == 0]
    if empty_data:
        out = BytesIO(); 
        with pd.ExcelWriter(out, engine='xlsxwriter') as w: pd.DataFrame(empty_data).to_excel(w, index=False)
        st.sidebar.download_button(L["export_btn"], out.getvalue(), "MDC_Free_Locs.xlsx", use_container_width=True)

    # --- 9. 货架显示 (修正分段逻辑) ---
    current_cols = sorted(list(set(i['Col'] for i in all_locs if i['Aisle'] == sel_aisle)))
    
    if sel_wh in ['A', 'B']:
        # A和B库：三段式 (01-24, 25-48, 49+)
        render_shelf([c for c in current_cols if int(c) <= 24], f"{L['east']} (01-24)", 3, sel_wh)
        render_shelf([c for c in current_cols if 25 <= int(c) <= 48], f"{L['mid']} (25-48)", 3, sel_wh)
        render_shelf([c for c in current_cols if int(c) > 48], f"{L['west']} (49+)", 3, sel_wh)
    elif sel_wh in ['C', 'D', 'E']:
        # C, D, E库：两段式 (01-22, 23+)
        render_shelf([c for c in current_cols if int(c) <= 22], f"{L['east']} (01-22)", 2, sel_wh)
        render_shelf([c for c in current_cols if int(c) > 22], f"{L['west']} (23+)", 2, sel_wh)
    else:
        render_shelf(current_cols, f"Corredor {sel_aisle}", 2, sel_wh)

else:
    st.warning("⚠️ SGF.csv 缺失或格式错误。")