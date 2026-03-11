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

# --- DISEÑO UI AVANZADO ---
st.markdown("""
    <style>
        /* Contenedor principal */
        .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
        
        /* Título Estilizado sin iconos */
        .main-title {
            text-align: center;
            background: linear-gradient(90deg, #1E88E5, #00D2FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: clamp(24px, 8vw, 42px);
            margin-bottom: 0.2rem;
            letter-spacing: -1px;
        }
        .title-underline {
            height: 4px;
            width: 50px;
            background: #1E88E5;
            margin: 0 auto 1.5rem auto;
            border-radius: 2px;
        }

        /* Ajustes de espaciado */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) { margin-top: 0.5rem; }
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        div[data-testid="stRadio"] {margin-bottom: -1.5rem; padding-top: 10px;}
        hr {margin-top: 1rem; margin-bottom: 1rem; opacity: 0.3;}

        /* Estilo de Tarjetas */
        .stElementContainerContainer { margin-bottom: -0.5rem; }
        
        /* Botón estilo Google Maps */
        .map-btn-container img {
            width: 18px;
            margin-right: 8px;
            vertical-align: middle;
        }
    </style>
""", unsafe_allow_html=True)

# Render del Título
st.markdown('<div class="main-title">GASOLINERAS PRO</div><div class="title-underline"></div>', unsafe_allow_html=True)

# 2. Carga de Datos
@st.cache_data(ttl=3600, show_spinner="Actualizando precios...")
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
    st.markdown(f"<div style='text-align: center; color: #888; font-size: 0.75rem; margin-top: -10px; margin-bottom: 20px;'>Última actualización: {fecha_act.strftime('%H:%M')}</div>", unsafe_allow_html=True)

if datos:
    df = pd.DataFrame(datos)
    # Limpieza de datos
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    loc = get_geolocation()
    lat_gps, lon_gps, muni_gps = None, None, None

    if loc and 'coords' in loc:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']
        # Usamos una muestra pequeña para buscar el municipio más cercano rápidamente
        df_sample = df.dropna(subset=['lat_num', 'lon_num']).head(500).copy()
        df_sample["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df_sample["lat_num"], df_sample["lon_num"])
        muni_gps = df_sample.sort_values("dist_temp").iloc[0]["Municipio"]

    # --- BLOQUE UBICACIÓN ---
    with st.container(border=True):
        idx = municipios_unicos.index(muni_gps) if muni_gps in municipios_unicos else None
        municipio_manual = st.selectbox("Selecciona tu zona:", options=municipios_unicos, index=idx)
        
        if lat_gps and (municipio_manual == muni_gps or municipio_manual is None):
            lat_ref, lon_ref = lat_gps, lon_gps
            st.markdown("<span style='color: #2e7d32; font-size: 0.8rem;'>📍 Ubicación GPS activa</span>", unsafe_allow_html=True)
        elif municipio_manual:
            ref = df[df["Municipio"] == municipio_manual].iloc[0]
            lat_ref, lon_ref = ref["lat_num"], ref["lon_num"]
        else:
            lat_ref, lon_ref = None, None

    # --- CONFIGURACIÓN ---
    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        radio_km = st.slider("Distancia:", 1, 50, 10, format="%d km")
    with col_s2:
        tipo_combustible = st.radio("Ordenar por:", ["Diésel", "G95"], horizontal=True)
    
    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    # --- RESULTADOS ---
    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[
            (df["Distancia"] <= radio_km) & 
            ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
        ].sort_values(col_orden, na_position='last')

        st.divider()
        
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    # Diseño compacto para móvil
                    c1, c2 = st.columns([0.65, 0.35])
                    
                    with c1:
                        # Rótulo y distancia
                        st.markdown(f"**{g['Rótulo']}**")
                        p_diesel = f"<span style='color:#1E88E5;'>{g['Precio Gasoleo A']}€</span>" if pd.notnull(g['Precio_Diesel']) else "—"
                        p_g95 = f"<span style='color:#E53935;'>{g['Precio Gasolina 95 E5']}€</span>" if pd.notnull(g['Precio_G95']) else "—"
                        st.markdown(f"D: {p_diesel} | G95: {p_g95}", unsafe_allow_html=True)
                        st.caption(f"{g['Distancia']:.1f} km • {g['Dirección'][:30]}...")

                    with c2:
                        url_map = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                        # Botón con logo de Google Maps
                        st.markdown(f"""
                            <a href="{url_map}" target="_blank" style="text-decoration: none;">
                                <div style="display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 8px 5px; margin-top: 10px;">
                                    <img src="https://upload.wikimedia.org/wikipedia/commons/3/39/Google_Maps_icon_%282015-2020%29.svg" width="16" style="margin-right: 5px;">
                                    <span style="color: #3c4043; font-size: 13px; font-weight: 500;">Ir</span>
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
        else:
            st.warning("No hay gasolineras cerca. Prueba a ampliar el radio.")
else:
    st.error("No se pudo conectar con el Ministerio.")
