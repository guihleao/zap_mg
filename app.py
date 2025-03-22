import streamlit as st
import ee
from streamlit_oauth import OAuth2Component
import json
import time

def authenticate():
    client_id = "SUA_CLIENT_ID"
    client_secret = "SUA_CLIENT_SECRET"
    authorization_url = "https://accounts.google.com/o/oauth2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    
    oauth = OAuth2Component(client_id, client_secret, authorization_url, token_url)
    token = oauth.get_access_token()
    if token:
        st.session_state["oauth_token"] = token
        return True
    return False

if "oauth_token" not in st.session_state:
    authenticated = authenticate()
    if not authenticated:
        st.stop()

ee.Initialize()

def processar_imagens(bacia):
    sentinel = ee.ImageCollection("COPERNICUS/S2")\
        .filterBounds(bacia)\
        .filterDate("2023-01-01", "2023-12-31")
    
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
    
    mde = ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2")\
        .filterBounds(bacia)\
        .mosaic()\
        .clip(bacia)
    declividade = ee.Terrain.slope(mde.select('DSM'))
    
    mapbiomas = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1")\
        .clip(bacia)
    pasture_quality = ee.Image("projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_pasture_quality_v1")\
        .select('pasture_quality_2023')\
        .clip(bacia)
    
    return {
        "sentinel_median": sentinel_median,
        "indices": indices,
        "mde": mde,
        "declividade": declividade,
        "mapbiomas": mapbiomas,
        "pasture_quality": pasture_quality,
    }

def exportar_para_drive(imagem, nome_arquivo):
    task = ee.batch.Export.image.toDrive(
        image=imagem,
        description=nome_arquivo,
        folder="GEE_Exports",
        fileNamePrefix=nome_arquivo,
        scale=10,
        region=imagem.geometry().bounds().getInfo(),
        fileFormat="GeoTIFF"
    )
    task.start()
    return task

def checar_status_exportacao(task):
    while task.status()["state"] in ["READY", "RUNNING"]:
        st.info(f"Exportando: {task.status()['state']}")
        time.sleep(10)
    if task.status()["state"] == "COMPLETED":
        st.success("Exportação concluída com sucesso!")
    else:
        st.error(f"Erro na exportação: {task.status()['error_message']}")

bacia = ee.Geometry.Polygon([[[LONG, LAT], [LONG, LAT], [LONG, LAT], [LONG, LAT]]])

dados = processar_imagens(bacia)
if dados:
    st.write("Dados processados com sucesso!")
    if st.button("Exportar NDVI para o Google Drive"):
        task = exportar_para_drive(dados["indices"]["NDVI"], "NDVI_Bacia")
        checar_status_exportacao(task)
