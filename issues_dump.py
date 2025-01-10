import requests
import psycopg2

# Configurações
GITHUB_TOKEN = "replace with token"
REPO_OWNER = "grafana"
REPO_NAME = "grafana"
DATABASE_CONFIG = {
    "dbname": "grafana_data",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

# Função para buscar issues

def fetch_issues(limit=1000):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    params = {"state": "closed", "per_page": 100, "page": 1}

    issues = []

    while len(issues) < limit:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
            break

        data = response.json()
        # Filtrar apenas issues (excluindo pull requests)
        data = [issue for issue in data if "pull_request" not in issue]

        if not data:
            break

        issues.extend(data)
        params["page"] += 1

        # Garantir que não ultrapasse o limite
        if len(issues) >= limit:
            issues = issues[:limit]

    return issues

def save_to_postgres(issues):
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        for issue in issues:
            issue_id = issue["id"]
            issue_number = issue["number"]

            cursor.execute(
                """
                INSERT INTO issues (issue_id, title, state, created_at, updated_at, closed_at, author, repo_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_id) DO NOTHING;
                """,
                (
                    issue["id"],
                    issue["title"],
                    issue["state"],
                    issue["created_at"],
                    issue["updated_at"],
                    issue.get("closed_at"),
                    issue["user"]["login"],
                    f"{REPO_OWNER}/{REPO_NAME}",
                ),
            )

            print(f"Issue {issue_number} inserted")

        conn.commit()
        print(f"{len(issues)} issues inseridas com sucesso.")

    except Exception as e:
        print(f"Erro ao salvar no PostgreSQL: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    issues = fetch_issues(limit=1000)
    print(f"{len(issues)} issues encontradas e serão inseridas no banco de dados.")
    save_to_postgres(issues)
