import requests
import pandas as pd
from datetime import datetime

# Lista de países da América do Sul com seus códigos ISO-3 do World Bank
COUNTRIES = {
    "Argentina": "ARG", "Bolivia": "BOL", "Brazil": "BRA", "Chile": "CHL",
    "Colombia": "COL", "Ecuador": "ECU", "Guyana": "GUY", "Paraguay": "PRY",
    "Peru": "PER", "Suriname": "SUR", "Uruguay": "URY", "Venezuela": "VEN"
}

# Indicadores do World Bank
INDICATORS = {
    "PIB (US$ atual)": "NY.GDP.MKTP.CD",  # Produto Interno Bruto em dólares americanos correntes
    "Inflação (% anual)": "FP.CPI.TOTL.ZG",  # Variação percentual anual do índice de preços ao consumidor
    "Taxa de juros real (%)": "FR.INR.RINR",  # Taxa de juros ajustada pela inflação
    "Desemprego (% força de trabalho)": "SL.UEM.TOTL.ZS",  # Porcentagem da força de trabalho desempregada
    "Taxa de câmbio (LCU/US$)": "PA.NUS.FCRF"  # Taxa de câmbio oficial
}


def fetch_indicator_data(indicator_code, start_year=2000, end_year=2025):
    """
    Coleta dados do World Bank para todos os países da América do Sul para um indicador específico.
    """
    """
    Coleta dados do World Bank para todos os países da América do Sul para um indicador específico.
    """
    all_data = []

    for country_name, country_code in COUNTRIES.items():
        url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}?format=json&date={start_year}:{end_year}&per_page=100"
        res = requests.get(url)

        if res.status_code != 200:
            print(f"[ERRO] {country_name}: {res.status_code}")
            continue

        try:
            data_json = res.json()[1]
        except:
            print(f"[ERRO JSON] {country_name}: dados não encontrados")
            continue

        for entry in data_json:
            if entry["value"] is not None:
                all_data.append({
                    "country": country_name,
                    "indicator": indicator_code,
                    "value": entry["value"],
                    "date": entry["date"]
                })

    return pd.DataFrame(all_data)


def fetch_all_indicators():
    """
    Retorna um DataFrame combinado com todos os indicadores e países.
    """
    dfs = []
    for name, code in INDICATORS.items():
        df = fetch_indicator_data(code)
        df = df.rename(columns={"value": name})
        dfs.append(df[["country", "date", name]])

    # Combinar todos os indicadores em um único DataFrame
    df_final = dfs[0]
    for df in dfs[1:]:
        df_final = pd.merge(df_final, df, on=["country", "date"], how="outer")

    # Formatar a data
    df_final["date"] = pd.to_datetime(df_final["date"], format="%Y")

    return df_final.sort_values(by=["country", "date"]).reset_index(drop=True)