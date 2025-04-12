import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os
import logging
from datetime import datetime
import urllib.parse
import fitz  # PyMuPDF

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("licencas_alternativo.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class LicencasAmbientaisScraperAlternativo:
    def __init__(self, download_folder="pareceres"):
        """
        Inicializa o scraper para coleta de licenças ambientais de MG
        Versão alternativa usando apenas requests e BeautifulSoup
        """
        self.base_url = "https://sistemas.meioambiente.mg.gov.br/licenciamento/site/consulta-licenca"
        self.download_folder = download_folder
        
        # Criar pasta para downloads se não existir
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        # Inicializar sessão para manter cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Inicializa o dataframe para armazenar os resultados
        self.df = pd.DataFrame(columns=[
            "Nome do Empreendimento", "Classe", "Decisão", 
            "Exigência (RCA/EIA-RIMA/Nenhuma)", "Atividade Principal", 
            "Município", "Ano da Decisão", "Link para o Parecer Técnico"
        ])

    def obter_csrf_token(self, html_content):
        """
        Extrai o token CSRF do HTML para enviar formulários
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        # Procurar pelo token CSRF (pode variar dependendo do site)
        csrf_token = None
        
        # Procurar em meta tags
        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
        if csrf_meta:
            csrf_token = csrf_meta.get('content')
            
        # Procurar em campos de input
        if not csrf_token:
            csrf_input = soup.find('input', attrs={'name': '_csrf'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
                
        return csrf_token

    def aplicar_filtros(self, ano_inicial=2015, ano_final=2024, classe="5", decisao="Deferida"):
        """
        Aplica filtros na busca por requests
        """
        logger.info(f"Aplicando filtros: Ano {ano_inicial}-{ano_final}, Classe {classe}, Decisão {decisao}")
        
        try:
            # Primeiro, acessar a página para obter cookies e token CSRF
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                logger.error(f"Erro ao acessar página inicial: {response.status_code}")
                return None
                
            # Obter token CSRF se necessário
            csrf_token = self.obter_csrf_token(response.text)
            if csrf_token:
                logger.info(f"Token CSRF encontrado: {csrf_token}")
                
            # Preparar os parâmetros do filtro
            params = {
                'LicencaSearch[regional_id]': '',
                'LicencaSearch[municipio_id]': '',
                'LicencaSearch[empreendimento]': '',
                'LicencaSearch[cnpj]': '',
                'LicencaSearch[processo_adm]': '',
                'LicencaSearch[numero_protocolo]': '',
                'LicencaSearch[modalidade]': '',
                'LicencaSearch[classe]': classe,
                'LicencaSearch[atividade_id]': '',
                'LicencaSearch[ano]': str(ano_inicial),
                'LicencaSearch[mes]': '',
                'LicencaSearch[data]': '',
                'LicencaSearch[decisao]': decisao
            }
            
            # Adicionar token CSRF se encontrado
            if csrf_token:
                params['_csrf'] = csrf_token
                
            # Fazer a consulta
            search_url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
            logger.info(f"URL de consulta: {search_url}")
            
            # Executar a consulta
            response = self.session.get(search_url)
            
            if response.status_code == 200:
                logger.info("Filtros aplicados com sucesso")
                return response.text
            else:
                logger.error(f"Erro ao aplicar filtros: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao aplicar filtros: {str(e)}")
            return None
    
    def processar_resultados(self, html_content):
        """
        Processa o HTML da página de resultados para extrair os dados
        """
        if not html_content:
            logger.error("Sem conteúdo para processar")
            return []
            
        logger.info("Processando página de resultados...")
        resultados = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Localizar a tabela de resultados
            tabela = soup.find('table', class_='table')
            if not tabela:
                logger.warning("Tabela de resultados não encontrada")
                return []
                
            # Obter as linhas da tabela (exceto cabeçalho)
            linhas = tabela.find_all('tr')[1:]  # Ignorar a primeira linha (cabeçalho)
            logger.info(f"Encontradas {len(linhas)} linhas na tabela")
            
            # Obter os nomes das colunas do cabeçalho para identificar os índices
            colunas_indices = {}
            cabecalhos = tabela.find_all('th')
            for i, cabecalho in enumerate(cabecalhos):
                texto = cabecalho.text.strip().lower()
                if 'empreendimento' in texto:
                    colunas_indices['empreendimento'] = i
                elif 'município' in texto:
                    colunas_indices['municipio'] = i
                elif 'classe' in texto:
                    colunas_indices['classe'] = i
                elif 'decisão' in texto:
                    colunas_indices['decisao'] = i
                elif 'atividade' in texto:
                    colunas_indices['atividade'] = i
                elif 'ano' in texto:
                    colunas_indices['ano'] = i
            
            logger.info(f"Mapeamento de colunas: {colunas_indices}")
            
            # Processar cada linha
            for linha in linhas:
                try:
                    colunas = linha.find_all('td')
                    if len(colunas) < len(cabecalhos):
                        continue
                        
                    # Extrair dados com base nos índices mapeados
                    dados = {
                        "Nome do Empreendimento": colunas[colunas_indices.get('empreendimento', 2)].text.strip() if 'empreendimento' in colunas_indices else "",
                        "Município": colunas[colunas_indices.get('municipio', 1)].text.strip() if 'municipio' in colunas_indices else "",
                        "Classe": colunas[colunas_indices.get('classe', 7)].text.strip() if 'classe' in colunas_indices else "",
                        "Decisão": colunas[colunas_indices.get('decisao', 12)].text.strip() if 'decisao' in colunas_indices else "",
                        "Atividade Principal": colunas[colunas_indices.get('atividade', 8)].text.strip() if 'atividade' in colunas_indices else "",
                        "Ano da Decisão": colunas[colunas_indices.get('ano', 9)].text.strip() if 'ano' in colunas_indices else "",
                        "Exigência (RCA/EIA-RIMA/Nenhuma)": "Não analisado"
                    }
                    
                    # Encontrar o link para a página de detalhes do processo
                    link_visualizar = None
                    for coluna in colunas:
                        link = coluna.find('a', text='Visualizar')
                        if link:
                            link_visualizar = urllib.parse.urljoin(self.base_url, link.get('href'))
                            break
                            
                    if not link_visualizar:
                        logger.warning(f"Link 'Visualizar' não encontrado para: {dados['Nome do Empreendimento']}")
                        continue
                        
                    dados["Link para o Parecer Técnico"] = link_visualizar
                    resultados.append(dados)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar linha da tabela: {str(e)}")
                    continue
                    
            logger.info(f"Processados {len(resultados)} resultados")
            return resultados
            
        except Exception as e:
            logger.error(f"Erro ao processar resultados: {str(e)}")
            return []
    
    def obter_proxima_pagina_url(self, html_content):
        """
        Extrai a URL da próxima página dos resultados
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Procurar os links de paginação
            pagination = soup.find('ul', class_='pagination')
            if not pagination:
                logger.warning("Elemento de paginação não encontrado")
                return None
                
            # Procurar o link para a próxima página
            for link in pagination.find_all('a'):
                if '»' in link.text or 'próxima' in link.text.lower():
                    href = link.get('href')
                    if href:
                        return urllib.parse.urljoin(self.base_url, href)
            
            logger.info("Link para próxima página não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar link da próxima página: {str(e)}")
            return None
    
    def extrair_link_parecer(self, html_content):
        """
        Extrai o link do parecer técnico da página de detalhes do processo
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Procurar pela seção de pareceres
            for h3 in soup.find_all('h3'):
                if 'parecer' in h3.text.lower():
                    # Procurar pelo link do PDF na mesma seção
                    section = h3.find_parent('div')
                    if section:
                        links = section.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if href.endswith('.pdf'):
                                return urllib.parse.urljoin(self.base_url, href)
            
            # Se não encontrou por h3, buscar diretamente pelos links
            for link in soup.find_all('a'):
                href = link.get('href', '')
                texto = link.text.lower()
                if href.endswith('.pdf') and ('parecer' in texto or 'técnico' in texto or 'pu-' in texto):
                    return urllib.parse.urljoin(self.base_url, href)
                    
            logger.warning("Link do parecer técnico não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair link do parecer: {str(e)}")
            return None
    
    def baixar_pdf(self, url, nome_arquivo=None):
        """
        Baixa um arquivo PDF a partir da URL
        """
        if not url:
            return None
            
        try:
            logger.info(f"Baixando PDF: {url}")
            
            if not nome_arquivo:
                nome_arquivo = f"parecer_{int(time.time())}.pdf"
                
            caminho_completo = os.path.join(self.download_folder, nome_arquivo)
            
            # Baixar o arquivo
            response = self.session.get(url, stream=True, timeout=30)
            
            if response.status_code == 200:
                with open(caminho_completo, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                logger.info(f"PDF baixado com sucesso: {caminho_completo}")
                return caminho_completo
            else:
                logger.error(f"Erro ao baixar PDF: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar PDF: {str(e)}")
            return None
    
    def verificar_exigencia_no_parecer(self, texto_parecer):
        """
        Analisa o texto do parecer técnico para identificar exigências de RCA ou EIA/RIMA
        """
        if not texto_parecer:
            return "Não analisado"
            
        # Extrair os primeiros 3000 caracteres (ou todo o texto se for menor)
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
        if not caminho_pdf or not os.path.exists(caminho_pdf):
            return ""
            
        texto = ""
        try:
            with fitz.open(caminho_pdf) as doc:
                for pagina in doc:
                    texto += pagina.get_text()
            return texto
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {str(e)}")
            return ""
    
    def analisar_processo(self, url_processo):
        """
        Acessa a página de detalhes do processo e analisa o parecer técnico
        """
        logger.info(f"Analisando processo: {url_processo}")
        
        try:
            # Acessar a página de detalhes
            response = self.session.get(url_processo)
            if response.status_code != 200:
                logger.error(f"Erro ao acessar página do processo: {response.status_code}")
                return "Erro na análise", ""
                
            # Extrair o link do parecer
            link_parecer = self.extrair_link_parecer(response.text)
            if not link_parecer:
                logger.warning("Nenhum link de parecer encontrado")
                return "Sem parecer", ""
                
            # Baixar o PDF
            caminho_pdf = self.baixar_pdf(link_parecer)
            if not caminho_pdf:
                logger.error("Falha ao baixar o PDF do parecer")
                return "Erro ao baixar parecer", link_parecer
                
            # Extrair texto do PDF
            texto_parecer = self.extrair_texto_do_pdf(caminho_pdf)
            if not texto_parecer:
                logger.error("Falha ao extrair texto do PDF")
                return "Erro ao extrair texto", link_parecer
                
            # Analisar exigências
            exigencia = self.verificar_exigencia_no_parecer(texto_parecer)
            logger.info(f"Exigência identificada: {exigencia}")
            
            return exigencia, link_parecer
            
        except Exception as e:
            logger.error(f"Erro ao analisar processo: {str(e)}")
            return "Erro na análise", ""
    
    def executar_coleta(self, anos=range(2015, 2025), classes=["5", "6"], max_paginas=10, max_processos_por_pagina=None):
        """
        Executa a coleta completa dos dados para múltiplos anos e classes
        """
        todos_resultados = []
        
        for ano in anos:
            for classe in classes:
                logger.info(f"Coletando dados para Ano {ano}, Classe {classe}...")
                
                # Aplicar filtros
                html_content = self.aplicar_filtros(ano_inicial=ano, classe=classe)
                if not html_content:
                    logger.error(f"Falha ao aplicar filtros para Ano {ano}, Classe {classe}")
                    continue
                    
                pagina_atual = 1
                pagina_html = html_content
                
                while pagina_atual <= max_paginas and pagina_html:
                    logger.info(f"Processando página {pagina_atual} para Ano {ano}, Classe {classe}...")
                    
                    # Extrair resultados da página atual
                    resultados_pagina = self.processar_resultados(pagina_html)
                    
                    # Limitar número de processos por página (para testes)
                    if max_processos_por_pagina and len(resultados_pagina) > max_processos_por_pagina:
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
                        logger.warning(f"Nenhum resultado na página {pagina_atual} para Ano {ano}, Classe {classe}")
                        break
                    
                    # Obter URL da próxima página
                    proxima_pagina_url = self.obter_proxima_pagina_url(pagina_html)
                    if not proxima_pagina_url:
                        logger.info(f"Não há mais páginas para Ano {ano}, Classe {classe}")
                        break
                        
                    # Acessar próxima página
                    pagina_atual += 1
                    try:
                        response = self.session.get(proxima_pagina_url)
                        if response.status_code == 200:
                            pagina_html = response.text
                        else:
                            logger.error(f"Erro ao acessar próxima página: {response.status_code}")
                            break
                    except Exception as e:
                        logger.error(f"Erro ao acessar próxima página: {str(e)}")
                        break
        
        # Converter resultados para DataFrame
        df_resultados = pd.DataFrame(todos_resultados)
        
        # Salvar resultados
        if not df_resultados.empty:
            self.salvar_resultados(df_resultados)
        else:
            logger.warning("Nenhum resultado para salvar")
        
        return df_resultados
    
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
    # Limites para testes
    ANOS_COLETA = [2015, 2016]  # Reduzido para teste
    CLASSES_COLETA = ["5", "6"]
    MAX_PAGINAS = 3  # Limitar a 3 páginas por combinação ano-classe
    MAX_PROCESSOS_POR_PAGINA = 2  # Limitar a 2 processos por página
    
    logger.info("Iniciando coleta alternativa de licenças ambientais...")
    
    scraper = LicencasAmbientaisScraperAlternativo(download_folder="pareceres")
    resultados = scraper.executar_coleta(
        anos=ANOS_COLETA,
        classes=CLASSES_COLETA,
        max_paginas=MAX_PAGINAS,
        max_processos_por_pagina=MAX_PROCESSOS_POR_PAGINA
    )
    
    logger.info(f"Coleta finalizada. Total de {len(resultados)} processos coletados.") 