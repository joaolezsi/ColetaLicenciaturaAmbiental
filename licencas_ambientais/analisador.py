import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from datetime import datetime
import seaborn as sns
import numpy as np

class AnalisadorLicencas:
    """
    Classe para análise dos dados coletados de licenças ambientais.
    """
    
    def __init__(self, arquivo_dados=None):
        """
        Inicializa o analisador de licenças.
        
        Args:
            arquivo_dados: Caminho para o arquivo Excel ou CSV com os dados coletados.
                          Se None, tentará encontrar o arquivo mais recente na pasta atual.
        """
        self.df = None
        
        if arquivo_dados is None:
            # Tentar encontrar o arquivo mais recente
            arquivos_excel = glob.glob("processos_ambientais_mg_*.xlsx")
            arquivos_csv = glob.glob("processos_ambientais_mg_*.csv")
            
            todos_arquivos = arquivos_excel + arquivos_csv
            if todos_arquivos:
                # Ordenar por data de modificação (mais recente primeiro)
                arquivo_dados = max(todos_arquivos, key=os.path.getmtime)
                print(f"Usando arquivo mais recente: {arquivo_dados}")
            else:
                raise FileNotFoundError("Nenhum arquivo de dados encontrado. Execute o scraper primeiro.")
        
        # Carregar os dados
        if arquivo_dados.endswith('.xlsx'):
            self.df = pd.read_excel(arquivo_dados)
        elif arquivo_dados.endswith('.csv'):
            self.df = pd.read_csv(arquivo_dados, encoding='utf-8-sig')
        else:
            raise ValueError("Formato de arquivo não suportado. Use Excel (.xlsx) ou CSV.")
            
        # Converter colunas de data se necessário
        if 'Ano da Decisão' in self.df.columns:
            self.df['Ano da Decisão'] = pd.to_numeric(self.df['Ano da Decisão'], errors='coerce')
            
        print(f"Dados carregados com sucesso: {len(self.df)} registros.")
        
    def resumo_estatistico(self):
        """
        Apresenta um resumo estatístico dos dados coletados.
        """
        if self.df is None or len(self.df) == 0:
            print("Sem dados para análise.")
            return
            
        print("\n=== RESUMO ESTATÍSTICO ===")
        print(f"Total de processos: {len(self.df)}")
        
        # Contagem por tipo de exigência
        print("\nDistribuição por tipo de exigência:")
        exigencias = self.df['Exigência (RCA/EIA-RIMA/Nenhuma)'].value_counts()
        for exigencia, contagem in exigencias.items():
            print(f"  {exigencia}: {contagem} ({contagem/len(self.df)*100:.1f}%)")
            
        # Contagem por classe
        print("\nDistribuição por classe:")
        classes = self.df['Classe'].value_counts()
        for classe, contagem in classes.items():
            print(f"  Classe {classe}: {contagem} ({contagem/len(self.df)*100:.1f}%)")
            
        # Municípios mais frequentes
        print("\nTop 10 municípios com mais processos:")
        municipios = self.df['Município'].value_counts().head(10)
        for municipio, contagem in municipios.items():
            print(f"  {municipio}: {contagem}")
            
        # Distribuição por ano
        if 'Ano da Decisão' in self.df.columns:
            print("\nDistribuição por ano:")
            anos = self.df['Ano da Decisão'].value_counts().sort_index()
            for ano, contagem in anos.items():
                if not pd.isna(ano):
                    print(f"  {int(ano)}: {contagem}")
    
    def grafico_exigencias(self, salvar=False):
        """
        Gera um gráfico de pizza com a distribuição de exigências (RCA, EIA/RIMA, Nenhuma).
        
        Args:
            salvar: Se True, salva o gráfico como PNG.
        """
        if self.df is None or len(self.df) == 0:
            print("Sem dados para gerar gráfico.")
            return
            
        # Configurar o estilo do gráfico
        plt.figure(figsize=(10, 6))
        sns.set_style("whitegrid")
        
        # Contar exigências
        exigencias = self.df['Exigência (RCA/EIA-RIMA/Nenhuma)'].value_counts()
        
        # Gerar gráfico de pizza
        plt.pie(exigencias, labels=exigencias.index, autopct='%1.1f%%', 
                startangle=90, shadow=True, explode=[0.05] * len(exigencias))
        plt.axis('equal')  # Para que o gráfico seja circular
        plt.title('Distribuição por Tipo de Exigência Ambiental')
        
        if salvar:
            plt.savefig(f'exigencias_{datetime.now().strftime("%Y%m%d")}.png', dpi=300, bbox_inches='tight')
            print(f"Gráfico salvo como exigencias_{datetime.now().strftime('%Y%m%d')}.png")
        
        plt.show()
    
    def grafico_evolucao_temporal(self, salvar=False):
        """
        Gera um gráfico de linhas mostrando a evolução temporal das licenças por tipo de exigência.
        
        Args:
            salvar: Se True, salva o gráfico como PNG.
        """
        if self.df is None or len(self.df) == 0 or 'Ano da Decisão' not in self.df.columns:
            print("Sem dados adequados para gerar gráfico temporal.")
            return
            
        # Remover linhas com ano ausente
        df_temp = self.df.dropna(subset=['Ano da Decisão'])
        
        # Agrupar por ano e tipo de exigência
        agrupado = df_temp.groupby(['Ano da Decisão', 'Exigência (RCA/EIA-RIMA/Nenhuma)']).size().unstack().fillna(0)
        
        # Configurar o estilo do gráfico
        plt.figure(figsize=(12, 7))
        sns.set_style("whitegrid")
        
        # Gerar gráfico de linhas
        agrupado.plot(kind='line', marker='o')
        
        plt.title('Evolução Temporal de Licenças por Tipo de Exigência')
        plt.xlabel('Ano')
        plt.ylabel('Número de Licenças')
        plt.xticks(agrupado.index.astype(int))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Tipo de Exigência')
        
        if salvar:
            plt.savefig(f'evolucao_temporal_{datetime.now().strftime("%Y%m%d")}.png', dpi=300, bbox_inches='tight')
            print(f"Gráfico salvo como evolucao_temporal_{datetime.now().strftime('%Y%m%d')}.png")
        
        plt.show()
    
    def mapa_calor_municipios_exigencias(self, top_n=15, salvar=False):
        """
        Gera um mapa de calor mostrando a relação entre os principais municípios e tipos de exigência.
        
        Args:
            top_n: Número de municípios mais frequentes a incluir no gráfico.
            salvar: Se True, salva o gráfico como PNG.
        """
        if self.df is None or len(self.df) == 0:
            print("Sem dados para gerar mapa de calor.")
            return
            
        # Identificar os top N municípios
        top_municipios = self.df['Município'].value_counts().head(top_n).index.tolist()
        
        # Filtrar o DataFrame para incluir apenas esses municípios
        df_top = self.df[self.df['Município'].isin(top_municipios)]
        
        # Criar tabela de contingência
        tabela = pd.crosstab(df_top['Município'], df_top['Exigência (RCA/EIA-RIMA/Nenhuma)'])
        
        # Configurar o estilo do gráfico
        plt.figure(figsize=(12, 10))
        sns.set_style("whitegrid")
        
        # Gerar mapa de calor
        sns.heatmap(tabela, cmap='YlGnBu', annot=True, fmt='d', cbar_kws={'label': 'Número de Licenças'})
        
        plt.title(f'Relação entre os {top_n} Municípios Mais Frequentes e Tipos de Exigência')
        plt.xlabel('Tipo de Exigência')
        plt.ylabel('Município')
        plt.tight_layout()
        
        if salvar:
            plt.savefig(f'mapa_calor_municipios_{datetime.now().strftime("%Y%m%d")}.png', dpi=300, bbox_inches='tight')
            print(f"Gráfico salvo como mapa_calor_municipios_{datetime.now().strftime('%Y%m%d')}.png")
        
        plt.show()
        
    def exportar_relatorio(self, nome_arquivo=None):
        """
        Exporta um relatório em formato Excel com várias abas de análise.
        
        Args:
            nome_arquivo: Nome do arquivo para salvar o relatório.
                         Se None, usa um nome padrão com timestamp.
        """
        if self.df is None or len(self.df) == 0:
            print("Sem dados para exportar relatório.")
            return
            
        if nome_arquivo is None:
            nome_arquivo = f"relatorio_licencas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
        # Criar um escritor do Excel
        writer = pd.ExcelWriter(nome_arquivo, engine='openpyxl')
        
        # Exportar dados brutos
        self.df.to_excel(writer, sheet_name='Dados Brutos', index=False)
        
        # Resumo por tipo de exigência
        resumo_exigencia = self.df.groupby('Exigência (RCA/EIA-RIMA/Nenhuma)').size().reset_index(name='Contagem')
        resumo_exigencia['Porcentagem'] = resumo_exigencia['Contagem'] / len(self.df) * 100
        resumo_exigencia.to_excel(writer, sheet_name='Resumo por Exigência', index=False)
        
        # Resumo por município
        resumo_municipio = self.df.groupby('Município').size().reset_index(name='Contagem')
        resumo_municipio = resumo_municipio.sort_values('Contagem', ascending=False)
        resumo_municipio.to_excel(writer, sheet_name='Resumo por Município', index=False)
        
        # Resumo por ano (se disponível)
        if 'Ano da Decisão' in self.df.columns:
            df_ano = self.df.dropna(subset=['Ano da Decisão'])
            resumo_ano = df_ano.groupby('Ano da Decisão').size().reset_index(name='Contagem')
            resumo_ano = resumo_ano.sort_values('Ano da Decisão')
            resumo_ano.to_excel(writer, sheet_name='Resumo por Ano', index=False)
            
            # Resumo cruzado: Ano x Exigência
            cruzada_ano_exigencia = pd.crosstab(
                df_ano['Ano da Decisão'], 
                df_ano['Exigência (RCA/EIA-RIMA/Nenhuma)']
            ).reset_index()
            cruzada_ano_exigencia.to_excel(writer, sheet_name='Ano x Exigência', index=False)
        
        # Salvar o arquivo
        writer.close()
        
        print(f"Relatório exportado para {nome_arquivo}")


if __name__ == "__main__":
    try:
        analisador = AnalisadorLicencas()
        
        # Exibir resumo estatístico
        analisador.resumo_estatistico()
        
        # Gerar gráficos básicos
        analisador.grafico_exigencias(salvar=True)
        analisador.grafico_evolucao_temporal(salvar=True)
        analisador.mapa_calor_municipios_exigencias(top_n=10, salvar=True)
        
        # Exportar relatório
        analisador.exportar_relatorio()
        
    except Exception as e:
        print(f"Erro na análise: {str(e)}") 