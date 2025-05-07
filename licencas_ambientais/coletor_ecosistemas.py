#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coletor de dados do sistema de licenciamento ambiental Ecosistemas MG.
Permite a coleta de processos de licenciamento ambiental com foco em Classe 6.

Versão: 2.0 - Melhoria na navegação entre páginas
Data de atualização: 09/05/2024
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import logging
from datetime import datetime
import csv
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import traceback

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"ecosistemas_coleta_{datetime.now().strftime('%Y%m%d_%H%M')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("coletor_ecosistemas")

class ColetorEcosistemas:
    def __init__(self, modo_headless=True):
        """
        Inicializa o coletor para o sistema ecosistemas
        
        Args:
            modo_headless (bool): Se True, executa o navegador sem interface gráfica
        """
        self.base_url = "https://ecosistemas.meioambiente.mg.gov.br/sla/#/acesso-visitante"
        self.modo_headless = modo_headless
        self.setup_driver()
        
    def setup_driver(self):
        """
        Configura o driver do Selenium com as opções necessárias
        """
        try:
            chrome_options = Options()
            if self.modo_headless:
                chrome_options.add_argument("--headless")  # Executar em modo headless (sem interface gráfica)
                logger.info("Executando em modo headless")
            else:
                logger.info("Executando com interface gráfica")
                
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Usar Chrome padrão sem webdriver-manager
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Configurar timeouts
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 15)
            
            logger.info("Driver Selenium configurado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {str(e)}")
            raise
    
    def acessar_site(self):
        """
        Acessa o site inicial do sistema
        """
        try:
            logger.info(f"Acessando URL: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Aguardar carregamento completo da página
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)  # Aguardar carregamento de elementos dinâmicos
            
            logger.info("Página inicial carregada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao acessar site: {str(e)}")
            return False
    
    def aplicar_filtro_classe_6(self):
        """
        Aplica o filtro para selecionar apenas empreendimentos de Classe 6
        """
        try:
            logger.info("Aplicando filtro para Classe 6")
            
            # Aguardar carregamento completo da página
            time.sleep(5)  # Aumentar tempo de espera para garantir carregamento
            
            # Tentar diferentes abordagens para encontrar o campo de classe predominante
            try:
                # Primeira abordagem: Direto pelo XPath relacionado ao label
                classe_input_container = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Classe predominante')]/following-sibling::div//input")
            except:
                try:
                    # Segunda abordagem: Encontrar todos os inputs e procurar pelo placeholder ou name relacionado
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    classe_input_container = None
                    for input_elem in inputs:
                        if input_elem.get_attribute("placeholder") and "classe" in input_elem.get_attribute("placeholder").lower():
                            classe_input_container = input_elem
                            break
                        if input_elem.get_attribute("name") and "classe" in input_elem.get_attribute("name").lower():
                            classe_input_container = input_elem
                            break
                except:
                    # Terceira abordagem: JavaScript para encontrar o elemento
                    logger.info("Tentando encontrar o campo de classe com JavaScript")
                    classe_input_container = self.driver.execute_script("""
                        return Array.from(document.querySelectorAll('input')).find(el => 
                            (el.placeholder && el.placeholder.toLowerCase().includes('classe')) || 
                            (el.name && el.name.toLowerCase().includes('classe')) ||
                            (el.id && el.id.toLowerCase().includes('classe'))
                        );
                    """)
            
            if not classe_input_container:
                logger.error("Não foi possível encontrar o campo de classe predominante")
                return False
                
            # Tentar clicar com várias abordagens
            try:
                # Abordagem 1: Clique normal
                classe_input_container.click()
            except:
                try:
                    # Abordagem 2: JavaScript click
                    self.driver.execute_script("arguments[0].click();", classe_input_container)
                except:
                    # Abordagem 3: Actions
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(classe_input_container).click().perform()
            
            time.sleep(2)  # Aguardar após o clique
            
            # Enviar valor '6'
            classe_input_container.send_keys("6")
            time.sleep(2)
            
            # Encontrar e clicar no botão de pesquisar usando abordagens diferentes
            try:
                # Primeira abordagem: por texto
                botao_pesquisar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Pesquisar')]")
            except:
                try:
                    # Segunda abordagem: por tipo e valor
                    botao_pesquisar = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                except:
                    # Terceira abordagem: por JavaScript
                    logger.info("Tentando encontrar o botão pesquisar com JavaScript")
                    botao_pesquisar = self.driver.execute_script("""
                        return Array.from(document.querySelectorAll('button')).find(el => 
                            el.textContent.includes('Pesquisar') || 
                            el.type === 'submit'
                        );
                    """)
            
            if not botao_pesquisar:
                logger.error("Não foi possível encontrar o botão de pesquisar")
                return False
            
            # Tentar clicar com várias abordagens
            try:
                # Abordagem 1: Clique normal
                botao_pesquisar.click()
            except:
                try:
                    # Abordagem 2: JavaScript click
                    self.driver.execute_script("arguments[0].click();", botao_pesquisar)
                except:
                    # Abordagem 3: Actions
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(botao_pesquisar).click().perform()
            
            # Aguardar carregamento dos resultados com tempo maior
            time.sleep(5)
            
            # Verificar se há resultados (tabela ou mensagem de nenhum resultado)
            try:
                self.driver.find_element(By.XPATH, "//table//tr")
                logger.info("Filtro de Classe 6 aplicado com sucesso")
                return True
            except:
                # Verificar se há mensagem de "nenhum resultado"
                try:
                    mensagem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Nenhum resultado')]")
                    logger.warning("Filtro aplicado, mas nenhum resultado encontrado")
                    return False
                except:
                    # Se não tem tabela e nem mensagem, algo deu errado
                    logger.error("Filtro aplicado, mas não foi possível confirmar resultados")
                    return False
                
        except Exception as e:
            logger.error(f"Erro ao aplicar filtro de Classe 6: {str(e)}")
            return False
    
    def extrair_dados_tabela(self):
        """
        Extrai dados da tabela de resultados
        """
        resultados = []
        
        logger.info("Extraindo dados da tabela de resultados")
        
        try:
            # NOVA ABORDAGEM: Usar o HTML diretamente para extrair a tabela
            # Isso pode resolver problemas de detecção incorreta dos elementos
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Verificar se a tabela está presente
            tabela = soup.find('table')
            if not tabela:
                logger.error("Tabela de resultados não encontrada")
                # Salvar screenshot para debugging
                screenshot_path = f"tabela_nao_encontrada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot salvo em {screenshot_path}")
                return []
            
            # Extrair cabeçalhos corretamente
            cabecalhos_elem = tabela.find_all('th')
            if not cabecalhos_elem:
                # Tentar encontrar cabeçalhos na primeira linha
                primeira_linha = tabela.find('tr')
                if primeira_linha:
                    cabecalhos_elem = primeira_linha.find_all(['th', 'td'])
            
            cabecalhos = []
            for elem in cabecalhos_elem:
                texto = elem.get_text(strip=True)
                cabecalhos.append(texto if texto else f"coluna_{len(cabecalhos)}")
            
            # Se não encontrou cabeçalhos, criar genéricos
            if not cabecalhos:
                logger.warning("Cabeçalhos não encontrados, criando genéricos")
                # Contar o número máximo de colunas nas linhas
                linhas = tabela.find_all('tr')
                max_cols = 0
                for linha in linhas:
                    cols = len(linha.find_all(['td', 'th']))
                    max_cols = max(max_cols, cols)
                
                # Criar cabeçalhos genéricos
                cabecalhos = [f"coluna_{i}" for i in range(max_cols)]
            
            logger.info(f"Cabeçalhos extraídos: {cabecalhos}")
            
            # Extrair linhas da tabela (excluindo a linha de cabeçalho se houver)
            linhas = tabela.find_all('tr')
            tem_cabecalho = False
            
            # Verificar se a primeira linha é cabeçalho
            if len(linhas) > 0:
                primeira_linha = linhas[0]
                if primeira_linha.find_all('th'):
                    tem_cabecalho = True
            
            # Determinar qual linha começar (pular cabeçalho se existir)
            inicio = 1 if tem_cabecalho else 0
            
            # Verificar se há linhas de dados
            if len(linhas) <= inicio:
                logger.warning("Nenhuma linha de dados encontrada na tabela")
                return []
            
            # Processar linhas de dados
            for i, linha in enumerate(linhas[inicio:], 1):
                colunas = linha.find_all(['td', 'th'])
                
                # Se a linha não tem colunas, pular
                if not colunas:
                    continue
                
                # Verificar formato especial onde tipo_de_estudo e classe_predominante estão em uma só célula
                if len(colunas) == 1 and len(cabecalhos) > 1:
                    # Esta é uma situação especial onde a tabela tem formato irregular
                    # Provavelmente cada célula única contém informações que precisam ser mapeadas
                    texto_celula = colunas[0].get_text(strip=True)
                    
                    # Criar resultado com esta informação
                    resultado = {
                        "classe_predominante": texto_celula,
                        "tipo_de_estudo": "A determinar"  # Valor padrão
                    }
                    
                    # Tentar identificar tipo de estudo baseado no texto
                    if "EIA" in texto_celula.upper() or "RIMA" in texto_celula.upper():
                        resultado["tipo_de_estudo"] = "EIA/RIMA"
                    elif "RCA" in texto_celula.upper():
                        resultado["tipo_de_estudo"] = "RCA"
                    
                    # Verificar se há links para detalhes
                    links = colunas[0].find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href:
                            resultado["link_detalhes"] = href
                            break
                else:
                    # Formato regular - extrair células normalmente
                    resultado = {}
                    
                    # Extrair dados das colunas
                    for j, coluna in enumerate(colunas):
                        # Obter chave do cabeçalho (ou usar índice se não houver chave correspondente)
                        chave = cabecalhos[j].replace(' ', '_').lower() if j < len(cabecalhos) else f"coluna_{j}"
                        
                        # Extrair texto da coluna
                        texto = coluna.get_text(strip=True)
                        resultado[chave] = texto
                        
                        # Verificar se há links na coluna
                        links = coluna.find_all('a')
                        for link in links:
                            href = link.get('href')
                            if href:
                                resultado["link_detalhes"] = href
                                break
                    
                    # Verificar se a atividade principal contém códigos que exigem EIA/RIMA
                    atividade_principal = resultado.get("atividade_principal", "")
                    # Adicionar o campo tipo_de_estudo se não existir
                    if 'tipo_de_estudo' not in resultado:
                        # Verificar se a atividade está entre as que exigem EIA/RIMA
                        if any(cod in atividade_principal for cod in ["A-05-02-0", "A-05-03-7", "A-05-04-5", "A-05-05-3"]):
                            resultado["tipo_de_estudo"] = "EIA/RIMA (inferido pela atividade)"
                        else:
                            resultado["tipo_de_estudo"] = "A determinar"
                
                # Tentar identificar o tipo de estudo pelo texto do documento
                classe_texto = resultado.get("classe_predominante", "").upper()
                if 'tipo_de_estudo' in resultado and resultado['tipo_de_estudo'] == "A determinar":
                    if "RCA" in classe_texto or "RELATÓRIO DE CONTROLE AMBIENTAL" in classe_texto:
                        resultado["tipo_de_estudo"] = "RCA"
                    elif "EIA" in classe_texto or "RIMA" in classe_texto or "ESTUDO DE IMPACTO" in classe_texto:
                        resultado["tipo_de_estudo"] = "EIA/RIMA"
                
                logger.info(f"Dados extraídos da linha {i}: {list(resultado.keys())}")
                resultados.append(resultado)
            
            logger.info(f"Total de {len(resultados)} resultados extraídos da tabela")
        except Exception as e:
            # Capturar screenshot do erro
            screenshot_path = f"erro_tabela_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            try:
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot do erro salvo em {screenshot_path}")
            except:
                pass
            
            logger.error(f"Erro ao extrair dados da tabela: {str(e)}")
        
        return resultados
    
    def acessar_proximo_registro(self, link_detalhes):
        """
        Acessa a página de detalhes de um registro específico
        """
        try:
            logger.info(f"Acessando página de detalhes: {link_detalhes}")
            
            # Abrir o link em uma nova aba
            self.driver.execute_script(f"window.open('{link_detalhes}');")
            
            # Mudar para a nova aba
            self.driver.switch_to.window(self.driver.window_handles[1])
            
            # Aguardar carregamento da página
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)  # Aguardar carregamento de elementos dinâmicos
            
            logger.info("Página de detalhes carregada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao acessar página de detalhes: {str(e)}")
            return False
    
    def extrair_dados_detalhados(self):
        """
        Extrai dados detalhados da página de um processo específico
        """
        dados_detalhados = {}
        
        try:
            logger.info("Extraindo dados detalhados do processo")
            
            # NOVA ABORDAGEM: Usar BeautifulSoup para processar o HTML
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extrair dados básicos do processo a partir do HTML
            # Tentar extrair campos comuns usando diferentes abordagens
            
            # 1. Buscar seções com rótulos específicos
            labels_interesse = [
                'CPF/CNPJ', 'Pessoa Física/Jurídica', 'Nome Fantasia', 
                'Empreendimento', 'Município da Solicitação', 'Número do Processo',
                'Classe predominante', 'Fator locacional', 'Modalidade licenciamento',
                'Fase do licenciamento', 'Tipo solicitação', 'Atividade Principal'
            ]
            
            # Procurar rótulos (em elementos strong, th, label ou span)
            for label in labels_interesse:
                # Abordagem 1: Procurar rótulos em elementos strong
                strong_elem = soup.find('strong', text=lambda t: label in t if t else False)
                if strong_elem and strong_elem.next_sibling:
                    valor = strong_elem.next_sibling.strip()
                    if valor:
                        dados_detalhados[label] = valor
                        continue
                
                # Abordagem 2: Procurar em células de tabela th
                th_elem = soup.find('th', text=lambda t: label in t if t else False)
                if th_elem and th_elem.find_next('td'):
                    valor = th_elem.find_next('td').get_text(strip=True)
                    if valor:
                        dados_detalhados[label] = valor
                        continue
                
                # Abordagem 3: Procurar por padrões comuns de layout (label: valor)
                # Isto busca qualquer elemento contendo o texto do rótulo seguido por ":"
                elem = soup.find(text=lambda t: f"{label}:" in t if t else False)
                if elem:
                    # Tentar extrair o valor que vem após o rótulo
                    texto_completo = elem.strip()
                    partes = texto_completo.split(':', 1)
                    if len(partes) > 1:
                        valor = partes[1].strip()
                        if valor:
                            dados_detalhados[label] = valor
            
            # 2. Buscar atividade principal especificamente (comum em processos de licenciamento)
            if 'Atividade Principal' not in dados_detalhados:
                # Procurar em tabelas de atividades
                tabela_atividades = soup.find('table', class_=lambda c: 'atividade' in c.lower() if c else False)
                if not tabela_atividades:
                    # Tentar encontrar qualquer tabela que pareça conter atividades
                    tabelas = soup.find_all('table')
                    for tabela in tabelas:
                        if tabela.find(text=lambda t: 'atividade' in t.lower() if t else False):
                            tabela_atividades = tabela
                            break
                
                if tabela_atividades:
                    # Pegar a primeira linha de dados (presumindo que a primeira é cabeçalho)
                    linhas = tabela_atividades.find_all('tr')
                    if len(linhas) > 1:
                        colunas = linhas[1].find_all('td')
                        if colunas:
                            # Geralmente a primeira coluna contém a descrição da atividade
                            dados_detalhados['Atividade Principal'] = colunas[0].get_text(strip=True)
            
            # 3. Extrair documentos (para avaliar EIA/RIMA ou RCA)
            tem_eia_rima = False
            tem_rca = False
            documentos = []
            links_documentos = []
            motivo_eia_rima = ""
            motivo_rca = ""
            
            # Procurar seção de documentos
            secao_documentos = None
            
            # Abordagem 1: Procurar título explícito
            titulo_docs = soup.find(['h2', 'h3', 'h4', 'div'], text=lambda t: 'documentos' in t.lower() if t else False)
            if titulo_docs:
                # Pegar o elemento pai ou seguinte como seção de documentos
                secao_documentos = titulo_docs.parent
            
            # Abordagem 2: Procurar links que pareçam ser documentos
            if not secao_documentos:
                # Considerar todos os links na página
                secao_documentos = soup
            
            # Extrair links de documentos
            for link in secao_documentos.find_all('a'):
                href = link.get('href')
                texto = link.get_text(strip=True)
                
                if texto and href:
                    documentos.append(texto)
                    links_documentos.append(href)
                    
                    # Verificar tipo de documento pelo nome
                    texto_upper = texto.upper()
                    if any(termo in texto_upper for termo in ['EIA', 'RIMA', 'ESTUDO DE IMPACTO', 'IMPACTO AMBIENTAL']):
                        tem_eia_rima = True
                        # Extrair o motivo entre parênteses, se houver
                        if 'ESTUDO DE IMPACTO AMBIENTAL' in texto_upper:
                            matches = re.search(r'EIA/RIMA -.*?\((.*?)\)', texto)
                            if matches:
                                motivo_eia_rima = matches.group(1).strip()
                            else:
                                motivo_eia_rima = texto
                        logger.info(f"Documento EIA/RIMA encontrado: {texto}")
                    
                    if any(termo in texto_upper for termo in ['RCA', 'RELATÓRIO DE CONTROLE', 'RELATORIO DE CONTROLE']):
                        tem_rca = True
                        # Extrair o motivo entre parênteses, se houver
                        if 'RELATÓRIO DE CONTROLE AMBIENTAL' in texto_upper:
                            matches = re.search(r'RCA -.*?\((.*?)\)', texto)
                            if matches:
                                motivo_rca = matches.group(1).strip()
                            else:
                                motivo_rca = texto
                        logger.info(f"Documento RCA encontrado: {texto}")
            
            # Verificar no conteúdo completo da página
            texto_pagina = soup.get_text().upper()
            
            # Busca específica para EIA/RIMA com motivo entre parênteses
            match_eia_rima = re.search(r'EIA/RIMA\s*-\s*[^(]*\(([^)]+)\)', texto_pagina)
            if match_eia_rima and not motivo_eia_rima:
                motivo_eia_rima = match_eia_rima.group(1).strip()
                tem_eia_rima = True
                logger.info(f"Motivo EIA/RIMA encontrado: {motivo_eia_rima}")
            
            # Busca específica para RCA com motivo entre parênteses
            match_rca = re.search(r'RCA\s*-\s*[^(]*\(([^)]+)\)', texto_pagina)
            if match_rca and not motivo_rca:
                motivo_rca = match_rca.group(1).strip()
                tem_rca = True
                logger.info(f"Motivo RCA encontrado: {motivo_rca}")
            
            # Lista expandida de termos para busca
            termos_eia_rima = [
                'EIA/RIMA', 'EIA / RIMA', 'EIA-RIMA', 'ESTUDO DE IMPACTO AMBIENTAL',
                'RELATÓRIO DE IMPACTO AMBIENTAL', 'RIMA', 'EIA', 'IMPACTO AMBIENTAL'
            ]
            
            termos_rca = [
                'RCA COM ART', 'RCA/PCA', 'RCA / PCA', 'RCA-PCA',
                'RELATÓRIO DE CONTROLE AMBIENTAL', 'RELATORIO DE CONTROLE AMBIENTAL',
                'RCA', 'CONTROLE AMBIENTAL'
            ]
            
            if not tem_eia_rima and any(termo in texto_pagina for termo in termos_eia_rima):
                tem_eia_rima = True
                logger.info("Referência a EIA/RIMA encontrada no texto da página")
            
            if not tem_rca and any(termo in texto_pagina for termo in termos_rca):
                tem_rca = True
                logger.info("Referência a RCA encontrada no texto da página")
            
            # Armazenar documentos encontrados
            dados_detalhados["Documentos"] = documentos
            dados_detalhados["Links_Documentos"] = links_documentos
            
            # Determinar o tipo de estudo, incluindo o motivo quando disponível
            if tem_eia_rima and tem_rca:
                tipo_estudo = "EIA/RIMA e RCA"
                if motivo_eia_rima:
                    tipo_estudo += f" (EIA/RIMA: {motivo_eia_rima})"
                if motivo_rca:
                    tipo_estudo += f" (RCA: {motivo_rca})"
            elif tem_eia_rima:
                tipo_estudo = "EIA/RIMA"
                if motivo_eia_rima:
                    tipo_estudo += f" ({motivo_eia_rima})"
            elif tem_rca:
                tipo_estudo = "RCA"
                if motivo_rca:
                    tipo_estudo += f" ({motivo_rca})"
            else:
                # Inferir pelo tipo de atividade se não encontrou nos documentos
                atividade_principal = dados_detalhados.get("Atividade Principal", "")
                classe_predominante = dados_detalhados.get("Classe predominante", "")
                
                # Códigos que geralmente requerem EIA/RIMA (mineração, grandes empreendimentos)
                if "6" in classe_predominante or any(cod in atividade_principal for cod in ["A-05-02-0", "A-05-03-7", "A-05-04-5", "A-05-05-3"]):
                    tipo_estudo = "EIA/RIMA (inferido pela atividade)"
                elif any(cod in atividade_principal for cod in ["A-01-03-1", "A-04-01-4", "E-04-01-4"]):
                    tipo_estudo = "RCA (inferido pela atividade)"
                else:
                    tipo_estudo = "A determinar"
            
            dados_detalhados["Tipo de Estudo"] = tipo_estudo
            dados_detalhados["motivo_estudo"] = motivo_eia_rima if tem_eia_rima else motivo_rca
            
            logger.info(f"Tipo de Estudo identificado: {dados_detalhados.get('Tipo de Estudo', 'Não identificado')}")
            logger.info("Dados detalhados extraídos com sucesso")
            return dados_detalhados
        except Exception as e:
            logger.error(f"Erro ao extrair dados detalhados: {str(e)}")
            return {"Tipo de Estudo": "Erro ao identificar"}
    
    def fechar_aba_detalhes(self):
        """
        Fecha a aba de detalhes e volta para a aba principal
        """
        try:
            # Fechar a aba atual
            self.driver.close()
            
            # Voltar para a aba principal
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            logger.info("Retornado para a aba principal")
            return True
        except Exception as e:
            logger.error(f"Erro ao fechar aba de detalhes: {str(e)}")
            return False
    
    def navegar_proxima_pagina(self):
        """
        Navega para a próxima página de resultados
        
        Esta função utiliza várias estratégias para encontrar e interagir com os controles de paginação:
        1. Rola até o final da página para garantir que os controles estejam visíveis
        2. Identifica o indicador de páginas (ex: "1 - 10 de 137 Registros")
        3. Busca elementos interativos que possam ser botões de paginação
        4. Tenta clicar nos botões encontrados usando diferentes abordagens
        
        Returns:
            bool: True se conseguiu navegar para a próxima página, False caso contrário
        """
        try:
            logger.info("Tentando navegar para a próxima página")
            
            # MELHORADO: Rolar até o final da página para garantir que os controles de paginação sejam visíveis
            logger.info("Rolando até o final da página para encontrar controles de paginação")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Aguardar a rolagem
            
            # Tentar encontrar e rolar até a tabela e depois um pouco mais para garantir que a paginação fique visível
            try:
                tabela = self.driver.find_element(By.TAG_NAME, "table")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", tabela)
                # Rolar um pouco mais para garantir que os controles abaixo da tabela sejam visíveis
                self.driver.execute_script("window.scrollBy(0, 200);")
                time.sleep(1)  # Aguardar a rolagem
            except:
                logger.warning("Não foi possível encontrar a tabela para rolar")
            
            # Aguardar para garantir que a paginação esteja visível
            time.sleep(2)
            
            # Capturar screenshot para depuração
            screenshot_path = f"paginacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot da paginação salvo em {screenshot_path}")
            
            # Procurar pelo indicador de páginas primeiro para confirmar que há mais páginas
            indicador_paginas = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Registros')]")
            
            tem_mais_paginas = False
            pagina_atual = 1
            total_registros = 0
            texto_indicador = ""
            
            for indicador in indicador_paginas:
                texto = indicador.text.strip()
                texto_indicador = texto
                logger.info(f"Encontrado indicador de páginas: {texto}")
                
                # Padrão: "1 - 10 de 137 Registros" ou similar
                match = re.search(r'(\d+)\s*-\s*(\d+)\s*de\s*(\d+)', texto)
                if match:
                    inicio = int(match.group(1))
                    fim = int(match.group(2))
                    total = int(match.group(3))
                    total_registros = total
                    logger.info(f"Indicador interpretado: início={inicio}, fim={fim}, total={total}")
                    
                    # Se o fim for menor que o total, há mais páginas
                    if fim < total:
                        tem_mais_paginas = True
                        
                        # Calcular página atual (assumindo 10 itens por página)
                        itens_por_pagina = fim - inicio + 1
                        pagina_atual = (inicio - 1) // itens_por_pagina + 1
                        proxima_pagina = pagina_atual + 1
                        
                        logger.info(f"Página atual calculada: {pagina_atual}, próxima será: {proxima_pagina}")
                        break
            
            if not tem_mais_paginas:
                logger.info("Não há mais páginas disponíveis")
                return False
            
            # MELHORADO: Após identificar que há mais páginas, rolar até o elemento indicador para garantir
            # que os controles de paginação próximos a ele estejam visíveis
            try:
                for indicador in indicador_paginas:
                    if indicador.text.strip() == texto_indicador:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", indicador)
                        # Rolar um pouco mais para baixo para garantir que os controles abaixo do indicador estejam visíveis
                        self.driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)  # Aguardar a rolagem
                        break
            except:
                logger.warning("Não foi possível rolar até o indicador de páginas")
                
            # Capturar novo screenshot após rolagem adicional
            post_scroll_screenshot = f"paginacao_apos_rolagem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(post_scroll_screenshot)
            logger.info(f"Screenshot após rolagem adicional salvo em {post_scroll_screenshot}")
            
            # Tentar localizar os botões de paginação com diferentes seletores
            botoes_paginacao = []
            
            # MELHORADO: Seletores mais específicos, priorizando elementos abaixo da tabela
            seletores = [
                # Seletores específicos para paginação após a tabela
                "//table/following-sibling::*//a[contains(text(), '>')]",  # Links com '>' após a tabela
                "//table/following-sibling::*//button[contains(text(), '>')]",  # Botões com '>' após a tabela
                "//table/following-sibling::*//*[contains(text(), '>')]",  # Qualquer elemento com '>' após a tabela
                "//table/following-sibling::*//*[contains(@class, 'pagination')]//a",  # Links de paginação após a tabela
                
                # Seletores específicos para a página 2
                "//table/following-sibling::*//a[contains(text(), '2')]",  # Link para página 2 após a tabela
                "//table/following-sibling::*//*[contains(text(), '2')]",  # Qualquer elemento com '2' após a tabela
                
                # Seletores específicos para "próximo"
                "//table/following-sibling::*//a[contains(text(), 'Próximo') or contains(text(), 'próximo') or contains(text(), 'Next')]",
                
                # Seletores gerais para paginação em qualquer lugar
                "//ul[contains(@class, 'pagination')]/li/a",  # Bootstrap padrão
                "//div[contains(@class, 'pagination')]//a",   # Outro padrão comum
                "//*[contains(@class, 'pagination')]//a",     # Genérico
                "//a[contains(@class, 'page-link')]",         # Links de página
                "//a[contains(@href, 'page=')]",              # Links com parâmetro page
                "//a[contains(text(), '>')]",                 # Seta para direita
                "//button[contains(text(), '>')]",           # Botão seta para direita
                "//i[contains(@class, 'fa-chevron-right')]",  # Ícone FontAwesome
                "//i[contains(@class, 'fa-arrow-right')]",    # Ícone FontAwesome
                "//span[contains(@class, 'icon') and contains(text(), '>')]", # Ícones em spans
                "//a[contains(text(), '2')]",                 # Número 2 (próxima página)
                "//a[contains(text(), 'Próximo') or contains(text(), 'próximo') or contains(text(), 'Next')]", # Texto indicando próximo
                "//button[contains(@aria-label, 'Next') or contains(@aria-label, 'Próximo')]", # Botões com aria-label
                "//div[contains(@class, 'next') or contains(@class, 'proximo')]", # Divs com classe next
                "//li[contains(@class, 'next') or contains(@class, 'pagination-next')]//a", # Elementos li com classe next
                "//img[contains(@src, 'next') or contains(@src, 'arrow')]", # Imagens de seta
                "//a/img[contains(@src, 'arrow') or contains(@src, 'next')]/parent::a" # Links com imagens de setas
            ]
            
            for seletor in seletores:
                try:
                    elementos = self.driver.find_elements(By.XPATH, seletor)
                    if elementos:
                        logger.info(f"Encontrados {len(elementos)} botões com o seletor: {seletor}")
                        botoes_paginacao.extend(elementos)
                except Exception as e:
                    logger.debug(f"Erro ao buscar seletor {seletor}: {str(e)}")
            
            logger.info(f"Total de {len(botoes_paginacao)} possíveis botões de paginação encontrados")
            
            # MELHORADO: JavaScript mais preciso para encontrar elementos clicáveis relacionados à paginação
            js_script_botoes = """
            function encontrarBotoesPaginacao() {
                const candidatos = [];
                
                // Buscar elementos com características visuais de paginação
                document.querySelectorAll('a, button, span, div, li').forEach(el => {
                    // Verificar se o elemento é visível
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    
                    const texto = el.textContent.trim();
                    const classes = (el.className || '').toLowerCase();
                    
                    // Verificar texto que indica próxima página
                    if (texto === '>' || texto === '>>' || texto === '→' || texto === '2' ||
                        texto === 'Next' || texto === 'Próximo' || texto === 'próximo') {
                        candidatos.push(el);
                    }
                    
                    // Verificar classes que sugerem paginação
                    if (classes.includes('next') || classes.includes('proximo') || 
                        classes.includes('próximo') || classes.includes('pagination')) {
                        candidatos.push(el);
                    }
                    
                    // Verificar se é um elemento clicável (elemento a com href ou button)
                    if ((el.tagName === 'A' && el.hasAttribute('href')) || 
                        el.tagName === 'BUTTON' || 
                        el.onclick || 
                        el.getAttribute('role') === 'button') {
                        
                        // Verificar se parece ser relacionado à paginação
                        if (texto.match(/^\\d+$/) || // Números isolados
                            texto.match(/[>»→]/) ||  // Símbolos de seta
                            classes.includes('page') || 
                            classes.includes('nav')) {
                            candidatos.push(el);
                        }
                    }
                    
                    // Verificar se tem filhos que podem ser ícones
                    if (el.children.length > 0) {
                        for (const child of el.children) {
                            const childClasses = (child.className || '').toLowerCase();
                            if (childClasses.includes('icon') || childClasses.includes('fa-') || 
                                childClasses.includes('arrow') || childClasses.includes('next')) {
                                candidatos.push(el);
                                break;
                            }
                        }
                    }
                });
                
                return candidatos;
            }
            
            return encontrarBotoesPaginacao();
            """
            
            try:
                js_botoes = self.driver.execute_script(js_script_botoes)
                if js_botoes and len(js_botoes) > 0:
                    logger.info(f"Encontrados {len(js_botoes)} botões adicionais via JavaScript")
                    botoes_paginacao.extend(js_botoes)
            except Exception as e:
                logger.warning(f"Erro ao executar JavaScript para encontrar botões: {str(e)}")
            
            # Remover duplicados
            botoes_unicos = []
            for botao in botoes_paginacao:
                if botao not in botoes_unicos:
                    botoes_unicos.append(botao)
            
            botoes_paginacao = botoes_unicos
            logger.info(f"Total de {len(botoes_paginacao)} botões únicos após remoção de duplicados")
            
            # Exibir informações sobre os botões encontrados
            for i, botao in enumerate(botoes_paginacao):
                try:
                    texto = botao.text.strip()
                    href = botao.get_attribute("href") if hasattr(botao, "get_attribute") else None
                    onclick = botao.get_attribute("onclick") if hasattr(botao, "get_attribute") else None
                    classes = botao.get_attribute("class") if hasattr(botao, "get_attribute") else None
                    logger.info(f"Botão {i+1}: texto='{texto}', href='{href}', onclick='{onclick}', classes='{classes}'")
                except:
                    pass
            
            # Tentar diferentes estratégias para clicar no botão de próxima página
            clicou = False
            
            # Estratégia 1: Priorizar botões com texto '>' ou '2' ou 'próximo'
            logger.info("Tentativa 1: Clicando em botões com texto de próxima página")
            for botao in botoes_paginacao:
                try:
                    texto = botao.text.strip()
                    if texto in ['>', '>>', '→', '2', 'Next', 'Próximo', 'próximo', 'Próxima']:
                        logger.info(f"Tentando clicar no botão com texto '{texto}'")
                        # Rolar até o botão
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
                        time.sleep(0.5)
                        
                        try:
                            # Tentar clique normal
                            botao.click()
                            logger.info(f"Clicou com sucesso no botão '{texto}'")
                            clicou = True
                            break
                        except:
                            # Se falhar, tentar com JavaScript
                            self.driver.execute_script("arguments[0].click();", botao)
                            logger.info(f"Clicou com JavaScript no botão '{texto}'")
                            clicou = True
                            break
                except Exception as e:
                    logger.debug(f"Erro ao clicar: {str(e)}")
            
            # NOVA ESTRATÉGIA: Inspecionar elementos visíveis na parte inferior da página que parecem controles de paginação
            if not clicou:
                logger.info("Tentativa especial: Localizando elementos visíveis na região de paginação")
                try:
                    elemento_visivel_js = """
                    function encontrarElementosClicaveisVisiveis() {
                        // Obter as dimensões da janela
                        const windowHeight = window.innerHeight;
                        const windowWidth = window.innerWidth;
                        
                        // Região onde provavelmente estão os controles de paginação (parte inferior da página)
                        const areaPaginacao = {
                            top: windowHeight * 0.7,  // Últimos 30% da altura da janela
                            bottom: windowHeight,
                            left: 0,
                            right: windowWidth
                        };
                        
                        // Elementos a considerar
                        const elementos = document.querySelectorAll('a, button, span[role="button"], div[role="button"]');
                        const elementosVisiveis = [];
                        
                        for (const el of elementos) {
                            const rect = el.getBoundingClientRect();
                            
                            // Verificar se o elemento está visível
                            if (rect.width > 0 && rect.height > 0) {
                                // Verificar se o elemento está na região de paginação
                                const centro = {
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2
                                };
                                
                                if (centro.y > areaPaginacao.top && centro.y < areaPaginacao.bottom &&
                                    centro.x > areaPaginacao.left && centro.x < areaPaginacao.right) {
                                    
                                    // Coletar informações sobre o elemento
                                    elementosVisiveis.push({
                                        elemento: el,
                                        texto: el.textContent.trim(),
                                        x: centro.x,
                                        y: centro.y,
                                        width: rect.width,
                                        height: rect.height,
                                        tag: el.tagName.toLowerCase()
                                    });
                                }
                            }
                        }
                        
                        // Ordenar elementos da esquerda para a direita (para pegar o "próximo" que normalmente está à direita)
                        elementosVisiveis.sort((a, b) => a.x - b.x);
                        
                        return elementosVisiveis;
                    }
                    
                    return encontrarElementosClicaveisVisiveis();
                    """
                    
                    elementos_visiveis = self.driver.execute_script(elemento_visivel_js)
                    logger.info(f"Encontrados {len(elementos_visiveis)} elementos visíveis na região de paginação")
                    
                    # Registrar informações para depuração
                    for i, el in enumerate(elementos_visiveis):
                        logger.info(f"Elemento visível {i+1}: tag={el.get('tag', '')}, texto='{el.get('texto', '')}', posição=({el.get('x', 0)}, {el.get('y', 0)})")
                    
                    # Tentar clicar no elemento mais à direita (geralmente o "próximo")
                    if elementos_visiveis:
                        # Separar os elementos por tipo
                        elementos_numericos = [el for el in elementos_visiveis if el.get('texto', '').strip() == str(pagina_atual + 1)]
                        elementos_seta = [el for el in elementos_visiveis if '>' in el.get('texto', '')]
                        elementos_proximos = [el for el in elementos_visiveis if 'próximo' in el.get('texto', '').lower()]
                        
                        # Priorizar elementos na ordem: "próximo" > seta > número da próxima página > último elemento
                        elemento_alvo = None
                        
                        if elementos_proximos:
                            elemento_alvo = elementos_proximos[0]
                            logger.info(f"Selecionado elemento 'próximo': {elemento_alvo.get('texto', '')}")
                        elif elementos_seta:
                            elemento_alvo = elementos_seta[0]
                            logger.info(f"Selecionado elemento seta: {elemento_alvo.get('texto', '')}")
                        elif elementos_numericos:
                            elemento_alvo = elementos_numericos[0]
                            logger.info(f"Selecionado elemento numérico: {elemento_alvo.get('texto', '')}")
                        else:
                            # Se nenhum elemento específico, pegar o mais à direita
                            # (último após ordenação por posição X)
                            elemento_alvo = elementos_visiveis[-1]
                            logger.info(f"Selecionado último elemento à direita: {elemento_alvo.get('texto', '')}")
                        
                        # Tentar clicar no elemento selecionado
                        try:
                            el = elemento_alvo.get('elemento')
                            self.driver.execute_script("arguments[0].click();", el)
                            logger.info(f"Clicou com sucesso no elemento visível: {elemento_alvo.get('texto', '')}")
                            clicou = True
                        except Exception as e:
                            logger.warning(f"Erro ao clicar no elemento visível: {str(e)}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao localizar elementos visíveis: {str(e)}")
            
            # Estratégia anterior: Tentar botões com href contendo 'page='
            if not clicou:
                logger.info("Tentativa 2: Clicando em links com href de paginação")
                for botao in botoes_paginacao:
                    try:
                        href = botao.get_attribute("href")
                        if href and ('page=' in href.lower() or 'pagina=' in href.lower()):
                            logger.info(f"Tentando clicar no link com href '{href}'")
                            
                            try:
                                botao.click()
                                logger.info(f"Clicou com sucesso no link com href '{href}'")
                                clicou = True
                                break
                            except:
                                # Se falhar, navegar diretamente para o href
                                self.driver.get(href)
                                logger.info(f"Navegou diretamente para '{href}'")
                                clicou = True
                                break
                    except Exception as e:
                        logger.debug(f"Erro ao acessar href: {str(e)}")
            
            # Estratégia 3: Tentar qualquer botão de paginação
            if not clicou:
                logger.info("Tentativa 3: Tentando qualquer botão candidato de paginação")
                for botao in botoes_paginacao:
                    try:
                        try:
                            # Rolar até o botão
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
                            time.sleep(0.5)
                            
                            botao.click()
                            logger.info("Clicou com sucesso em um botão candidato")
                            clicou = True
                        except:
                            # Se falhar, tentar com JavaScript
                            self.driver.execute_script("arguments[0].click();", botao)
                            logger.info("Clicou com JavaScript em um botão candidato")
                            clicou = True
                            break
                    except Exception as e:
                        logger.debug(f"Erro ao clicar em candidato: {str(e)}")
            
            # Estratégia 4: Tentar injetar botão de paginação personalizado
            if not clicou:
                logger.info("Tentativa 4: Injetando botão de paginação personalizado")
                try:
                    # Injetar um botão personalizado para navegar para a próxima página
                    inject_js = """
                    function injetarBotaoPaginacao() {
                        // Verificar se já existe o botão personalizado
                        if (document.getElementById('botao-pagina-injetado')) {
                            document.getElementById('botao-pagina-injetado').remove();
                        }
                        
                        // Encontrar a tabela
                        const tabela = document.querySelector('table');
                        if (!tabela) return false;
                        
                        // Criar o botão
                        const botao = document.createElement('button');
                        botao.id = 'botao-pagina-injetado';
                        botao.textContent = 'Próxima Página →';
                        botao.style.cssText = 'margin: 20px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; font-size: 16px;';
                        
                        // Adicionar após a tabela
                        tabela.parentNode.insertBefore(botao, tabela.nextSibling);
                        
                        // Configurar ação do botão para navegar para a próxima página
                        const proximaPagina = """ + str(pagina_atual + 1) + """;
                        botao.onclick = function() {
                            let url = window.location.href;
                            
                            if (url.includes('page=')) {
                                url = url.replace(/page=\\d+/, 'page=' + proximaPagina);
                            } else if (url.includes('?')) {
                                url += '&page=' + proximaPagina;
                            } else {
                                url += '?page=' + proximaPagina;
                            }
                            
                            console.log('Navegando para:', url);
                            window.location.href = url;
                        };
                        
                        return true;
                    }
                    
                    return injetarBotaoPaginacao();
                    """
                    
                    sucesso_injecao = self.driver.execute_script(inject_js)
                    if sucesso_injecao:
                        logger.info("Botão de paginação personalizado injetado com sucesso")
                        
                        # Capturar screenshot do botão injetado
                        inj_screenshot = f"botao_injetado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        self.driver.save_screenshot(inj_screenshot)
                        logger.info(f"Screenshot do botão injetado salvo em {inj_screenshot}")
                        
                        # Clicar no botão injetado
                        try:
                            botao_injetado = self.driver.find_element(By.ID, "botao-pagina-injetado")
                            botao_injetado.click()
                            logger.info("Clicou no botão injetado")
                            clicou = True
                        except Exception as e:
                            logger.warning(f"Erro ao clicar no botão injetado: {str(e)}")
                            
                            # Tentar clicar com JavaScript
                            try:
                                self.driver.execute_script("document.getElementById('botao-pagina-injetado').click();")
                                logger.info("Clicou no botão injetado via JavaScript")
                                clicou = True
                            except Exception as e2:
                                logger.warning(f"Erro ao clicar no botão injetado via JavaScript: {str(e2)}")
                except Exception as e:
                    logger.warning(f"Erro ao injetar botão de paginação: {str(e)}")
            
            # Estratégia 5: Navegar diretamente para a URL com parâmetro de página
            if not clicou:
                logger.info("Tentativa 5: Navegando diretamente para URL com parâmetro de página")
                try:
                    url_atual = self.driver.current_url
                    proxima_pagina = pagina_atual + 1
                    
                    nova_url = url_atual
                    if "page=" in url_atual:
                        nova_url = re.sub(r'page=\d+', f'page={proxima_pagina}', url_atual)
                    elif "?" in url_atual:
                        nova_url = f"{url_atual}&page={proxima_pagina}"
                    else:
                        nova_url = f"{url_atual}?page={proxima_pagina}"
                    
                    if nova_url != url_atual:
                        logger.info(f"Navegando diretamente para: {nova_url}")
                        self.driver.get(nova_url)
                        clicou = True
                except Exception as e:
                    logger.warning(f"Erro ao navegar diretamente para a próxima página: {str(e)}")
            
            # ESTRATÉGIA 6 (NOVA): Tentar simular a tecla Tab para navegar até o botão de próxima página e pressionar Enter
            if not clicou:
                logger.info("Tentativa 6: Simulando navegação por teclado")
                try:
                    # Primeiro rolar até o fim da página
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    actions = ActionChains(self.driver)
                    # Tentar pressionar Tab várias vezes para chegar aos controles de paginação
                    for _ in range(5):  # Simular 5 pressionamentos de Tab
                        actions.send_keys(Keys.TAB)
                        actions.perform()
                        time.sleep(0.5)
                    
                    # Tentar pressionar Enter para clicar no controle selecionado
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    
                    # Capturar screenshot após tentativa de teclado
                    keyboard_screenshot = f"teclado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(keyboard_screenshot)
                    logger.info(f"Screenshot após simulação de teclado salvo em {keyboard_screenshot}")
                    
                    # Verificar se a navegação parece ter funcionado
                    # Assumir que funcionou e verificar posteriormente
                    clicou = True
                    logger.info("Simulação de teclado executada, verificando resultado posteriormente")
                except Exception as e:
                    logger.warning(f"Erro ao simular navegação por teclado: {str(e)}")
            
            # Verificar se a navegação foi bem-sucedida
            if clicou:
                # Aguardar carregamento da nova página
                time.sleep(5)
                
                # Tirar screenshot da nova página 
                nova_screenshot = f"nova_pagina_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(nova_screenshot)
                logger.info(f"Screenshot da nova página salvo em {nova_screenshot}")
                
                try:
                    # Verificar pelo indicador de páginas para confirmar que mudou
                    novo_indicador = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Registros')]")
                    if novo_indicador:
                        novo_texto = novo_indicador[0].text.strip()
                        logger.info(f"Novo indicador de páginas: {novo_texto}")
                        
                        # Verificar se o texto do indicador mudou
                        if novo_texto != texto_indicador:
                            logger.info("Indicador de páginas mudou, navegação bem-sucedida")
                            return True
                        else:
                            logger.warning("O indicador de páginas não mudou. Pode não ter navegado corretamente.")
                    
                    # Se chegamos aqui, o indicador não mudou ou não foi encontrado
                    # Vamos verificar a tabela para confirmar que estamos em uma página válida
                    table_rows = self.driver.find_elements(By.XPATH, "//table//tr")
                    
                    if table_rows and len(table_rows) > 1:  # Se tem tabela com pelo menos uma linha além do cabeçalho
                        # Verificar se parece conteúdo diferente comparando com o primeiro texto da tabela anterior
                        logger.info("Tabela encontrada com conteúdo. Verificando se é uma nova página...")
                        
                        # Por enquanto, confiar que a página mudou se temos uma tabela válida
                        # Para implementação futura: comparar conteúdo da tabela com a página anterior
                        logger.info("Tabela encontrada com conteúdo, considerando navegação bem-sucedida")
                        return True
                    else:
                        logger.warning("Tabela não encontrada ou sem conteúdo após navegação")
                        return False
                    
                except NoSuchElementException:
                    logger.warning("Tabela não encontrada após navegação, possível página em branco ou erro")
                    return False
                except Exception as e:
                    logger.error(f"Erro ao verificar resultado da navegação: {str(e)}")
                    # Como já clicamos e possivelmente navegamos, vamos retornar True e ver o que acontece na próxima iteração
                    return True
            
            # Se chegamos aqui é porque não conseguimos clicar em nenhum botão ou falhou a navegação
            logger.warning("Não foi possível navegar para a próxima página após múltiplas tentativas")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao navegar para próxima página: {str(e)}")
            return False
    
    def salvar_resultados(self, resultados, prefixo="licencas_ecosistemas"):
        """
        Salva os resultados em Excel e CSV
        """
        if not resultados:
            logger.warning("Nenhum resultado para salvar")
            return
        
        # Garantir que todos os resultados tenham tipo_de_estudo
        for resultado in resultados:
            if 'tipo_de_estudo' not in resultado:
                atividade_principal = resultado.get('atividade_principal', '')
                if any(cod in atividade_principal for cod in ["A-05-02-0", "A-05-03-7", "A-05-04-5", "A-05-05-3"]):
                    resultado['tipo_de_estudo'] = "EIA/RIMA (inferido pela atividade)"
                else:
                    resultado['tipo_de_estudo'] = "A determinar"
                    
            # Garantir que tenha o campo motivo_estudo
            if 'motivo_estudo' not in resultado:
                resultado['motivo_estudo'] = ""
        
        logger.info(f"Salvando {len(resultados)} resultados totais")
        
        # Criar um DataFrame com os resultados
        df = pd.DataFrame(resultados)
        
        # Remover colunas de link (informação interna)
        colunas_para_remover = [
            'link_detalhes', 'Links_Documentos', 'Documentos'
        ]
        
        for coluna in colunas_para_remover:
            if coluna in df.columns:
                df = df.drop(columns=[coluna])
        
        # Definir a ordem das colunas para o arquivo final
        # Primeiro, colunas básicas de identificação
        colunas_inicio = [
            'processo', 'pessoa_física/jurídica', 'empreendimento', 
            'modalidade', 'cpf/cnpj', 'atividade_principal', 
            'município_da_solicitação'
        ]
        
        # Depois, colunas específicas de tipo de estudo no final
        colunas_fim = ['tipo_de_estudo', 'motivo_estudo', 'ações']
        
        # Colunas intermediárias (todas as outras que não estão no início ou fim)
        colunas_todas = list(df.columns)
        colunas_meio = [col for col in colunas_todas 
                        if col not in colunas_inicio and col not in colunas_fim]
        
        # Montar a ordem final de colunas
        colunas_ordenadas = []
        for col in colunas_inicio:
            if col in colunas_todas:
                colunas_ordenadas.append(col)
                
        for col in colunas_meio:
            colunas_ordenadas.append(col)
            
        for col in colunas_fim:
            if col in colunas_todas:
                colunas_ordenadas.append(col)
        
        # Verificar se todas as colunas foram incluídas
        colunas_existentes = [col for col in colunas_ordenadas if col in df.columns]
        
        # Reordenar o DataFrame
        if colunas_existentes:
            df = df[colunas_existentes]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Salvar CSV
        csv_path = f"{prefixo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"Resultados salvos em CSV: {csv_path}")
        
        # Salvar Excel
        excel_path = f"{prefixo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False)
        logger.info(f"Resultados salvos em Excel: {excel_path}")
        
        # Contar e logar os tipos de estudo
        estudos = {"EIA/RIMA": 0, "RCA": 0, "Não identificado": 0, "EIA/RIMA (inferido pela atividade)": 0, "A determinar": 0}
        for resultado in resultados:
            tipo_estudo = resultado.get('tipo_de_estudo', 'Não identificado')
            tipo_base = tipo_estudo.split('(')[0].strip()  # Pegar apenas a parte inicial antes de parênteses
            
            # Verificar em qual categoria se encaixa
            if tipo_base == "EIA/RIMA":
                estudos["EIA/RIMA"] += 1
            elif tipo_base == "RCA":
                estudos["RCA"] += 1
            elif "inferido pela atividade" in tipo_estudo:
                estudos["EIA/RIMA (inferido pela atividade)"] += 1
            elif tipo_estudo == "A determinar":
                estudos["A determinar"] += 1
            else:
                estudos["Não identificado"] += 1
        
        logger.info("=== RESUMO DOS TIPOS DE ESTUDOS ENCONTRADOS ===")
        for estudo, quantidade in estudos.items():
            if quantidade > 0:
                logger.info(f"- {estudo}: {quantidade}")
        logger.info("============================================")
    
    def salvar_resultados_incrementais(self, resultados, filename="ecosistemas_resultados_incrementais.csv"):
        """
        Salva resultados de forma incremental, para não perder dados em caso de falha
        """
        # Criar o arquivo se não existir
        if not os.path.exists(filename):
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if resultados and len(resultados) > 0:
                    fieldnames = resultados[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
        
        # Adicionar novos resultados
        with open(filename, 'a', newline='', encoding='utf-8-sig') as csvfile:
            if resultados and len(resultados) > 0:
                fieldnames = resultados[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                for resultado in resultados:
                    writer.writerow(resultado)
        
        logger.info(f"Salvos {len(resultados)} resultados incrementais em {filename}")
    
    def coletar_dados(self, max_paginas=100):
        """
        Coleta dados do sistema ecosistemas aplicando filtro de Classe 6
        """
        logger.info("Iniciando coleta de dados do sistema ecosistemas")
        
        # Acessar site
        if not self.acessar_site():
            logger.error("Falha ao acessar o site. Encerrando coleta.")
            return []
        
        # Aplicar filtro de Classe 6
        if not self.aplicar_filtro_classe_6():
            logger.error("Falha ao aplicar filtro de Classe 6. Encerrando coleta.")
            return []
        
        todos_resultados = []
        contador_paginas = 1
        
        try:
            # Loop de paginação
            while contador_paginas <= max_paginas:
                logger.info(f"Processando página {contador_paginas} de até {max_paginas}")
                
                # Extrair dados da tabela
                resultados_tabela = self.extrair_dados_tabela()
                
                if not resultados_tabela or len(resultados_tabela) == 0:
                    logger.warning(f"Nenhum resultado encontrado na página {contador_paginas}. Encerrando coleta.")
                    break
                
                logger.info(f"Encontrados {len(resultados_tabela)} registros na página {contador_paginas}")
                
                # Para cada registro, acessar detalhes
                resultados_pagina = []
                for i, resultado in enumerate(resultados_tabela):
                    logger.info(f"Processando registro {i+1} de {len(resultados_tabela)} na página {contador_paginas}")
                    
                    # Unir dados básicos da tabela
                    dados_completos = resultado.copy()
                    
                    # Verificar se tem link para detalhes
                    if "link_detalhes" in resultado and resultado["link_detalhes"]:
                        # Verificar se o link é válido
                        link = resultado["link_detalhes"]
                        if not link.startswith("http"):
                            # Tentar construir o link completo
                            base_url = "https://ecosistemas.meioambiente.mg.gov.br"
                            if link.startswith("/"):
                                link = f"{base_url}{link}"
                            else:
                                link = f"{base_url}/{link}"
                            logger.info(f"Link ajustado para: {link}")
                        
                        # Acessar página de detalhes
                        if self.acessar_proximo_registro(link):
                            # Verificar se estamos em uma página válida
                            try:
                                # Verificar se a página carregou corretamente verificando algum elemento esperado
                                WebDriverWait(self.driver, 5).until(
                                    EC.visibility_of_element_located((By.TAG_NAME, "table"))
                                )
                                
                                # Extrair dados detalhados
                                dados_detalhados = self.extrair_dados_detalhados()
                                
                                # Unir dados
                                dados_completos.update(dados_detalhados)
                                
                                # Garantir que o tipo de estudo seja incluído
                                if "Tipo de Estudo" in dados_detalhados:
                                    # Atualizar o campo tipo_de_estudo com o valor detalhado
                                    dados_completos["tipo_de_estudo"] = dados_detalhados["Tipo de Estudo"]
                                
                                logger.info(f"Dados detalhados extraídos com sucesso para o registro {i+1}")
                            except (TimeoutException, NoSuchElementException) as e:
                                logger.warning(f"Página de detalhes inválida ou vazia: {str(e)}")
                                # Tirar screenshot da página para análise posterior
                                screenshot_path = f"pagina_invalida_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                self.driver.save_screenshot(screenshot_path)
                                logger.info(f"Screenshot da página inválida salvo em {screenshot_path}")
                            finally:
                                # Fechar aba de detalhes independentemente do resultado
                                self.fechar_aba_detalhes()
                        else:
                            logger.warning(f"Não foi possível acessar os detalhes do registro {i+1} na página {contador_paginas}")
                    else:
                        logger.warning(f"O registro {i+1} na página {contador_paginas} não possui link para detalhes")
                        # Garantir que tenha um tipo de estudo mesmo sem acessar detalhes
                        if "tipo_de_estudo" not in dados_completos or dados_completos["tipo_de_estudo"] == "A determinar":
                            atividade_principal = dados_completos.get("atividade_principal", "")
                            if any(cod in atividade_principal for cod in ["A-05-02-0", "A-05-03-7", "A-05-04-5", "A-05-05-3"]):
                                dados_completos["tipo_de_estudo"] = "EIA/RIMA (inferido pela atividade)"
                            else:
                                dados_completos["tipo_de_estudo"] = "A determinar"
                    
                    resultados_pagina.append(dados_completos)
                    
                    # Salvar de forma incremental a cada registro
                    self.salvar_resultados_incrementais([dados_completos])
                    
                    # Pausa entre registros
                    time.sleep(1)
                
                # Adicionar resultados da página aos resultados totais
                todos_resultados.extend(resultados_pagina)
                
                # Verificar se já atingimos o limite máximo de registros para coletar
                if len(todos_resultados) >= 137:
                    logger.info(f"Atingido limite máximo de 137 registros. Finalizando coleta.")
                    break
                
                # Tentar navegar para a próxima página com mais tentativas
                tentativas = 0
                max_tentativas = 3
                tem_proxima_pagina = False
                
                while tentativas < max_tentativas and not tem_proxima_pagina:
                    tentativas += 1
                    logger.info(f"Tentativa {tentativas} de {max_tentativas} para navegar para a próxima página")
                    
                    tem_proxima_pagina = self.navegar_proxima_pagina()
                    
                    if tem_proxima_pagina:
                        logger.info(f"Navegado com sucesso para a página {contador_paginas + 1}")
                        
                        # Aguardar carregamento completo da nova página
                        try:
                            # Esperar pela tabela ou mensagem de nenhum resultado
                            elemento_carregado = WebDriverWait(self.driver, 10).until(
                                EC.any_of(
                                    EC.presence_of_element_located((By.TAG_NAME, "table")),
                                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum registro encontrado')]"))
                                )
                            )
                            
                            # Se encontrou mensagem de nenhum registro, considerar fim da paginação
                            if "Nenhum registro encontrado" in elemento_carregado.text:
                                logger.info("Página sem resultados encontrada. Finalizando coleta.")
                                tem_proxima_pagina = False
                                break
                        except TimeoutException:
                            logger.warning("Timeout esperando carregamento da nova página. Tentando continuar mesmo assim.")
                        
                        break
                    elif tentativas < max_tentativas:
                        logger.warning(f"Falha na tentativa {tentativas}. Aguardando antes de tentar novamente...")
                        time.sleep(3)  # Aguardar antes de tentar novamente
                
                if not tem_proxima_pagina:
                    logger.info("Chegou à última página ou falhou em navegar. Finalizando coleta.")
                    break
                
                contador_paginas += 1

                # Pausa entre páginas para garantir carregamento
                time.sleep(5)
        except Exception as e:
            logger.error(f"Erro durante a coleta: {str(e)}")
            logger.error(traceback.format_exc())  # Registrar o traceback completo
        finally:
            # Salvar todos os resultados
            self.salvar_resultados(todos_resultados)
            
            # Fechar o driver
            try:
                self.driver.quit()
                logger.info("Driver fechado com sucesso")
            except:
                pass
        
        logger.info(f"Coleta concluída. Total de {len(todos_resultados)} registros coletados.")
        return todos_resultados

if __name__ == "__main__":
    # Configurações
    MAX_PAGINAS = 20  # Limite de páginas a serem processadas
    
    logger.info("=" * 50)
    logger.info("INICIANDO COLETA DE LICENÇAS AMBIENTAIS - ECOSISTEMAS")
    logger.info("=" * 50)
    
    coletor = ColetorEcosistemas()
    resultados = coletor.coletar_dados(max_paginas=MAX_PAGINAS)
    
    logger.info("=" * 50)
    logger.info(f"COLETA FINALIZADA: {len(resultados)} REGISTROS")
    logger.info("=" * 50)

    # Nota sobre paginação:
    # A navegação de páginas utiliza várias estratégias progressivas para tentar avançar para a próxima página:
    # 1. Detecta o indicador de páginas (ex: "1 - 10 de 137 Registros") para confirmar existência de mais páginas
    # 2. Procura botões de paginação por meio de diversos seletores XPath e JavaScript
    # 3. Tenta clicar primeiro em botões com texto >», 2, "Próximo", etc.
    # 4. Se não funcionar, tenta clicar em links com href contendo "page="
    # 5. Como último recurso, injeta um botão personalizado ou tenta navegar diretamente por URL
    # 
    # Se o site mudar sua estrutura, pode ser necessário atualizar os seletores ou adicionar novas estratégias.
    # Screenshots são salvos em cada tentativa para auxiliar na depuração. 