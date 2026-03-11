import streamlit as st
import requests
import pandas as pd

# Configuración en castellano y layout
st.set_page_config(page_title="Gasolineras Pro", page_icon="⛽", layout="centered")

@st.cache_data(ttl=3600, show_spinner="Actualizando precios oficiales...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

def mostrar_gasolinera(gas, es_favorito=False):
    """Renderiza la tarjeta de cada gasolinera"""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(gas['Rótulo'])
            st.caption(f"📍 {gas['Dirección']} ({gas['Municipio']})")
        with col2:
            if es_favorito:
                st.write("⭐ **Favorito**")
        
        c1, c2, c3 = st.columns(3)
        d_val = f"{gas['Precio Gasoleo A']} €" if gas['Precio Gasoleo A'] else "N/A"
        g_val = f"{gas['Precio Gasolina 95 E5']} €" if gas['Precio Gasolina 95 E5'] else "N/A"
        
        c1.metric("Diésel A", d_val)
        c2.metric("Gasolina 95", g_val)
        
        lat = gas["Latitud"].replace(",", ".")
        lon = gas["Longitud (WGS84)"].replace(",", ".")
        c3.write("")
        c3.link_button("📍 Mapa", f"https://www.google.com/maps?q={lat},{lon}")

# --- INICIO DE LA APP ---
st.title("⛽ Gasolineras Pro")
datos = cargar_datos()

if datos:
    # Gestión de Favoritos mediante multiselect
    # Creamos un ID único para cada gasolinera combinando Rótulo y Dirección
    todas_opciones = [f"{g['Rótulo']} | {g['Dirección']} | {g['Municipio']}" for g in datos]
    
    st.sidebar.header("Configuración")
    favoritos_seleccionados = st.sidebar.multiselect(
        "⭐ Gestionar Favoritos:",
        options=todas_opciones,
        help="Las gasolineras seleccionadas aparecerán siempre al inicio."
    )

    # 1. SECCIÓN DE FAVORITOS (Se muestra siempre arriba si hay seleccionados)
    if favoritos_seleccionados:
        st.header("⭐ Tus Favoritos")
        for fav in favoritos_seleccionados:
            # Buscamos los datos del favorito en la lista global
            gas_fav = next(g for g in datos if f"{g['Rótulo']} | {g['Dirección']} | {g['Municipio']}" == fav)
            mostrar_gasolinera(gas_fav, es_favorito=True)
        st.divider()

    # 2. SECCIÓN DE BÚSQUEDA INDIVIDUAL
    st.header("🔍 Búsqueda por Municipio")
    municipios = sorted(list(set([g["Municipio"] for g in datos])))
    municipio_sel = st.selectbox("Selecciona un municipio para buscar:", ["Seleccionar..."] + municipios)

    if municipio_sel != "Seleccionar...":
        busqueda = [g for g in datos if g["Municipio"] == municipio_sel]
        for g in busqueda:
            mostrar_gasolinera(g)
else:
    st.error("No se ha podido conectar con el Ministerio de Energía.")
