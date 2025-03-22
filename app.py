import ee
import streamlit as st
import geopandas as gpd
import tempfile
import zipfile
import io
import requests
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import folium
from streamlit_folium import st_folium
import json

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
if "drive_service" not in st.session_state:
    st.session_state["drive_service"] = None

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

# Função para autenticar no Google Drive (fluxo manual)
def authenticate_google_drive():
    try:
        # Reconstruir o credentials.json a partir dos secrets
        credentials = {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "project_id": st.secrets["google_oauth"]["project_id"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "redirect_uris": [st.secrets["google_oauth"]["redirect_uris"]]
            }
        }

        # Salvar o credentials.json temporariamente
        with open('credentials.json', 'w') as f:
            json.dump(credentials, f)

        # Configura o fluxo de autenticação
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/drive'],
            redirect_uri=st.secrets["google_oauth"]["redirect_uris"]  # Adiciona o redirect_uri
        )

        # Gera a URL de autorização
        auth_url, _ = flow.authorization_url(prompt='consent')

        # Exibe a URL para o usuário
        st.write("Por favor, acesse o link abaixo para autenticar:")
        st.write(auth_url)

        # Solicita o código de autorização
        auth_code = st.text_input("Cole o código de autorização aqui:")

        if auth_code:
            # Troca o código por credenciais
            flow.fetch_token(code=auth_code)
            creds = flow.credentials

            # Salva as credenciais para uso futuro
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

            # Cria o serviço do Google Drive
            drive_service = build('drive', 'v3', credentials=creds)
            st.session_state["drive_service"] = drive_service
            st.session_state["drive_authenticated"] = True
            st.success("Autenticação no Google Drive realizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao autenticar no Google Drive: {e}")

# Função para carregar o GeoJSON e visualizar o polígono
def load_geojson(file):
    try:
        # Carrega o GeoJSON
        gdf = gpd.read_file(file)
        
        # Verifica se o GeoJSON contém geometrias
        if gdf.geometry.is_empty.any():
            st.error("O arquivo GeoJSON contém geometrias vazias.")
            return None, None
        
        # Verifica se as geometrias são polígonos ou multipolígonos
        if not all(gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])):
            st.error("O arquivo deve conter apenas polígonos ou multipolígonos.")
            return None, None
        
        # Corrige geometrias inválidas (se necessário)
        gdf['geometry'] = gdf['geometry'].buffer(0)
        
        # Obtém o CRS do GeoDataFrame
        crs = gdf.crs
        if crs is None:
            st.warning("O arquivo GeoJSON não possui CRS definido. Assumindo WGS84 (EPSG:4326).")
            crs = "EPSG:4326"
        else:
            st.write(f"CRS do arquivo GeoJSON: {crs}")
        
        # Visualiza o polígono no mapa usando folium
        st.write("Visualização do polígono carregado:")
        
        # Calcula o centróide para centralizar o mapa
        centroid = gdf.geometry.centroid
        m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=10)
        
        # Adiciona o polígono ao mapa
        for _, row in gdf.iterrows():
            folium.GeoJson(row['geometry']).add_to(m)
        
        # Exibe o mapa no Streamlit usando st_folium
        st_folium(m, returned_objects=[])
        
        # Retorna a geometria e o CRS
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__), crs
    except Exception as e:
        st.error(f"Erro ao carregar o GeoJSON: {e}")
        return None, None

# Função para exportar para o Google Drive
def export_to_drive(image, name, geometry, folder_id=None):
    try:
        # Exporta a imagem para o Google Drive
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=name,
            folder=folder_id,  # ID da pasta no Google Drive (opcional)
            fileNamePrefix=name,
            scale=10,
            region=geometry,
            fileFormat='GeoTIFF',
        )
        task.start()
        st.success(f"Exportação {name} iniciada. Verifique seu Google Drive.")
        return task
    except Exception as e:
        st.error(f"Erro ao exportar {name} para o Google Drive: {e}")
        return None

# Inicializa o Earth Engine
if not st.session_state["ee_initialized"]:
    initialize_ee()

# Interface de upload e processamento
if st.session_state["ee_initialized"]:
    # Autenticação no Google Drive
    if not st.session_state["drive_authenticated"]:
        st.write("Para exportar arquivos, faça login no Google Drive:")
        if st.button("Autenticar no Google Drive"):
            authenticate_google_drive()
    
    if st.session_state["drive_authenticated"]:
        uploaded_file = st.file_uploader("Carregue o arquivo GeoJSON da bacia", type=["geojson"])
        
        if uploaded_file is not None:
            # Carrega o GeoJSON e obtém o CRS
            geometry, crs = load_geojson(uploaded_file)
            
            if geometry:
                # Exibe o CRS encontrado
                st.write(f"CRS do arquivo GeoJSON: {crs}")
                
                # Processa os dados usando o CRS identificado
                if st.button("Processar Dados"):
                    resultados = process_data(geometry, crs)
                    if resultados:
                        st.write("Índices processados:")
                        for key, image in resultados.items():
                            st.write(f"- {key}")
                            if st.button(f"Exportar {key} para o Google Drive"):
                                export_to_drive(image, key, geometry)