import os
import re
import pandas as pd
import fitz  # PyMuPDF
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdfs_para_csv.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def extrair_texto_pdf(caminho_pdf):
    """Extrai o texto de um PDF com técnicas adicionais para PDFs problemáticos"""
    try:
        texto = ""
        # Primeira tentativa - método padrão PyMuPDF
        with fitz.open(caminho_pdf) as doc:
            for pagina in doc:
                texto += pagina.get_text()
                
        # Se não conseguiu extrair texto substancial, tentar método alternativo
        if len(texto.strip()) < 100:  # Se extraiu menos de 100 caracteres
            logger.info(f"Texto extraído muito curto, tentando método alternativo para {caminho_pdf}")
            # Tentar extrair com parâmetros diferentes
            with fitz.open(caminho_pdf) as doc:
                for pagina in doc:
                    # Tentar diferentes flags de extração
                    texto_alt = pagina.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
                    if texto_alt:
                        texto += texto_alt
            
            # Se ainda não conseguiu texto substancial, pode-se implementar OCR aqui
            # Isso requer instalação adicional do pytesseract
            
        return texto
    except Exception as e:
        logger.error(f"Erro ao extrair texto de {caminho_pdf}: {str(e)}")
        return ""

def verificar_exigencia(texto):
    """Verifica as exigências no texto do PDF usando uma abordagem mais robusta"""
    if not texto:
        return "Não identificado"
    
    texto_lower = texto.lower()
    
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
    paragrafos = texto_lower.split('\n\n')
    
    # Extrair o início do documento (primeiros parágrafos)
    inicio = ' '.join(paragrafos[:10] if len(paragrafos) > 10 else paragrafos)
    
    # Tentar encontrar conclusão ou parecer final
    conclusao = ""
    for i, paragrafo in enumerate(paragrafos):
        if 'conclus' in paragrafo or 'parecer' in paragrafo:
            # Pegar este parágrafo e os próximos 3
            conclusao = ' '.join(paragrafos[i:i+4] if i+4 <= len(paragrafos) else paragrafos[i:])
            break
    
    # Verificar RCA em partes críticas do documento primeiro
    for termo in termos_rca:
        if termo in inicio or termo in conclusao:
            return "RCA"
            
    # Verificar EIA/RIMA em partes críticas do documento
    for termo in termos_eia_rima:
        if termo in inicio or termo in conclusao:
            return "EIA/RIMA"
    
    # Se não encontrou nas seções críticas, verificar no texto completo
    for termo in termos_rca:
        if termo in texto_lower:
            return "RCA"
            
    for termo in termos_eia_rima:
        if termo in texto_lower:
            return "EIA/RIMA"
    
    return "Nenhuma"

def extrair_metadados_do_texto(texto):
    """Tenta extrair metadados do texto do PDF"""
    metadados = {
        "Nome do Empreendimento": "Não identificado",
        "Classe": "Não identificado",
        "Decisão": "Deferida",  # Assumindo que é deferida conforme os filtros
        "Atividade Principal": "Não identificado",
        "Município": "Não identificado",
        "Ano da Decisão": "Não identificado",
        "Regional": "Não identificado",
        "CNPJ/CPF": "Não identificado",
        "Processo Adm": "Não identificado",
        "Modalidade": "Não identificado",
    }
    
    # Lista de linhas do texto
    linhas = texto.split('\n')
    
    # Padrões para identificar informações
    padroes = {
        "Nome do Empreendimento": [
            r"empreendimento:\s*(.+)",
            r"empreendimento/?razão\s*social\s*[:-]\s*(.+)",
            r"denominado\s*(.+?)\s*,\s*localizada?",
            r"o\s*empreendimento\s*(.+?)\s*está\s*localizada?",
        ],
        "Classe": [
            r"classe\s*(\d+)",
            r"classe:?\s*(\d+)",
        ],
        "Município": [
            r"município\s*[:-]?\s*(.+)",
            r"municípios?\s*[:-]?\s*(.+)",
            r"localizada?\s*no\s*município\s*de\s*(.+?)[,\.]",
        ],
        "Processo Adm": [
            r"processo\s*administrativo\s*[:-]?\s*(.+)",
            r"processo\s*[:-]?\s*(.+)",
            r"pa\s*[:-]?\s*(.+)",
        ],
        "CNPJ/CPF": [
            r"cnpj\s*[:-]?\s*(.+)",
            r"cnpj\s*[:-]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
            r"cpf\s*[:-]?\s*(.+)",
            r"cpf\s*[:-]?\s*(\d{3}\.\d{3}\.\d{3}-\d{2})",
        ],
        "Atividade Principal": [
            r"atividade\s*principal\s*[:-]?\s*(.+)",
            r"atividade\s*[:-]?\s*(.+)",
            r"tipologia\s*[:-]?\s*(.+)",
        ],
        "Ano da Decisão": [
            r"data\s*da\s*decisão\s*[:-]?\s*(.+?)/(\d{4})",
            r"decisão\s*em\s*(.+?)/(\d{4})",
        ],
        "Regional": [
            r"regional\s*[:-]?\s*(.+)",
            r"supram\s*[:-]?\s*(.+)",
            r"ura\s*[:-]?\s*(.+)",
        ],
        "Modalidade": [
            r"modalidade\s*[:-]?\s*(.+)",
            r"tipo\s*de\s*licença\s*[:-]?\s*(.+)",
        ],
    }
    
    # Procurar os padrões no texto
    for campo, lista_padroes in padroes.items():
        for padrao in lista_padroes:
            for linha in linhas:
                match = re.search(padrao, linha.lower())
                if match:
                    valor = match.group(1).strip()
                    # Pegar apenas o que parece ser um valor válido
                    if valor and len(valor) > 1 and len(valor) < 100:  # Evitar textos muito longos
                        metadados[campo] = valor.title()  # Capitalizar nomes próprios
                        break
            if metadados[campo] != "Não identificado":
                break
    
    # Caso especial para o ano da decisão (extrair do segundo grupo)
    for linha in linhas:
        for padrao in padroes["Ano da Decisão"]:
            match = re.search(padrao, linha.lower())
            if match and len(match.groups()) >= 2:
                metadados["Ano da Decisão"] = match.group(2).strip()
                break
    
    # Caso especial para classe (extrair apenas o número)
    if metadados["Classe"] != "Não identificado":
        match = re.search(r'(\d+)', metadados["Classe"])
        if match:
            metadados["Classe"] = f"Classe {match.group(1)}"
    
    return metadados

def processar_pdfs(pasta_pdfs="pareceres"):
    """Processa todos os PDFs na pasta e gera um CSV"""
    logger.info(f"Processando PDFs na pasta: {pasta_pdfs}")
    
    if not os.path.exists(pasta_pdfs):
        logger.error(f"Pasta {pasta_pdfs} não encontrada")
        return []
    
    resultados = []
    arquivos_pdf = [f for f in os.listdir(pasta_pdfs) if f.endswith('.pdf')]
    total_pdfs = len(arquivos_pdf)
    logger.info(f"Encontrados {total_pdfs} arquivos PDF para processar")
    
    for i, arquivo in enumerate(arquivos_pdf):
        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        logger.info(f"Processando {i+1}/{total_pdfs}: {arquivo}")
        
        # Extrair texto do PDF
        texto = extrair_texto_pdf(caminho_completo)
        if not texto:
            logger.warning(f"Não foi possível extrair texto de {arquivo}")
            continue
        
        # Verificar exigência
        exigencia = verificar_exigencia(texto)
        logger.info(f"Exigência identificada: {exigencia}")
        
        # Extrair metadados
        metadados = extrair_metadados_do_texto(texto)
        metadados["Exigência (RCA/EIA-RIMA/Nenhuma)"] = exigencia
        metadados["Nome do Arquivo"] = arquivo
        metadados["Caminho do Arquivo"] = caminho_completo
        
        resultados.append(metadados)
        
        # Salvar resultados parciais a cada 10 PDFs
        if (i + 1) % 10 == 0 or i == total_pdfs - 1:
            df_parcial = pd.DataFrame(resultados)
            df_parcial.to_csv(f"resultados_parciais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                              index=False, encoding='utf-8-sig')
            logger.info(f"Salvos resultados parciais com {len(resultados)} registros")
    
    logger.info(f"Processamento concluído. Total de {len(resultados)} PDFs processados.")
    return resultados

def main():
    logger.info("=" * 50)
    logger.info("INICIANDO PROCESSAMENTO DE PDFs PARA CSV")
    logger.info("=" * 50)
    
    pasta_pdfs = "pareceres"  # Pasta onde estão os PDFs
    resultados = processar_pdfs(pasta_pdfs)
    
    # Salvar resultados em CSV e Excel
    if resultados:
        df = pd.DataFrame(resultados)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"licencas_de_pdfs_{timestamp}.csv"
        excel_path = f"licencas_de_pdfs_{timestamp}.xlsx"
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"Resultados salvos em CSV: {csv_path}")
        
        df.to_excel(excel_path, index=False)
        logger.info(f"Resultados salvos em Excel: {excel_path}")
    else:
        logger.warning("Nenhum resultado para salvar")
    
    logger.info("=" * 50)
    logger.info("PROCESSAMENTO CONCLUÍDO")
    logger.info("=" * 50)

if __name__ == "__main__":
    main() 