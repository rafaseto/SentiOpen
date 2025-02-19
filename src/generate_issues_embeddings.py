from sentence_transformers import SentenceTransformer
import psycopg2
import numpy as np

# 1. Configuração do modelo
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# 2. Conexão ao banco PostgreSQL
conn = psycopg2.connect(
    dbname="grafana_data",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# 3. Extrair textos do banco
cursor.execute("SELECT issue_id, title FROM issues")
rows = cursor.fetchall()

# 4. Gerar embeddings e salvar no banco
for row in rows:
    issue_id_, title = row
    embedding = model.encode([title])[0]  # Calcula o embedding do texto
    embedding_array = embedding.tolist()  # Converte para lista para o PostgreSQL

    # Atualizar ou inserir o embedding no banco
    cursor.execute(
        """
        UPDATE issues
        SET embedding = %s
        WHERE issue_id = %s
        """,
        (embedding_array, issue_id_)
    )

# 5. Confirmar alterações e fechar conexão
conn.commit()
cursor.close()
conn.close()