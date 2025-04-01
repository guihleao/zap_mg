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
from googleapiclient.http import MediaIoBaseUpload

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

# ===============================================
# FUNÇÕES AUXILIARES E COMPONENTES REUTILIZÁVEIS
# ===============================================

def local_css():
    """Carrega estilos CSS personalizados"""
    st.markdown("""
    <style>
        /* Estilos gerais */      
        /* Cards personalizados */
        .custom-card {
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #2e7d32;
        }
        .custom-card h3 {
            color: #2e7d32;
            margin-top: 0;
            font-size: 1.2rem;
        }
        
        /* Sidebar */
        .sidebar-link {
            display: block;
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            color: #333 !important;
            text-decoration: none !important;
            transition: all 0.3s;
            border: 1px solid #ddd;
            font-size: 0.9rem;
        }
        .sidebar-link:hover {
            transform: translateX(5px);
        }
        
        /* Botões */
        .stButton button {
            transition: all 0.3s !important;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
        }
        .primary-button {
            color: white !important;
            border: none !important;
        }
        .secondary-button {
            color: #333 !important;
            border: 1px solid #ddd !important;
        }
        
        /* Uploader de arquivos */
        .stFileUploader > label > div:first-child {
            font-weight: bold;
            color: #2e7d32;
        }
        .stFileUploader > label > div:nth-child(2) {
            font-size: 0.8em;
            color: #666;
        }
        
        /* Tabelas */
        .stDataFrame {
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Adaptações para mobile */
        @media (max-width: 768px) {
            .card-buttons-container {
                flex-direction: column;
                gap: 0.5rem;
            }
            .custom-card {
                padding: 1rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

def mostrar_card(titulo, conteudo, icone="ℹ️"):
    """Componente padronizado para cards"""
    with st.container():
        st.markdown(f"""
        <div class="custom-card">
            <h3>{icone} {titulo}</h3>
            {conteudo}
        </div>
        """, unsafe_allow_html=True)

def create_map(geometry, nome_bacia="Bacia"):
    """Cria um mapa Folium com a geometria da bacia"""
    centroid = geometry.centroid
    m = folium.Map(
        location=[centroid.y.mean(), centroid.x.mean()],
        zoom_start=10,
        tiles='CartoDB positron',
        control_scale=True,
        prefer_canvas=True,
        width='100%',
        height=400
    )
    
    folium.GeoJson(
        geometry.__geo_interface__,
        style_function=lambda x: {
            'fillColor': '#4daf4a',
            'color': '#377eb8',
            'weight': 2,
            'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(fields=[], aliases=[f'Bacia: {nome_bacia}'])
    ).add_to(m)
    
    return m

def validar_nome_bacia(nome):
    """Valida o nome da bacia conforme padrão ZAP"""
    if not nome:
        return False, "O nome não pode estar vazio"
    if ' ' in nome:
        return False, "Não use espaços - substitua por underscores (_)"
    if not all(c.isalnum() or c in ['_', '-'] for c in nome):
        return False, "Use apenas letras, números, hífens (-) ou underscores (_)"
    return True, ""

def mostrar_politica_privacidade():
    """Mostra a política de privacidade em um modal"""
    with st.expander("🔒 Política de Privacidade", expanded=False):
        st.markdown("""
        ## Política de Privacidade e Termos de Serviço para o Aplicativo ZAP Automatização

        **1. Informações Gerais**  
        - O aplicativo ZAP Automatização é desenvolvido pela Secretaria de Agricultura, Pecuária e Abastecimento de Minas Gerais.
        
        **2. Dados Coletados**  
        - Autenticação Google (OAuth 2.0)  
        - Arquivos GeoJSON (armazenados temporariamente)  
        - Dados de uso para auditoria e melhorias  

        **3. Uso dos Dados**  
        - Processamento de informações geográficas  
        - Geração de relatórios do ZAP  
        - Melhoria contínua do aplicativo  

        **4. Compartilhamento**  
        Não compartilhamos seus dados pessoais, exceto quando exigido por lei.  

        **5. Seus Direitos**  
        Você pode revogar o acesso, solicitar dados ou requerer exclusão.  

        **Contato:** zap@agricultura.mg.gov.br  
        """)

def mostrar_termos_servico():
    """Mostra os termos de serviço em um modal"""
    with st.expander("⚖️ Termos de Serviço", expanded=False):
        st.markdown("""
        ## Termos de Serviço

        **1. Aceitação**  
        Ao usar o aplicativo, você concorda com estes Termos.  

        **2. Uso Autorizado**  
        Destinado a técnicos e gestores públicos do ZAP.  

        **3. Responsabilidades**  
        - Fornecer informações precisas  
        - Não utilizar para fins ilegais  
        - Manter credenciais em sigilo  

        **4. Limitações**  
        Não garantimos disponibilidade contínua ou precisão absoluta.  

        **5. Propriedade Intelectual**  
        Conteúdo é propriedade do Governo de Minas Gerais.  

        **Contato:** zap@agricultura.mg.gov.br  
        """)

# ===============================================
# CONFIGURAÇÃO INICIAL E AUTENTICAÇÃO
# ===============================================

# Carregar CSS personalizado
local_css()

# Configuração OAuth2
if 'google_oauth' in st.secrets:
    CLIENT_ID = st.secrets['google_oauth']['client_id']
    CLIENT_SECRET = st.secrets['google_oauth']['client_secret']
    REDIRECT_URI = st.secrets['google_oauth']['redirect_uris']
else:
    st.error("Configurações do OAuth2 não encontradas.")
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

# ===============================================
# SIDEBAR - NAVEGAÇÃO E LINKS
# ===============================================

# Logo Sidebar
sidebar_logo = "https://i.postimg.cc/c4VZ0fQw/zap-logo.png"
main_body_logo = "https://i.postimg.cc/65qGpMc8/zap-logo-sb.png"
st.sidebar.image(sidebar_logo, use_container_width=True) 

# Links de navegação
with st.sidebar:
    st.markdown("## Navegação")
    
    # Documentação
    with st.expander("📚 Documentação", expanded=True):
        st.markdown('[📘 Sobre o ZAP](https://www.mg.gov.br/agricultura/pagina/zoneamento-ambiental-e-produtivo)', unsafe_allow_html=True)
        st.markdown('[🎥 Tutorial em Vídeo](https://youtu.be/exemplo)', unsafe_allow_html=True)
        st.markdown('[🐞 Reportar Bug](mailto:zap@agricultura.mg.gov.br)', unsafe_allow_html=True)
    
    # Termos legais
    with st.expander("⚖️ Legal"):
        if st.button("Política de Privacidade", key="privacy_button"):
            mostrar_politica_privacidade()
        if st.button("Termos de Serviço", key="legal_button"):
            mostrar_termos_servico()
    
    st.markdown("---")
    st.markdown("### Versão 1.0")
    st.caption("Desenvolvido para a 5ª edição do ZAP")
    st.caption("Secretaria de Agricultura, Pecuária e Abastecimento de Minas Gerais")

# ===============================================
# CABEÇALHO DA PÁGINA
# ===============================================

# Logo e título centralizado
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("https://i.postimg.cc/c4VZ0fQw/zap-logo.png", width=400)

# Título do aplicativo
st.title("Automatização de Obtenção de Dados para o Zoneamento Ambiental e Produtivo")

# ===============================================
# CARDS INFORMATIVOS
# ===============================================

# Card Sobre o ZAP
mostrar_card(
    "🌱 Sobre o ZAP",
    """
    O Zoneamento Ambiental e Produtivo (ZAP) é um instrumento de planejamento e gestão territorial para o uso sustentável 
    dos recursos naturais pela atividade agrossilvipastoril no estado de Minas Gerais.
    
    **Produtos Básicos:**
    - Mapeamento da cobertura e terra
    - Índice de Demanda Hídrica Superficial (IDHS)
    - Potencial de Uso Conservacionista (PUC)
    
    [Mais informações no Site do Governo de MG](https://www.mg.gov.br/agricultura/pagina/zoneamento-ambiental-e-produtivo)
    """
)

# Card Sobre a Ferramenta
mostrar_card(
    "🛠️ Sobre esta Ferramenta",
    """
    Esta ferramenta automatiza a obtenção de produtos e bases para os produtos utilizados no ZAP para a 5ª edição da metodologia.
    
    **🔑 Requisitos:**
    - Conexão com conta Google (Earth Engine, Cloud Service e Drive)
    - Arquivo GeoJSON da bacia hidrográfica (preferencialmente em UTM)
    
    **📌 Dicas:**
    - Use o template disponível na sidebar
    - O arquivo deve conter apenas um polígono
    - O CRS deve ser SIRGAS 2000 (EPSG:4674)
    """
)

# ===============================================
# DICIONÁRIOS E CONFIGURAÇÕES
# ===============================================

# Dicionário de produtos
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

# URLs das tabelas
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

# ===============================================
# FUNÇÕES DE PROCESSAMENTO
# ===============================================

@st.cache_data(ttl=3600)
def load_geojson(file):
    """Carrega e valida um arquivo GeoJSON"""
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

        # Verificação do CRS (SIRGAS 2000)
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
        
        # Visualização no mapa
        m = create_map(gdf.geometry.iloc[0])
        st_folium(m, width=600, height=400)
        st.success(f"CRS do arquivo validado: {gdf.crs} (SIRGAS 2000)")
        
        # Retorna geometria no SIRGAS 2000
        return ee.Geometry(gdf.geometry.iloc[0].__geo_interface__), CRS_OBRIGATORIO
        
    except Exception as e:
        st.error(f"Erro crítico ao carregar GeoJSON: {str(e)}")
        return None, None

def reprojetarImagem(imagem, epsg, escala):
    """Reprojeção de imagens para o CRS especificado"""
    return imagem.reproject(crs=f"EPSG:{epsg}", scale=escala)

def exportarImagem(imagem, nome_prefixo, nome_sufixo, escala, regiao, nome_bacia_export, pasta="zap"):
    """Exporta imagem para o Google Drive"""
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
    """Verifica o status de uma tarefa no Earth Engine"""
    try:
        status = task.status()
        state = status["state"]
        if state == "COMPLETED":
            return "✅ Concluído"
        elif state == "RUNNING":
            return "⏳ Em execução"
        elif state == "FAILED":
            return f"❌ Falhou: {status.get('error_message', 'Sem detalhes')}"
        else:
            return f"ℹ️ {state}"
    except Exception as e:
        return f"⚠️ Erro: {str(e)}"

@st.cache_data(ttl=3600)
def baixar_tabela(url):
    """Baixa tabelas do Google Drive"""
    try:
        output = BytesIO()
        gdown.download(url, output, quiet=True)
        output.seek(0)
        return pd.read_csv(output)
    except Exception as e:
        st.error(f"Erro ao baixar tabela: {e}")
        return None

def processar_municipios(geometry, nome_bacia_export):
    """Processa os municípios que intersectam a bacia"""
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

def processar_tabelas_agro(geocodigos):
    """Processa todas as tabelas agropecuárias"""
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
            # Remover colunas indesejadas
            colunas_remover = [col for col in ['.geo', 'system:index'] if col in df_filtrado.columns]
            if colunas_remover:
                df_filtrado = df_filtrado.drop(columns=colunas_remover)
            
            # Renomear colunas
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
            
            # Definir a ordem das colunas
            ordem_colunas = [
                'Municípios', 'geocodigo', 'Gentílico', 'Bioma predominante',
                'Área (km²)', 'População no último censo', 'População ocupada {%}',
                'Densidade demográfica (hab/km²)', 'PIB per capita',
                'Salário médio mensal dos trabalhadores formais', 'Receitas',
                'Despesas', 'Esgotamento sanitário adequado {%}',
                'Estabelecimentos de Saúde SUS', 'Mortalidade Infantil {%}',
                'Taxa de escolarização de 6 a 14 anos de idade {%}',
                'Urbanização de vias públicas {%}', 'Arborização de vias públicas {%}',
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
            
            # Identificar colunas de anos
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
            
            # Converter para DataFrame e pegar top 10 produtos
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
    """Gera arquivo Excel com os dados agropecuários"""
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
        
        # Exportar para o Google Drive
        try:
            drive_service = build('drive', 'v3', credentials=st.session_state["ee_credentials"])
            
            # Criar metadados do arquivo
            file_metadata = {
                'name': f"{nome_bacia_export}_dados_agro.xlsx",
                'parents': ['zap'],  # Pasta destino
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            # Fazer o upload
            media = MediaIoBaseUpload(output, 
                                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    resumable=True)
            
            file = drive_service.files().create(body=file_metadata,
                                              media_body=media,
                                              fields='id').execute()
            
            st.success(f"Arquivo exportado para o Google Drive na pasta 'zap' (ID: {file.get('id')})")
        except Exception as e:
            st.error(f"Erro ao exportar para o Google Drive: {e}")
        
        return output
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {e}")
        return None

def process_data(geometry, crs, nome_bacia_export="bacia", process_type="all"):
    """Função principal para processar os dados"""
    try:
        # Verificar se o Earth Engine está inicializado
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
            with st.status("Processando dados agro e socioeconômicos...", expanded=True) as status:
                municipios_df = processar_municipios(geometry, nome_bacia_export)
                
                if municipios_df is not None:
                    dados_agro = processar_tabelas_agro([int(x) for x in municipios_df['geocodigo'].tolist()])
                    status.update(label="Processamento agro concluído!", state="complete")
                    return dados_agro
            
            return None
        
        # Processar apenas sensoriamento remoto
        elif process_type == "remoto":
            with st.status("Processando dados de sensoriamento remoto...", expanded=True) as status:
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
                            st.success("Exportação da lista de imagens Sentinel-2 iniciada.")
                        except Exception as e:
                            st.error(f"Erro ao exportar a lista de imagens Sentinel-2: {e}")

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
                
                status.update(label="Processamento de sensoriamento concluído!", state="complete")
                return resultados
            
        return None
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# ===============================================
# INTERFACE PRINCIPAL
# ===============================================

# 1. Autenticação
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
    st.success("✅ Você está conectado à sua conta Google!")

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
                        if st.button("Confirmar Projeto", key="confirm_project"):
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

    # 2. Upload do arquivo GeoJSON
    if st.session_state.get("ee_initialized"):
        uploaded_file = st.file_uploader(
            "Carregue o arquivo GeoJSON da bacia hidrográfica (SIRGAS 2000 - EPSG:4674):",
            type=["geojson"],
            accept_multiple_files=False,
            help="Requisitos do arquivo:\n"
                 "- Apenas 1 polígono/multipolígono\n"
                 "- CRS SIRGAS 2000 (EPSG:4674)\n"
                 "- Tamanho máximo: 1MB\n"
                 "Obs: Técnicos devem preparar o arquivo previamente em seu software SIG"
        )
        
        if uploaded_file is not None:
            geometry, crs = load_geojson(uploaded_file)
            if geometry:
                nome_bacia_export = st.text_input(
                    "Digite o nome para exportação (sem espaços ou caracteres especiais):",
                    placeholder="Ex: Rib_Santa_Juliana",
                    help="⚠️ Este campo é obrigatório e deve seguir o padrão de nomenclatura do ZAP"
                )
                
                if nome_bacia_export:
                    # Validação do nome da bacia
                    nome_valido, msg_erro = validar_nome_bacia(nome_bacia_export)
                    if not nome_valido:
                        st.error(f"Nome inválido: {msg_erro}")
                        st.stop()
                    
                    # 3. Seleção de produtos
                    with st.form(key='product_selection_form'):
                        st.subheader("📡 Produtos de Sensoriamento Remoto (Imagens/Raster)")
                        st.caption(f"Sistema de referência espacial: {crs}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Índices Espectrais**")
                            exportar_ndvi = st.checkbox("NDVI (10m)", value=st.session_state.get('select_all', False), key="ndvi")
                            exportar_gndvi = st.checkbox("GNDVI (10m)", value=st.session_state.get('select_all', False), key="gndvi")
                            exportar_ndwi = st.checkbox("NDWI (10m)", value=st.session_state.get('select_all', False), key="ndwi")
                            exportar_ndmi = st.checkbox("NDMI (10m)", value=st.session_state.get('select_all', False), key="ndmi")
                            
                            st.markdown("**Modelo Digital de Elevação**")
                            exportar_srtm_mde = st.checkbox("SRTM MDE (30m)", value=st.session_state.get('select_all', False), key="mde")
                            exportar_declividade = st.checkbox("Declividade (30m)", value=st.session_state.get('select_all', False), key="declividade")

                        with col2:
                            st.markdown("**Cobertura e Uso da Terra**")
                            exportar_mapbiomas = st.checkbox("MapBiomas 2023 (30m)", value=st.session_state.get('select_all', False), key="mapbiomas")
                            exportar_pasture_quality = st.checkbox("Qualidade de Pastagem 2023 (30m)", value=st.session_state.get('select_all', False), key="pasture")
                            exportar_sentinel_composite = st.checkbox("Sentinel-2 B2/B3/B4/B8 (10m)", value=st.session_state.get('select_all', False), key="sentinel")
                            
                            st.markdown("**Potencial de Uso**")
                            exportar_puc_ufv = st.checkbox("PUC UFV (30m)", value=st.session_state.get('select_all', False), key="puc_ufv")
                            exportar_puc_ibge = st.checkbox("PUC IBGE (30m)", value=st.session_state.get('select_all', False), key="puc_ibge")
                            exportar_puc_embrapa = st.checkbox("PUC Embrapa (30m)", value=st.session_state.get('select_all', False), key="puc_embrapa")
                            
                            st.markdown("**Geomorfologia**")
                            exportar_landforms = st.checkbox("Landforms (30m)", value=st.session_state.get('select_all', False), key="landforms")
                        
                        st.markdown("---")
                        
                        st.subheader("📊 Dados Agro e Socioeconômicos")
                        st.caption("Municípios com representatividade >20% na bacia hidrográfica")
                        exportar_dados_agro = st.checkbox("Ativar processamento de dados do IBGE", value=st.session_state.get('select_ibge', False), key="dados_agro")
                        
                        st.markdown("---")                    
                        submit_button = st.form_submit_button(label='✅ Confirmar Seleção', use_container_width=True)

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

                    # 4. Processamento dos dados
                    if st.session_state.get("exportar_srtm_mde") is not None and nome_bacia_export:
                        if st.button("Processar Dados", key="process_data", use_container_width=True):
                            with st.status("Iniciando processamento...", expanded=True) as status:
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
                                    status.update(label="Processando dados agropecuários...")
                                    dados_agro = process_data(geometry, crs, nome_bacia_export, "agro")
                                    if dados_agro:
                                        excel_agro = gerar_excel_agro(dados_agro, nome_bacia_export)
                                        if excel_agro:
                                            st.download_button(
                                                label="📥 Baixar Dados Agro e Socioeconômicos",
                                                data=excel_agro,
                                                file_name=f"{nome_bacia_export}_dados_agro.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key=f"download_agro_{int(time.time())}",
                                                use_container_width=True
                                            )
                                            status.update(label="Processamento concluído!", state="complete")
                                            st.success("✅ Os dados foram enviados para a pasta 'zap' no seu Google Drive")
                                
                                # Processar sensoriamento remoto (e agro depois, se selecionado)
                                elif process_remoto:
                                    status.update(label="Processando dados de sensoriamento remoto...")
                                    resultados = process_data(geometry, crs, nome_bacia_export, "remoto")
                                    
                                    if resultados:
                                        st.session_state["resultados"] = resultados
                                        
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
                                        
                                        # Verificar status das tarefas
                                        if tasks_remoto:
                                            status.update(label="Verificando status das tarefas...")
                                            
                                            progress_bar = st.progress(0)
                                            status_table = st.empty()
                                            
                                            todas_concluidas = False
                                            last_update = time.time()
                                            
                                            while not todas_concluidas:
                                                todas_concluidas = True
                                                completed_tasks = 0
                                                status_data = []
                                                
                                                for i, task in enumerate(tasks_remoto):
                                                    state = check_task_status(task)
                                                    status_data.append({
                                                        "Tarefa": f"Tarefa {i+1}",
                                                        "Status": state
                                                    })
                                                    
                                                    if "Concluído" not in state:
                                                        todas_concluidas = False
                                                    else:
                                                        completed_tasks += 1
                                                
                                                # Atualizar tabela de status
                                                status_df = pd.DataFrame(status_data)
                                                status_table.table(status_df)
                                                
                                                # Atualizar barra de progresso
                                                progress = completed_tasks / len(tasks_remoto)
                                                progress_bar.progress(progress)
                                                
                                                if todas_concluidas:
                                                    status.update(label="✅ Todos os produtos de sensoriamento foram processados!", state="complete")
                                                    break
                                                else:
                                                    status.update(label=f"⌛ Progresso: {completed_tasks}/{len(tasks_remoto)} tarefas concluídas")
                                                
                                                # Espera 30 segundos entre verificações
                                                time.sleep(30)
                                        
                                        # Processar dados agro APÓS o sensoriamento, se selecionado
                                        if process_agro:
                                            status.update(label="Processando dados agropecuários...")
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
                                                            key=f"download_agro_{int(time.time())}",
                                                            use_container_width=True
                                                        )
                                                        status.update(label="✅ Todos os processamentos foram concluídos!", state="complete")
                                                        st.success("ℹ️ Os dados estão disponíveis em: (1) Seu download local e (2) Pasta 'zap' no Google Drive")
                                                        st.markdown(
                                                            f"[Abrir pasta 'zap' no Google Drive](https://drive.google.com/drive/folders/zap)",
                                                            unsafe_allow_html=True)