import ee
import streamlit as st
import geopandas as gpd
from shapely.geometry import shape
import tempfile
import json
from google_auth_oauthlib.flow import Flow

# Título do aplicativo
st.title("Automatização de Obtenção de dados para o Zoneamento Ambiental e Produtivo")

# Configuração do OAuth
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = "https://zap-mg.streamlit.app/"  # URL do seu Streamlit Cloud

# Inicializar session_state para autenticação
if "oauth_token" not in st.session_state:
    st.session_state["oauth_token"] = None
if "oauth_state" not in st.session_state:
    st.session_state["oauth_state"] = None

def login():
    """Cria o fluxo OAuth e redireciona o usuário para autenticação."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=["https://www.googleapis.com/auth/earthengine"],
    )
    
    flow.redirect_uri = REDIRECT_URI
    auth_url, state = flow.authorization_url(prompt="consent")
    
    # Salvar o estado no session_state
    st.session_state["oauth_state"] = state
    st.markdown(f"[Clique aqui para fazer login]({auth_url})")

def authenticate(auth_code):
    """Recebe o código de autenticação e troca por um token de acesso."""
    if "oauth_state" not in st.session_state or not st.session_state["oauth_state"]:
        st.error("Erro: estado da autenticação inválido. Tente novamente.")
        return

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=["https://www.googleapis.com/auth/earthengine"],
        state=st.session_state["oauth_state"]
    )

    flow.redirect_uri = REDIRECT_URI
    try:
        token = flow.fetch_token(code=auth_code)
        st.session_state["oauth_token"] = token

        # Inicializa o Earth Engine com as credenciais
        credentials = ee.ServiceAccountCredentials(None, key_data=json.dumps(token))
        ee.Initialize(credentials)

        st.success("Autenticação realizada com sucesso!")
        st.rerun()  # Atualiza a página

    except Exception as e:
        st.error(f"Erro na autenticação: {e}")

# --- INTERFACE ---
if st.session_state["oauth_token"]:
    st.success("Usuário autenticado no Earth Engine!")
else:
    st.write("Para começar, autentique sua conta do Google Earth Engine.")
    login()
    auth_code = st.text_input("Se já autenticou, cole o código aqui:")
    if st.button("Confirmar Código") and auth_code:
        authenticate(auth_code)

# Função para carregar o GeoPackage e converter para um objeto de geometria do Earth Engine
def load_geopackage(file_path):
    gdf = gpd.read_file(file_path)
    geometry = gdf.geometry.iloc[0]  # Pega a primeira geometria do arquivo
    return ee.Geometry(geometry.__geo_interface__)

# Função principal para processar os dados
def process_data(nome_bacia, nome_bacia_export, epsg, buffer_km=1):
    bacia = nome_bacia.buffer(buffer_km * 1000)  # Buffer em metros

    # Definir período de interesse
    periodo_fim = ee.Date("2023-12-31")  # Data fixa para exemplo
    periodo_inicio = periodo_fim.advance(-365, 'day')

    # Filtrar imagens Sentinel-2
    sentinel = ee.ImageCollection("COPERNICUS/S2_SR") \
        .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12') \
        .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10) \
        .filterBounds(bacia) \
        .filterDate(periodo_inicio, periodo_fim)

    if sentinel.size().getInfo() == 0:
        st.error("Nenhuma imagem foi encontrada para o período especificado.")
        return

    sentinel_median = sentinel.median().clip(bacia)
    ndvi = sentinel_median.normalizedDifference(['B8', 'B4']).rename('NDVI')
    gndvi = sentinel_median.normalizedDifference(['B8', 'B3']).rename('GNDVI')
    ndwi = sentinel_median.normalizedDifference(['B3', 'B8']).rename('NDWI')
    ndmi = sentinel_median.normalizedDifference(['B8', 'B11']).rename('NDMI')

    scale = 10  # Escala de resolução
    def reproject_image(image, epsg, scale):
        return image.reproject(crs=epsg, scale=scale)

    ndvi_reprojected = reproject_image(ndvi, epsg, scale)
    gndvi_reprojected = reproject_image(gndvi, epsg, scale)
    ndwi_reprojected = reproject_image(ndwi, epsg, scale)
    ndmi_reprojected = reproject_image(ndmi, epsg, scale)

    st.success("Processamento concluído!")
    return {'ndvi': ndvi_reprojected, 'gndvi': gndvi_reprojected, 'ndwi': ndwi_reprojected, 'ndmi': ndmi_reprojected}

if st.session_state["oauth_token"]:
    uploaded_file = st.file_uploader("Carregue o arquivo GeoPackage da bacia", type=["gpkg"])
    epsg_options = {"31982 (Z 22S)": "EPSG:31982", "31983 (Z 23S)": "EPSG:31983", "31984 (Z 24S)": "EPSG:31984"}
    epsg_selected = st.selectbox("Selecione o EPSG", list(epsg_options.keys()))
    nome_bacia_export = st.text_input("Nome da bacia para exportação")

    if st.button("Processar Dados") and uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.gpkg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        nome_bacia = load_geopackage(tmp_file_path)
        resultados = process_data(nome_bacia, nome_bacia_export, epsg_options[epsg_selected])
        st.write("Resultados do processamento:", resultados)
