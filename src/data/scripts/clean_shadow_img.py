import os
import shutil

# Define o caminho da pasta InMaps
inmaps_path = r"C:\Users\Marllon\PycharmProjects\pkm-td\res\PokemonSprites\InMaps"

if not os.path.exists(inmaps_path):
    print(f"Pasta não encontrada: {inmaps_path}")
    exit()

print(f"Procurando em: {inmaps_path}\n")

arquivos_encontrados = []

# Percorre todas as subpastas
for root, dirs, files in os.walk(inmaps_path):
    for file in files:
        if file.endswith('-Shadow.png'):
            full_path = os.path.join(root, file)
            arquivos_encontrados.append(full_path)
            print(f"Encontrado: {full_path}")

print(f"\n{'=' * 60}")
print(f"Total de arquivos -shadow.png: {len(arquivos_encontrados)}")

if arquivos_encontrados:
    resposta = input("\nDeseja deletar TODOS estes arquivos? (sim/NÃO): ")

    if resposta.lower() == 'sim':
        deletados = 0
        for arquivo in arquivos_encontrados:
            try:
                os.remove(arquivo)
                print(f"✓ Deletado: {arquivo}")
                deletados += 1
            except Exception as e:
                print(f"✗ Erro ao deletar {arquivo}: {e}")

        print(f"\n✅ {deletados} arquivos deletados com sucesso!")
    else:
        print("❌ Operação cancelada.")
else:
    print("✅ Nenhum arquivo -shadow.png encontrado nesta pasta!")