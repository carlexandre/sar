# SAR - Sistema de Automatização de Relatórios 📊

O **SAR** é uma aplicação web desenvolvida em Python com Streamlit para automatizar a extração de dados e a geração de relatórios em PDF de tráfego dos links monitorados no Zabbix (PoP-CE / RNP).

## ✨ Funcionalidades

* **Gerar Relatórios:** Extrai dados de tráfego (Histórico e Tendências) e alertas de downtime da API do Zabbix e compila tudo num PDF formatado e com gráficos suavizados.

* **Gestão de Links:** Permite cadastrar grupos (ex: GigaFOR, CDC) e vincular hosts do Zabbix com as suas respetivas interfaces de Entrada/Saída e capacidade de banda.

* **Histórico Automático:** Mantém uma base de dados local (`SQLite`) com os registos de todos os relatórios gerados para download rápido a qualquer momento.

## 🚀 Como Instalar e Rodar Localmente

### 1. Pré-requisitos

* Python 3.8 ou superior instalado.

* Acesso à rede onde o servidor Zabbix está alojado.

### 2. Instalação do Ambiente

É altamente recomendado o uso de um ambiente virtual para não causar conflito de bibliotecas. Abra o terminal na pasta do projeto e execute:

```bash
# Cria o ambiente virtual chamado 'venv'
python -m venv venv

# Ativa o ambiente virtual (No Windows)
venv\Scripts\activate

# Ativa o ambiente virtual (No Linux/Mac)
source venv/bin/activate

# Instala as dependências necessárias
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente (.env)

Crie um ficheiro chamado `.env` na pasta raiz do projeto (mesmo local do `app.py`) e insira as suas credenciais do Zabbix:

```env
ZABBIX_URL="[https://seu-zabbix.rnp.br](https://seu-zabbix.rnp.br)"
ZABBIX_USER="seu_usuario"
ZABBIX_PASSWORD="sua_senha"
```

## 🔒 Como Obter o Certificado do Zabbix

Como o servidor Zabbix do PoP-CE/RNP pode utilizar certificados internos para conexões HTTPS (SSL/TLS), a API do Python rejeitará a conexão por segurança caso não tenha o certificado instalado. Para o sistema funcionar corretamente, você deve exportar o certificado e colocá-lo na pasta do projeto.

**Passo a passo (Google Chrome / Edge):**

1. Abra o navegador e aceda à página web do seu Zabbix.
2. Clique no ícone de **Cadeado** ao lado esquerdo da URL (na barra de endereços).
3. Clique em **"A conexão é segura"** (ou "Connection is secure").
4. Clique em **"O certificado é válido"** (ou no ícone do certificado).
5. Na janela que se abre, vá ao separador **"Detalhes"**.
6. Clique no botão **"Exportar"**.
7. Na hora de guardar, escolha o formato: **Certificado X.509 codificado na base 64 (*.crt, *.cer)**.
8. Guarde o ficheiro na pasta **raiz do projeto** e **renomeie-o** exatamente para:
   👉 `zabbix-certificado.crt`

*Nota: Se o ficheiro não for encontrado, a aplicação tentará forçar uma conexão insegura emitindo um aviso na consola, mas ter o certificado é a prática recomendada.*

## ▶️ Executando a Aplicação

Com o ambiente ativado, o `.env` configurado e o certificado na pasta, inicie o servidor do Streamlit:

```bash
streamlit run app.py
```

O seu navegador irá abrir automaticamente a aplicação no endereço `http://localhost:8501`.

## 📂 Estrutura do Projeto

* `app.py`: Arquivo principal, contém a interface gráfica, roteamento e a integração entre Zabbix e PDF.
* `database.py`: Módulo responsável por criar e gerir o banco de dados `relatorios_popce.db` em SQLite (Grupos, Links e Histórico).
* `gerador_relatorio.py`: Módulo que contém a lógica de formatação do FPDF2, textos base e a geração visual dos gráficos de tráfego com Matplotlib.
* `requirements.txt`: Lista de bibliotecas Python necessárias.
* `assets/logo/`: Pasta onde devem ficar as imagens `pop-ce-logo-preto.png` e `pop-ce-logo-branca.png`.
* `pdfs_gerados/`: Pasta criada automaticamente para armazenar os relatórios finalizados.