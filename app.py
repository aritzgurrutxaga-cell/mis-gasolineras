import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Gasolineras Pro", page_icon="⛽", layout="centered")

@st.cache_data(ttl=3600, show_spinner="Actualizando base de datos...")
def descargar_base_datos_completa():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.json()
    except:
        return None

st.title("⛽ Gasolineras Pro")

datos_json = descargar_base_datos_completa()

if datos_json:
    estaciones = datos_json.get("ListaEESSPrecio", [])
    municipios = sorted(list(set([e["Municipio"] for e in estaciones])))
    
    municipio_sel = st.selectbox("📍 Municipio:", municipios, index=municipios.index("IRURA") if "IRURA" in municipios else 0)

    if municipio_sel:
        datos_municipio = [e for e in estaciones if e["Municipio"] == municipio_sel]
        
        if datos_municipio:
            df = pd.DataFrame(datos_municipio)
            
            # --- LIMPIEZA BLINDADA ---
            # 1. Convertimos las comas en puntos
            # 2. pd.to_numeric con errors='coerce' convierte lo que no sea número en un "NaN" (nulo)
            df["Precio Gasoleo A"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
            df["Precio Gasolina 95 E5"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')

            opcion = st.radio("Ordenar por:", ["Diésel A", "Gasolina 95"], horizontal=True)
            col_sort = "Precio Gasoleo A" if opcion == "Diésel A" else "Precio Gasolina 95 E5"
            
            # 3. Quitamos las gasolineras que se han quedado sin precio tras la limpieza
            df = df.dropna(subset=[col_sort])
            df = df.sort_values(by=col_sort)

            for _, gas in df.iterrows():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(gas['Rótulo'])
                    c1.caption(gas['Dirección'])
                    c2.metric("Precio", f"{gas[col_sort]} €")
                    
                    lat = gas["Latitud"].replace(",", ".")
                    lon = gas["Longitud (WGS84)"].replace(",", ".")
                    st.link_button("🗺️ Cómo llegar", f"https://www.google.com/maps?q={lat},{lon}")
                    st.divider()
else:
    st.error("Error al conectar con el Ministerio.")
