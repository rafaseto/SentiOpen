import requests
import psycopg2

# Configurações padrão
GITHUB_TOKEN = "Your token"

# Função para buscar pull requests fechados
def fetch_closed_pull_requests(repo_owner, repo_name, limit=1000):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
    params = {"state": "closed", "per_page": 100, "page": 1}

    pull_requests = []
    while len(pull_requests) < limit:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
            break

        data = response.json()
        if not data:
            break

        pull_requests.extend(data[:limit - len(pull_requests)])
        params["page"] += 1

    return pull_requests[:limit]

# Função para buscar comentários de um pull request
def fetch_comments_for_pr(repo_owner, repo_name, pull_number):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pull_number}/comments"
    params = {"per_page": 100, "page": 1}

    comments = []
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar comentários do PR #{pull_number}: {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        comments.extend(data)
        params["page"] += 1

    return comments

# Função para salvar comentários no PostgreSQL
def save_comments_to_postgres(conn, pr_id, comments):
    try:
        cursor = conn.cursor()

        for comment in comments:
            print(f"Inserting comment {comment["id"]}")

            cursor.execute(
                """
                INSERT INTO pr_comments (comment_id, pr_id, body, author, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (comment_id) DO NOTHING;
                """,
                (
                    comment["id"],
                    pr_id,
                    comment["body"],
                    comment["user"]["login"],
                    comment["created_at"],
                    comment["updated_at"],
                ),
            )

        conn.commit()
        print(f"{len(comments)} comentários inseridos para o PR {pr_id}")

    except Exception as e:
        print(f"Erro ao salvar comentários: {e}")

# Função para salvar pull requests e seus comentários no PostgreSQL
def save_to_postgres(conn, pull_requests, repo_owner, repo_name):
    try:
        cursor = conn.cursor()

        i = 0
        for pr in pull_requests:
            pr_id = pr["id"]
            pull_number = pr["number"]

            print(f"Inserting PR {pull_number} --- {i}/1000")

            # Salvar o pull request
            cursor.execute(
                """
                INSERT INTO pull_requests (pr_id, title, state, created_at, updated_at, closed_at, merged_at, author, repo_name, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pr_id) DO NOTHING;
                """,
                (
                    pr["id"],
                    pr["title"],
                    pr["state"],
                    pr["created_at"],
                    pr["updated_at"],
                    pr["closed_at"],
                    pr["merged_at"],
                    pr["user"]["login"],
                    f"{repo_owner}/{repo_name}",
                    pr["html_url"],  # Adiciona a URL do pull request
                ),
            )

            i += 1

            # Buscar e salvar os comentários do pull request
            comments = fetch_comments_for_pr(repo_owner, repo_name, pull_number)
            save_comments_to_postgres(conn, pr_id, comments)

        conn.commit()
        print(f"{len(pull_requests)} pull requests e seus comentários inseridos com sucesso.")
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
        "user": "Your user",
        "password": "Your password",
        "host": "Your host",
        "port": 5432,
    }

    try:
        # Conecta ao banco de dados
        conn = psycopg2.connect(**DATABASE_CONFIG)

        # Busca e salva os pull requests e comentários
        prs = fetch_closed_pull_requests(repo_owner, repo_name)
        print(f"{len(prs)} pull requests fechados encontrados.")
        save_to_postgres(conn, prs, repo_owner, repo_name)

    except Exception as e:
        print(f"Erro ao conectar ao banco de dados ou executar o processo: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
