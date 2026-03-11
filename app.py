import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3

# Deshabilitar advertencias de seguridad si optamos por verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Configuración (Tu base Versión 1)
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

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# 3. Carga de Datos (VERSIÓN ULTRA-RESISTENTE)
@st.cache_data(ttl=3600, show_spinner="Sincronizando con el Ministerio...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # Usamos una sesión para mantener la conexión y verify=False para evitar el error de SSL
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=30, verify=False)
        r.raise_for_status()
        
        data = r.json()["ListaEESSPrecio"]
        df = pd.DataFrame(data)
        
        # Limpieza de datos (igual que antes)
        df["Latitud"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["Longitud (WGS84)"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["Precio Gasoleo A"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df["Precio Gasolina 95 E5"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- RESTO DE LA INTERFAZ (Tu lógica de ubicación y radio) ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

df = cargar_datos()

if df is not None:
    with st.container(border=True):
        municipios_unicos = sorted(df["Municipio"].unique())
        municipio_sel = st.selectbox("📍 Municipio base:", options=municipios_unicos, index=None, placeholder="Escribe tu municipio...")
        
        c1, c2 = st.columns(2)
        with c1:
            radio_km = st.slider("Radio (Km):", 1, 30, 5)
        with c2:
            tipo = st.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        # Filtrar gasolineras del municipio para obtener el punto central
        punto_ref = df[df["Municipio"] == municipio_sel].iloc[0]
        
        df["Distancia"] = calcular_distancia(
            punto_ref["Latitud"], punto_ref["Longitud (WGS84)"],
            df["Latitud"], df["Longitud (WGS84)"]
        )
        
        resultados = df[(df["Distancia"] <= radio_km) & (df[col_precio].notna())].sort_values(by=col_precio)

        st.divider()
        if not resultados.empty:
            for _, gas in resultados.head(10).iterrows():
                with st.container(border=True):
                    col_txt, col_btn = st.columns([3, 1])
                    with col_txt:
                        st.markdown(f"**{gas['Rótulo']}** - {gas[col_precio]}€/L")
                        st.caption(f"{gas['Dirección']} ({gas['Municipio']}) | {gas['Distancia']:.1f} km")
                    with col_btn:
                        map_link = f"https://www.google.com/maps?q={gas['Latitud']},{gas['Longitud (WGS84)']}"
                        st.link_button("Ir", map_link, use_container_width=True)
        else:
            st.warning("No hay resultados en este radio.")
