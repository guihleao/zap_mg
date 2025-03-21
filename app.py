import ee
import streamlit as st
import geopandas as gpd
import tempfile
import json

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Configuração da conta de serviço
SERVICE_ACCOUNT_KEY = st.secrets["service_account_key"]  # Chave JSON da conta de serviço
PROJECT_ID = "ee-zapmg"  # Substitua pelo ID do seu projeto do Google Cloud

# Inicializar session_state
if "ee_initialized" not in st.session_state:
    st.session_state["ee_initialized"] = False

# Função para inicializar o Earth Engine
def initialize_ee():
    try:
        # Carrega a chave da conta de serviço
        service_account_info = json.loads(SERVICE_ACCOUNT_KEY)
        credentials = ee.ServiceAccountCredentials(service_account_info["client_email"], SERVICE_ACCOUNT_KEY)
        ee.Initialize(credentials=credentials, project=PROJECT_ID)
        st.session_state["ee_initialized"] = True
        st.success("Earth Engine inicializado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao inicializar o Earth Engine: {e}")

# Inicializa o Earth Engine
if not st.session_state["ee_initialized"]:
    initialize_ee()

# Função para carregar o GeoPackage
def load_geopackage(file_path):
    gdf = gpd.read_file(file_path)
    return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__)

# Função principal para processar os dados
def process_data(geometry, epsg, buffer_km=1):
    bacia = geometry.buffer(buffer_km * 1000)  # Buffer em metros

    # Filtrar imagens Sentinel-2
    periodo_fim = ee.Date("2023-12-31")  
    periodo_inicio = periodo_fim.advance(-365, 'day')

    sentinel = ee.ImageCollection("COPERNICUS/S2_SR") \
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

# Interface de upload e processamento
if st.session_state["ee_initialized"]:
    uploaded_file = st.file_uploader("Carregue o arquivo GeoPackage da bacia", type=["gpkg"])
    epsg_options = {"31982 (Z 22S)": "EPSG:31982", "31983 (Z 23S)": "EPSG:31983", "31984 (Z 24S)": "EPSG:31984"}
    epsg_selected = st.selectbox("Selecione o EPSG", list(epsg_options.keys()))

    if st.button("Processar Dados") and uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.gpkg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        geometry = load_geopackage(tmp_file_path)
        resultados = process_data(geometry, epsg_options[epsg_selected])

        if resultados:
            st.write("Índices processados:")
            for key in resultados:
                st.write(f"- {key}")