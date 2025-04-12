import requests
import logging
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("teste_conexao.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def testar_requests():
    """
    Testa a conexão com o site da SEMAD usando requests
    """
    logger.info("Testando conexão com requests...")
    
    urls = [
        "https://sistemas.meioambiente.mg.gov.br/licenciamento/site/consulta-licenca",
        "https://www.google.com",  # Site de referência para comparação
    ]
    
    for url in urls:
        try:
            start = time.time()
            response = requests.get(url, timeout=30)
            elapsed = time.time() - start
            
            logger.info(f"Conectado a {url} com status {response.status_code} em {elapsed:.2f} segundos")
            logger.info(f"Tamanho da resposta: {len(response.content)} bytes")
            
            if response.status_code == 200:
                logger.info(f"Conexão bem-sucedida com {url}")
            else:
                logger.warning(f"Conexão com {url} retornou status {response.status_code}")
                
        except requests.exceptions.ConnectTimeout:
            logger.error(f"Timeout ao conectar com {url}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão com {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Erro genérico ao conectar com {url}: {str(e)}")

def testar_selenium():
    """
    Testa a conexão com o site da SEMAD usando Selenium
    """
    logger.info("Testando conexão com Selenium...")
    
    # Configurações do Chrome
    chrome_options = Options()
    # Descomente a linha abaixo se quiser ver o navegador
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # Iniciar o driver
        logger.info("Iniciando Chrome WebDriver...")
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        
        # Testar conexão com o site da SEMAD
        logger.info("Acessando site da SEMAD...")
        driver.get("https://sistemas.meioambiente.mg.gov.br/licenciamento/site/consulta-licenca")
        time.sleep(5)
        
        # Verificar se a página carregou
        page_source = driver.page_source
        
        if "Consulta de Decisões de Processos de Licenciamento Ambiental" in page_source:
            logger.info("Página da SEMAD carregada com sucesso!")
            logger.info(f"Título da página: {driver.title}")
            
            # Verificar elementos específicos
            logger.info("Testando elementos da interface...")
            try:
                form_elements = driver.find_elements("tag name", "select")
                logger.info(f"Encontrados {len(form_elements)} elementos select")
                
                for i, element in enumerate(form_elements):
                    name = element.get_attribute("name") or ""
                    options = len(element.find_elements("tag name", "option"))
                    logger.info(f"Select #{i}: name='{name}', options={options}")
            
            except Exception as e:
                logger.error(f"Erro ao verificar elementos da interface: {str(e)}")
        else:
            logger.error("Página da SEMAD não carregou corretamente")
            logger.info(f"Conteúdo da página: {page_source[:500]}...")
        
        # Teste de sites de referência
        logger.info("Acessando google.com para comparação...")
        driver.get("https://www.google.com")
        time.sleep(2)
        
        if "Google" in driver.title:
            logger.info("Página do Google carregada com sucesso!")
        else:
            logger.error("Página do Google não carregou corretamente")
        
    except Exception as e:
        logger.error(f"Erro ao testar com Selenium: {str(e)}")
    finally:
        try:
            driver.quit()
            logger.info("WebDriver encerrado")
        except:
            pass

def verificar_rede():
    """
    Verifica configurações de rede e ambiente
    """
    logger.info("Verificando configurações de rede...")
    
    # Verificar proxy
    proxies = {
        'http': os.environ.get('HTTP_PROXY', ''),
        'https': os.environ.get('HTTPS_PROXY', '')
    }
    
    logger.info(f"Configurações de proxy: {proxies}")
    
    # Verificar firewall e outros bloqueios
    logger.info("Verificando conexão com portas comuns...")
    
    ports_to_check = [80, 443, 8080]
    for port in ports_to_check:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            result = s.connect_ex(("sistemas.meioambiente.mg.gov.br", port))
            s.close()
            if result == 0:
                logger.info(f"Porta {port} está aberta")
            else:
                logger.warning(f"Porta {port} parece estar fechada (código: {result})")
        except Exception as e:
            logger.error(f"Erro ao verificar porta {port}: {str(e)}")

if __name__ == "__main__":
    import os
    
    logger.info("=" * 50)
    logger.info("INICIANDO TESTE DE CONEXÃO")
    logger.info("=" * 50)
    
    logger.info(f"Diretório atual: {os.getcwd()}")
    logger.info(f"Versão do Python: {sys.version}")
    
    # Testar conexão básica com requests
    testar_requests()
    
    # Verificar configurações de rede
    verificar_rede()
    
    # Testar com Selenium
    testar_selenium()
    
    logger.info("=" * 50)
    logger.info("TESTE DE CONEXÃO FINALIZADO")
    logger.info("=" * 50) 