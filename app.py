import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np

# 1. Configuración idéntica a tu Versión 1
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1rem !important; }
        hr { margin: 0.8rem 0 !important; }
        .titulo-una-linea {
            text-align: center;
            white-space: nowrap;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Función JS de tu Versión 1
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 3. Carga de Datos (Restaurada de tu Versión 1 para que no falle)
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    # He vuelto a poner la URL exacta de tu primer código
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 4. Función de apoyo para calcular distancia (necesaria para el radio)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INICIO DE LA INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    # Convertimos a DataFrame para procesar distancias y precios rápido
    df = pd.DataFrame(datos)
    
    # Limpieza básica de columnas necesarias
    df["Latitud"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["Longitud (WGS84)"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["D"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')

    municipios_unicos = sorted(df["Municipio"].unique())
    
    # === SECCIÓN DE CONFIGURACIÓN ===
    with st.container(border=True):
        municipio_sel = st.selectbox(
            "📍 Municipio base (Ubicación):",
            options=municipios_unicos,
            index=None,
            placeholder="Escribe tu municipio..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)
        with col2:
            tipo_comb = st.radio("Ordenar por precio de:", ["Diésel", "G95"], horizontal=True)
            col_target = "D" if tipo_comb == "Diésel" else "G95"

    if municipio_sel:
        ocultar_teclado()
        
        # Obtenemos coordenadas del municipio elegido para el radio
        muni_data = df[df["Municipio"] == municipio_sel].iloc[0]
        lat_ref, lon_ref = muni_data["Latitud"], muni_data["Longitud (WGS84)"]
        
        # Calculamos distancias
        df["Distancia"] = haversine(lat_ref, lon_ref, df["Latitud"], df["Longitud (WGS84)"])
        
        # Filtrar por radio y ordenar por el combustible elegido
        resultados = df[(df["Distancia"] <= radio_km) & (df[col_target].notna())].sort_values(by=col_target)

        st.divider()
        st.write(f"### 📉 {tipo_comb} más barato a {radio_km}km")

        if not resultados.empty:
            for _, gas in resultados.head(15).iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{gas['Rótulo']}**")
                        st.caption(f"{gas['Dirección']} ({gas['Municipio']})")
                        st.write(f"📍 a {gas['Distancia']:.1f} km")
                    with c2:
                        st.markdown(f"### {gas[col_target]}€")
                        # Link directo a Google Maps
                        map_url = f"https://www.google.com/maps?q={gas['Latitud']},{gas['Longitud (WGS84)']}"
                        st.link_button("Ir", map_url, use_container_width=True)
        else:
            st.warning("No hay gasolineras en este rango.")
else:
    st.error("No se ha podido conectar con el Ministerio.")
