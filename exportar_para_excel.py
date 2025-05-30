# exportar_para_excel.py
import os
import pandas as pd
from dotenv import load_dotenv
import requests
from msal import PublicClientApplication # Usamos PublicClientApplication para autenticação de usuário
from utils import conectar_banco # Certifique-se de que utils.py esteja acessível

# Carrega as variáveis de ambiente. No Railway, elas já estarão disponíveis.
load_dotenv()

# --- Credenciais e configurações do OneDrive (Azure AD) ---
# Estas variáveis serão lidas do ambiente do Railway (e do .env para testes locais)
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID") # Pode ser "common" para contas pessoais
ONEDRIVE_REFRESH_TOKEN = os.getenv("ONEDRIVE_REFRESH_TOKEN")

# Para contas pessoais, o 'authority' pode ser "https://login.microsoftonline.com/common"
# Para contas organizacionais, use f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}" if TENANT_ID else "https://login.microsoftonline.com/common"

# Escopos de recurso. 'offline_access' NÃO deve ser incluído aqui.
# O MSAL lida com ele automaticamente para a renovação do token.
SCOPES = ["Files.ReadWrite.All"] 

def exportar_csvs():
    """
    Conecta-se ao banco de dados PostgreSQL, lê as tabelas 'registros' e 'demandas',
    e as salva como arquivos CSV temporários na pasta 'backup'.
    """
    conn = conectar_banco()
    if not conn:
        print("Erro ao conectar ao banco de dados.")
        return False

    try:
        # Lendo os dados das tabelas do PostgreSQL
        registros = pd.read_sql("SELECT * FROM registros", conn)
        demandas = pd.read_sql("SELECT * FROM demandas", conn)
        
        # Cria a pasta 'backup' se ela não existir
        os.makedirs("backup", exist_ok=True)
        
        # Salva os DataFrames como arquivos CSV
        registros.to_csv("backup/registros.csv", index=False)
        demandas.to_csv("backup/demandas.csv", index=False)
        print("Arquivos CSV gerados com sucesso na pasta 'backup'.")
        return True
    except Exception as e:
        print(f"Erro ao exportar CSVs do banco de dados: {e}")
        return False
    finally:
        if conn:
            conn.close()

def autenticar_graph_com_refresh_token():
    """
    Usa o refresh token armazenado para obter um novo access token para o Microsoft Graph API.
    """
    if not CLIENT_ID or not ONEDRIVE_REFRESH_TOKEN:
        print("Erro: CLIENT_ID ou ONEDRIVE_REFRESH_TOKEN não encontrados nas variáveis de ambiente.")
        print("Certifique-se de que configurou todas as variáveis necessárias no Railway.")
        print("Para obter o ONEDRIVE_REFRESH_TOKEN, execute o script 'get_onedrive_token.py' localmente.")
        return None

    # Usamos PublicClientApplication porque estamos renovando um token de usuário
    app = PublicClientApplication(
        CLIENT_ID, authority=AUTHORITY
    )

    # Tenta adquirir um novo token de acesso usando o refresh token
    # O MSAL gerencia o cache internamente e tentará usar o refresh token para renovar.
    result = app.acquire_token_by_refresh_token(
        ONEDRIVE_REFRESH_TOKEN,
        scopes=SCOPES
    )

    if "access_token" in result:
        print("Autenticação no Microsoft Graph API bem-sucedida usando refresh token.")
        # Se um novo refresh token for emitido pelo servidor, ele estará em result['refresh_token']
        # e o MSAL irá gerenciá-lo internamente. Para seu caso no Railway,
        # o Refresh Token inicial deve ser de longa duração.
        return result["access_token"]
    else:
        print(f"Erro ao renovar token de acesso para o OneDrive: {result.get('error')}")
        print(f"Descrição do erro: {result.get('error_description')}")
        print("O Refresh Token pode ter expirado ou sido revogado. Por favor, obtenha um novo refresh token usando 'get_onedrive_token.py'.")
        return None

def enviar_para_onedrive(filepath, nome_destino, token):
    """
    Envia um arquivo para uma pasta específica no OneDrive do usuário.
    """
    if not token:
        print(f"Não foi possível enviar '{nome_destino}' para o OneDrive: token de autenticação ausente.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    try:
        with open(filepath, "rb") as f:
            # Envia o arquivo para a pasta 'Backups' no seu OneDrive
            # A pasta 'Backups' será criada automaticamente se não existir.
            r = requests.put(
                f"https://graph.microsoft.com/v1.0/me/drive/root:/Backups/{nome_destino}:/content",
                headers=headers,
                data=f
            )
        r.raise_for_status() # Lança uma exceção para códigos de status de erro (4xx ou 5xx)
        print(f"Arquivo '{nome_destino}' enviado com sucesso para o OneDrive. Status: {r.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar '{nome_destino}' para o OneDrive: {e}")
        # Detalhes adicionais do erro, se disponíveis na resposta
        if hasattr(e, 'response') and e.response is not None:
            print(f"Resposta de erro da API do OneDrive: {e.response.text}")
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filepath}' não encontrado. Certifique-se de que 'exportar_csvs()' criou o arquivo.")

def executar_backup():
    """
    Orquestra o processo completo de backup:
    1. Exporta dados do banco para CSV.
    2. Autentica no OneDrive usando refresh token.
    3. Envia os arquivos CSV para o OneDrive.
    """
    print(f"--- Iniciando processo de backup para OneDrive (Hora local: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    if exportar_csvs(): # Primeiro, exporta os dados do banco para CSV
        token = autenticar_graph_com_refresh_token() # Depois, autentica no OneDrive
        if token:
            # Envia os arquivos CSV para o OneDrive
            enviar_para_onedrive("backup/registros.csv", "registros.csv", token)
            enviar_para_onedrive("backup/demandas.csv", "demandas.csv", token)
        else:
            print("Não foi possível obter o token de acesso para o OneDrive. Backup interrompido.")
    else:
        print("Não foi possível gerar os arquivos CSV. Backup interrompido.")
    print("--- Processo de backup finalizado. ---")

if __name__ == "__main__":
    # Quando você executa este arquivo diretamente (para testes locais)
    executar_backup()