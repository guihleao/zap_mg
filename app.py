import ee
import streamlit as st
import geopandas as gpd
import pandas as pd
import datetime
import folium
from streamlit_folium import st_folium
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import time
from io import BytesIO

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# Dicionário de mapeamento de produtos
DICIONARIO_PRODUTOS = {
    'abacate23': 'Abacate',
    'abacaxi23': 'Abacaxi',
    'algodaa23': 'Algodão arbóreo (em caroço)',
    # ... (complete com todos os itens do seu dicionário original)
    'tucuna': 'Tucunaré'
}

# Configurações do Google Drive (substitua com seus IDs reais)
TABELAS_CSV = {
    "PAM_Quantidade_produzida_14-23": "10uwm4SgvYKDzTpi2jlPirjzPcL_5PTCB",
    "PAM_Valor_da_producao_14-23": "16VeRUfYvGgj2_swg_g671uJ_5I2QPpo2",
    # ... (adicione todas as tabelas)
}

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
    "https://www.googleapis.com/auth/earthengine",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/drive",
]
SCOPE = " ".join(SCOPES)

# Inicializar OAuth2Component
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

# Funções auxiliares
def carregar_csv_do_drive(file_id):
    """Carrega um CSV do Google Drive usando a API."""
    try:
        service = build('drive', 'v3', credentials=Credentials(
            token=st.session_state.token['access_token'],
            refresh_token=st.session_state.token.get('refresh_token'),
            token_uri=TOKEN_URL,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES
        ))
        request = service.files().get_media(fileId=file_id)
        fh = BytesIO(request.execute())
        return pd.read_csv(fh)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None

def intersect_municipios(geometry, municipios_gdf):
    """Calcula a interseção entre a bacia e os municípios."""
    try:
        bacia_gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
        area_bacia = bacia_gdf.geometry.area.sum() / 10000
        
        municipios_interseccao = gpd.overlay(municipios_gdf, bacia_gdf, how='intersection')
        municipios_interseccao['area_ha'] = municipios_interseccao.geometry.area / 10000
        municipios_interseccao['representatividade'] = (municipios_interseccao['area_ha'] / area_bacia) * 100
        
        return municipios_interseccao[municipios_interseccao['representatividade'] > 20]
    except Exception as e:
        st.error(f"Erro no cálculo de interseção: {e}")
        return None

def processar_tabelas_socioeconomicas(municipios_filtrados):
    """Processa as tabelas de dados socioeconômicos e agropecuários."""
    resultados = {}
    geocodigos = municipios_filtrados['geocodigo'].astype(str).tolist()
    
    for nome_tabela, file_id in TABELAS_CSV.items():
        try:
            df = carregar_csv_do_drive(file_id)
            if df is None:
                continue
                
            df_filtrado = df[df['geocodigo'].astype(str).isin(geocodigos)]
            
            if df_filtrado.empty:
                st.warning(f"Nenhum dado encontrado para {nome_tabela}")
                continue
                
            colunas_produtos = [col for col in df_filtrado.columns if col.endswith(tuple(str(ano)[-2:] for ano in range(14,24)))]
            
            top10 = (df_filtrado[colunas_produtos]
                     .sum()
                     .sort_values(ascending=False)
                     .head(10)
                     .reset_index()
                     .rename(columns={'index': 'produto', 0: 'valor'}))
            
            top10['produto_nome'] = top10['produto'].map(lambda x: DICIONARIO_PRODUTOS.get(x, x))
            resultados[nome_tabela] = top10
            
            # Exportar para CSV
            export_path = f"top10_{nome_tabela}.csv"
            top10.to_csv(export_path, index=False)
            st.success(f"Dados de {nome_tabela} processados e salvos em {export_path}")
            
        except Exception as e:
            st.error(f"Erro ao processar {nome_tabela}: {e}")
    
    return resultados

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

# Função para reprojetar imagens
def reprojetarImagem(imagem, epsg, escala):
    return imagem.reproject(crs=f"EPSG:{epsg}", scale=escala)

def exportarImagem(imagem, nome_prefixo, nome_sufixo, escala, regiao, nome_bacia_export, pasta="zap"):
    try:
        nome_arquivo = f"{nome_prefixo}{nome_bacia_export}{nome_sufixo}"
        task = ee.batch.Export.image.toDrive(
            image=imagem,
            description=nome_arquivo,
            folder=pasta,
            fileNamePrefix=nome_arquivo,
            scale=escala,
            region=regiao,
            fileFormat='GeoTIFF',
            maxPixels=1e13,
        )
        task.start()
        st.success(f"Exportação {nome_arquivo} iniciada. Verifique seu Google Drive na pasta '{pasta}'.")
        return task
    except Exception as e:
        st.error(f"Erro ao exportar {nome_arquivo} para o Google Drive: {e}")
        return None

# Função para processar os dados
def process_data(geometry, crs, nome_bacia_export="bacia"):
    try:
        bbox = geometry.bounds()
        bacia = bbox.buffer(1000)
        data_atual = datetime.datetime.now()
        periodo_fim = ee.Date(data_atual.strftime("%Y-%m-%d"))
        periodo_inicio = periodo_fim.advance(-365, 'day')

        ano_atual = data_atual.year
        ano_anterior = ano_atual - 1
        mes_formatado = data_atual.strftime("%b")

        sentinel = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']) \
            .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10) \
            .filterBounds(bacia) \
            .filterDate(periodo_inicio, periodo_fim)

        num_imagens = sentinel.size().getInfo()
        if num_imagens == 0:
            st.error("Nenhuma imagem foi encontrada para o período especificado.")
            return None
        else:
            st.success(f"Imagens encontradas: {num_imagens}")

            if st.session_state.get("exportar_sentinel_composite"):
                try:
                    sentinel_list = sentinel.toList(sentinel.size())
                    features = ee.FeatureCollection(sentinel_list.map(lambda img: ee.Feature(None, {
                        'id': ee.Image(img).id(),
                        'date': ee.Image(img).date().format('YYYY-MM-dd'),
                        'cloud_cover': ee.Image(img).get('CLOUDY_PIXEL_PERCENTAGE')
                    })))

                    export_task = ee.batch.Export.table.toDrive(
                        collection=features,
                        folder='zap',
                        description='lista_imagens_sentinel-2',
                        fileFormat='CSV'
                    )
                    export_task.start()
                    st.success("Exportação da lista de imagens Sentinel-2 iniciada.")
                except Exception as e:
                    st.error(f"Erro ao exportar a lista de imagens Sentinel-2: {e}")

        sentinel_median = sentinel.median().clip(bacia)
        sentinel_composite = sentinel_median.select(['B2', 'B3', 'B4', 'B8']).rename(['B2', 'B3', 'B4', 'B8'])

        indices = {
            "NDVI": sentinel_median.normalizedDifference(['B8', 'B4']),
            "GNDVI": sentinel_median.normalizedDifference(['B8', 'B3']),
            "NDWI": sentinel_median.normalizedDifference(['B3', 'B8']),
            "NDMI": sentinel_median.normalizedDifference(['B8', 'B11']),
        }

        mde_proj = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2").filterBounds(bacia).first().select(0).projection()
        mde = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2").filterBounds(bacia).mosaic().clip(bacia).setDefaultProjection(mde_proj)
        elevation = mde.select('DSM')

        declividade_graus = ee.Terrain.slope(elevation)
        declividade = declividade_graus.divide(180).multiply(3.14159).tan().multiply(100)
        declividade_reclass = declividade.expression(
            "b(0) == 0 ? 1 : " + 
            "b(0) <= 3 ? 1 : " + 
            "(b(0) > 3 && b(0) <= 8) ? 2 : " + 
            "(b(0) > 8 && b(0) <= 20) ? 3 : " + 
            "(b(0) > 20 && b(0) <= 45) ? 4 : " + 
            "(b(0) > 45 && b(0) <= 75) ? 5 : " + 
            "(b(0) > 75) ? 6 : -1"
        )

        mapbiomas = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1") \
            .select('classification_2023') \
            .clip(bacia)

        pasture_quality = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_pasture_quality_v1") \
            .select('pasture_quality_2023') \
            .clip(bacia)

        puc_ufv = ee.ImageCollection('users/zap/puc_ufv').filterBounds(bacia).mosaic().clip(bacia)
        puc_ibge = ee.ImageCollection('users/zap/puc_ibge').filterBounds(bacia).mosaic().clip(bacia)
        puc_embrapa = ee.ImageCollection('users/zap/puc_embrapa').filterBounds(bacia).mosaic().clip(bacia)

        landforms = ee.Image('CSP/ERGo/1_0/Global/SRTM_landforms').clip(bacia)

        fusos_mg = ee.FeatureCollection('users/zap/fusos_mg')
        fuso_maior_area = fusos_mg.filterBounds(bacia).map(lambda f: f.set('area', f.area())).sort('area', False).first()
        epsg = fuso_maior_area.get('epsg').getInfo()

        utm_elevation = reprojetarImagem(elevation, epsg, 30)
        utm_declividade = reprojetarImagem(declividade_reclass, epsg, 30).float()
        utm_ndvi = reprojetarImagem(indices["NDVI"], epsg, 10)
        utm_gndvi = reprojetarImagem(indices["GNDVI"], epsg, 10)
        utm_ndwi = reprojetarImagem(indices["NDWI"], epsg, 10)
        utm_ndmi = reprojetarImagem(indices["NDMI"], epsg, 10)
        utm_sentinel2 = reprojetarImagem(sentinel_composite, epsg, 10).float()
        utm_mapbiomas = reprojetarImagem(mapbiomas, epsg, 30)
        utm_pasture_quality = reprojetarImagem(pasture_quality, epsg, 30).float()
        utm_landforms = reprojetarImagem(landforms, epsg, 30)
        utm_puc_ufv = reprojetarImagem(puc_ufv, epsg, 30).float()
        utm_puc_ibge = reprojetarImagem(puc_ibge, epsg, 30).float()
        utm_puc_embrapa = reprojetarImagem(puc_embrapa, epsg, 30).float()

        return {
            "utm_elevation": utm_elevation,
            "utm_declividade": utm_declividade,
            "utm_ndvi": utm_ndvi,
            "utm_gndvi": utm_gndvi,
            "utm_ndwi": utm_ndwi,
            "utm_ndmi": utm_ndmi,
            "utm_sentinel2": utm_sentinel2,
            "utm_mapbiomas": utm_mapbiomas,
            "utm_pasture_quality": utm_pasture_quality,
            "utm_landforms": utm_landforms,
            "utm_puc_ufv": utm_puc_ufv,
            "utm_puc_ibge": utm_puc_ibge,
            "utm_puc_embrapa": utm_puc_embrapa,
            "nome_bacia_export": nome_bacia_export,
            "mes_formatado": mes_formatado,
            "ano_atual": ano_atual,
            "ano_anterior": ano_anterior,
        }
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None

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

# Verificar se o token está na session state
if 'token' not in st.session_state:
    st.write("Para começar, conecte-se à sua conta Google:")
    result = oauth2.authorize_button("Conectar à Conta Google", REDIRECT_URI, SCOPE)
    if result and 'token' in result:
        st.session_state.token = result.get('token')
        st.rerun()
else:
    token = st.session_state['token']
    st.success("Você está conectado à sua conta Google!")

    if "ee_initialized" not in st.session_state:
        try:
            credentials = Credentials(
                token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_uri=TOKEN_URL,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=SCOPES
            )

            service = build('cloudresourcemanager', 'v1', credentials=credentials)
            projects = service.projects().list().execute().get('projects', [])
            project_ids = [project['projectId'] for project in projects]

            if not project_ids:
                st.warning("Nenhum projeto encontrado na sua conta do Google Cloud.")
                if st.button("Criar um novo projeto"):
                    st.info("Funcionalidade de criação de projetos ainda não implementada.")
                    st.stop()
            else:
                selected_project = st.selectbox("Selecione um projeto:", project_ids)
                st.session_state["selected_project"] = selected_project

                ee.Initialize(credentials, project=selected_project)
                st.session_state["ee_initialized"] = True
                st.session_state["tasks"] = []
                st.success(f"Earth Engine inicializado com sucesso no projeto: {selected_project}")
        except Exception as e:
            st.error(f"Erro ao inicializar o Earth Engine: {e}")
            st.stop()

    if st.session_state.get("ee_initialized"):
        uploaded_file = st.file_uploader("Carregue o arquivo GeoJSON da bacia", type=["geojson"])
        
        if uploaded_file is not None:
            geometry, crs = load_geojson(uploaded_file)
            if geometry:
                st.write(f"CRS do arquivo GeoJSON: {crs}")
                nome_bacia_export = st.text_input("Digite o nome para exportação (sem espaços ou caracteres especiais):")
                
                # Opção para processar dados socioeconômicos
                processar_dados_extras = st.checkbox("Processar dados socioeconômicos e agropecuários")
                
                if processar_dados_extras:
                    st.info("Os dados socioeconômicos serão processados junto com as imagens selecionadas")
                
                st.write("Selecione os produtos que deseja exportar:")
                with st.form(key='product_selection_form'):
                    exportar_srtm_mde = st.checkbox("SRTM MDE (30m)", value=True)
                    exportar_declividade = st.checkbox("Declividade (30m)", value=True)
                    exportar_ndvi = st.checkbox("NDVI (10m)", value=True)
                    exportar_gndvi = st.checkbox("GNDVI (10m)", value=True)
                    exportar_ndwi = st.checkbox("NDWI (10m)", value=True)
                    exportar_ndmi = st.checkbox("NDMI (10m)", value=True)
                    exportar_mapbiomas = st.checkbox("MapBiomas 2023 (30m)", value=True)
                    exportar_pasture_quality = st.checkbox("Qualidade de Pastagem 2023 (30m)", value=True)
                    exportar_sentinel_composite = st.checkbox("Sentinel-2 B2/B3/B4/B8 (10m)", value=True)
                    exportar_puc_ufv = st.checkbox("PUC UFV (30m)", value=True)
                    exportar_puc_ibge = st.checkbox("PUC IBGE (30m)", value=True)
                    exportar_puc_embrapa = st.checkbox("PUC Embrapa (30m)", value=True)
                    exportar_landforms = st.checkbox("Landforms (30m)", value=True)

                    submit_button = st.form_submit_button(label='Confirmar Seleção')

                if submit_button:
                    st.session_state["exportar_srtm_mde"] = exportar_srtm_mde
                    st.session_state["exportar_declividade"] = exportar_declividade
                    st.session_state["exportar_ndvi"] = exportar_ndvi
                    st.session_state["exportar_gndvi"] = exportar_gndvi
                    st.session_state["exportar_ndwi"] = exportar_ndwi
                    st.session_state["exportar_ndmi"] = exportar_ndmi
                    st.session_state["exportar_mapbiomas"] = exportar_mapbiomas
                    st.session_state["exportar_pasture_quality"] = exportar_pasture_quality
                    st.session_state["exportar_sentinel_composite"] = exportar_sentinel_composite
                    st.session_state["exportar_puc_ufv"] = exportar_puc_ufv
                    st.session_state["exportar_puc_ibge"] = exportar_puc_ibge
                    st.session_state["exportar_puc_embrapa"] = exportar_puc_embrapa
                    st.session_state["exportar_landforms"] = exportar_landforms
                    st.session_state["processar_dados_extras"] = processar_dados_extras
                    st.success("Seleção de produtos confirmada!")

                if st.session_state.get("exportar_srtm_mde") is not None:
                    if st.button("Processar Dados") and nome_bacia_export:
                        with st.spinner("Processando dados, por favor aguarde..."):
                            resultados = process_data(geometry, crs, nome_bacia_export=nome_bacia_export)
                            
                            if resultados:
                                st.session_state["resultados"] = resultados
                                st.success("Dados processados com sucesso, iniciando exportação!")

                                tasks_selecionadas = []
                                if st.session_state.get("exportar_srtm_mde"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_elevation"], "06_", "_SRTM_MDE", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_declividade"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_declividade"], "02_", "_declividade", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_ndvi"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndvi"], "06_", f"_NDVImediana_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_gndvi"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_gndvi"], "06_", f"_GNDVImediana_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_ndwi"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndwi"], "06_", f"_NDWImediana_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_ndmi"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndmi"], "06_", f"_NDMImediana_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_mapbiomas"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_mapbiomas"], "06_", "_MapBiomas_col9_2023", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_pasture_quality"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_pasture_quality"], "06_", "_Pastagem_col9_2023", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_sentinel_composite"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_sentinel2"], "06_", f"_S2_B2B3B4B8_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_puc_ufv"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_ufv"], "02_", "_puc_ufv", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_puc_ibge"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_ibge"], "02_", "_puc_ibge", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_puc_embrapa"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_embrapa"], "02_", "_puc_embrapa", 30, geometry, nome_bacia_export, "zap"))
                                if st.session_state.get("exportar_landforms"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_landforms"], "06_", "_landforms", 30, geometry, nome_bacia_export, "zap"))

                                if tasks_selecionadas:
                                    st.session_state["tasks"] = tasks_selecionadas
                                    st.success("Exportação dos produtos selecionados iniciada.")
                                else:
                                    st.warning("Nenhum produto selecionado para exportação.")
                                
                                # Processar dados socioeconômicos se selecionado
                                if st.session_state.get("processar_dados_extras"):
                                    st.info("Processando dados socioeconômicos...")
                                    
                                    # Carregar municípios (substitua pelo seu arquivo)
                                    municipios_gdf = gpd.read_file("https://drive.google.com/.../municipios.geojson") 
                                    
                                    municipios_filtrados = intersect_municipios(geometry, municipios_gdf)
                                    
                                    if municipios_filtrados is not None and not municipios_filtrados.empty:
                                        st.write(f"Municípios com >20% de representatividade: {len(municipios_filtrados)}")
                                        resultados_socio = processar_tabelas_socioeconomicas(municipios_filtrados)
                                        
                                        for tabela, dados in resultados_socio.items():
                                            st.write(f"Top 10 produtos - {tabela}")
                                            st.dataframe(dados)
                                    else:
                                        st.warning("Nenhum município com mais de 20% de representatividade encontrado.")

                                if st.session_state.get("tasks"):
                                    st.write("Verificando status das tarefas... Por favor aguarde, dependendo do tamanho da bacia, pode levar até 20 minutos.")
                                    
                                    status_placeholder = st.empty()

                                    while True:
                                        status_placeholder.empty()

                                        todas_concluidas = True
                                        for task in st.session_state["tasks"]:
                                            state = check_task_status(task)
                                            if state != "COMPLETED":
                                                todas_concluidas = False

                                        if todas_concluidas:
                                            status_placeholder.success("Todas as tarefas foram concluídas com sucesso!")
                                            break

                                        time.sleep(60)