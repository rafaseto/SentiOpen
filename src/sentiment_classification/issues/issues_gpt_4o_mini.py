import psycopg2
import openai  
import pandas as pd
import time

def main():
    dbname = input("Database Name: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "",
        "host": "",
        "port": 5432,
    }

    MODEL = "gpt-4o-mini"
    OPENAI_API_KEY = "" 

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        def analyze_sentiment_comment(context, comment, model):
            prompt = f"""
            In the context of the following issue:
            {context}

            Respond with only one word: 'positive', 'neutral', or 'negative'. 
            What is the sentiment of the next comment?
            {comment}
            """
            
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        
        # Selecting issues 
        cursor.execute(
            """
            SELECT 
                issue_id,
                title 
            FROM 
                issues
            WHERE
                issue_id IN (
                    SELECT issue_id
                    FROM issue_comments
                    GROUP BY issue_id
                    HAVING COUNT(*) >= 4
                )
            LIMIT 10
            """
        )  
        issues = cursor.fetchmany(10)

        resultados = []  
        num_comments_classified = 0

        start = time.time()
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
                    issue_comments 
                WHERE 
                    issue_id = %s
                ORDER BY
                    created_at;
                """, (issue_id,)
            )
            comments = cursor.fetchall()

            print(f"Comments for the Issue {issue_id} - {title}:")
            context = f"Title of the issue: '{title}'."
            i = 1
            
            for comment in comments:
                comment_id, created_at, body = comment
                print(f"Classifying sentiment for comment {comment_id}: {body[:30]}...")
                print("     Generating response...")

                # Classifyig the comment`s sentiment
                resultado = analyze_sentiment_comment(context, body, MODEL)
                print(f"     Response Generated: {resultado}")
                resultados.append((issue_id, resultado))  
                print("     Response saved")

                # Increment the context
                context = context + " " + f"Comment {i}: <beginning of comment {i}> '{body}' <end of comment {i}>."
                i += 1

                num_comments_classified += 1
            print("")
            print("")
        end = time.time()


        classification_time = end - start
        print(f"Classification Time: {classification_time:.4f} seconds")

        cursor.execute("ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS sentiment_gpt_4o_mini TEXT")  # Adiciona a coluna 'sentimento_gpt' na tabela se não existir
 
        for res in resultados:  
            cursor.execute(  
                "UPDATE issue_comments SET sentiment_gpt_4o_mini = %s WHERE issue_id = %s",  
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
