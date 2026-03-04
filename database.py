import sqlite3
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

# Executa a inicialização ao importar o módulo
init_db()