import streamlit as st
import requests
import pandas as pd

# 1. Configuración de la WebApp
st.set_page_config(page_title="Gasolineras Pro", page_icon="⛽", layout="centered")

# 2. Función de descarga "Blindada"
# Guardamos los datos en la memoria de la plataforma online durante 1 hora (3600 seg)
@st.cache_data(ttl=3600, show_spinner="Actualizando base de datos desde el Ministerio...")
def descargar_base_datos_completa():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://geoportalgasolineras.es/'
    }
    try:
        # Intentamos la descarga
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Si falla la descarga, devolvemos None para manejarlo
        return None

st.title("⛽ Gasolineras Pro")
st.markdown("Consulta local de precios (Base de datos en la nube)")

# 3. Lógica de ejecución
datos_json = descargar_base_datos_completa()

if datos_json is not None:
    estaciones = datos_json.get("ListaEESSPrecio", [])
    
    # Extraemos todos los municipios para el listado
    municipios_disponibles = sorted(list(set([e["Municipio"] for e in estaciones])))
    
    municipio_sel = st.selectbox(
        "📍 Selecciona tu municipio:", 
        municipios_disponibles, 
        index=municipios_disponibles.index("IRURA") if "IRURA" in municipios_disponibles else 0
    )

    if municipio_sel:
        # Filtramos directamente sobre la lista que ya tenemos en la memoria de la plataforma
        datos_municipio = [e for e in estaciones if e["Municipio"] == municipio_sel]
        
        if datos_municipio:
            df = pd.DataFrame(datos_municipio)
            
            # Limpieza de precios
            df["Precio Gasoleo A"] = df["Precio Gasoleo A"].str.replace(",", ".").astype(float)
            df["Precio Gasolina 95 E5"] = df["Precio Gasolina 95 E5"].str.replace(",", ".").astype(float)

            opcion = st.radio("Ordenar por:", ["Diésel A", "Gasolina 95"], horizontal=True)
            col_sort = "Precio Gasoleo A" if opcion == "Diésel A" else "Precio Gasolina 95 E5"
            df = df.sort_values(by=col_sort)

            st.divider()
            for _, gas in df.iterrows():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(gas['Rótulo'])
                    c1.caption(gas['Dirección'])
                    c2.metric("Precio", f"{gas[col_sort]}€")
                    
                    lat = gas["Latitud"].replace(",", ".")
                    lon = gas["Longitud (WGS84)"].replace(",", ".")
                    st.link_button("🗺️ Cómo llegar", f"https://www.google.com/maps?q={lat},{lon}")
                    st.write("")
        else:
            st.warning("No hay datos disponibles para este municipio en este momento.")
else:
    st.error("⚠️ El Ministerio no responde. Usando última copia de seguridad de la plataforma...")
    st.info("Reintenta recargar la página en unos segundos.")
