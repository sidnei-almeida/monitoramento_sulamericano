# Função para coletar dados de mais de uma fonte

from requisicoes import coletar_dados_wb
import pandas as pd

# Lista de Países
paises = ['BRA', 'ARG', 'CHL', 'COL', 'PER']

# Discionário de indicadores
indicadores = {
    "PIB_USD": "NY.GDP.MKTP.CD",
    "Inflacao": "FP.CPI.TOTL.ZG",
    "Desemprego": "SL.UEM.TOTL.ZS"
}

# Lista para armazenar os DataFrames
todos_os_dados = []

# Loop para coletar dados de cada país e indicador
for pais in paises:
    for nome_indicador, codigo_indicador in indicadores.items():
        print(f"🔍 Coletando {nome_indicador} para {pais}...")
        df = coletar_dados_wb(pais, codigo_indicador, 2010, 2025)
        if not df.empty:
            df["indicador"] = nome_indicador
            todos_os_dados.append(df)

# Concatenar tudo em um único DataFrame
df_final = pd.concat(todos_os_dados, ignore_index=True)

# Salvar em CSV
df_final.to_csv("dados/dados_macro_america_sul.csv", index=False)
print("✅ Coleta finalizada. Dados salvos em dados_macro_america_sul.csv")