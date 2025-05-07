from licencas_ambientais.coletor_otimizado import ColetorOtimizado

# Inicializar o coletor
coletor = ColetorOtimizado()

# Coletar dados para os anos de 2015 a 2024 e classes 5 e 6
anos = list(range(2015, 2025))
classes = [5, 6]

# Executar a coleta
resultados = coletor.coletar_dados(anos, classes)