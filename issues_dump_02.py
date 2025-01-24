import requests
import psycopg2

# Configurações padrão
GITHUB_TOKEN = "Your token"

# Função para buscar issues fechadas
def fetch_closed_issues(repo_owner, repo_name, limit=1000):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    params = {"state": "closed", "per_page": 100, "page": 1}

    issues = []
    while len(issues) < limit:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
            break

        data = response.json()
        if not data:
            break

        # Filtrar apenas issues (excluindo pull requests)
        filtered_issues = [issue for issue in data if "pull_request" not in issue]
        issues.extend(filtered_issues[:limit - len(issues)])
        params["page"] += 1

    return issues[:limit]

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

        for comment in comments:
            print(f"Inserindo comentário {comment['id']}")

            cursor.execute(
                """
                INSERT INTO issue_comments (comment_id, issue_id, body, author, created_at, updated_at)
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

# Função para salvar issues e seus comentários no PostgreSQL
def save_issues_to_postgres(conn, issues, repo_owner, repo_name):
    try:
        cursor = conn.cursor()

        for i, issue in enumerate(issues):
            issue_id = issue["id"]
            issue_number = issue["number"]

            print(f"Inserindo issue #{issue_number} --- {i + 1}/{len(issues)}")

            # Salvar a issue
            cursor.execute(
                """
                INSERT INTO issues (issue_id, title, state, created_at, updated_at, closed_at, author, repo_name, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_id) DO NOTHING;
                """,
                (
                    issue["id"],
                    issue["title"],
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

# Função principal
if __name__ == "__main__":
    # Coleta as informações do usuário
    repo_owner = input("REPO OWNER: ").strip()
    repo_name = input("REPO NAME: ").strip()
    dbname = input("DATABASE NAME: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "Your password",
        "host": "Your host",
        "port": 5432,
    }

    try:
        # Conecta ao banco de dados
        conn = psycopg2.connect(**DATABASE_CONFIG)

        # Busca e salva as issues e comentários
        issues = fetch_closed_issues(repo_owner, repo_name)
        print(f"{len(issues)} issues fechadas encontradas.")
        save_issues_to_postgres(conn, issues, repo_owner, repo_name)

    except Exception as e:
        print(f"Erro ao conectar ao banco de dados ou executar o processo: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
