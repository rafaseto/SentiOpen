import psycopg2
from google import genai  
import pandas as pd
import time
import json

def main():
    dbname = input("Database Name: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "",
        "host": "",
        "port": 5432,
    }

    MODEL = "gemini-2.0-flash"
    GENAI_API_KEY = "" 

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        def analyze_sentiment_comment(context, comment, model):
            prompt = f"""
            In the context of the following GitHub issue:
            {context}

            Respond with only one word: 'positive', 'neutral', or 'negative'. 
            What is the sentiment of the next comment?
            {comment}
            """
            
            client = genai.Client(api_key=GENAI_API_KEY)
            response = client.models.generate_content(
                model=model,
                contents=prompt                
            )
            return response.text
        
        # Selecting releases
        cursor.execute(
            """
            SELECT 
                release_id,
                tag_name,
                name
            FROM
                releases;
            """
        )
        releases = cursor.fetchall()

        resultados = [] 
        num_pos_neg_neu = {} 
        num_comments_classified = 0

        start = time.time()
        for release in releases:
            release_id, tag_name, name = release
            num_pos_neg_neu[tag_name] = {"positive": 0, "negative": 0, "neutral": 0}

            print(f"Starting classification for Release: {tag_name}")

            # Selecting issues 
            cursor.execute(
                """
                SELECT 
                    issue_id,
                    title
                FROM 
                    issues_from_release
                WHERE
                    release_id = %s;
                """, (release_id,)
            )  
            issues = cursor.fetchall()

            for issue in issues: 
                issue_id, title = issue
                # Selecting comments
                cursor.execute(
                    """
                    SELECT 
                        comment_id,
                        created_at,
                        body
                    FROM 
                        issue_comments_from_release
                    WHERE 
                        issue_id = %s
                    ORDER BY
                        created_at;
                    """, (issue_id,)
                )
                comments = cursor.fetchall()

                print(f"Starting classification for Issue {issue_id} - {title}:")
                context = f"Title of the issue: '{title}'."
                i = 1
                
                for comment in comments:
                    comment_id, created_at, body = comment
                    print(f"Classifying sentiment for comment {comment_id}: {body[:30]}...")
                    print("     Generating response...")

                    # Classifyig the comment`s sentiment
                    resultado = analyze_sentiment_comment(context, body, MODEL)
                    resultado = resultado.lower()
                    print(f"     Response Generated: {resultado}")
                    resultados.append((comment_id, resultado))  
                    print("     Response saved")

                    # Updating the stats
                    if "positive" in resultado:
                        num_pos_neg_neu[tag_name]["positive"] += 1
                    elif "negative" in resultado:
                        num_pos_neg_neu[tag_name]["negative"] += 1
                    elif "neutral" in resultado:
                        num_pos_neg_neu[tag_name]["neutral"] += 1
                    # Increment the context
                    context = context + " " + f"Comment {i}: <beginning of comment {i}> '{body}' <end of comment {i}>."
                    i += 1

                    num_comments_classified += 1
                print("")
                print("")

            print(f"Number of neutral for release {tag_name}: {num_pos_neg_neu[tag_name]["neutral"]}")
            print(f"Number of positive for release {tag_name}: {num_pos_neg_neu[tag_name]["positive"]}")
            print(f"Number of negative for release {tag_name}: {num_pos_neg_neu[tag_name]["negative"]}")
            print("")
            print("")
            print("")
            print("")            

        end = time.time()

        stats_file = "stats_gemini_2_0_flash.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(num_pos_neg_neu, f, indent=4, ensure_ascii=False)

        classification_time = end - start
        print(f"Classification Time: {classification_time:.4f} seconds")

        cursor.execute("ALTER TABLE issue_comments_from_release ADD COLUMN IF NOT EXISTS sentiment_gemini_2_0_flash TEXT")  # Adiciona a coluna 'sentimento_gpt' na tabela se não existir
  
        for res in resultados:  
            cursor.execute(  
                "UPDATE issue_comments_from_release SET sentiment_gemini_2_0_flash = %s WHERE comment_id = %s",  
                (res[1], res[0])  
            )
        print(f"Sentiment Classification Data Saved - {num_comments_classified} Comments Classified")

        conn.commit()  
        cursor.close()  
        conn.close() 

    except Exception as e:
        print(f"Error when connecting to the database or when executing process: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
