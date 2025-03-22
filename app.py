import ee
import streamlit as st
import geopandas as gpd
import tempfile
import zipfile
import io
import requests
from google.oauth2 import service_account

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

# Função para carregar o GeoPackage e visualizar a geometria
def load_geopackage(file_path):
    try:
        # Carrega o GeoPackage
        gdf = gpd.read_file(file_path)
        
        # Corrige geometrias inválidas (se necessário)
        gdf['geometry'] = gdf['geometry'].buffer(0)
        
        # Reprojeta para WGS84 (lat/lon) se necessário
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        
        # Extrai as coordenadas de latitude e longitude da geometria
        gdf['latitude'] = gdf.geometry.centroid.y
        gdf['longitude'] = gdf.geometry.centroid.x
        
        # Visualiza a geometria no mapa
        st.write("Visualização da geometria carregada:")
        st.map(gdf[['latitude', 'longitude']])  # Usa as colunas de latitude e longitude
        
        # Retorna a geometria para o Earth Engine
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__)
    except Exception as e:
        st.error(f"Erro ao carregar o GeoPackage: {e}")
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

# Função para exportar os índices como GeoTIFF
def export_geotiff(image, name, geometry, scale=10):
    try:
        url = image.getDownloadURL({
            'name': name,
            'scale': scale,
            'region': geometry,
            'format': 'GEO_TIFF',
        })
        return url
    except Exception as e:
        st.error(f"Erro ao exportar {name}: {e}")
        return None

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
        if geometry:
            st.session_state["resultados"] = process_data(geometry, epsg_options[epsg_selected])

    if st.session_state["resultados"]:
        st.write("Índices processados:")
        for key in st.session_state["resultados"]:
            st.write(f"- {key}")

        # Exportar os índices como GeoTIFF
        st.subheader("Exportar Resultados")
        export_zip = st.checkbox("Exportar todos os índices em um arquivo ZIP")

        if export_zip:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for name, image in st.session_state["resultados"].items():
                    download_url = export_geotiff(image, name, geometry)
                    if download_url:
                        response = requests.get(download_url)
                        zip_file.writestr(f"{name}.tif", response.content)
            
            zip_buffer.seek(0)
            st.download_button(
                label="Baixar todos os índices (ZIP)",
                data=zip_buffer,
                file_name="indices.zip",
                mime="application/zip"
            )
        else:
            for name, image in st.session_state["resultados"].items():
                download_url = export_geotiff(image, name, geometry)
                if download_url:
                    st.markdown(f"**{name}**: [Baixar GeoTIFF]({download_url})")