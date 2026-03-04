import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from fpdf import FPDF
import tempfile
import os

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

# --- 2. FUNÇÃO DE GERAR GRÁFICO (COM SUAVIZAÇÃO) ---
def gerar_grafico_trafego(df, titulo_interface):
    """
    Gera gráfico estilo Zabbix Moderno.
    Aplica resampling se houver muitos pontos para evitar o visual "blocado".
    """
    # Cria uma cópia para não alterar os dados originais fora da função
    df_plot = df.copy()
    
    # SUAVIZAÇÃO VISUAL (Resampling)
    # Se tivermos mais de 1000 pontos (aprox. 1 dia de dados minuto a minuto),
    # agrupa por hora ou 30min para limpar o visual.
    if len(df_plot) > 1000:
        # Garante que 'clock' é índice para o resample funcionar
        df_plot = df_plot.set_index('clock')
        # Calcula a média a cada 30 minutos para suavizar as linhas
        # Se quiser mais detalhe, mude '30min' para '10min'. Se quiser mais liso, '1H'.
        df_plot = df_plot.resample('30min').mean().reset_index()

    plt.style.use('dark_background') 
    
    # Ajuste de tamanho para o PDF
    fig, ax = plt.subplots(figsize=(10, 3.5))
    
    # --- PLOTAGEM ---
    # Linha Verde (Download)
    # linewidth=0.8 é fino o suficiente para ser elegante, mas visível
    ax.plot(df_plot['clock'], df_plot['recv_mbps'], color='#00FF00', linewidth=0.8, label='Download (Entrada)', zorder=2)
    # Preenchimento MUITO leve (alpha=0.15) para não virar um paredão
    ax.fill_between(df_plot['clock'], df_plot['recv_mbps'], color='#00FF00', alpha=0.15, zorder=1)
    
    # Linha Vermelha (Upload)
    ax.plot(df_plot['clock'], df_plot['sent_mbps'], color='#FF3333', linewidth=0.8, label='Upload (Saída)', zorder=2)
    # Preenchimento ainda mais leve ou inexistente no vermelho para não poluir
    ax.fill_between(df_plot['clock'], df_plot['sent_mbps'], color='#FF3333', alpha=0.1, zorder=1)
    
    # --- ESTÉTICA ---
    ax.set_title(f"Tráfego: {titulo_interface}", fontsize=10, color='white', pad=10)
    ax.set_ylabel("Mbps", color='white', fontsize=9)
    
    # Grid discreto
    ax.grid(True, which='major', color='#444444', linestyle='--', linewidth=0.5, alpha=0.5)
    
    # Legenda
    ax.legend(loc='upper right', fontsize=8, facecolor='black', framealpha=0.7)
    
    # Eixo X (Datas)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.xticks(rotation=45, fontsize=8)
    plt.yticks(fontsize=8)
    
    # Limites e Limpeza
    if not df_plot.empty:
        ax.set_xlim(df_plot['clock'].min(), df_plot['clock'].max())
        ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    
    # Salva
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name, dpi=150, facecolor='black')
    plt.close()
    
    return temp_file.name

# --- 3. CLASSE DO PDF (ESTRUTURA) ---
class RelatorioPDF(FPDF):
    def header(self):
        # self.image('logo_pop.png', 10, 8, 33) # Descomente se tiver logo
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'RELATÓRIO TÉCNICO DE MONITORAMENTO', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Rede GigaFOR / PoP-CE', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def capitulo_titulo(self, titulo):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, titulo, 0, 1, 'L', fill=True)
        self.ln(4)

    def corpo_texto(self, texto):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, texto)
        self.ln(5)

    def tabela_alertas(self, lista_alertas):
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(200, 200, 200)
        self.cell(35, 7, 'Data', 1, 0, 'C', True)
        self.cell(85, 7, 'Alerta (Trigger)', 1, 0, 'C', True)
        self.cell(30, 7, 'Duração', 1, 0, 'C', True)
        self.cell(40, 7, 'Campus', 1, 1, 'C', True)
        
        self.set_font('Arial', '', 9)
        if not lista_alertas:
            self.ln(7)
            self.cell(190, 7, 'Nenhuma ocorrência crítica registrada.', 1, 1, 'C')
        else:
            self.ln(7) # Pula linha do cabeçalho
            for alerta in lista_alertas:
                # Corta textos longos
                trig = str(alerta.get('trigger', '-'))
                if len(trig) > 45: trig = trig[:42] + "..."
                
                host = str(alerta.get('host', '-'))
                if len(host) > 22: host = host[:19] + "..."

                self.cell(35, 7, str(alerta.get('data', '-')), 1, 0, 'C')
                self.cell(85, 7, trig, 1, 0, 'L')
                self.cell(30, 7, str(alerta.get('duracao', '-')), 1, 0, 'C')
                self.cell(40, 7, host, 1, 1, 'C')
        self.ln(10)

# --- 4. FUNÇÃO PRINCIPAL ---
def criar_pdf_completo(dados_trafego, infos_relatorio, lista_alertas=None, estatisticas=None):
    pdf = RelatorioPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Introdução
    pdf.capitulo_titulo(f"1. Relatório: {infos_relatorio['instituicao']}")
    pdf.corpo_texto(f"Período de Referência: {infos_relatorio['periodo']}")
    pdf.ln(5)
    pdf.capitulo_titulo("2. Introdução")
    pdf.corpo_texto(TEXTOS['introducao'].format(instituicao=infos_relatorio['instituicao']))
    pdf.capitulo_titulo("2.1. Sobre a RNP")
    pdf.corpo_texto(TEXTOS['sobre_rnp'])
    pdf.capitulo_titulo("2.2. Sobre a GigaFOR")
    pdf.corpo_texto(TEXTOS['sobre_gigafor'])
    
    pdf.add_page() 

    # Análise Gráfica
    pdf.capitulo_titulo("3. Análise de Tráfego")
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, f"Link Contratado/Capacidade: {infos_relatorio.get('capacidade', '1 Gbps')}", 0, 1)
    pdf.cell(0, 6, f"Interface Monitorada: {infos_relatorio['interface']}", 0, 1)
    pdf.ln(5)
    
    # Gera imagem SUAVIZADA
    caminho_img = gerar_grafico_trafego(dados_trafego, infos_relatorio['interface'])
    pdf.image(caminho_img, x=10, w=190)
    os.remove(caminho_img)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, "Legenda: Verde = Download (Entrada) | Vermelho = Upload (Saída)", 0, 1, 'C')
    pdf.ln(10)

    # Estatísticas (Usa os valores exatos calculados no app.py)
    if estatisticas:
        media_in = estatisticas['media_in']
        media_out = estatisticas['media_out']
        max_in = estatisticas['max_in']
        max_out = estatisticas['max_out']
    else:
        # Fallback de segurança
        media_in = dados_trafego['recv_mbps'].mean()
        media_out = dados_trafego['sent_mbps'].mean()
        max_in = dados_trafego['recv_mbps'].max()
        max_out = dados_trafego['sent_mbps'].max()
    
    pdf.capitulo_titulo("Análise Técnica dos Dados")
    pdf.set_font('Arial', '', 10)
    
    stats = (
        f"- Tráfego Médio (Download): {media_in:.2f} Mbps\n"
        f"- Tráfego Médio (Upload):   {media_out:.2f} Mbps\n"
        f"- Pico Máximo (Download):   {max_in:.2f} Mbps\n"
        f"- Pico Máximo (Upload):     {max_out:.2f} Mbps\n"
    )
    pdf.multi_cell(0, 6, stats)
    pdf.ln(5)
    
    obs = "Observações:\n"
    if max_in > 900 or max_out > 900:
        obs += "- ALERTA DE SATURAÇÃO: O tráfego atingiu níveis próximos à capacidade física do link (>90%).\n"
        obs += "- Nota-se picos elevados de utilização.\n"
    else:
        obs += "- O link operou dentro da normalidade, suportando a demanda sem saturação severa.\n"
    
    pdf.multi_cell(0, 6, obs)
    pdf.ln(10)

    # Alertas
    pdf.capitulo_titulo("4. Resumo de Ocorrências e Alertas")
    pdf.tabela_alertas(lista_alertas)

    # Conclusão
    pdf.capitulo_titulo("5. Conclusão")
    pdf.corpo_texto(
        "A análise dos dados demonstra o perfil de utilização do link. "
        "Recomenda-se a verificação dos alertas listados acima para garantir a continuidade dos serviços."
    )

    return pdf.output(dest='S')