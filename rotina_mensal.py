"""
rotina_mensal.py
================
Motor de execução dos envios mensais automáticos. Pode ser chamado:
  - Sem argumentos: processa TODOS os clientes com perfil de faturamento.
  - Com --link-ids '[1,2,3]': processa apenas os IDs informados.
  - Com --incluir-fatura: gera e anexa a fatura além do relatório técnico.

Exemplos de uso pelo cron (gerado pelo agendamento_service.py):
  python rotina_mensal.py --link-ids '[1,2]' --incluir-fatura --fatura-prefixo 'FAT' --fatura-venc-dia 15
  python rotina_mensal.py   # modo legado — todos os clientes
"""

import os
import sys
import time
import json
import argparse
from datetime import date, timedelta

import database as db
from zabbix_service import conectar_zabbix, processar_dados_instituicao
from gerador_relatorio import criar_pdf_completo
from gerador_fatura import criar_fatura_pdf
from email_service import enviar_email_com_anexos

# ------------------------------------------------------------------
# 1. ARGUMENTOS DE LINHA DE COMANDO
# ------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="SAR — Rotina de Fechamento Mensal Automatizado"
)
parser.add_argument(
    "--link-ids",
    type=str,
    default=None,
    metavar="JSON",
    help="Array JSON de IDs de links a processar. Ex: '[1,2,3]'. "
         "Se omitido, processa todos os clientes com perfil de fatura.",
)
parser.add_argument(
    "--incluir-fatura",
    action="store_true",
    default=False,
    help="Se presente, gera e anexa a Fatura Comercial no e-mail.",
)
parser.add_argument(
    "--fatura-prefixo",
    type=str,
    default="FAT",
    metavar="PREFIX",
    help="Prefixo do número da fatura. Padrão: FAT",
)
parser.add_argument(
    "--fatura-venc-dia",
    type=int,
    default=15,
    metavar="DIA",
    help="Dia do mês para o vencimento da fatura. Padrão: 15",
)
args = parser.parse_args()

# Garante a pasta de saída
PASTA_PDFS = "pdfs_gerados"
os.makedirs(PASTA_PDFS, exist_ok=True)

# ------------------------------------------------------------------
# 2. CALCULAR O PERÍODO (Mês Anterior Completo)
# ------------------------------------------------------------------
hoje = date.today()
primeiro_dia_mes_atual = hoje.replace(day=1)
ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)

data_vencimento = hoje.replace(day=args.fatura_venc_dia)
competencia_str = primeiro_dia_mes_passado.strftime("%m/%Y")

print(f"🚀 Iniciando Automação Mensal — Competência: {competencia_str}")
print(
    f"📅 Período: {primeiro_dia_mes_passado.strftime('%d/%m/%Y')} "
    f"a {ultimo_dia_mes_passado.strftime('%d/%m/%Y')}"
)
print(f"📎 Incluir fatura: {'Sim' if args.incluir_fatura else 'Não'}")

# ------------------------------------------------------------------
# 3. DETERMINAR CLIENTES A PROCESSAR
# ------------------------------------------------------------------
if args.link_ids:
    # Modo agendado: apenas os IDs especificados que tiverem perfil de fatura
    ids_solicitados = json.loads(args.link_ids)
    print(f"🎯 Modo seletivo — {len(ids_solicitados)} link(s): {ids_solicitados}")

    placeholders = ",".join("?" for _ in ids_solicitados)
    with db.conectar() as conn:
        clientes_para_processar = conn.execute(f'''
            SELECT l.id, l.nome_instituicao,
                   COALESCE(f.fatura_para, l.nome_instituicao),
                   f.cnpj, f.cep, f.endereco, f.numero, f.cidade, f.uf,
                   COALESCE(f.email_contato, '')
            FROM links l
            LEFT JOIN faturas_cadastradas f ON l.id = f.link_id
            WHERE l.id IN ({placeholders})
            ORDER BY l.nome_instituicao
        ''', ids_solicitados).fetchall()
else:
    # Modo legado: todos os clientes com perfil de faturamento
    print("🔄 Modo global — processando todos os clientes com perfil de fatura.")
    with db.conectar() as conn:
        clientes_para_processar = conn.execute('''
            SELECT l.id, l.nome_instituicao,
                   f.fatura_para,
                   f.cnpj, f.cep, f.endereco, f.numero, f.cidade, f.uf,
                   COALESCE(f.email_contato, '')
            FROM links l
            JOIN faturas_cadastradas f ON l.id = f.link_id
            ORDER BY l.nome_instituicao
        ''').fetchall()

if not clientes_para_processar:
    print("⚠️  Nenhum cliente encontrado para processar. Encerrando.")
    sys.exit(0)

print(f"✅ {len(clientes_para_processar)} cliente(s) a processar.\n")

# ------------------------------------------------------------------
# 4. CONECTAR NO ZABBIX
# ------------------------------------------------------------------
zapi = conectar_zabbix()

# ------------------------------------------------------------------
# 5. EXECUTAR A ROTINA POR CLIENTE
# ------------------------------------------------------------------
for cliente in clientes_para_processar:
    (link_id, nome_inst, fatura_para,
     cnpj, cep, endereco, numero, cidade, uf, email_destino) = cliente

    print(f"--- Processando: {nome_inst} ---")

    # ── Passo A: Relatório Técnico ────────────────────────────────
    print("  📊 Extraindo métricas do Zabbix...")
    try:
        dados_relatorio = processar_dados_instituicao(
            zapi, link_id, primeiro_dia_mes_passado, ultimo_dia_mes_passado
        )
    except Exception as e:
        print(f"  ❌ Erro ao processar Zabbix: {e}. Pulando.")
        continue

    if not dados_relatorio:
        print(f"  ⚠️  Sem tráfego no período. Pulando.")
        continue

    print("  📄 Gerando PDF do Relatório Técnico...")
    pdf_relatorio = criar_pdf_completo(
        [dados_relatorio], primeiro_dia_mes_passado, ultimo_dia_mes_passado
    )
    if not isinstance(pdf_relatorio, bytes):
        pdf_relatorio = pdf_relatorio.encode("latin-1")

    nome_arq_relatorio = (
        f"Relatorio_Tecnico_{nome_inst.replace(' ', '_')}"
        f"_{competencia_str.replace('/', '-')}.pdf"
    )
    caminho_salvo = os.path.join(PASTA_PDFS, nome_arq_relatorio)

    with open(caminho_salvo, "wb") as f:
        f.write(pdf_relatorio)

    db.registrar_relatorio(
        link_id,
        f"{primeiro_dia_mes_passado.strftime('%d/%m/%Y')} a {ultimo_dia_mes_passado.strftime('%d/%m/%Y')}",
        caminho_salvo,
    )

    # ── Passo B: Fatura (opcional) ────────────────────────────────
    anexos = [(nome_arq_relatorio, pdf_relatorio)]

    if args.incluir_fatura:
        print("  🧾 Gerando PDF da Fatura Comercial...")
        numero_fatura = (
            f"{args.fatura_prefixo}-"
            f"{primeiro_dia_mes_passado.strftime('%m%Y')}-{link_id}"
        )
        dados_fatura = {
            "cliente_nome": fatura_para,
            "cliente_cnpj": cnpj or "",
            "cliente_cep": cep or "",
            "cliente_end": endereco or "",
            "cliente_num": numero or "",
            "cliente_cidade": cidade or "",
            "cliente_uf": uf or "",
            "fatura_num": numero_fatura,
            "fatura_data": hoje.strftime("%d/%m/%Y"),
            "fatura_venc": data_vencimento.strftime("%d/%m/%Y"),
        }
        try:
            pdf_fatura = criar_fatura_pdf(dados_fatura)
            if not isinstance(pdf_fatura, bytes):
                pdf_fatura = pdf_fatura.encode("latin-1")

            nome_arq_fatura = (
                f"Fatura_Gigafor_{nome_inst.replace(' ', '_')}"
                f"_{competencia_str.replace('/', '-')}.pdf"
            )
            anexos.append((nome_arq_fatura, pdf_fatura))
        except Exception as e:
            print(f"  ⚠️  Falha ao gerar fatura: {e}. Enviando só o relatório.")

    # ── Passo C: Envio de E-mail ──────────────────────────────────
    if not email_destino:
        print(f"  ⚠️  E-mail não cadastrado para {nome_inst}. Pulando envio.")
        continue

    print(f"  📧 Enviando e-mail para {email_destino}...")

    assunto = (
        f"Fatura e Relatório de Tráfego GigaFOR — {competencia_str} ({nome_inst})"
        if args.incluir_fatura
        else f"Relatório de Tráfego GigaFOR — {competencia_str} ({nome_inst})"
    )

    corpo_email = f"""Olá, equipe da {nome_inst},

Segue em anexo {'a Fatura Comercial e ' if args.incluir_fatura else ''}o Relatório Técnico de Monitoramento de Tráfego referente ao mês de {competencia_str}.
"""
    if args.incluir_fatura:
        corpo_email += f"\nA fatura possui vencimento para o dia {data_vencimento.strftime('%d/%m/%Y')}.\n"

    corpo_email += """
Em caso de dúvidas, nossa equipe do PoP-CE está à disposição.

Atenciosamente,
Sistema de Automatização de Relatórios (SAR)
PoP-CE / RNP
"""

    sucesso = enviar_email_com_anexos(email_destino, assunto, corpo_email, anexos)

    if sucesso:
        print(f"  ✅ E-mail enviado com sucesso!")
    else:
        print(f"  ❌ Falha no envio do e-mail.")

    time.sleep(2)  # Pausa amigável para API do Zabbix e SMTP

print(f"\n🎉 Rotina de fechamento mensal concluída — {competencia_str}")