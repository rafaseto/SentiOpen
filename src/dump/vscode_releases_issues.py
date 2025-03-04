import requests
import psycopg2

GITHUB_TOKEN = ""

# Function to get the releases
def fetch_releases(repo_owner, repo_name, limit=10):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    params = {"per_page": 10, "page": 1}

    releases = []
    while len(releases) < limit:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar dados: {response.status_code} - {response.text}")
            break

        data = response.json()
        if not data:
            break

        releases.extend(data[:limit - len(releases)])
        params["page"] += 1

        return releases[:limit]

# Function to save the releases
def save_releases_to_postgres(conn, releases, repo_owner, repo_name):
    try:
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS releases (
            release_id BIGINT PRIMARY KEY,
            tag_name TEXT,
            name TEXT,
            created_at TIMESTAMP,
            published_at TIMESTAMP,
            author TEXT,
            repo_name TEXT,
            url TEXT,
            body TEXT
        );
        """)

        for i, release in enumerate(releases):
            release_id = release["id"]
            tag_name = release["tag_name"]
            name = release["name"]
            created_at = release["created_at"]
            published_at = release["published_at"]
            author = release["author"]["login"] if release["author"] else None
            html_url = release["html_url"]
            body = release["body"]

            print(f"Inserting release {tag_name} --- {i + 1}/{len(releases)}")

            cursor.execute(
            """
            INSERT INTO releases (release_id, tag_name, name, created_at, published_at, author, repo_name, url, body)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (release_id) DO NOTHING;
            """,
            (
                release_id,
                tag_name,
                name,
                created_at,
                published_at,
                author,
                f"{repo_owner}/{repo_name}",
                html_url,
                body
            ),
            )

        conn.commit()
        print(f"Inserted {len(releases)} releases successfully")
    except Exception as e:
        print(f"Error when saving on PostgreSQL: {e}")

if __name__ == "__main__":
    repo_owner = input("REPO OWNER: ").strip()
    repo_name = input("REPO NAME: ").strip()
    dbname = input("DATABASE NAME: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "",
        "host": "",
        "port": 5432,
    }

    try:
        # connect to the db
        conn = psycopg2.connect(**DATABASE_CONFIG)

        # Select and save releases
        releases = fetch_releases(repo_owner, repo_name)
        print(f"{len(releases)} found.")
        save_releases_to_postgres(conn, releases, repo_owner, repo_name)

    except Exception as e:
        print(f"Error when connecting to the DB or when executing process: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
