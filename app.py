import streamlit as st
import requests
import pandas as pd

# 1. Configuración de App Nativa
st.set_page_config(
    page_title="Precios Combustible", 
    page_icon="⛽", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 2. CSS Avanzado: Look & Feel de Android / iOS
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Ajuste de márgenes para móvil */
        .block-container {
            padding: 1.5rem 0.8rem !important;
            max-width: 100% !important;
        }
        
        /* Tarjetas estilo Material Design */
        .gas-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 1px solid #f0f0f0;
        }
        
        /* Botones grandes y táctiles */
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.5rem;
        }
        .stLinkButton>a {
            width: 100%;
            text-align: center;
            border-radius: 10px;
            font-weight: 600;
        }
        
        /* Resalte visual para el buscador */
        .stTextInput>div>div>input {
            border: 2px solid #ff4b4b !important;
            border-radius: 10px !important;
            font-size: 1.1rem !important;
            padding: 0.75rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Descarga de datos
@st.cache_data(ttl=3600, show_spinner="Sincronizando precios...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except:
        return None

# 4. Gestión Indestructible de Favoritos (Vía URL Params)
def obtener_favoritos():
    if "favs" in st.query_params:
        # Usamos el separador | para no interferir con las comas de las direcciones
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
st.title("⛽ Precios Combustible")

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    
    # === SECCIÓN FAVORITOS ===
    if favs_ids:
        st.subheader("⭐ Mis Estaciones")
        
        orden = st.radio("Mejor precio:", ["Diésel A", "Gasolina 95 E5"], horizontal=True, label_visibility="collapsed")
        col_sort = "Precio Gasoleo A" if orden == "Diésel A" else "Precio Gasolina 95 E5"
        
        lista_favs = [g for g in datos if f"{g['Rótulo']}~{g['Dirección']}" in favs_ids]
        df_favs = pd.DataFrame(lista_favs)
        
        df_favs["Precio Gasoleo A"] = pd.to_numeric(df_favs["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
        df_favs["Precio Gasolina 95 E5"] = pd.to_numeric(df_favs["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
        df_favs = df_favs.sort_values(by=col_sort)
        
        for _, gas in df_favs.iterrows():
            g_id = f"{gas['Rótulo']}~{gas['Dirección']}"
            with st.container(border=True):
                st.markdown(f"### {gas['Rótulo']}")
                st.caption(f"📍 {gas['Dirección']} ({gas['Municipio']})")
                
                c1, c2 = st.columns(2)
                c1.metric("Diésel A", f"{gas['Precio Gasoleo A']} €" if pd.notna(gas['Precio Gasoleo A']) else "N/A")
                c2.metric("G95 E5", f"{gas['Precio Gasolina 95 E5']} €" if pd.notna(gas['Precio Gasolina 95 E5']) else "N/A")
                
                b1, b2 = st.columns(2)
                lat = str(gas["Latitud"]).replace(",", ".")
                lon = str(gas["Longitud (WGS84)"]).replace(",", ".")
                
                with b1:
                    if st.button("Quitar ❌", key=f"del-{g_id}"):
                        eliminar_favorito(g_id)
                with b2:
                    st.link_button("Ruta 🗺️", f"https://www.google.com/maps?q={lat},{lon}")
        
        st.divider()

    # === SECCIÓN BUSCADOR EN VIVO ===
    st.subheader("🔍 Buscar Municipio")
    
    # Buscador de texto libre, mucho más cómodo en móvil que un desplegable enorme
    busqueda = st.text_input("Escribe tu municipio (ej: Irura, Tolosa)...", placeholder="Toca aquí para escribir...").upper()

    if len(busqueda) >= 3: # Empieza a buscar a partir de 3 letras para no saturar
        resultados = [g for g in datos if busqueda in g["Municipio"].upper()]
        
        if resultados:
            st.success(f"Se han encontrado {len(resultados)} estaciones.")
            for g in resultados:
                g_id = f"{g['Rótulo']}~{g['Dirección']}"
                with st.container(border=True):
                    st.markdown(f"**{g['Rótulo']}**")
                    st.caption(f"{g['Dirección']} ({g['Municipio']})")
                    
                    d_precio = g['Precio Gasoleo A'] if g['Precio Gasoleo A'] else "--"
                    g_precio = g['Precio Gasolina 95 E5'] if g['Precio Gasolina 95 E5'] else "--"
                    st.write(f"⛽ **Diésel:** {d_precio} € | **G95:** {g_precio} €")
                    
                    if g_id in favs_ids:
                        st.info("⭐ Guardada en tus estaciones")
                    else:
                        if st.button("Añadir ⭐", key=f"add-{g_id}", type="primary"):
                            guardar_favorito(g_id)
        else:
            st.warning("No se ha encontrado ningún municipio con ese nombre.")
    elif len(busqueda) > 0:
        st.caption("Escribe al menos 3 letras para buscar...")

else:
    st.error("No se han podido cargar los precios del Ministerio. Reintenta en unos minutos.")
