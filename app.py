import warnings
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Função para converter DataFrame para Excel
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    output.seek(0)
    return output.getvalue()
import numpy as np
from datetime import datetime
from scipy.stats import linregress
from data_api import fetch_all_indicators

# Desativar warnings
warnings.filterwarnings('ignore')

# Configurações da página
st.set_page_config(
    layout="wide",
    page_title="Dashboard Econômica - América do Sul",
    initial_sidebar_state="expanded"
)

# --- Sidebar customizada e botão de ocultar ---
import streamlit.components.v1 as components
# Injeta JS para toggle
components.html(
    """
    <script src="sidebar_toggle.js"></script>
    <script>
        // Aplica classe customizada ao sidebar
        window.addEventListener('DOMContentLoaded', function() {
            var sidebar = window.parent.document.querySelector('section[data-testid=\"stSidebar\"]');
            if (sidebar && !sidebar.classList.contains('sidebar-bg-custom')) {
                sidebar.classList.add('sidebar-bg-custom');
            }
        });
        setTimeout(function() {
            var sidebar = window.parent.document.querySelector('section[data-testid=\"stSidebar\"]');
            if (sidebar && !sidebar.classList.contains('sidebar-bg-custom')) {
                sidebar.classList.add('sidebar-bg-custom');
            }
        }, 1000);
    </script>
    """,
    height=0
)

# Função auxiliar para formatação de números
def format_number(value, indicator_code):
    """
    Formata números com base no tipo de indicador.
    """
    if pd.isna(value):
        return "-"

    # Permitir formatação compacta para qualquer indicador relacionado a PIB/GDP
    if (
        indicator_code == "NY.GDP.MKTP.CD"
        or "PIB" in str(indicator_code).upper()
        or "GDP" in str(indicator_code).upper()
        or "US$" in str(indicator_code).upper()
    ):
        abs_value = abs(value)
        if abs_value >= 1e12:
            return f"US$ {value/1e12:,.2f} TRI"
        elif abs_value >= 1e9:
            return f"US$ {value/1e9:,.2f} BI"
        elif abs_value >= 1e6:
            return f"US$ {value/1e6:,.2f} MI"
        else:
            return f"US$ {value:,.0f}"
    elif indicator_code == "FP.CPI.TOTL.ZG":  # Inflação
        return f"{value:.1f}%"
    elif indicator_code == "FR.INR.RINR":  # Taxa de juros real
        return f"{value:.1f}%"
    elif indicator_code == "SL.UEM.TOTL.ZS":  # Desemprego
        return f"{value:.1f}%"
    elif indicator_code == "PA.NUS.FCRF":  # Taxa de câmbio
        return f"{value:.4f}"
    else:
        return f"{value:.2f}"

    

# Cabeçalho principal com timestamp de atualização
current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
st.markdown("### Monitoramento Econômico - América do Sul")
st.caption(f"Última atualização: {current_time}")

# Carregar dados
import time

@st.cache_data(ttl=3600)
def carregar_dados(): # cache de 1 hora
    """
    Carrega dados econômicos com cache de 1 hora
    Returns:
        pd.DataFrame: DataFrame com dados econômicos
    """
    try:
        data = fetch_all_indicators()
        if data.empty:
            st.warning("Nenhum dado disponível no momento")
        return data
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

# Mensagem simples de carregamento
with st.spinner("Carregando dados econômicos..."):
    # Carregar dados
    df = carregar_dados()

# Verificar se os dados foram carregados com sucesso
if df.empty:
    st.error("Não foi possível carregar os dados. Por favor, tente novamente mais tarde.")
    st.stop()

# Lista dos indicadores disponíveis (colunas no DataFrame, exceto 'country' e 'date')
indicator_columns = [col for col in df.columns if col not in ['country', 'date']]

# Sidebar: filtros aprimorados
st.sidebar.header("Filtros e Controles")

# Modo de visualização
viz_mode = st.sidebar.radio("Modo de visualização", ["País único", "Comparação entre países"])

# Seleção de indicador comum para ambos os modos
selected_indicator = st.sidebar.selectbox("Selecione o indicador", indicator_columns)

# Filtragem baseada no modo selecionado
if viz_mode == "País único":
    selected_country = st.sidebar.selectbox("Selecione o país", sorted(df["country"].unique()))
    # Mensagem de atualização automática na sidebar (após seleção de país)
    st.sidebar.info('Os dados são atualizados automaticamente a cada hora.')
    
    # Filtrar dados para o país e indicador selecionados
    country_data = df[df["country"] == selected_country].copy()
    country_data = country_data[["country", "date", selected_indicator]]
    country_data = country_data.sort_values("date")
    
    # Verificar se há dados disponíveis
    if country_data.empty:
        st.warning(f"Não há dados disponíveis para {selected_country} e o indicador selecionado.")
        st.stop()
    
    # Renomeando a coluna do indicador para facilitar o trabalho com os gráficos
    country_data = country_data.rename(columns={selected_indicator: "value"})
    
    # Exibir presidente correspondente ao ano
    import pandas as pd
    try:
        pres_df = pd.read_csv("https://raw.githubusercontent.com/sidnei-almeida/monitoramento_sulamericano/refs/heads/main/presidentes.csv")
        pres_df = pres_df[pres_df["pais"] == selected_country]
        # Gráfico de linha do tempo dos mandatos presidenciais
        import plotly.express as px
        # Filtrar mandatos para o período 2000-2025
        mandatos = pres_df.copy()
        mandatos = mandatos[(mandatos["mandato_fim"] >= 2000) & (mandatos["mandato_inicio"] <= 2025)]
        mandatos["inicio"] = pd.to_datetime(mandatos["mandato_inicio"].astype(str) + "-01-01")
        mandatos["fim"] = pd.to_datetime(mandatos["mandato_fim"].astype(str) + "-12-31")
        fig_timeline = px.timeline(
            mandatos,
            x_start="inicio",
            x_end="fim",
            y="presidente",
            color="presidente",
            color_discrete_sequence=["#1e88e5", "#43a047", "#e53935", "#fbc02d", "#8e24aa", "#00897b", "#f4511e", "#3949ab", "#6d4c41", "#c0ca33"],  # Paleta sóbria para Gantt
            hover_data={
                "inicio": True,
                "fim": True,
                "presidente": True
            }
        )
        fig_timeline.update_yaxes(autorange="reversed")
        fig_timeline.update_traces(
            marker=dict(line=dict(color="#333", width=0.7),
                        opacity=0.95),
        )
        fig_timeline.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Ano",
            yaxis_title="Presidente",
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="#1e3d59"),
            showlegend=False,
            yaxis=dict(showgrid=False),
            xaxis=dict(
                showgrid=True, gridcolor="#eee", zeroline=False,
                tickformat="%Y",
                ticks="outside",
                ticklabelmode="period",
                showline=True, linecolor="#bbb"
            )
        )
        fig_timeline.update_traces(opacity=0.8)
        # Adicionar labels de datas nos extremos
        for i, row in mandatos.iterrows():
            fig_timeline.add_annotation(
                x=row["inicio"], y=row["presidente"],
                text=row["mandato_inicio"],
                showarrow=False, yshift=8, font=dict(size=10, color="#666")
            )
            fig_timeline.add_annotation(
                x=row["fim"], y=row["presidente"],
                text=row["mandato_fim"],
                showarrow=False, yshift=8, font=dict(size=10, color="#666")
            )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
    except Exception as e:
        st.warning(f"Não foi possível carregar dados políticos: {e}")
    
    # Layout de duas colunas
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Gráfico principal - evolução do indicador
        fig = px.line(
            country_data, 
            x="date", 
            y="value",
            title=f"Evolução do {selected_indicator} para {selected_country}",
            template="plotly_white",
            markers=True,
            color_discrete_sequence=["#D50032"]  # Rosa padrão
        )

        # Customizar eixo y para PIB
        if selected_indicator == "NY.GDP.MKTP.CD":
            max_val = country_data['value'].max()
            if max_val >= 1e12:
                fig.update_yaxes(tickformat=".2f", ticksuffix=" TRI")
            elif max_val >= 1e9:
                fig.update_yaxes(tickformat=".2f", ticksuffix=" BI")
            elif max_val >= 1e6:
                fig.update_yaxes(tickformat=".2f", ticksuffix=" MI")
            else:
                fig.update_yaxes(tickformat=",.0f")
        
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Valor",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(0,0,0,0)'),
            height=450,
            margin=dict(l=10, r=10, t=50, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f2f2f7")
        )
        
        st.plotly_chart(fig, use_container_width=True)

        
        # Análise de distribuição
        if not country_data["value"].isna().all():
            fig_hist = px.histogram(
                country_data, 
                x="value", 
                nbins=10,
                title=f"Distribuição de {selected_indicator}",
                template="plotly_white",
                color_discrete_sequence=["#D50032"]  # Rosa padrão
            )
            
            fig_hist.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f2f2f7"),
                legend_bgcolor='rgba(0,0,0,0)'
            )
            fig_hist.update_layout(
                xaxis_title="Valor",
                yaxis_title="Frequência",
                bargap=0.1,
                height=350
            )
            st.plotly_chart(fig_hist, use_container_width=True, key="hist")

        
        # Análise de tendência
        if len(country_data) > 1:
            st.markdown("<h2><i class='fas fa-microscope'></i> Análise de Tendência</h2>", unsafe_allow_html=True)

            # Ordenar por data para garantir alinhamento
            country_data = country_data.sort_values('date').reset_index(drop=True)
            # Converter datas para números para regressão
            date_dt = pd.to_datetime(country_data['date'])
            x = date_dt.view('int64')
            y = country_data['value']

            # Calcular linha de tendência usando regressão linear
            slope, intercept, r_value, p_value, std_err = linregress(x, y)

            # Gerar valores previstos para cada ponto do eixo X
            trend = slope * x + intercept

            # Plotar dados com linha de tendência
            fig_trend = px.scatter(
                country_data,
                x="date",
                y="value",
                title=f"Tendência de {selected_indicator} - {selected_country}",
                template="plotly_white",
                color_discrete_sequence=["#D50032"]  # Rosa padrão
            )

            # Adicionar linha de tendência (mesmo eixo X do gráfico principal)
            fig_trend.add_trace(
                go.Scatter(
                    x=country_data['date'],
                    y=trend,
                    mode='lines',
                    name='Tendência',
                    line=dict(color='#ffe600', width=3, dash='dash')  # Amarelo bem visível
                )
            )

            fig_trend.update_layout(
                xaxis_title="Data",
                yaxis_title="Valor",
                hovermode="x unified",
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f2f2f7"),
                legend_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig_trend, use_container_width=True, key="trend")

            # Mostrar métricas de tendência
            st.markdown("<h3><i class='fas fa-calculator'></i> Métricas de Tendência</h3>", unsafe_allow_html=True)
            st.info(f"Coeficiente de correlação (R²): {r_value**2:.4f}")
            st.info(f"P-valor: {p_value:.4f}")
            st.info(f"Erro padrão: {std_err:.4f}")

    
    with col2:
        # Métricas e estatísticas
        try:
            # Encontrar o valor mais recente não-nulo
            valid_values = country_data.dropna(subset=["value"])
            if not valid_values.empty:
                latest_row = valid_values.iloc[-1]
                latest_value = latest_row["value"]
                latest_year = latest_row["date"]
            else:
                latest_value = float('nan')
                latest_year = "-"

            previous_value = valid_values.iloc[-2]["value"] if len(valid_values) > 1 else None

            # Calcular variação
            delta = None
            if previous_value is not None:
                delta = (latest_value - previous_value) / previous_value * 100
                delta = f"{delta:.2f}%"
            
            # Métricas principais

            st.metric(
                "Valor mais atual",
                format_number(latest_value, selected_indicator),
                delta=format_number(latest_value - previous_value if previous_value else 0, selected_indicator),
                help=f"Ano da medição: {latest_year}"
            )
            
            # Estatísticas descritivas
            st.markdown("### Estatísticas")
            stats = country_data["value"].describe()
            
            # Criar DataFrame para as estatísticas
            stats_df = pd.DataFrame({
                "Métrica": ["Média", "Mediana", "Mínimo", "Máximo", "Desvio Padrão"],
                "Valor": [stats['mean'], stats['50%'], stats['min'], stats['max'], stats['std']]
            })
            
            # Formatar valores
            stats_df["Valor"] = stats_df["Valor"].apply(lambda x: format_number(x, selected_indicator))
            
            # Mostrar tabela de estatísticas
            st.dataframe(
                stats_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Métrica": st.column_config.TextColumn(
                        "Métrica",
                        help="Estatísticas descritivas do indicador selecionado"
                    ),
                    "Valor": st.column_config.TextColumn(
                        "Valor",
                        help="Valores formatados de acordo com o tipo de indicador"
                    )
                }
            )
            
            # Opções de download
            st.markdown("<h3><i class='fas fa-download'></i> Downloads</h3>", unsafe_allow_html=True)
            
            # Baixar dados em CSV
            st.download_button(
                label="Baixar dados em CSV",
                data=country_data.to_csv(index=False).encode('utf-8'),
                file_name=f"dados_{selected_indicator}_{selected_country}.csv",
                mime='text/csv'
            )
            
            # Baixar dados em Excel
            st.download_button(
                label="Baixar dados em Excel",
                data=to_excel(country_data),
                file_name=f"dados_{selected_indicator}_{selected_country}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            if "not enough values to unpack" in str(e) or "index out of bounds" in str(e):
                st.warning("⚠️ Sem dados suficientes para calcular as métricas")
            else:
                st.warning(f"⚠️ Erro ao calcular métricas: {str(e)}")

else:  # Modo de comparação entre países
    multi_countries = st.sidebar.multiselect(
        "Selecione países para comparar",
        sorted(df["country"].unique()),
        default=list(df["country"].unique())[:3]
    )
    # Mensagem de atualização automática na sidebar (após seleção de países)
    st.sidebar.info('Os dados são atualizados automaticamente a cada hora.')
    
    if not multi_countries:
        st.warning("⚠️ Por favor, selecione pelo menos um país para visualizar os dados.")
        st.stop()
    
    # Filtrar dados para múltiplos países
    multi_data = df[df["country"].isin(multi_countries)].copy()
    multi_data["date"] = pd.to_datetime(multi_data["date"])
    
    # Renomeando a coluna do indicador para facilitar o trabalho com os gráficos
    multi_data = multi_data.rename(columns={selected_indicator: "value"})
    
    # Verificar se há dados disponíveis
    if multi_data.empty:
        st.warning("Nenhum dado disponível para os países selecionados.")
        st.stop()
    
    # Visão por abas
    compare_tabs = st.tabs(["Comparação Temporal", "Ranking", "Mapa", "Análise Estatística", "Correlação"])
    
    with compare_tabs[0]:
        # Gráfico de linha comparando países
        fig_compare = px.line(
            multi_data,
            x="date",
            y="value",
            color="country",
            title=f"Evolução comparativa de {selected_indicator}",
            template="plotly_white",
            markers=True,
            hover_name="country"
        )
        
        fig_compare.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f2f2f7"),
            legend_bgcolor='rgba(0,0,0,0)'
        )
        fig_compare.update_layout(
            xaxis_title="Data",
            yaxis_title="Valor",
            legend_title="País",
            hovermode="x unified",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(0,0,0,0)')
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        
        # Análise de correlação
        if len(multi_countries) > 1:
            pivot_df = multi_data.pivot(index='date', columns='country', values='value').reset_index()
            pivot_df = pivot_df.dropna()
            
            if not pivot_df.empty and len(pivot_df) > 1:
                corr_matrix = pivot_df.drop(columns=['date']).corr()
                
                fig_corr = px.imshow(
                    corr_matrix,
                    template="plotly_white",
                    color_continuous_scale="viridis",
                    text_auto=True,
                    title="Mapa de Calor das Correlações"
                )
                
                fig_corr.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#f2f2f7"),
                    legend_bgcolor='rgba(0,0,0,0)'
                )
                fig_corr.update_layout(height=400)
                st.plotly_chart(fig_corr, use_container_width=True)

                
                st.info("Interpretação: Valores próximos a 1 indicam forte correlação positiva, -1 indica forte correlação negativa, e 0 indica ausência de correlação.")
                
    with compare_tabs[1]:
        # Ranking e comparações estáticas
        latest_values = multi_data.sort_values('date').groupby('country').last().reset_index()
        
        # Gráfico de barras para ranking
        fig_rank = px.bar(
            latest_values,
            y="country",
            x="value",
            orientation='h',
            title=f"Ranking atual de {selected_indicator}",
            template="plotly_white",
            color_discrete_sequence=["#D50032"],  # Rosa padrão
            text="value"
        )
        
        fig_rank.update_traces(
            texttemplate='%{text:.2f}',
            textposition='outside'
        )
        
        fig_rank.update_layout(
            yaxis_title="",
            xaxis_title="Valor",
            height=500,
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_rank, use_container_width=True)

        
        # Tabela de ranking
        rank_table = latest_values[["country", "value", "date"]].copy()
        rank_table["Ranking"] = range(1, len(rank_table) + 1)
        rank_table = rank_table[["Ranking", "country", "value", "date"]]
        rank_table.columns = ["Ranking", "País", "Valor", "Data da Medição"]
        
        st.dataframe(
            rank_table,
            hide_index=True,
            use_container_width=True
        )
    
    with compare_tabs[2]:
        # Visualização em mapa
        geo_data = {
            "Argentina": (-38.416097, -63.616672),
            "Bolivia": (-16.290154, -63.588653),
            "Brazil": (-14.235004, -51.92528),
            "Chile": (-35.675147, -71.542969),
            "Colombia": (4.570868, -74.297333),
            "Ecuador": (-2.897533, -78.979733),
            "Guyana": (4.860416, -58.930180),
            "Paraguay": (-23.442503, -58.443833),
            "Peru": (-9.189967, -75.015152),
            "Suriname": (3.919305, -56.027783),
            "Uruguay": (-32.522779, -55.765835),
            "Venezuela": (6.423750, -66.589730)
        }
        
        # Filtrar apenas os países selecionados
        filtered_geo = {country: geo_data[country] for country in multi_countries if country in geo_data}
        
        # Verificar países sem dados
        countries_without_data = []
        countries_with_data = []
        
        for country in filtered_geo.keys():
            country_data = latest_values[latest_values['country'] == country]
            if len(country_data) == 0:
                countries_without_data.append(country)
            else:
                countries_with_data.append(country)
        
        if countries_without_data:
            st.error(f"❌ Erro: Os seguintes países não possuem dados disponíveis para este indicador: {', '.join(countries_without_data)}")
            st.stop()
        
        # Criar DataFrame apenas com países que têm dados
        map_df = pd.DataFrame({
            'country': countries_with_data,
            'lat': [lat for country, (lat, lon) in filtered_geo.items() if country in countries_with_data],
            'lon': [lon for country, (lat, lon) in filtered_geo.items() if country in countries_with_data],
            'value': [latest_values[latest_values['country'] == country]['value'].iloc[0] 
                     for country in countries_with_data]
        })
        # Filtrar valores nulos (NaN) para evitar erro no mapa
        map_df = map_df.dropna(subset=['value'])
        # Para o parâmetro size, só valores positivos e válidos
        map_df['size'] = pd.to_numeric(map_df['value'], errors='coerce')
        map_df.loc[map_df['size'] <= 0, 'size'] = None
        map_df = map_df.dropna(subset=['size'])
        
        # Criar mapa apenas com países que têm dados válidos
        fig_map = px.scatter_mapbox(
            map_df,
            lat="lat",
            lon="lon",
            size="size",
            color="value",
            color_continuous_scale="viridis",
            size_max=50,
            zoom=3,
            title="Distribuição Geográfica dos Valores",
            hover_name="country"
        )
        
        fig_map.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=0, r=0, t=50, b=0)
        )
        st.plotly_chart(fig_map, use_container_width=True)


    with compare_tabs[3]:
        # Análise estatística comparativa
        pivot_data = multi_data.pivot_table(
            index="date",
            columns="country",
            values="value"
        ).reset_index()
        
        st.dataframe(
            pivot_data,
            use_container_width=True,
            height=500
        )
        
        # Download dos dados
        st.download_button(
            label="Baixar dados comparativos (CSV)",
            data=pivot_data.to_csv(index=False).encode('utf-8'),
            file_name=f"comparacao_{selected_indicator}.csv",
            mime="text/csv"
        )
    
    # Correlação entre indicadores
    with compare_tabs[4]:
        st.markdown("### Matriz de Correlação dos Indicadores Econômicos")
        # Selecionar indicadores para correlação
        corr_indicators = [col for col in df.columns if col not in ['country', 'date']]
        corr_df = multi_data.pivot_table(index=["country", "date"], values="value").reset_index()
        corr_df = df[df["country"].isin(multi_countries)].copy()
        corr_matrix = corr_df[corr_indicators].corr()
        import plotly.express as px
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale="RdBu",
            title="Correlação entre Indicadores Econômicos"
        )
        st.plotly_chart(fig_corr, use_container_width=True)

# Rodapé com informações técnicas
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Fonte de Dados")
    st.markdown("World Bank API - Indicadores Econômicos da América do Sul")

with col2:
    st.markdown("### Metodologia")
    st.markdown("Coleta automatizada e processamento com Python/Pandas")

with col3:
    st.markdown("### Atualização")
    st.markdown(f"Automática a cada hora (última: {current_time})")

# Expandir para informações detalhadas sobre os indicadores
with st.expander("ℹ️ Informações sobre os Indicadores"):
    indicators_info = {
        "NY.GDP.MKTP.CD": "**PIB (US$ atual)** - Produto Interno Bruto em dólares americanos correntes.",
        "FP.CPI.TOTL.ZG": "**Inflação (% anual)** - Variação percentual anual do índice de preços ao consumidor.",
        "FR.INR.RINR": "**Taxa de juros real (%)** - Taxa de juros ajustada pela inflação medida pelo deflator do PIB.",
        "SL.UEM.TOTL.ZS": "**Desemprego (% força de trabalho)** - Porcentagem da força de trabalho que está sem trabalho, mas disponível e buscando emprego.",
        "PA.NUS.FCRF": "**Taxa de câmbio (LCU por US$)** - Taxa de câmbio oficial determinada pela autoridade nacional."
    }
    
    for ind_code, ind_desc in indicators_info.items():
        st.markdown(f"**{ind_code}**: {ind_desc}")
