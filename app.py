import streamlit as st
import requests
import pandas as pd
from streamlit_local_storage import LocalStorage

# 1. Configuración de página optimizada
st.set_page_config(
    page_title="Precios Combustible", 
    page_icon="⛽", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# Inyección de CSS para que el buscador destaque y los botones sean perfectos en Android
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            font-weight: bold;
        }
        .stLinkButton>a {
            width: 100%;
            text-align: center;
            border-radius: 8px;
            font-weight: bold;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
        /* Hacemos que la caja de búsqueda sea más evidente */
        div[data-baseweb="select"] {
            border: 2px solid #ff4b4b !important;
            border-radius: 8px !important;
        }
    </style>
""", unsafe_allow_html=True)

local_storage = LocalStorage()

@st.cache_data(ttl=3600, show_spinner="Actualizando precios oficiales...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

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

# --- INICIO DE LA APLICACIÓN ---
st.title("⛽ Precios Combustible")

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    
    # ==========================================
    # SECCIÓN 1: FAVORITOS (Si existen)
    # ==========================================
    if favs_ids:
        st.subheader("⭐ Mis Favoritos")
        
        # Opciones de ordenación dinámicas
        orden_combustible = st.radio(
            "Ordenar por el precio más bajo de:", 
            ["Diésel A", "Gasolina 95 E5"], 
            horizontal=True
        )
        col_sort = "Precio Gasoleo A" if orden_combustible == "Diésel A" else "Precio Gasolina 95 E5"
        
        # Filtramos y preparamos el DataFrame de favoritos
        lista_favs = [g for g in datos if f"{g['Rótulo']}-{g['Dirección']}" in favs_ids]
        df_favs = pd.DataFrame(lista_favs)
        
        df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df_favs = df_favs.sort_values(by=col_sort)
        
        # Pintamos las tarjetas
        for _, gas in df_favs.iterrows():
            g_id = f"{gas['Rótulo']}-{gas['Dirección']}"
            with st.container(border=True):
                st.markdown(f"**{gas['Rótulo']}**")
                st.caption(f"📍 {gas['Dirección']} ({gas['Municipio']})")
                
                p1, p2 = st.columns(2)
                p1.metric("Diésel A", f"{gas['Precio Gasoleo A']} €" if pd.notna(gas['Precio Gasoleo A']) else "N/A")
                p2.metric("G95 E5", f"{gas['Precio Gasolina 95 E5']} €" if pd.notna(gas['Precio Gasolina 95 E5']) else "N/A")
                
                b1, b2 = st.columns(2)
                lat = str(gas["Latitud"]).replace(",", ".")
                lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                
                with b1:
                    if st.button("❌ Quitar", key=f"del-{g_id}"):
                        eliminar_favorito(g_id)
                with b2:
                    st.link_button("🗺️ Ruta", f"https://www.google.com/maps?q={lat},{lon}")
        
        st.divider() # Línea separadora elegante para no mezclar secciones
    else:
        # Mensaje de bienvenida si la app está "limpia"
        st.info("👋 ¡Hola! Aún no tienes gasolineras favoritas. Usa el buscador de abajo para encontrar y guardar las estaciones que más utilices.")

    # ==========================================
    # SECCIÓN 2: BUSCADOR UNIFICADO
    # ==========================================
    st.subheader("🔍 Buscar y Añadir")
    
    municipios = sorted(list(set([g["Municipio"] for g in datos])))
    
    # Truco de UX: La primera opción está en blanco pero con un texto que invita a interactuar
    municipio_sel = st.selectbox(
        "Escribe o selecciona tu municipio:", 
        options=[""] + municipios, 
        index=0,
        format_func=lambda x: "Toca aquí para buscar..." if x == "" else x
    )

    if municipio_sel != "":
        resultados = [g for g in datos if g["Municipio"] == municipio_sel]
        
        if resultados:
            st.success(f"Se han encontrado {len(resultados)} gasolineras en {municipio_sel}.")
            for g in resultados:
                g_id = f"{g['Rótulo']}-{g['Dirección']}"
                with st.container(border=True):
                    st.markdown(f"**{g['Rótulo']}**")
                    st.caption(f"{g['Dirección']}")
                    
                    d_precio = g['Precio Gasoleo A'] if g['Precio Gasoleo A'] else "--"
                    g_precio = g['Precio Gasolina 95 E5'] if g['Precio Gasolina 95 E5'] else "--"
                    st.write(f"⛽ **Diésel:** {d_precio} € | **G95:** {g_precio} €")
                    
                    if g_id in favs_ids:
                        st.success("⭐ Ya está en tus Favoritos")
                    else:
                        if st.button("Añadir a Favoritos ⭐", key=f"add-{g_id}", type="primary"):
                            guardar_favorito(g_id)
        else:
            st.warning("No hay datos disponibles para este municipio en este momento.")

else:
    st.error("No se han podido cargar los precios del Ministerio. Es posible que el servicio esté en mantenimiento. Vuelve a intentarlo en unos minutos.")
