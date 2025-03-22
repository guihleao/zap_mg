import ee
import streamlit as st
import geopandas as gpd
import tempfile
import zipfile
import io
import requests
from google.oauth2 import service_account
import folium
from streamlit_folium import folium_static

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Configuração da conta de serviço
SERVICE_ACCOUNT_KEY = st.secrets["google"]  # Acessa as credenciais do GCS
PROJECT_ID = "ee-zapmg"  # Substitua pelo ID do seu projeto do Google Cloud

# Inicializar session_state
if "ee_initialized" not in st.session_state:
    st.session_state["ee_initialized"] = False
if "resultados" not in st.session_state:
    st.session_state["resultados"] = None

# Função para inicializar o Earth Engine
def initialize_ee():
    try:
        # Formata a chave privada corretamente
        private_key = SERVICE_ACCOUNT_KEY["private_key"]
        
        # Usa o dicionário diretamente
        credentials = ee.ServiceAccountCredentials(
            SERVICE_ACCOUNT_KEY["client_email"],
            key_data=private_key,  # Passa a chave privada formatada
        )
        ee.Initialize(credentials=credentials, project=PROJECT_ID)
        st.session_state["ee_initialized"] = True
        st.success("Earth Engine inicializado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao inicializar o Earth Engine: {e}")

# Inicializa o Earth Engine
if not st.session_state["ee_initialized"]:
    initialize_ee()

# Função para carregar o GeoJSON e visualizar o polígono
def load_geojson(file):
    try:
        # Carrega o GeoJSON
        gdf = gpd.read_file(file)
        
        # Verifica se o GeoJSON contém geometrias
        if gdf.geometry.is_empty.any():
            st.error("O arquivo GeoJSON contém geometrias vazias.")
            return None
        
        # Verifica se as geometrias são polígonos ou multipolígonos
        if not all(gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])):
            st.error("O arquivo deve conter apenas polígonos ou multipolígonos.")
            return None
        
        # Corrige geometrias inválidas (se necessário)
        gdf['geometry'] = gdf['geometry'].buffer(0)
        
        # Reprojeta para WGS84 (lat/lon) se necessário
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        
        # Visualiza o polígono no mapa usando folium
        st.write("Visualização do polígono carregado:")
        m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=10)
        
        # Adiciona o polígono ao mapa
        for _, row in gdf.iterrows():
            folium.GeoJson(row['geometry']).add_to(m)
        
        # Exibe o mapa no Streamlit
        folium_static(m)
        
        # Retorna a geometria para o Earth Engine
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__)
    except Exception as e:
        st.error(f"Erro ao carregar o GeoJSON: {e}")
        return None

# Função principal para processar os dados
def process_data(geometry, epsg, buffer_km=1):
    try:
        bacia = geometry.buffer(buffer_km * 1000)  # Buffer em metros

        # Filtrar imagens Sentinel-2 Harmonized
        periodo_fim = ee.Date("2023-12-31")  
        periodo_inicio = periodo_fim.advance(-365, 'day')

        sentinel = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .select(['B4', 'B3', 'B8', 'B11']) \
            .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10) \
            .filterBounds(bacia) \
            .filterDate(periodo_inicio, periodo_fim)

        if sentinel.size().getInfo() == 0:
            st.error("Nenhuma imagem foi encontrada para o período especificado.")
            return None

        sentinel_median = sentinel.median().clip(bacia)
        
        indices = {
            "NDVI": sentinel_median.normalizedDifference(['B8', 'B4']),
            "GNDVI": sentinel_median.normalizedDifference(['B8', 'B3']),
            "NDWI": sentinel_median.normalizedDifference(['B3', 'B8']),
            "NDMI": sentinel_median.normalizedDifference(['B8', 'B11']),
        }

        return {name: img.reproject(crs=epsg, scale=10) for name, img in indices.items()}
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None

# Interface de upload e processamento
if st.session_state["ee_initialized"]:
    uploaded_file = st.file_uploader("Carregue o arquivo GeoJSON da bacia", type=["geojson"])
    epsg_options = {"31982 (Z 22S)": "EPSG:31982", "31983 (Z 23S)": "EPSG:31983", "31984 (Z 24S)": "EPSG:31984"}
    epsg_selected = st.selectbox("Selecione o EPSG", list(epsg_options.keys()))

    if st.button("Processar Dados") and uploaded_file is not None:
        geometry = load_geojson(uploaded_file)
        if geometry:
            st.session_state["resultados"] = process_data(geometry, epsg_options[epsg_selected])

    if st.session_state["resultados"]:
        st.write("Índices processados:")
        for key in st.session_state["resultados"]:
            st.write(f"- {key}")