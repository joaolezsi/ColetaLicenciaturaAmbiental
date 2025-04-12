# Coleta Otimizada de Licenças Ambientais MG

Este guia explica os scripts otimizados para coleta de licenças ambientais do estado de Minas Gerais, focados em resolver problemas de desempenho e garantir a integridade dos dados.

## Scripts Otimizados

1. **coletor_otimizado.py** - Coleta dados diretamente das tabelas de resultados sem depender de PDFs
2. **criar_csv_dos_pdfs.py** - Cria CSV a partir dos PDFs já baixados na pasta "pareceres"

## Uso Recomendado

Para garantir a coleta mais completa e robusta, siga esta abordagem:

### Método 1: Coleta Direta da Tabela (Mais Rápido)

Este método extrai os dados diretamente das tabelas de resultados, sem depender da análise de PDFs, o que é muito mais rápido:

```bash
python licencas_ambientais/coletor_otimizado.py
```

Parâmetros configuráveis (edite o script para ajustar):
- `ANOS` - Lista de anos para coletar (padrão: 2015 a 2024)
- `CLASSES` - Lista de classes para coletar (padrão: 5 e 6)
- `MAX_PAGINAS` - Número máximo de páginas por consulta (padrão: 100)
- `ANALISAR_PROCESSOS` - Se deve visitar cada página de processo (padrão: True)

**Características**:
- Salva resultados incrementalmente durante a coleta
- Mais rápido que o método baseado em análise de PDFs
- Não depende do Selenium, apenas requests e BeautifulSoup
- Produz CSV e Excel com todos os campos necessários

### Método 2: Criar CSV a partir dos PDFs (Mais detalhado)

Se você já baixou os PDFs dos pareceres na pasta "pareceres" e quer extrair informações deles:

```bash
python licencas_ambientais/criar_csv_dos_pdfs.py
```

**Características**:
- Analisa cada PDF para extrair metadados e identificar exigências
- Salva resultados incrementalmente a cada 10 PDFs processados
- Mais preciso para identificar exigências de RCA e EIA/RIMA
- Produz CSV e Excel com todos os campos necessários

## Solução de Problemas Comuns

### 1. Problema: Coleta interrompida

Se a coleta for interrompida antes de terminar, você não perderá os dados já coletados:

- O `coletor_otimizado.py` salva resultados incrementais em `resultados_incrementais.csv`
- O `criar_csv_dos_pdfs.py` salva resultados parciais a cada 10 PDFs

### 2. Problema: Dados inconsistentes

Se os dados coletados parecerem inconsistentes:

- Verifique os logs para identificar erros
- Execute o script com diferentes configurações (anos/classes)
- Tente usar a abordagem alternativa (se usou coleta direta, tente análise de PDFs)

### 3. Problema: Problemas de conexão

Se encontrar problemas de conexão ao site:

- Aguarde alguns minutos e tente novamente
- Verifique se o site está acessível pelo navegador
- Use o script `testar_conexao.py` para diagnosticar problemas

## Campos no CSV/Excel Gerado

Os seguintes campos são incluídos nos arquivos gerados:

- **Nome do Empreendimento** - Nome da empresa/empreendimento
- **Classe** - Classe do empreendimento (5 ou 6)
- **Decisão** - Decisão sobre a licença (geralmente "Deferida")
- **Exigência (RCA/EIA-RIMA/Nenhuma)** - Tipo de exigência identificada
- **Atividade Principal** - Atividade principal do empreendimento
- **Município** - Município onde está localizado
- **Ano da Decisão** - Ano em que a decisão foi tomada
- **Link para o Parecer Técnico** - Link para o parecer ou caminho local do arquivo
- **Regional** - Regional da SEMAD responsável
- **CNPJ/CPF** - Documento de identificação do empreendimento
- **Processo Adm** - Número do processo administrativo
- **Modalidade** - Modalidade da licença

## Recomendações

1. **Abordagem combinada**: Para melhor resultado, recomendamos executar o `coletor_otimizado.py` primeiro para obter os dados básicos e depois o `criar_csv_dos_pdfs.py` para enriquecer com informações dos pareceres.

2. **Múltiplas execuções**: Se o site for instável, considere executar múltiplas vezes com diferentes faixas de anos ou classes.

3. **Verificação manual**: Sempre faça uma verificação manual de alguns registros para confirmar a qualidade dos dados extraídos. 