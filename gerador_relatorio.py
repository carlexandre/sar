import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import textwrap
from datetime import date

# --- 1. CONFIGURAÇÃO DE TEXTOS ---
TEXTOS = {
    "introducao": (
        "Este relatório apresenta a análise técnica de tráfego de dados referente à {instituicao}, "
        "focando no monitoramento do link de conectividade. A análise abrange a conexão da instituição "
        "à rede metropolitana GigaFOR e o acesso ao backbone nacional da RNP.\n\n"
        "O objetivo principal é monitorar o comportamento do tráfego na interface de borda, "
        "identificar a taxa de ocupação do link e garantir a disponibilidade dos serviços."
    ),
    "sobre_rnp": (
        "A Rede Nacional de Ensino e Pesquisa (RNP) é a organização responsável por prover a "
        "infraestrutura de rede avançada que conecta as instituições de ensino e pesquisa no Brasil. "
        "Ela viabiliza a colaboração científica e tecnológica, oferecendo serviços de conectividade "
        "de alta velocidade."
    ),
    "sobre_gigafor": (
        "A GigaFOR é a Rede Metropolitana de Educação e Pesquisa de Fortaleza. Trata-se da "
        "infraestrutura de fibra óptica de alto desempenho que conecta a instituição ao "
        "Ponto de Presença da RNP no Ceará (PoP-CE)."
    )
}

# --- 2. FUNÇÃO DE GERAR GRÁFICO (ESTILO ZABBIX) ---
def gerar_grafico_trafego(df, nome_instituicao):
    """
    Gera gráfico simulando a interface clara do Zabbix.
    Aplica suavização (1h max) se houver muitos dados, para limpar o ruído visual 
    sem perder a métrica dos picos de saturação.
    """
    df_plot = df.copy()
    
    # SUAVIZAÇÃO VISUAL (Resampling)
    if len(df_plot) > 500:
        df_plot = df_plot.set_index('clock')
        # Pega o MAX de cada hora para o gráfico não esconder picos reais de banda
        # CORREÇÃO: Uso de '1h' (minúsculo) para compatibilidade com versões novas do Pandas
        df_plot = df_plot.resample('1h').max().reset_index()

    # Define o fundo para claro (Estilo Zabbix Clássico)
    plt.style.use('default') 
    
    # Ajuste de tamanho (largura aumentada de 10.5 para 14 para ficar mais largo/panorâmico)
    fig, ax = plt.subplots(figsize=(14, 4.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8f9fa') # Cinza super claro no fundo do gráfico
    
    # --- PLOTAGEM ---
    # Download (Verde com preenchimento)
    ax.fill_between(df_plot['clock'], df_plot['recv_mbps'], color='#34c759', alpha=0.3, linewidth=0)
    ax.plot(df_plot['clock'], df_plot['recv_mbps'], color='#27ae60', linewidth=1.2)
    
    # Upload (Vermelho apenas em linha fina)
    ax.plot(df_plot['clock'], df_plot['sent_mbps'], color='#e74c3c', linewidth=1.2)
    
    # --- ESTÉTICA DO ZABBIX ---
    ax.set_title(f"{nome_instituicao}: Network traffic", fontsize=12, color='#333333', pad=15)
    ax.set_ylabel("Mbps", color='#333333', fontsize=9)
    
    # Rótulos no eixo Y em ambos os lados e rótulos X em vermelho na vertical
    ax.tick_params(axis='y', colors='#333333', labelsize=9, labelright=True)
    ax.tick_params(axis='x', colors='#e74c3c', labelsize=9, rotation=90)
    
    # Grid pontilhado idêntico ao Zabbix
    ax.grid(True, which='major', color='#cccccc', linestyle='--', linewidth=0.7)
    
    # Eixo X (Datas formatadas)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    
    # Bordas limpas
    ax.spines['top'].set_color('#cccccc')
    ax.spines['right'].set_color('#cccccc')
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    
    # --- LIMITES DO EIXO Y (Topagem de 1000 Mbps) ---
    if not df_plot.empty:
        max_trafego = max(df_plot['recv_mbps'].max(), df_plot['sent_mbps'].max())
        ax.set_xlim(df_plot['clock'].min(), df_plot['clock'].max())
        # Força a topagem para 1000. Se o tráfego passar de 1000, adapta-se para não cortar.
        ax.set_ylim(0, max(1000, max_trafego * 1.05))

    # --- CRIAÇÃO DA TABELA DE LEGENDA (Abaixo do Gráfico) ---
    if not df.empty:
        # Usa os dados originais (não suavizados) para obter a precisão real nas estatísticas
        in_last = df['recv_mbps'].iloc[-1]
        in_min = df['recv_mbps'].min()
        in_avg = df['recv_mbps'].mean()
        in_max = df['recv_mbps'].max()
        
        out_last = df['sent_mbps'].iloc[-1]
        out_min = df['sent_mbps'].min()
        out_avg = df['sent_mbps'].mean()
        out_max = df['sent_mbps'].max()

        # Texto monoespaçado para a tabela alinhar perfeitamente
        legenda_texto = (
            f"                            último         mín           méd           máx\n"
            f"[🟩] Download (Entrada)  {in_last:>8.2f} Mbps  {in_min:>8.2f} Mbps  {in_avg:>8.2f} Mbps  {in_max:>8.2f} Mbps\n"
            f"[🟥] Upload   (Saída)    {out_last:>8.2f} Mbps  {out_min:>8.2f} Mbps  {out_avg:>8.2f} Mbps  {out_max:>8.2f} Mbps"
        )
    else:
        legenda_texto = "Sem dados para o período."

    # Levanta a caixa do gráfico para caber o texto por baixo
    plt.subplots_adjust(bottom=0.35)
    
    # Imprime a tabela monoespaçada no canto esquerdo inferior (tamanho de fonte compensado para a nova largura)
    fig.text(0.08, 0.02, legenda_texto, family='monospace', fontsize=10, va='bottom', color='#333333')

    # Salva
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close()
    
    return temp_file.name

# --- 3. CLASSE DO PDF (ESTRUTURA COM CAPA, CABEÇALHO E RODAPÉ) ---
class RelatorioPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pop_ce_logo = "assets/logo/pop-ce-logo-preto.png"
        self.rnp_logo = "assets/logo/rnp-logo-preto.png" 

    def header(self):
        if self.page_no() > 1:
            if os.path.exists(self.pop_ce_logo):
                self.image(self.pop_ce_logo, 85, 8, 40)
                self.set_y(24) 
            else:
                self.set_font('Arial', 'B', 14)
                self.cell(0, 10, 'PoP-CE', 0, 1, 'C')
            
            self.set_font('Arial', 'B', 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 4, 'PONTO DE PRESENÇA', 0, 1, 'C')
            self.cell(0, 4, 'DA RNP CEARÁ', 0, 1, 'C')
            self.ln(8) 

    def footer(self):
        if self.page_no() > 1:
            if os.path.exists(self.rnp_logo):
                self.image(self.rnp_logo, 80, 276, 50) 
            else:
                self.set_y(-20)
                self.set_font('Arial', 'B', 12)
                self.set_text_color(50, 50, 50)
                self.cell(0, 10, 'RNP', 0, 0, 'C')

            self.set_y(-15)
            self.set_font('Arial', '', 10)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, str(self.page_no()), 0, 0, 'R')

    def gerar_capa(self, instituicao, periodo):
        self.add_page()
        
        if os.path.exists(self.pop_ce_logo):
            self.image(self.pop_ce_logo, 70, 40, 70)
        
        self.set_y(95)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(50, 50, 50)
        self.cell(0, 6, 'PONTO DE PRESENÇA', 0, 1, 'C')
        self.cell(0, 6, 'DA RNP CEARÁ', 0, 1, 'C')
        
        self.ln(25)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, 'RELATÓRIO TÉCNICO DE', 0, 1, 'C')
        self.cell(0, 8, 'MONITORAMENTO DE TRÁFEGO', 0, 1, 'C')
        
        self.ln(10)
        self.set_font('Arial', '', 14)
        self.cell(0, 8, 'Rede GigaFOR / POP-CE', 0, 1, 'C')
        
        self.ln(25)
        self.set_font('Arial', '', 12)
        self.cell(0, 6, 'Período de Referência:', 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, periodo, 0, 1, 'C')
        
        self.ln(20)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, instituicao, 0, 1, 'C')
        
        self.set_y(-30)
        self.set_font('Arial', '', 10)
        data_atual = date.today().strftime('%d/%m/%Y')
        self.cell(0, 10, f'Fortaleza - CE - {data_atual}', 0, 0, 'C')

    def capitulo_titulo(self, titulo):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, titulo, 0, 1, 'L', fill=True)
        self.ln(2)

    def corpo_texto(self, texto):
        self.set_font('Arial', '', 11)
        self.set_text_color(30, 30, 30)
        try:
            texto = texto.encode('latin-1', 'replace').decode('latin-1')
        except:
            pass
        self.multi_cell(0, 6, texto)
        self.ln(5)

    def tabela_alertas(self, lista_alertas):
        self.set_font('Arial', 'B', 9)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(220, 220, 220)
        self.cell(35, 7, 'Data', 1, 0, 'C', True)
        self.cell(85, 7, 'Tipo de Alerta (Trigger)', 1, 0, 'C', True)
        self.cell(30, 7, 'Duração', 1, 0, 'C', True)
        self.cell(40, 7, 'Campus', 1, 1, 'C', True)
        
        self.set_font('Arial', '', 9)
        if not lista_alertas:
            self.ln(2)
            self.cell(190, 7, 'Nenhuma ocorrência crítica registrada.', 1, 1, 'C')
        else:
            for alerta in lista_alertas:
                trig = str(alerta.get('trigger', '-'))
                host = str(alerta.get('host', '-'))
                if len(host) > 22: host = host[:19] + "..."
                
                try:
                    trig = trig.encode('latin-1', 'replace').decode('latin-1')
                    host = host.encode('latin-1', 'replace').decode('latin-1')
                except:
                    pass

                linhas_trig = textwrap.wrap(trig, width=48)
                num_linhas = max(1, len(linhas_trig))
                altura_linha = 7
                altura_total = altura_linha * num_linhas
                
                if self.get_y() + altura_total > 270:
                    self.add_page()
                    
                x_atual = self.get_x()
                y_atual = self.get_y()
                
                self.rect(x_atual, y_atual, 35, altura_total)
                self.cell(35, altura_total, str(alerta.get('data', '-')), border=0, align='C')
                
                x_trigger = self.get_x()
                self.rect(x_trigger, y_atual, 85, altura_total)
                
                if num_linhas == 1:
                    self.cell(85, altura_total, trig, border=0, align='L')
                else:
                    self.set_xy(x_trigger + 1, y_atual + 1) 
                    self.multi_cell(83, 5, trig, border=0, align='L')
                    self.set_xy(x_trigger + 85, y_atual) 
                    
                x_duracao = self.get_x()
                self.rect(x_duracao, y_atual, 30, altura_total)
                self.cell(30, altura_total, str(alerta.get('duracao', '-')), border=0, align='C')
                
                x_campus = self.get_x()
                self.rect(x_campus, y_atual, 40, altura_total)
                self.cell(40, altura_total, host, border=0, ln=1, align='C')
                
        self.ln(10)

# --- 4. FUNÇÃO PRINCIPAL ---
def criar_pdf_completo(dados_trafego, infos_relatorio, lista_alertas=None, estatisticas=None):
    pdf = RelatorioPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # 1. GERAÇÃO DA CAPA (Página 1)
    pdf.gerar_capa(infos_relatorio['instituicao'], infos_relatorio['periodo'])
    
    # 2. CONTEÚDO (Início na Página 2 com cabeçalho/rodapé ativados)
    pdf.add_page() 
    
    # Introdução
    pdf.capitulo_titulo("2. Introdução")
    pdf.corpo_texto(TEXTOS['introducao'].format(instituicao=infos_relatorio['instituicao']))
    pdf.capitulo_titulo("2.1. Sobre a RNP")
    pdf.corpo_texto(TEXTOS['sobre_rnp'])
    pdf.capitulo_titulo("2.2. Sobre a GigaFOR")
    pdf.corpo_texto(TEXTOS['sobre_gigafor'])
    
    pdf.add_page() 

    # Análise Gráfica
    pdf.capitulo_titulo("3. Análise de Tráfego por Unidade")
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"3.1. Instituição: {infos_relatorio['instituicao']}", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Link Contratado/Capacidade: {infos_relatorio.get('capacidade', '1 Gbps')}", 0, 1)
    pdf.ln(3)
    
    # O gráfico já inclui a legenda Zabbix internamente, então removemos a instrução de legenda em texto manual daqui
    caminho_img = gerar_grafico_trafego(dados_trafego, infos_relatorio['instituicao'])
    pdf.image(caminho_img, x=10, w=190)
    os.remove(caminho_img)
    
    # Damos um pulo de linha maior porque a tabela do gráfico já faz o trabalho da legenda
    pdf.ln(8)

    # Estatísticas
    if estatisticas:
        media_in = estatisticas['media_in']
        media_out = estatisticas['media_out']
        max_in = estatisticas['max_in']
        max_out = estatisticas['max_out']
    else:
        media_in = dados_trafego['recv_mbps'].mean()
        media_out = dados_trafego['sent_mbps'].mean()
        max_in = dados_trafego['recv_mbps'].max()
        max_out = dados_trafego['sent_mbps'].max()
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "Análise Técnica", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    stats = (
        f"Tráfego Médio (Entrada): {media_in:.2f} Mbps\n"
        f"Tráfego Médio (Saída): {media_out:.2f} Mbps\n"
        f"Pico Máximo (Entrada): {max_in:.2f} Mbps\n"
        f"Pico Máximo (Saída): {max_out:.2f} Mbps\n"
    )
    pdf.multi_cell(0, 6, stats)
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "Observações:", 0, 1)
    pdf.set_font('Arial', '', 10)
    obs = ""
    if max_in > 900 or max_out > 900:
        obs += "- Alerta de Saturação: O tráfego atingiu níveis muito próximos à capacidade física do link (>90%).\n"
        obs += "- Nota-se o \"achatamento\" das ondas nos picos, indicando que a demanda pode ser maior do que a banda contratada, gerando possíveis lentidões ou filas em horários de pico.\n"
    else:
        obs += "- O link operou dentro da normalidade, suportando a demanda sem saturação severa ou gargalos contínuos.\n"
    
    pdf.multi_cell(0, 6, obs)
    pdf.ln(10)

    # Alertas
    pdf.capitulo_titulo("4. Resumo de Ocorrências e Alertas")
    pdf.tabela_alertas(lista_alertas)

    # Conclusão
    pdf.capitulo_titulo("5. Conclusão")
    pdf.corpo_texto(
        f"A análise dos dados de tráfego coletados no período de {infos_relatorio['periodo'].replace(' a ', ' a ')} "
        f"permite traçar um diagnóstico sobre a conectividade da {infos_relatorio['instituicao']}.\n\n"
        "Recomenda-se a verificação constante dos alertas listados acima (caso existam ocorrências) "
        "para garantir a disponibilidade e a continuidade dos serviços essenciais operados pela unidade."
    )

    return pdf.output(dest='S')