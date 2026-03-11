import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np

# 1. Configuración y Estilos (Base de la Versión 1)
st.set_page_config(page_title="Gasolina Cerca de Mí", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1.5rem !important; }
        .titulo-una-linea {
            text-align: center;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .price-tag {
            font-size: 1.2rem;
            font-weight: bold;
            color: #2e7d32;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Función para calcular distancia entre dos coordenadas (Km)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# 3. Carga de Datos (Optimizado con coordenadas)
@st.cache_data(ttl=3600, show_spinner="Actualizando precios oficiales...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        lista = r.json()["ListaEESSPrecio"]
        df = pd.DataFrame(lista)
        
        # Limpieza de precios y coordenadas
        df["Precio Gasoleo A"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df["Precio Gasolina 95 E5"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df["Latitud"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["Longitud (WGS84)"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        
        return df
    except:
        return None

# --- INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Gasolina al Mejor Precio</div>", unsafe_allow_html=True)

df_total = cargar_datos()

if df_total is not None:
    # 4. CONFIGURACIÓN DE BÚSQUEDA
    with st.expander("⚙️ Ajustes de búsqueda", expanded=True):
        # Municipio (Editable)
        municipios_unicos = sorted(df_total["Municipio"].unique())
        
        # Simulación de ubicación actual (Donostia como ejemplo inicial de tu zona)
        municipio_default = "DONOSTIA/SAN SEBASTIÁN" if "DONOSTIA/SAN SEBASTIÁN" in municipios_unicos else None
        
        municipio_sel = st.selectbox(
            "📍 Municipio base:",
            options=municipios_unicos,
            index=municipios_unicos.index(municipio_default) if municipio_default else 0
        )
        
        radio_km = st.slider("🔍 Radio de búsqueda (Km):", 1, 50, 10)
        tipo_combustible = st.radio("Combustible:", ["Diésel", "Gasolina 95"], horizontal=True)
        col_precio = "Precio Gasoleo A" if tipo_combustible == "Diésel" else "Precio Gasolina 95 E5"

    # 5. LÓGICA DE FILTRADO
    # Obtenemos las coordenadas medias del municipio seleccionado para buscar a la redonda
    base_coords = df_total[df_total["Municipio"] == municipio_sel][["Latitud", "Longitud (WGS84)"]].mean()
    
    if not base_coords.isna().any():
        # Calcular distancia de todas las gasolineras respecto al centro del municipio elegido
        df_total["Distancia"] = df_total.apply(
            lambda x: calcular_distancia(base_coords["Latitud"], base_coords["Longitud (WGS84)"], x["Latitud"], x["Longitud (WGS84)"]),
            axis=1
        )
        
        # Filtrar por radio y precio disponible
        resultados = df_total[
            (df_total["Distancia"] <= radio_km) & 
            (df_total[col_precio].notna())
        ].sort_values(by=col_precio)

        # 6. MOSTRAR RESULTADOS
        st.write(f"### 🏁 Top baratas a {radio_km}km de {municipio_sel}")
        
        if not resultados.empty:
            for _, gas in resultados.head(15).iterrows(): # Mostramos las 15 mejores
                with st.container(border=True):
                    col_info, col_price = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"**{gas['Rótulo']}**")
                        st.caption(f"{gas['Dirección']}\n\nA **{gas['Distancia']:.1f} km** de distancia")
                    
                    with col_price:
                        st.markdown(f"<div style='text-align:right'><span class='price-tag'>{gas[col_precio]} €</span></div>", unsafe_allow_html=True)
                        # Enlace a Maps
                        lat_val = str(gas['Latitud'])
                        lon_val = str(gas['Longitud (WGS84)'])
                        st.markdown(f"[🗺️ Ver mapa](https://www.google.com/maps/search/?api=1&query={lat_val},{lon_val})")
        else:
            st.warning("No se han encontrado gasolineras en ese radio con el combustible seleccionado.")
else:
    st.error("Error al conectar con el servidor de precios.")
