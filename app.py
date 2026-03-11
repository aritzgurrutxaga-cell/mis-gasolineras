import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
from streamlit_js_eval import streamlit_js_eval  # Necesitarás instalarlo: pip install streamlit-js-eval

# 1. Configuración limpia (Tu V1)
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

# 2. Función JS para ocultar teclado (Tu V1)
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 3. Carga de Datos (Tu V1 intacta)
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 4. Función Haversine
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INICIO DE LA LÓGICA ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

# Obtener ubicación GPS (Esto activará el mensaje de permiso del navegador)
loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.parent.postMessage({type: 'streamlit:set_component_value', value: {lat: pos.coords.latitude, lon: pos.coords.longitude}}, '*') }, err => {}, {enableHighAccuracy: true});", key="gps")

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    # Limpieza necesaria
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(df["Municipio"].unique())
    index_default = None

    # Si tenemos el GPS, buscamos el municipio más cercano para ponerlo por defecto
    if loc and 'lat' in loc:
        df["dist_gps"] = calcular_distancia(loc['lat'], loc['lon'], df["lat_num"], df["lon_num"])
        municipio_detectado = df.sort_values("dist_gps").iloc[0]["Municipio"]
        if municipio_detectado in municipios_unicos:
            index_default = municipios_unicos.index(municipio_detectado)
            st.toast(f"📍 Ubicación detectada: {municipio_detectado}", icon="🌍")

    # Selector de ubicación
    with st.container(border=True):
        municipio_sel = st.selectbox(
            "🔍 Municipio (se rellena solo si das permiso GPS):",
            options=municipios_unicos,
            index=index_default,
            placeholder="Elige tu municipio..."
        )
        
        col_radio, col_tipo = st.columns(2)
        with col_radio:
            radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)
        with col_tipo:
            orden = st.radio("Precio más barato de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if orden == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        ocultar_teclado()
        
        # Coordenadas de referencia (municipio elegido)
        ref = df[df["Municipio"] == municipio_sel].iloc[0]
        # Si tenemos el GPS exacto y el municipio coincide, usamos el GPS para más precisión
        lat_ref = loc['lat'] if (loc and 'lat' in loc and municipio_sel == municipio_detectado) else ref["lat_num"]
        lon_ref = loc['lon'] if (loc and 'lon' in loc and municipio_sel == municipio_detectado) else ref["lon_num"]
        
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        resultados = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values(by="precio_num")

        st.divider()
        st.write(f"### 📉 {orden} más barato a {radio_km}km")
        
        if not resultados.empty:
            for _, g in resultados.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{g['Rótulo']}**")
                        st.caption(f"{g['Dirección']} ({g['Municipio']})")
                        st.write(f"💰 **{g[col_precio]} €** |  📍 {g['Distancia']:.1f} km")
                    with col_btn:
                        map_url = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                        st.link_button("Ir", map_url, use_container_width=True)
        else:
            st.warning("No hay gasolineras en este radio.")
else:
    st.error("No se ha podido conectar con el Ministerio.")
