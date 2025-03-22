import ee
import streamlit as st
import geopandas as gpd
import datetime
import folium
from streamlit_folium import st_folium
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
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
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uris"]  # URI de redirecionamento
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Função para autenticar no Google Drive
def authenticate_google_drive():
    try:
        # Configura o fluxo de autenticação
        flow = InstalledAppFlow.from_client_config(
            client_config={
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],  # Certifique-se de que está correto
                }
            },
            scopes=SCOPES,
        )

        # Gera a URL de autorização
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            redirect_uri=REDIRECT_URI  # Adiciona o redirect_uri
        )

        # Exibe o link de autenticação
        st.write("Clique no link abaixo para autenticar no Google Drive:")
        st.markdown(f"[Autenticar no Google Drive]({auth_url})")

        # Solicita o código de autorização
        auth_code = st.text_input("Cole o código de autorização aqui:")

        if auth_code:
            # Troca o código de autorização por um token de acesso
            flow.fetch_token(code=auth_code, redirect_uri=REDIRECT_URI)  # Passa o redirect_uri
            creds = flow.credentials

            # Armazena as credenciais na sessão
            st.session_state["creds"] = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            st.session_state["drive_authenticated"] = True
            st.success("Autenticação no Google Drive realizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao autenticar no Google Drive: {e}")

# Função para salvar um arquivo .txt no Google Drive
def save_txt_to_drive():
    try:
        # Verifica se as credenciais estão disponíveis
        if "creds" not in st.session_state:
            st.error("Erro: Credenciais de autenticação não encontradas.")
            return

        # Cria as credenciais a partir do token armazenado
        creds = Credentials(
            token=st.session_state["creds"]["token"],
            refresh_token=st.session_state["creds"]["refresh_token"],
            token_uri=st.session_state["creds"]["token_uri"],
            client_id=st.session_state["creds"]["client_id"],
            client_secret=st.session_state["creds"]["client_secret"],
            scopes=st.session_state["creds"]["scopes"],
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