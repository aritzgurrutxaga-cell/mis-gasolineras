import streamlit as st
import requests
import pandas as pd
from streamlit_local_storage import LocalStorage

# 1. Configuración Profesional de la App
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# Inicializar almacenamiento local
local_storage = LocalStorage()

@st.cache_data(ttl=3600, show_spinner="Actualizando precios a nivel nacional...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# --- LÓGICA DE ALMACENAMIENTO ---
def obtener_favoritos():
    favs = local_storage.getItem("gas_favs")
    return favs if favs else []

def guardar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas not in actuales:
        actuales.append(id_gas)
        local_storage.setItem("gas_favs", actuales)
        st.rerun()

def eliminar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas in actuales:
        actuales.remove(id_gas)
        local_storage.setItem("gas_favs", actuales)
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("⛽ Precios Combustible")
st.markdown("Consulta y compara las estaciones de servicio actualizadas.")

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    
    # Creación de Pestañas para una navegación limpia
    tab_favs, tab_buscar = st.tabs(["⭐ Mis Favoritos", "🔍 Buscar y Añadir"])
    
    # ==========================================
    # PESTAÑA 1: FAVORITOS (Con ordenación dinámica)
    # ==========================================
    with tab_favs:
        if favs_ids:
            st.write("### Tus estaciones guardadas")
            
            # Selector de ordenación integrado en la interfaz
            orden_combustible = st.radio(
                "Ordenar ranking por precio de:", 
                ["Diésel A", "Gasolina 95 E5"], 
                horizontal=True
            )
            col_sort = "Precio Gasoleo A" if orden_combustible == "Diésel A" else "Precio Gasolina 95 E5"
            
            # Extraemos solo los datos de los favoritos para ordenarlos
            lista_favs = [g for g in datos if f"{g['Rótulo']}-{g['Dirección']}" in favs_ids]
            df_favs = pd.DataFrame(lista_favs)
            
            # Limpieza y ordenación matemática
            df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
            df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
            df_favs = df_favs.sort_values(by=col_sort)
            
            # Renderizado de las tarjetas ordenadas
            for _, gas in df_favs.iterrows():
                g_id = f"{gas['Rótulo']}-{gas['Dirección']}"
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{gas['Rótulo']}**")
                    c1.caption(f"📍 {gas['Dirección']} ({gas['Municipio']})")
                    if c2.button("❌ Quitar", key=f"del-{g_id}"):
                        eliminar_favorito(g_id)
                    
                    p1, p2, p3 = st.columns(3)
                    p1.metric("Diésel A", f"{gas['Precio Gasoleo A']} €" if pd.notna(gas['Precio Gasoleo A']) else "N/A")
                    p2.metric("G95 E5", f"{gas['Precio Gasolina 95 E5']} €" if pd.notna(gas['Precio Gasolina 95 E5']) else "N/A")
                    
                    lat = str(gas["Latitud"]).replace(",", ".")
                    lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                    p3.write("")
                    p3.link_button("🗺️ Ruta", f"https://www.google.com/maps?q={lat},{lon}")
        else:
            st.info("Aún no tienes gasolineras favoritas. Ve a la pestaña 'Buscar y Añadir' para empezar a guardar tus estaciones habituales.")

    # ==========================================
    # PESTAÑA 2: BUSCADOR
    # ==========================================
    with tab_buscar:
        st.write("### Explorar nuevos municipios")
        municipios = sorted(list(set([g["Municipio"] for g in datos])))
        municipio_sel = st.selectbox("Selecciona Municipio:", ["Seleccionar..."] + municipios)

        if municipio_sel != "Seleccionar...":
            resultados = [g for g in datos if g["Municipio"] == municipio_sel]
            
            for g in resultados:
                g_id = f"{g['Rótulo']}-{g['Dirección']}"
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    col_info.markdown(f"**{g['Rótulo']}**")
                    col_info.caption(f"{g['Dirección']}")
                    
                    if g_id in favs_ids:
                        col_btn.success("⭐ Guardada")
                    else:
                        if col_btn.button("Añadir", key=f"add-{g_id}", type="primary"):
                            guardar_favorito(g_id)
                    
                    # Mostrar precios rápidos en la búsqueda
                    d_precio = g['Precio Gasoleo A'] if g['Precio Gasoleo A'] else "--"
                    g_precio = g['Precio Gasolina 95 E5'] if g['Precio Gasolina 95 E5'] else "--"
                    st.write(f"⛽ **Diésel:** {d_precio} €/L | **G95:** {g_precio} €/L")

else:
    st.error("No se han podido cargar los precios. El servicio del Gobierno podría estar en mantenimiento.")
