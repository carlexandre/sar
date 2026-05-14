import sqlite3
import json
import os

DB_NAME = "relatorios_popce.db"

def conectar():
    """Cria e retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_NAME)

def init_db():
    """Inicializa o banco de dados criando as tabelas necessárias se não existirem."""
    with conectar() as conn:
        cursor = conn.cursor()
        
        # Tabela de Grupos (ex: GigaFOR, CDC, Interior)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Tabela de Links (Clientes/Instituições)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL,
                nome_instituicao TEXT NOT NULL,
                host_id TEXT NOT NULL,
                item_down_id TEXT NOT NULL,
                item_up_id TEXT NOT NULL,
                capacidade_str TEXT NOT NULL,
                FOREIGN KEY (grupo_id) REFERENCES grupos (id)
            )
        ''')
        
        # Tabela de Histórico de Relatórios Gerados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_relatorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL,
                data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                periodo_texto TEXT NOT NULL,
                caminho_arquivo TEXT NOT NULL,
                FOREIGN KEY (link_id) REFERENCES links (id)
            )
        ''')

        # Tabela de Perfis Comerciais (Faturas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faturas_cadastradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER UNIQUE NOT NULL,
                fatura_para TEXT NOT NULL,
                cnpj TEXT,
                cep TEXT,
                endereco TEXT,
                numero TEXT,
                cidade TEXT,
                uf TEXT,
                email_contato TEXT,
                FOREIGN KEY (link_id) REFERENCES links (id)
            )
        ''')
        
        # Tenta adicionar a coluna caso a tabela já exista de versões anteriores
        try:
            cursor.execute("ALTER TABLE faturas_cadastradas ADD COLUMN email_contato TEXT")
        except sqlite3.OperationalError:
            pass

        # -------------------------------------------------------
        # Tabela de Agendamentos de Email (NOVA)
        # -------------------------------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_ids TEXT NOT NULL,
                dia_envio INTEGER NOT NULL,
                horario TEXT NOT NULL,
                incluir_fatura INTEGER DEFAULT 1,
                fatura_num_prefixo TEXT DEFAULT 'FAT',
                fatura_venc_dia INTEGER DEFAULT 15,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()


# --- FUNÇÕES PARA GRUPOS ---

def adicionar_grupo(nome):
    with conectar() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO grupos (nome) VALUES (?)", (nome,))
            conn.commit()
            return True, "Grupo adicionado com sucesso."
        except sqlite3.IntegrityError:
            return False, "Este grupo já existe."

def listar_grupos():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM grupos ORDER BY nome")
        return cursor.fetchall()


# --- FUNÇÕES PARA LINKS ---

def adicionar_link(grupo_id, nome, host_id, item_down_id, item_up_id, capacidade_str):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO links (grupo_id, nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (grupo_id, nome, host_id, item_down_id, item_up_id, capacidade_str))
        conn.commit()

def listar_links(grupo_id=None):
    with conectar() as conn:
        cursor = conn.cursor()
        if grupo_id:
            cursor.execute('''
                SELECT id, nome_instituicao, host_id, item_down_id, item_up_id, capacidade_str 
                FROM links WHERE grupo_id = ? ORDER BY nome_instituicao
            ''', (grupo_id,))
        else:
            cursor.execute('''
                SELECT l.id, l.nome_instituicao, g.nome as grupo, l.capacidade_str 
                FROM links l
                JOIN grupos g ON l.grupo_id = g.id
                ORDER BY g.nome, l.nome_instituicao
            ''')
        return cursor.fetchall()


# --- FUNÇÕES PARA HISTÓRICO ---

def registrar_relatorio(link_id, periodo_texto, caminho_arquivo):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historico_relatorios (link_id, periodo_texto, caminho_arquivo)
            VALUES (?, ?, ?)
        ''', (link_id, periodo_texto, caminho_arquivo))
        conn.commit()

def listar_historico():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT h.data_geracao, l.nome_instituicao, h.periodo_texto, h.caminho_arquivo
            FROM historico_relatorios h
            JOIN links l ON h.link_id = l.id
            ORDER BY h.data_geracao DESC
        ''')
        return cursor.fetchall()


# --- FUNÇÕES PARA AGENDAMENTOS ---

def salvar_agendamento(link_ids: list, dia_envio: int, horario: str,
                       incluir_fatura: bool, fatura_num_prefixo: str = "FAT",
                       fatura_venc_dia: int = 15) -> int:
    """
    Salva um novo agendamento de envio automático.
    Retorna o ID do agendamento criado.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agendamentos
                (link_ids, dia_envio, horario, incluir_fatura, fatura_num_prefixo, fatura_venc_dia)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            json.dumps(link_ids),
            dia_envio,
            horario,
            int(incluir_fatura),
            fatura_num_prefixo,
            fatura_venc_dia,
        ))
        conn.commit()
        return cursor.lastrowid

def listar_agendamentos(apenas_ativos: bool = False) -> list:
    """
    Retorna todos os agendamentos.
    Colunas: id, link_ids (JSON str), dia_envio, horario,
             incluir_fatura, fatura_num_prefixo, fatura_venc_dia, ativo
    """
    with conectar() as conn:
        cursor = conn.cursor()
        if apenas_ativos:
            cursor.execute('''
                SELECT id, link_ids, dia_envio, horario, incluir_fatura,
                       fatura_num_prefixo, fatura_venc_dia, ativo
                FROM agendamentos
                WHERE ativo = 1
                ORDER BY dia_envio, horario
            ''')
        else:
            cursor.execute('''
                SELECT id, link_ids, dia_envio, horario, incluir_fatura,
                       fatura_num_prefixo, fatura_venc_dia, ativo
                FROM agendamentos
                ORDER BY dia_envio, horario
            ''')
        return cursor.fetchall()

def deletar_agendamento(ag_id: int):
    """Remove permanentemente um agendamento."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agendamentos WHERE id = ?", (ag_id,))
        conn.commit()

def toggle_agendamento(ag_id: int, ativo: bool):
    """Ativa ou pausa um agendamento sem excluí-lo."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE agendamentos SET ativo = ? WHERE id = ?", (int(ativo), ag_id))
        conn.commit()

def buscar_nomes_links(link_ids: list) -> list[str]:
    """Retorna os nomes das instituições para uma lista de IDs."""
    if not link_ids:
        return []
    placeholders = ",".join("?" for _ in link_ids)
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT nome_instituicao FROM links WHERE id IN ({placeholders}) ORDER BY nome_instituicao",
            link_ids,
        )
        return [row[0] for row in cursor.fetchall()]


# Executa a inicialização ao importar o módulo
init_db()