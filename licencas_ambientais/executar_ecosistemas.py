#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para execução da coleta de dados do sistema Ecosistemas MG.
Este script facilita a execução do coletor com diferentes parametros.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
import json
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import csv

# Adicionar diretório pai ao path para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importar Selenium direto aqui para o modo manual
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd

def main():
    """Função principal que configura e executa o coletor"""
    
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Coleta de Licenças Ambientais - Sistema Ecosistemas MG')
    
    parser.add_argument('--max-paginas', type=int, default=100,
                        help='Número máximo de páginas a coletar (padrão: 100)')
    
    parser.add_argument('--output-prefix', type=str, default='licencas_ecosistemas',
                        help='Prefixo para os arquivos de saída (padrão: licencas_ecosistemas)')
    
    parser.add_argument('--modo-manual', action='store_true',
                        help='Executar em modo manual, onde o usuário fará a interação inicial com a página')
    
    parser.add_argument('--verbose', action='store_true',
                        help='Exibir logs detalhados')
    
    # Analisar argumentos da linha de comando
    args = parser.parse_args()
    
    # Configurar nivel de log
    log_level = logging.DEBUG if args.verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"ecosistemas_coleta_{datetime.now().strftime('%Y%m%d_%H%M')}.log"),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Exibir parâmetros de execução
    logger.info("=" * 50)
    logger.info("INICIANDO COLETA DE LICENÇAS AMBIENTAIS - ECOSISTEMAS")
    logger.info("=" * 50)
    logger.info(f"Parâmetros de execução:")
    logger.info(f"- Máximo de páginas: {args.max_paginas}")
    logger.info(f"- Prefixo de saída: {args.output_prefix}")
    logger.info(f"- Modo manual: {args.modo_manual}")
    logger.info(f"- Modo verbose: {args.verbose}")
    logger.info("=" * 50)
    
    try:
        # Inicializar o coletor (sempre com interface visível para facilitar depuração)
        from coletor_ecosistemas import ColetorEcosistemas
        coletor = ColetorEcosistemas(modo_headless=False)
        
        # Acessar o site
        if not coletor.acessar_site():
            logger.error("Erro ao acessar o site. Verifique sua conexão.")
            return 1
        
        # Se modo manual, deixar usuário aplicar filtros
        if args.modo_manual:
            print("\n" + "=" * 80)
            print("INSTRUÇÕES PARA MODO MANUAL:")
            print("1. No navegador que se abriu, aplique o filtro para Classe 6")
            print("2. Clique em Pesquisar para exibir os resultados")
            print("3. NÃO FECHE O NAVEGADOR! O script fará a coleta automaticamente")
            print("4. Quando estiver pronto, pressione Enter para continuar...")
            print("=" * 80 + "\n")
            
            # Aguardar entrada do usuário
            input("Pressione Enter quando estiver pronto para iniciar a coleta...")
        else:
            # Modo automático - tentar aplicar filtro
            if not coletor.aplicar_filtro_classe_6():
                logger.error("Erro ao aplicar filtro de Classe 6. Tente usar o modo manual.")
                return 1
        
        # Coletar dados das páginas
        todos_resultados = []
        contador_paginas = 1
        
        while contador_paginas <= args.max_paginas:
            logger.info(f"Processando página {contador_paginas}")
            
            # Extrair dados da tabela atual
            resultados_tabela = coletor.extrair_dados_tabela()
            
            if not resultados_tabela:
                logger.warning(f"Nenhum resultado encontrado na página {contador_paginas}")
                break
            
            logger.info(f"Encontrados {len(resultados_tabela)} registros na página {contador_paginas}")
            
            # Para cada registro, processar detalhes
            for i, resultado in enumerate(resultados_tabela):
                logger.info(f"Processando registro {i+1} de {len(resultados_tabela)} na página {contador_paginas}")
                
                # Verificar se já podemos identificar o tipo de estudo
                tipo_estudo = resultado.get("tipo_de_estudo", "")
                if tipo_estudo not in ["EIA/RIMA", "RCA"] and "link_detalhes" in resultado:
                    # Se não temos o tipo de estudo identificado, acessar detalhes
                    if coletor.acessar_proximo_registro(resultado["link_detalhes"]):
                        # Extrair dados detalhados
                        dados_detalhados = coletor.extrair_dados_detalhados()
                        
                        # Atualizar o tipo de estudo
                        if "Tipo de Estudo" in dados_detalhados:
                            resultado["tipo_de_estudo"] = dados_detalhados["Tipo de Estudo"]
                        
                        # Fechar aba de detalhes
                        coletor.fechar_aba_detalhes()
                
                todos_resultados.append(resultado)
            
            # Tentar navegar para a próxima página
            if not coletor.navegar_proxima_pagina():
                logger.info("Não há mais páginas disponíveis.")
                break
            
            contador_paginas += 1
            time.sleep(3)  # Aguardar um pouco entre páginas
        
        # Salvar resultados
        if todos_resultados:
            # Resumo dos tipos de estudo
            estudos = {"EIA/RIMA": 0, "RCA": 0, "EIA/RIMA e RCA": 0, "EIA/RIMA (inferido pela atividade)": 0, "RCA (inferido pela atividade)": 0, "A determinar": 0}
            
            for resultado in todos_resultados:
                tipo = resultado.get("tipo_de_estudo", "A determinar")
                if tipo in estudos:
                    estudos[tipo] += 1
                else:
                    estudos[tipo] = 1
            
            # Salvar resultados em Excel
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            # Definir ordem das colunas (para garantir que tipo_de_estudo apareça em destaque)
            colunas_ordem = [col for col in todos_resultados[0].keys() if col != "tipo_de_estudo"]
            # Inserir tipo_de_estudo após classe_predominante ou no início
            if "classe_predominante" in colunas_ordem:
                indice = colunas_ordem.index("classe_predominante")
                colunas_ordem.insert(indice + 1, "tipo_de_estudo")
            else:
                colunas_ordem.insert(0, "tipo_de_estudo")
            
            df = pd.DataFrame(todos_resultados)
            
            # Garantir que todas as colunas estejam presentes
            for coluna in colunas_ordem:
                if coluna not in df.columns:
                    df[coluna] = ""
            
            # Reordenar colunas
            colunas_existentes = [col for col in colunas_ordem if col in df.columns]
            df = df[colunas_existentes]
            
            # Salvar como Excel
            arquivo_excel = f"{args.output_prefix}_{timestamp}.xlsx"
            df.to_excel(arquivo_excel, index=False)
            logger.info(f"Resultados salvos em Excel: {arquivo_excel}")
            
            # Salvar como CSV
            arquivo_csv = f"{args.output_prefix}_{timestamp}.csv"
            df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Resultados salvos em CSV: {arquivo_csv}")
            
            # Exibir resumo para o usuário
            print("\n" + "=" * 80)
            print(f"RESUMO DA COLETA - {len(todos_resultados)} REGISTROS")
            print("-" * 80)
            print("TIPOS DE ESTUDOS ENCONTRADOS:")
            for estudo, quantidade in estudos.items():
                if quantidade > 0:
                    print(f"- {estudo}: {quantidade}")
            print("-" * 80)
            print(f"Dados salvos em:")
            print(f"- Excel: {arquivo_excel}")
            print(f"- CSV: {arquivo_csv}")
            print("=" * 80)
        else:
            logger.warning("Nenhum resultado coletado.")
        
        # Fechar o navegador
        try:
            coletor.driver.quit()
            logger.info("Navegador fechado com sucesso.")
        except:
            pass
            
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}", exc_info=True)
        return 1
    
    logger.info("=" * 50)
    logger.info("COLETA FINALIZADA")
    logger.info("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 