"""
agendamento_service.py
======================
Responsável por sincronizar os agendamentos salvos no banco de dados com
o crontab do sistema Linux. Cada agendamento gera uma linha no crontab
marcada com SAR_MARKER para que possam ser identificadas e atualizadas.
"""

import subprocess
import sys
import os
import json

import database as db

# Marca que identifica as linhas gerenciadas pelo SAR no crontab
SAR_MARKER = "# SAR-MANAGED"

# Caminho absoluto para o script de rotina mensal (mesmo diretório deste arquivo)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "rotina_mensal.py")
PYTHON_PATH = sys.executable


# ------------------------------------------------------------------
# Funções de baixo nível para o crontab
# ------------------------------------------------------------------

def verificar_cron_disponivel() -> bool:
    """Verifica se o cron está disponível no sistema."""
    try:
        subprocess.run(["crontab", "-l"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_crontab() -> str:
    """Lê o crontab atual do usuário. Retorna string vazia se vazio ou ausente."""
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=10
        )
        # returncode 1 com "no crontab for user" é normal (sem entradas ainda)
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def _set_crontab(content: str) -> tuple[bool, str]:
    """Escreve o novo conteúdo no crontab. Retorna (sucesso, mensagem)."""
    try:
        proc = subprocess.run(
            ["crontab", "-"],
            input=content,
            text=True,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return True, "Crontab atualizado com sucesso."
        return False, proc.stderr.strip() or "Erro desconhecido ao gravar o crontab."
    except FileNotFoundError:
        return False, "Comando 'crontab' não encontrado. Verifique se o cron está instalado."
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------
# Funções públicas
# ------------------------------------------------------------------

def atualizar_crontab() -> tuple[bool, str]:
    """
    Sincroniza os agendamentos ativos do banco com o crontab.
    Remove todas as entradas SAR existentes e recria a partir do banco.
    Retorna (sucesso, mensagem).
    """
    crontab_atual = _get_crontab()

    # Mantém apenas linhas que NÃO são gerenciadas pelo SAR
    linhas_usuario = [
        linha for linha in crontab_atual.splitlines()
        if SAR_MARKER not in linha
    ]

    # Gera as novas entradas cron a partir dos agendamentos ativos
    agendamentos = db.listar_agendamentos(apenas_ativos=True)
    novas_entradas = []

    for ag in agendamentos:
        ag_id, link_ids_json, dia, horario, incluir_fatura, fatura_prefixo, fatura_venc_dia, _ = ag
        hora, minuto = horario.split(":")

        # Monta os argumentos do script
        args = [f"--link-ids '{link_ids_json}'"]
        if incluir_fatura:
            args.append("--incluir-fatura")
            args.append(f"--fatura-prefixo '{fatura_prefixo or 'FAT'}'")
            args.append(f"--fatura-venc-dia {fatura_venc_dia or 15}")

        args_str = " ".join(args)

        # Formato cron: minuto hora dia_mes mês dia_semana comando
        linha_cron = (
            f"{minuto} {hora} {dia} * * "
            f"{PYTHON_PATH} {SCRIPT_PATH} {args_str} "
            f"{SAR_MARKER} [ID:{ag_id}]"
        )
        novas_entradas.append(linha_cron)

    # Une linhas antigas do usuário com as novas do SAR
    linhas_finais = [l for l in linhas_usuario if l.strip()] + novas_entradas
    conteudo_final = "\n".join(linhas_finais)
    if conteudo_final and not conteudo_final.endswith("\n"):
        conteudo_final += "\n"

    return _set_crontab(conteudo_final)


def ler_entradas_sar() -> list[str]:
    """Retorna apenas as linhas SAR presentes no crontab atual (para diagnóstico)."""
    crontab = _get_crontab()
    return [linha for linha in crontab.splitlines() if SAR_MARKER in linha]


def preview_cron_expressao(dia: int, horario: str) -> str:
    """Retorna uma descrição legível da expressão cron para exibir na UI."""
    hora, minuto = horario.split(":")
    return f"{minuto} {hora} {dia} * *  →  Todo dia {dia} de cada mês, às {horario}"