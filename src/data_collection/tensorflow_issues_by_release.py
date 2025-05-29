import requests
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def fetch_issues_from_release(release_label, token=None, per_page=100):
    """
    Busca issues na API do GitHub usando a query fornecida e retorna todas as issues encontradas.
    
    Parâmetros:
      - query (str): Query de busca (ex.: 'is:issue milestone:"October 2024 Recovery 2" is:closed')
      - token (str, opcional): Token de acesso para autenticação na API do GitHub.
      - per_page (int, opcional): Número máximo de itens por página (padrão é 100).
    
    Retorna:
      - list: Lista com todas as issues coletadas.
    """
    query = f'is:issue state:closed label:{release_label}'

    if not query:
        print("Nenhuma query fornecida.")
        return []

    url_api = f"https://api.github.com/search/issues?q={query}"
    print(url_api)
    params = {
        'per_page': per_page,
        'page': 1
    }
    headers = {'Authorization': f'token {token}'} if token else {}

    all_issues = []
    while True:
        response = requests.get(url_api, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro na requisição: {response.status_code} - {response.text}")
            break

        data = response.json()
        issues = data.get('items', [])
        all_issues.extend(issues)

        # Verifica se há próxima página pela presença do link 'next'
        if 'next' not in response.links:
            break

        params['page'] += 1

    print(f"Total de issues coletadas: {len(all_issues)}")
    return all_issues

def dump_github_issues_from_release(release_label, github_token=None, per_page=100):
    """
    Realiza o dump das issues do GitHub de acordo com a query informada.
    
    Parâmetros:
      - query (str): A query de busca (ex.: 'is:issue milestone:"October 2024 Recovery 2" is:closed')
      - github_token (str, opcional): Token de acesso para autenticação na API do GitHub.
      - per_page (int, opcional): Número de itens por página (padrão 100).
    
    Retorna:
      - all_issues (list): Lista com todas as issues coletadas.
    """
    headers = {'Authorization': f'token {github_token}'} if github_token else {}

    query = f'is:issue state:closed label:{release_label}'

    url = 'https://api.github.com/search/issues'
    params = {
        'q': query,
        'per_page': per_page,
        'page': 1
    }

    all_issues = []

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro na requisição: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        issues = data.get('items', [])
        all_issues.extend(issues)

        # Verifica se há mais páginas pela presença do link 'next'
        if 'next' not in response.links:
            break

        params['page'] += 1

    print(f"Total de issues coletadas: {len(all_issues)}")
    return all_issues

# Função para buscar comentários de uma issue
def fetch_comments_for_issue(repo_owner, repo_name, issue_number):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
    params = {"per_page": 100, "page": 1}

    comments = []
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar comentários da issue #{issue_number}: {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        comments.extend(data)
        params["page"] += 1

    return comments

# Função para salvar comentários no PostgreSQL
def save_comments_to_postgres(conn, issue_id, comments):
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issue_comments_from_release (
            comment_id BIGINT PRIMARY KEY,
            issue_id BIGINT,
            body TEXT,
            author TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
            );
            """
        )

        for comment in comments:
            print(f"Inserindo comentário {comment['id']}")

            cursor.execute(
                """
                INSERT INTO issue_comments_from_release (comment_id, issue_id, body, author, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (comment_id) DO NOTHING;
                """,
                (
                    comment["id"],
                    issue_id,
                    comment["body"],
                    comment["user"]["login"],
                    comment["created_at"],
                    comment["updated_at"],
                ),
            )

        conn.commit()
        print(f"{len(comments)} comentários inseridos para a issue {issue_id}")

    except Exception as e:
        print(f"Erro ao salvar comentários: {e}")

def save_issues_to_postgres(conn, issues, release_number, repo_owner, repo_name):
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issues_from_release (
                issue_id BIGINT PRIMARY KEY,
                release_number TEXT,
                title TEXT,
                body TEXT,
                state TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                closed_at TIMESTAMP,
                author TEXT,
                repo_name TEXT,
                url TEXT
            );
            """
        )

        for i, issue in enumerate(issues):
            issue_id = issue["id"]
            issue_number = issue["number"]

            print(f"Inserindo issue #{issue_number} --- {i + 1}/{len(issues)}")

            # Salvar a issue
            cursor.execute(
                """
                INSERT INTO issues_from_release (issue_id, release_number, title, body, state, created_at, updated_at, closed_at, author, repo_name, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_id) DO NOTHING;
                """,
                (
                    issue["id"],
                    release_number,
                    issue["title"],
                    issue["body"],
                    issue["state"],
                    issue["created_at"],
                    issue["updated_at"],
                    issue["closed_at"],
                    issue["user"]["login"],
                    f"{repo_owner}/{repo_name}",
                    issue["html_url"],  # URL da issue
                ),
            )

            # Buscar e salvar os comentários da issue
            comments = fetch_comments_for_issue(repo_owner, repo_name, issue_number)
            save_comments_to_postgres(conn, issue_id, comments)

        conn.commit()
        print(f"{len(issues)} issues e seus comentários inseridos com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar no PostgreSQL: {e}")

if __name__ == "__main__":
    # Coleta as informações do usuário
    repo_owner = "tensorflow"
    repo_name = "tensorflow"
    dbname = "tensorflow_data"

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "YzLq4UAMQ7LOadXh",
        "host": "humanely-winged-bluebird.data-1.use1.tembo.io",
        "port": 5432,
    }

    try:
        # Conecta ao banco de dados
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()


        release_number = '"TF 2.18"'

        issues = fetch_issues_from_release(release_number, GITHUB_TOKEN)

        print(f"{len(issues)} issues fechadas encontradas.")
        save_issues_to_postgres(conn, issues, release_number, repo_owner, repo_name)

    except Exception as e:
        print(f"Erro ao conectar ao banco de dados ou executar o processo: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()