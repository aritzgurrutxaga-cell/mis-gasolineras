import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd

# 1. Configuración de App Nativa
st.set_page_config(
    page_title="Precios Combustible", 
    page_icon="⛽", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 2. CSS ESTRICTO: Bloqueo de apilamiento en móviles
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding: 1rem 0.5rem 0rem 0.5rem !important;
            max-width: 100% !important;
        }
        
        /* Ajuste de márgenes de texto */
        p {
            margin-bottom: 0rem !important;
            font-size: 0.85rem !important;
        }
        
        /* 🛑 EL TRUCO MAGICO: Forzar a Streamlit a NO apilar las columnas en móvil */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important; /* Prohíbe que salten a la siguiente línea */
            align-items: center !important; /* Centra los botones con el texto verticalmente */
            gap: 0.3rem !important; /* Reduce el espacio entre columnas */
        }
        
        /* Permite que las columnas se encojan si la pantalla es muy pequeña */
        div[data-testid="column"] {
            min-width: 0 !important;
        }

        /* Botones ultra-compactos para que quepan en la misma línea */
        .stButton>button, .stLinkButton>a {
            padding: 0.1rem 0.2rem !important;
            min-height: 0px !important;
            line-height: 1.2 !important;
            border-radius: 6px;
            font-size: 0.8rem !important;
            width: 100%;
        }
        
        hr {
            margin: 0.4em 0em !important;
            border-top: 1px solid #e0e0e0;
        }
        
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #ff4b4b !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Función JS para ocultar teclado
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 4. Descarga de datos
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 5. Gestión de Favoritos
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
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    # === SECCIÓN AÑADIR GASOLINERAS ===
    with st.expander("➕ Añadir más gasolineras", expanded=not bool(favs_ids)):
        municipio_sel = st.selectbox(
            "Buscar municipio:", options=municipios_unicos, index=None, placeholder="Escribe para buscar (ej: IRU...)"
        )
        
        if municipio_sel:
            ocultar_teclado()
            resultados = [g for g in datos if g["Municipio"] == municipio_sel]
            
            for g in resultados:
                g_id = f"{g['Rótulo']}~{g['Dirección']}"
                st.markdown(f"**{g['Rótulo']}** <span style='font-size:0.75em; color:gray;'>{g['Dirección'][:20]}...</span>", unsafe_allow_html=True)
                
                # REPARTO DE ESPACIO: D (25%), G (25%), Mapa (30%), Añadir (20%)
                c_d, c_g, c_map, c_add = st.columns([2.5, 2.5, 3, 2])
                
                c_d.markdown(f"**D:** {g['Precio Gasoleo A']}€" if g['Precio Gasoleo A'] else "**D:** --")
                c_g.markdown(f"**G:** {g['Precio Gasolina 95 E5']}€" if g['Precio Gasolina 95 E5'] else "**G:** --")
                
                with c_map:
                    lat = str(g["Latitud"]).replace(",", ".")
                    lon = str(g["Longitud (WGS84)"]).replace(",", ".")
                    st.link_button("📍 Maps", f"https://www.google.com/maps?q={lat},{lon}")
                
                with c_add:
                    if g_id in favs_ids:
                        st.markdown("<div style='text-align:center;'>✅</div>", unsafe_allow_html=True)
                    else:
                        if st.button("⭐", key=f"add-{g_id}"): guardar_favorito(g_id)
                st.markdown("<hr>", unsafe_allow_html=True)

    # === SECCIÓN TUS FAVORITOS ===
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
            
            # Título y dirección sutil en una línea
            st.markdown(f"**{gas['Rótulo']}** <span style='font-size:0.75em; color:gray;'>{gas['Dirección'][:20]}...</span>", unsafe_allow_html=True)
            
            # 🛑 LA FILA ÚNICA PROMETIDA
            # Proporciones calculadas para que no se pise el texto con los botones
            col_d, col_g, col_map, col_del = st.columns([2.5, 2.5, 3, 2])
            
            col_d.markdown(f"**D:** {gas['Precio Gasoleo A']}€" if pd.notna(gas['Precio Gasoleo A']) else "**D:** --")
            col_g.markdown(f"**G:** {gas['Precio Gasolina 95 E5']}€" if pd.notna(gas['Precio Gasolina 95 E5']) else "**G:** --")
            
            with col_map:
                lat = str(gas["Latitud"]).replace(",", ".")
                lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                st.link_button("📍 Maps", f"https://www.google.com/maps?q={lat},{lon}")
            
            with col_del:
                if st.button("🗑️", key=f"del-{g_id}"): eliminar_favorito(g_id)
            
            st.markdown("<hr>", unsafe_allow_html=True)
