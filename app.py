import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3
from streamlit_js_eval import streamlit_js_eval

# Esto evita que salgan mensajes feos en la pantalla por el tema del SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Configuración Estilo Versión 1
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

# 2. Función JS Ocultar Teclado (Versión 1)
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 3. Carga de Datos (Tu lógica V1 + Parche de Conexión)
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Usamos una sesión y verify=False para fulminar el error de conexión
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=25, verify=False)
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        return None

# 4. Función de distancia
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INICIO APP ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

# Pedir ubicación GPS
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'streamlit:set_component_value', value: {lat: pos.coords.latitude, lon: pos.coords.longitude}}, '*') }, err => {}, {enableHighAccuracy: true});", key="gps")

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    # Limpieza de datos necesaria para los cálculos
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(df["Municipio"].unique())
    index_default = None

    # Si hay GPS, buscamos el municipio más cercano para preseleccionar
    if loc and 'lat' in loc:
        # Calculamos distancia rápida para saber el municipio
        df["dist_gps"] = calcular_distancia(loc['lat'], loc['lon'], df["lat_num"], df["lon_num"])
        municipio_detectado = df.sort_values("dist_gps").iloc[0]["Municipio"]
        if municipio_detectado in municipios_unicos:
            index_default = municipios_unicos.index(municipio_detectado)

    # Selector de ubicación y ajustes
    with st.container(border=True):
        muni_sel = st.selectbox("📍 Municipio:", options=municipios_unicos, index=index_default, placeholder="Cargando ubicación...")
        
        c1, c2 = st.columns(2)
        with c1:
            radio = st.slider("Radio (Km):", 1, 50, 10)
        with c2:
            tipo = st.radio("Precio de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    if muni_sel:
        ocultar_teclado()
        
        # Punto de referencia: Coordenadas del municipio (o GPS si coincide)
        ref = df[df["Municipio"] == muni_sel].iloc[0]
        lat_ref = loc['lat'] if (loc and 'lat' in loc and muni_sel == ref["Municipio"]) else ref["lat_num"]
        lon_ref = loc['lon'] if (loc and 'lon' in loc and muni_sel == ref["Municipio"]) else ref["lon_num"]
        
        # Calcular distancias reales
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        df["p_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        # Filtrar y ordenar
        res = df[(df["Distancia"] <= radio) & (df["p_num"].notna())].sort_values(by="p_num")

        st.divider()
        st.write(f"### 📉 {tipo} más barato a {radio}km")
        
        for _, g in res.head(15).iterrows():
            with st.container(border=True):
                col_txt, col_btn = st.columns([3, 1])
                with col_txt:
                    st.markdown(f"**{g['Rótulo']}**")
                    st.caption(f"{g['Dirección']} ({g['Municipio']})")
                    st.write(f"💰 **{g[col_precio]} €** | 📍 {g['Distancia']:.1f} km")
                with col_btn:
                    map_url = f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}"
                    st.link_button("Ir", map_url, use_container_width=True)
else:
    st.error("No se ha podido conectar con el Ministerio. Reintentando...")
    if st.button("🔄 Forzar Reintento"):
        st.rerun()
