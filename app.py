import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- ADAPTADOR SSL ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# --- DISEÑO UI CORREGIDO ---
st.markdown("""
    <style>
        /* Bajamos el contenedor para que no se corte el título */
        .block-container {padding-top: 4rem; padding-bottom: 1rem;}
        
        /* Título Estilizado */
        .main-title {
            text-align: center;
            background: linear-gradient(90deg, #1E88E5, #00D2FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: clamp(24px, 7vw, 38px);
            margin-bottom: 0.2rem;
            text-transform: uppercase;
        }
        .title-underline {
            height: 4px;
            width: 60px;
            background: #1E88E5;
            margin: 0.5rem auto 2rem auto;
            border-radius: 2px;
        }

        /* Ajustes de espaciado para que quepa en una fila */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) { margin-top: 0.5rem; }
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        div[data-testid="stRadio"] {margin-bottom: -1.5rem;}
        
        /* Botón Navegar Centrado */
        .nav-button {
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            text-decoration: none !important;
            margin-top: 5px;
            transition: background 0.3s;
        }
        .nav-button:hover { background-color: #f0f2f6; }
        .nav-button img { width: 18px; margin-right: 8px; }
        .nav-button span { color: #3c4043; font-size: 14px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# Título corregido
st.markdown('<div class="main-title">Buscador Gasolineras</div><div class="title-underline"></div>', unsafe_allow_html=True)

# 2. Carga de Datos
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    archivo_backup = "gasolineras_backup.csv"
    tz_madrid = pytz.timezone('Europe/Madrid')
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, datetime.datetime.now(tz_madrid)
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            mtime = os.path.getmtime(archivo_backup)
            fecha_utc = datetime.datetime.fromtimestamp(mtime, pytz.utc)
            return df_rec.to_dict('records'), fecha_utc.astimezone(tz_madrid)
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

datos, fecha_act = cargar_datos()

if fecha_act:
    st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.8rem; margin-top: -15px; margin-bottom: 15px;'>Actualizado: {fecha_act.strftime('%H:%M')}</div>", unsafe_allow_html=True)

if datos:
    df = pd.DataFrame(datos)
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    loc = get_geolocation()
    lat_gps, lon_gps, muni_gps = None, None, None

    if loc and 'coords' in loc:
        lat_gps, lon_gps = loc['coords']['latitude'], loc['coords']['longitude']
        # Buscamos municipio cercano solo para el selector
        df_geo = df.dropna(subset=['lat_num', 'lon_num']).head(1000).copy()
        df_geo["d"] = calcular_distancia(lat_gps, lon_gps, df_geo["lat_num"], df_geo["lon_num"])
        muni_gps = df_geo.sort_values("d").iloc[0]["Municipio"]

    with st.container(border=True):
        idx = municipios_unicos.index(muni_gps) if muni_gps in municipios_unicos else None
        municipio_manual = st.selectbox("📍 Ubicación:", options=municipios_unicos, index=idx)
        lat_ref, lon_ref = (lat_gps, lon_gps) if (lat_gps and (municipio_manual == muni_gps or not municipio_manual)) else (None, None)
        
        if not lat_ref and municipio_manual:
            ref = df[df["Municipio"] == municipio_manual].iloc[0]
            lat_ref, lon_ref = ref["lat_num"], ref["lon_num"]

    radio_km = st.slider("Radio (Km):", 1, 50, 10)
    tipo_combustible = st.radio("Ordenar por:", ["Diésel", "G95"], horizontal=True)
    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[(df["Distancia"] <= radio_km) & (df[col_orden].notna())].sort_values(col_orden)

        st.divider()
        
        for _, g in res.head(15).iterrows():
            with st.container(border=True):
                # Layout en una fila para móvil
                col_info, col_btn = st.columns([0.65, 0.35])
                with col_info:
                    st.markdown(f"**{g['Rótulo']}**")
                    p_d = f"{g['Precio Gasoleo A']}€" if pd.notnull(g['Precio_Diesel']) else "-"
                    p_g = f"{g['Precio Gasolina 95 E5']}€" if pd.notnull(g['Precio_G95']) else "-"
                    st.markdown(f"<small>D: **{p_d}** | G95: **{p_g}**</small>", unsafe_allow_html=True)
                    st.caption(f"{g['Distancia']:.1f}km • {g['Dirección'][:25]}...")
                
                with col_btn:
                    url_map = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                    # Botón centrado con icono y texto original
                    st.markdown(f"""
                        <a href="{url_map}" target="_blank" class="nav-button">
                            <img src="https://upload.wikimedia.org/wikipedia/commons/3/39/Google_Maps_icon_%282015-2020%29.svg">
                            <span>Navegar</span>
                        </a>
                    """, unsafe_allow_html=True)
else:
    st.error("Error al cargar datos.")
