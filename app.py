import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np

# 1. Configuración (Tu base Versión 1)
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# --- ESTILOS CSS (Tu base Versión 1) ---
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

# 2. Función de distancia (Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0 # Radio de la Tierra en km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# 3. Carga de Datos (CORREGIDA para evitar el error de conexión)
@st.cache_data(ttl=3600, show_spinner="Sincronizando con el Ministerio...")
def cargar_datos():
    # URL sin la barra final para mayor compatibilidad
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    try:
        # Añadimos un User-Agent común y aumentamos el timeout
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status() # Lanza error si la respuesta no es 200
        
        data = r.json()["ListaEESSPrecio"]
        df = pd.DataFrame(data)
        
        # Limpieza de datos crítica para que el cálculo de distancia no falle
        df["Latitud"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["Longitud (WGS84)"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["Precio Gasoleo A"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df["Precio Gasolina 95 E5"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error detallado: {e}")
        return None

# --- INICIO DE LA INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

df = cargar_datos()

if df is not None:
    # 4. Ajustes de búsqueda
    with st.container(border=True):
        municipios_unicos = sorted(df["Municipio"].unique())
        
        # Selección de municipio (Editable)
        municipio_sel = st.selectbox(
            "📍 Tu ubicación (Municipio):",
            options=municipios_unicos,
            index=None,
            placeholder="Escribe tu municipio..."
        )
        
        col_r, col_t = st.columns(2)
        with col_r:
            radio_km = st.slider("Radio (Km):", 1, 30, 10)
        with col_t:
            tipo = st.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        # Coordenadas del "centro" de ese municipio para el radio
        coords_base = df[df["Municipio"] == municipio_sel][["Latitud", "Longitud (WGS84)"]].iloc[0]
        
        # Calculamos distancia de todas las gasolineras respecto a ese punto
        df["Distancia"] = calcular_distancia(
            coords_base["Latitud"], coords_base["Longitud (WGS84)"],
            df["Latitud"], df["Longitud (WGS84)"]
        )
        
        # Filtramos por radio y ordenamos por precio
        resultados = df[(df["Distancia"] <= radio_km) & (df[col_precio].notna())].sort_values(by=col_precio)

        st.divider()
        st.write(f"### 💸 {tipo} más barato cerca de {municipio_sel}")

        if not resultados.empty:
            for _, gas in resultados.head(10).iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{gas['Rótulo']}**")
                        st.caption(f"{gas['Dirección']} ({gas['Municipio']})")
                        st.write(f"📍 a {gas['Distancia']:.1f} km")
                    with c2:
                        st.markdown(f"### {gas[col_precio]}€")
                        # Link a Maps con las coordenadas
                        maps_url = f"https://www.google.com/maps?q={gas['Latitud']},{gas['Longitud (WGS84)']}"
                        st.link_button("Ir", maps_url, use_container_width=True)
        else:
            st.warning("No hay gasolineras en este radio.")

else:
    st.error("Sigue habiendo problemas con la conexión al Ministerio. Revisa si el sitio web oficial funciona.")
