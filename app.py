import streamlit as st
import requests
import pandas as pd
from streamlit_local_storage import LocalStorage

# Configuración de página
st.set_page_config(page_title="Gasolineras Pro", page_icon="⛽", layout="centered")

# Inicializar almacenamiento local en el navegador del usuario
local_storage = LocalStorage()

@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

def limpiar_precio(valor):
    if not valor: return None
    try:
        return float(valor.replace(",", "."))
    except:
        return None

# --- LÓGICA DE FAVORITOS ---
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

# --- INTERFAZ ---
st.title("⛽ Gasolineras Pro")
datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    
    # 1. SECCIÓN DE FAVORITOS (Arriba)
    if favs_ids:
        st.subheader("⭐ Tus Gasolineras Habituales")
        for f_id in favs_ids:
            # Buscar datos de la gasolinera guardada
            gas = next((g for g in datos if f"{g['Rótulo']}-{g['Dirección']}" == f_id), None)
            if gas:
                with st.expander(f"⭐ {gas['Rótulo']} - {gas['Municipio']}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Diésel A", f"{gas['Precio Gasoleo A']} €")
                    c2.metric("G95 E5", f"{gas['Precio Gasolina 95 E5']} €")
                    if st.button("Quitar de favoritos", key=f"del-{f_id}"):
                        eliminar_favorito(f_id)
        st.divider()

    # 2. BÚSQUEDA PRINCIPAL
    st.subheader("🔍 Buscar nuevas gasolineras")
    municipios = sorted(list(set([g["Municipio"] for g in datos])))
    municipio_sel = st.selectbox("Selecciona Municipio:", ["Busca un pueblo..."] + municipios)

    if municipio_sel != "Busca un pueblo...":
        resultados = [g for g in datos if g["Municipio"] == municipio_sel]
        
        for g in resultados:
            g_id = f"{g['Rótulo']}-{g['Dirección']}"
            with st.container(border=True):
                col_info, col_btn = st.columns([3, 1])
                col_info.markdown(f"**{g['Rótulo']}**")
                col_info.caption(f"{g['Dirección']}")
                
                # Botón dinámico según si ya es favorito o no
                if g_id in favs_ids:
                    col_btn.write("✅ Guardada")
                else:
                    if col_btn.button("Añadir ⭐", key=f"add-{g_id}"):
                        guardar_favorito(g_id)
                
                # Precios
                p1, p2, p3 = st.columns(3)
                p1.write(f"**Diésel:** {g['Precio Gasoleo A']}€")
                p2.write(f"**G95:** {g['Precio Gasolina 95 E5']}€")
                
                lat = g["Latitud"].replace(",", ".")
                lon = g["Longitud (WGS84)"].replace(",", ".")
                p3.link_button("🗺️ Ir", f"https://www.google.com/maps?q={lat},{lon}")

else:
    st.error("No se han podido cargar los precios. Inténtalo de nuevo.")
