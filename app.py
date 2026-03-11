import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Gasolineras Pro", page_icon="⛽", layout="wide")

@st.cache_data(ttl=1800) # Se actualiza cada 30 min
def get_data():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    return r.json()["ListaEESSPrecio"]

st.title("⛽ Mi Gasolinera Barata")

try:
    estaciones = get_data()
    
    # Buscador con autocompletado de municipios
    municipios = sorted(list(set([e["Municipio"] for e in estaciones])))
    municipio_sel = st.selectbox("Selecciona tu Municipio", municipios, index=municipios.index("IRURA") if "IRURA" in municipios else 0)

    if municipio_sel:
        # Filtrar y limpiar datos
        df = pd.DataFrame([e for e in estaciones if e["Municipio"] == municipio_sel])
        
        # Convertir precios a número para poder ordenar (vienen con comas)
        df["Precio Gasoleo A"] = df["Precio Gasoleo A"].str.replace(",", ".").astype(float)
        df["Precio Gasolina 95 E5"] = df["Precio Gasolina 95 E5"].str.replace(",", ".").astype(float)

        # Botón para ordenar por la más barata
        tipo_combustible = st.radio("Ordenar por mejor precio de:", ["Diésel A", "Gasolina 95"])
        col_sort = "Precio Gasoleo A" if tipo_combustible == "Diésel A" else "Precio Gasolina 95 E5"
        df = df.sort_values(by=col_sort)

        st.subheader(f"Gasolineras en {municipio_sel}")
        
        for _, gas in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{gas['Rótulo']}**\n\n{gas['Dirección']}")
                c2.metric(tipo_combustible, f"{gas[col_sort]} €/L")
                
                # Botón mágico para abrir Google Maps
                lat = gas["Latitud"].replace(",", ".")
                lon = gas["Longitud (WGS84)"].replace(",", ".")
                maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                c3.link_button("Ir ahora 📍", maps_url)
                st.divider()

except Exception as e:
    st.error("Servidor del Ministerio no disponible. Reintenta en unos minutos.")
