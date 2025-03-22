import ee
import streamlit as st
import geopandas as gpd
import datetime
import folium
from streamlit_folium import st_folium
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from streamlit_oauth import OAuth2Component

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

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
if "selected_project" not in st.session_state:
    st.session_state["selected_project"] = None

# Configuração do OAuth2
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uris"]

# Escopos como uma string separada por espaços
SCOPES = "https://www.googleapis.com/auth/earthengine https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/cloud-platform"

# Cria a instância do OAuth2Component
oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint=AUTHORIZE_URL,
    token_endpoint=TOKEN_URL,
    refresh_token_endpoint=REFRESH_TOKEN_URL,
    revoke_token_endpoint=REVOKE_TOKEN_URL,
)

# Verifica se o token já está na session_state
if "token" not in st.session_state:
    # Se não estiver, exibe o botão de autorização
    result = oauth2.authorize_button(
        name="Autenticar no Google Drive e Earth Engine",
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,  # Passa a string de escopos
    )
    if result and "token" in result:
        # Se a autorização for bem-sucedida, salva o token na session_state
        st.session_state["token"] = result["token"]
        st.session_state["creds"] = {
            "token": result["token"]["access_token"],
            "refresh_token": result["token"].get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scopes": SCOPES.split(),  # Converte a string de escopos de volta para lista
        }
        st.session_state["drive_authenticated"] = True
        st.rerun()  # Recarrega a página para atualizar o estado
else:
    # Se o token já estiver na session_state, exibe o token
    token = st.session_state["token"]
    st.json(token)  # Exibe o token em formato JSON (apenas para depuração)

    # Botão para atualizar o token
    if st.button("Atualizar Token"):
        token = oauth2.refresh_token(token)
        st.session_state["token"] = token
        st.rerun()  # Recarrega a página para atualizar o estado

# Função para listar projetos do Google Cloud
def list_google_cloud_projects():
    try:
        # Verifica se as credenciais estão disponíveis
        if "creds" not in st.session_state:
            st.error("Erro: Credenciais de autenticação não encontradas.")
            return None

        # Cria as credenciais a partir do token armazenado
        creds = Credentials(
            token=st.session_state["creds"]["token"],
            refresh_token=st.session_state["creds"]["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        # Cria o serviço do Google Cloud Resource Manager
        service = build("cloudresourcemanager", "v1", credentials=creds)

        # Lista os projetos
        projects = service.projects().list().execute()
        if "projects" in projects:
            return [project["projectId"] for project in projects["projects"]]
        else:
            st.warning("Nenhum projeto encontrado no Google Cloud.")
            return None
    except Exception as e:
        st.error(f"Erro ao listar projetos do Google Cloud: {e}")
        return None

# Função para inicializar o Earth Engine com o projeto selecionado
def initialize_ee_with_project(project_id):
    try:
        # Inicializa o Earth Engine com o projeto
        ee.Initialize(credentials=st.session_state["creds"]["token"], project=project_id)
        st.session_state["ee_initialized"] = True
        st.session_state["selected_project"] = project_id
        st.success(f"Earth Engine inicializado com sucesso no projeto: {project_id}")
        return True
    except Exception as e:
        st.error(f"Erro ao inicializar o Earth Engine: {e}")
        return False

# Função para carregar o GeoJSON e visualizar o polígono
def load_geojson(file):
    try:
        gdf = gpd.read_file(file)
        if gdf.geometry.is_empty.any():
            st.error("O arquivo GeoJSON contém geometrias vazias.")
            return None, None
        if not all(gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])):
            st.error("O arquivo deve conter apenas polígonos ou multipolígonos.")
            return None, None
        gdf['geometry'] = gdf['geometry'].buffer(0)
        crs = gdf.crs if gdf.crs is not None else "EPSG:4326"
        st.write(f"CRS do arquivo GeoJSON: {crs}")
        centroid = gdf.geometry.centroid
        m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=10)
        for _, row in gdf.iterrows():
            folium.GeoJson(row['geometry']).add_to(m)
        st_folium(m, returned_objects=[])
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__), crs
    except Exception as e:
        st.error(f"Erro ao carregar o GeoJSON: {e}")
        return None, None

# Função para processar os dados
def process_data(geometry, crs, buffer_km=1, nome_bacia_export="bacia"):
    try:
        bacia = geometry.buffer(buffer_km * 1000)
        data_atual = datetime.datetime.now().strftime("%Y-%m-%d")
        periodo_fim = ee.Date(data_atual)
        periodo_inicio = periodo_fim.advance(-365, 'day')
        sentinel = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']) \
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
        mde = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2") \
            .filterBounds(bacia) \
            .mosaic() \
            .clip(bacia)
        declividade = ee.Terrain.slope(mde.select('DSM'))
        mapbiomas = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1") \
            .clip(bacia)
        pasture_quality = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_pasture_quality_v1") \
            .select('pasture_quality_2023') \
            .clip(bacia)
        return {
            "sentinel_median": sentinel_median,
            "indices": indices,
            "mde": mde,
            "declividade": declividade,
            "mapbiomas": mapbiomas,
            "pasture_quality": pasture_quality,
            "nome_bacia_export": nome_bacia_export,
        }
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None

# Função para exportar para o Google Drive
def export_to_drive(image, name, geometry, folder="zap"):
    try:
        # Verifica se as credenciais estão disponíveis
        if "creds" not in st.session_state:
            st.error("Erro: Credenciais de autenticação não encontradas.")
            return None

        # Exporta a imagem para o Drive
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=name,
            folder=folder,
            fileNamePrefix=name,
            scale=10,
            region=geometry,
            fileFormat='GeoTIFF',
            maxPixels=1e13,  # Ajuste conforme necessário
        )
        task.start()
        st.success(f"Exportação {name} iniciada. Verifique seu Google Drive na pasta '{folder}'.")
        return task
    except Exception as e:
        st.error(f"Erro ao exportar {name} para o Google Drive: {e}")
        return None

# Função para verificar o status das tarefas
def check_task_status(task):
    try:
        status = task.status()
        state = status["state"]
        if state == "COMPLETED":
            st.success(f"Tarefa {task.id} concluída com sucesso!")
        elif state == "RUNNING":
            st.warning(f"Tarefa {task.id} ainda está em execução.")
        elif state == "FAILED":
            st.error(f"Tarefa {task.id} falhou. Motivo: {status['error_message']}")
        else:
            st.info(f"Status da tarefa {task.id}: {state}")
        return state
    except Exception as e:
        st.error(f"Erro ao verificar o status da tarefa: {e}")
        return None

# Interface de upload e processamento
if not st.session_state.get("ee_initialized"):
    st.write("Para começar, faça login no Google Drive e Earth Engine:")

    # Botão de login integrado
    result = oauth2.authorize_button(
        "Autenticar no Google Drive e Earth Engine",
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
    )

    # Após o login
    if result:
        token = result["token"]
        st.session_state["creds"] = {
            "token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scopes": SCOPES.split(),  # Converte a string de escopos de volta para lista
        }
        st.session_state["drive_authenticated"] = True
        st.success("Autenticação no Google Drive e Earth Engine realizada com sucesso!")

        # Lista os projetos disponíveis
        projects = list_google_cloud_projects()
        if projects:
            selected_project = st.selectbox("Escolha um projeto:", projects)
            if st.button("Usar este projeto"):
                if initialize_ee_with_project(selected_project):
                    st.session_state["selected_project"] = selected_project
        else:
            st.error("""
                Nenhum projeto encontrado no Google Cloud. 
                Para usar o Earth Engine, você precisa criar um projeto no Google Cloud Platform:
                1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
                2. Crie um novo projeto.
                3. Volte aqui e recarregue a página.
            """)

if st.session_state.get("ee_initialized"):
    uploaded_file = st.file_uploader("Carregue o arquivo GeoJSON da bacia", type=["geojson"])
    
    if uploaded_file is not None:
        geometry, crs = load_geojson(uploaded_file)
        if geometry:
            st.write(f"CRS do arquivo GeoJSON: {crs}")
            nome_bacia_export = st.text_input("Digite o nome para exportação (sem espaços ou caracteres especiais):")
            
            if st.button("Processar Dados") and nome_bacia_export:
                resultados = process_data(geometry, crs, nome_bacia_export=nome_bacia_export)
                if resultados:
                    st.session_state["resultados"] = resultados
                    st.write("Índices processados:")
                    for key in resultados["indices"]:
                        st.write(f"- {key}")
            
            if st.session_state.get("resultados"):
                if st.button("Exportar Tudo para o Google Drive"):
                    st.session_state["export_started"] = True
                    resultados = st.session_state["resultados"]
                    tasks = []
                    for key, image in resultados["indices"].items():
                        task = export_to_drive(image, f"{resultados['nome_bacia_export']}_{key}", geometry)
                        if task:
                            tasks.append(task)
                    task = export_to_drive(resultados["mde"], f"{resultados['nome_bacia_export']}_MDE", geometry)
                    if task:
                        tasks.append(task)
                    task = export_to_drive(resultados["declividade"], f"{resultados['nome_bacia_export']}_Declividade", geometry)
                    if task:
                        tasks.append(task)
                    task = export_to_drive(resultados["mapbiomas"], f"{resultados['nome_bacia_export']}_MapBiomas", geometry)
                    if task:
                        tasks.append(task)
                    task = export_to_drive(resultados["pasture_quality"], f"{resultados['nome_bacia_export']}_QualidadePastagem", geometry)
                    if task:
                        tasks.append(task)
                    st.session_state["tasks"] = tasks
                    st.success("Todas as tarefas de exportação foram iniciadas.")
                
                if st.session_state.get("tasks"):
                    st.write("Verificando status das tarefas...")
                    for task in st.session_state["tasks"]:
                        check_task_status(task)