import ee
import streamlit as st
import geopandas as gpd
import datetime
import folium
from streamlit_folium import st_folium
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Carregar configurações do OAuth2 do secrets.toml
if 'google_oauth' in st.secrets:
    CLIENT_ID = st.secrets['google_oauth']['client_id']
    CLIENT_SECRET = st.secrets['google_oauth']['client_secret']
    REDIRECT_URI = st.secrets['google_oauth']['redirect_uris']
else:
    st.error("Configurações do OAuth2 não encontradas no secrets.toml.")
    st.stop()

# URLs do OAuth2 (Google)
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"

# Scopes necessários
SCOPES = [
    "https://www.googleapis.com/auth/earthengine",  # Earth Engine
    "https://www.googleapis.com/auth/cloud-platform",  # Cloud Platform
    "https://www.googleapis.com/auth/drive",  # Google Drive
]
SCOPE = " ".join(SCOPES)  # Juntar os scopes em uma única string

# Inicializar OAuth2Component
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

# Verificar se o token está na session state
if 'token' not in st.session_state:
    # Se não estiver, mostrar o botão de autorização
    st.write("Para começar, conecte-se à sua conta Google:")
    result = oauth2.authorize_button("Conectar à Conta Google", REDIRECT_URI, SCOPE)
    if result and 'token' in result:
        # Se a autorização for bem-sucedida, salvar o token na session state
        st.session_state.token = result.get('token')
        st.rerun()
else:
    # Se o token estiver na session state, inicializar o Earth Engine automaticamente
    token = st.session_state['token']
    st.success("Você está conectado à sua conta Google!")

    # Inicializar o Earth Engine
    if "ee_initialized" not in st.session_state:
        try:
            # Criar credenciais a partir do token
            credentials = Credentials(
                token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_uri=TOKEN_URL,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=SCOPES
            )

            # Listar projetos disponíveis
            service = build('cloudresourcemanager', 'v1', credentials=credentials)
            projects = service.projects().list().execute().get('projects', [])
            project_ids = [project['projectId'] for project in projects]

            if not project_ids:
                st.warning("Nenhum projeto encontrado na sua conta do Google Cloud.")
                if st.button("Criar um novo projeto"):
                    # Lógica para criar um novo projeto (implemente conforme necessário)
                    st.info("Funcionalidade de criação de projetos ainda não implementada.")
                    st.stop()
            else:
                # Permitir que o usuário selecione um projeto
                selected_project = st.selectbox("Selecione um projeto:", project_ids)
                st.session_state["selected_project"] = selected_project

                # Inicializar o Earth Engine com o projeto selecionado
                ee.Initialize(credentials, project=selected_project)
                st.session_state["ee_initialized"] = True
                st.success(f"Earth Engine inicializado com sucesso no projeto: {selected_project}")
        except Exception as e:
            st.error(f"Erro ao inicializar o Earth Engine: {e}")
            st.stop()  # Interrompe a execução se a inicialização falhar

    # Restante do código (carregar GeoJSON, processar dados, exportar para o Drive)
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