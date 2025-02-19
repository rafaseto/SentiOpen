import psycopg2  
from transformers import pipeline, AutoTokenizer  
import torch  
import ollama
import pandas as pd

def main():
    dbname = input("Database Name: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "",
        "host": "",
        "port": 5432,
    }

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # Carregar o modelo e o tokenizer
        if torch.cuda.is_available():  # Verifica se há uma GPU disponível
            device = torch.device("cuda")  # Se houver, usa a GPU
            print("GPU disponível! Usando:", torch.cuda.get_device_name(0))  # Exibe o nome da GPU
        else:
            device = torch.device("cpu")  # Se não houver GPU, usa o CPU
            print("GPU não disponível, usando CPU.")  # Informa que o CPU será usado

        def analisar_sentimento_ds(texto):
            prompt = f"Respond with only one word: positive, neutral, or negative. What is the sentiment of the following text? {texto}"
            resposta = ollama.chat(model="deepseek-r1:8b", messages=[{"role": "user", "content": prompt}])
            return resposta["message"]["content"].strip().split()[-1].lower()
        

        cursor.execute("SELECT issue_id, body, comment_id FROM issue_comments")  
        rows = cursor.fetchmany(50)


        resultados = []  # Lista onde os resultados da classificação serão armazenados
        num_issues_classified = 0
        for row in rows: 
            issue_id, body, comment_id = row  
            
            print(f"Classifying sentiment for issue comment {comment_id}")
            num_issues_classified += 1

            # Classificar o texto
            print("     Generating response...")
            resultado = analisar_sentimento_ds(body)
            print(f"     Response Generated: {resultado}")
            resultados.append((issue_id, resultado))  
            print("     Response saved")

        # Atualizar resultados no banco de dados
        cursor.execute("ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS sentimento_ds TEXT")  # Adiciona a coluna 'sentimento' na tabela se ela não existir
 
        for res in resultados:  
            cursor.execute(  
                "UPDATE issue_comments SET sentimento_ds = %s WHERE issue_id = %s",  
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