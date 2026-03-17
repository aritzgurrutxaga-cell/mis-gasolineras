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

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# AJUSTES DE ESPACIADO PRECISOS
st.markdown("""
    <style>
        .block-container {padding-top: 2.8rem;}
        
        /* Ajuste específico para que los bullets no tengan tanto margen */
        div[data-testid="stRadio"] > label {
            font-weight: bold;
            margin-bottom: -0.5rem;
        }
        
        /* Reduce espacio entre radio y la línea de debajo */
        div[data-testid="stRadio"] {margin-bottom: 0.5rem;}
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
        
        h1 {margin-top: -0.8rem; margin-bottom: 0.8rem;}
        
        /* Estilo para que los bullets se vean más grandes y fáciles de pulsar */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px); white-space: nowrap; overflow: hidden;'>
        ⛽ Buscador Gasolineras
    </h1>
    """, 
    unsafe_allow_html=True
)

# 2. Carga de Datos
@st.cache_data(ttl=3600,
