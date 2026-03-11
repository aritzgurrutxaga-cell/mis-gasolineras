import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np

# 1. Configuración (Tu Versión 1)
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

# 2. Función JS para móviles (Tu Versión 1)
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 3. Carga de Datos - AJUSTE DE COMPATIBILIDAD
@st.cache_data(ttl=3600, show_spinner="Sincronizando...")
def cargar_datos():
    # Usamos la URL sin la barra final, que es más estándar para REST
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres"
    try:
        # Algunos servidores bloquean peticiones sin un User-Agent de navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        # Añadimos verify=False solo si el error de SSL persiste
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        # Si falla, intentamos una vez más con una configuración más relajada
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25, verify=False)
            return r.json()["ListaEESSPrecio"]
        except:
            return None

# 4. Cálculo de distancia (Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- LÓGICA DE LA APP ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    
    # Limpieza de datos (necesaria para operar)
    df["Lat"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["Lon"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["D"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')

    municipios_unicos = sorted(df["Municipio"].unique())
    
    # 5. Interfaz de usuario
    with st.container(border=True):
        muni_sel = st.selectbox("📍 Municipio actual:", options=municipios_unicos, index=None)
        col1, col2 = st.columns(2)
        with col1:
            radio = st.slider("Radio (Km):", 1, 50, 10)
        with col2:
            combustible = st.radio("Ordenar por:", ["Diésel", "G95"], horizontal=True)
            target = "D" if combustible == "Diésel" else "G95"

    if muni_sel:
        ocultar_teclado()
        
        # Punto de referencia: primera gasolinera del municipio elegido
        ref = df[df["Municipio"] == muni_sel].iloc[0]
        
        # Calcular distancias de todas
        df["Distancia"] = calcular_distancia(ref["Lat"], ref["Lon"], df["Lat"], df["Lon"])
        
        # Filtrar por radio y que tengan precio
        res = df[(df["Distancia"] <= radio) & (df[target].notna())].sort_values(by=target)

        st.divider()
        st.write(f"### 📉 {combustible} más barato a {radio}km")

        for _, gas in res.head(15).iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{gas['Rótulo']}**")
                    st.caption(f"{gas['Dirección']} ({gas['Municipio']})")
                    st.write(f"📍 a {gas['Distancia']:.1f} km")
                with c2:
                    st.markdown(f"### {gas[target]}€")
                    link = f"https://www.google.com/maps?q={gas['Lat']},{gas['Lon']}"
                    st.link_button("Ir", link, use_container_width=True)
else:
    st.error("Error crítico de conexión. El servidor del Ministerio no responde.")
