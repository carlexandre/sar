from fpdf import FPDF
import os

def _enc(texto: str) -> str:
    """Converte texto para latin-1, evitando erros de encoding no FPDF."""
    try:
        return str(texto).encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return str(texto)

class FaturaPDF(FPDF):
    pass # As faturas geralmente ocupam apenas uma folha rígida, não requer Header repetitivo

def criar_fatura_pdf(dados: dict) -> bytes:
    """Gera a fatura em PDF idêntica ao modelo fornecido."""
    pdf = FaturaPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    
    # ==========================================
    # LOGO E TÍTULO PRINCIPAL
    # ==========================================
    logo_path = "assets/logo/gigafor-logo.png"
    if os.path.exists(logo_path):
        # Travamos a largura em 45 e a altura em 20 para se alinhar
        # milimetricamente com a altura da caixa de título ao lado.
        pdf.image(logo_path, x=10, y=10, w=45, h=20)
    else:
        # Fallback caso a logo não esteja na pasta ainda
        pdf.set_xy(10, 10)
        pdf.set_fill_color(30, 100, 180)
        pdf.rect(10, 10, 45, 20, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(45, 20, 'GIGAFOR', border=1, align='C', fill=True)
        
    pdf.set_xy(55, 10)
    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(145, 20, _enc('CONECTIVIDADE A REDE GIGAFOR'), border=1, align='C')
    
    # ==========================================
    # BLOCO 1: DE / FATURA PARA
    # ==========================================
    pdf.set_xy(10, 35)
    pdf.set_font('Arial', '', 9)
    
    # Linha 1 (Nomes)
    pdf.cell(12, 5, _enc("DE:"), border='LT')
    pdf.cell(73, 5, _enc("ASSOCIAÇÃO GIGAFOR"), border='RT')
    pdf.cell(28, 5, _enc("FATURA PARA:"), border='LT')
    
    nome_cliente = dados.get('cliente_nome', '')
    # Diminui a fonte levemente se o nome for gigante para não quebrar a borda
    pdf.set_font('Arial', '', 8 if len(nome_cliente) > 35 else 9)
    pdf.cell(77, 5, _enc(nome_cliente), border='RT', ln=1)
    pdf.set_font('Arial', '', 9) # Volta pro normal
    
    # Linha 2 (CNPJs)
    pdf.cell(12, 5, _enc("CNPJ:"), border='L')
    pdf.cell(73, 5, _enc("57.735.222/0001-70"), border='R')
    pdf.cell(12, 5, _enc("CNPJ:"), border='L')
    pdf.cell(93, 5, _enc(f"{dados.get('cliente_cnpj', '')}"), border='R', ln=1)
    
    # Linha 3 (Endereços)
    pdf.cell(18, 5, _enc("Endereço:"), border='L')
    pdf.cell(42, 5, _enc("AV. HUMBERTO MONTE"), border=0)
    pdf.cell(8, 5, _enc("Nº:"), border=0)
    pdf.cell(17, 5, _enc("S/N"), border='R')
    
    pdf.cell(18, 5, _enc("Endereço:"), border='L')
    pdf.cell(50, 5, _enc(f"{dados.get('cliente_end', '')}"), border=0)
    pdf.cell(8, 5, _enc("Nº:"), border=0)
    pdf.cell(29, 5, _enc(f"{dados.get('cliente_num', '')}"), border='R', ln=1)

    # Linha 4 (Cidades e Estados)
    pdf.cell(15, 5, _enc("Cidade:"), border='L')
    pdf.cell(45, 5, _enc("FORTALEZA"), border=0)
    pdf.cell(12, 5, _enc("Estado:"), border=0)
    pdf.cell(13, 5, _enc("CE"), border='R')
    
    pdf.cell(15, 5, _enc("Cidade:"), border='L')
    pdf.cell(50, 5, _enc(f"{dados.get('cliente_cidade', '')}"), border=0)
    pdf.cell(15, 5, _enc("Estado:"), border=0)
    pdf.cell(25, 5, _enc(f"{dados.get('cliente_uf', '')}"), border='R', ln=1)
    
    # Linha 5 (CEP e borda inferior)
    pdf.cell(12, 5, _enc("CEP:"), border='LB')
    pdf.cell(73, 5, _enc("60.440-554"), border='RB')
    pdf.cell(12, 5, _enc("CEP:"), border='LB')
    pdf.cell(93, 5, _enc(f"{dados.get('cliente_cep', '')}"), border='RB', ln=1)
    
    pdf.ln(4)
    
    # ==========================================
    # BLOCO 2: INFORMAÇÕES DA FATURA
    # ==========================================
    pdf.cell(25, 6, _enc("Nº da fatura:"), border='LTB')
    pdf.cell(165, 6, _enc(f"{dados.get('fatura_num', '')}"), border='RTB', ln=1)
    
    pdf.cell(30, 6, _enc("Data da fatura:"), border='LTB')
    pdf.cell(65, 6, _enc(f"{dados.get('fatura_data', '')}"), border='RTB')
    pdf.cell(25, 6, _enc("Vencimento:"), border='LTB')
    pdf.cell(70, 6, _enc(f"{dados.get('fatura_venc', '')}"), border='RTB', ln=1)
    
    pdf.ln(4)
    
    # ==========================================
    # BLOCO 3: TABELA DE PRODUTOS
    # ==========================================
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(115, 8, _enc("Descrição do produto/serviço:"), border=1, align='C')
    pdf.cell(20, 8, _enc("QTD:"), border=1, align='C')
    pdf.cell(30, 8, _enc("Preço unitário:"), border=1, align='C')
    pdf.cell(25, 8, _enc("Total:"), border=1, align='C', ln=1)
    
    pdf.set_font('Arial', '', 9)
    
    # Produto 1
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    pdf.multi_cell(115, 5, _enc("\nTIPO A - Referente à prestação de serviço de conectividade, integrante da\nRedecomep Gigafor\n "), border='LBR', align='C')
    h = pdf.get_y() - y_start
    pdf.set_xy(x_start + 115, y_start)
    pdf.cell(20, h, _enc("1"), border=1, align='C')
    pdf.cell(30, h, _enc("R$:6.000,00"), border=1, align='C')
    pdf.cell(25, h, _enc("R$:6.000,00"), border=1, align='C', ln=1)
    
    # Produto 2
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    pdf.multi_cell(115, 5, _enc("\nTIPO C - Referente à prestação de serviço de conectividade, integrante da\nRedecomep Gigafor\n "), border='LBR', align='C')
    h = pdf.get_y() - y_start
    pdf.set_xy(x_start + 115, y_start)
    pdf.cell(20, h, _enc("1"), border=1, align='C')
    pdf.cell(30, h, _enc("R$:1.500,00"), border=1, align='C')
    pdf.cell(25, h, _enc("R$:1.500,00"), border=1, align='C', ln=1)
    
    # Preenchimento em branco (para empurrar o total para baixo)
    h_blank = 45
    pdf.cell(115, h_blank, "", border=1)
    pdf.cell(20, h_blank, "", border=1)
    pdf.cell(30, h_blank, "", border=1)
    pdf.cell(25, h_blank, "", border=1, ln=1)
    
    # ==========================================
    # BLOCO 4: RODAPÉ E TOTAIS
    # ==========================================
    # Alinhamento exato com a tabela de produtos:
    # 115mm (largura da Coluna Descrição) -> Termos de Pagamento
    # 75mm  (20+30+25 das outras colunas) -> Subtotal / Total
    w_termos = 115
    w_totais = 75
    x_termos = 10
    x_totais = 125

    pdf.set_font('Arial', 'B', 10)
    
    # Cabeçalhos dos blocos
    pdf.set_x(x_termos)
    pdf.cell(w_termos, 6, _enc("Termos de Pagamento:"), border='LTR', align='C')
    pdf.set_x(x_totais)
    pdf.cell(w_totais, 6, _enc("Subtotal:"), border='LTR', align='C', ln=1)
    
    # Conteúdo dos blocos
    y_start = pdf.get_y()
    
    # Sem quebra de linha extra no final para padronizar altura exata
    termos = "DEPOSITO BANCARIO:\nBANCO: BANCO DO BRASIL\nAGÊNCIA: 4439-3\nCONTA CORRENTE: 41468-9"
    
    pdf.set_font('Arial', '', 9)
    pdf.set_x(x_termos)
    # multi_cell de 4 linhas com altura 5 = 20mm de altura exatos
    pdf.multi_cell(w_termos, 5, _enc(termos), border='LBR', align='L')
    
    # Valores dos totais (Altura fixa equivalente aos 20mm do bloco de termos: 5 + 5 + 10)
    pdf.set_xy(x_totais, y_start)
    pdf.cell(w_totais, 5, _enc("R$:7.500,00"), border='LR', align='C', ln=1)
    
    pdf.set_x(x_totais)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(w_totais, 5, _enc("Total:"), border='LR', align='C', ln=1)
    
    pdf.set_x(x_totais)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(w_totais, 10, _enc("R$:7.500,00"), border='LBR', align='C', ln=1)
    
    saida = pdf.output(dest='S')
    if isinstance(saida, str):
        return saida.encode('latin-1')
    return bytes(saida)