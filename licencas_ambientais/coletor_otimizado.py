import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import logging
from datetime import datetime
import urllib.parse
import csv

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("coletor_otimizado.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ColetorOtimizado:
    def __init__(self):
        """
        Inicializa o coletor otimizado para obter dados diretos da tabela de resultados
        """
        self.base_url = "https://sistemas.meioambiente.mg.gov.br/licenciamento/site/consulta-licenca"
        
        # Inicializar sessão para manter cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })

    def obter_csrf_token(self, html_content):
        """
        Extrai o token CSRF do HTML para enviar formulários
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Procurar em meta tags
        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
        if csrf_meta:
            return csrf_meta.get('content')
            
        # Procurar em campos de input
        csrf_input = soup.find('input', attrs={'name': '_csrf'})
        if csrf_input:
            return csrf_input.get('value')
                
        return None

    def aplicar_filtros(self, ano_inicial, classe, decisao="Deferida"):
        """
        Aplica filtros na busca por requests
        """
        logger.info(f"Aplicando filtros: Ano {ano_inicial}, Classe {classe}, Decisão {decisao}")
        
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
    
    def processar_tabela(self, html_content):
        """
        Extrai diretamente os dados da tabela para um formato estruturado
        """
        if not html_content:
            logger.error("Sem conteúdo HTML para processar")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tabela = soup.find('table', class_='table')
        
        if not tabela:
            logger.warning("Tabela não encontrada no HTML")
            return []
        
        # Obter cabeçalhos da tabela
        cabecalhos = []
        for th in tabela.find_all('th'):
            cabecalhos.append(th.text.strip())
        
        logger.info(f"Cabeçalhos encontrados: {cabecalhos}")
        
        # Mapear índices de colunas importantes
        indices = {}
        for i, cabecalho in enumerate(cabecalhos):
            cabecalho_lower = cabecalho.lower()
            if 'regional' in cabecalho_lower:
                indices['regional'] = i
            elif 'município' in cabecalho_lower:
                indices['municipio'] = i
            elif 'empreendimento' in cabecalho_lower:
                indices['empreendimento'] = i
            elif 'cnpj' in cabecalho_lower:
                indices['cnpj'] = i
            elif 'processo' in cabecalho_lower:
                indices['processo'] = i
            elif 'modalidade' in cabecalho_lower:
                indices['modalidade'] = i
            elif 'classe' in cabecalho_lower:
                indices['classe'] = i
            elif 'atividade' in cabecalho_lower:
                indices['atividade'] = i
            elif 'ano' in cabecalho_lower:
                indices['ano'] = i
            elif 'mês' in cabecalho_lower:
                indices['mes'] = i
            elif 'data' in cabecalho_lower and 'publicação' in cabecalho_lower:
                indices['data_publicacao'] = i
            elif 'decisão' in cabecalho_lower:
                indices['decisao'] = i
        
        # Coletar dados de cada linha
        resultados = []
        linhas = tabela.find_all('tr')[1:]  # Ignorar a linha de cabeçalho
        
        for linha in linhas:
            colunas = linha.find_all('td')
            if len(colunas) < len(cabecalhos):
                continue
            
            # Extrair link para visualizar processo
            link_processo = ""
            link_btn = linha.find('a', text='Visualizar')
            if link_btn:
                link_processo = urllib.parse.urljoin(self.base_url, link_btn.get('href', ''))
            
            # Coletar dados conforme o mapeamento de índices
            dados = {
                "Nome do Empreendimento": colunas[indices.get('empreendimento', 2)].text.strip() if 'empreendimento' in indices else "",
                "Classe": colunas[indices.get('classe', 7)].text.strip() if 'classe' in indices else "",
                "Decisão": colunas[indices.get('decisao', 12)].text.strip() if 'decisao' in indices else "Deferida",
                "Exigência (RCA/EIA-RIMA/Nenhuma)": "A definir",  # Será definido depois
                "Atividade Principal": colunas[indices.get('atividade', 8)].text.strip() if 'atividade' in indices else "",
                "Município": colunas[indices.get('municipio', 1)].text.strip() if 'municipio' in indices else "",
                "Ano da Decisão": colunas[indices.get('ano', 9)].text.strip() if 'ano' in indices else "",
                "Link para o Parecer Técnico": link_processo,
                "Regional": colunas[indices.get('regional', 0)].text.strip() if 'regional' in indices else "",
                "CNPJ/CPF": colunas[indices.get('cnpj', 3)].text.strip() if 'cnpj' in indices else "",
                "Processo Adm": colunas[indices.get('processo', 4)].text.strip() if 'processo' in indices else "",
                "Modalidade": colunas[indices.get('modalidade', 6)].text.strip() if 'modalidade' in indices else "",
                "Data de Publicação": colunas[indices.get('data_publicacao', 11)].text.strip() if 'data_publicacao' in indices else "",
            }
            
            resultados.append(dados)
        
        logger.info(f"Extraídos {len(resultados)} registros da tabela")
        return resultados
    
    def obter_url_proxima_pagina(self, html_content):
        """
        Extrai a URL da próxima página de resultados
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        paginacao = soup.find('ul', class_='pagination')
        if not paginacao:
            return None
        
        for li in paginacao.find_all('li'):
            a = li.find('a')
            if a and ('»' in a.text or 'próximo' in a.text.lower()):
                href = a.get('href')
                if href:
                    return urllib.parse.urljoin(self.base_url, href)
        
        return None
    
    def acessar_pagina_processo(self, url):
        """
        Acessa a página de detalhes do processo
        """
        try:
            logger.info(f"Acessando página de processo: {url}")
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                logger.info("Página do processo acessada com sucesso")
                return response.text
            else:
                logger.warning(f"Erro ao acessar página do processo: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erro ao acessar página do processo: {str(e)}")
            return None
    
    def verificar_exigencia(self, html_content):
        """
        Verifica as exigências no HTML da página do processo com método avançado
        """
        if not html_content:
            return "Não identificado"
        
        soup = BeautifulSoup(html_content, 'html.parser')
        texto_completo = soup.get_text().lower()
        
        # Lista expandida de termos para RCA
        termos_rca = [
            'rca', 
            'relatório de controle ambiental',
            'relatorio de controle',
            'controle ambiental',
            'r.c.a',
            'r c a',
            'r.c.a.'
        ]
        
        # Lista expandida de termos para EIA/RIMA
        termos_eia_rima = [
            'eia', 'rima',
            'eia/rima', 'eia-rima',
            'estudo de impacto ambiental',
            'relatório de impacto',
            'estudo ambiental',
            'impacto ambiental',
            'e.i.a', 'r.i.m.a',
            'e i a', 'r i m a',
            'e.i.a.', 'r.i.m.a.'
        ]
        
        # Dividir o texto em parágrafos
        paragrafos = texto_completo.split('\n\n')
        inicio = ' '.join(paragrafos[:10] if len(paragrafos) > 10 else paragrafos)
        
        # Tentar encontrar conclusão ou parecer final
        conclusao = ""
        for i, paragrafo in enumerate(paragrafos):
            if 'conclus' in paragrafo or 'parecer' in paragrafo:
                # Pegar este parágrafo e os próximos 3
                conclusao = ' '.join(paragrafos[i:i+4] if i+4 <= len(paragrafos) else paragrafos[i:])
                break
        
        # Verificar RCA em partes críticas do documento
        for termo in termos_rca:
            if termo in inicio or termo in conclusao:
                return "RCA"
                
        # Verificar EIA/RIMA em partes críticas do documento
        for termo in termos_eia_rima:
            if termo in inicio or termo in conclusao:
                return "EIA/RIMA"
        
        # Se não encontrou nas seções críticas, verificar no texto completo
        for termo in termos_rca:
            if termo in texto_completo:
                return "RCA"
                
        for termo in termos_eia_rima:
            if termo in texto_completo:
                return "EIA/RIMA"
        
        # Verificar nos títulos de documentos/links para PDFs
        for link in soup.find_all('a'):
            href = link.get('href', '')
            texto_link = link.text.lower()
            if href.endswith('.pdf'):
                # Verificar RCA nos links
                for termo in termos_rca:
                    if termo in texto_link:
                        return "RCA"
                
                # Verificar EIA/RIMA nos links
                for termo in termos_eia_rima:
                    if termo in texto_link:
                        return "EIA/RIMA"
        
        return "Nenhuma"
    
    def salvar_resultados(self, resultados, prefixo="processos_licenca"):
        """
        Salva os resultados em Excel e CSV
        """
        if not resultados:
            logger.warning("Nenhum resultado para salvar")
            return
        
        df = pd.DataFrame(resultados)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Salvar CSV
        csv_path = f"{prefixo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"Resultados salvos em CSV: {csv_path}")
        
        # Salvar Excel
        excel_path = f"{prefixo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False)
        logger.info(f"Resultados salvos em Excel: {excel_path}")
        
        # Salvar CSV simples sem pandas (para garantir)
        csv_simple_path = f"{prefixo}_simples_{timestamp}.csv"
        with open(csv_simple_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            if resultados:
                fieldnames = resultados[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for resultado in resultados:
                    writer.writerow(resultado)
        logger.info(f"Resultados salvos em CSV simples: {csv_simple_path}")
    
    def salvar_resultados_incrementais(self, resultados, filename="resultados_incrementais.csv"):
        """
        Salva resultados de forma incremental, para não perder dados em caso de falha
        """
        # Criar o arquivo se não existir
        if not os.path.exists(filename):
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if resultados:
                    fieldnames = resultados[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
        
        # Adicionar novos resultados
        with open(filename, 'a', newline='', encoding='utf-8-sig') as csvfile:
            if resultados:
                fieldnames = resultados[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                for resultado in resultados:
                    writer.writerow(resultado)
        
        logger.info(f"Salvos {len(resultados)} resultados incrementais em {filename}")
    
    def coletar_dados(self, anos, classes, max_paginas_por_consulta=100, analisar_processos=True):
        """
        Coleta dados para os anos e classes especificados
        """
        todos_resultados = []
        
        for ano in anos:
            for classe in classes:
                logger.info(f"Coletando dados para Ano={ano}, Classe={classe}")
                
                # Aplicar filtros
                html_content = self.aplicar_filtros(ano, classe)
                if not html_content:
                    logger.error(f"Falha ao aplicar filtros para Ano={ano}, Classe={classe}")
                    continue
                
                # Processar resultados da primeira página
                resultados_pagina = self.processar_tabela(html_content)
                if resultados_pagina:
                    if analisar_processos:
                        # Analisar cada processo para identificar exigências
                        for resultado in resultados_pagina:
                            if resultado["Link para o Parecer Técnico"]:
                                html_processo = self.acessar_pagina_processo(resultado["Link para o Parecer Técnico"])
                                if html_processo:
                                    exigencia = self.verificar_exigencia(html_processo)
                                    resultado["Exigência (RCA/EIA-RIMA/Nenhuma)"] = exigencia
                                time.sleep(1)  # Pausa para não sobrecarregar o servidor
                    
                    # Adicionar resultados
                    todos_resultados.extend(resultados_pagina)
                    
                    # Salvar de forma incremental para não perder dados
                    self.salvar_resultados_incrementais(resultados_pagina)
                
                # Navegar pelas páginas seguintes
                pagina_atual = 1
                proxima_pagina_url = self.obter_url_proxima_pagina(html_content)
                
                while proxima_pagina_url and pagina_atual < max_paginas_por_consulta:
                    pagina_atual += 1
                    logger.info(f"Navegando para página {pagina_atual} (Ano={ano}, Classe={classe})")
                    
                    try:
                        response = self.session.get(proxima_pagina_url)
                        if response.status_code == 200:
                            html_content = response.text
                            
                            # Processar resultados da página
                            resultados_pagina = self.processar_tabela(html_content)
                            if resultados_pagina:
                                if analisar_processos:
                                    # Analisar cada processo
                                    for resultado in resultados_pagina:
                                        if resultado["Link para o Parecer Técnico"]:
                                            html_processo = self.acessar_pagina_processo(resultado["Link para o Parecer Técnico"])
                                            if html_processo:
                                                exigencia = self.verificar_exigencia(html_processo)
                                                resultado["Exigência (RCA/EIA-RIMA/Nenhuma)"] = exigencia
                                            time.sleep(1)
                                
                                # Adicionar resultados
                                todos_resultados.extend(resultados_pagina)
                                
                                # Salvar de forma incremental
                                self.salvar_resultados_incrementais(resultados_pagina)
                            
                            # Obter URL da próxima página
                            proxima_pagina_url = self.obter_url_proxima_pagina(html_content)
                        else:
                            logger.error(f"Erro ao acessar página {pagina_atual}: {response.status_code}")
                            break
                    except Exception as e:
                        logger.error(f"Erro ao processar página {pagina_atual}: {str(e)}")
                        break
                    
                    time.sleep(2)  # Pausa entre páginas
                
                logger.info(f"Concluído processamento de {pagina_atual} página(s) para Ano={ano}, Classe={classe}")
                
                # Pausa entre consultas
                time.sleep(5)
        
        # Salvar todos os resultados no final
        self.salvar_resultados(todos_resultados)
        logger.info(f"Coleta concluída. Total de {len(todos_resultados)} registros coletados.")
        
        return todos_resultados

if __name__ == "__main__":
    # Configurações de coleta
    ANOS = range(2015, 2025)  # 2015 a 2024
    CLASSES = ["5", "6"]      # Classes 5 e 6
    MAX_PAGINAS = 100         # Limite máximo de páginas por consulta
    ANALISAR_PROCESSOS = True # Definir como False para coletar mais rápido sem analisar exigências
    
    logger.info("=" * 50)
    logger.info("INICIANDO COLETA OTIMIZADA DE LICENÇAS AMBIENTAIS")
    logger.info("=" * 50)
    
    coletor = ColetorOtimizado()
    resultados = coletor.coletar_dados(
        anos=ANOS,
        classes=CLASSES,
        max_paginas_por_consulta=MAX_PAGINAS,
        analisar_processos=ANALISAR_PROCESSOS
    )
    
    logger.info("=" * 50)
    logger.info(f"COLETA FINALIZADA: {len(resultados)} REGISTROS")
    logger.info("=" * 50) 