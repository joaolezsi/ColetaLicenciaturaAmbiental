import pandas as pd
import os
import glob
import logging
from datetime import datetime
import re
import fitz  # PyMuPDF

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("retroalimentar.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def extrair_texto_pdf_melhorado(caminho_pdf):
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
            # import pytesseract
            # from PIL import Image
            # ...
            
        return texto
    except Exception as e:
        logger.error(f"Erro ao extrair texto de {caminho_pdf}: {str(e)}")
        return ""

def verificar_exigencia_avancado(texto):
    """Verificação mais robusta de exigências nos textos"""
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
    
    # Se não encontrou nas seções críticas, verificar no documento todo
    for termo in termos_rca:
        if termo in texto_lower:
            return "RCA"
            
    for termo in termos_eia_rima:
        if termo in texto_lower:
            return "EIA/RIMA"
    
    return "Nenhuma"

def identificar_pdfs_da_pasta(pasta_pdfs):
    """Identifica todos os PDFs na pasta e retorna um dicionário com informações"""
    resultados = {}
    arquivos_pdf = [f for f in os.listdir(pasta_pdfs) if f.endswith('.pdf')]
    total_pdfs = len(arquivos_pdf)
    logger.info(f"Encontrados {total_pdfs} arquivos PDF para processar")
    
    return arquivos_pdf

def mapear_pdf_para_processo(arquivo_csv, arquivos_pdf, pasta_pdfs):
    """
    Mapeia os PDFs para os processos no CSV, usando vários métodos:
    1. URL direta que inclui o nome do arquivo
    2. ID do processo que aparece no nome do arquivo
    3. Nome do empreendimento que aparece no início do PDF
    """
    # Carregar o CSV
    try:
        df = pd.read_csv(arquivo_csv)
        logger.info(f"Arquivo CSV carregado: {len(df)} registros")
    except Exception as e:
        logger.error(f"Erro ao carregar CSV: {str(e)}")
        return {}, pd.DataFrame()
    
    # Criar mapeamento de PDFs para processos
    mapeamento = {}
    
    # Extrair IDs da coluna de links
    df['processo_id'] = df['Link para o Parecer Técnico'].apply(
        lambda x: re.search(r'id=(\d+)', str(x)).group(1) if isinstance(x, str) and re.search(r'id=(\d+)', str(x)) else None
    )
    
    # Para cada PDF, tentar mapear para um processo
    for arquivo in arquivos_pdf:
        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        
        # Procurar processo por ID no nome do arquivo (parecer_12345.pdf)
        id_match = re.search(r'(\d+)\.pdf$', arquivo)
        if id_match:
            numero = id_match.group(1)
            for idx, row in df.iterrows():
                if row['processo_id'] == numero:
                    mapeamento[arquivo] = idx
                    break
        
        # Se não encontrou por ID, tentar pelo conteúdo inicial do PDF
        if arquivo not in mapeamento:
            texto = extrair_texto_pdf_melhorado(caminho_completo)
            if texto:
                # Pegar as primeiras 500 caracteres para buscar o nome do empreendimento
                inicio_texto = texto[:500].lower()
                for idx, row in df.iterrows():
                    nome_empreendimento = str(row['Nome do Empreendimento']).lower()
                    if len(nome_empreendimento) > 5 and nome_empreendimento in inicio_texto:
                        mapeamento[arquivo] = idx
                        break
    
    logger.info(f"Mapeados {len(mapeamento)} PDFs para processos no CSV")
    return mapeamento, df

def retroalimentar_exigencias(arquivo_csv="resultados_incrementais.csv", pasta_pdfs="pareceres"):
    """Retroalimenta o arquivo CSV com as exigências analisadas dos PDFs já baixados"""
    
    # Identificar PDFs na pasta
    arquivos_pdf = identificar_pdfs_da_pasta(pasta_pdfs)
    
    # Mapear PDFs para processos no CSV
    mapeamento, df = mapear_pdf_para_processo(arquivo_csv, arquivos_pdf, pasta_pdfs)
    
    if df.empty:
        logger.error("Não foi possível carregar ou processar o CSV")
        return None
    
    # Contador de atualizações
    atualizados = 0
    
    # Para cada PDF mapeado para um processo, analisar e atualizar
    for arquivo, idx in mapeamento.items():
        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        
        # Verificar se já tem exigência identificada
        exigencia_atual = df.at[idx, 'Exigência (RCA/EIA-RIMA/Nenhuma)']
        if exigencia_atual in ['Nenhuma', 'A definir', 'Não identificado', 'Não analisado']:
            logger.info(f"Analisando PDF {arquivo} para processo {idx}")
            
            # Extrair texto do PDF
            texto = extrair_texto_pdf_melhorado(caminho_completo)
            
            if texto:
                # Identificar exigência
                exigencia = verificar_exigencia_avancado(texto)
                
                # Atualizar dataframe se encontrou algo diferente de "Nenhuma"
                if exigencia != 'Nenhuma':
                    df.at[idx, 'Exigência (RCA/EIA-RIMA/Nenhuma)'] = exigencia
                    atualizados += 1
                    logger.info(f"Exigência identificada: {exigencia} para {arquivo}")
    
    # Salvar dataframe atualizado
    if atualizados > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        novo_csv = f"processos_atualizados_{timestamp}.csv"
        df.to_csv(novo_csv, index=False, encoding='utf-8-sig')
        
        # Salvar também em Excel
        try:
            novo_excel = f"processos_atualizados_{timestamp}.xlsx"
            df.to_excel(novo_excel, index=False)
            logger.info(f"Resultados salvos em Excel: {novo_excel}")
        except Exception as e:
            logger.error(f"Erro ao salvar Excel (verifique se 'openpyxl' está instalado): {str(e)}")
        
        logger.info(f"Processo concluído. Atualizados {atualizados} registros.")
        logger.info(f"Novos arquivos salvos: {novo_csv}")
    else:
        logger.info("Nenhum registro atualizado")
    
    return df

def executar_analise_rapida():
    """Executa uma análise rápida de todos os PDFs na pasta pareceres"""
    pasta_pdfs = "pareceres"
    logger.info("Executando análise rápida de todos os PDFs...")
    
    # Identificar PDFs na pasta
    arquivos_pdf = [f for f in os.listdir(pasta_pdfs) if f.endswith('.pdf')]
    resultados = []
    
    for arquivo in arquivos_pdf:
        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        logger.info(f"Analisando {arquivo}...")
        
        # Extrair texto
        texto = extrair_texto_pdf_melhorado(caminho_completo)
        
        if texto:
            # Identificar exigência
            exigencia = verificar_exigencia_avancado(texto)
            
            # Adicionar aos resultados
            resultados.append({
                "Arquivo": arquivo,
                "Exigência": exigencia,
                "Tamanho do Texto": len(texto)
            })
            logger.info(f"Exigência identificada: {exigencia}")
        else:
            logger.warning(f"Não foi possível extrair texto de {arquivo}")
            resultados.append({
                "Arquivo": arquivo,
                "Exigência": "Falha na extração",
                "Tamanho do Texto": 0
            })
    
    # Salvar resultados
    if resultados:
        df_resultados = pd.DataFrame(resultados)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        arquivo_saida = f"analise_rapida_{timestamp}.csv"
        df_resultados.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
        logger.info(f"Análise rápida concluída. Resultados salvos em {arquivo_saida}")
        
        # Contagem por tipo de exigência
        contagem = df_resultados['Exigência'].value_counts()
        logger.info("Resumo de exigências identificadas:")
        for exigencia, count in contagem.items():
            logger.info(f"  {exigencia}: {count}")
    
    return resultados

if __name__ == "__main__":
    import sys
    
    # Verificar se deve executar análise rápida ou retroalimentação
    if len(sys.argv) > 1 and sys.argv[1] == '--rapido':
        executar_analise_rapida()
    else:
        # Encontrar o CSV mais recente
        arquivos_csv = glob.glob("*.csv")
        arquivo_csv = max([f for f in arquivos_csv if f.startswith(('processos_', 'resultados_'))], 
                        key=os.path.getmtime, default=None)
        
        if arquivo_csv:
            logger.info(f"Usando o arquivo CSV mais recente: {arquivo_csv}")
            retroalimentar_exigencias(arquivo_csv=arquivo_csv)
        else:
            logger.error("Nenhum arquivo CSV de resultados encontrado")
            print("Por favor, forneça o caminho para o arquivo CSV: python retroalimentar_exigencias.py /caminho/para/arquivo.csv") 