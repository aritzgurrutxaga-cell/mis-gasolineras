import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation, streamlit_js_eval
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

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# AJUSTES DE ESPACIADO PRECISOS Y DISEÑO CSS
st.markdown("""
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        div[data-testid="stRadio"] > label {font-weight: bold; margin-bottom: -0.5rem;}
        div[data-testid="stRadio"] {margin-bottom: 0.5rem;}
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
        h1 {margin-top: -1rem; margin-bottom: 0.5rem;}
        
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

        /* --- CSS PARA EL BOTÓN GIGANTE --- */
        div[data-testid="stButton"] button[kind="primary"] {
            font-size: 1.4rem !important;
            font-weight: bold !important;
            padding: 1.5rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
            transition: all 0.2s ease-in-out !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 14px rgba(0,0,0,0.2) !important;
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px);'>
        ⛽ Buscador Gasolineras
    </h1>
    """, 
    unsafe_allow_html=True
)

# --- INICIALIZACIÓN DE MEMORIA Y LOCAL STORAGE (MEMORIA PERMANENTE) ---
if 'solicitar_gps' not in st.session_state:
    st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state:
    st.session_state.municipio_guardado = None

# 1. Recuperamos la caché persistente del navegador de forma silenciosa
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# 2. Lógica oculta para guardar en la caché permanente cuando sea necesario
if 'guardar_js' in st.session_state and st.session_state.guardar_js:
    js_code = f"parent.window.localStorage.setItem('muni_gasolineras', '{st.session_state.guardar_js}')"
    streamlit_js_eval(js_expressions=js_code, key=f"set_{st.session_state.guardar_js}")
    st.session_state.guardar_js = None


# Consultar estado de los permisos de ubicación
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")

gps_denegado = (estado_permiso == "denied")

# --- PANTALLA INICIAL PURA (Solo el botón rojo) ---
if not st.session_state.solicitar_gps:
    st.write("") # Espaciador visual
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop()


# ==========================================
# EL USUARIO YA HA PULSADO EL BOTÓN
# ==========================================

loc = None
lat_gps, lon_gps = None, None

# Si NO han bloqueado el GPS y NO tienen un municipio permanente en caché, activamos el GPS
if not gps_denegado and not st.session_state.municipio_guardado:
    loc = get_geolocation()
    if loc is None:
        st.info("⏳ Localizando...")
        st.stop() 
    elif 'coords' not in loc:
        gps_denegado = True
    else:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']


# 2. Carga de Datos
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

datos, fecha_act = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    lat_ref, lon_ref, muni_ref = None, None, None

    if st.session_state.municipio_guardado:
        # Prioridad absoluta: El municipio recuperado de la caché permanente
        muni_ref = st.session_state.municipio_guardado
        fila_muni = df[df["Municipio"] == muni_ref].iloc[0]
        lat_ref, lon_ref = fila_muni["lat_num"], fila_muni["lon_num"]
    elif lat_gps and lon_gps:
        # Si no hay caché, usamos el GPS
        df["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
        muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
        lat_ref, lon_ref = lat_gps, lon_gps

    # --- LÓGICA DE INTERFAZ: BÚSQUEDA MANUAL ---
    abrir_busqueda = True if (gps_denegado and not st.session_state.municipio_guardado) else False

    with st.expander("🔍 Búsqueda manual", expanded=abrir_busqueda):
        
        if gps_denegado and not st.session_state.municipio_guardado:
            st.warning("No hemos podido acceder a tu ubicación. Por favor, selecciona tu municipio a mano.")

        texto_busqueda = st.text_input(
            "📍 Escribe tu municipio:", 
            placeholder="Ej: Madrid, Bilbao, Valencia..."
        )

        municipio_seleccionado = None
        
        if texto_busqueda:
            opciones_filtradas = [m for m in municipios_unicos if texto_busqueda.lower() in m.lower()]
            
            if len(opciones_filtradas) == 1:
                municipio_seleccionado = opciones_filtradas[0]
                st.success(f"Sugerencia encontrada: {municipio_seleccionado}")
            elif len(opciones_filtradas) > 1:
                municipio_seleccionado = st.selectbox("Elige una opción:", options=opciones_filtradas)
            else:
                st.warning("No se ha encontrado ningún municipio con ese nombre.")

        if st.button("✅ Aceptar", type="secondary"):
            if municipio_seleccionado:
                # Guardamos en la memoria RAM temporal
                st.session_state.municipio_guardado = municipio_seleccionado
                # Pasamos la orden para guardarlo en el disco duro del navegador (Local Storage)
                st.session_state.guardar_js = municipio_seleccionado
                st.rerun() 
            else:
                st.error("Por favor, escribe y selecciona un municipio válido primero.")
                
        st.divider()

        col_km, col_gas = st.columns(2)
        with col_km:
            radio_km = st.radio(
                "Radio de búsqueda:",
                options=[5, 10, 20, 50],
                format_func=lambda x: f"{x} km",
                index=0, 
                horizontal=True
            )
        with col_gas:
            tipo_combustible = st.radio(
                "Ordenar por precio de:", 
                ["Diésel", "G95"], 
                horizontal=True
            )

    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    # --- RESULTADOS ---
    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[
            (df["Distancia"] <= radio_km) & 
            ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
        ].sort_values(col_orden, na_position='last')

        if muni_ref:
            st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_ref}</b>  |  🚗 <b>{radio_km} km</b>  |  ⛽ <b>{tipo_combustible}</b></div>", unsafe_allow_html=True)
        
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
                        url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                        st.link_button("🗺️ Ir allí", url_map, use_container_width=True)
        else:
            st.warning(f"No hay resultados a {radio_km} km. Prueba a ampliar el radio en la Búsqueda manual.")
else:
    st.error("Sin conexión a los datos oficiales.")

if fecha_act:
    st.markdown(f"<div style='text-align: center; color: #a3a8b8; font-size: 0.75rem; margin-top: 25px;'>Última actualización MINETUR: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)
