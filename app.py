import streamlit as st
import requests
import pandas as pd

# 1. Configuración limpia
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding: 1rem !important;
        }
        hr {
            margin: 0.8rem 0 !important;
        }
        /* Ajustes para que la caja de sugerencias sea elegante */
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #ccc !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Carga de Datos
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 3. Gestión de Favoritos
def obtener_favoritos():
    if "favs" in st.query_params:
        return st.query_params["favs"].split("|")
    return []

def guardar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas not in actuales:
        actuales.append(id_gas)
        st.query_params["favs"] = "|".join(actuales)
        st.toast("Añadido a favoritos", icon="✅")
        st.rerun()

def eliminar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas in actuales:
        actuales.remove(id_gas)
        if actuales:
            st.query_params["favs"] = "|".join(actuales)
        else:
            del st.query_params["favs"]
        st.toast("Eliminado de favoritos", icon="🗑️")
        st.rerun()

# --- INICIO DE LA INTERFAZ ---
st.markdown("<h2 style='text-align: center;'>⛽ Precios Combustible</h2>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    # === 1. SECCIÓN DE BÚSQUEDA ===
    municipio_sel = st.selectbox(
        "🔍 Buscar municipio:",
        options=municipios_unicos,
        index=None,
        placeholder="Empieza a escribir (ej. IRU) y elige en la lista..."
    )
    
    if municipio_sel:
        resultados = [g for g in datos if g["Municipio"] == municipio_sel]
        
        st.caption(f"Resultados para **{municipio_sel}**:")
        for g in resultados:
            g_id = f"{g['Rótulo']}~{g['Dirección']}"
            
            with st.container(border=True):
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    # AQUÍ ESTÁ EL CAMBIO: Rótulo - Municipio en el título principal
                    st.markdown(f"**{g['Rótulo']} - {g['Municipio']}**<br><span style='color: gray; font-size: 0.85em;'>{g['Dirección']}</span>", unsafe_allow_html=True)
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

    # === 2. SECCIÓN DE FAVORITOS ===
    if favs_ids:
        c_title, c_sort = st.columns([1.5, 1])
        with c_title:
            st.write("### ⭐ Guardadas")
        with c_sort:
            orden = st.radio("Orden", ["Diésel", "G95"], horizontal=True, label_visibility="collapsed")
            col_sort = "Precio Gasoleo A" if orden == "Diésel" else "Precio Gasolina 95 E5"
        
        lista_favs = [g for g in datos if f"{g['Rótulo']}~{g['Dirección']}" in favs_ids]
        df_favs = pd.DataFrame(lista_favs)
        
        df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df_favs = df_favs.sort_values(by=col_sort)
        
        for _, gas in df_favs.iterrows():
            g_id = f"{gas['Rótulo']}~{gas['Dirección']}"
            
            with st.container(border=True):
                # AQUÍ ESTÁ EL CAMBIO: Rótulo - Municipio en los favoritos también
                st.markdown(f"**{gas['Rótulo']} - {gas['Municipio']}**<br><span style='color: gray; font-size: 0.9em;'>{gas['Dirección']}</span>", unsafe_allow_html=True)
                
                d_val = f"{gas['Precio Gasoleo A']} €" if pd.notna(gas['Precio Gasoleo A']) else "--"
                g_val = f"{gas['Precio Gasolina 95 E5']} €" if pd.notna(gas['Precio Gasolina 95 E5']) else "--"
                st.markdown(f"**Diésel:** {d_val}   |   **G95:** {g_val}")
                
                if st.button("🗑️ Borrar", key=f"del-{g_id}", use_container_width=True):
                    eliminar_favorito(g_id)
                    
else:
    st.error("No se ha podido conectar con el Ministerio en este momento.")
