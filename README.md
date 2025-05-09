# Dashboard Econômico América do Sul

Este projeto é um dashboard interativo desenvolvido em **Streamlit** para monitoramento e visualização de dados econômicos de países da América do Sul, com foco em indicadores como PIB, inflação, desemprego, taxa de juros, entre outros. Os dados são coletados automaticamente da API do World Bank.

## Funcionalidades Principais

- Visualização de séries temporais para cada país e indicador.
- **Score de Risco de Investimento** para avaliação comparativa entre países.
- Comparação entre múltiplos países em tempo real.
- Análise de correlação entre indicadores econômicos.
- Mapa interativo de distribuição dos indicadores.
- Estatísticas descritivas e métricas de tendência.
- Download dos dados em CSV e Excel diretamente pelo dashboard.
- Atualização automática dos dados a cada 1 hora.

## Como rodar o projeto

1. Clone este repositório:
   ```bash
   git clone https://github.com/sidnei-almeida/monitoramento_sulamericano
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o dashboard:
   ```bash
   streamlit run app.py
   ```

## Estrutura do Projeto
- `app.py`: Código principal do dashboard.
- `dashboard_portfolio.css`: Customização visual do dashboard.
- `data_api.py`: Funções para coleta de dados do World Bank.
- `presidentes.csv`: Dados sobre presidentes para contextualização política.
- `fundo.png`: (Opcional) Imagem para customização visual.

## Requisitos
- Python 3.1
- Streamlit
- Plotly
- Pandas
- openpyxl

## Sobre o Projeto
Este dashboard foi desenvolvido para compor o meu portfólio de projetos de Data Science. O objetivo é demonstrar habilidades em coleta, processamento, análise e visualização de dados econômicos em tempo real.

---

### Atualização dos Dados
- Os dados econômicos são coletados em tempo real da API do World Bank.
- O dashboard permite atualização manual ou automática a cada 1 hora.
- Os dados disponíveis vão até o ano de 2025, conforme disponibilidade do World Bank.

### Score de Risco de Investimento
- **Nova funcionalidade (2025)**: Sistema de avaliação de risco relativo para investimentos nos países da América do Sul.
- Utiliza um algoritmo que pondera múltiplos indicadores econômicos para gerar um score entre 0-100:
  - **0-30**: Baixo risco de investimento (verde)
  - **30-60**: Risco moderado (laranja)
  - **60-100**: Alto risco (vermelho)
- Considera indicadores como PIB, inflação, taxa de juros e desemprego, com pesos calibrados conforme o impacto no ambiente de investimento.
- Disponibiliza visualizações comparativas e detalhadas para análise de risco por país.
- Inclui explicação detalhada da metodologia para auxílio na tomada de decisões.
