import ee
import streamlit as st
import geopandas as gpd
from shapely.geometry import shape
import hashlib
import base64
import os
import tempfile

# Título do aplicativo
st.title("Automatização de Obtenção de dados para o Zoneamento Ambiental e Produtivo")

# Configurar a meta tag de verificação do Google
st.set_page_config(
    page_title="Automatização de Obtenção de dados para o Zoneamento Ambiental e Produtivo",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Aplicativo para obtenção de dados do Earth Engine."
    },
    meta_tags=[
        {"name": "google-site-verification", "content": "y_IsrsAS9m58uq1YmBuBQf9gzELlg0axsqPmfQmL5T8"}
    ]
)

# Verificar se o usuário já está autenticado
if not ee.data._credentials:
    st.write("Para começar, autentique sua conta do Earth Engine.")
    
    # Obter as credenciais OAuth do Secrets do Streamlit
    CLIENT_ID = os.environ.get("EARTHENGINE_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("EARTHENGINE_CLIENT_SECRET")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("Credenciais OAuth não configuradas. Verifique o Secrets do Streamlit.")
    else:
        # Gerar o code_verifier e o code_challenge
        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(os.urandom(32)).digest()).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b'=').decode('utf-8')
        
        # Gerar o link de autenticação
        auth_url = ee.oauth.get_authorization_url(code_challenge=code_challenge)
        
        # Exibir o link para o usuário
        st.markdown(f"**[Clique aqui para autenticar sua conta do Earth Engine]({auth_url})**")
        
        # Solicitar o código de autorização
        auth_code = st.text_input("Depois de autenticar, cole o código de autorização aqui:")
        
        # Botão para autenticar
        if st.button("Autenticar") and auth_code:
            try:
                # Trocar o código de autorização por credenciais
                ee.oauth.get_tokens(auth_code, code_verifier=code_verifier)
                ee.Initialize()
                st.success("Autenticação realizada com sucesso!")
            except Exception as e:
                st.error(f"Erro na autenticação: {e}")
else:
    st.write("Você já está autenticado! Pode prosseguir com o uso do aplicativo.")
# Função para carregar o GeoPackage e converter para um objeto de geometria do Earth Engine
def load_geopackage(file_path):
    gdf = gpd.read_file(file_path)
    geometry = gdf.geometry.iloc[0]  # Pega a primeira geometria do arquivo
    return ee.Geometry(geometry.__geo_interface__)

# Função principal para processar os dados
def process_data(nome_bacia, nome_bacia_export, epsg, buffer_km=1):
    # Carregar a bacia e aplicar o buffer
    bacia = nome_bacia.buffer(buffer_km * 1000)  # Buffer em metros

    # Definir período de interesse
    periodo_fim = ee.Date(Date.now())  # Data atual
    periodo_inicio = periodo_fim.advance(-365, 'day')  # Um ano antes

    # Filtrar imagens Sentinel-2
    sentinel = ee.ImageCollection("COPERNICUS/S2_SR") \
        .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12') \
        .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10) \
        .filterBounds(bacia) \
        .filterDate(periodo_inicio, periodo_fim)

    # Verificar se há imagens para o período definido
    if sentinel.size().getInfo() == 0:
        st.error("Nenhuma imagem foi encontrada para o período especificado.")
        return

    # Calcular a mediana das imagens
    sentinel_median = sentinel.median().clip(bacia)

    # Calcular índices
    ndvi = sentinel_median.normalizedDifference(['B8', 'B4']).rename('NDVI')
    gndvi = sentinel_median.normalizedDifference(['B8', 'B3']).rename('GNDVI')
    ndwi = sentinel_median.normalizedDifference(['B3', 'B8']).rename('NDWI')
    ndmi = sentinel_median.normalizedDifference(['B8', 'B11']).rename('NDMI')

    # Reprojetar as imagens
    def reproject_image(image, epsg, scale):
        return image.reproject(crs=epsg, scale=scale)

    scale = 10  # Escala de resolução
    ndvi_reprojected = reproject_image(ndvi, epsg, scale)
    gndvi_reprojected = reproject_image(gndvi, epsg, scale)
    ndwi_reprojected = reproject_image(ndwi, epsg, scale)
    ndmi_reprojected = reproject_image(ndmi, epsg, scale)

    # Exportar as imagens (localmente ou para o Google Drive)
    # Aqui você pode adicionar a lógica para salvar as imagens localmente ou no Google Drive
    st.success("Processamento concluído!")

    return {
        'ndvi': ndvi_reprojected,
        'gndvi': gndvi_reprojected,
        'ndwi': ndwi_reprojected,
        'ndmi': ndmi_reprojected
    }

# Interface do Streamlit para o processamento de dados
if ee.data._credentials:
    st.write("Agora você pode usar o aplicativo normalmente.")

    # Upload do arquivo GeoPackage
    uploaded_file = st.file_uploader("Carregue o arquivo GeoPackage da bacia", type=["gpkg"])

    # Seleção do EPSG
    epsg_options = {
        "31982 (Z 22S)": "EPSG:31982",
        "31983 (Z 23S)": "EPSG:31983",
        "31984 (Z 24S)": "EPSG:31984"
    }
    epsg_selected = st.selectbox("Selecione o EPSG", list(epsg_options.keys()))

    # Nome da bacia para exportação
    nome_bacia_export = st.text_input("Nome da bacia para exportação")

    # Botão para processar os dados
    if st.button("Processar Dados") and uploaded_file is not None:
        # Salvar o arquivo GeoPackage temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.gpkg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        # Carregar o GeoPackage
        nome_bacia = load_geopackage(tmp_file_path)

        # Processar os dados
        resultados = process_data(nome_bacia, nome_bacia_export, epsg_options[epsg_selected])

        # Exibir resultados
        st.write("Resultados do processamento:")
        st.write(resultados)