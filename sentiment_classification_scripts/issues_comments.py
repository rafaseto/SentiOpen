import psycopg2  # Importa o módulo para interação com o banco de dados PostgreSQL
from transformers import pipeline, AutoTokenizer  # Importa o pipeline e o AutoTokenizer da biblioteca transformers para trabalhar com modelos de NLP
import torch  # Importa o módulo PyTorch para trabalhar com GPU/CPU e redes neurais

def main():
    dbname = input("Database Name: ").strip()

    DATABASE_CONFIG = {
        "dbname": dbname,
        "user": "postgres",
        "password": "Your password",
        "host": "Your host",
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

        # Carregar o modelo e tokenizer do HuggingFace para análise de sentimentos
        classifier = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis", device=device)  
        # O pipeline é uma abstração de alto nível para execução de tarefas de NLP. Aqui, é usado para classificação de sentimentos.
        tokenizer = AutoTokenizer.from_pretrained("finiteautomata/bertweet-base-sentiment-analysis")  
        # Carrega o tokenizer que foi treinado para o modelo específico "finiteautomata/bertweet-base-sentiment-analysis"

        # Função para verificar o comprimento do texto
        def is_text_too_long(text, max_length=128):  
            # Função que verifica se o texto excede o comprimento máximo permitido (em tokens)
            tokens = tokenizer.encode(text)  # Codifica o texto em tokens
            return len(tokens) > max_length  # Retorna True se o texto for maior que o limite especificado
        
        # Buscar textos do banco de dados
        cursor.execute("SELECT issue_id, body FROM issue_comments")  
        # Executa a consulta SQL para selecionar o 'issue_id' e o 'body' (corpo do comentário) da tabela 'issue_comments'
        rows = cursor.fetchall()  # Recupera todas as linhas resultantes da consulta

        # Processar e classificar
        resultados = []  # Lista onde os resultados da classificação serão armazenados
        num_issues_classified = 0
        for row in rows:  # Itera sobre as linhas retornadas
            issue_id, body = row  # Extrai o 'issue_id' e o 'body' de cada linha
            
            # Verificar se o texto é muito longo
            if is_text_too_long(body):  # Verifica se o corpo do comentário excede o limite de tokens
                print(f"Texto com {len(body)} caracteres excede o limite de 128 tokens. Ignorando...")  # Informa que o comentário foi ignorado
                continue  # Ignora o processamento deste comentário e passa para o próximo
            else: 
                print(f"Classifying sentiment for issue comment {issue_id}")
                num_issues_classified += 1
            # Classificar o texto
            resultado = classifier(body)[0]  # Classifica o sentimento do comentário (retorna um dicionário com 'label' e 'score')
            resultados.append((issue_id, resultado['label'], resultado['score']))  # Armazena o 'issue_id', o 'label' e o 'score' na lista de resultados

        # Atualizar resultados no banco de dados
        cursor.execute("ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS sentimento TEXT")  # Adiciona a coluna 'sentimento' na tabela se ela não existir
        cursor.execute("ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS confianca NUMERIC")  # Adiciona a coluna 'confianca' para armazenar a confiança da classificação
        for res in resultados:  # Itera sobre os resultados da classificação
            cursor.execute(  # Executa um comando SQL para atualizar o banco de dados
                "UPDATE issue_comments SET sentimento = %s, confianca = %s WHERE issue_id = %s",  # Atualiza as colunas 'sentimento' e 'confianca' com os valores dos resultados
                (res[1], res[2], res[0])  # Passa os valores do 'label', 'score' e 'issue_id' para a consulta
            )
        print(f"Sentiment Classification Data Saved - {num_issues_classified} Issue Comments Classified")

        conn.commit()  # Aplica as alterações no banco de dados
        cursor.close()  # Fecha o cursor
        conn.close()  # Fecha a conexão com o banco de dados



    except Exception as e:
        print(f"Error when connecting to the database or when executing process: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()