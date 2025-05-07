# Coleta de Licenças Ambientais - Sistema Ecosistemas MG

Este script permite a coleta automatizada de informações sobre licenciamentos ambientais de Classe 6 do sistema Ecosistemas do estado de Minas Gerais.

## Novidades! - Melhorias na Paginação (Versão 2.0)

A nova versão do coletor inclui melhorias significativas na navegação entre páginas de resultados:

- **Rolagem automática** para visualizar elementos de paginação no final da página
- **Abordagem multi-estratégia** para garantir a navegação mesmo em situações difíceis
- **Algoritmo avançado de detecção de botões** que identifica elementos clicáveis relacionados à paginação
- **Screenshots de diagnóstico** para facilitar a depuração
- **Simulação de teclado** como método alternativo para navegar quando os cliques tradicionais falham

Com essas melhorias, o coletor agora consegue navegar com sucesso por todas as páginas de resultados, permitindo a extração completa dos 137 registros disponíveis.

## Sobre o Sistema Ecosistemas

O [Sistema de Licenciamento Ambiental (SLA) - Ecosistemas](https://ecosistemas.meioambiente.mg.gov.br/sla/) é a plataforma atual da Secretaria de Meio Ambiente e Desenvolvimento Sustentável de Minas Gerais (SEMAD-MG) para gerenciamento e consulta de processos de licenciamento ambiental.

## Funcionalidades do Coletor

O script `coletor_ecosistemas.py` implementa:

- Acesso automatizado ao portal público de consulta
- Aplicação de filtro para Classe 6 (empreendimentos de maior impacto)
- Navegação robusta por todas as páginas de resultados (total de 137 registros)
- Extração de dados detalhados de cada processo
- Identificação avançada de exigências de estudos ambientais (EIA/RIMA ou RCA)
- Salvamento incremental dos dados (proteção contra falhas)
- Exportação final em formato CSV e Excel
- Logging detalhado e screenshots para diagnóstico

## Executando via Script de Execução

A forma mais fácil de executar o coletor é usando o script `executar_ecosistemas.py`:

```bash
python licencas_ambientais/executar_ecosistemas.py
```

Opções disponíveis:
- `--max-paginas` - Número máximo de páginas a coletar (padrão: 100)
- `--output-prefix` - Prefixo para arquivos de saída (padrão: licencas_ecosistemas)
- `--modo-manual` - Permite que você aplique filtros manualmente no navegador antes da coleta automática
- `--verbose` - Exibe logs detalhados

Exemplo com configurações personalizadas:
```bash
python licencas_ambientais/executar_ecosistemas.py --max-paginas 15 --output-prefix dados_mineracao --verbose
```

## Requisitos

Antes de executar o script, instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

Principais dependências:
- selenium==4.15.2
- pandas==2.1.0
- webdriver-manager==4.0.1
- beautifulsoup4==4.12.2
- requests==2.31.0
- openpyxl==3.1.2

## Dados Coletados

O script coleta as seguintes informações:

### Dados Básicos (da tabela)
- Processo
- Pessoa Física/Jurídica
- Empreendimento
- Modalidade
- CPF/CNPJ
- Atividade Principal
- Município da Solicitação
- Ações

### Dados Detalhados (de cada processo)
- CPF/CNPJ
- Pessoa Física/Jurídica
- Nome Fantasia
- Empreendimento detalhado
- Município da Solicitação
- Número do Processo
- Classe predominante
- Fator locacional
- Modalidade licenciamento
- Fase do licenciamento
- Tipo solicitação
- Tipo de Estudo (EIA/RIMA, RCA ou Não identificado)
- Lista de documentos associados

## Estratégias de Paginação

O coletor usa múltiplas estratégias para garantir a navegação entre páginas:

1. **Rolagem inteligente** - Rola até o final da página e especificamente até o indicador de registros para garantir visibilidade
2. **Detectores específicos** - Utiliza XPath e JavaScript para encontrar botões de paginação
3. **Abordagem progressiva** - Tenta diferentes métodos de clique, priorizando botões mais relevantes
4. **Análise visual** - Detecta elementos clicáveis na região onde normalmente está a paginação
5. **Injeção de DOM** - Como último recurso, injeta um botão personalizado para navegar
6. **Simulação de teclado** - Usa Tab e Enter para navegar quando os cliques falham

## Tratamento de Erros

O script implementa:

- Recuperação de falhas de conexão
- Salvamento incremental de dados para evitar perda em caso de interrupção
- Logging detalhado para diagnóstico de problemas
- Screenshots automáticos em pontos críticos para facilitar a depuração
- Tratamento de timeouts e elementos não encontrados

## Solução de Problemas

1. **Problema de navegação entre páginas**:
   - Verifique os screenshots gerados para entender o que está acontecendo
   - Os arquivos `paginacao_*.png` e `paginacao_apos_rolagem_*.png` mostram o estado da página durante a tentativa de navegação
   - Ajuste o valor de rolagem em `window.scrollBy(0, X)` se os controles não estiverem visíveis

2. **Erros ao extrair informações**:
   - Verifique se o site mudou seu layout ou classes CSS
   - Aumente os tempos de espera (`time.sleep()`) se necessário

3. **Coleta incompleta ou lenta**:
   - Os dados já coletados são salvos incrementalmente no arquivo `ecosistemas_resultados_incrementais.csv`
   - Para continuar uma coleta interrompida, execute o script novamente

4. **Mensagens "Não foi possível navegar para a próxima página"**:
   - Verifique os logs e os screenshots gerados durante a execução
   - Pode indicar que você chegou ao fim dos resultados ou que os controles de paginação não estão acessíveis 