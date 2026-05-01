"""
LAUNCHER DO POKEMON TD
Verifica versões no GitHub e atualiza automaticamente
"""
import os
import sys
import json
import zipfile
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
import subprocess
import re

# CONFIGURAÇÃO DO GITHUB
GITHUB_REPO = "Marllon-Mayron/pkm-td"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class PokemonTDLauncher:
    def __init__(self):
        # Onde o launcher está
        self.launcher_dir = Path(sys.argv[0]).parent

        # Onde o jogo será instalado/atualizado
        self.game_dir = self.launcher_dir / "PokemonTD"

        # Versão atual
        self.current_version = self.get_local_version()

    def get_local_version(self):
        """Lê a versão instalada localmente"""
        version_file = self.game_dir / "game_version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.0.0"

    def get_latest_release(self):
        """Pega informações da última release no GitHub"""
        try:
            print(f"\n📡 Conectando ao GitHub...")
            with urlopen(GITHUB_API, timeout=10) as response:
                data = json.loads(response.read().decode())

                version = data.get("tag_name", "0.0.0")
                # Remove o 'v' se existir (v0.1.5 -> 0.1.5)
                if version.startswith('v'):
                    version = version[1:]

                # O GitHub sempre gera o Source code.zip
                # A URL é sempre: https://github.com/Marllon-Mayron/pkm-td/archive/refs/tags/v0.1.5.zip
                zip_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/v{version}.zip"

                # Tenta achar também nos assets
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        zip_url = asset["browser_download_url"]
                        break

                # Pega as notas da versão
                changelog = data.get("body", "Sem descrição")

                return {
                    "version": version,
                    "download_url": zip_url,
                    "changelog": changelog,
                    "published_at": data.get("published_at", "")
                }

        except URLError:
            print("   ⚠️  Sem conexão com a internet!")
            return None
        except Exception as e:
            print(f"   ⚠️  Erro: {e}")
            return None

    def download_game(self, download_url):
        """Baixa o jogo do GitHub"""
        try:
            print(f"\n📥 Baixando jogo versão {self.latest_version}...")

            # Cria arquivo temporário
            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.close()

            # Baixa o arquivo
            print(f"   🔗 URL: {download_url}")
            print(f"   ⏳ Baixando... (pode levar alguns segundos)")
            urlretrieve(download_url, temp_zip.name)

            # Remove jogo antigo se existir
            if self.game_dir.exists():
                print("   🗑️  Removendo versão antiga...")
                shutil.rmtree(self.game_dir)

            self.game_dir.mkdir(parents=True)

            # Extrai o zip
            print("   📦 Extraindo arquivos...")
            extracted_files = 0

            with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                # O GitHub cria uma pasta tipo: pkm-td-0.1.5/
                # Precisamos extrair o conteúdo dessa pasta

                # Descobre o nome da pasta raiz no zip
                root_folder = None
                for name in zip_ref.namelist():
                    if '/' in name:
                        root_folder = name.split('/')[0]
                        break

                for member in zip_ref.namelist():
                    # Pula arquivos de sistema
                    if '__MACOSX' in member or '.DS_Store' in member:
                        continue

                    # Remove a pasta raiz do caminho
                    if root_folder and member.startswith(root_folder):
                        # Pega o caminho relativo (remove a pasta raiz)
                        relative_path = member[len(root_folder)+1:]

                        if relative_path:  # Se não for vazio
                            target_path = self.game_dir / relative_path

                            if member.endswith('/'):  # É pasta
                                target_path.mkdir(parents=True, exist_ok=True)
                            else:  # É arquivo
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)
                                extracted_files += 1

            # Limpa o zip temporário
            os.unlink(temp_zip.name)

            print(f"   ✅ {extracted_files} arquivos extraídos com sucesso!")

            # Verifica se main.py existe
            main_py = self.game_dir / "main.py"
            if not main_py.exists():
                # Tenta em src/main.py
                main_py = self.game_dir / "src" / "main.py"
                if main_py.exists():
                    print("   ✅ Jogo encontrado em src/main.py")
                else:
                    print("   ⚠️  Aviso: main.py não encontrado, mas continuando...")

            return True

        except Exception as e:
            print(f"   ❌ Erro no download: {e}")
            return False

    def launch_game(self):
        """Inicia o jogo"""
        # Procura o main.py em várias possíveis localizações
        possible_paths = [
            self.game_dir / "main.py",
            self.game_dir / "src" / "main.py",
            self.game_dir / "game" / "main.py",
        ]

        main_py = None
        for path in possible_paths:
            if path.exists():
                main_py = path
                break

        if not main_py:
            print("\n❌ ERRO: Jogo não encontrado!")
            print(f"   Procurado em: {self.game_dir}")
            print("   Tente executar o launcher novamente.")
            input("\nPressione ENTER para sair...")
            return False

        print(f"\n🎮 Iniciando Pokémon TD...")
        print(f"   📂 {main_py}")

        # Muda para o diretório do jogo
        os.chdir(self.game_dir)

        # Executa o jogo
        try:
            if sys.platform == "win32":
                # Windows
                subprocess.Popen([sys.executable, str(main_py)],
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # Linux/Mac
                subprocess.Popen([sys.executable, str(main_py)])

            return True
        except Exception as e:
            print(f"   ❌ Erro ao iniciar: {e}")
            return False

    def show_menu(self):
        """Mostra menu do launcher"""
        print("\n" + "="*50)
        print("     🎮 POKEMON TD - LAUNCHER")
        print("="*50)
        print(f"   📍 Versão instalada: {self.current_version}")
        print()
        print("   [1] Jogar")
        print("   [2] Verificar atualizações")
        print("   [3] Sair")
        print("="*50)

        choice = input("   Escolha: ").strip()
        return choice

    def run(self):
        """Loop principal"""
        while True:
            choice = self.show_menu()

            if choice == "1":
                # Verifica atualizações antes de jogar
                release = self.get_latest_release()

                if release and release["version"] > self.current_version:
                    self.latest_version = release["version"]
                    print(f"\n✨ Nova versão disponível: {release['version']}")
                    print(f"   Versão atual: {self.current_version}")

                    if release['changelog']:
                        print(f"\n📝 Novidades:\n{release['changelog'][:200]}")

                    update = input("\n   Deseja atualizar agora? (S/N): ").upper().strip()
                    if update == "S":
                        if self.download_game(release["download_url"]):
                            # Salva a nova versão
                            version_file = self.game_dir / "game_version.txt"
                            version_file.write_text(release["version"])
                            self.current_version = release["version"]
                            print(f"\n✅ Atualizado para versão {release['version']}!")
                        else:
                            print("\n❌ Falha na atualização!")
                            input("\nPressione ENTER para continuar...")
                            continue
                elif release:
                    print(f"\n✅ Jogo atualizado! (versão {self.current_version})")

                # Inicia o jogo
                if self.launch_game():
                    print("\n💡 Dica: Você já pode fechar este launcher!")
                else:
                    print("\n❌ Falha ao iniciar o jogo!")

                input("\nPressione ENTER para sair...")
                break

            elif choice == "2":
                release = self.get_latest_release()
                if release:
                    print(f"\n📦 Versão no GitHub: {release['version']}")
                    print(f"📦 Versão instalada: {self.current_version}")

                    if release["version"] > self.current_version:
                        print(f"\n✨ Atualização disponível!")
                        if release['changelog']:
                            print(f"\n📝 Novidades:\n{release['changelog'][:300]}")

                        update = input("\n   Deseja atualizar? (S/N): ").upper().strip()
                        if update == "S":
                            if self.download_game(release["download_url"]):
                                version_file = self.game_dir / "game_version.txt"
                                version_file.write_text(release["version"])
                                self.current_version = release["version"]
                                print(f"\n✅ Atualizado para versão {release['version']}!")
                            else:
                                print("\n❌ Falha na atualização!")
                    elif release["version"] == self.current_version:
                        print("\n✅ Já está na versão mais recente!")
                    else:
                        print("\n🤔 Versão local é mais nova que a remota?")

                    input("\nPressione ENTER para continuar...")
                else:
                    print("\n❌ Não foi possível verificar versão!")
                    input("\nPressione ENTER para continuar...")

            elif choice == "3":
                print("\n👋 Até logo!")
                break

            else:
                print("\n❌ Opção inválida!")
                input("Pressione ENTER...")

if __name__ == "__main__":
    launcher = PokemonTDLauncher()
    launcher.run()