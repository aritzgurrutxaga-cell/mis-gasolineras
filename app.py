import streamlit as st
import streamlit.components.v1 as components
import requests

# === 1. CONFIGURACIÓN LIMPIA ===
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
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #ccc !important;
        }
        /* Pequeño ajuste para que los botones de borrar no tengan un padding excesivo */
        .stButton button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. FUNCIÓN JS PARA OCULTAR TECLADO EN MÓVILES ===
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# === 3. CARGA DE DATOS ===
@st.cache_data(ttl=3600, show_spinner="Sincronizando con el Ministerio...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# === 4. GESTIÓN DE FAVORITOS (Vía URL Params) ===
def obtener_favoritos():
    if "favs" in st.query_params:
        return st.query_params["favs"].split("|")
    return []

def guardar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas not in actuales:
        actuales.append(id_gas)
        st.query_params["favs"] = "|".join(actuales)
        st.toast("¡Añadido a favoritos!", icon="✅")

def eliminar_favorito(id_gas):
    actuales = obtener_favoritos()
    if id_gas in actuales:
        actuales.remove(id_gas)
        if actuales:
            st.query_params["favs"] = "|".join(actuales)
        else:
            del st.query_params["favs"]
        st.toast("Eliminado de favoritos", icon="🗑️")


# ==========================================
# === INICIO DE LA INTERFAZ DE USUARIO ===
# ==========================================

st.markdown("<h2 style='text-align: center;'>⛽ Precios Combustible</h2>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    favs_ids = obtener_favoritos()
    # Limpiamos y ordenamos los municipios
    municipios_unicos = sorted(list(set([g.get("Municipio", "") for g in datos if g.get("Municipio")])))
    
    # --- SECCIÓN A: BÚSQUEDA ---
    st.markdown("### 🔍 Buscar Gasolineras")
    municipio_sel = st.selectbox(
        "Selecciona un municipio:",
        options=[""] + municipios_unicos,
        index=0
    )

    if municipio_sel:
        # Filtramos los datos por el municipio elegido
        resultados = [g for g in datos if g.get("Municipio") == municipio_sel]
        
        st.caption(f"Se han encontrado {len(resultados)} gasolineras en {municipio_sel}.")
        
        for gas in resultados:
            id_gas = gas.get("IDEESS")
            nombre = gas.get("Rótulo", "Gasolinera")
            direccion = gas.get("Dirección", "")
            precio_95 = gas.get("Precio Gasolina 95 E5", "N/D")
            
            # Solo mostramos el botón de añadir si NO está ya en favoritos
            if id_gas not in favs_ids:
                with st.container():
                    col1, col2 = st.columns([0.7, 0.3])
                    with col1:
                        st.markdown(f"**{nombre}**")
                        st.caption(f"📍 {direccion} | 💶 **{precio_95} €/L**")
                    with col2:
                        st.button(
                            "⭐ Añadir", 
                            key=f"add_{id_gas}", 
                            on_click=guardar_favorito, 
                            args=(id_gas,)
                        )
                    st.markdown("<hr style='margin: 0.5rem 0; border-top: 1px solid #f0f0f0;'>", unsafe_allow_html=True)

    st.markdown("---")

    # --- SECCIÓN B: FAVORITOS ---
    st.markdown("### ⭐ Tus Favoritas")
    
    if not favs_ids:
        st.info("Aún no tienes gasolineras guardadas. Busca un municipio y añade algunas.")
    else:
        # Extraemos solo las gasolineras que coinciden con los IDs guardados
        gasolineras_favs = [g for g in datos if str(g.get("IDEESS")) in favs_ids]
        
        for gasolinera in gasolineras_favs:
            id_gas = str(gasolinera.get("IDEESS"))
            nombre = gasolinera.get("Rótulo", "Gasolinera")
            direccion = gasolinera.get("Dirección", "")
            precio_gasolina = gasolinera.get("Precio Gasolina 95 E5", "N/D")
            precio_diesel = gasolinera.get("Precio Gasoleo A", "N/D") # Añadido el diésel por si acaso
            
            # La tarjeta de favoritos con la "X" en la esquina superior derecha
            with st.container():
                col_info, col_btn = st.columns([0.85, 0.15])
                
                with col_info:
                    st.markdown(f"**{nombre}**")
                    st.caption(f"📍 {direccion}")
                
                with col_btn:
                    # Botón de borrar anclado a la derecha
                    st.button(
                        "❌", 
                        key=f"del_{id_gas}", 
                        help="Eliminar de favoritos", 
                        on_click=eliminar_favorito, 
                        args=(id_gas,)
                    )
                
                # Precios destacados debajo
                st.markdown(f"""
                    <div style='display: flex; gap: 15px; margin-top: -5px;'>
                        <span style='color: #2c3e50; font-size: 1.1rem;'>⛽ 95: <b>{precio_gasolina} €/L</b></span>
                        <span style='color: #2c3e50; font-size: 1.1rem;'>🛢️ Diésel: <b>{precio_diesel} €/L</b></span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 1rem 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

else:
    st.error("No se pudieron cargar los datos. Por favor, recarga la página en unos minutos.")
