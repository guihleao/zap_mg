import ee
import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import datetime
import folium
from streamlit_folium import st_folium
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import time
import requests
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import gdown

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# 1. Configuração inicial e autenticação (mantida igual)
if 'google_oauth' in st.secrets:
    CLIENT_ID = st.secrets['google_oauth']['client_id']
    CLIENT_SECRET = st.secrets['google_oauth']['client_secret']
    REDIRECT_URI = st.secrets['google_oauth']['redirect_uris']
else:
    st.error("Configurações do OAuth2 não encontradas no secrets.toml.")
    st.stop()

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"

SCOPES = [
    "https://www.googleapis.com/auth/earthengine",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/drive",
]
SCOPE = " ".join(SCOPES)

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

# 2. Dicionário de produtos (completo)
DICIONARIO_PRODUTOS = {
    'abacate': 'Abacate', 'abacaxi': 'Abacaxi', 'algodaa': 'Algodão arbóreo', 
    'algodah': 'Algodão herbáceo', 'alho': 'Alho', 'amendoi': 'Amendoim', 
    'arroz': 'Arroz', 'aveia': 'Aveia', 'azeiton': 'Azeitona', 'acai': 'Açaí',
    'banana': 'Banana', 'batatad': 'Batata-doce', 'batatai': 'Batata-inglesa',
    'borrach': 'Borracha', 'cacau': 'Cacau', 'cafeara': 'Café Arábica',
    'cafecan': 'Café Canephora', 'cafetot': 'Café Total', 'cana': 'Cana-de-açúcar',
    'caqui': 'Caqui', 'castcaj': 'Castanha de caju', 'cebola': 'Cebola',
    'centeio': 'Centeio', 'cevada': 'Cevada', 'chaind': 'Chá-da-índia',
    'cocobai': 'Coco-da-baía', 'dende': 'Dendê', 'ervamat': 'Erva-mate',
    'ervilha': 'Ervilha', 'fava': 'Fava', 'feijao': 'Feijão', 'figo': 'Figo',
    'fumo': 'Fumo', 'girass': 'Girassol', 'goiaba': 'Goiaba', 'guarana': 'Guaraná',
    'juta': 'Juta', 'laranja': 'Laranja', 'limao': 'Limão', 'linho': 'Linho',
    'mamona': 'Mamona', 'mamao': 'Mamão', 'mandioc': 'Mandioca', 'manga': 'Manga',
    'maracuj': 'Maracujá', 'marmelo': 'Marmelo', 'maca': 'Maçã', 'melanci': 'Melancia',
    'melao': 'Melão', 'milho': 'Milho', 'noz': 'Noz', 'palmito': 'Palmito',
    'pera': 'Pera', 'pimrein': 'Pimenta-do-reino', 'pessego': 'Pêssego',
    'rami': 'Rami', 'sisal': 'Sisal', 'soja': 'Soja', 'sorgo': 'Sorgo',
    'tangeri': 'Tangerina', 'tomate': 'Tomate', 'trigo': 'Trigo', 
    'tritica': 'Triticale', 'tungue': 'Tungue', 'urucum': 'Urucum', 'uva': 'Uva',
    'bovino': 'Bovino', 'bubalin': 'Bubalino', 'caprino': 'Caprino', 
    'codorna': 'Codornas', 'equino': 'Equino', 'galin': 'Galináceos',
    'ovino': 'Ovino', 'suino': 'Suíno', 'bichsed': 'Casulos do bicho-da-seda',
    'leite': 'Leite', 'la': 'Lã', 'mel': 'Mel', 'ovocod': 'Ovos de codorna',
    'ovogal': 'Ovos de galinha', 'alevino': 'Alevinos', 'camarao': 'Camarão',
    'carpa': 'Carpa', 'curimat': 'Curimatã', 'dourado': 'Dourado',
    'jatuara': 'Jatuarana', 'lambari': 'Lambari', 'camlarv': 'Larvas de camarão',
    'matrinx': 'Matrinxã', 'mexilh': 'Mexilhões', 'outpeix': 'Outros peixes',
    'pacu': 'Pacu', 'piau': 'Piau', 'pintado': 'Pintado', 'pirapi': 'Pirapitinga',
    'piraruc': 'Pirarucu', 'semmol': 'Sementes de moluscos', 'tambacu': 'Tambacu',
    'tambaqu': 'Tambaqui', 'tilapia': 'Tilápia', 'traira': 'Traíra', 'truta': 'Truta',
    'tucuna': 'Tucunaré', 'eucalip': 'Eucalipto', 'outesp': 'Outras espécies',
    'pinus': 'Pinus', 'carveg': 'Carvão vegetal', 'lenha': 'Lenha',
    'madtor': 'Madeira em tora', 'outprod': 'Outros produtos'
}

# 3. URLs das tabelas (convertidas para links diretos do Google Drive)
TABELAS_AGRO = {
    'PAM_Quantidade_produzida_14-23': 'https://drive.google.com/uc?id=10uwm4SgvYKDzTpi2jlPirjzPcL_5PTCB',
    'PAM_Valor_da_producao_14-23': 'https://drive.google.com/uc?id=16VeRUfYvGgj2_swg_g671uJ_5I2QPpo2',
    'PPM_Efetivo_dos_rebanhos_14-23': 'https://drive.google.com/uc?id=18I1Yr7qsICf8hBtBawkmG9Wes5Hd2hBz',
    'PPM_Prod_origem_animal_14-23': 'https://drive.google.com/uc?id=19-yrafwVj0ZOPiqbwhqX1Ho3Gwr1GoIA',
    'PPM_Valor_da_producao_prod_animal_14-23': 'https://drive.google.com/uc?id=19BaNA96nXA4gtkmF_nwSQFdxA5UEBmmx',
    'PPM_Producao_aquicultura_14-23': 'https://drive.google.com/uc?id=1A9o-eEiXpPMWOyCtE4m2jwYaovRy9bv9',
    'PPM_Valor_producao_aquicultura_14-23': 'https://drive.google.com/uc?id=1BzPQy5pFNrqgC_9gHCUDO7Sy4O-t6nrA',
    'PEVS_Area_silv_14-23': 'https://drive.google.com/uc?id=1VTNqLYXi5AjiWCZDu2cUfbmVzwYjbLrY',
    'PEVS_Qnt_prod_silv_14-23': 'https://drive.google.com/uc?id=1qIHRhddxGV8WtEEt0lJcaxnUpKjF1MBK',
    'PEVS_Valor_prod_silv_14-23': 'https://drive.google.com/uc?id=1s-9uSiVOxZJLgIKVP8ZI8rCo99DgiEIf',
    'IBGE_Municipios_ZAP': 'https://drive.google.com/uc?id=1skVkA0cN3TVlJThvqsilWwO2SGLY-joi'
}

# 4. Funções auxiliares (mantidas iguais)
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

# 5. Novas funções para processamento dos dados agro
def processar_municipios(geometry, nome_bacia_export):
    try:
        # Carregar municípios de MG (do Earth Engine)
        municipios_mg = ee.FeatureCollection("projects/ee-zapmg/assets/mg-municipios")
        
        # Calcular área da bacia
        area_bacia = geometry.area()
        
        # Função para calcular interseção
        def calcular_intersecao(feature):
            intersecao = feature.geometry().intersection(geometry, 1)
            area_intersecao = intersecao.area()
            percentual = area_intersecao.divide(area_bacia).multiply(100)
            
            return feature.set({
                'area_intersecao_ha': area_intersecao.divide(10000),
                'percentual_na_bacia': percentual,
                'area_municipio_ha': feature.geometry().area().divide(10000),
                'area_bacia_ha': area_bacia.divide(10000)
            })
        
        # Processar todos os municípios que intersectam
        municipios_processados = municipios_mg.filterBounds(geometry).map(calcular_intersecao)
        
        # Filtrar municípios com mais de 20% de representatividade
        municipios_selecionados = municipios_processados.filter(ee.Filter.gte('percentual_na_bacia', 20))
        
        # Converter para Pandas DataFrame
        features = municipios_selecionados.getInfo()['features']
        dados_municipios = []
        
        for feature in features:
            props = feature['properties']
            props['geocodigo'] = int(props['geocodigo'])  # Garantir que é inteiro
            dados_municipios.append(props)
        
        df_municipios = pd.DataFrame(dados_municipios)
        
        if not df_municipios.empty:
            df_municipios = df_municipios.sort_values('percentual_na_bacia', ascending=False)
            st.success(f"{len(df_municipios)} municípios selecionados com mais de 20% de área na bacia")
            return df_municipios
        else:
            st.warning("Nenhum município com mais de 20% de área na bacia foi encontrado.")
            return None
            
    except Exception as e:
        st.error(f"Erro ao processar municípios: {e}")
        return None

def baixar_tabela(url):
    try:
        output = BytesIO()
        gdown.download(url, output, quiet=True)
        output.seek(0)
        return pd.read_csv(output)
    except Exception as e:
        st.error(f"Erro ao baixar tabela: {e}")
        return None

def processar_tabelas_agro(geocodigos):
    resultados = {}
    
    for nome_tabela, url in TABELAS_AGRO.items():
        if nome_tabela == 'IBGE_Municipios_ZAP':
            continue  # Processamos separadamente
            
        df = baixar_tabela(url)
        if df is None:
            resultados[nome_tabela] = None
            continue
            
        # Converter geocodigo para inteiro
        df['geocodigo'] = df['geocodigo'].astype(int)
        
        # Filtrar municípios selecionados
        df_filtrado = df[df['geocodigo'].isin(geocodigos)]
        
        if df_filtrado.empty:
            resultados[nome_tabela] = None
            continue
            
        # Para tabelas de produção, identificar top 10 produtos de 2023
        if nome_tabela.startswith(('PAM', 'PPM', 'PEVS')):
            colunas_2023 = [col for col in df_filtrado.columns if col.endswith('23') and col not in ['geocodigo', 'nome']]
            
            if colunas_2023:
                # Somar valores por produto
                soma_produtos = df_filtrado[colunas_2023].sum().sort_values(ascending=False)
                top_10 = soma_produtos.head(10).index.tolist()
                
                # Selecionar colunas relevantes
                colunas_selecionadas = ['geocodigo', 'nome']
                for produto in top_10:
                    base = produto[:-2]
                    cols_produto = [col for col in df_filtrado.columns if col.startswith(base)]
                    colunas_selecionadas.extend(cols_produto)
                
                df_resultado = df_filtrado[colunas_selecionadas]
                
                # Traduzir nomes das colunas
                novo_nomes = {}
                for col in df_resultado.columns:
                    if col not in ['geocodigo', 'nome']:
                        base = col[:-2] if col[-2:].isdigit() else col
                        novo_nome = DICIONARIO_PRODUTOS.get(base, base)
                        novo_nomes[col] = f"{novo_nome}_{col[-2:]}" if col[-2:].isdigit() else novo_nome
                    else:
                        novo_nomes[col] = col
                
                df_resultado = df_resultado.rename(columns=novo_nomes)
                resultados[nome_tabela] = df_resultado
            else:
                resultados[nome_tabela] = df_filtrado
        else:
            resultados[nome_tabela] = df_filtrado
    
    return resultados

def gerar_excel_agro(dados_agro, nome_bacia_export):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for nome_tabela, df in dados_agro.items():
                if df is not None:
                    df.to_excel(writer, sheet_name=nome_tabela[:31], index=False)
        
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {e}")
        return None

# 6. Processamento principal (modificado)
def process_data(geometry, crs, nome_bacia_export="bacia"):
    try:
        # ... (código existente de processamento de imagens)
        
        # Se selecionado, processar dados agro
        if st.session_state.get("exportar_dados_agro"):
            st.session_state["municipios_df"] = processar_municipios(geometry, nome_bacia_export)
            
            if st.session_state["municipios_df"] is not None:
                geocodigos = st.session_state["municipios_df"]['geocodigo'].tolist()
                st.session_state["dados_agro"] = processar_tabelas_agro(geocodigos)
                
                # Baixar tabela IBGE separadamente
                df_ibge = baixar_tabela(TABELAS_AGRO['IBGE_Municipios_ZAP'])
                if df_ibge is not None:
                    df_ibge['geocodigo'] = df_ibge['geocodigo'].astype(int)
                    st.session_state["ibge_municipios"] = df_ibge[df_ibge['geocodigo'].isin(geocodigos)]
        
        return {
            # ... (resultados existentes)
            "nome_bacia_export": nome_bacia_export,
            "mes_formatado": mes_formatado,
            "ano_atual": ano_atual,
            "ano_anterior": ano_anterior,
        }
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# 7. Interface do usuário (modificada)
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
                
                with st.form(key='product_selection_form'):
                    col1, col2 = st.columns(2)
                    with col1:
                        exportar_srtm_mde = st.checkbox("SRTM MDE (30m)", value=True)
                        exportar_declividade = st.checkbox("Declividade (30m)", value=True)
                        exportar_ndvi = st.checkbox("NDVI (10m)", value=True)
                        exportar_gndvi = st.checkbox("GNDVI (10m)", value=True)
                        exportar_ndwi = st.checkbox("NDWI (10m)", value=True)
                        exportar_ndmi = st.checkbox("NDMI (10m)", value=True)
                    with col2:
                        exportar_mapbiomas = st.checkbox("MapBiomas 2023 (30m)", value=True)
                        exportar_pasture_quality = st.checkbox("Qualidade de Pastagem 2023 (30m)", value=True)
                        exportar_sentinel_composite = st.checkbox("Sentinel-2 B2/B3/B4/B8 (10m)", value=True)
                        exportar_puc_ufv = st.checkbox("PUC UFV (30m)", value=True)
                        exportar_puc_ibge = st.checkbox("PUC IBGE (30m)", value=True)
                        exportar_puc_embrapa = st.checkbox("PUC Embrapa (30m)", value=True)
                        exportar_landforms = st.checkbox("Landforms (30m)", value=True)
                    
                    st.markdown("---")
                    exportar_dados_agro = st.checkbox("Dados Agro e Socioeconômicos", value=False)
                    
                    submit_button = st.form_submit_button(label='Confirmar Seleção')

                if submit_button:
                    st.session_state.update({
                        "exportar_srtm_mde": exportar_srtm_mde,
                        "exportar_declividade": exportar_declividade,
                        "exportar_ndvi": exportar_ndvi,
                        "exportar_gndvi": exportar_gndvi,
                        "exportar_ndwi": exportar_ndwi,
                        "exportar_ndmi": exportar_ndmi,
                        "exportar_mapbiomas": exportar_mapbiomas,
                        "exportar_pasture_quality": exportar_pasture_quality,
                        "exportar_sentinel_composite": exportar_sentinel_composite,
                        "exportar_puc_ufv": exportar_puc_ufv,
                        "exportar_puc_ibge": exportar_puc_ibge,
                        "exportar_puc_embrapa": exportar_puc_embrapa,
                        "exportar_landforms": exportar_landforms,
                        "exportar_dados_agro": exportar_dados_agro
                    })
                    st.success("Seleção de produtos confirmada!")

                if st.session_state.get("exportar_srtm_mde") is not None and nome_bacia_export:
                    if st.button("Processar Dados"):
                        with st.spinner("Processando dados, por favor aguarde..."):
                            resultados = process_data(geometry, crs, nome_bacia_export)
                            
                            if resultados:
                                st.session_state["resultados"] = resultados
                                st.success("Dados processados com sucesso!")
                                
                                # Exportar imagens
                                tasks_selecionadas = []
                                if st.session_state.get("exportar_srtm_mde"):
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_elevation"], "06_", "_SRTM_MDE", 30, geometry, nome_bacia_export))
                                # ... (adicionar outras exportações de imagem conforme necessário)
                                
                                # Processar dados agro se selecionado
                                if st.session_state.get("exportar_dados_agro") and 'municipios_df' in st.session_state:
                                    st.info("Processando dados agro e socioeconômicos...")
                                    
                                    # Gerar Excel com dados agro
                                    excel_agro = gerar_excel_agro(st.session_state["dados_agro"], nome_bacia_export)
                                    
                                    if excel_agro:
                                        # Adicionar planilha IBGE se existir
                                        if 'ibge_municipios' in st.session_state and st.session_state["ibge_municipios"] is not None:
                                            with pd.ExcelWriter(excel_agro, engine='openpyxl', mode='a') as writer:
                                                st.session_state["ibge_municipios"].to_excel(
                                                    writer, sheet_name='IBGE_Municipios_ZAP', index=False)
                                        
                                        # Oferecer download
                                        st.download_button(
                                            label="Baixar Dados Agro e Socioeconômicos",
                                            data=excel_agro,
                                            file_name=f"{nome_bacia_export}_dados_agro.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                        )
                                
                                # Verificar status das tarefas
                                if tasks_selecionadas:
                                    st.session_state["tasks"] = tasks_selecionadas
                                    st.write("Verificando status das tarefas...")
                                    
                                    status_placeholder = st.empty()
                                    todas_concluidas = False
                                    
                                    while not todas_concluidas:
                                        status_placeholder.empty()
                                        todas_concluidas = True
                                        
                                        for task in st.session_state["tasks"]:
                                            state = check_task_status(task)
                                            if state != "COMPLETED":
                                                todas_concluidas = False
                                        
                                        if todas_concluidas:
                                            status_placeholder.success("Todas as tarefas concluídas!")
                                            break
                                        
                                        time.sleep(60)