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

# Função para buscar commits

def fetch_commits(limit=1000):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    params = {"per_page": 100, "page": 1}

    commits = []

    while len(commits) < limit:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
            break

        data = response.json()

        if not data:
            break

        commits.extend(data)
        params["page"] += 1

        # Garantir que não ultrapasse o limite
        if len(commits) >= limit:
            commits = commits[:limit]

    return commits

def save_to_postgres(commits):
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        for commit in commits:
            commit_id = commit["sha"]
            message = commit["commit"]["message"]
            author_name = commit["commit"]["author"].get("name")
            author_email = commit["commit"]["author"].get("email")
            date = commit["commit"]["author"].get("date")

            cursor.execute(
                """
                INSERT INTO commits (commit_id, message, author_name, author_email, date, repo_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (commit_id) DO NOTHING;
                """,
                (
                    commit_id,
                    message,
                    author_name,
                    author_email,
                    date,
                    f"{REPO_OWNER}/{REPO_NAME}",
                ),
            )

            print(f"Commit {commit_id} inserted")

        conn.commit()
        print(f"{len(commits)} commits inseridos com sucesso.")

    except Exception as e:
        print(f"Erro ao salvar no PostgreSQL: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    commits = fetch_commits(limit=1000)
    print(f"{len(commits)} commits encontrados e serão inseridos no banco de dados.")
    save_to_postgres(commits)
