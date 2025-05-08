import requests
import pandas as pd
import json

# Criei a função para coletar dados da API do World Bank
def coletar_dados_wb(pais_iso, indicador, ano_inicio=2010, ano_fim=2025):
    """
    Coleta dados da API do World Bank para um país e indicador específico.

    Parâmetros:
    - pais_iso (str): Código ISO do país (ex: 'BRA')
    - indicador (str): Código do indicador (ex: 'NY.GDP.MKTP.CD')
    - ano_inicio (int)
    - ano_fim (int)

    Retorna:
    - DataFrame com colunas: pais, ano, valor
    """
    url = (
        f"https://api.worldbank.org/v2/country/{pais_iso}/indicator/{indicador}"
        f"?format=json&date={ano_inicio}:{ano_fim}&per_page=100"
    )

    resposta = requests.get(url)
    if resposta.status_code != 200:
        print(f"[ERRO] Falha na requisicao: {resposta.status_code}")
        return pd.DataFrame()

    dados_json = resposta.json()
    if not dados_json or len(dados_json) < 2:
        print("[AVISO] Nenhum dado encontrado.")
        return pd.DataFrame()

    registros = dados_json[1]
    df = pd.DataFrame([
        {
            "pais": item["country"]["value"],
            "ano": int(item["date"]),
            "valor": item["value"]
        }
        for item in registros if item["value"] is not None
    ])

    return df

