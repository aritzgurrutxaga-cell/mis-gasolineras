import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
from streamlit_js_eval import get_geolocation
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- ADAPTADOR SSL (Para saltar bloqueos del Ministerio) ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# 2. Carga de Datos con Backup Persistente
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    archivo_backup = "gasolineras_backup.csv"
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, datetime.datetime.now()
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            fecha = datetime.datetime.fromtimestamp(os.path.getmtime(archivo_backup))
            return df_rec.to_dict('records'), fecha
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.title("⛽ Buscador Gasolineras")

datos, fecha_act = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    # Limpieza numérica de lat/lon
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    # Lógica GPS Silenciosa para el pre-rellenado
    loc = get_geolocation()
    lat_gps, lon_gps, muni_gps = None, None, None

    if loc and 'coords' in loc:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']
        # Buscar municipio más cercano para pre-rellenar el selector visualmente
        df["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
        muni_gps = df.sort_values("dist_temp").iloc[0]["Municipio"]

    # --- BLOQUE 1: UBICACIÓN UNIFICADA ---
    with st.container(border=True):
        idx = municipios_unicos.index(muni_gps) if muni_gps in municipios_unicos else None
        municipio_manual = st.selectbox("📍 Ubicación:", options=municipios_unicos, index=idx)
        
        # Lógica de prioridad de coordenadas
        if lat_gps and (municipio_manual == muni_gps or municipio_manual is None):
            lat_ref, lon_ref = lat_gps, lon_gps
            origen_label = "tu ubicación exacta"
            st.success("✅ GPS: Usando tu ubicación actual")
        elif municipio_manual:
            ref = df[df["Municipio"] == municipio_manual].iloc[0]
            lat_ref, lon_ref = ref["lat_num"], ref["lon_num"]
            origen_label = municipio_manual
        else:
            lat_ref, lon_ref = None, None
            st.info("⌛ Esperando señal GPS o elige un municipio...")

    # --- BLOQUE 2: RADIO ---
    radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)

    # --- LÓGICA DE COMBUSTIBLE (ESTADO) ---
    if 'tipo_combustible' not in st.session_state:
        st.session_state.tipo_combustible = "Diésel"

    combustible = st.session_state.tipo_combustible
    col_precio = "Precio Gasoleo A" if combustible == "Diésel" else "Precio Gasolina 95 E5"

    # --- RESULTADOS ---
    if lat_ref and lon_ref:
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values("precio_num")

        st.divider()
        st.subheader(f"📉 {combustible} cerca de {origen_label}")
        
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        # Formato: Nombre - Municipio
                        st.write(f"### {g['Rótulo']} - {g['Municipio']}")
                        st.write(f"💰 **{g[col_precio]} €/L** | 📍 {g['Distancia']:.2f} km")
                        st.caption(f"{g['Dirección']}")
                    with col_btn:
                        # URL de navegación directa
                        url_map = f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}"
                        st.link_button("Ir", url_map, use_container_width=True)
        else:
            st.warning("No hay resultados con este combustible en este radio.")

    # --- BLOQUE 3: CONFIGURACIÓN AL FINAL (PEQUEÑO) ---
    st.write("---")
    st.caption("Configuración de búsqueda:")
    st.session_state.tipo_combustible = st.radio(
        "Ordenar por precio de:", 
        ["Diésel", "G95"], 
        horizontal=True,
        index=0 if st.session_state.tipo_combustible == "Diésel" else 1
    )

    # Pie de página con fecha
    if fecha_act:
        st.caption(f"Última actualización: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}")
else:
    st.error("No se han podido cargar los datos.")
