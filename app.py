import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3

# Silenciamos avisos de seguridad SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1rem !important; }
        .titulo-una-linea {
            text-align: center;
            white-space: nowrap;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

def ocultar_teclado():
    components.html("<script>window.parent.document.activeElement.blur();</script>", height=0, width=0)

@st.cache_data(ttl=600, show_spinner="Conectando con el Ministerio...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        # Usamos Session para una conexión más robusta
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=20, verify=False)
        r.raise_for_status()
        return r.json()["ListaEESSPrecio"]
    except:
        return None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        muni_sel = st.selectbox("🔍 Municipio:", options=municipios_unicos, index=None, placeholder="Selecciona ubicación...")
        c1, c2 = st.columns(2)
        with c1:
            radio = st.slider("Radio (Km):", 1, 50, 10)
        with c2:
            tipo = st.radio("Precio de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    if muni_sel:
        ocultar_teclado()
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        
        ref = df[df["Municipio"] == muni_sel].iloc[0]
        df["Distancia"] = calcular_distancia(ref["lat_num"], ref["lon_num"], df["lat_num"], df["lon_num"])
        df["p_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        res = df[(df["Distancia"] <= radio) & (df["p_num"].notna())].sort_values(by="p_num")

        st.divider()
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{g['Rótulo']}**")
                        st.caption(f"{g['Dirección']} ({g['Municipio']})")
                        st.write(f"💰 **{g[col_precio]} €** | 📍 {g['Distancia']:.1f} km")
                    with col_btn:
                        map_url = f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}"
                        st.link_button("Ir", map_url, use_container_width=True)
        else:
            st.info("No hay resultados en este radio.")
else:
    st.error("El Ministerio está saturado o bloqueando la conexión temporalmente.")
    if st.button("🔄 Reintentar conexión"):
        st.cache_data.clear()
        st.rerun()
