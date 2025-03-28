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

# 1. Configuração inicial e autenticação
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
    'PAM_Quantidade_produzida_14-23': 'https://drive.google.com/uc?id=19BaNA96nXA4gtkmF_nwSQFdxA5UEBmmx',
    'PAM_Valor_da_producao_14-23': 'https://drive.google.com/uc?id=1A9o-eEiXpPMWOyCtE4m2jwYaovRy9bv9',
    'PPM_Efetivo_dos_rebanhos_14-23': 'https://drive.google.com/uc?id=1VTNqLYXi5AjiWCZDu2cUfbmVzwYjbLrY',
    'PPM_Prod_origem_animal_14-23': 'https://drive.google.com/uc?id=18I1Yr7qsICf8hBtBawkmG9Wes5Hd2hBz',
    'PPM_Valor_da_producao_prod_animal_14-23': 'https://drive.google.com/uc?id=1s-9uSiVOxZJLgIKVP8ZI8rCo99DgiEIf',
    'PPM_Producao_aquicultura_14-23': 'https://drive.google.com/uc?id=16VeRUfYvGgj2_swg_g671uJ_5I2QPpo2',
    'PPM_Valor_producao_aquicultura_14-23': 'https://drive.google.com/uc?id=19-yrafwVj0ZOPiqbwhqX1Ho3Gwr1GoIA',
    'PEVS_Area_silv_14-23': 'https://drive.google.com/uc?id=10uwm4SgvYKDzTpi2jlPirjzPcL_5PTCB',
    'PEVS_Qnt_prod_silv_14-23': 'https://drive.google.com/uc?id=1qIHRhddxGV8WtEEt0lJcaxnUpKjF1MBK',
    'PEVS_Valor_prod_silv_14-23': 'https://drive.google.com/uc?id=1BzPQy5pFNrqgC_9gHCUDO7Sy4O-t6nrA',
    'IBGE_Municipios_ZAP': 'https://drive.google.com/uc?id=1skVkA0cN3TVlJThvqsilWwO2SGLY-joi'
}

# 4. Funções auxiliares
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

# 5. Funções para processamento dos dados agro
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
            
            # Formatando as colunas numéricas
            df_municipios['area_intersecao_ha'] = df_municipios['area_intersecao_ha'].round(2)
            df_municipios['percentual_na_bacia'] = df_municipios['percentual_na_bacia'].round(2)
            df_municipios['area_municipio_ha'] = df_municipios['area_municipio_ha'].round(2)
            
            # Criando DataFrame para exibição
            df_display = df_municipios[['nome', 'area_intersecao_ha', 'percentual_na_bacia']].copy()
            df_display.columns = ['Município', 'Área na Bacia (ha)', 'Representatividade (%)']
            
            st.success(f"{len(df_municipios)} município(s) selecionado(s) com mais de 20% de área na bacia")
            
            # Mostrar tabela detalhada
            st.write("### Detalhes dos Municípios")
            st.dataframe(df_display.sort_values('Representatividade (%)', ascending=False))
            
            # Adicionar métricas resumidas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Municípios selecionados", len(df_municipios))
            with col2:
                st.metric("Área total na bacia (ha)", 
                         round(df_municipios['area_intersecao_ha'].sum(), 2))
            with col3:
                st.metric("Representatividade média (%)", 
                         round(df_municipios['percentual_na_bacia'].mean(), 2))
            
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
    
    # Processar todas as tabelas, incluindo IBGE
    for nome_tabela, url in TABELAS_AGRO.items():
        df = baixar_tabela(url)
        if df is None:
            continue
            
        # Converter geocodigo para inteiro
        df['geocodigo'] = df['geocodigo'].astype(int)
        
        # Filtrar municípios selecionados
        df_filtrado = df[df['geocodigo'].isin(geocodigos)]
        
        if df_filtrado.empty:
            continue
            
        # Tratamento especial para tabela IBGE
        if nome_tabela == 'IBGE_Municipios_ZAP':
            # Remover colunas indesejadas (mas manter 'Municípios')
            colunas_remover = [col for col in ['.geo', 'system:index'] if col in df_filtrado.columns]
            if colunas_remover:
                df_filtrado = df_filtrado.drop(columns=colunas_remover)
            
            # Renomear colunas conforme solicitado
            renomear = {
                'População ocupada': 'População ocupada {%}',
                'Densidade demográfica': 'Densidade demográfica (hab/km²)',
                'Esgotamento sanitário adequado': 'Esgotamento sanitário adequado {%}',
                'Mortalidade Infantil': 'Mortalidade Infantil {%}',
                'Taxa de escolarização de 6 a 14 anos de idade': 'Taxa de escolarização de 6 a 14 anos de idade {%}',
                'Urbanização de vias públicas': 'Urbanização de vias públicas {%}',
                'Arborização de vias públicas': 'Arborização de vias públicas {%}'
            }
            df_filtrado = df_filtrado.rename(columns=renomear)
            
            # Definir a ordem das colunas (incluindo 'Municípios')
            ordem_colunas = [
                'Municípios',
                'geocodigo',
                'Gentílico',
                'Bioma predominante',
                'Área (km²)',
                'População no último censo',
                'População ocupada {%}',
                'Densidade demográfica (hab/km²)',
                'PIB per capita',
                'Salário médio mensal dos trabalhadores formais',
                'Receitas',
                'Despesas',
                'Esgotamento sanitário adequado {%}',
                'Estabelecimentos de Saúde SUS',
                'Mortalidade Infantil {%}',
                'Taxa de escolarização de 6 a 14 anos de idade {%}',
                'Urbanização de vias públicas {%}',
                'Arborização de vias públicas {%}',
                'Índice de Desenvolvimento Humano Municipal (IDHM)'
            ]
            
            # Manter apenas as colunas que existem no DataFrame
            ordem_colunas = [col for col in ordem_colunas if col in df_filtrado.columns]
            
            # Reordenar as colunas e transpor
            df_final = df_filtrado[ordem_colunas].set_index('Municípios').T
            df_final.index.name = 'Indicador'
            resultados[nome_tabela] = df_final
            continue
            
        # Para outras tabelas, criar uma planilha com top 10 produtos por município
        municipios_dfs = {}
        for _, row in df_filtrado.iterrows():
            municipio = row['nome']
            geocodigo = row['geocodigo']
            
            # Identificar colunas de anos (terminadas com 2 dígitos)
            colunas_ano = [col for col in row.index if col[-2:].isdigit() and col not in ['geocodigo', 'nome']]
            
            # Agrupar por produto (prefixo antes do ano)
            produtos = {}
            for col in colunas_ano:
                produto = col[:-2]
                ano = col[-2:]
                valor = row[col]
                
                if produto not in produtos:
                    produtos[produto] = {}
                produtos[produto][ano] = valor
            
            # Converter para DataFrame e pegar top 10 produtos com maior valor em 2023
            df_produtos = pd.DataFrame.from_dict(produtos, orient='index')
            
            # Ordenar por 2023 (se existir) ou pelo último ano disponível
            if '23' in df_produtos.columns:
                df_produtos = df_produtos.sort_values('23', ascending=False)
            else:
                ultimo_ano = sorted(df_produtos.columns)[-1]
                df_produtos = df_produtos.sort_values(ultimo_ano, ascending=False)
            
            # Pegar top 10 e traduzir nomes
            top_10 = df_produtos.head(10)
            top_10.index = [DICIONARIO_PRODUTOS.get(p, p) for p in top_10.index]
            
            # Adicionar município como coluna
            top_10 = top_10.reset_index()
            top_10.columns = ['Produto'] + [f'20{ano}' for ano in top_10.columns[1:]]
            
            municipios_dfs[municipio] = top_10
        
        resultados[nome_tabela] = municipios_dfs
    
    return resultados

def gerar_excel_agro(dados_agro, nome_bacia_export):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Escrever cada planilha
            for nome_tabela, dados in dados_agro.items():
                # Tabela IBGE tem tratamento especial (já está correta)
                if nome_tabela == 'IBGE_Municipios_ZAP':
                    dados.to_excel(writer, sheet_name='IBGE_Municipios', index=True)
                    continue
                
                # Para outras tabelas, consolidar todos os municípios em uma planilha
                if isinstance(dados, dict):
                    # Criar DataFrame consolidado
                    df_consolidado = pd.DataFrame()
                    
                    for municipio, df in dados.items():
                        # Adicionar linha com nome do município
                        df_municipio = pd.DataFrame([f"{municipio}"], columns=['Produto'])
                        df_consolidado = pd.concat([df_consolidado, df_municipio], ignore_index=True)
                        
                        # Adicionar dados do município
                        df_consolidado = pd.concat([df_consolidado, df], ignore_index=True)
                        
                        # Adicionar linha vazia para separação
                        df_consolidado = pd.concat([df_consolidado, pd.DataFrame([[""]*len(df.columns)], columns=df.columns)], ignore_index=True)
                    
                    # Remover a última linha vazia se existir
                    if df_consolidado.iloc[-1].isnull().all():
                        df_consolidado = df_consolidado.iloc[:-1]
                    
                    # Escrever no Excel (limitando nome da planilha a 31 caracteres)
                    sheet_name = nome_tabela[:31]
                    df_consolidado.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {e}")
        return None

# 6. Processamento principal
def process_data(geometry, crs, nome_bacia_export="bacia"):
    try:
        data_atual = datetime.datetime.now()
        mes_formatado = data_atual.strftime("%b")  # Ex: "Jan"
        ano_atual = data_atual.year
        ano_anterior = ano_atual - 1
        
        # Inicializar dicionário de resultados
        resultados = {
            "nome_bacia_export": nome_bacia_export,
            "mes_formatado": mes_formatado,
            "ano_atual": ano_atual,
            "ano_anterior": ano_anterior,
        }
        
        # Se selecionado, processar dados agro
        if st.session_state.get("exportar_dados_agro"):
            st.info("Processando dados agro e socioeconômicos...")
            
            # Processar municípios na bacia
            municipios_df = processar_municipios(geometry, nome_bacia_export)
            
            if municipios_df is not None:
                geocodigos = municipios_df['geocodigo'].tolist()
                
                # Processar todas as tabelas agro
                dados_agro = processar_tabelas_agro(geocodigos)
                
                # Gerar Excel consolidado
                if dados_agro:
                    excel_agro = gerar_excel_agro(dados_agro, nome_bacia_export)
                    
                    if excel_agro:
                        st.download_button(
                            label="📥 Baixar Dados Agro e Socioeconômicos",
                            data=excel_agro,
                            file_name=f"{nome_bacia_export}_dados_agro.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            
            # Se também estiver processando imagens, retornar os resultados
            if any(st.session_state.get(key) for key in [
                "exportar_srtm_mde", "exportar_declividade", "exportar_ndvi", 
                "exportar_gndvi", "exportar_ndwi", "exportar_ndmi",
                "exportar_mapbiomas", "exportar_pasture_quality", "exportar_sentinel_composite",
                "exportar_puc_ufv", "exportar_puc_ibge", "exportar_puc_embrapa",
                "exportar_landforms"
            ]):
                return resultados
        
        # Se não for apenas agro, processar imagens
        # Calcular o bounding box da geometria
        bbox = geometry.bounds()
        # Aplicar um buffer de 1 km ao bounding box
        bacia = bbox.buffer(1000)  # 1000 metros = 1 km
        periodo_fim = ee.Date(data_atual.strftime("%Y-%m-%d"))
        periodo_inicio = periodo_fim.advance(-365, 'day')

        # Carregar imagens Sentinel-2 se selecionado
        if st.session_state.get("exportar_sentinel_composite"):
            sentinel = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']) \
                .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10) \
                .filterBounds(bacia) \
                .filterDate(periodo_inicio, periodo_fim)

            # Verificar se há imagens para o período definido
            num_imagens = sentinel.size().getInfo()
            if num_imagens == 0:
                st.error("Nenhuma imagem foi encontrada para o período especificado.")
                return None
            else:
                st.success(f"Imagens encontradas: {num_imagens}")

                # Exportar a lista de imagens Sentinel-2 para um arquivo CSV (se selecionado)
                try:
                    # Criar uma FeatureCollection com as informações das imagens
                    sentinel_list = sentinel.toList(sentinel.size())
                    features = ee.FeatureCollection(sentinel_list.map(lambda img: ee.Feature(None, {
                        'id': ee.Image(img).id(),
                        'date': ee.Image(img).date().format('YYYY-MM-dd'),
                        'cloud_cover': ee.Image(img).get('CLOUDY_PIXEL_PERCENTAGE')
                    })))

                    # Exportar a lista de imagens para um arquivo CSV
                    export_task = ee.batch.Export.table.toDrive(
                        collection=features,
                        folder='zap',
                        description='lista_imagens_sentinel-2',
                        fileFormat='CSV'
                    )
                    export_task.start()
                    st.success("Exportação da lista de imagens Sentinel-2 iniciada. Verifique seu Google Drive na pasta 'export_zap'.")
                except Exception as e:
                    st.error(f"Erro ao exportar a lista de imagens Sentinel-2: {e}")

            # Gerar a mediana das imagens Sentinel-2
            sentinel_median = sentinel.median().clip(bacia)
            sentinel_composite = sentinel_median.select(['B2', 'B3', 'B4', 'B8']).rename(['B2', 'B3', 'B4', 'B8'])

        # Gerar índices se selecionados
        indices = {}
        if st.session_state.get("exportar_ndvi"):
            indices["NDVI"] = sentinel_median.normalizedDifference(['B8', 'B4'])
        if st.session_state.get("exportar_gndvi"):
            indices["GNDVI"] = sentinel_median.normalizedDifference(['B8', 'B3'])
        if st.session_state.get("exportar_ndwi"):
            indices["NDWI"] = sentinel_median.normalizedDifference(['B3', 'B8'])
        if st.session_state.get("exportar_ndmi"):
            indices["NDMI"] = sentinel_median.normalizedDifference(['B8', 'B11'])

        # Carregar MDE e Declividade se selecionados
        if st.session_state.get("exportar_srtm_mde") or st.session_state.get("exportar_declividade"):
            mde_proj = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2").filterBounds(bacia).first().select(0).projection()
            mde = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2").filterBounds(bacia).mosaic().clip(bacia).setDefaultProjection(mde_proj)
            elevation = mde.select('DSM')

            if st.session_state.get("exportar_declividade"):
                # Calcular a declividade em porcentagem
                declividade_graus = ee.Terrain.slope(elevation)
                declividade = declividade_graus.divide(180).multiply(3.14159).tan().multiply(100)
                declividade_reclass = declividade.expression(
                    "b(0) == 0 ? 1 : " +  # Inclui declividade = 0 no valor 1
                    "b(0) <= 3 ? 1 : " + 
                    "(b(0) > 3 && b(0) <= 8) ? 2 : " + 
                    "(b(0) > 8 && b(0) <= 20) ? 3 : " + 
                    "(b(0) > 20 && b(0) <= 45) ? 4 : " + 
                    "(b(0) > 45 && b(0) <= 75) ? 5 : " + 
                    "(b(0) > 75) ? 6 : -1"
                )

        # Carregar MapBiomas 2023 se selecionado
        if st.session_state.get("exportar_mapbiomas"):
            mapbiomas = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1") \
                .select('classification_2023') \
                .clip(bacia)

        # Carregar Qualidade de Pastagens se selecionado
        if st.session_state.get("exportar_pasture_quality"):
            pasture_quality = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_pasture_quality_v1") \
                .select('pasture_quality_2023') \
                .clip(bacia)

        # Carregar PUC (UFV, IBGE, Embrapa) se selecionados
        if st.session_state.get("exportar_puc_ufv"):
            puc_ufv = ee.ImageCollection('users/zap/puc_ufv').filterBounds(bacia).mosaic().clip(bacia)
        if st.session_state.get("exportar_puc_ibge"):
            puc_ibge = ee.ImageCollection('users/zap/puc_ibge').filterBounds(bacia).mosaic().clip(bacia)
        if st.session_state.get("exportar_puc_embrapa"):
            puc_embrapa = ee.ImageCollection('users/zap/puc_embrapa').filterBounds(bacia).mosaic().clip(bacia)

        # Carregar Landforms se selecionado
        if st.session_state.get("exportar_landforms"):
            landforms = ee.Image('CSP/ERGo/1_0/Global/SRTM_landforms').clip(bacia)

        # Determinar o EPSG com base no fuso
        fusos_mg = ee.FeatureCollection('users/zap/fusos_mg')
        fuso_maior_area = fusos_mg.filterBounds(bacia).map(lambda f: f.set('area', f.area())).sort('area', False).first()
        epsg = fuso_maior_area.get('epsg').getInfo()

        # Reprojetar todas as imagens selecionadas
        if st.session_state.get("exportar_srtm_mde"):
            resultados["utm_elevation"] = reprojetarImagem(elevation, epsg, 30)
        if st.session_state.get("exportar_declividade"):
            resultados["utm_declividade"] = reprojetarImagem(declividade_reclass, epsg, 30).float()
        if st.session_state.get("exportar_ndvi"):
            resultados["utm_ndvi"] = reprojetarImagem(indices["NDVI"], epsg, 10)
        if st.session_state.get("exportar_gndvi"):
            resultados["utm_gndvi"] = reprojetarImagem(indices["GNDVI"], epsg, 10)
        if st.session_state.get("exportar_ndwi"):
            resultados["utm_ndwi"] = reprojetarImagem(indices["NDWI"], epsg, 10)
        if st.session_state.get("exportar_ndmi"):
            resultados["utm_ndmi"] = reprojetarImagem(indices["NDMI"], epsg, 10)
        if st.session_state.get("exportar_sentinel_composite"):
            resultados["utm_sentinel2"] = reprojetarImagem(sentinel_composite, epsg, 10).float()
        if st.session_state.get("exportar_mapbiomas"):
            resultados["utm_mapbiomas"] = reprojetarImagem(mapbiomas, epsg, 30)
        if st.session_state.get("exportar_pasture_quality"):
            resultados["utm_pasture_quality"] = reprojetarImagem(pasture_quality, epsg, 30).float()
        if st.session_state.get("exportar_landforms"):
            resultados["utm_landforms"] = reprojetarImagem(landforms, epsg, 30)
        if st.session_state.get("exportar_puc_ufv"):
            resultados["utm_puc_ufv"] = reprojetarImagem(puc_ufv, epsg, 30).float()
        if st.session_state.get("exportar_puc_ibge"):
            resultados["utm_puc_ibge"] = reprojetarImagem(puc_ibge, epsg, 30).float()
        if st.session_state.get("exportar_puc_embrapa"):
            resultados["utm_puc_embrapa"] = reprojetarImagem(puc_embrapa, epsg, 30).float()
        
        return resultados
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# 7. Interface do usuário
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
                    # Título da seção de Sensoriamento Remoto
                    st.subheader("📡 Produtos de Sensoriamento Remoto (Imagens/Raster)")
                    st.caption(f"Sistema de referência espacial: {crs}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Índices Espectrais**")
                        exportar_ndvi = st.checkbox("NDVI (10m)", value=False)
                        exportar_gndvi = st.checkbox("GNDVI (10m)", value=False)
                        exportar_ndwi = st.checkbox("NDWI (10m)", value=False)
                        exportar_ndmi = st.checkbox("NDMI (10m)", value=False)
                        
                        st.markdown("**Modelo Digital de Elevação**")
                        exportar_srtm_mde = st.checkbox("SRTM MDE (30m)", value=False)
                        exportar_declividade = st.checkbox("Declividade (30m)", value=False)

                    with col2:
                        st.markdown("**Cobertura e Uso da Terra**")
                        exportar_mapbiomas = st.checkbox("MapBiomas 2023 (30m)", value=False)
                        exportar_pasture_quality = st.checkbox("Qualidade de Pastagem 2023 (30m)", value=False)
                        exportar_sentinel_composite = st.checkbox("Sentinel-2 B2/B3/B4/B8 (10m)", value=False)
                        
                        st.markdown("**Potencial de Uso**")
                        exportar_puc_ufv = st.checkbox("PUC UFV (30m)", value=False)
                        exportar_puc_ibge = st.checkbox("PUC IBGE (30m)", value=False)
                        exportar_puc_embrapa = st.checkbox("PUC Embrapa (30m)", value=False)
                        
                        st.markdown("**Geomorfologia**")
                        exportar_landforms = st.checkbox("Landforms (30m)", value=False)
                    
                    # Divisão visual
                    st.markdown("---")
                    
                    # Título da seção de Dados Socioeconômicos
                    st.subheader("📊 Dados Agro e Socioeconômicos")
                    st.caption("Municípios com representatividade >20% na bacia hidrográfica")
                    exportar_dados_agro = st.checkbox("Ativar processamento de dados do IBGE", value=False)
                    
                    # Divisão visual
                    st.markdown("---")                    
                    submit_button = st.form_submit_button(label='✅ Confirmar Seleção')

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
                                
                                # Exportar imagens se selecionadas
                                tasks_selecionadas = []
                                if st.session_state.get("exportar_srtm_mde") and "utm_elevation" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_elevation"], "06_", "_SRTM_MDE", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_declividade") and "utm_declividade" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_declividade"], "07_", "_Declividade", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_ndvi") and "utm_ndvi" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndvi"], "01_", "_NDVI", 10, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_gndvi") and "utm_gndvi" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_gndvi"], "02_", "_GNDVI", 10, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_ndwi") and "utm_ndwi" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndwi"], "03_", "_NDWI", 10, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_ndmi") and "utm_ndmi" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_ndmi"], "04_", "_NDMI", 10, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_sentinel_composite") and "utm_sentinel2" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_sentinel2"], "05_", "_Sentinel2", 10, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_mapbiomas") and "utm_mapbiomas" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_mapbiomas"], "08_", "_MapBiomas", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_pasture_quality") and "utm_pasture_quality" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_pasture_quality"], "09_", "_PastureQuality", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_landforms") and "utm_landforms" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_landforms"], "10_", "_Landforms", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_puc_ufv") and "utm_puc_ufv" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_ufv"], "11_", "_PUC_UFV", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_puc_ibge") and "utm_puc_ibge" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_ibge"], "12_", "_PUC_IBGE", 30, geometry, nome_bacia_export))
                                if st.session_state.get("exportar_puc_embrapa") and "utm_puc_embrapa" in resultados:
                                    tasks_selecionadas.append(exportarImagem(resultados["utm_puc_embrapa"], "13_", "_PUC_Embrapa", 30, geometry, nome_bacia_export))
                                
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