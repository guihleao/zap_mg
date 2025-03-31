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
from openpyxl.styles import Alignment
import gdown
import webbrowser

# Configuração de layout
st.set_page_config(
    page_title="ZAP - Automatização",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': 'https://www.mg.gov.br/agricultura/pagina/zoneamento-ambiental-e-produtivo',
        'Report a Bug': "mailto:zap@agricultura.mg.gov.br"
    }
)

#Logo Sidebar e Sidebar
sidebar_logo = "https://i.postimg.cc/c4VZ0fQw/zap-logo.png"
main_body_logo = "https://i.postimg.cc/65qGpMc8/zap-logo-sb.png"
st.logo(sidebar_logo, size="large", icon_image=main_body_logo)
# Sidebar com links como markdown
with st.sidebar:
    st.markdown("## Navegação")
    
    # Links como markdown formatados como botões
    st.markdown("""
    <style>
        .sidebar-link {
            display: block;
            padding: 0.5rem 1rem;
            margin: 0.25rem 0;
            background-color: #f0f2f6;
            border-radius: 0.5rem;
            color: #333 !important;
            text-decoration: none !important;
            transition: all 0.3s;
            border: 1px solid #ddd;
        }
        .sidebar-link:hover {
            background-color: #e6e6e6;
            transform: translateX(3px);
        }
    </style>
    """, unsafe_allow_html=True)

    # Link 1 - Sobre o ZAP
    st.markdown('<a href="https://www.mg.gov.br/agricultura/pagina/zoneamento-ambiental-e-produtivo" class="sidebar-link" target="_blank">📘 Sobre o ZAP</a>', unsafe_allow_html=True)
    
    # Link 2 - Reportar Bug
    st.markdown('<a href="mailto:zap@agricultura.mg.gov.br" class="sidebar-link">🐞 Reportar um Bug</a>', unsafe_allow_html=True)
    
    # Link 3 - Política de Privacidade
    st.markdown('<a href="https://github.com/guihleao/zap_mg/tree/main?tab=security-ov-file" class="sidebar-link" target="_blank">🔒 Política de Privacidade</a>', unsafe_allow_html=True)
    
    # Link 4 - Termo de Serviço
    st.markdown('<a href="https://github.com/guihleao/zap_mg/tree/main?tab=security-ov-file" class="sidebar-link" target="_blank">⚖️ Aspectos Legais</a>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Versão 1.0")
    st.caption("Desenvolvido para a 5ª edição do ZAP")
    st.caption("Secretaria de Agricultura, Pecuária e Abastecimento de Minas Gerais")
    
# Logo e título centralizado
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("https://i.postimg.cc/c4VZ0fQw/zap-logo.png", width=400)

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# CSS customizado para os cards
st.markdown("""
<style>
    .custom-card {
        background-color: #242434;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #2e7d32;
    }
    .custom-card h3 {
        color: #2e7d32;
        margin-top: 0;
    }
    .custom-card ul {
        padding-left: 1.2rem;
    }
    .custom-card a {
        color: #1a5a96 !important;
        font-weight: 500;
    }
        .stFileUploader > label > div:first-child {
        font-weight: bold;
        color: #ff4b4b;
    }
    .stFileUploader > label > div:nth-child(2) {
        font-size: 0.8em;
        color: #777;
    }
</style>
""", unsafe_allow_html=True)

# Card 1 - Sobre o ZAP
st.markdown("""
<div class="custom-card">
<h3>🌱 Sobre o ZAP</h3>
O Zoneamento Ambiental e Produtivo (ZAP) é um instrumento de planejamento e gestão territorial para o uso sustentável dos recursos naturais pela atividade agrossilvipastoril no estado de Minas Gerais, instituído pelo Decreto Estadual nº 46.650/2014.

<h3>🗺️ Produtos Básicos</h3>
<ul>
<li>Mapeamento da cobertura e terra</li>
<li>Índice de Demanda Hídrica Superficial (IDHS)</li>
<li>Potencial de Uso Conservacionista (PUC)</li>
</ul>

O ZAP busca disponibilizar informações detalhadas sobre o meio natural e produtivo por sub-bacia hidrográfica.

<h3>🔄 Evolução da Metodologia</h3>
Desenvolvida inicialmente pela Semad e Seapa em 2014, a metodologia do ZAP está atualmente na 5ª edição (2025). O Comitê Gestor do ZAP é a instância consultiva e deliberativa da ferramenta.

<h3>🤝 Integração com Outros Instrumentos</h3>
<ul>
<li>Indicadores de Sustentabilidade em Agroecossistemas (ISAs)</li>
<li>Planos de Adequação Socioeconômica e Ambiental (PASEAs)</li>
<li>Cadastro Ambiental Rural (CAR)</li>
<li>Entre outros</li>
</ul>

🔗 <a href="https://www.mg.gov.br/agricultura/pagina/zoneamento-ambiental-e-produtivo" target="_blank">Mais informações no Site do Governo de MG</a>
</div>
""", unsafe_allow_html=True)

# Card 2 - Sobre a Ferramenta
st.markdown("""
<div class="custom-card">
<h3>🛠️ Sobre esta Ferramenta</h3>
Esta ferramenta automatiza a obtenção de produtos e bases para os produtos utilizados no ZAP para a 5ª edição da metodologia.

<h3>🔑 Requisitos</h3>
<ul>
<li>Conexão com conta Google (para Earth Engine, Cloud Service e Drive)</li>
<li>Arquivo GeoJSON da bacia hidrográfica (preferencialmente em UTM)</li>
</ul>
</div>
""", unsafe_allow_html=True)

# Divisão visual
st.markdown("---")

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
    'cenoura': 'Cenoura', 'morango': 'Morango', 'madtor': 'Madeira em tora', 'outprod': 'Outros produtos'
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
        # Verificação de tamanho (1 MB)
        MAX_FILE_SIZE_KB = 1024
        if file.size > MAX_FILE_SIZE_KB * 1024:
            st.error(f"Tamanho do arquivo ({file.size/1024:.1f} KB) excede o limite de {MAX_FILE_SIZE_KB} KB")
            return None, None

        gdf = gpd.read_file(file)
        
        # Verifica número de features
        if len(gdf) > 1:
            st.error("Erro: O arquivo deve conter APENAS UMA feature (polígono/multipolígono).")
            return None, None
            
        # Validações de geometria
        if gdf.geometry.is_empty.any():
            st.error("Erro: O arquivo contém geometrias vazias.")
            return None, None
            
        if not all(gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])):
            st.error("Erro: Apenas polígonos ou multipolígonos são aceitos.")
            return None, None

        # Verificação do CRS (APENAS SIRGAS 2000)
        CRS_OBRIGATORIO = 'EPSG:4674'
        if gdf.crs is None:
            st.error(f"Erro: O arquivo não possui CRS definido. O CRS deve ser {CRS_OBRIGATORIO} (SIRGAS 2000).")
            return None, None
            
        if str(gdf.crs).upper() != CRS_OBRIGATORIO:
            st.error(f"Erro: CRS {gdf.crs} não permitido. O arquivo deve estar em {CRS_OBRIGATORIO} (SIRGAS 2000).")
            return None, None

        # Correção de geometrias (buffer 0 se necessário)
        if not gdf.geometry.is_valid.all():
            gdf['geometry'] = gdf.geometry.buffer(0)
        
        # Visualização DIRETAMENTE no SIRGAS 2000 (Folium aceita coordenadas equivalentes)
        centroid = gdf.geometry.centroid
        m = folium.Map(
            location=[centroid.y.mean(), centroid.x.mean()],  # Coordenadas serão interpretadas como WGS84
            zoom_start=10,
            tiles='CartoDB positron'
        )
        
        folium.GeoJson(
            gdf.geometry.iloc[0],
            style_function=lambda x: {'fillColor': '#4daf4a', 'color': '#377eb8'}
        ).add_to(m)
            
        st_folium(m, width=600, height=400)
        st.success(f"CRS do arquivo validado: {gdf.crs} (SIRGAS 2000)")
        
        # Retorna geometria no SIRGAS 2000
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__), CRS_OBRIGATORIO
        
    except Exception as e:
        st.error(f"Erro crítico ao carregar GeoJSON: {str(e)}")
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
        workbook = Workbook()
        workbook.remove(workbook.active)  # Remove a planilha padrão vazia
        
        # Escrever cada planilha
        for nome_tabela, dados in dados_agro.items():
            # Tabela IBGE tem tratamento especial
            if nome_tabela == 'IBGE_Municipios_ZAP':
                ws = workbook.create_sheet(title='IBGE_Municipios')
                for r in dataframe_to_rows(dados, index=True, header=True):
                    ws.append(r)
                continue
            
            # Para outras tabelas, criar uma planilha consolidada
            if isinstance(dados, dict):
                # Criar nova planilha (limitando nome a 31 caracteres)
                sheet_name = nome_tabela[:31]
                ws = workbook.create_sheet(title=sheet_name)
                
                # Adicionar cabeçalho inicial
                current_row = 1
                
                for municipio, df in dados.items():
                    # Adicionar cabeçalho completo antes de cada município
                    if not df.empty:
                        # Cabeçalho das colunas (com anos corretos)
                        header = ['Produto'] + [str(col)[-4:] if str(col).startswith('20') else col for col in df.columns[1:]]
                        ws.append(header)
                        
                        # Formatar cabeçalho em negrito
                        for col in range(1, len(header)+1):
                            cell = ws.cell(row=current_row, column=col)
                            cell.font = cell.font.copy(bold=True)
                        
                        current_row += 1
                        
                        # Nome do município (mesclado, em negrito e centralizado)
                        ws.append([municipio] + ['']*(len(df.columns)-1))
                        ws.merge_cells(start_row=current_row, start_column=1, 
                                      end_row=current_row, end_column=len(df.columns))
                        cell = ws.cell(row=current_row, column=1)
                        cell.font = cell.font.copy(bold=True)
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                        current_row += 1
                        
                        # Dados do município
                        for _, row in df.iterrows():
                            ws.append(row.tolist())
                            current_row += 1
                        
                        # Linha vazia de separação
                        ws.append(['']*len(df.columns))
                        current_row += 1
        
        # Salvar o workbook no buffer
        workbook.save(output)
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {e}")
        return None

# 6. Processamento principal
def process_data(geometry, crs, nome_bacia_export="bacia", process_type="all"):
    try:
        # Verificar se o Earth Engine está inicializado com o projeto correto
        if "selected_project" not in st.session_state or "ee_credentials" not in st.session_state:
            st.error("Earth Engine não foi inicializado corretamente. Por favor, reconecte-se.")
            return None
            
        # Garantir que o Earth Engine está inicializado com o projeto selecionado
        try:
            ee.Initialize(st.session_state["ee_credentials"], project=st.session_state["selected_project"])
        except Exception as e:
            st.error(f"Erro ao reinicializar Earth Engine: {e}")
            return None
        
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
        
        # Processar apenas dados agro se especificado
        if process_type == "agro":
            st.info("Processando dados agro e socioeconômicos...")
            municipios_df = processar_municipios(geometry, nome_bacia_export)
            
            if municipios_df is not None:
                geocodigos = municipios_df['geocodigo'].tolist()
                dados_agro = processar_tabelas_agro(geocodigos)
                return dados_agro
            
            return None
        
        # Processar apenas sensoriamento remoto
        elif process_type == "remoto":
            # Calcular o bounding box da geometria
            bbox = geometry.bounds()
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

                num_imagens = sentinel.size().getInfo()
                if num_imagens == 0:
                    st.error("Nenhuma imagem Sentinel-2 encontrada para o período especificado.")
                else:
                    st.success(f"Imagens Sentinel-2 encontradas: {num_imagens}")
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
        
        return None
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# 7. Interface do usuário (modificar apenas a parte do processamento)
if 'token' not in st.session_state:
    st.write("Para começar, conecte-se à sua conta Google:")
    result = oauth2.authorize_button(
        "🔵 Conectar com Google",
        REDIRECT_URI, 
        SCOPE,
        icon="https://www.google.com/favicon.ico"
    )
    if result and 'token' in result:
        st.session_state.token = result.get('token')
        st.rerun()
else:
    token = st.session_state['token']
    st.success("Você está conectado à sua conta Google!")

    # Verificar se já temos credenciais e projeto inicializados
    if "ee_credentials" not in st.session_state or "selected_project" not in st.session_state:
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
                # Armazenar as credenciais e projetos na sessão
                st.session_state["ee_credentials"] = credentials
                st.session_state["available_projects"] = project_ids
                
                # Verificar se já temos um projeto selecionado
                if "selected_project" not in st.session_state:
                    # Tentar encontrar um projeto com Earth Engine ativado
                    selected_project = None
                    for project in project_ids:
                        try:
                            ee.Initialize(credentials, project=project)
                            selected_project = project
                            break
                        except:
                            continue
                    
                    if selected_project:
                        st.session_state["selected_project"] = selected_project
                        st.session_state["ee_initialized"] = True
                        st.success(f"Earth Engine inicializado com sucesso no projeto: {selected_project}")
                    else:
                        # Se nenhum projeto tiver EE ativado, pedir para selecionar
                        selected_project = st.selectbox(
                            "Selecione um projeto com Earth Engine ativado:", 
                            project_ids,
                            key="project_selection"
                        )
                        if st.button("Confirmar Projeto"):
                            try:
                                ee.Initialize(credentials, project=selected_project)
                                st.session_state["selected_project"] = selected_project
                                st.session_state["ee_initialized"] = True
                                st.success(f"Earth Engine inicializado com sucesso no projeto: {selected_project}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao inicializar Earth Engine: {e}. Verifique se a API está ativada para este projeto.")
                                st.stop()
                else:
                    # Já temos um projeto selecionado, inicializar
                    try:
                        ee.Initialize(credentials, project=st.session_state["selected_project"])
                        st.session_state["ee_initialized"] = True
                        st.success(f"Earth Engine inicializado com sucesso no projeto: {st.session_state['selected_project']}")
                    except Exception as e:
                        st.error(f"Erro ao inicializar Earth Engine: {e}")
                        st.stop()
        except Exception as e:
            st.error(f"Erro ao inicializar o Earth Engine: {e}")
            st.stop()

    if st.session_state.get("ee_initialized"):
        uploaded_file = st.file_uploader(
            "Carregue o arquivo GeoJSON da bacia (apenas 1 polígono/multipolígono, SIRGAS 2000 (4674), máximo 1 MB)",
            type=["geojson"],
            accept_multiple_files=False,
            help="Seu arquivo tem de estar projetado em SIRGAS 2000 (4674). Use ferramentas como QGIS ou geojson.io para garantir que seu arquivo tem apenas UMA geometria"
        )
        if uploaded_file is not None:
            geometry, crs = load_geojson(uploaded_file)
            if geometry:
                nome_bacia_export = st.text_input(
                    "Digite o nome para exportação (sem espaços ou caracteres especiais). "
                    "Esse nome deve seguir o padrão utilizado para todos os produtos SIG do ZAP "
                    "(Ex.: Para o Ribeirão Santa Juliana foi utilizado o nome Rib_Santa_Juliana):",
                    placeholder="Ex: Rib_Santa_Juliana",
                    help="⚠️ Este campo é obrigatório e deve seguir o padrão de nomenclatura do ZAP"
                )
                
                if nome_bacia_export:
                    col1, col2 = st.columns([4,1])
                    with col2:
                        if st.button("✅ Marcar Todos"):
                            st.session_state.select_all = not st.session_state.get('select_all', False)
                            st.session_state.select_ibge = st.session_state.select_all
                            st.rerun()
                    
                    with st.form(key='product_selection_form'):
                        st.subheader("📡 Produtos de Sensoriamento Remoto (Imagens/Raster)")
                        st.caption(f"Sistema de referência espacial: {crs}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Índices Espectrais**")
                            exportar_ndvi = st.checkbox("NDVI (10m)", value=st.session_state.get('select_all', False))
                            exportar_gndvi = st.checkbox("GNDVI (10m)", value=st.session_state.get('select_all', False))
                            exportar_ndwi = st.checkbox("NDWI (10m)", value=st.session_state.get('select_all', False))
                            exportar_ndmi = st.checkbox("NDMI (10m)", value=st.session_state.get('select_all', False))
                            
                            st.markdown("**Modelo Digital de Elevação**")
                            exportar_srtm_mde = st.checkbox("SRTM MDE (30m)", value=st.session_state.get('select_all', False))
                            exportar_declividade = st.checkbox("Declividade (30m)", value=st.session_state.get('select_all', False))

                        with col2:
                            st.markdown("**Cobertura e Uso da Terra**")
                            exportar_mapbiomas = st.checkbox("MapBiomas 2023 (30m)", value=st.session_state.get('select_all', False))
                            exportar_pasture_quality = st.checkbox("Qualidade de Pastagem 2023 (30m)", value=st.session_state.get('select_all', False))
                            exportar_sentinel_composite = st.checkbox("Sentinel-2 B2/B3/B4/B8 (10m)", value=st.session_state.get('select_all', False))
                            
                            st.markdown("**Potencial de Uso**")
                            exportar_puc_ufv = st.checkbox("PUC UFV (30m)", value=st.session_state.get('select_all', False))
                            exportar_puc_ibge = st.checkbox("PUC IBGE (30m)", value=st.session_state.get('select_all', False))
                            exportar_puc_embrapa = st.checkbox("PUC Embrapa (30m)", value=st.session_state.get('select_all', False))
                            
                            st.markdown("**Geomorfologia**")
                            exportar_landforms = st.checkbox("Landforms (30m)", value=st.session_state.get('select_all', False))
                        
                        st.markdown("---")
                        
                        st.subheader("📊 Dados Agro e Socioeconômicos")
                        st.caption("Municípios com representatividade >20% na bacia hidrográfica")
                        exportar_dados_agro = st.checkbox("Ativar processamento de dados do IBGE", value=st.session_state.get('select_ibge', False))
                        
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
                                # Verificar se deve processar sensoriamento remoto
                                process_remoto = any([
                                    st.session_state.get("exportar_srtm_mde"),
                                    st.session_state.get("exportar_declividade"), 
                                    st.session_state.get("exportar_ndvi"),
                                    st.session_state.get("exportar_gndvi"),
                                    st.session_state.get("exportar_ndwi"),
                                    st.session_state.get("exportar_ndmi"),
                                    st.session_state.get("exportar_sentinel_composite"),
                                    st.session_state.get("exportar_mapbiomas"),
                                    st.session_state.get("exportar_pasture_quality"),
                                    st.session_state.get("exportar_landforms"),
                                    st.session_state.get("exportar_puc_ufv"),
                                    st.session_state.get("exportar_puc_ibge"),
                                    st.session_state.get("exportar_puc_embrapa")
                                ])
                                
                                # Verificar se deve processar dados agro
                                process_agro = st.session_state.get("exportar_dados_agro")
                                
                                # Processar apenas agro se for o único selecionado
                                if not process_remoto and process_agro:
                                    dados_agro = process_data(geometry, crs, nome_bacia_export, "agro")
                                    if dados_agro:
                                        excel_agro = gerar_excel_agro(dados_agro, nome_bacia_export)
                                        if excel_agro:
                                            st.download_button(
                                                label="📥 Baixar Dados Agro e Socioeconômicos",
                                                data=excel_agro,
                                                file_name=f"{nome_bacia_export}_dados_agro.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key=f"download_agro_{int(time.time())}"
                                            )
                                
                                # Processar sensoriamento remoto (e agro depois, se selecionado)
                                elif process_remoto:
                                    resultados = process_data(geometry, crs, nome_bacia_export, "remoto")
                                    
                                    if resultados:
                                        st.session_state["resultados"] = resultados
                                        st.success("Dados de sensoriamento processados com sucesso!")
                                        
                                        # Exportar produtos de sensoriamento remoto
                                        tasks_remoto = []
                                        if st.session_state.get("exportar_srtm_mde") and "utm_elevation" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_elevation"], "06_", "_SRTM_MDE", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_declividade") and "utm_declividade" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_declividade"], "02_", "_Declividade", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_ndvi") and "utm_ndvi" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_ndvi"], "06_", f"_NDVImediana_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_gndvi") and "utm_gndvi" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_gndvi"], "06_", f"_GNDVI_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_ndwi") and "utm_ndwi" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_ndwi"], "06_", f"_NDWI_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_ndmi") and "utm_ndmi" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_ndmi"], "06_", f"_NDMI_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_sentinel_composite") and "utm_sentinel2" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_sentinel2"], "06_", f"_S2_B2B3B4B8_{resultados['mes_formatado']}{resultados['ano_anterior']}-{resultados['ano_atual']}", 10, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_mapbiomas") and "utm_mapbiomas" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_mapbiomas"], "06_", "_MapBiomas_col9_2023", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_pasture_quality") and "utm_pasture_quality" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_pasture_quality"], "06_", "_Vigor_Pastagem_col9_2023", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_landforms") and "utm_landforms" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_landforms"], "06_", "_Landforms", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_puc_ufv") and "utm_puc_ufv" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_puc_ufv"], "02_", "_PUC_UFV", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_puc_ibge") and "utm_puc_ibge" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_puc_ibge"], "02_", "_PUC_IBGE", 30, geometry, nome_bacia_export))
                                        if st.session_state.get("exportar_puc_embrapa") and "utm_puc_embrapa" in resultados:
                                            tasks_remoto.append(exportarImagem(resultados["utm_puc_embrapa"], "02_", "_PUC_Embrapa", 30, geometry, nome_bacia_export))
                                        
                                        # Verifica conclusão das tarefas de sensoriamento
                                        if tasks_remoto:
                                            status_container = st.empty()  # Container fixo para as mensagens
                                            
                                            with status_container:
                                                st.write("⏳ Processando produtos de sensoriamento remoto na Earth Engine...")
                                                
                                                progress_bar = st.progress(0)
                                                status_text = st.empty()
                                            
                                            todas_concluidas = False
                                            last_update = time.time()
                                            
                                            while not todas_concluidas:
                                                todas_concluidas = True
                                                completed_tasks = 0
                                                
                                                # Atualiza status dentro do mesmo container
                                                with status_container:
                                                    progress_bar.empty()
                                                    status_text.empty()
                                                    
                                                    for i, task in enumerate(tasks_remoto):
                                                        state = check_task_status(task)
                                                        status_text.write(f"Tarefa {i+1}/{len(tasks_remoto)}: {state}")
                                                        
                                                        if state != "COMPLETED":
                                                            todas_concluidas = False
                                                        else:
                                                            completed_tasks += 1
                                                    
                                                    # Barra de progresso
                                                    progress = completed_tasks / len(tasks_remoto)
                                                    progress_bar.progress(progress)
                                                    
                                                    if todas_concluidas:
                                                        st.success("✅ Todos os produtos de sensoriamento foram processados!")
                                                        break
                                                    else:
                                                        st.warning(f"⌛ Progresso: {completed_tasks}/{len(tasks_remoto)} tarefas concluídas")
                                                
                                                # Espera 60 segundos entre verificações
                                                time.sleep(60)
                                        
                                        # Processar dados agro APÓS o sensoriamento, se selecionado
                                        if process_agro:
                                            st.write("Iniciando processamento de dados agro/socioeconômicos...")
                                            municipios_df = processar_municipios(geometry, nome_bacia_export)
                                            
                                            if municipios_df is not None:
                                                dados_agro = processar_tabelas_agro([int(x) for x in municipios_df['geocodigo'].tolist()])
                                                
                                                if dados_agro:
                                                    excel_agro = gerar_excel_agro(dados_agro, nome_bacia_export)
                                                    if excel_agro:
                                                        st.download_button(
                                                            label="📥 Baixar Dados Agro e Socioeconômicos",
                                                            data=excel_agro,
                                                            file_name=f"{nome_bacia_export}_dados_agro.xlsx",
                                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                            key=f"download_agro_{int(time.time())}"
                                                        )
                                
                                st.success("Todos os processamentos foram concluídos com sucesso!")
                else:
                    st.warning("Por favor, preencha o nome para exportação antes de selecionar os produtos.")