import streamlit as st
import requests
import pandas as pd

# 1. Configuración limpia y estable
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding: 1rem !important;
        }
        hr {
            margin: 1rem 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Carga de Datos
@st.cache_data(ttl=3600, show_spinner="Sincronizando con el Ministerio...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 3. Gestión de Favoritos en la URL con Popups Sutiles (Toasts)
def obtener_favoritos():
    if "favs" in st.query_params:
        return st.query_params["favs"].split("|")
    return []

def guardar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas not in actuales:
        actuales.append(id_gas)
        st.query_params["favs"] = "|".join(actuales)
        st.toast("Añadido a favoritos", icon="✅") # POPUP SUTIL
        st.rerun()

def eliminar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas in actuales:
        actuales.remove(id_gas)
        if actuales:
            st.query_params["favs"] = "|".join(actuales)
        else:
            del st.query_params["favs"]
        st.toast("Eliminado de favoritos", icon="🗑️") # POPUP SUTIL
        st.rerun()

# --- INICIO DE LA INTERFAZ ---
st.markdown("<h2 style='text-align: center;'>⛽ Precios Combustible</h2>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    # === 1. SECCIÓN DE BÚSQUEDA (SIEMPRE ARRIBA) ===
    st.subheader("🔍 Buscar gasolineras")
    
    municipio_sel = st.selectbox(
        "Selecciona o escribe el municipio:", 
        options=municipios_unicos, 
        index=None, 
        placeholder="Ej: IRURA"
    )
    
    if municipio_sel:
        resultados = [g for g in datos if g["Municipio"] == municipio_sel]
        
        with st.container(border=True):
            st.write(f"Resultados en **{municipio_sel}**:")
            for g in resultados:
                g_id = f"{g['Rótulo']}~{g['Dirección']}"
                
                # Diseño en dos columnas para resultados de búsqueda (más compacto)
                col_info, col_btn = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"**{g['Rótulo']}**<br><span style='color: gray; font-size: 0.85em;'>{g['Dirección']}</span>", unsafe_allow_html=True)
                    d_val = f"{g['Precio Gasoleo A']} €" if g['Precio Gasoleo A'] else "--"
                    g_val = f"{g['Precio Gasolina 95 E5']} €" if g['Precio Gasolina 95 E5'] else "--"
                    st.markdown(f"<span style='font-size: 0.85em;'><b>D:</b> {d_val} | <b>G:</b> {g_val}</span>", unsafe_allow_html=True)
                
                with col_btn:
                    if g_id in favs_ids:
                        st.button("✅", key=f"saved-{g_id}", disabled=True, use_container_width=True)
                    else:
                        if st.button("⭐ Añadir", key=f"add-{g_id}", type="primary", use_container_width=True):
                            guardar_favorito(g_id)
        st.divider()

    # === 2. SECCIÓN DE FAVORITOS (ABAJO) ===
    if favs_ids:
        st.subheader("⭐ Mis Estaciones Guardadas")
        
        lista_favs = [g for g in datos if f"{g['Rótulo']}~{g['Dirección']}" in favs_ids]
        df_favs = pd.DataFrame(lista_favs)
        
        df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df_favs = df_favs.sort_values(by="Precio Gasoleo A")
        
        for _, gas in df_favs.iterrows():
            g_id = f"{gas['Rótulo']}~{gas['Dirección']}"
            
            with st.container(border=True):
                # Información principal
                st.markdown(f"**{gas['Rótulo']}**<br><span style='color: gray; font-size: 0.9em;'>{gas['Dirección']} ({gas['Municipio']})</span>", unsafe_allow_html=True)
                
                # Precios
                d_val = f"{gas['Precio Gasoleo A']} €" if pd.notna(gas['Precio Gasoleo A']) else "--"
                g_val = f"{gas['Precio Gasolina 95 E5']} €" if pd.notna(gas['Precio Gasolina 95 E5']) else "--"
                st.markdown(f"**Diésel:** {d_val}   |   **Gasolina 95:** {g_val}")
                
                # Botones de acción
                col1, col2 = st.columns(2)
                lat = str(gas["Latitud"]).replace(",", ".")
                lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                
                col1.link_button("📍 Maps", f"https://www.google.com/maps?q={lat},{lon}", use_container_width=True)
                if col2.button("🗑️ Borrar", key=f"del-{g_id}", use_container_width=True):
                    eliminar_favorito(g_id)
                    
else:
    st.error("No se ha podido conectar con el Ministerio de Energía en este momento.")
