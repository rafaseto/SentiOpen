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

        def analyze_sentiment_gpt(text, model):
            prompt = f"""
            Respond with only one word: 'positive', 'neutral', or 'negative'. 
            What is the sentiment of the following text?
            {text}
            """
            
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        
        cursor.execute("SELECT issue_id, body, comment_id FROM issue_comments")  
        rows = cursor.fetchmany(50)

        resultados = []  
        num_issues_classified = 0

        start = time.time()
        for row in rows: 
            issue_id, body, comment_id = row  
            
            print(f"Classifying sentiment for issue comment {comment_id}")
            num_issues_classified += 1

            # Classificar o texto
            print("     Generating response...")
            resultado = analyze_sentiment_gpt(body, MODEL)
            print(f"     Response Generated: {resultado}")
            resultados.append((issue_id, resultado))  
            print("     Response saved")
        end = time.time()

        classification_time = end - start
        print(f"Classification Time: {classification_time:.4f} seconds")

        cursor.execute("ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS sentiment_gpt_4o_mini TEXT")  # Adiciona a coluna 'sentimento_gpt' na tabela se não existir
 
        for res in resultados:  
            cursor.execute(  
                "UPDATE issue_comments SET sentiment_gpt_4o_mini = %s WHERE issue_id = %s",  
                (res[1], res[0])  
            )
        print(f"Sentiment Classification Data Saved - {num_issues_classified} Issue Comments Classified")

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
