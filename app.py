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
    elif indicator_code == "RISK_SCORE":  # Score de risco
        # Formatar o score de risco como um valor de 0-100 com uma casa decimal
        return f"{value:.1f}"
    else:
        return f"{value:.2f}"

# Função para calcular o score de risco de investimento
def calculate_risk_score(df, country):
    """
    Calcula um score de risco de investimento para um país baseado em vários indicadores econômicos.
    
    Parâmetros:
    df (DataFrame): DataFrame completo com todos os indicadores
    country (str): Nome do país para calcular o score
    
    Retorna:
    float: Score de risco entre 0 (menor risco) e 100 (maior risco)
    """
    try:
        # Filtrar dados do país
        country_data = df[df["country"] == country].copy()
        
        if country_data.empty:
            return None
        
        # Pegar os valores mais recentes de cada indicador
        latest_data = country_data.sort_values("date").groupby("country").last().reset_index()
        
        # Coletar todos os dados mais recentes de todos os países para comparação
        all_countries_latest = df.sort_values("date").groupby("country").last().reset_index()
        
        # Definir os pesos para cada indicador no cálculo de risco
        # Indicadores positivos (quanto maior, menor o risco)
        # Indicadores negativos (quanto maior, maior o risco)
        weights = {
            "NY.GDP.MKTP.CD": -0.25,    # PIB: maior PIB = menor risco (-)
            "FP.CPI.TOTL.ZG": 0.35,    # Inflação: maior inflação = maior risco (+) - Peso aumentado
            "FR.INR.RINR": 0.15,       # Taxa de juros real: maior taxa = maior risco (+)
            "SL.UEM.TOTL.ZS": 0.25,   # Desemprego: maior desemprego = maior risco (+)
            "PA.NUS.FCRF": 0.0        # Taxa de câmbio: neutro (0)
        }
        
        # Inicializar score com valor base mais baixo
        score = 35  # Valor base mais baixo para aumentar a dispersão
        used_weights = 0
        total_impact = 0
        
        # Calcular percentis para cada indicador
        percentiles = {}
        for indicator in weights.keys():
            if indicator in df.columns:
                # Classificar os países pelo indicador (sem valores nulos)
                valid_values = all_countries_latest[all_countries_latest[indicator].notna()]
                
                if not valid_values.empty:
                    if indicator == "NY.GDP.MKTP.CD":  # PIB (invertido - menor PIB = maior risco)
                        sorted_data = valid_values.sort_values(indicator, ascending=True)
                    else:  # Outros indicadores (maior valor = maior risco)
                        sorted_data = valid_values.sort_values(indicator, ascending=False)
                    
                    # Criar um ranking normalizado (0-100)
                    n_countries = len(sorted_data)
                    ranks = pd.Series(range(n_countries), index=sorted_data["country"])
                    percentiles[indicator] = (ranks / max(1, n_countries - 1)) * 100  # Evitar divisão por zero
        
        # Calcular score com base em percents e valores extremos
        for indicator, weight in weights.items():
            if indicator in latest_data.columns and not pd.isna(latest_data[indicator].iloc[0]):
                value = latest_data[indicator].iloc[0]
                country_val = latest_data["country"].iloc[0]
                
                # Verificar casos extremos diretos - indicadores críticos
                # Inflação muito alta - risco muito elevado
                if indicator == "FP.CPI.TOTL.ZG" and value > 50:
                    direct_impact = min((value - 50) * 0.8, 45)  # Até +45 pontos para inflação extrema
                    score += direct_impact
                    total_impact += abs(direct_impact)
                # Desemprego muito alto - risco elevado
                elif indicator == "SL.UEM.TOTL.ZS" and value > 15:
                    direct_impact = min((value - 15) * 2, 25)  # Até +25 pontos para desemprego extremo
                    score += direct_impact
                    total_impact += abs(direct_impact)
                # PIB muito baixo - risco elevado (PIB em US$)
                elif indicator == "NY.GDP.MKTP.CD" and value < 1e11:  # Menos de 100 bilhões
                    # Escala logarítmica para PIB baixo
                    log_val = np.log10(max(value, 1e8) / 1e11)  # max com 1e8 para evitar log(0)
                    direct_impact = min(-log_val * 10, 30)  # Até +30 pontos para PIB baixo
                    score += direct_impact
                    total_impact += abs(direct_impact)
                
                # Usar percents se disponíveis
                if indicator in percentiles and country_val in percentiles[indicator].index:
                    percentile = percentiles[indicator][country_val]
                    
                    # Aplicar o peso ao percentil (0-100)
                    if indicator == "NY.GDP.MKTP.CD":
                        # Para PIB, menor percentil (maior PIB) = menor risco
                        impact = percentile * weight  # Já está com sinal negativo no peso
                    else:
                        # Para outros, maior percentil = maior risco
                        impact = percentile * weight
                    
                    score += impact
                    total_impact += abs(impact)
                    used_weights += abs(weight)
        
        # Aplicar ajustes finais para casos específicos de países
        # Venezuela tem condições econômicas extremas
        if country == "Venezuela":
            score += 30  # Adicionar um bom risco adicional para Venezuela
        # Ajuste para países estáveis
        elif country in ["Chile", "Uruguay"]:
            score -= 15  # Reduzir o risco para países economicamente mais estáveis
        # Brasil - ajuste moderado
        elif country == "Brazil":
            score -= 5  # Brasil tem grande economia mas problemas estruturais
        
        # Garantir que o score esteja no intervalo [0, 100]
        score = max(min(score, 100), 0)
        
        return score
    
    except Exception as e:
        print(f"Erro ao calcular score de risco para {country}: {str(e)}")
        return None
    

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
from streamlit_option_menu import option_menu

with st.sidebar:
    st.markdown("""
        <div style='color:#f2f2f7; font-family:sans-serif; font-size:1.3em; font-weight:600; margin-bottom:6px; letter-spacing:0.5px;'>
            Navegação
        </div>
        <hr style='margin: 0 0 15px 0; border-top: 1px solid #111;'>
    """, unsafe_allow_html=True)
    selected_menu = option_menu(
        None,  # Remove o título do menu
        ["País único", "Comparação entre países"],
        icons=["bar-chart-line", "people"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "rgba(0,0,0,0)"},
            "icon": {"color": "#fff", "font-size": "16px"},
            "nav-link": {
                "text-align": "left",
                "margin": "0px",
                "color": "#c7c7cc",
                "padding": "14px 8px",
                "background-color": "rgba(0,0,0,0)",
            },
            "nav-link-selected": {
                "background-color": "#4d4d5c",
                "color": "#fff"
            },
            "nav-link:hover": {
                "background-color": "#232946",
                "color": "#fff"
            }
        }
    )
    st.markdown("<hr style='margin: 10px 0 15px 0; border-top: 1px solid #111;'>", unsafe_allow_html=True)
    st.header("Filtros e Controles")
    # Seleção de indicador comum para ambos os modos
    selected_indicator = st.selectbox("Selecione o indicador", indicator_columns)

# O menu controla o modo de visualização
if selected_menu == "País único":
    viz_mode = "País único"
elif selected_menu == "Comparação entre países":
    viz_mode = "Comparação entre países"
else:
    viz_mode = "Sobre"

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
        st.error(f"❌ Não existem dados disponíveis no momento para o país: **{selected_country}**.")
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
            color_discrete_sequence=[
                "#D50032", # vermelho vivo
                "#1e88e5", # azul tema
                "#ffe600", # amarelo tema
                "#43a047", # verde
                "#8e24aa", # roxo
                "#f4511e", # laranja
                "#3949ab", # azul escuro
                "#00bcd4", # turquesa
                "#ff9800", # laranja vivo
                "#c2185b", # magenta
                "#388e3c"  # verde escuro
            ],
            hover_data={
                "inicio": True,
                "fim": True,
                "presidente": True
            }
        )
        fig_timeline.update_yaxes(autorange="reversed")
        fig_timeline.update_traces(
            opacity=0.95,
            marker_line_width=0  # Remove contorno das barras
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
            ),
            dragmode='zoom',
            hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
            modebar=dict(orientation='v')
        )
        fig_timeline.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
        fig_timeline.update_traces(opacity=0.95)
        # Removido: não adicionar labels de datas nos extremos para deixar só as barras
        st.plotly_chart(fig_timeline, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})

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
            font=dict(color="#f2f2f7"),
            dragmode='zoom',
            hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
            xaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            yaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            modebar=dict(orientation='v')
        )
        fig.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})

        # Comparação com Média Regional
        # Calcular média regional por data (excluindo o país selecionado da média)
        regional_mean = df[df['country'] != selected_country].groupby('date')[selected_indicator].mean().reset_index()
        regional_mean = regional_mean.rename(columns={selected_indicator: 'Média Regional'})
        # Dados do país
        pais_data = country_data[['date', 'value']].rename(columns={'value': selected_country})
        # Unir país e média regional
        comp_df = pd.merge(pais_data, regional_mean, on='date', how='inner')
        # Exibir gráfico apenas se houver dados válidos
        if not comp_df.empty and comp_df[selected_country].notna().any() and comp_df['Média Regional'].notna().any():
            import plotly.graph_objects as go
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(
                x=comp_df['date'], y=comp_df[selected_country], mode='lines+markers', name=selected_country,
                line=dict(color='#D50032', width=3)
            ))
            fig_comp.add_trace(go.Scatter(
                x=comp_df['date'], y=comp_df['Média Regional'], mode='lines+markers', name='Média Regional',
                line=dict(color='#43a047', width=3, dash='dash')
            ))
            fig_comp.update_layout(
                title=f"{selected_indicator}: {selected_country} vs. Média Regional",
                xaxis_title='Data',
                yaxis_title='Valor',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(0,0,0,0)'),
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f2f2f7")
            )
            st.plotly_chart(fig_comp, use_container_width=True, key="pais_vs_regional")
        else:
            st.info(f"Não há dados suficientes para comparar {selected_country} com a média regional neste indicador.")

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
                height=350,
                dragmode='zoom',
                hovermode='closest',
                hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
                xaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
                yaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
                modebar=dict(orientation='v')
            )
            fig_hist.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
            st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]}, key="hist")

        

    
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
            
            # Calcular o score de risco de investimento
            risk_score = calculate_risk_score(df, selected_country)
            
            # Métrica principal do valor atualizado - ocupa toda a largura
            st.metric(
                "Valor mais atual",
                format_number(latest_value, selected_indicator),
                delta=format_number(latest_value - previous_value if previous_value else 0, selected_indicator),
                help=f"Ano da medição: {latest_year}"
            )
            
            # Espaço entre as métricas
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            
            # Exibir o score de risco com cor apropriada
            if risk_score is not None:
                if risk_score < 30:
                    risk_color = "green"
                    risk_label = "Baixo Risco"
                elif risk_score < 60:
                    risk_color = "orange"
                    risk_label = "Risco Moderado"
                else:
                    risk_color = "red"
                    risk_label = "Alto Risco"
                
                # Título e card do score de risco
                st.markdown(f"### Score de Risco de Investimento")
                st.markdown(
                    f"<div style='background-color: rgba(0,0,0,0.1); padding: 10px; border-radius: 5px; text-align: center;'>"
                    f"<h1 style='color: {risk_color}; margin: 0; font-size: 2.2rem;'>{risk_score:.1f}</h1>"
                    f"<p style='margin: 0; color: {risk_color};'>{risk_label}</p>"
                    f"</div>", unsafe_allow_html=True
                )
                
                # Adicionar uma mini barra de progresso
                st.progress(min(risk_score/100, 1.0))
                st.caption("0 = Menor risco, 100 = Maior risco")
            else:
                st.info("Dados insuficientes para calcular o score de risco.")
            
            # Espaço antes das estatísticas
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            
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
        st.error("❌ Não existem dados disponíveis no momento para os países selecionados.")
        st.stop()
    # Checar quais países não têm dados
    missing_countries = [c for c in multi_countries if c not in multi_data['country'].unique()]
    if missing_countries:
        st.warning(f"Os seguintes países não possuem dados disponíveis: **{', '.join(missing_countries)}**")
    
    # Visão por abas
    compare_tabs = st.tabs(["Comparação Temporal", "Ranking", "Mapa", "Score de Risco", "Análise Estatística", "Correlação"])
    
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
            legend_bgcolor='rgba(0,0,0,0)',
            dragmode='zoom',
            hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
            xaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            yaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            modebar=dict(orientation='v')
        )
        fig_compare.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
        st.plotly_chart(fig_compare, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})

        
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
                    legend_bgcolor='rgba(0,0,0,0)',
                    dragmode='zoom',
                    hovermode='closest',
                    hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
                    modebar=dict(orientation='v')
                )
                fig_corr.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
                fig_corr.update_layout(height=400)
                st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})
                
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
            dragmode='zoom',
            hovermode='closest',
            hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
            xaxis=dict(showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            yaxis=dict(categoryorder='total ascending', showspikes=False, spikemode='across', spikesnap='cursor', showline=True, showgrid=True, zeroline=False, showticklabels=True, spikecolor='#cccccc', spikethickness=0.35, spikedash='solid'),
            modebar=dict(orientation='v')
        )
        fig_rank.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
        st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})

        
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
            margin=dict(l=0, r=0, t=50, b=0),
            dragmode='zoom',
            hovermode='closest',
            hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
            modebar=dict(orientation='v')
        )
        fig_map.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline","drawopenpath","drawrect","drawcircle","eraseshape"]})

    with compare_tabs[3]:
        # Aba de Score de Risco
        st.markdown("### Score de Risco de Investimento por País")
        st.markdown("O score de risco é calculado com base em diversos indicadores econômicos e representa uma estimativa do risco relativo de investimento em cada país. Valores mais baixos indicam menor risco.")
        
        # Calcular score de risco para cada país
        risk_scores = []
        for country in multi_countries:
            score = calculate_risk_score(df, country)
            if score is not None:
                risk_scores.append({"country": country, "risk_score": score})
        
        # Criar DataFrame com os scores
        if risk_scores:
            risk_df = pd.DataFrame(risk_scores)
            risk_df = risk_df.sort_values("risk_score")
            
            # Definir cores conforme o nível de risco
            colors = []
            risk_categories = []
            for score in risk_df["risk_score"]:
                if score < 30:
                    colors.append("#4CAF50")  # Verde para baixo risco
                    risk_categories.append("Baixo Risco")
                elif score < 60:
                    colors.append("#FF9800")  # Laranja para risco moderado
                    risk_categories.append("Risco Moderado")
                else:
                    colors.append("#F44336")  # Vermelho para alto risco
                    risk_categories.append("Alto Risco")
            
            risk_df["category"] = risk_categories
            
            # Criar gráfico de barras horizontais
            fig_risk = px.bar(
                risk_df,
                y="country",
                x="risk_score",
                orientation="h",
                title="Score de Risco de Investimento por País",
                template="plotly_white",
                color="category",
                color_discrete_map={
                    "Baixo Risco": "#4CAF50",
                    "Risco Moderado": "#FF9800",
                    "Alto Risco": "#F44336"
                },
                category_orders={"category": ["Baixo Risco", "Risco Moderado", "Alto Risco"]},
                labels={"country": "País", "risk_score": "Score de Risco (0-100)", "category": "Categoria de Risco"}
            )
            
            fig_risk.update_layout(
                yaxis_title="",
                xaxis_title="Score de Risco (0-100)",
                xaxis=dict(range=[0, 100]),  # Fixar escala de 0 a 100
                height=500,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f2f2f7"),
                hoverlabel=dict(bgcolor="#232946", font_size=13, font_family="sans-serif"),
                modebar=dict(orientation='v')
            )
            
            fig_risk.update_traces(
                texttemplate='%{x:.1f}',
                textposition='outside'
            )
            
            fig_risk.update_layout(modebar_add=['zoom', 'pan', 'select', 'lasso2d', 'resetScale2d', 'toImage'])
            st.plotly_chart(fig_risk, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
            
            # Adicionar explicação da metodologia
            with st.expander("Entenda a metodologia do Score de Risco"):
                st.markdown("""
                ### Metodologia de Cálculo do Score de Risco
                
                O Score de Risco de Investimento é calculado com base em uma combinação ponderada de indicadores econômicos:
                
                - **PIB**: Quanto maior o PIB, menor é o risco de investimento (peso negativo)
                - **Inflação**: Quanto maior a inflação, maior é o risco (peso positivo)
                - **Taxa de Juros Real**: Taxas muito altas indicam maior risco (peso positivo)
                - **Desemprego**: Altos níveis de desemprego elevam o risco (peso positivo)
                
                Cada país é avaliado em comparação à média regional, e os desvios são ponderados conforme o impacto de cada indicador no risco de investimento.
                
                O score final é apresentado em uma escala de 0 a 100, onde:
                - **0-30**: Baixo risco de investimento
                - **30-60**: Risco moderado
                - **60-100**: Alto risco
                """)
            
            # Tabela de scores de risco com formatação condicional
            st.subheader("Detalhamento dos Scores de Risco")
            # Adicionar coluna formatada para score
            risk_df["score_formatted"] = risk_df["risk_score"].apply(lambda x: format_number(x, "RISK_SCORE"))
            display_df = risk_df[["country", "score_formatted", "category"]].rename(columns={"country": "País", "score_formatted": "Score", "category": "Categoria"})
            
            # Exibir tabela com formatação condicional
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Score": st.column_config.TextColumn(
                        "Score de Risco",
                        help="Score de 0 (menor risco) a 100 (maior risco)"
                    ),
                    "Categoria": st.column_config.TextColumn(
                        "Categoria de Risco",
                        help="Classificação do nível de risco"
                    )
                }
            )
        else:
            st.warning("Não foi possível calcular o score de risco para os países selecionados. Verifique se há dados suficientes disponíveis.")
    
    with compare_tabs[4]:
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

# Expandir para informações detalhadas sobre os indicadores e metodologia
with st.expander("ℹ️ Informações sobre os Indicadores"):
    indicators_info = {
        "NY.GDP.MKTP.CD": "**PIB (US$ atual)** - Produto Interno Bruto em dólares americanos correntes.",
        "FP.CPI.TOTL.ZG": "**Inflação (% anual)** - Variação percentual anual do índice de preços ao consumidor.",
        "FR.INR.RINR": "**Taxa de juros real (%)** - Taxa de juros ajustada pela inflação medida pelo deflator do PIB.",
        "SL.UEM.TOTL.ZS": "**Desemprego (% força de trabalho)** - Porcentagem da força de trabalho que está sem trabalho, mas disponível e buscando emprego.",
        "PA.NUS.FCRF": "**Taxa de câmbio (LCU por US$)** - Taxa de câmbio oficial determinada pela autoridade nacional.",
        "RISK_SCORE": "**Score de Risco de Investimento** - Índice composto que avalia o risco relativo de investimento com base em indicadores econômicos. Escala de 0 (menor risco) a 100 (maior risco)."
    }
    
    for ind_code, ind_desc in indicators_info.items():
        st.markdown(f"**{ind_code}**: {ind_desc}")

with st.expander("💸 Metodologia do Score de Risco de Investimento"):
    st.markdown("""
    ### Metodologia de Cálculo do Score de Risco
    
    O **Score de Risco de Investimento** é uma métrica personalizada desenvolvida para avaliar o risco relativo de investimento 
    em países da América do Sul. O modelo considera os seguintes fatores e seus pesos:
    
    | Indicador | Descrição | Peso | Impacto |
    | --- | --- | --- | --- |
    | PIB | Produto Interno Bruto | -0.30 | Negativo (maior PIB = menor risco) |
    | Inflação | Variação percentual anual do IPC | 0.25 | Positivo (maior inflação = maior risco) |
    | Taxa de Juros Real | Taxa ajustada pela inflação | 0.20 | Positivo (maior taxa = maior risco) |
    | Desemprego | % da força de trabalho sem emprego | 0.25 | Positivo (maior desemprego = maior risco) |
    
    #### Cálculo do Score
    
    1. Para cada indicador, calculamos o desvio percentual do país em relação à média regional
    2. Aplicamos os pesos a esses desvios (limitando o impacto máximo)
    3. Somamos a um valor base (50) para obter um score entre 0 e 100
    
    #### Interpretação
    
    - **0-30**: Baixo risco de investimento
    - **30-60**: Risco moderado
    - **60-100**: Alto risco
    
    *Nota: Este score é uma medida relativa e deve ser usado como uma ferramenta de comparação entre países, não como uma avaliação absoluta de risco.*
    """)

