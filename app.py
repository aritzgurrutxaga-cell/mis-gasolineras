import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import urllib3

# Desactivamos avisos de seguridad SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1rem !important; }
        .titulo-una-linea {
            text-align: center;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

def ocultar_teclado():
    components.html("<script>window.parent.document.activeElement.blur();</script>", height=0, width=0)

# Carga de datos con "Rotación de Estrategia"
@st.cache_data(ttl=300, show_spinner="Intentando saltar el bloqueo del Ministerio...")
def cargar_datos():
    # Probamos la URL sin la barra final (a veces el firewall bloquea rutas específicas)
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    try:
        # Intentamos la petición con un tiempo de espera generoso
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        return response.json()["ListaEESSPrecio"]
    except Exception as e:
        return None

def calcular_distancia(lat1, lon1, lat2, lon2):
    # Fórmula de Haversine para precisión en km
    R = 6371.0 
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# --- INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        muni_sel = st.selectbox("📍 Municipio base:", options=municipios_unicos, index=None, placeholder="Selecciona tu ciudad...")
        c1, c2 = st.columns(2)
        with c1:
            radio = st.slider("Radio (Km):", 1, 50, 10)
        with c2:
            tipo = st.radio("Precio de:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    if muni_sel:
        ocultar_teclado()
        
        # Procesar coordenadas y precios
        df["lat_n"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_n"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["p_n"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        # Referencia del municipio
        ref = df[df["Municipio"] == muni_sel].iloc[0]
        df["Distancia"] = calcular_distancia(ref["lat_n"], ref["lon_n"], df["lat_n"], df["lon_n"])
        
        # Filtrado y ordenación
        res = df[(df["Distancia"] <= radio) & (df["p_n"].notna())].sort_values(by="p_n")

        st.divider()
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{g['Rótulo']}**")
                        st.caption(f"{g['Dirección']} ({g['Municipio']})")
                        st.write(f"💰 **{g[col_precio]} €** | 📍 {g['Distancia']:.1f} km")
                    with col_btn:
                        map_url = f"https://www.google.com/maps?q={g['lat_n']},{g['lon_n']}"
                        st.link_button("Ir", map_url, use_container_width=True)
        else:
            st.info("No hay gasolineras baratas en este radio.")
else:
    st.error("❌ El Ministerio sigue bloqueando la conexión.")
    st.info("💡 **Dato clave:** Si ejecutas este mismo código en tu ordenador (Localhost), funcionará perfectamente. El problema es la 'lista negra' que el Ministerio tiene aplicada a Streamlit Cloud.")
    if st.button("🔄 Intentar de nuevo"):
        st.rerun()
