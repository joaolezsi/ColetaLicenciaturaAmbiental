# Coleta de Licenciamento Ambiental MG

Este repositório contém scripts para coleta automatizada de dados de licenciamento ambiental do estado de Minas Gerais.

## Módulos Disponíveis

Atualmente, o sistema inclui coletores para duas plataformas distintas:

1. **Sistema Antigo** - scraper baseado no site sistemas.meioambiente.mg.gov.br
   - Ver documentação em [licencas_ambientais/README.md](licencas_ambientais/README.md)
   - Coletor otimizado: [licencas_ambientais/README_OTIMIZADO.md](licencas_ambientais/README_OTIMIZADO.md)

2. **Sistema Ecosistemas** - scraper para o novo portal ecosistemas.meioambiente.mg.gov.br
   - Ver documentação em [licencas_ambientais/README_ECOSISTEMAS.md](licencas_ambientais/README_ECOSISTEMAS.md)

## Executando o Novo Coletor Ecosistemas

Para coletar dados do novo sistema Ecosistemas, execute:

```bash
python licencas_ambientais/executar_ecosistemas.py
```

Opções disponíveis:
- `--max-paginas` - Número máximo de páginas a coletar (padrão: 20)
- `--output-prefix` - Prefixo para arquivos de saída (padrão: licencas_ecosistemas)
- `--modo-headless` - Executa o navegador sem interface gráfica
- `--verbose` - Exibe logs detalhados

Exemplo com configurações personalizadas:
```bash
python licencas_ambientais/executar_ecosistemas.py --max-paginas 15 --output-prefix dados_mineracao --verbose
```

## Dados Coletados

O sistema coleta informações detalhadas sobre processos de licenciamento ambiental, incluindo:

- Nome do empreendimento e dados de identificação
- Modalidade e classe do licenciamento
- Municípios e regionais
- Tipos de estudos exigidos (EIA/RIMA, RCA)
- Documentação associada ao processo

Os dados são salvos em formato CSV e Excel para facilitar análises posteriores.

## Requisitos

O projeto requer Python 3.8 ou superior com as seguintes dependências:

```
selenium==4.15.2
pandas==2.1.0
webdriver-manager==4.0.1
beautifulsoup4==4.12.2
requests==2.31.0
openpyxl==3.1.2
```

Para instalar todas as dependências:

```bash
pip install -r licencas_ambientais/requirements.txt
```

## Estrutura do Projeto

```
licencas_ambientais/
├── coletor_ecosistemas.py     # Coletor para o sistema novo (Ecosistemas)
├── coletor_otimizado.py       # Coletor otimizado para o sistema antigo
├── executar_ecosistemas.py    # Script executável para o novo coletor
├── requirements.txt           # Dependências do projeto
├── README_ECOSISTEMAS.md      # Documentação do coletor Ecosistemas
└── README_OTIMIZADO.md        # Documentação do coletor otimizado
```

## Tratamento de Erro e Logs

Todos os coletores implementam:
- Salvamento incremental de dados para prevenir perda em caso de falhas
- Logs detalhados em arquivos e no console
- Tratamento de exceções e falhas de conexão 