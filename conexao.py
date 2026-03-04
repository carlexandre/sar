import os
import sys
import requests
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv

# Carrega variáveis
load_dotenv()

ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_USER = os.getenv("ZABBIX_USER")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD")

# Nome do arquivo que você acabou de exportar
CERT_PATH = "zabbix-certificado.crt"

if not all([ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD]):
    sys.exit("ERRO: Variáveis de ambiente faltando.")

# Configura a sessão
session = requests.Session()

# LÓGICA DE SEGURANÇA:
# Se o arquivo do certificado existir na pasta, usa ele.
# Se não, avisa e usa o modo inseguro (útil se você trocar de PC).
if os.path.exists(CERT_PATH):
    print(f"🔒 Usando certificado de segurança: {CERT_PATH}")
    session.verify = CERT_PATH
else:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("⚠️ AVISO: Certificado não encontrado. Rodando em modo INSEGURO.")
    session.verify = False

print(f"Conectando em: {ZABBIX_URL}...")

try:
    zapi = ZabbixAPI(ZABBIX_URL, session=session)
    zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
    
    print(f"✅ Conectado com sucesso! (API Versão: {zapi.api_version()})")
    print(f"Usuário logado: {ZABBIX_USER}")

except Exception as e:
    print(f"❌ Erro: {e}")