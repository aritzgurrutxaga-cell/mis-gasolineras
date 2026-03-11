import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import json
import os

# 1. Configuración limpia
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

# 3. Función de Carga Híbrida (Online + Local)
@st.cache_data(ttl=3600)
def cargar_datos():
    # Intento 1: Online (como la V1)
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            return r.json()["ListaEESSPrecio"], "Online 🟢"
    except:
        pass

    # Intento 2: Leer el archivo que tú has subido
    if os.path.exists("datos.json"):
        with open("datos.json", "r", encoding='utf-8') as f:
            data = json.load(f)
            # Dependiendo de cómo guardes el archivo, puede que necesites acceder a la clave o no
            if "ListaEESSPrecio" in data:
                return data["ListaEESSPrecio"], "Archivo Local 📂"
            return data, "Archivo Local 📂"
    
    return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos, origen = cargar_datos()

if datos:
    if origen == "Archivo Local 📂":
        st.info("⚠️ El Ministerio no responde. Usando el archivo 'datos.json' que subiste.")

    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        municipio_sel = st.selectbox("🔍 Municipio:", options=municipios_unicos, index=None, placeholder="Elige ubicación...")
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
        df["p_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        res = df[(df["Distancia"] <= radio_km) & (df["p_num"].notna())].sort_values(by="p_num")

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
    st.error("No hay conexión ni existe el archivo 'datos.json'.")
    st.write("Sube el archivo 'datos.json' a tu GitHub para que la app funcione sin conexión.")
