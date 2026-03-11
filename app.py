import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3
import json
import os

# Silenciar avisos de seguridad SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# Nombre del archivo de respaldo
BACKUP_FILE = "ultimo_backup_gasolina.json"

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

def ocultar_teclado():
    components.html("<script>window.parent.document.activeElement.blur();</script>", height=0, width=0)

# Carga de Datos con Sistema de Respaldo
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        # Intento conectar con el Ministerio
        r = requests.get(url, headers=headers, timeout=20, verify=False)
        r.raise_for_status()
        datos = r.json()["ListaEESSPrecio"]
        
        # Si funciona, guardamos una copia de seguridad en un archivo local
        with open(BACKUP_FILE, 'w') as f:
            json.dump(datos, f)
        
        return datos, False # False significa que NO son datos antiguos
        
    except Exception as e:
        # Si falla la conexión, intentamos cargar el archivo de respaldo
        if os.path.exists(BACKUP_FILE):
            with open(BACKUP_FILE, 'r') as f:
                datos_antiguos = json.load(f)
            return datos_antiguos, True # True significa que son datos antiguos
        else:
            return None, False

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos, es_backup = cargar_datos()

if datos:
    # Si estamos usando el backup, avisamos al usuario
    if es_backup:
        st.warning("⚠️ No se ha podido conectar con el Ministerio. Mostrando los últimos datos guardados (pueden no estar actualizados).")

    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        municipio_sel = st.selectbox("🔍 Municipio:", options=municipios_unicos, index=None)
        c1, c2 = st.columns(2)
        with c1:
            radio_km = st.slider("Radio (Km):", 1, 50, 10)
        with c2:
            orden = st.radio("Precio de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if orden == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        ocultar_teclado()
        
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        
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
            st.info("No hay resultados en este radio.")
else:
    st.error("No hay conexión ni datos guardados disponibles.")
