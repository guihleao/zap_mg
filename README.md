# ZAP Automatização - Earth Engine Processor

[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

![ZAP Logo](https://i.postimg.cc/c4VZ0fQw/zap-logo.png)

## 📋 Tabela de Conteúdos
- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-Funcionalidades)
- [Como Usar](#-como-usar)
- [Tecnologias](#-Tecnologias)
- [Política de Privacidade](#-política-de-privacidade-e-termo-de-serviço)
- [Licença](#-licença)
- [Contato](#-contato)

## 🌍 Visão Geral
Aplicação web para processamento automatizado de dados geoespaciais e agropecuários para o Zoneamento Ambiental e Produtivo (ZAP) de Minas Gerais, hospedada na nuvem do Streamlit.

## ⚙️ Funcionalidades

### 🛰️ Processamento Geoespacial
| Módulo | Descrição |
|--------|-----------|
| **Índices de Vegetação** | NDVI, GNDVI, NDWI, NDMI |
| **Topografia** | Modelo Digital de Elevação (SRTM) e declividade |
| **Cobertura do Solo** | MapBiomas + Qualidade de Pastagens |

### 📊 Dados Agropecuários
- Análise de dados do IBGE, PAM e PPM
- Filtro automático por municípios relevantes
- Exportação de relatórios em Excel

## 🚀 Como Usar
1. **Acesse** o aplicativo pelo link disponibilizado
2. **Faça login** com sua conta Google (requer acesso ao Earth Engine)
3. **Carregue** seu arquivo GeoJSON da bacia hidrográfica
4. **Selecione** os produtos desejados
5. **Exporte** os resultados para seu Google Drive

📌 **Requisitos:**
- Conta Google com acesso ao Earth Engine ativado
- Arquivo GeoJSON em SIRGAS 2000 (EPSG:4674)

## 🛠️ Tecnologias
- **Frontend**: ![Streamlit](https://img.shields.io/badge/Streamlit-1.22+-FF4B4B)
- **Backend**: ![Python](https://img.shields.io/badge/Python-3.8+-blue)
- **APIs**: 
  - ![Earth Engine](https://img.shields.io/badge/Earth_Engine_API-v1.0-orange)
  - ![Google Drive](https://img.shields.io/badge/Google_Drive_API-v3-blue)

## 🔒 Política de Privacidade e Termo de Serviço
- Autenticação via OAuth 2.0 do Google
- Dados processados são armazenados **temporariamente** durante a sessão
- Credenciais são gerenciadas diretamente pelo Google Auth
- [Política completa disponível aqui]([#](https://github.com/guihleao/zap_mg/security/policy))
- [Termo de Serviços]([#](https://github.com/guihleao/zap_mg/security/policy))

## 📜 Licença
Copyright © 2025 SEAPA-MG
Distribuído sob licença MIT. Consulte o arquivo [LICENSE](LICENSE) para termos completos.

```text
Permissão é concedida, gratuitamente, a qualquer pessoa que obtenha uma cópia
deste software e documentação associada, para lidar com o Software sem restrição,
incluindo direitos de uso, cópia, modificação, mesclagem, publicação, distribuição,
sublicenciamento e/ou venda de cópias do Software.
```

## 📧 Contato
Secretaria de Agricultura de MG  
📩 [zap@agricultura.mg.gov.br](mailto:zap@agricultura.mg.gov.br)  
🌐 [www.agricultura.mg.gov.br/zap](https://www.agricultura.mg.gov.br/zap)

[![Acesse o App](https://img.shields.io/badge/ACESSE_O_APP_AQUI-FF6B6B?style=for-the-badge&logo=google-chrome&logoColor=white)](https://zap-mg.streamlit.app)
