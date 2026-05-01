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
                # Remove o 'v' se existir (v1.0.0 -> 1.0.0)
                if version.startswith('v'):
                    version = version[1:]

                # Pega a URL do zip da release
                zip_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        zip_url = asset["browser_download_url"]
                        break

                # Se não tiver asset, usa o source code
                if not zip_url:
                    zip_url = data.get("zipball_url")

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
            print(f"\n📥 Baixando jogo...")

            # Cria arquivo temporário
            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.close()

            # Baixa o arquivo
            print(f"   🔗 Baixando de: {download_url[:50]}...")
            urlretrieve(download_url, temp_zip.name)

            # Remove jogo antigo se existir
            if self.game_dir.exists():
                print("   🗑️  Removendo versão antiga...")
                shutil.rmtree(self.game_dir)

            self.game_dir.mkdir(parents=True)

            # Extrai o zip
            print("   📦 Extraindo arquivos...")
            with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                # GitHub adiciona uma pasta raiz, precisamos extrair o conteúdo
                for member in zip_ref.namelist():
                    # Pula arquivos de sistema do macOS
                    if '__MACOSX' in member or member.startswith('.'):
                        continue

                    # Remove a primeira pasta do caminho (ex: Marllon-Mayron-pkm-td-abc123/src/main.py -> src/main.py)
                    parts = Path(member).parts
                    if len(parts) > 1:
                        # Pula a primeira parte (nome da pasta raiz do zip)
                        new_path = Path(*parts[1:])
                    else:
                        new_path = Path(member)

                    if new_path.name == '':  # É uma pasta
                        (self.game_dir / new_path).mkdir(parents=True, exist_ok=True)
                    else:
                        # Extrai o arquivo
                        target = self.game_dir / new_path
                        target.parent.mkdir(parents=True, exist_ok=True)

                        with zip_ref.open(member) as source, open(target, 'wb') as target_file:
                            shutil.copyfileobj(source, target_file)

            # Limpa o zip temporário
            os.unlink(temp_zip.name)

            return True

        except Exception as e:
            print(f"   ❌ Erro no download: {e}")
            return False

    def launch_game(self):
        """Inicia o jogo"""
        # Procura o main.py
        main_py = self.game_dir / "main.py"
        if not main_py.exists():
            # Tenta em src/main.py
            main_py = self.game_dir / "src" / "main.py"

        if not main_py.exists():
            print("\n❌ ERRO: Jogo não encontrado!")
            print("   Tente executar o launcher novamente.")
            input("\nPressione ENTER para sair...")
            return False

        print(f"\n🎮 Iniciando Pokémon TD...")

        # Muda para o diretório do jogo
        os.chdir(self.game_dir)

        # Executa o jogo
        if sys.platform == "win32":
            # Windows: abre sem console
            subprocess.Popen([sys.executable, str(main_py)],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # Linux/Mac
            subprocess.Popen([sys.executable, str(main_py)])

        return True

    def show_menu(self):
        """Mostra menu do launcher"""
        print("\n" + "=" * 50)
        print("     🎮 POKEMON TD - LAUNCHER")
        print("=" * 50)
        print(f"   📍 Versão instalada: {self.current_version}")
        print()
        print("   [1] Jogar")
        print("   [2] Verificar atualizações")
        print("   [3] Sair")
        print("=" * 50)

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
                    print(f"\n✨ Nova versão disponível: {release['version']}")
                    print(f"   Versão atual: {self.current_version}")

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

                # Inicia o jogo
                self.launch_game()
                print("\n💡 Dica: Você já pode fechar este launcher!")
                input("\nPressione ENTER para sair...")
                break

            elif choice == "2":
                release = self.get_latest_release()
                if release:
                    print(f"\n📦 Versão no GitHub: {release['version']}")
                    print(f"📦 Versão instalada: {self.current_version}")

                    if release["version"] > self.current_version:
                        print(f"\n✨ Atualização disponível!")
                        print(f"\n📝 Novidades:\n{release['changelog'][:200]}")

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
                        print("\n🤔 Versão local é mais nova que a remota? (teste)")

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