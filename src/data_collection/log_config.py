import logging

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            # logging.FileHandler("processamento_issues.log")  # Descomente se desejar salvar em arquivo.
        ]
    )