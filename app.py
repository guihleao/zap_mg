import ee
import streamlit as st
import geopandas as gpd
import tempfile
from google_auth_oauthlib.flow import Flow
from urllib.parse import urlparse, parse_qs

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Configuração do OAuth
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = "https://zap-mg.streamlit.app/"  # Substitua pelo seu redirecionamento

# Inicializar session_state
if "oauth_token" not in st.session_state:
    st.session_state["oauth_token"] = None
if "auth_code" not in st.session_state:
    st.session_state["auth_code"] = None

def login():
    """Cria o fluxo OAuth e gera a URL de autenticação."""
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
    auth_url, _ = flow.authorization_url(prompt="consent")
    
    st.markdown(f"""
        **Siga os passos abaixo para autenticar:**
        1. Clique no link abaixo para fazer login e autorizar o aplicativo.
        2. Após autorizar, você será redirecionado para uma página.
        3. Copie o código de autorização exibido na URL da página.
        4. Cole o código no campo abaixo.
        
        [Clique aqui para fazer login]({auth_url})
    """)

def authenticate(auth_code):
    """Troca o código de autenticação por um token de acesso."""
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
    try:
        token = flow.fetch_token(code=auth_code)
        st.session_state["oauth_token"] = token

        # Inicializa o Earth Engine com o token de acesso
        ee.Initialize(credentials=token["access_token"])

        st.success("Autenticação realizada com sucesso!")
        st.rerun()

    except Exception as e:
        st.error(f"Erro na autenticação: {e}")

# --- INTERFACE ---
if st.session_state["oauth_token"]:
    st.success("Usuário autenticado no Earth Engine!")
else:
    st.write("Para começar, autentique sua conta do Google Earth Engine.")
    login()

    # Captura o código de autorização da URL
    query_params = st.query_params
    auth_code = query_params.get("code", None)

    if auth_code:
        st.session_state["auth_code"] = auth_code
        st.write(f"**Código de autorização capturado:** `{auth_code}`")
        st.write("Cole o código abaixo para autenticar:")
        auth_code_input = st.text_input("Cole o código de autorização aqui:")

        if auth_code_input:
            authenticate(auth_code_input)

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
if st.session_state["oauth_token"]:
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