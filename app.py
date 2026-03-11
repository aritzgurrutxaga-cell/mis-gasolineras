import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3
import json
import os

# 1. Silenciamos los avisos de seguridad SSL para evitar ruidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# Archivo de respaldo local
BACKUP_FILE = "datos_gasolineras_v1.json"

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

# 3. Función de Carga con "Fuerza Bruta"
@st.cache_data(ttl=3600, show_spinner="Intentando conectar con el Ministerio...")
def cargar_datos():
    # Probamos con la URL que mejor suele responder a servidores
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    
    # Headers extremadamente realistas
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Referer': 'https://geoportal.minetur.gob.es/',
        'Connection': 'keep-alive'
    }
    
    try:
        # Intentamos la conexión ignorando errores de certificado (verify=False)
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=30, verify=False)
        r.raise_for_status()
        datos = r.json()["ListaEESSPrecio"]
        
        # Si logramos conectar una sola vez, guardamos el Backup
        with open(BACKUP_FILE, 'w') as f:
            json.dump(datos, f)
        
        return datos, False
        
    except Exception as e:
        # Si falla (Bloqueo de IP), buscamos el backup
        if os.path.exists(BACKUP_FILE):
            with open(BACKUP_FILE, 'r') as f:
                return json.load(f), True
        return None, False

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- LÓGICA DE LA INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos, es_backup = cargar_datos()

if datos:
    if es_backup:
        st.warning("⚠️ El Ministerio está bloqueando la conexión. Mostrando últimos datos guardados.")
    
    df = pd.DataFrame(datos)
    # Limpieza de datos
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        municipio_sel = st.selectbox("🔍 Municipio base:", options=municipios_unicos, index=None, placeholder="Elige tu ubicación...")
        c1, c2 = st.columns(2)
        with c1:
            radio_km = st.slider("Radio (Km):", 1, 50, 10)
        with c2:
            orden = st.radio("Mejor precio de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if orden == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        ocultar_teclado()
        ref = df[df["Municipio"] == municipio_sel].iloc[0]
        df["Distancia"] = calcular_distancia(ref["lat_num"], ref["lon_num"], df["lat_num"], df["lon_num"])
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        resultados = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values(by="precio_num")

        st.divider()
        if not resultados.empty:
            for _, g in resultados.head(15).iterrows():
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
            st.info("No hay gasolineras en ese radio.")
else:
    st.error("❌ El servidor del Ministerio no responde a la aplicación.")
    st.info("💡 Consejo: Abre la web del Ministerio una vez en este dispositivo y luego refresca la app.")
    if st.button("🔄 Intentar reconectar"):
        st.cache_data.clear()
        st.rerun()
