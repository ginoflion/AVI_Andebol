import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

st.set_page_config(page_title="Scouting Guarda-Redes", layout="wide", page_icon="🧤")

st.title("Dashboard de Performance: Guarda-Redes")
st.markdown("---")

#CARREGAR DADOS
@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv('dataset_guarda_redes_v2.csv')
        if 'session_date' in df.columns:
            df['session_date'] = pd.to_datetime(df['session_date'])
        return df
    except FileNotFoundError:
        return None

df = carregar_dados()

if df is None:
    st.error("Ficheiro 'dataset_guarda_redes_v2.csv' não encontrado!")
    st.stop()

df_games = df[df['session_type'] == 'GAME'].copy()

#FILTROS 
st.sidebar.header("Filtros")
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ("Por Adversário (Agregado)", "Por Jogo Individual")
)

df_filtrado = pd.DataFrame()
titulo_heatmap = ""
is_aggregated_view = False
opcao_geral_selecionada = False

if modo_analise == "Por Adversário (Agregado)":
    is_aggregated_view = True
    oponentes = sorted(df_games['opponent'].dropna().unique().tolist())
    oponentes.insert(0, "Geral (Todos os Jogos)")
    
    escolha_oponente = st.sidebar.selectbox("Selecionar Adversário:", oponentes)
    
    if escolha_oponente == "Geral (Todos os Jogos)":
        df_filtrado = df_games
        titulo_heatmap = "Geral (Todos os Jogos)"
        opcao_geral_selecionada = True
    else:
        df_filtrado = df_games[df_games['opponent'] == escolha_oponente]
        titulo_heatmap = f"vs {escolha_oponente} (Total Época)"

else:
    lista_jogos = df_games[['session_id', 'session_date', 'opponent']].drop_duplicates().sort_values('session_date')
    lista_jogos['label'] = lista_jogos['session_date'].dt.strftime('%Y-%m-%d') + " | " + lista_jogos['opponent']
    mapa_jogos = dict(zip(lista_jogos['label'], lista_jogos['session_id']))
    
    escolha_jogo = st.sidebar.selectbox("Selecionar Jogo:", lista_jogos['label'])
    id_sessao = mapa_jogos[escolha_jogo]
    
    df_filtrado = df_games[df_games['session_id'] == id_sessao]
    titulo_heatmap = f"Jogo: {escolha_jogo}"


if df_filtrado.empty:
    st.warning("Não foram encontrados dados para esta seleção.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
total_remates = len(df_filtrado)
golos = len(df_filtrado[df_filtrado['outcome'] == 'GOAL'])
defesas = len(df_filtrado[df_filtrado['outcome'] == 'SAVE'])
eficacia_global = (defesas / total_remates * 100) if total_remates > 0 else 0

col1.metric("Total Remates", total_remates)
col2.metric("Golos Sofridos", golos, delta_color="inverse")
col3.metric("Defesas", defesas, delta_color="normal")
col4.metric("Eficácia Global", f"{eficacia_global:.1f}%")

st.markdown("---")
#VISUALIZAÇÃO BALIZA
col_heat, col_quad = st.columns(2)

with col_heat:
    st.subheader(f"Mapa de Calor (Baliza)")
    df_golos = df_filtrado[df_filtrado['outcome'] == 'GOAL']
    if len(df_golos) < 3:
        st.info("Dados insuficientes.")
    else:
        fig_s, ax_s = plt.subplots(figsize=(8, 5))
        ax_s.add_patch(plt.Rectangle((0,0), 3, 2, facecolor='#f9f9f9', alpha=0.5))
        sns.kdeplot(x=df_golos['target_y'], y=df_golos['target_z'], fill=True, cmap='Reds', thresh=0.05, alpha=0.8, clip=((0, 3), (0, 2)), ax=ax_s)
        ax_s.plot([0,0],[0,2], c='k', lw=4); ax_s.plot([3,3],[0,2], c='k', lw=4); ax_s.plot([0,3],[2,2], c='k', lw=4)
        ax_s.set_xlim(-0.2, 3.2); ax_s.set_ylim(-0.1, 2.2); ax_s.axis('off')
        st.pyplot(fig_s)

with col_quad:
    st.subheader("Eficácia por Zona")
    fig_q, ax_q = plt.subplots(figsize=(8, 5))
    ax_q.plot([0,0],[0,2], c='k', lw=4); ax_q.plot([3,3],[0,2], c='k', lw=4); ax_q.plot([0,3],[2,2], c='k', lw=4)
    for x in [1, 2]: ax_q.plot([x,x], [0,2], 'gray', ls='--', alpha=0.5)
    for y in [2/3, 4/3]: ax_q.plot([0,3], [y,y], 'gray', ls='--', alpha=0.5)
    
    y_bins, z_bins = [0, 1, 2, 3], [0, 2/3, 4/3, 2]
    for z in range(3):
        for y in range(3):
            mask = (df_filtrado['target_y']>=y_bins[y]) & (df_filtrado['target_y']<y_bins[y+1]) & \
                   (df_filtrado['target_z']>=z_bins[z]) & (df_filtrado['target_z']<z_bins[z+1])
            d = df_filtrado[mask]
            g=len(d[d['outcome']=='GOAL']); tot=len(d)
            pct=(g/tot*100) if tot>0 else 0
            color='darkred' if pct>50 else 'darkgreen'
            txt = f"{pct:.0f}%\n(G:{g})" if tot>0 else "-"
            ax_q.text(y+0.5, z_bins[z]+0.33, txt, ha='center', va='center', color=color, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    ax_q.set_xlim(-0.2, 3.2); ax_q.set_ylim(-0.1, 2.2); ax_q.axis('off')
    st.pyplot(fig_q)

st.markdown("---")


#MATRIZ DE EFICÁCIA
if is_aggregated_view:
    st.subheader("Matriz de Eficácia: Jogo vs Tipo de Remate")
    
    df_filtrado['Game_Label'] = df_filtrado['session_date'].dt.strftime('%d/%m') + '\n' + df_filtrado['opponent']
    
    heatmap_data = df_filtrado.groupby(['Game_Label', 'session_date', 'shot_type']).apply(
        lambda x: (len(x[x['outcome'] == 'SAVE']) / len(x) * 100) if len(x) > 0 else 0
    ).reset_index(name='Eficacia')

    if not heatmap_data.empty:
        heatmap_matrix = heatmap_data.pivot(index='shot_type', columns='Game_Label', values='Eficacia')
        
        sorted_labels = df_filtrado.sort_values('session_date')['Game_Label'].unique()
        heatmap_matrix = heatmap_matrix.reindex(columns=sorted_labels)
        
        eixo_x_label = ""
        if opcao_geral_selecionada:
            heatmap_matrix.columns = [str(i+1) for i in range(len(heatmap_matrix.columns))]
            eixo_x_label = "Sequência de Jogos da Época"
        else:
            eixo_x_label = "Jogos (Data / Adversário)"

        cmap_saturado = mcolors.LinearSegmentedColormap.from_list("", ["#FF0000","#FF9100", "#FFFF00","#53CE2E", "#00A300"])

        fig_mat, ax_mat = plt.subplots(figsize=(15, 5))
        sns.heatmap(
            heatmap_matrix, 
            cmap=cmap_saturado, 
            annot=False,       
            fmt=".0f",       
            vmin=0, vmax=100, 
            linewidths=1,      
            linecolor='white',
            ax=ax_mat
        )
        
        ax_mat.set_xlabel(eixo_x_label)
        ax_mat.set_ylabel("Tipo de Remate")
        plt.xticks(rotation=0) 
        st.pyplot(fig_mat)
    else:
        st.info("Sem dados suficientes para gerar a matriz.")
    
    st.markdown("---")


#FISIOLOGIA
st.subheader("Fisiologia e Tempo de Reação")
df_sorted = df_filtrado.sort_values('game_minute')
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Evolução do Cansaço (BPM)**")
    if not df_sorted.empty:
        fig, ax = plt.subplots(figsize=(8, 3))
        sns.lineplot(data=df_sorted, x='game_minute', y='heart_rate', color='tab:red', ax=ax)
        ax.set_xlabel("Minuto"); ax.set_ylabel("BPM"); ax.grid(True, alpha=0.3)
        st.pyplot(fig)

with c2:
    st.markdown("**Evolução dos Reflexos (ms)**")
    if not df_sorted.empty:
        fig, ax = plt.subplots(figsize=(8, 3))
        sns.lineplot(data=df_sorted, x='game_minute', y='reaction_time_ms', color='tab:blue', ax=ax)
        ax.set_xlabel("Minuto"); ax.set_ylabel("ms"); ax.grid(True, alpha=0.3)
        st.pyplot(fig)

st.markdown("---")



#ANÁLISE POR TIPO DE REMATE
st.subheader("Análise Detalhada (Ranking e Volume)")
c_bar, c_scat = st.columns(2)

if not df_filtrado.empty:
    df_stats = df_filtrado.groupby('shot_type').apply(
        lambda x: pd.Series({
            'Total': len(x),
            'Defesas': len(x[x['outcome'] == 'SAVE']),
            'Eficacia': (len(x[x['outcome'] == 'SAVE']) / len(x) * 100) if len(x) > 0 else 0,
            'ReactionMean': x['reaction_time_ms'].mean()
        })
    ).reset_index().sort_values('Eficacia', ascending=False)

    with c_bar:
        st.markdown("**Ranking de Eficácia (%)**")
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=df_stats, x='shot_type', y='Eficacia', palette='Blues_r', ax=ax)
        ax.set_ylim(0, 100); ax.set_ylabel("% Eficácia")
        for c in ax.containers: ax.bar_label(c, fmt='%.0f%%')
        st.pyplot(fig)

    with c_scat:
        st.markdown("**Volume vs. Eficácia**")
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.scatterplot(
            data=df_stats, 
            x='Total', y='Eficacia', hue='shot_type', size='Total', sizes=(100, 400),
            palette='viridis', ax=ax
        )
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, title="Tipo")
        ax.set_xlabel("Volume"); ax.set_ylabel("Eficácia (%)")
        ax.set_ylim(-5, 110); ax.set_xlim(0, df_stats['Total'].max() * 1.2)
        ax.grid(True, ls='--', alpha=0.5)
        st.pyplot(fig)

    st.markdown("**Rapidez de Reação (200-500ms)**")
    fig, ax = plt.subplots(figsize=(10, 3))
    sns.barplot(data=df_stats.sort_values('ReactionMean'), x='shot_type', y='ReactionMean', palette='viridis', ax=ax)
    ax.set_ylim(200, 500); ax.set_ylabel("ms"); ax.set_xlabel("")
    for c in ax.containers: ax.bar_label(c, fmt='%.0f ms')
    st.pyplot(fig)

with st.expander("Dados Brutos"):
    st.dataframe(df_filtrado.sort_values('game_minute'))