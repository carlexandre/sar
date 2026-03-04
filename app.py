import streamlit as st
import os
import requests
import re
import urllib3
import base64
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
st.set_page_config(page_title="SAR | PoP-CE", layout="wide", page_icon="assets/favicon/relatorio-de-lucro.png")

# --- 1. INJEÇÃO DE CSS E ÍCONES (FONT AWESOME) ---
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Puxa a aplicação para o topo (reduz o espaço branco gigante padrão do Streamlit) */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
    }

    /* Estilização dos Cards da Home */
    .card-icon {
        font-size: 50px;
        margin-bottom: 15px;
    }
    .card-title {
        font-weight: 600;
        margin-bottom: 10px;
    }
    .card-desc {
        color: #888;
        font-size: 14px;
        margin-bottom: 20px;
        min-height: 40px;
    }
    
    /* Estilização da Navbar Customizada */
    .custom-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between; /* Empurra o texto para a esquerda e o logo para a direita */
        width: 100%;
    }
    .nav-logo {
        height: 40px; /* Altura reduzida para não cortar */
        width: auto;
        object-fit: contain; /* Garante que as proporções da imagem são respeitadas */
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
    }
    .nav-subtitle {
        font-size: 1rem;
        font-weight: 500;
        color: #888888;
        letter-spacing: 1px;
    }
    
    /* Alternância de cores da Logo (Light/Dark Mode) */
    .logo-light { display: block !important; }
    .logo-dark { display: none !important; }
    @media (prefers-color-scheme: dark) {
        .logo-light { display: none !important; }
        .logo-dark { display: block !important; }
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

    /* Estilização do Novo Botão Voltar HTML */
    .btn-voltar {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background-color: transparent;
        color: #b0b0b0 !important;
        padding: 6px 14px;
        border-radius: 6px;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 600;
        border: 1px solid #555;
        transition: all 0.2s ease;
    }
    .btn-voltar:hover {
        color: #ffffff !important;
        border-color: #ffffff;
        background-color: rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONTROLE DE ESTADO E URL (ROTEAMENTO) ---
# Lendo a página diretamente da URL (permite usar o botão voltar do navegador)
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
        return None

def limpar_nome_host(nome_bruto):
    nome = nome_bruto.replace(" -- GIGAFOR", "").replace(" -- RNP", "")
    nome = re.sub(r'^RG\d+\s+-\s+', '', nome)
    return nome

# Otimização de Performance: Cache dos dados do Zabbix por 5 minutos (300s)
# O underline em _zapi diz ao Streamlit para não tentar fazer hash da conexão
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
# NAVBAR (CABEÇALHO GLOBAL)
# ==========================================
def renderizar_navbar():
    caminho_preto = "assets/logo/pop-ce-logo-preto.png"
    caminho_branco = "assets/logo/pop-ce-logo-branca.png"
    
    b64_light = ""
    b64_dark = ""
    
    if os.path.exists(caminho_preto) and os.path.exists(caminho_branco):
        with open(caminho_preto, "rb") as f:
            b64_light = base64.b64encode(f.read()).decode("utf-8")
        with open(caminho_branco, "rb") as f:
            b64_dark = base64.b64encode(f.read()).decode("utf-8")
            
    # Constrói o HTML da Navbar
    html_navbar = f"""
    <a href="?page=Home" target="_self" class="navbar-link">
        <div class="custom-navbar">
            <div class="nav-text">
                <span class="nav-title">SAR</span>
                <span class="nav-subtitle">SISTEMA DE AUTOMATIZAÇÃO DE RELATÓRIOS</span>
            </div>
            <div class="logo-wrapper">
                <img src="data:image/png;base64,{b64_light}" class="nav-logo logo-light" onerror="this.style.display='none'">
                <img src="data:image/png;base64,{b64_dark}" class="nav-logo logo-dark" onerror="this.style.display='none'">
            </div>
        </div>
    </a>
    """
    return html_navbar

# A Navbar agora é estática e idêntica em todas as rotas
st.markdown(renderizar_navbar(), unsafe_allow_html=True)
st.markdown("<hr style='margin-top: 15px; margin-bottom: 30px; border-color: #555; opacity: 0.3;'>", unsafe_allow_html=True)


# ==========================================
# ROTEAMENTO DE PÁGINAS
# ==========================================

if page == "Home":
    # --- PÁGINA INICIAL (CARDS) ---
    st.markdown("<h3 style='text-align: center; margin-bottom: 40px;'>Selecione um Módulo</h3>", unsafe_allow_html=True)
    
    # Criamos 3 colunas para os blocos/cards
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True): # Borda nativa do Streamlit
            st.markdown("<div style='text-align: center;'><i class='fa-solid fa-file-pdf card-icon' style='color: #E74C3C;'></i></div>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center;' class='card-title'>Gerar Relatório</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;' class='card-desc'>Consulte o tráfego do Zabbix e exporte o documento PDF formatado.</p>", unsafe_allow_html=True)
            if st.button("Acessar Módulo", key="btn_home_gerar", use_container_width=True, type="primary"):
                ir_para("Gerar")
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("<div style='text-align: center;'><i class='fa-solid fa-network-wired card-icon' style='color: #3498DB;'></i></div>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center;' class='card-title'>Cadastrar Links</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;' class='card-desc'>Gerencie as instituições, grupos e interfaces de monitoramento.</p>", unsafe_allow_html=True)
            if st.button("Acessar Módulo", key="btn_home_cad", use_container_width=True):
                ir_para("Cadastros")
                st.rerun()

    with c3:
        with st.container(border=True):
            st.markdown("<div style='text-align: center;'><i class='fa-solid fa-folder-open card-icon' style='color: #F39C12;'></i></div>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center;' class='card-title'>Histórico</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;' class='card-desc'>Acesse o repositório de relatórios gerados anteriormente pelo sistema.</p>", unsafe_allow_html=True)
            if st.button("Acessar Módulo", key="btn_home_hist", use_container_width=True):
                ir_para("Historico")
                st.rerun()

elif page == "Gerar":
    # --- PÁGINA: GERAR RELATÓRIO ---
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown("<h3 style='margin-bottom: 20px;'><i class='fa-solid fa-file-pdf' style='color: #E74C3C; margin-right: 10px;'></i> Gerar Novo Relatório</h3>", unsafe_allow_html=True)
    with col_btn:
        st.markdown('<div style="text-align: right; margin-top: 5px;"><a href="?page=Home" target="_self" class="btn-voltar"><i class="fa-solid fa-arrow-left"></i> Voltar</a></div>', unsafe_allow_html=True)
    
    links_cadastrados = db.listar_links()
    
    if not links_cadastrados:
        st.info("Nenhum link cadastrado ainda. Vá para o módulo 'Cadastrar Links'.")
    elif not zapi:
        st.error("Sem conexão com o Zabbix. Verifique suas credenciais no .env.")
    else:
        col_link, col_data = st.columns([2, 1])
        
        with col_link:
            opcoes_links = {f"{link[2]} - {link[1]}": link[0] for link in links_cadastrados}
            link_selecionado_nome = st.selectbox("Selecione o Link Cadastrado:", options=list(opcoes_links.keys()))
            link_id_selecionado = opcoes_links[link_selecionado_nome]
            
        with col_data:
            dt_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=30))
            dt_fim = st.date_input("Data Fim", value=date.today())
            
        st.divider()
        if st.button("Gerar Relatório e Salvar", type="primary"):
            with st.spinner("Conectando ao Zabbix, processando dados e desenhando o PDF..."):
                try:
                    with db.conectar() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str FROM links WHERE id = ?", (link_id_selecionado,))
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
                        
                    db.registrar_relatorio(link_id_selecionado, infos['periodo'], caminho_completo)

                    st.success("Relatório gerado e salvo no histórico com sucesso!")
                    st.download_button(
                        label="Baixar PDF Agora",
                        data=bytes(pdf_bytes),
                        file_name=nome_arquivo,
                        mime="application/pdf"
                    )

                except Exception as e:
                    st.error(f"Erro Crítico: {e}")

elif page == "Cadastros":
    # --- PÁGINA: CADASTRAR LINKS ---
    col_tit, col_btn = st.columns([8, 2])
    with col_tit:
        st.markdown("<h3 style='margin-bottom: 20px;'><i class='fa-solid fa-network-wired' style='color: #3498DB; margin-right: 10px;'></i> Gestão de Grupos e Links</h3>", unsafe_allow_html=True)
    with col_btn:
        st.markdown('<div style="text-align: right; margin-top: 5px;"><a href="?page=Home" target="_self" class="btn-voltar"><i class="fa-solid fa-arrow-left"></i> Voltar</a></div>', unsafe_allow_html=True)
    
    col_grp, col_lnk = st.columns([1, 2])
    
    with col_grp:
        st.markdown("#### 1. Criar Grupo")
        with st.form("form_grupo"):
            novo_grupo = st.text_input("Nome do Grupo (ex: GigaFOR, CDC)")
            submit_grupo = st.form_submit_button("Salvar Grupo")
            if submit_grupo and novo_grupo:
                sucesso, msg = db.adicionar_grupo(novo_grupo)
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
        st.write("Grupos Atuais:")
        grupos = db.listar_grupos()
        for g in grupos:
            st.markdown(f"<div style='color: #888; font-size: 14px; margin-bottom: 8px;'><i class='fa-solid fa-folder' style='color: #F39C12; margin-right: 8px;'></i> {g[1]}</div>", unsafe_allow_html=True)

    with col_lnk:
        st.markdown("#### 2. Gerir Links")
        if not grupos:
            st.warning("Crie um grupo primeiro para prosseguir.")
        elif not zapi:
            st.error("Conecte ao Zabbix primeiro para listar as interfaces.")
        else:
            modo_acao = st.radio("Selecione a Ação:", ["Cadastrar Novo Link", "Editar Link Existente"], horizontal=True)
            
            dict_grupos = {g[1]: g[0] for g in grupos}
            hosts = get_hosts(zapi)
            dict_hosts = {h['name']: h['hostid'] for h in hosts}

            if modo_acao == "Cadastrar Novo Link":
                grupo_sel = st.selectbox("Selecione o Grupo:", options=list(dict_grupos.keys()))
                host_sel = st.selectbox("Selecione o Host no Zabbix:", options=list(dict_hosts.keys()))
                
                host_id_real = dict_hosts[host_sel]
                itens_brutos = get_items(zapi, host_id_real)
                dict_itens = {i['name']: i['itemid'] for i in itens_brutos}
                
                nome_sugerido = limpar_nome_host(host_sel)
                
                with st.form("form_link_novo"):
                    nome_personalizado = st.text_input("Nome da Instituição (para o relatório):", value=nome_sugerido)
                    
                    if not dict_itens:
                        st.warning("Nenhuma interface encontrada neste host.")
                        item_down_sel, item_up_sel = None, None
                    else:
                        item_down_sel = st.selectbox("Interface de DOWNLOAD (Entrada):", options=list(dict_itens.keys()))
                        item_up_sel = st.selectbox("Interface de UPLOAD (Saída):", options=list(dict_itens.keys()))
                    
                    cap = st.text_input("Capacidade (ex: 1 Gbps, 500 Mbps)", value="1 Gbps")
                    
                    if st.form_submit_button("Cadastrar Link no Banco"):
                        if not dict_itens:
                            st.error("Erro: Host sem interfaces.")
                        elif not nome_personalizado.strip():
                            st.error("Erro: Nome em branco.")
                        else:
                            db.adicionar_link(dict_grupos[grupo_sel], nome_personalizado, host_id_real, dict_itens[item_down_sel], dict_itens[item_up_sel], cap)
                            st.success(f"Link '{nome_personalizado}' vinculado com sucesso!")
                            st.rerun()
            
            else:
                links_cadastrados = db.listar_links()
                if not links_cadastrados:
                    st.info("Nenhum link cadastrado para editar.")
                else:
                    opcoes_links = {f"{link[2]} - {link[1]}": link[0] for link in links_cadastrados}
                    link_selecionado_nome = st.selectbox("Selecione o Link para Editar:", options=list(opcoes_links.keys()))
                    link_id_selecionado = opcoes_links[link_selecionado_nome]

                    with db.conectar() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT grupo_id, nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str FROM links WHERE id = ?", (link_id_selecionado,))
                        curr_grupo_id, curr_nome, curr_host_id, curr_item_down_id, curr_item_up_id, curr_cap = cursor.fetchone()

                    idx_grupo = list(dict_grupos.values()).index(curr_grupo_id) if curr_grupo_id in dict_grupos.values() else 0
                    grupo_sel = st.selectbox("Grupo:", options=list(dict_grupos.keys()), index=idx_grupo)
                    
                    idx_host = list(dict_hosts.values()).index(curr_host_id) if curr_host_id in dict_hosts.values() else 0
                    host_sel = st.selectbox("Host no Zabbix:", options=list(dict_hosts.keys()), index=idx_host)
                    
                    host_id_real = dict_hosts[host_sel]
                    itens_brutos = get_items(zapi, host_id_real)
                    dict_itens = {i['name']: i['itemid'] for i in itens_brutos}
                    
                    with st.form("form_link_editar"):
                        nome_personalizado = st.text_input("Nome da Instituição (para o relatório):", value=curr_nome)
                        
                        if not dict_itens:
                            st.warning("Nenhuma interface encontrada neste host.")
                            item_down_sel, item_up_sel = None, None
                        else:
                            idx_down = list(dict_itens.values()).index(curr_item_down_id) if curr_item_down_id in dict_itens.values() else 0
                            idx_up = list(dict_itens.values()).index(curr_item_up_id) if curr_item_up_id in dict_itens.values() else 0
                            
                            item_down_sel = st.selectbox("Interface de DOWNLOAD (Entrada):", options=list(dict_itens.keys()), index=idx_down)
                            item_up_sel = st.selectbox("Interface de UPLOAD (Saída):", options=list(dict_itens.keys()), index=idx_up)
                        
                        cap = st.text_input("Capacidade (ex: 1 Gbps, 500 Mbps)", value=curr_cap)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submit_edit = st.form_submit_button("Salvar Alterações", type="primary")
                        with col_btn2:
                            submit_delete = st.form_submit_button("Excluir Link")
                        
                        if submit_edit:
                            if not dict_itens:
                                st.error("Erro: Host sem interfaces válidas.")
                            elif not nome_personalizado.strip():
                                st.error("Erro: Nome em branco.")
                            else:
                                with db.conectar() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('UPDATE links SET grupo_id=?, nome_instituicao=?, host_id=?, item_down_id=?, item_up_id=?, capacidade_str=? WHERE id=?', 
                                                   (dict_grupos[grupo_sel], nome_personalizado, host_id_real, dict_itens[item_down_sel], dict_itens[item_up_sel], cap, link_id_selecionado))
                                    conn.commit()
                                st.success("Atualizado com sucesso!")
                                st.rerun()

                        if submit_delete:
                            try:
                                with db.conectar() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM links WHERE id=?", (link_id_selecionado,))
                                    conn.commit()
                                st.success("Link excluído!")
                                st.rerun()
                            except Exception as e:
                                st.error("Não foi possível excluir. (Existem relatórios atrelados no histórico)")

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
        df_hist = pd.DataFrame(historico, columns=["Data Geração", "Instituição", "Período Referência", "Caminho Arquivo"])
        st.dataframe(df_hist[["Data Geração", "Instituição", "Período Referência"]], use_container_width=True)
        
        st.divider()
        st.markdown("#### Baixar Relatórios Salvos")
        
        for i, row in enumerate(historico[:15]): # Exibe os últimos 15
            data_geracao, inst, periodo, caminho = row
            
            if os.path.exists(caminho):
                with open(caminho, "rb") as pdf_file:
                    st.download_button(
                        label=f"{inst} ({periodo}) - Gerado em: {data_geracao[:16]}",
                        data=pdf_file,
                        file_name=os.path.basename(caminho),
                        mime="application/pdf",
                        key=f"{caminho}_{i}"
                    )
            else:
                st.error(f"Arquivo apagado do disco: {inst} ({periodo})")