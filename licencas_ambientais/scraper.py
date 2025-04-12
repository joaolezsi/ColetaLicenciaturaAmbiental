import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import io
import fitz  # PyMuPDF
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("licencas_ambientais.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class LicencasAmbientaisScraper:
    def __init__(self, download_folder="pareceres"):
        """
        Inicializa o scraper para coleta de licenças ambientais de MG
        """
        self.base_url = "https://sistemas.meioambiente.mg.gov.br/licenciamento/site/consulta-licenca"
        self.download_folder = download_folder
        
        # Criar pasta para downloads se não existir
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
            
        # Configuração do Chrome Driver
        self.chrome_options = Options()
        # Comentar a linha abaixo para visualizar o navegador durante testes
        self.chrome_options.add_argument("--headless")  # Executar em modo headless
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        # Aumentar o timeout e adicionar opções de estabilidade
        self.chrome_options.add_argument("--dns-prefetch-disable")
        self.chrome_options.add_argument("--disable-extensions")
        
        # Definir preferências para download automático de PDFs
        prefs = {
            "download.default_directory": os.path.abspath(download_folder),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0
        }
        self.chrome_options.add_experimental_option("prefs", prefs)
        
        # Inicializa o dataframe para armazenar os resultados
        self.df = pd.DataFrame(columns=[
            "Nome do Empreendimento", "Classe", "Decisão", 
            "Exigência (RCA/EIA-RIMA/Nenhuma)", "Atividade Principal", 
            "Município", "Ano da Decisão", "Link para o Parecer Técnico"
        ])

    def iniciar_driver(self):
        """Inicializa o WebDriver do Selenium"""
        logger.info("Iniciando o WebDriver...")
        try:
            # Usar o ChromeDriverManager para gerenciar automaticamente a instalação do ChromeDriver
            servico = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=servico, options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, 15)  # Aumentado para 15 segundos
            return True
        except Exception as e:
            logger.error(f"Erro ao iniciar o WebDriver: {str(e)}")
            return False
        
    def fechar_driver(self):
        """Fecha o WebDriver"""
        logger.info("Fechando o WebDriver...")
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Erro ao fechar o WebDriver: {str(e)}")
            
    def aplicar_filtros(self):
        """
        Acessa o portal e aplica os filtros conforme especificações
        """
        logger.info("Acessando o portal e aplicando filtros...")
        
        try:
            # Acessar a URL principal
            self.driver.get(self.base_url)
            time.sleep(5)  # Aguarda o carregamento da página (aumentado)
            
            # Selecionar classes 5 e 6 (baseado nas capturas de tela)
            try:
                # Clique no dropdown de classe
                classe_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "select[name='LicencaSearch[classe]']")))
                select_classe = Select(classe_dropdown)
                
                # Selecionar classe 5 e 6 (verificar se é possível selecionar múltiplos)
                select_classe.select_by_visible_text("Classe 5")
                logger.info("Classe 5 selecionada")
                # Tentar selecionar classe 6 também
                try:
                    select_classe.select_by_visible_text("Classe 6")
                    logger.info("Classe 6 selecionada")
                except:
                    logger.warning("Não foi possível selecionar múltiplas classes. Usando apenas Classe 5.")
            except Exception as e:
                logger.error(f"Erro ao selecionar Classe: {str(e)}")
                # Tentar usar alternativa - selecionar apenas uma classe por vez
                try:
                    classe_input = self.wait.until(EC.presence_of_element_located((By.ID, "licencasearch-classe")))
                    classe_input.clear()
                    classe_input.send_keys("5")
                    logger.info("Aplicado filtro de Classe usando campo de entrada")
                except:
                    logger.error("Falha ao aplicar filtro de Classe")
                    pass
            
            # Selecionar decisão Deferida
            try:
                decisao_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "select[name='LicencaSearch[decisao]']")))
                select_decisao = Select(decisao_dropdown)
                select_decisao.select_by_visible_text("Deferida")
                logger.info("Decisão 'Deferida' selecionada")
            except Exception as e:
                logger.error(f"Erro ao selecionar Decisão: {str(e)}")
                pass
            
            # Filtrar por anos de 2015 a 2024
            try:
                # Ano inicial (2015)
                ano_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "select[name='LicencaSearch[ano]']")))
                select_ano = Select(ano_dropdown)
                select_ano.select_by_value("2015")
                logger.info("Ano 2015 selecionado")
                
                # Selecionar todos os anos até 2024
                # Note: O site pode não permitir selecionar múltiplos anos, pode ser preciso fazer várias consultas
            except Exception as e:
                logger.error(f"Erro ao selecionar Ano: {str(e)}")
                # Alternativa - usar campo de entrada se disponível
                try:
                    ano_input = self.wait.until(EC.presence_of_element_located((By.ID, "licencasearch-ano")))
                    ano_input.clear()
                    ano_input.send_keys("2015")
                    logger.info("Aplicado filtro de Ano usando campo de entrada")
                except:
                    logger.error("Falha ao aplicar filtro de Ano")
                    pass
            
            # Clicar no botão de pesquisa
            try:
                pesquisar_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
                pesquisar_button.click()
                logger.info("Botão de pesquisa clicado")
            except Exception as e:
                logger.error(f"Erro ao clicar no botão de pesquisa: {str(e)}")
                # Tentar abordagem alternativa
                try:
                    self.driver.execute_script("document.querySelector('button[type=\"submit\"]').click();")
                    logger.info("Botão de pesquisa clicado via JavaScript")
                except:
                    logger.error("Falha ao clicar no botão de pesquisa")
                    return False
            
            # Aguardar o carregamento dos resultados
            time.sleep(5)
            
            # Verificar se a pesquisa retornou resultados
            try:
                resultados = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table")))
                logger.info("Pesquisa retornou resultados")
                return True
            except:
                logger.warning("A pesquisa não retornou resultados ou a página não carregou corretamente")
                return False
            
        except Exception as e:
            logger.error(f"Erro ao aplicar filtros: {str(e)}")
            return False
            
    def coletar_dados_da_pagina(self):
        """
        Coleta os dados da página atual de resultados
        """
        logger.info("Coletando dados da página atual...")
        
        try:
            # Aguardar tabela de resultados
            tabela = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table")))
            
            # Obter todas as linhas da tabela (exceto cabeçalho)
            linhas = tabela.find_elements(By.TAG_NAME, "tr")[1:]  # Ignora a primeira linha (cabeçalho)
            
            resultados_pagina = []
            
            for linha in linhas:
                try:
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    
                    # Baseado nas capturas de tela, ajustamos os índices
                    # Verificar se temos colunas suficientes
                    if len(colunas) < 7:
                        logger.warning(f"Linha com número insuficiente de colunas: {len(colunas)}")
                        continue
                    
                    # Coletar dados da linha com base na estrutura vista nas capturas
                    try:
                        # Baseado nas capturas, as colunas parecem ser:
                        # Regional | Município | Empreendimento | CNPJ/CPF | Processo Adm | Nº Protocolo | Modalidade | Classe | Atividade | Ano | Mês | Data Publicação | Decisão
                        
                        # Ajustar índices conforme necessário após inspeção
                        regional = colunas[0].text.strip()
                        municipio = colunas[1].text.strip()
                        nome_empreendimento = colunas[2].text.strip()
                        classe = "" 
                        decisao = ""
                        atividade_principal = ""
                        ano_decisao = ""
                        
                        # Localizar as colunas corretas baseado nos cabeçalhos da tabela
                        for i, col in enumerate(colunas):
                            header_text = self.driver.find_elements(By.TAG_NAME, "th")[i].text.strip().lower()
                            col_text = col.text.strip()
                            
                            if "classe" in header_text:
                                classe = col_text
                            elif "decisão" in header_text:
                                decisao = col_text
                            elif "atividade" in header_text:
                                atividade_principal = col_text
                            elif "ano" in header_text:
                                ano_decisao = col_text
                        
                        # Pegar o link para o processo (botão "Visualizar" na última coluna)
                        visualizar_link = None
                        try:
                            visualizar_btn = colunas[-1].find_element(By.LINK_TEXT, "Visualizar")
                            visualizar_link = visualizar_btn.get_attribute("href")
                        except:
                            try:
                                # Tentar encontrar qualquer link na linha
                                links = linha.find_elements(By.TAG_NAME, "a")
                                for link in links:
                                    if link.text.strip().lower() == "visualizar":
                                        visualizar_link = link.get_attribute("href")
                                        break
                            except:
                                logger.warning("Não foi possível encontrar o link de visualização para este processo")
                                visualizar_link = ""
                        
                        # Se algum dado crítico estiver faltando, pular para o próximo
                        if not nome_empreendimento or not visualizar_link:
                            logger.warning(f"Dados críticos faltando para o processo. Nome: '{nome_empreendimento}', Link: '{visualizar_link}'")
                            continue
                            
                        resultados_pagina.append({
                            "Nome do Empreendimento": nome_empreendimento,
                            "Classe": classe,
                            "Decisão": decisao,
                            "Atividade Principal": atividade_principal,
                            "Município": municipio,
                            "Ano da Decisão": ano_decisao,
                            "Link para o Parecer Técnico": visualizar_link,
                            "Exigência (RCA/EIA-RIMA/Nenhuma)": "Não analisado"
                        })
                        
                    except Exception as e:
                        logger.error(f"Erro ao extrair dados da linha: {str(e)}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Erro ao processar linha da tabela: {str(e)}")
                    continue
            
            logger.info(f"Coletados {len(resultados_pagina)} resultados da página atual")
            return resultados_pagina
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados da página: {str(e)}")
            return []
    
    def verificar_exigencia_no_parecer(self, texto_parecer):
        """
        Analisa o texto do parecer técnico para identificar exigências de RCA ou EIA/RIMA
        """
        # Extrair os primeiros 2000 caracteres (ou todo o texto se for menor)
        amostra_texto = texto_parecer[:3000].lower()
        
        # Verificar menções a RCA
        padrao_rca = re.compile(r'rca|relatório\s+de\s+controle\s+ambiental')
        if padrao_rca.search(amostra_texto):
            return "RCA"
        
        # Verificar menções a EIA/RIMA
        padrao_eia_rima = re.compile(r'eia(?:\s*/\s*|-)?rima|estudo\s+de\s+impacto\s+ambiental')
        if padrao_eia_rima.search(amostra_texto):
            return "EIA/RIMA"
            
        return "Nenhuma"
    
    def extrair_texto_do_pdf(self, caminho_pdf):
        """
        Extrai o texto de um arquivo PDF usando PyMuPDF
        """
        texto = ""
        try:
            with fitz.open(caminho_pdf) as doc:
                for pagina in doc:
                    texto += pagina.get_text()
            return texto
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {str(e)}")
            return ""
    
    def analisar_processo(self, link_processo):
        """
        Acessa o processo e analisa o parecer técnico
        """
        logger.info(f"Analisando processo: {link_processo}")
        exigencia = "Não identificado"
        link_parecer = ""
        
        try:
            # Acessar página do processo
            self.driver.get(link_processo)
            time.sleep(5)  # Aguardar carregamento
            
            # Procurar link do parecer técnico (baseado nas capturas de tela)
            # Procurar na seção "Parecer Único/Parecer de Licenciamento Ambiental Simplificado"
            try:
                # Buscar todos os links na página
                links = self.driver.find_elements(By.TAG_NAME, "a")
                
                for link in links:
                    texto_link = link.text.lower()
                    href = link.get_attribute("href") or ""
                    
                    # Verificar se o link contém palavras-chave relacionadas a parecer e é um PDF
                    if any(keyword in texto_link.lower() for keyword in ["parecer", "técnico", "pu-", "pt-"]) and href.endswith(".pdf"):
                        link_parecer = href
                        logger.info(f"Encontrado link do parecer: {link_parecer}")
                        
                        try:
                            # Baixar o PDF diretamente usando requests
                            nome_arquivo = f"parecer_{int(time.time())}.pdf"
                            caminho_pdf = os.path.join(self.download_folder, nome_arquivo)
                            
                            response = requests.get(link_parecer, timeout=30)
                            if response.status_code == 200:
                                with open(caminho_pdf, 'wb') as f:
                                    f.write(response.content)
                                logger.info(f"PDF baixado para: {caminho_pdf}")
                                
                                # Extrair texto do PDF
                                texto_parecer = self.extrair_texto_do_pdf(caminho_pdf)
                                
                                # Analisar o texto para identificar exigências
                                if texto_parecer:
                                    exigencia = self.verificar_exigencia_no_parecer(texto_parecer)
                                    logger.info(f"Exigência identificada: {exigencia}")
                                else:
                                    logger.warning("Não foi possível extrair texto do PDF")
                            else:
                                logger.warning(f"Falha ao baixar PDF: Status {response.status_code}")
                        except Exception as e:
                            logger.error(f"Erro ao baixar/processar o PDF: {str(e)}")
                            
                        break
                        
                if not link_parecer:
                    logger.warning("Nenhum link de parecer encontrado neste processo")
                    
            except Exception as e:
                logger.error(f"Erro ao buscar parecer técnico: {str(e)}")
                
            return exigencia, link_parecer
            
        except Exception as e:
            logger.error(f"Erro ao analisar processo: {str(e)}")
            return "Erro na análise", ""
    
    def navegar_para_proxima_pagina(self):
        """
        Navega para a próxima página de resultados
        Retorna True se conseguiu navegar, False se não há mais páginas
        """
        try:
            # Procurar links de paginação
            try:
                # Com base nas capturas, verificar elementos de paginação
                pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, ".pagination li")
                
                # Procurar botão "próximo" (geralmente é o último ou penúltimo elemento)
                for elemento in pagination_elements:
                    # Verificar se tem o caractere '»' ou 'próximo'
                    if "»" in elemento.text or "próximo" in elemento.text.lower():
                        # Verificar se o elemento está desabilitado
                        if "disabled" in elemento.get_attribute("class"):
                            logger.info("Botão de próxima página está desabilitado. Fim da paginação.")
                            return False
                            
                        # Clicar no link dentro do elemento de paginação
                        try:
                            link = elemento.find_element(By.TAG_NAME, "a")
                            link.click()
                            time.sleep(3)  # Aguardar carregamento da próxima página
                            logger.info("Navegado para a próxima página")
                            return True
                        except:
                            logger.warning("Elemento de próxima página encontrado, mas não foi possível clicar")
                            return False
                
                logger.warning("Elemento de próxima página não encontrado")
                return False
                
            except Exception as e:
                logger.error(f"Erro ao procurar elementos de paginação: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao navegar para próxima página: {str(e)}")
            return False
    
    def executar_coleta(self, max_paginas=10, max_processos_por_pagina=None):
        """
        Executa a coleta completa dos dados
        """
        try:
            if not self.iniciar_driver():
                logger.error("Falha ao iniciar o WebDriver. Encerrando coleta.")
                return pd.DataFrame()
            
            # Aplicar filtros iniciais
            if not self.aplicar_filtros():
                logger.error("Falha ao aplicar filtros. Encerrando coleta.")
                self.fechar_driver()
                return pd.DataFrame()
            
            todos_resultados = []
            pagina_atual = 1
            
            while pagina_atual <= max_paginas:
                logger.info(f"Processando página {pagina_atual}...")
                
                # Coletar dados da página atual
                resultados_pagina = self.coletar_dados_da_pagina()
                
                # Limitar número de processos por página (para testes)
                if max_processos_por_pagina:
                    resultados_pagina = resultados_pagina[:max_processos_por_pagina]
                
                # Para cada processo, analisar o parecer técnico
                for i, resultado in enumerate(resultados_pagina):
                    logger.info(f"Analisando processo {i+1}/{len(resultados_pagina)} da página {pagina_atual}")
                    
                    exigencia, link_parecer = self.analisar_processo(resultado["Link para o Parecer Técnico"])
                    resultado["Exigência (RCA/EIA-RIMA/Nenhuma)"] = exigencia
                    
                    # Atualizar o link apenas se um novo for encontrado
                    if link_parecer:
                        resultado["Link para o Parecer Técnico"] = link_parecer
                    
                    # Pausa para não sobrecarregar o servidor
                    time.sleep(3)
                
                # Adicionar resultados desta página ao total
                todos_resultados.extend(resultados_pagina)
                
                # Se não coletamos resultados nesta página, não continuar
                if not resultados_pagina:
                    logger.warning("Nenhum resultado coletado na página atual. Encerrando coleta.")
                    break
                
                # Navegar para próxima página
                tem_proxima_pagina = self.navegar_para_proxima_pagina()
                if not tem_proxima_pagina:
                    logger.info("Não há mais páginas. Finalizando coleta.")
                    break
                    
                pagina_atual += 1
            
            # Converter resultados para DataFrame
            df_resultados = pd.DataFrame(todos_resultados)
            
            # Salvar resultados
            if not df_resultados.empty:
                self.salvar_resultados(df_resultados)
            else:
                logger.warning("Nenhum resultado para salvar.")
            
            return df_resultados
            
        except Exception as e:
            logger.error(f"Erro durante a coleta de dados: {str(e)}")
            return pd.DataFrame()
            
        finally:
            self.fechar_driver()
    
    def salvar_resultados(self, df):
        """
        Salva os resultados em arquivo Excel e CSV
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Salvar em Excel
            excel_path = f"processos_ambientais_mg_{timestamp}.xlsx"
            df.to_excel(excel_path, index=False)
            logger.info(f"Resultados salvos em Excel: {excel_path}")
            
            # Salvar em CSV
            csv_path = f"processos_ambientais_mg_{timestamp}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"Resultados salvos em CSV: {csv_path}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {str(e)}")


if __name__ == "__main__":
    # Limites para testes (reduzir para testes iniciais)
    MAX_PAGINAS = 5  # Limitar a 5 páginas para teste
    MAX_PROCESSOS_POR_PAGINA = 3  # Limitar a 3 processos por página para teste
    
    logger.info("Iniciando coleta de licenças ambientais...")
    
    scraper = LicencasAmbientaisScraper(download_folder="pareceres")
    resultados = scraper.executar_coleta(
        max_paginas=MAX_PAGINAS,
        max_processos_por_pagina=MAX_PROCESSOS_POR_PAGINA
    )
    
    logger.info(f"Coleta finalizada. Total de {len(resultados)} processos coletados.") 