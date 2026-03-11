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
            
            # Limpieza blindada de datos para evitar el ValueError anterior [cite: 2, 4]
            df["Precio Gasoleo A"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
            df["Precio Gasolina 95 E5"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')

            # Ordenamos por Diésel por defecto, pero mostramos todo
            df = df.sort_values(by="Precio Gasoleo A")

            st.divider()
            for _, gas in df.iterrows():
                with st.container():
                    st.subheader(gas['Rótulo'])
                    st.caption(f"🏠 {gas['Dirección']}")
                    
                    # Mostramos ambos precios en columnas 
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    # Si el precio es NaN (nulo), mostramos "--"
                    d_val = f"{gas['Precio Gasoleo A']} €" if not pd.isna(gas['Precio Gasoleo A']) else "N/A"
                    g_val = f"{gas['Precio Gasolina 95 E5']} €" if not pd.isna(gas['Precio Gasolina 95 E5']) else "N/A"
                    
                    col1.metric("Diésel A", d_val)
                    col2.metric("Gasolina 95", g_val)
                    
                    # Botón de Google Maps optimizado
                    lat = gas["Latitud"].replace(",", ".")
                    lon = gas["Longitud (WGS84)"].replace(",", ".")
                    col3.write("") # Espaciador visual
                    col3.link_button("📍 Mapa", f"https://www.google.com/maps?q={lat},{lon}")
                    st.divider()
else:
    st.error("Error al conectar con el Ministerio.")
