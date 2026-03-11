import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Silenciar avisos de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Configuración (Tu versión de siempre)
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1rem !important; }
        .titulo-una-linea {
            text-align: center;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Función de Carga con ADAPTADOR (El blindaje real)
@st.cache_data(ttl=3600, show_spinner="Conectando con el Ministerio...")
def cargar_datos():
    # URL sin la barra final (a veces esto es la clave)
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    
    # Configuramos una sesión con reintentos automáticos
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # Forzamos la descarga ignorando certificados que dan guerra
        r = session.get(url, headers=headers, timeout=30, verify=False)
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        return None

# 3. Resto de tu lógica "de puta madre"
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
        # Procesar datos
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        
        ref = df[df["Municipio"] == muni_sel].iloc[0]
        df["Distancia"] = calcular_distancia(ref["lat_num"], ref["lon_num"], df["lat_num"], df["lon_num"])
        df["p_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        res = df[(df["Distancia"] <= radio) & (df["p_num"].notna())].sort_values(by="p_num")

        st.divider()
        for _, g in res.head(15).iterrows():
            with st.container(border=True):
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**{g['Rótulo']}**")
                    st.caption(f"{g['Dirección']} ({g['Municipio']})")
                    st.write(f"💰 **{g[col_precio]} €** | 📍 {g['Distancia']:.1f} km")
                with col_btn:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                    st.link_button("Ir", map_url, use_container_width=True)
else:
    st.error("El Ministerio está bloqueando la conexión de la app.")
    if st.button("🔄 Forzar reintento"):
        st.cache_data.clear()
        st.rerun()
