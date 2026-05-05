import os
import time
from datetime import date, timedelta
import database as db
from zabbix_service import conectar_zabbix, processar_dados_instituicao
from gerador_relatorio import criar_pdf_completo
from gerador_fatura import criar_fatura_pdf
from email_service import enviar_email_com_anexos

# 1. CALCULAR O PERÍODO AUTOMATICAMENTE (Mês Anterior Completo)
hoje = date.today()
primeiro_dia_mes_atual = hoje.replace(day=1)
ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

data_vencimento = hoje.replace(day=15) # Vencimento sempre dia 15 do mês atual
competencia_str = primeiro_dia_mes_passado.strftime("%m/%Y")

print(f"🚀 Iniciando Automação Mensal para a competência: {competencia_str}")
print(f"📅 Período de busca: {primeiro_dia_mes_passado.strftime('%d/%m/%Y')} a {ultimo_dia_mes_passado.strftime('%d/%m/%Y')}")

# Conecta no Zabbix via Backend
zapi = conectar_zabbix()

# 2. BUSCAR TODOS OS CLIENTES QUE POSSUEM DADOS DE FATURA CADASTRADOS
with db.conectar() as conn:
    # Seleciona apenas links que têm faturamento cadastrado. 
    # Para adaptar, adicionei uma coluna de 'email_contato' hipotética (pode ser hardcoded por enquanto)
    clientes_para_faturar = conn.execute('''
        SELECT l.id, l.nome_instituicao, f.fatura_para, f.cnpj, f.cep, f.endereco, f.numero, f.cidade, f.uf
        FROM links l
        JOIN faturas_cadastradas f ON l.id = f.link_id
    ''').fetchall()

if not clientes_para_faturar:
    print("Nenhum cliente com perfil de faturamento encontrado.")
    exit()

# 3. EXECUTAR A ROTINA POR CLIENTE
for cliente in clientes_para_faturar:
    link_id = cliente[0]
    nome_inst = cliente[1]
    
    print(f"\n--- Processando {nome_inst} ---")
    
    # Passo A: Gerar Dados do Relatório Técnico
    print("Extraindo métricas do Zabbix...")
    dados_relatorio = processar_dados_instituicao(zapi, link_id, primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    
    if not dados_relatorio:
        print(f"⚠️ Sem tráfego no período para {nome_inst}. Ignorando.")
        continue
        
    print("Gerando PDF do Relatório Técnico...")
    pdf_relatorio = criar_pdf_completo([dados_relatorio], primeiro_dia_mes_passado, ultimo_dia_mes_passado)
    nome_arq_relatorio = f"Relatorio_Tecnico_{nome_inst.replace(' ', '_')}_{competencia_str.replace('/', '-')}.pdf"
    
    # Salva no disco (opcional para ter log)
    caminho_salvo = os.path.join("pdfs_gerados", nome_arq_relatorio)
    with open(caminho_salvo, "wb") as f:
        f.write(pdf_relatorio if isinstance(pdf_relatorio, bytes) else pdf_relatorio.encode('latin-1'))
    db.registrar_relatorio(link_id, f"{primeiro_dia_mes_passado.strftime('%d/%m/%Y')} a {ultimo_dia_mes_passado.strftime('%d/%m/%Y')}", caminho_salvo)

    # Passo B: Gerar Fatura
    print("Gerando PDF da Fatura Comercial...")
    dados_fatura = {
        'cliente_nome': cliente[2], 'cliente_cnpj': cliente[3], 'cliente_cep': cliente[4],
        'cliente_end': cliente[5], 'cliente_num': cliente[6], 'cliente_cidade': cliente[7], 'cliente_uf': cliente[8],
        'fatura_num': f"{primeiro_dia_mes_passado.strftime('%m%Y')}-{link_id}", # Gerador de número único de fatura
        'fatura_data': hoje.strftime("%d/%m/%Y"),
        'fatura_venc': data_vencimento.strftime("%d/%m/%Y")
    }
    pdf_fatura = criar_fatura_pdf(dados_fatura)
    nome_arq_fatura = f"Fatura_Gigafor_{nome_inst.replace(' ', '_')}_{competencia_str.replace('/', '-')}.pdf"

    # Passo C: Disparar Email
    print("Enviando Email...")
    
    # Você precisará ter o e-mail atrelado no banco depois, mas por hora vamos simular:
    email_destino = "noc@instituicao-exemplo.edu.br" 
    
    assunto = f"Fatura e Relatório de Tráfego GigaFOR - {competencia_str} ({nome_inst})"
    corpo_email = f"""Olá equipe da {nome_inst},

Segue em anexo a Fatura Comercial e o Relatório Técnico de Monitoramento de Tráfego referente ao mês de {competencia_str}.

A fatura possui vencimento para o dia {data_vencimento.strftime('%d/%m/%Y')}.

Em caso de dúvidas, nossa equipe do PoP-CE está à disposição.

Atenciosamente,
Sistema de Automatização de Relatórios (SAR)
PoP-CE / RNP
"""
    
    anexos = [
        (nome_arq_relatorio, pdf_relatorio if isinstance(pdf_relatorio, bytes) else pdf_relatorio.encode('latin-1')),
        (nome_arq_fatura, pdf_fatura if isinstance(pdf_fatura, bytes) else pdf_fatura.encode('latin-1'))
    ]
    
    # Descomente a linha abaixo quando colocar as chaves SMTP no arquivo .env
    # sucesso = enviar_email_com_anexos(email_destino, assunto, corpo_email, anexos)
    sucesso = True # Simulação
    
    if sucesso:
        print("✅ Processo concluído e email enviado!")
    else:
        print("❌ Falha no envio do email.")
        
    time.sleep(2) # Pausa amigável para a API do Zabbix e SMTP

print("\n🎉 Rotina de fechamento mensal concluída!")