from log_config import configure_logging
import logging
import requests


configure_logging()


def fetch_issues_from_query(query, token=None, per_page=100):
    """
    Busca issues na API do GitHub usando a query fornecida e retorna todas as issues encontradas.
    
    Parâmetros:
      - query (str): Query de busca (ex.: 'repo:microsoft/vscode is:issue is:closed milestone:"April 2025"')
      - token (str, opcional): Token de acesso para autenticação na API do GitHub.
      - per_page (int, opcional): Número máximo de itens por página (padrão é 100).
    
    Retorna:
      - list: Lista com todas as issues coletadas.
    """
    if not query:
        logging.error("No query received.")
        return []

    url_api = f"https://api.github.com/search/issues?q={query}"
    
    params = {
        'per_page': per_page,
        'page': 1
    }

    headers = {'Authorization': f'token {token}'} if token else {}

    issues = []
    while True:
        response = requests.get(url_api, headers=headers, params=params)

        if response.status_code != 200:
            logging.error(f"Error with the request: {response.status_code} - {response.text}")
            break

        data = response.json()

        curr_issues = data.get('items', [])
        
        issues.extend(curr_issues)

        if 'next' not in response.links:
            break

        params['page'] += 1

    logging.info(f"Number of collected issues: {len(issues)}")

    return issues


def fetch_comments_for_issue(issue_number, repo_owner, repo_name, headers):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
    params = {"per_page": 100, "page": 1}
    
    comments = []
    while True:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logging.error(
                "Error when fetching comments for issue"
                f" #{issue_number}: {response.status_code}"
            )
            break

        data = response.json()

        if not data:
            break

        comments.extend(data)

        params["page"] += 1
    
    logging.info(
        f"{len(comments)} comments found for issue {issue_number}."
    )

    return comments


def fetch_and_save_comments_for_issues(issues, repo_owner, repo_name, conn, token=None):
    """
    Fetches and saves all comments for the given issue by iterating through paginated API results.

    This function uses the GitHub REST API to retrieve comments for the given issues
    in the specified repository. It will automatically paginate through all available pages
    (100 comments per page) until no more comments are returned.

    Parameters:
        issues (list):
            List of issues.
        repo_owner (str):
            The username or organization that owns the repository.
        repo_name (str):
            The name of the repository.
        token (str):
            GitHub token.

    Returns:
        list of dict:
            A list of comment objects as returned by the GitHub API. Each dict represents one comment.
    """
    headers = {"Authorization": f"Bearer {token}"}

    for i, issue in enumerate(issues):
        issue_number = issue['number']
        issue_id = issue['id']

        logging.info(
            f"Fetching comments for issue #{issue_number}"
        )

        comments = fetch_comments_for_issue(
            issue_number=issue_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            headers=headers
        )

        logging.info(
            f"Saving comments for issue #{issue_number}"
        )

        save_comments_to_postgres(
            conn=conn,
            issue_id=issue_id,
            comments=comments
        )

        logging.info(
            f"Finished issue #{issue_number} --- {i + 1}/{len(issues)}"
        )

    logging.info(f"Finished fetching and saving all of the comments.")


def save_comments_to_postgres(conn, issue_id, comments):
    """
    Saves a list of GitHub issue comments into a PostgreSQL database.

    This function ensures the target table `comments` exists,
    then inserts each comment into the table. If a comment with the same `comment_id`
    already exists, it will be skipped (avoiding duplicate entries via `ON CONFLICT DO NOTHING`).

    Parameters:
        conn (psycopg2.connection):
            An active PostgreSQL database connection.
        issue_id (int):
            The ID of the GitHub issue associated with the comments.
        comments (list of dict):
            A list of comment dictionaries, typically retrieved from the GitHub API.
            Each comment must include 'id', 'body', 'user' (with 'login'), 'created_at', and 'updated_at'.
    """
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
            comment_id BIGINT PRIMARY KEY,
            issue_id BIGINT,
            body TEXT,
            author TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
            );
            """
        )

        for i, comment in enumerate(comments):
            logging.info(
                f"  Inserting comment {comment['id']}"
                f" --- {i + 1}/{len(comments)}"
            )

            cursor.execute(
                """
                INSERT INTO comments (comment_id, issue_id, body, author, created_at, updated_at)
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

        logging.info(
            f"  {len(comments)} comments inserted for issue {issue_id}"
        )

    except Exception as e:
        logging.error(f"Error when saving the comments: {e}")


def save_issues_to_postgres(conn, issues, release_id, repo_owner, repo_name):
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                issue_id BIGINT PRIMARY KEY,
                release TEXT,
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

            logging.info(f"Inserting issue #{issue_number} --- {i + 1}/{len(issues)}")

            # Salvar a issue
            cursor.execute(
                """
                INSERT INTO issues (issue_id, release, title, body, state, created_at, updated_at, closed_at, author, repo_name, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_id) DO NOTHING;
                """,
                (
                    issue["id"],
                    release_id,
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

        conn.commit()

        logging.info("Issues successfully inserted.")
        
    except Exception as e:
        logging.error(f"Error when saving the issues: {e}")
