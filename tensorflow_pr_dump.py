import requests
import psycopg2

# Configurações
GITHUB_TOKEN = "replace with token"
REPO_OWNER = "tensorflow"
REPO_NAME = "tensorflow"
DATABASE_CONFIG = {
    "dbname": "tensorflow_data",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

# Função para buscar pull requests

def fetch_pull_requests(limit=1000):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
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

        pull_requests.extend(data)
        params["page"] += 1

        # Garantir que não ultrapasse o limite
        if len(pull_requests) >= limit:
            pull_requests = pull_requests[:limit]

    return pull_requests

def save_to_postgres(pull_requests):
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        for pr in pull_requests:
            pr_id = pr["id"]
            pull_number = pr["number"]

            cursor.execute(
                """
                INSERT INTO pull_requests (pr_id, title, state, created_at, updated_at, closed_at, merged_at, author, repo_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    f"{REPO_OWNER}/{REPO_NAME}",
                ),
            )

            print(f"PR {pr["number"]} inserted")

        conn.commit()
        print(f"{len(pull_requests)} pull requests inseridos com sucesso.")

    except Exception as e:
        print(f"Erro ao salvar no PostgreSQL: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    prs = fetch_pull_requests(limit=1000)
    print(f"{len(prs)} pull requests encontrados e serão inseridos no banco de dados.")
    save_to_postgres(prs)
