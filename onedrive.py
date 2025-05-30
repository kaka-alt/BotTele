import pandas as pd
import os
from msal import ConfidentialClientApplication
import requests
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar credenciais do Azure AD (use suas variáveis de ambiente)
client_id = os.getenv("MS_CLIENT_ID")
client_secret = os.getenv("MS_CLIENT_SECRET")
tenant_id = os.getenv("MS_TENANT_ID")
authority = f"https://login.microsoftonline.com/{tenant_id}"
scopes = ["https://graph.microsoft.com/.default"]  # Ou as permissões mais restritas

app = ConfidentialClientApplication(
    client_id,
    authority=authority,
    client_credential=client_secret
)

def get_access_token():
    """Obtém o token de acesso do Microsoft Graph."""
    try:
        result = app.acquire_token_for_client(scopes=scopes)
        if "error" in result:
            raise Exception(f"Erro ao obter o token: {result['error_description']}")
        return result["access_token"]
    except Exception as e:
        logging.error(f"Erro ao obter o token: {e}")
        return None

def upload_to_onedrive(file_path, file_name, onedrive_folder):
    """Envia um arquivo para o OneDrive."""

    access_token = get_access_token()
    if not access_token:
        return False  # Falha ao obter o token

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }

    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_folder}/{file_name}:/content"

    try:
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, headers=headers, data=f)
        response.raise_for_status()  # Lança uma exceção para status codes ruins (4xx ou 5xx)
        logging.info(f"Arquivo '{file_name}' enviado para o OneDrive com sucesso.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar '{file_name}' para o OneDrive: {e}")
        return False
    except FileNotFoundError:
        logging.error(f"Arquivo '{file_path}' não encontrado.")
        return False

def export_data_to_excel(data, file_name):
    """Exporta os dados para um arquivo Excel e retorna o caminho do arquivo."""
    file_path = f"/tmp/{file_name}"  # Use /tmp/ para arquivos temporários no Railway
    df = pd.DataFrame(data)  # Supondo que 'data' seja uma lista de dicionários
    df.to_excel(file_path, index=False)
    return file_path

def fetch_data_from_db(db_connection, query):
    """Busca dados do banco de dados usando a consulta fornecida."""
    try:
        df = pd.read_sql_query(query, db_connection)  # Use pandas para ler a consulta
        return df.to_dict(orient='records')  # Converte para lista de dicionários
    except Exception as e:
        logging.error(f"Erro ao buscar dados do banco de dados: {e}")
        return []

if __name__ == '__main__':
    # Exemplo de uso (para testes locais - adapte para seu bot)
    # Substitua com sua lógica de conexão do banco de dados
    # db_connection = ...

    # Exemplo de consulta (adapte para suas tabelas)
    query = "SELECT * FROM your_table"
    #data = fetch_data_from_db(db_connection, query)

    #if data:
    #    excel_file = export_data_to_excel(data, "dados_do_banco.xlsx")
    #    upload_to_onedrive(excel_file, "dados_do_banco.xlsx", "BotData")
    #else:
    #    print("Não há dados para exportar.")
    print("Teste")