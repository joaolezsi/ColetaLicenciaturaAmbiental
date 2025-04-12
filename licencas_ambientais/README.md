# Coletor de Licenças Ambientais de Minas Gerais

Este script automatiza a coleta de dados de licenciamento ambiental do portal da Secretaria de Estado de Meio Ambiente e Desenvolvimento Sustentável (SEMAD) de Minas Gerais.

## Funcionalidades

- Acessa o portal de consulta de licenças ambientais
- Aplica filtros por classe (5 e 6), decisão (Deferida) e período (2015-2024)
- Coleta dados de cada processo listado
- Analisa os pareceres técnicos em busca de referências a RCA ou EIA/RIMA
- Exporta os resultados em formatos Excel e CSV

## Requisitos

- Python 3.8 ou superior
- Google Chrome instalado
- ChromeDriver compatível com a versão do Chrome
- Pacotes Python conforme listados em `requirements.txt`

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Uso

Você pode executar o script de duas maneiras:

### 1. Script básico:

```bash
python scraper.py
```

### 2. Script com parâmetros personalizados:

```bash
python executar.py --paginas 10 --processos 5 --pasta pareceres_coletados
```

Parâmetros disponíveis:
- `--paginas`: Número máximo de páginas para coletar (padrão: 5)
- `--processos`: Número máximo de processos por página (padrão: todos)
- `--pasta`: Pasta para salvar os pareceres técnicos (padrão: pareceres)

### 3. Script alternativo (sem Selenium):

Se você encontrar problemas com o Selenium, um script alternativo está disponível:

```bash
python scraper_alternativo.py
```

Este script usa apenas `requests` e `BeautifulSoup` para coletar os dados, sem depender do navegador Chrome.

## Estrutura dos Dados Coletados

Os dados são exportados em formato Excel e CSV com as seguintes colunas:

- Nome do Empreendimento
- Classe
- Decisão
- Exigência (RCA/EIA-RIMA/Nenhuma)
- Atividade Principal
- Município
- Ano da Decisão
- Link para o Parecer Técnico

## Observações Importantes

- O script inclui pausas entre as requisições para não sobrecarregar o servidor
- Os pareceres técnicos são baixados na pasta "pareceres" para análise
- Logs detalhados são salvos no arquivo "licencas_ambientais.log"

## Ajustes e Personalização

Para modificar os filtros de pesquisa, edite a função `aplicar_filtros()` no arquivo `scraper.py`.

## Análise dos Dados

Após a coleta, você pode utilizar o script de análise para gerar estatísticas e visualizações:

```bash
python analisador.py
```

O analisador oferece:

- **Resumo estatístico** dos dados coletados (distribuição por exigência, classe, município, ano)
- **Visualizações gráficas**:
  - Gráfico de pizza da distribuição de exigências
  - Gráfico de evolução temporal por tipo de exigência
  - Mapa de calor relacionando municípios e tipos de exigência
- **Relatório consolidado** em formato Excel com múltiplas abas de análise

### Requisitos para Análise

Para usar o analisador, instale as dependências adicionais:

```bash
pip install matplotlib seaborn numpy
```

## Solução de Problemas

Se você encontrar problemas ao executar o script, tente as seguintes soluções:

### 1. Verifique a conectividade com o site

Execute o script de teste de conexão:

```bash
python testar_conexao.py
```

Este script verificará se você consegue acessar o site da SEMAD e coletará informações sobre possíveis problemas.

### 2. Problemas com o Selenium/ChromeDriver

- Certifique-se de que o Chrome está instalado no seu sistema
- Verifique se o ChromeDriver está instalado corretamente
- Execute sem o modo headless (comentando a linha 42 em `scraper.py`)
- Tente usar o script alternativo: `python scraper_alternativo.py`

### 3. Erros específicos

- **"Failed to establish a new connection [WinError 10061]"**: Este erro geralmente indica que o ChromeDriver não está iniciando corretamente. Verifique configurações de firewall/antivírus que possam estar bloqueando o ChromeDriver.

- **"Elemento não encontrado"**: Isto pode acontecer se o site da SEMAD mudar seu layout. Tente usar o script alternativo, que é mais flexível para lidar com mudanças no HTML. 