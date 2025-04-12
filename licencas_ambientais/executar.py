import argparse
from scraper import LicencasAmbientaisScraper, logger

def main():
    """
    Script para executar a coleta de licenças ambientais com parâmetros personalizados.
    """
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Coletor de licenças ambientais de MG')
    parser.add_argument('--paginas', type=int, default=5, help='Número máximo de páginas para coletar (padrão: 5)')
    parser.add_argument('--processos', type=int, default=None, help='Máximo de processos por página (padrão: todos)')
    parser.add_argument('--pasta', type=str, default='pareceres', help='Pasta para salvar os pareceres técnicos (padrão: pareceres)')
    
    args = parser.parse_args()
    
    logger.info(f"Iniciando coleta com configurações: {args.paginas} páginas, {args.processos or 'todos'} processos por página")
    
    # Inicializar e executar o scraper
    scraper = LicencasAmbientaisScraper(download_folder=args.pasta)
    resultados = scraper.executar_coleta(
        max_paginas=args.paginas,
        max_processos_por_pagina=args.processos
    )
    
    if not resultados.empty:
        logger.info(f"Coleta finalizada com sucesso! {len(resultados)} processos coletados.")
    else:
        logger.warning("A coleta não retornou resultados.")
    
if __name__ == "__main__":
    main() 