import ee
import streamlit as st
import geopandas as gpd
import datetime
import folium
from streamlit_folium import st_folium
from streamlit_oauth import OAuth2Component
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import io

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Configuração da conta de serviço do Earth Engine
SERVICE_ACCOUNT_KEY = st.secrets["google"]  # Acessa as credenciais do GCS
PROJECT_ID = "ee-zapmg"  # Substitua pelo ID do seu projeto do Google Cloud

# Inicializar session_state
if "ee_initialized" not in st.session_state:
    st.session_state["ee_initialized"] = False
if "resultados" not in st.session_state:
    st.session_state["resultados"] = None
if "drive_authenticated" not in st.session_state:
    st.session_state["drive_authenticated"] = False
if "export_started" not in st.session_state:
    st.session_state["export_started"] = False
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

# Função para inicializar o Earth Engine
def initialize_ee():
    try:
        private_key = SERVICE_ACCOUNT_KEY["private_key"]
        credentials = ee.ServiceAccountCredentials(
            SERVICE_ACCOUNT_KEY["client_email"],
            key_data=private_key,
        )
        ee.Initialize(credentials=credentials, project=PROJECT_ID)
        st.session_state["ee_initialized"] = True
        st.success("Earth Engine inicializado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao inicializar o Earth Engine: {e}")

# Configuração do OAuth2
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uris"]
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/drive"

# Inicializa o componente OAuth2
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL)

# Função para autenticar no Google Drive
def authenticate_google_drive():
    try:
        if "token" not in st.session_state:
            result = oauth2.authorize_button(
                "Autenticar no Google Drive",
                redirect_uri=REDIRECT_URI,
                scope=SCOPES
            )
            if result:
                st.session_state["token"] = result
                st.session_state["drive_authenticated"] = True
                st.success("Autenticação no Google Drive realizada com sucesso!")
        else:
            st.success("Você já está autenticado no Google Drive.")
    except Exception as e:
        st.error(f"Erro ao autenticar no Google Drive: {e}")

# Função para salvar um arquivo .txt no Google Drive
def save_txt_to_drive():
    try:
        # Verifica se o token de autenticação está disponível
        if "token" not in st.session_state:
            st.error("Erro: Token de autenticação não encontrado.")
            return

        # Obtém o token da sessão
        token = st.session_state["token"]

        # Verifica se o token contém os campos mínimos necessários
        if "access_token" not in token:
            st.error("Erro: Token de autenticação incompleto. Falta o campo 'access_token'.")
            return

        # Cria as credenciais manualmente
        creds = Credentials(
            token=token["access_token"],  # Token de acesso
            refresh_token=token.get("refresh_token"),  # Token de atualização (opcional)
            token_uri=token.get("token_uri", TOKEN_URL),  # URL do token (usa o padrão se não estiver presente)
            client_id=token.get("client_id", CLIENT_ID),  # ID do cliente (usa o padrão se não estiver presente)
            client_secret=token.get("client_secret", CLIENT_SECRET),  # Segredo do cliente (usa o padrão se não estiver presente)
        )

        # Cria o serviço do Google Drive
        drive_service = build("drive", "v3", credentials=creds)

        # Define o conteúdo do arquivo
        file_metadata = {
            "name": "teste.txt",  # Nome do arquivo
            "mimeType": "text/plain",  # Tipo do arquivo
        }
        media_body = io.BytesIO(b"OKAY")  # Conteúdo do arquivo

        # Envia o arquivo para o Google Drive
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media_body,
            fields="id",
        ).execute()

        st.success(f"Arquivo 'teste.txt' criado com sucesso! ID: {file['id']}")
    except Exception as e:
        st.error(f"Erro ao salvar o arquivo no Google Drive: {e}")

# Inicializa o Earth Engine
if not st.session_state["ee_initialized"]:
    initialize_ee()

# Interface de upload e processamento
if st.session_state["ee_initialized"]:
    if not st.session_state["drive_authenticated"]:
        st.write("Para exportar arquivos, faça login no Google Drive:")
        authenticate_google_drive()
    
    if st.session_state["drive_authenticated"]:
        # Botão para testar a escrita no Google Drive
        if st.button("Salvar arquivo de teste no Google Drive"):
            save_txt_to_drive()