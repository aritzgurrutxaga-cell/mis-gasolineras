import streamlit as st
import requests
import pandas as pd

# 1. Configuración de App Nativa (Compacta)
st.set_page_config(
    page_title="Precios Combustible", 
    page_icon="⛽", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 2. CSS Ultra-Compacto para máxima densidad
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding: 1rem 0.5rem 0rem 0.5rem !important;
            max-width: 100% !important;
        }
        p {
            margin-bottom: 0.1rem !important;
            font-size: 0.95rem !important;
        }
        .stButton>button, .stLinkButton>a {
            padding: 0.1rem !important;
            min-height: 0px !important;
            line-height: 1.5 !important;
            border-radius: 6px;
        }
        hr {
            margin: 0.5em 0em !important;
            border-top: 1px solid #e0e0e0;
        }
        /* Estilo sutil y elegante para la caja predictiva */
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #ff4b4b !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Descarga de datos
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 4. Gestión de Favoritos (Vía URL Params)
def obtener_favoritos():
    if "favs" in st.query_params:
        return st.query_params["favs"].split("|")
    return []

def guardar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas not in actuales:
        actuales.append(id_gas)
        st.query_params["favs"] = "|".join(actuales)
        st.rerun()

def eliminar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas in actuales:
        actuales.remove(id_gas)
        if actuales:
            st.query_params["favs"] = "|".join(actuales)
        else:
            del st.query_params["favs"]
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.markdown("<h3 style='text-align: center; margin-top: -15px;'>⛽ Precios Combustible</h3>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    
    # Extraer todos los municipios únicos para el autocompletado
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    # === SECCIÓN SUPERIOR: AÑADIR MÁS GASOLINERAS ===
    with st.expander("➕ Añadir más gasolineras", expanded=not bool(favs_ids)):
        
        # Buscador Predictivo (Autocompletado en vivo)
        municipio_sel = st.selectbox(
            "Buscar municipio:",
            options=municipios_unicos,
            index=None, # Para que empiece vacío
            placeholder="Escribe para buscar (ej: IRU...)"
        )
        
        if municipio_sel:
            resultados = [g for g in datos if g["Municipio"] == municipio_sel]
            st.caption(f"Se han encontrado {len(resultados)} estaciones en {municipio_sel}:")
            
            for g in resultados:
                g_id = f"{g['Rótulo']}~{g['Dirección']}"
                
                # Fila compacta de resultados
                st.markdown(f"**{g['Rótulo']}** <span style='font-size:0.8em; color:gray;'>{g['Dirección'][:25]}...</span>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([4, 4, 3])
                c1.markdown(f"<span style='font-size:0.85em;'>**D:** {g['Precio Gasoleo A'] if g['Precio Gasoleo A'] else '--'}€</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='font-size:0.85em;'>**G:** {g['Precio Gasolina 95 E5'] if g['Precio Gasolina 95 E5'] else '--'}€</span>", unsafe_allow_html=True)
                
                with c3:
                    if g_id in favs_ids:
                        st.markdown("<span style='font-size:0.85em; color:green;'>✅ Guardada</span>", unsafe_allow_html=True)
                    else:
                        if st.button("Añadir ⭐", key=f"add-{g_id}"):
                            guardar_favorito(g_id)
                st.markdown("<hr>", unsafe_allow_html=True)

    # === SECCIÓN INFERIOR: TUS FAVORITOS (LISTA COMPACTA) ===
    if favs_ids:
        orden = st.radio("Ordenar ranking:", ["Diésel", "Gasolina 95"], horizontal=True, label_visibility="collapsed")
        col_sort = "Precio Gasoleo A" if orden == "Diésel" else "Precio Gasolina 95 E5"
        
        lista_favs = [g for g in datos if f"{g['Rótulo']}~{g['Dirección']}" in favs_ids]
        df_favs = pd.DataFrame(lista_favs)
        
        df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df_favs = df_favs.sort_values(by=col_sort)
        
        st.markdown("<hr style='border-top: 2px solid #333;'>", unsafe_allow_html=True)
        
        for _, gas in df_favs.iterrows():
            g_id = f"{gas['Rótulo']}~{gas['Dirección']}"
            
            st.markdown(f"**{gas['Rótulo']}** <span style='font-size:0.8em; color:gray;'>{gas['Dirección'][:25]}...</span>", unsafe_allow_html=True)
            
            col_d, col_g, col_btn1, col_btn2 = st.columns([3, 3, 2, 2])
            
            d_val = gas['Precio Gasoleo A']
            g_val = gas['Precio Gasolina 95 E5']
            
            col_d.markdown(f"⛽ **D:** {d_val}€" if pd.notna(d_val) else "⛽ **D:** --")
            col_g.markdown(f"⛽ **G:** {g_val}€" if pd.notna(g_val) else "⛽ **G:** --")
            
            with col_btn1:
                if st.button("❌", key=f"del-{g_id}", help="Quitar de favoritos"):
                    eliminar_favorito(g_id)
            with col_btn2:
                lat = str(gas["Latitud"]).replace(",", ".")
                lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                st.link_button("🗺️", f"https://www.google.com/maps?q={lat},{lon}", help="Ver en mapa")
            
            st.markdown("<hr>", unsafe_allow_html=True)

else:
    st.error("Error al cargar datos del Ministerio.")
