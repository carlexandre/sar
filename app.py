import streamlit as st
import streamlit.components.v1 as components
import os
import requests
import re
import urllib3
import base64
import time
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from datetime import date, timedelta
import pandas as pd
from gerador_relatorio import criar_pdf_completo
import database as db

# Garante que a pasta de PDFs exista
PASTA_PDFS = "pdfs_gerados"
if not os.path.exists(PASTA_PDFS):
    os.makedirs(PASTA_PDFS)

# Configuração da Página
st.set_page_config(page_title="SAR | PoP-CE", layout="wide", page_icon="assets/favicon/icons8-relatório-100.png")

# --- 1. INJEÇÃO DE CSS E ÍCONES (FONT AWESOME) ---
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Puxa a aplicação completamente para o topo */
    .block-container {
        padding-top: 2.5rem !important; 
        padding-bottom: 2rem !important;
    }

    /* CARDS DA HOME (Blocos Totalmente Clicáveis) */
    .card-link {
        text-decoration: none !important;
        display: block;
        color: inherit !important;
        height: 100%;
    }
    .card-container {
        border: 1px solid rgba(128, 128, 128, 0.3);
        border-radius: 0.75rem;
        padding: 2.5rem 1.5rem;
        text-align: center;
        background-color: var(--secondary-background-color);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .card-link:hover .card-container {
        transform: translateY(-5px) scale(1.02);
        border-color: var(--primary-color);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    .card-icon {
        font-size: 55px;
        margin-bottom: 20px;
    }
    .card-icon.pdf { color: #E74C3C; }
    .card-icon.net { color: #3498DB; }
    .card-icon.hist { color: #F39C12; }
    
    .card-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 10px;
        color: var(--text-color);
    }
    .card-desc {
        color: var(--text-color);
        font-size: 0.95rem;
        opacity: 0.75;
        margin: 0;
        line-height: 1.4;
    }
    
    /* Estilização da Navbar Customizada - Colada no Topo */
    .custom-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        margin-top: -10px; 
    }
    
    /* Ícone de Ajuda (i) na Navbar */
    .info-icon {
        color: var(--text-color);
        font-size: 1.3rem;
        opacity: 0.4;
        transition: all 0.2s ease;
        text-decoration: none !important;
        display: flex;
        align-items: center;
        cursor: pointer;
        margin-top: 5px;
    }
    .info-icon:hover {
        opacity: 1;
        color: var(--primary-color);
        transform: scale(1.1);
    }

    /* MODAL DE AJUDA 100% CSS (Dispara via checkbox oculta) */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    #modal-toggle:checked ~ .modal-overlay {
        opacity: 1;
        visibility: visible;
    }
    .modal-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        cursor: default;
    }
    .modal-content {
        background-color: #ffffff; /* Força o branco absoluto no tema light */
        padding: 30px 40px;
        border: 1px solid rgba(128,128,128,0.3);
        border-radius: 12px;
        width: 90%;
        max-width: 700px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        position: relative;
        z-index: 2;
        transform: scale(0.95) translateY(-20px);
        transition: transform 0.3s ease;
        max-height: 90vh;
        overflow-y: auto;
    }
    
    #modal-toggle:checked ~ .modal-overlay .modal-content {
        transform: scale(1) translateY(0);
    }
    .modal-close {
        position: absolute;
        top: 15px;
        right: 20px;
        font-size: 28px;
        font-weight: bold;
        color: var(--text-color);
        opacity: 0.4;
        cursor: pointer;
        transition: 0.2s;
        line-height: 1;
    }
    .modal-close:hover {
        opacity: 1;
        color: #E74C3C;
    }
    .modal-body p, .modal-body ul {
        color: var(--text-color);
        opacity: 0.85;
        line-height: 1.6;
        font-size: 15px;
    }
    .modal-body h4 {
        color: var(--text-color);
        margin-top: 25px;
        margin-bottom: 10px;
    }

    /* LOGOS E RESPONSIVIDADE NATIVA */
    .nav-logo {
        height: 35px; /* Reduzido para ficar do mesmo tamanho do texto SAR */
        width: auto;
        object-fit: contain; 
    }
    .logo-light { display: none; }
    .logo-dark { display: block; }
    
    @media (prefers-color-scheme: light) {
        .logo-light { display: block; }
        .logo-dark { display: none; }
    }

    .nav-text {
        display: flex;
        align-items: baseline;
        gap: 12px;
    }
    .nav-title {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 0;
        line-height: 1;
        letter-spacing: -1px;
        color: var(--text-color);
    }
    .nav-subtitle {
        font-size: 1rem;
        font-weight: 500;
        color: var(--text-color);
        opacity: 0.6;
        letter-spacing: 1px;
    }
    
    /* Remove o sublinhado do link da Navbar */
    .navbar-link {
        text-decoration: none !important;
        color: inherit !important;
        display: block;
        width: 100%;
    }
    .navbar-link:hover {
        opacity: 0.9;
    }

    /* BOTÃO VOLTAR */
    .btn-voltar {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 6px;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.2s ease;
        background-color: var(--secondary-background-color);
        color: var(--text-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.4);
    }
    .btn-voltar:hover {
        background-color: var(--text-color);
        color: var(--background-color) !important;
        border-color: var(--text-color);
    }
    
    /* ESTILIZAÇÃO DA LISTA DE GRUPOS (EXPANDERS INTERATIVOS) */
    [data-testid="stExpander"] {
        border: 1px solid rgba(128,128,128, 0.2);
        border-radius: 8px;
        margin-bottom: 10px;
        background-color: transparent;
        opacity: 0.65; 
        transition: all 0.3s ease;
    }
    [data-testid="stExpander"]:hover {
        opacity: 1; 
        border-color: var(--primary-color);
        background-color: var(--secondary-background-color);
        transform: translateX(5px); 
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
    }
    
    /* ESTILIZAÇÃO DAS TABS (NAVBAR INTERNA DE CADASTRO/EDIÇÃO) */
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 1.5. HACK JS: HISTÓRICO E TEMA INTELIGENTE ---
components.html(
    """
    <script>
    // 1. Corrige o botão voltar do navegador
    window.parent.addEventListener('popstate', function(event) {
        window.parent.location.reload();
    });

    // 2. Observer de Tema do Streamlit (Detecta toggles manuais no Menu do site)
    function syncTheme() {
        try {
            var parentDoc = window.parent.document;
            var stApp = parentDoc.querySelector('.stApp');
            if (!stApp) return;
            
            var bgColor = window.getComputedStyle(stApp).backgroundColor;
            var rgba = bgColor.match(/[0-9]+/g);
            if (rgba) {
                var brightness = (parseInt(rgba[0]) * 299 + parseInt(rgba[1]) * 587 + parseInt(rgba[2]) * 114) / 1000;
                var lightLogos = parentDoc.querySelectorAll('.logo-light');
                var darkLogos = parentDoc.querySelectorAll('.logo-dark');
                var modalContents = parentDoc.querySelectorAll('.modal-content');
                
                if (brightness > 125) { 
                    lightLogos.forEach(el => el.style.display = 'block');
                    darkLogos.forEach(el => el.style.display = 'none');
                    modalContents.forEach(el => {
                        el.style.backgroundColor = '#ffffff';
                        el.style.boxShadow = '0 10px 40px rgba(0,0,0,0.3)';
                    });
                } else { 
                    lightLogos.forEach(el => el.style.display = 'none');
                    darkLogos.forEach(el => el.style.display = 'block');
                    modalContents.forEach(el => {
                        el.style.backgroundColor = '#0e1117';
                        el.style.boxShadow = '0 10px 40px rgba(0,0,0,0.8)';
                    });
                }
            }
        } catch (e) {}
    }
    
    syncTheme();
    setInterval(syncTheme, 500); 
    </script>
    """,
    height=0, width=0
)

# --- 2. CONTROLE DE ESTADO E URL (ROTEAMENTO) ---
page = st.query_params.get("page", "Home")

def ir_para(pagina):
    st.query_params["page"] = pagina

# --- 3. CONEXÃO E FUNÇÕES AUXILIARES ---
@st.cache_resource
def connect_zabbix():
    load_dotenv()
    ZABBIX_URL = os.getenv("ZABBIX_URL")
    ZABBIX_USER = os.getenv("ZABBIX_USER")
    ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD")
    CERT_PATH = "zabbix-certificado.crt" 
    
    if not all([ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD]):
        return None

    session = requests.Session()
    if os.path.exists(CERT_PATH):
        session.verify = CERT_PATH
    else:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session.verify = False
    
    try:
        zapi = ZabbixAPI(ZABBIX_URL, session=session)
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        return zapi
    except Exception as e:
        st.error(f"ERRO FATAL DE CONEXÃO COM O ZABBIX: {e}")
        return None

def limpar_nome_host(nome_bruto):
    nome = nome_bruto.replace(" -- GIGAFOR", "").replace(" -- RNP", "")
    nome = re.sub(r'^RG\d+\s+-\s+', '', nome)
    return nome

@st.cache_data(ttl=300, show_spinner=False)
def get_hosts(_zapi):
    return _zapi.host.get(output=['hostid', 'name'], sortfield='name')

@st.cache_data(ttl=300, show_spinner=False)
def get_items(_zapi, host_id):
    return _zapi.item.get(
        hostids=host_id,
        output=['itemid', 'name', 'key_'],
        search={'name': 'Interface'}, 
        sortfield='name'
    )

zapi = connect_zabbix()

# ==========================================
# JANELAS MODAIS (DIALOGS DE CONFIRMAÇÃO)
# ==========================================
@st.dialog("⚠️ Confirmar Exclusão do Grupo")
def dialog_excluir_grupo(grupo_id, grupo_nome):
    st.warning(f"Você está prestes a excluir o grupo **{grupo_nome}**.")
    st.write("Esta ação removerá o grupo permanentemente do banco de dados.")
    
    col1, col2 = st.columns(2)
    if col1.button("Sim, excluir grupo", type="primary", use_container_width=True):
        try:
            with db.conectar() as conn:
                cursor = conn.cursor()
                # Verifica se existem links (instituições) atrelados a este grupo
                cursor.execute("SELECT count(*) FROM links WHERE grupo_id = ?", (grupo_id,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    st.error(f"Não é possível excluir. Existem {count} instituição(ões) vinculadas a este grupo.")
                else:
                    cursor.execute("DELETE FROM grupos WHERE id=?", (grupo_id,))
                    conn.commit()
                    st.success("Grupo excluído com sucesso!")
                    time.sleep(1.2)
                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir grupo: {e}")
            
    if col2.button("Cancelar", use_container_width=True):
        st.rerun()

@st.dialog("⚠️ Confirmar Exclusão da Instituição")
def dialog_excluir_instituicao(inst_id, inst_nome):
    st.warning(f"Você está prestes a excluir a instituição **{inst_nome}**.")
    st.write("Esta ação removerá a instituição do monitoramento e não poderá ser desfeita.")
    
    col1, col2 = st.columns(2)
    if col1.button("Sim, excluir instituição", type="primary", use_container_width=True):
        try:
            with db.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM links WHERE id=?", (inst_id,))
                conn.commit()
            st.success("Instituição excluída com sucesso!")
            time.sleep(1.2)
            st.rerun()
        except Exception as e:
            st.error("Não foi possível excluir. (Existem relatórios atrelados no histórico)")
            
    if col2.button("Cancelar", use_container_width=True):
        st.rerun()

# ==========================================
# NAVBAR (CABEÇALHO GLOBAL E MODAL HTML)
# ==========================================
def renderizar_navbar():
    caminho_preto = "assets/logo/pop-ce-logo-preto.png"
    caminho_branco = "assets/logo/pop-ce-logo-branca.png"
    
    b64_light = ""
    b64_dark = ""
    
    if os.path.exists(caminho_preto):
        with open(caminho_preto, "rb") as f:
            b64_light = base64.b64encode(f.read()).decode("utf-8")
    if os.path.exists(caminho_branco):
        with open(caminho_branco, "rb") as f:
            b64_dark = base64.b64encode(f.read()).decode("utf-8")
            
    # IMPORTANTE: Absolutamente nenhuma linha de HTML dentro dessa string
    # pode ter 4 ou mais espaços de indentação, senão o Streamlit transforma em bloco de código.
    html_navbar = f"""
<div class="custom-navbar">
<div style="display: flex; align-items: baseline; gap: 12px;">
<a href="?page=Home" target="_self" style="text-decoration: none; color: inherit;">
<span class="nav-title">SAR</span>
</a>
<span class="nav-subtitle">SISTEMA DE AUTOMATIZAÇÃO DE RELATÓRIOS</span>
<label for="modal-toggle" class="info-icon" title="Saiba mais / Ajuda" style="margin-top: 0;">
<i class="fa-solid fa-circle-info"></i>
</label>
</div>

<div class="logo-wrapper">
<a href="?page=Home" target="_self" style="text-decoration: none;">
<img src="data:image/png;base64,{b64_light}" class="nav-logo logo-light" onerror="this.style.display='none'">
<img src="data:image/png;base64,{b64_dark}" class="nav-logo logo-dark" onerror="this.style.display='none'">
</a>
</div>
</div>

<input type="checkbox" id="modal-toggle" style="display: none;">
<div class="modal-overlay">
<label for="modal-toggle" class="modal-backdrop"></label>
<div class="modal-content">
<label for="modal-toggle" class="modal-close">&times;</label>
<h3 style="margin-top: 0; color: var(--text-color);"><i class='fa-solid fa-circle-info' style='color: #3498DB; margin-right: 10px;'></i> Sobre o Sistema SAR</h3>
<div class="modal-body">
<p>O <strong>Sistema de Automatização de Relatórios (SAR)</strong> foi desenvolvido para simplificar e padronizar a extração de métricas de rede do monitoramento do PoP-CE.</p>

<h4><i class="fa-solid fa-layer-group" style="color: #E74C3C; margin-right: 8px;"></i> Como funciona cada aba?</h4>
<ul>
<li><strong>Gerar Relatório:</strong> O módulo principal. Permite selecionar uma instituição já cadastrada e definir um intervalo de datas. O sistema consulta a API do Zabbix automaticamente e monta um documento PDF formatado com gráficos limpos, picos de tráfego e resumo de quedas de link (downtime) desse período.</li>
<li><strong>Gerenciar Instituições:</strong> É o módulo de administração. Aqui você pode criar grupos (como GigaFOR, CDC, etc) e vincular o nome de uma instituição aos seus respectivos <code>Hosts</code> e <code>Interfaces</code> que já estão a ser monitorados lá dentro do Zabbix.</li>
<li><strong>Histórico:</strong> Mantém um acervo permanente de todos os relatórios em PDF que já foram gerados. Permite buscas e filtragens avançadas para realizar novos downloads instantâneos sem precisar consultar o Zabbix repetidas vezes.</li>
</ul>

<hr style="border-color: rgba(128,128,128,0.2); margin: 25px 0;">

<h4><i class="fa-solid fa-chart-pie" style="color: #2ECC71; margin-right: 8px;"></i> Entendendo o Relatório e as Interfaces</h4>
<p>Os relatórios gerados em PDF têm o objetivo de extrair de forma muito clara e visual o panorama de tráfego dos links conectados ao PoP-CE.</p>
<p><strong>O que as interfaces monitoradas representam?</strong><br>
Os gráficos desenhados e os cálculos de tráfego baseiam-se na leitura das <strong>interfaces de borda</strong> dos nossos equipamentos. Isto significa que os resultados de <em>Download</em> e <em>Upload</em> apresentados no documento refletem exatamente <strong>o quanto cada instituição está consumindo</strong> do seu link contratado ou disponibilizado, garantindo total transparência do uso efetivo da rede pela visão do PoP-CE.</p>
</div>
</div>
</div>
"""
    return html_navbar

st.markdown(renderizar_navbar(), unsafe_allow_html=True)
st.markdown("<hr style='margin-top: 15px; margin-bottom: 30px; border-color: #555; opacity: 0.3;'>", unsafe_allow_html=True)

# ==========================================
# ROTEAMENTO DE PÁGINAS
# ==========================================

if page == "Home":
    st.markdown("<h3 style='text-align: center; margin-bottom: 40px; color: var(--text-color);'>Selecione um Módulo</h3>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""
        <a href="?page=Gerar" target="_self" class="card-link">
            <div class="card-container">
                <i class='fa-solid fa-file-pdf card-icon pdf'></i>
                <div class='card-title'>Gerar Relatório</div>
                <p class='card-desc'>Consulte o tráfego do Zabbix e exporte o documento PDF formatado.</p>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <a href="?page=Cadastros" target="_self" class="card-link">
            <div class="card-container">
                <i class='fa-solid fa-network-wired card-icon net'></i>
                <div class='card-title'>Gerenciar Instituições</div>
                <p class='card-desc'>Gerencie as instituições, grupos e interfaces de monitoramento.</p>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <a href="?page=Historico" target="_self" class="card-link">
            <div class="card-container">
                <i class='fa-solid fa-folder-open card-icon hist'></i>
                <div class='card-title'>Histórico</div>
                <p class='card-desc'>Acesse o repositório de relatórios gerados anteriormente pelo sistema.</p>
            </div>
        </a>
        """, unsafe_allow_html=True)

elif page == "Gerar":
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown("<h3 style='margin-bottom: 20px;'><i class='fa-solid fa-file-pdf' style='color: #E74C3C; margin-right: 10px;'></i> Gerar Novo Relatório</h3>", unsafe_allow_html=True)
    with col_btn:
        st.markdown('<div style="text-align: right; margin-top: 5px;"><a href="?page=Home" target="_self" class="btn-voltar"><i class="fa-solid fa-arrow-left"></i> Voltar</a></div>', unsafe_allow_html=True)
    
    # Realiza a consulta SQL trazendo as instituições com o nome do grupo associado
    with db.conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.id, l.nome_instituicao, g.nome 
            FROM links l 
            LEFT JOIN grupos g ON l.grupo_id = g.id
        """)
        links_raw = cursor.fetchall()
    
    if not links_raw:
        st.info("Nenhuma Instituição cadastrada ainda. Vá para o módulo 'Gerenciar Instituições'.")
    elif not zapi:
        st.error("Sem conexão com o Zabbix. Verifique suas credenciais no .env.")
    else:
        # Coloca num DataFrame para facilitar os filtros e formata os sem grupo
        df_links = pd.DataFrame(links_raw, columns=["id", "nome", "grupo"])
        df_links["grupo"] = df_links["grupo"].fillna("Sem Grupo")
        
        st.markdown("#### <i class='fa-solid fa-filter' style='color: #3498DB; margin-right: 8px;'></i> Filtrar Instituições", unsafe_allow_html=True)
        col_busca, col_filtro = st.columns([2, 1])
        
        with col_busca:
            busca_inst = st.text_input("Pesquisar por nome da Instituição:", placeholder="Ex: UECE Itaperi...")
        with col_filtro:
            opcoes_grupos = ["Todos"] + sorted(list(df_links["grupo"].unique()))
            filtro_grupo = st.selectbox("Filtrar por Grupo:", options=opcoes_grupos)
            
        # Aplicação dos Filtros no Dataframe de Instituições
        if filtro_grupo != "Todos":
            df_links = df_links[df_links["grupo"] == filtro_grupo]
        if busca_inst:
            df_links = df_links[df_links["nome"].str.contains(busca_inst, case=False, na=False)]
            
        st.divider()

        col_link, col_data = st.columns([2, 1])
        
        with col_link:
            if df_links.empty:
                st.warning("Nenhuma instituição encontrada com os filtros atuais.")
                inst_id_selecionada = None
            else:
                # O Dicionário de opções com o formato "Grupo - Nome"
                opcoes_inst = {f"{row['grupo']} - {row['nome']}": row['id'] for _, row in df_links.iterrows()}
                # Caixa de Seleção com index=None deixa-a "vazia" inicialmente com a string placeholder
                inst_selecionada_nome = st.selectbox(
                    "Selecione a Instituição:", 
                    options=list(opcoes_inst.keys()),
                    index=None,
                    placeholder="Instituições"
                )
                inst_id_selecionada = opcoes_inst.get(inst_selecionada_nome) if inst_selecionada_nome else None
            
        with col_data:
            dt_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=30))
            dt_fim = st.date_input("Data Fim", value=date.today())
            
        st.divider()
        
        # Botão fica desativado (cinza) até que o utilizador selecione ativamente uma Instituição na caixa
        if st.button("Gerar Relatório e Salvar", type="primary", disabled=(not inst_id_selecionada)):
            with st.spinner("Conectando ao Zabbix, processando dados e desenhando o PDF..."):
                try:
                    with db.conectar() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str FROM links WHERE id = ?", (inst_id_selecionada,))
                        dados_link = cursor.fetchone()
                    
                    nome_inst, host_id, item_down, item_up, cap_str = dados_link
                    ts_from = int(pd.Timestamp(dt_inicio).timestamp())
                    ts_till = int(pd.Timestamp(dt_fim).timestamp()) + 86400 

                    def buscar_dados(api, item_id, t_from, t_till):
                        dados = api.history.get(itemids=[item_id], time_from=t_from, time_till=t_till, output='extend', history=3)
                        eh_tendencia = False
                        if not dados:
                            dados = api.trend.get(itemids=[item_id], time_from=t_from, time_till=t_till, output=['clock', 'value_avg', 'value_max'])
                            eh_tendencia = True
                        return dados, eh_tendencia

                    raw_in, is_trend_in = buscar_dados(zapi, item_down, ts_from, ts_till)
                    raw_out, is_trend_out = buscar_dados(zapi, item_up, ts_from, ts_till)

                    if not raw_in or not raw_out:
                        st.error("Dados de tráfego não encontrados para este período.")
                        st.stop()

                    def calc_stats(dados_raw, is_trend):
                        df = pd.DataFrame(dados_raw)
                        df['value'] = pd.to_numeric(df['value']) if not is_trend else pd.to_numeric(df['value_avg'])
                        if is_trend:
                            return pd.to_numeric(df['value_max']).max(), pd.to_numeric(df['value_avg']).mean()
                        return df['value'].max(), df['value'].mean()

                    pico_in, media_in = calc_stats(raw_in, is_trend_in)
                    pico_out, media_out = calc_stats(raw_out, is_trend_out)

                    estatisticas_reais = {
                        'media_in': media_in / 1_000_000, 'max_in': pico_in / 1_000_000,
                        'media_out': media_out / 1_000_000, 'max_out': pico_out / 1_000_000
                    }

                    def prep_df(dados, is_trend):
                        df = pd.DataFrame(dados)
                        df['clock'] = pd.to_datetime(pd.to_numeric(df['clock']), unit='s')
                        df['value'] = pd.to_numeric(df['value_avg']) if is_trend else pd.to_numeric(df['value'])
                        return df[['clock', 'value']]

                    df_final = pd.merge(prep_df(raw_in, is_trend_in), prep_df(raw_out, is_trend_out), on='clock', how='outer', suffixes=('_in', '_out')).sort_values('clock').fillna(0)
                    df_final['recv_mbps'] = df_final['value_in'] / 1_000_000
                    df_final['sent_mbps'] = df_final['value_out'] / 1_000_000

                    alertas_reais = []
                    eventos_problema = zapi.event.get(hostids=[host_id], time_from=ts_from, time_till=ts_till, output=['eventid', 'name', 'clock', 'r_eventid'], value=1, sortfield='clock')
                    r_event_ids = [e['r_eventid'] for e in eventos_problema if e.get('r_eventid') and e.get('r_eventid') != '0']
                    
                    mapa_recuperacao = {}
                    if r_event_ids:
                        eventos_recuperacao = zapi.event.get(eventids=r_event_ids, output=['eventid', 'clock'])
                        mapa_recuperacao = {r['eventid']: int(r['clock']) for r in eventos_recuperacao}

                    for e in eventos_problema:
                        inicio = int(e['clock'])
                        r_id = e.get('r_eventid')
                        dur_str = "Ativo/S.Rec."
                        if r_id and r_id in mapa_recuperacao:
                            duracao_segundos = mapa_recuperacao[r_id] - inicio
                            dias, resto = divmod(duracao_segundos, 86400)
                            horas, resto = divmod(resto, 3600)
                            minutos, segundos = divmod(resto, 60)
                            partes = []
                            if dias > 0: partes.append(f"{dias}d")
                            if horas > 0: partes.append(f"{horas}h")
                            if minutos > 0: partes.append(f"{minutos}m")
                            if not partes: partes.append(f"{segundos}s")
                            dur_str = " ".join(partes)
                        
                        alertas_reais.append({
                            'data': pd.to_datetime(inicio, unit='s').tz_localize('UTC').tz_convert('America/Fortaleza').strftime('%d/%m %H:%M'),
                            'trigger': e['name'], 'duracao': dur_str, 'host': nome_inst
                        })

                    infos = {
                        'instituicao': nome_inst,
                        'interface': "Interface de Borda (Banco de Dados)",
                        'periodo': f"{dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}",
                        'capacidade': cap_str 
                    }
                    
                    pdf_bytes = criar_pdf_completo(df_final, infos, alertas_reais, estatisticas_reais)
                    
                    nome_arquivo = f"Relatorio_{nome_inst.replace(' ', '_')}_{dt_inicio.strftime('%Y%m%d')}.pdf"
                    caminho_completo = os.path.join(PASTA_PDFS, nome_arquivo)
                    with open(caminho_completo, "wb") as f:
                        f.write(pdf_bytes)
                        
                    db.registrar_relatorio(inst_id_selecionada, infos['periodo'], caminho_completo)

                    st.toast("Relatório gerado e salvo no histórico com sucesso!")
                    st.download_button(
                        label="Baixar PDF Agora",
                        data=bytes(pdf_bytes),
                        file_name=nome_arquivo,
                        mime="application/pdf"
                    )

                except Exception as e:
                    st.error(f"Erro Crítico: {e}")

elif page == "Cadastros":
    # --- PÁGINA: GERENCIAR INSTITUIÇÕES ---
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown("<h3 style='margin-bottom: 20px;'><i class='fa-solid fa-network-wired' style='color: #3498DB; margin-right: 10px;'></i> Gestão de Grupos e Instituições</h3>", unsafe_allow_html=True)
    with col_btn:
        st.markdown('<div style="text-align: right; margin-top: 5px;"><a href="?page=Home" target="_self" class="btn-voltar"><i class="fa-solid fa-arrow-left"></i> Voltar</a></div>', unsafe_allow_html=True)
    
    col_grp, col_lnk = st.columns([1, 2])
    
    with col_grp:
        st.markdown("#### 1. Gerenciar Grupos")
        tab_novo_grp, tab_excluir_grp = st.tabs(["Novo Grupo", "Excluir Grupo"])
        
        with tab_novo_grp:
            with st.form("form_grupo"):
                novo_grupo = st.text_input("Nome do Grupo (ex: GigaFOR, CDC)")
                submit_grupo = st.form_submit_button("Salvar Grupo", type="primary", use_container_width=True)
                if submit_grupo and novo_grupo:
                    sucesso, msg = db.adicionar_grupo(novo_grupo)
                    if sucesso:
                        st.toast(f"Grupo '{novo_grupo}' criado com sucesso!")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        with tab_excluir_grp:
            grupos_disp = db.listar_grupos()
            if grupos_disp:
                dict_grupos_excluir = {g[1]: g[0] for g in grupos_disp}
                grupo_excluir_sel = st.selectbox("Selecione para excluir:", options=list(dict_grupos_excluir.keys()), key="sel_excluir_grupo")
                
                if st.button("Excluir Grupo Selecionado", use_container_width=True):
                    dialog_excluir_grupo(dict_grupos_excluir[grupo_excluir_sel], grupo_excluir_sel)
            else:
                st.info("Nenhum grupo cadastrado.")
                
        st.markdown("<h4 style='margin-top: 20px;'><i class='fa-solid fa-folder-tree' style='color: #F39C12; margin-right: 8px;'></i> Grupos Atuais</h4>", unsafe_allow_html=True)
        grupos = db.listar_grupos()
        for g in grupos:
            grupo_id, grupo_nome = g[0], g[1]
            # Expander permite clicar e abrir para ver o conteúdo
            with st.expander(f"📂 {grupo_nome}"):
                # Consulta SQL embutida para buscar as instituições deste grupo específico
                with db.conectar() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT nome_instituicao FROM links WHERE grupo_id = ?", (grupo_id,))
                    instituicoes_do_grupo = cursor.fetchall()
                
                if instituicoes_do_grupo:
                    for inst in instituicoes_do_grupo:
                        st.markdown(f"<div style='padding-left: 10px; border-left: 2px solid var(--primary-color); margin-bottom: 6px; color: var(--text-color); opacity: 0.85; font-size: 14px;'>• {inst[0]}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='padding-left: 10px; color: #888; font-style: italic; font-size: 13px;'>Nenhuma instituição cadastrada.</div>", unsafe_allow_html=True)

    with col_lnk:
        st.markdown("#### 2. Gerir Instituições")
        if not grupos:
            st.warning("Crie um grupo primeiro para prosseguir.")
        elif not zapi:
            st.error("Conecte ao Zabbix primeiro para listar as interfaces.")
        else:
            dict_grupos = {g[1]: g[0] for g in grupos}
            hosts = get_hosts(zapi)
            dict_hosts = {h['name']: h['hostid'] for h in hosts}

            tab_novo, tab_editar = st.tabs(["Cadastrar Nova Instituição", "Editar Instituição Existente"])

            with tab_novo:
                grupo_sel = st.selectbox("Selecione o Grupo:", options=list(dict_grupos.keys()), key="cad_grupo")
                host_sel = st.selectbox("Selecione o Host no Zabbix:", options=list(dict_hosts.keys()), key="cad_host")
                
                host_id_real = dict_hosts[host_sel]
                itens_brutos = get_items(zapi, host_id_real)
                dict_itens = {i['name']: i['itemid'] for i in itens_brutos}
                
                nome_sugerido = limpar_nome_host(host_sel)
                
                with st.form("form_link_novo"):
                    nome_personalizado = st.text_input("Nome da Instituição (para o relatório):", value=nome_sugerido, key="cad_nome")
                    
                    if not dict_itens:
                        st.warning("Nenhuma interface encontrada neste host.")
                        item_down_sel, item_up_sel = None, None
                    else:
                        item_down_sel = st.selectbox("Interface de DOWNLOAD (Entrada):", options=list(dict_itens.keys()), key="cad_down")
                        item_up_sel = st.selectbox("Interface de UPLOAD (Saída):", options=list(dict_itens.keys()), key="cad_up")
                    
                    cap = st.text_input("Capacidade (ex: 1 Gbps, 500 Mbps)", value="1 Gbps", key="cad_cap")
                    
                    if st.form_submit_button("Cadastrar Instituição no Banco", type="primary"):
                        if not dict_itens:
                            st.error("Erro: Host sem interfaces.")
                        elif not nome_personalizado.strip():
                            st.error("Erro: Nome em branco.")
                        else:
                            db.adicionar_link(dict_grupos[grupo_sel], nome_personalizado, host_id_real, dict_itens[item_down_sel], dict_itens[item_up_sel], cap)
                            st.toast(f"Instituição '{nome_personalizado}' vinculada com sucesso!")
                            time.sleep(1.5)
                            st.rerun()
            
            with tab_editar:
                inst_cadastradas = db.listar_links()
                if not inst_cadastradas:
                    st.info("Nenhuma Instituição cadastrada para editar.")
                else:
                    opcoes_inst = {f"{inst[2]} - {inst[1]}": inst[0] for inst in inst_cadastradas}
                    inst_selecionada_nome = st.selectbox("Selecione a Instituição para Editar:", options=list(opcoes_inst.keys()), key="edit_sel_inst")
                    inst_id_selecionada = opcoes_inst[inst_selecionada_nome]

                    with db.conectar() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT grupo_id, nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str FROM links WHERE id = ?", (inst_id_selecionada,))
                        curr_grupo_id, curr_nome, curr_host_id, curr_item_down_id, curr_item_up_id, curr_cap = cursor.fetchone()

                    idx_grupo = list(dict_grupos.values()).index(curr_grupo_id) if curr_grupo_id in dict_grupos.values() else 0
                    grupo_sel_edit = st.selectbox("Grupo:", options=list(dict_grupos.keys()), index=idx_grupo, key="edit_grupo")
                    
                    idx_host = list(dict_hosts.values()).index(curr_host_id) if curr_host_id in dict_hosts.values() else 0
                    host_sel_edit = st.selectbox("Host no Zabbix:", options=list(dict_hosts.keys()), index=idx_host, key="edit_host")
                    
                    host_id_real_edit = dict_hosts[host_sel_edit]
                    itens_brutos_edit = get_items(zapi, host_id_real_edit)
                    dict_itens_edit = {i['name']: i['itemid'] for i in itens_brutos_edit}
                    
                    with st.form("form_link_editar"):
                        nome_personalizado_edit = st.text_input("Nome da Instituição (para o relatório):", value=curr_nome, key="edit_nome_input")
                        
                        if not dict_itens_edit:
                            st.warning("Nenhuma interface encontrada neste host.")
                            item_down_sel_edit, item_up_sel_edit = None, None
                        else:
                            idx_down = list(dict_itens_edit.values()).index(curr_item_down_id) if curr_item_down_id in dict_itens_edit.values() else 0
                            idx_up = list(dict_itens_edit.values()).index(curr_item_up_id) if curr_item_up_id in dict_itens_edit.values() else 0
                            
                            item_down_sel_edit = st.selectbox("Interface de DOWNLOAD (Entrada):", options=list(dict_itens_edit.keys()), index=idx_down, key="edit_down")
                            item_up_sel_edit = st.selectbox("Interface de UPLOAD (Saída):", options=list(dict_itens_edit.keys()), index=idx_up, key="edit_up")
                        
                        cap_edit = st.text_input("Capacidade (ex: 1 Gbps, 500 Mbps)", value=curr_cap, key="edit_cap")
                        
                        submit_edit = st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True)
                        
                        if submit_edit:
                            if not dict_itens_edit:
                                st.error("Erro: Host sem interfaces válidas.")
                            elif not nome_personalizado_edit.strip():
                                st.error("Erro: Nome em branco.")
                            else:
                                with db.conectar() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('UPDATE links SET grupo_id=?, nome_instituicao=?, host_id=?, item_down_id=?, item_up_id=?, capacidade_str=? WHERE id=?', 
                                                   (dict_grupos[grupo_sel_edit], nome_personalizado_edit, host_id_real_edit, dict_itens_edit[item_down_sel_edit], dict_itens_edit[item_up_sel_edit], cap_edit, inst_id_selecionada))
                                    conn.commit()
                                st.toast("Alterações salvas com sucesso!")
                                time.sleep(1.2)
                                st.rerun()

                    # O botão de exclusão da Instituição fica de FORA do formulário
                    # para que o pop-up (dialog) não seja fechado pelo refresh do botão submit_form
                    st.markdown("<hr style='margin: 15px 0; opacity: 0.3;'>", unsafe_allow_html=True)
                    st.markdown("<h5 style='color: #E74C3C;'>Zona de Perigo</h5>", unsafe_allow_html=True)
                    if st.button("Excluir Instituição", use_container_width=True):
                        dialog_excluir_instituicao(inst_id_selecionada, curr_nome)

elif page == "Historico":
    # --- PÁGINA: HISTÓRICO ---
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown("<h3 style='margin-bottom: 20px;'><i class='fa-solid fa-folder-open' style='color: #F39C12; margin-right: 10px;'></i> Histórico de Relatórios</h3>", unsafe_allow_html=True)
    with col_btn:
        st.markdown('<div style="text-align: right; margin-top: 5px;"><a href="?page=Home" target="_self" class="btn-voltar"><i class="fa-solid fa-arrow-left"></i> Voltar</a></div>', unsafe_allow_html=True)
    
    historico = db.listar_historico()
    
    if not historico:
        st.info("Nenhum relatório foi gerado e salvo no banco de dados ainda.")
    else:
        # Cruza os dados do histórico para descobrir o "Grupo" de cada Instituição via SQL direto no Pandas
        with db.conectar() as conn:
            links_raw = conn.execute("SELECT nome_instituicao, grupo_id FROM links").fetchall()
            grupos_raw = conn.execute("SELECT id, nome FROM grupos").fetchall()
            mapa_grupos = {g[0]: g[1] for g in grupos_raw}
            mapa_inst_grupo = {l[0]: mapa_grupos.get(l[1], "Sem Grupo") for l in links_raw}

        df_hist = pd.DataFrame(historico, columns=["Data Geração", "Instituição", "Período Referência", "Caminho Arquivo"])
        # Adiciona a coluna de Grupo mapeando os dados
        df_hist["Grupo"] = df_hist["Instituição"].map(mapa_inst_grupo).fillna("Excluído/Desconhecido")
        
        # Converte a Coluna de Data para DateTime facilitando os filtros abaixo
        df_hist["Data Geração DT"] = pd.to_datetime(df_hist["Data Geração"], errors='coerce')

        st.markdown("#### <i class='fa-solid fa-filter' style='color: #3498DB; margin-right: 8px;'></i> Filtrar Histórico", unsafe_allow_html=True)
        col_busca, col_filtro, col_data = st.columns([2, 1, 1])
        
        with col_busca:
            busca_texto = st.text_input("Pesquisar por nome da Instituição:", placeholder="Ex: UECE Itaperi...")
        with col_filtro:
            opcoes_grupos = ["Todos"] + sorted(list(df_hist["Grupo"].unique()))
            filtro_grupo = st.selectbox("Filtrar por Grupo:", options=opcoes_grupos)
        with col_data:
            opcoes_tempo = ["Todo o tempo", "Hoje", "Últimos 7 dias", "Últimos 30 dias", "Últimos 3 meses", "Personalizado"]
            filtro_tempo = st.selectbox("Filtrar por Data:", options=opcoes_tempo, index=0)
            
        # Se escolher Personalizado, abre o seletor de duas datas na linha de baixo
        if filtro_tempo == "Personalizado":
            col_dt1, col_dt2, _ = st.columns([1, 1, 2])
            with col_dt1:
                dt_inicio_hist = st.date_input("De:", value=date.today() - timedelta(days=7), key="hist_dt_inicio")
            with col_dt2:
                dt_fim_hist = st.date_input("Até:", value=date.today(), key="hist_dt_fim")
            
        # Aplicação dos Filtros Simples no Dataframe
        if filtro_grupo != "Todos":
            df_hist = df_hist[df_hist["Grupo"] == filtro_grupo]
        if busca_texto:
            df_hist = df_hist[df_hist["Instituição"].str.contains(busca_texto, case=False, na=False)]
            
        # Aplicação do Filtro Inteligente de Datas
        hoje = pd.Timestamp(date.today())
        if filtro_tempo == "Hoje":
            df_hist = df_hist[df_hist["Data Geração DT"] >= hoje]
        elif filtro_tempo == "Últimos 7 dias":
            df_hist = df_hist[df_hist["Data Geração DT"] >= (hoje - pd.Timedelta(days=7))]
        elif filtro_tempo == "Últimos 30 dias":
            df_hist = df_hist[df_hist["Data Geração DT"] >= (hoje - pd.Timedelta(days=30))]
        elif filtro_tempo == "Últimos 3 meses":
            df_hist = df_hist[df_hist["Data Geração DT"] >= (hoje - pd.Timedelta(days=90))]
        elif filtro_tempo == "Personalizado":
            fim_inclusivo = pd.Timestamp(dt_fim_hist) + pd.Timedelta(days=1) # +1 dia para cobrir até às 23:59h do dia escolhido
            df_hist = df_hist[(df_hist["Data Geração DT"] >= pd.Timestamp(dt_inicio_hist)) & (df_hist["Data Geração DT"] < fim_inclusivo)]

        st.dataframe(df_hist[["Data Geração", "Grupo", "Instituição", "Período Referência"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown(f"#### <i class='fa-solid fa-download' style='color: #2ECC71; margin-right: 8px;'></i> Baixar Relatórios ({len(df_hist)} encontrados)", unsafe_allow_html=True)
        
        for index, row in df_hist.head(15).iterrows():
            data_geracao = row["Data Geração"]
            inst = row["Instituição"]
            periodo = row["Período Referência"]
            caminho = row["Caminho Arquivo"]
            grupo = row["Grupo"]
            
            if os.path.exists(caminho):
                with open(caminho, "rb") as pdf_file:
                    st.download_button(
                        label=f"{grupo} | {inst} ({periodo}) - Gerado em: {data_geracao[:16]}",
                        data=pdf_file,
                        file_name=os.path.basename(caminho),
                        mime="application/pdf",
                        key=f"{caminho}_{index}"
                    )
            else:
                st.error(f"Arquivo apagado do disco: {inst} ({periodo})")