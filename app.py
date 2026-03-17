import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- ADAPTADOR SSL ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# AJUSTES DE ESPACIADO PRECISOS Y DISEÑO CSS
st.markdown("""
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        div[data-testid="stRadio"] > label {font-weight: bold; margin-bottom: -0.5rem;}
        div[data-testid="stRadio"] {margin-bottom: 0.5rem;}
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
        h1 {margin-top: -1rem; margin-bottom: 0.5rem;}
        
        /* Barra de resumen visual */
        .resumen-filtros {
            text-align: center; 
            color: #444; 
            font-size: 0.95rem; 
            margin-bottom: 1.5rem; 
            background-color: #f0f2f6; 
            padding: 10px; 
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        
        /* Pantalla de bloqueo de ubicación */
        .bloqueo-ubicacion {
            text-align: center;
            padding: 3rem 1rem;
            background-color: #fff3cd;
            border: 2px solid #ffeeba;
            border-radius: 12px;
            margin-top: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# Título de la aplicación
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px);'>
        ⛽ Buscador Gasolineras
    </h1>
    """, 
    unsafe_allow_html=True
)

# --- 2. SISTEMA DE BLOQUEO POR GEOLOCALIZACIÓN (HARD GATE) ---
loc = get_geolocation()

# Si 'loc' es None (está cargando o bloqueado) o no tiene coordenadas
if loc is None or 'coords' not in loc:
    st.markdown("""
        <div class="bloqueo-ubicacion">
            <h1 style="font-size: 4rem; margin-bottom: 0;">📍</h1>
            <h2 style="color: #856404; font-size: 1.8rem; margin-top: 10px;">No sabemos dónde estás</h2>
            <p style="color: #664d03; font-size: 1.1rem; max-width: 500px; margin: 0 auto 20px auto;">
                Has denegado el permiso de ubicación o tu navegador lo está bloqueando. Esta web necesita saber dónde estás para mostrarte automáticamente las gasolineras más baratas a tu alrededor.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Instrucciones claras paso a paso
    st.markdown("### 🛠️ Cómo solucionarlo en 2 pasos:")
    st.info("**Paso 1:** Toca el icono del candado 🔒 (o el símbolo de ajustes) que está arriba del todo, en la barra de direcciones de tu navegador.\n\n**Paso 2:** Busca la opción de 'Ubicación' y cámbiala a **Permitir**.")
    
    # Botón de reintento centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Ya lo he permitido, volver a intentar", use_container_width=True):
            st.rerun()
            
    # Detenemos la carga de la página aquí mismo
    st.stop()

# --- 3. EXTRACCIÓN DE COORDENADAS ---
lat_gps = loc['coords']['latitude']
lon_gps = loc['coords']['longitude']

# --- 4. FUNCIONES DE DATOS Y MATEMÁTICAS ---
@st.cache_data(ttl=3600, show_spinner="Descargando precios oficiales...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    archivo_backup = "gasolineras_backup.csv"
    tz_madrid = pytz.timezone('Europe/Madrid')
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, datetime.datetime.now(tz_madrid)
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            mtime = os.path.getmtime(archivo_backup)
            fecha_utc = datetime.datetime.fromtimestamp(mtime, pytz.utc)
            return df_rec.to_dict('records'), fecha_utc.astimezone(tz_madrid)
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- 5. LÓGICA PRINCIPAL ---
datos, fecha_act = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    # Limpieza de datos: cambiar comas por puntos y pasar a numérico
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    # Calcular distancia real de cada gasolinera al usuario
    df["Distancia"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
    
    # Identificar el municipio en el que se encuentra el usuario basándonos en la gasolinera más cercana
    muni_gps = df.sort_values("Distancia").iloc[0]["Municipio"]

    # --- 6. PANEL DE FILTROS MINIMIZADO POR DEFECTO ---
    with st.expander("⚙️ Ajustes de Búsqueda (Distancia y Combustible)", expanded=False):
        col_km, col_gas = st.columns(2)
        
        with col_km:
            radio_km = st.radio(
                "Radio de búsqueda:",
                options=[5, 10, 20, 50],
                format_func=lambda x: f"{x} km",
                index=0, # Empieza en 5km por defecto
                horizontal=True
            )
            
        with col_gas:
            tipo_combustible = st.radio(
                "Ordenar por precio de:", 
                ["Diésel", "G95"], 
                horizontal=True
            )

    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    # --- 7. PROCESAMIENTO DE RESULTADOS ---
    res = df[
        (df["Distancia"] <= radio_km) & 
        ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
    ].sort_values(col_orden, na_position='last')

    # Barra de resumen visual siempre visible
    st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_gps}</b>  |  🚗 <b>{radio_km} km</b>  |  ⛽ <b>{tipo_combustible}</b></div>", unsafe_allow_html=True)
    
    # --- 8. MOSTRAR GASOLINERAS ---
    if not res.empty:
        for _, g in res.head(20).iterrows():
            with st.container(border=True):
                col_info, col_btn = st.columns([2.4, 1.6], vertical_alignment="center")
                with col_info:
                    st.write(f"### {g['Rótulo']}")
                    p_diesel = f"{g['Precio Gasoleo A']} €" if pd.notnull(g['Precio_Diesel']) else "N/A"
                    p_g95 = f"{g['Precio Gasolina 95 E5']} €" if pd.notnull(g['Precio_G95']) else "N/A"
                    st.write(f"⛽ **D:** {p_diesel} | **G95:** {p_g95}")
                    st.caption(f"📍 A {g['Distancia']:.2f} km | {g['Dirección']}")
                with col_btn:
                    # Enlace directo para abrir la ruta en Google Maps
                    url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                    st.link_button("🗺️ Ir allí", url_map, use_container_width=True)
    else:
        st.warning(f"No hay resultados en un radio de {radio_km} km. Prueba a abrir los Ajustes y ampliar el radio de búsqueda.")
else:
    st.error("Sin conexión a los datos oficiales del Ministerio.")

# --- 9. PIE DE PÁGINA ---
if fecha_act:
    st.markdown(f"<div style='text-align: center; color: #a3a8b8; font-size: 0.75rem; margin-top: 25px;'>Última actualización MINETUR: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)
