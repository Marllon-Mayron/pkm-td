"""
LAUNCHER DEFINITIVO POKEMON TD - COM EXECUTAVEL
Gera o executavel do jogo automaticamente, sem precisar de Python
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
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
import webbrowser

# Configuracao
GITHUB_REPO = "Marllon-Mayron/pkm-td"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"


def center_window(window, width, height):
    """Centraliza uma janela na tela"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


class ModernDialog:
    """Classe para criar dialogs padronizados"""

    @staticmethod
    def create(parent, title, width=500, height=400):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.minsize(width, height)
        dialog.transient(parent)
        dialog.grab_set()
        dialog.configure(bg='#1e1e1e')
        center_window(dialog, width, height)
        return dialog

    @staticmethod
    def show_update_dialog(parent, current_version, new_version, changelog, on_update):
        dialog = ModernDialog.create(parent, "Atualizacao Disponivel", 550, 480)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Nova Versao Disponivel",
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Label(info_frame, text=f"Versao atual:  {current_version}",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Nova versao:   {new_version}",
                 font=("Segoe UI", 11, "bold"), foreground="#0078d4").pack(anchor=tk.W, pady=2)

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        ttk.Label(main_frame, text="Novidades:", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        changelog_frame = ttk.Frame(main_frame)
        changelog_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        changelog_text = tk.Text(changelog_frame, wrap=tk.WORD,
                                font=("Consolas", 9),
                                bg='#252526', fg='#d4d4d4',
                                relief=tk.FLAT, borderwidth=1)
        changelog_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        changelog_text.insert(tk.END, changelog)
        changelog_text.config(state='disabled')

        scrollbar = ttk.Scrollbar(changelog_frame, command=changelog_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        changelog_text.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Atualizar Agora", command=lambda: [dialog.destroy(), on_update()],
                  width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy,
                  width=18).pack(side=tk.LEFT, padx=5)

        return dialog

    @staticmethod
    def show_offline_dialog(parent, versions, current_version, on_play):
        dialog = ModernDialog.create(parent, "Modo Offline", 400, 350)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Modo Offline",
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        ttk.Label(main_frame, text="Versoes disponiveis para jogar:",
                 font=("Segoe UI", 10)).pack()

        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        listbox = tk.Listbox(listbox_frame, height=6, font=("Segoe UI", 10),
                            bg='#252526', fg='#d4d4d4', selectbackground='#0078d4')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)

        for ver in versions:
            listbox.insert(tk.END, f"Versao {ver}")

        if current_version != "0.0.0":
            listbox.insert(tk.END, f"Versao {current_version} (atual)")

        def use_selected():
            selection = listbox.curselection()
            if selection:
                selected = listbox.get(selection[0])
                ver = selected.split()[1]
                dialog.destroy()
                on_play(ver)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Jogar", command=use_selected,
                  width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy,
                  width=15).pack(side=tk.LEFT, padx=5)

        return dialog


class PokemonTDLauncher:
    def __init__(self):
        self.launcher_dir = Path(sys.argv[0]).parent
        self.game_dir = self.launcher_dir / "PokemonTD"
        self.versions_dir = self.launcher_dir / "Versions"
        self.current_version = self.get_local_version()
        self.offline_mode = False
        self.latest_release = None
        self.is_downloading = False
        self.saves_backup_temp = None

        # Interface
        self.root = None
        self.status_var = None
        self.progress_var = None
        self.progress_bar = None
        self.version_label = None
        self.log_text = None
        self.play_btn = None
        self.check_btn = None
        self.download_btn = None
        self.offline_btn = None

    def add_log(self, message, level="INFO"):
        """Adiciona mensagem ao console de logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        color_tags = {
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "SUCCESS": "success"
        }

        tag = color_tags.get(level, "info")
        log_message = f"[{timestamp}] {message}\n"

        if self.log_text:
            self.log_text.insert(tk.END, log_message, tag)
            self.log_text.see(tk.END)
            self.root.update()

        print(log_message.strip())

    def set_buttons_state(self, enabled):
        """Habilita ou desabilita botoes durante download"""
        state = 'normal' if enabled else 'disabled'
        if self.play_btn:
            self.play_btn.config(state=state)
        if self.check_btn:
            self.check_btn.config(state=state)
        if self.download_btn:
            self.download_btn.config(state=state)
        if self.offline_btn:
            self.offline_btn.config(state=state)

    def backup_saves_preserve(self):
        """PRESERVA os saves do usuario"""
        saves_path = self.game_dir / "src" / "saves"

        if saves_path.exists() and any(saves_path.iterdir()):
            save_files = list(saves_path.glob("*.json")) + list(saves_path.glob("*.dat")) + list(saves_path.rglob("*"))
            save_count = len([f for f in save_files if f.is_file()])

            import tempfile
            self.saves_backup_temp = tempfile.mkdtemp(prefix="pokemon_saves_")
            backup_path = Path(self.saves_backup_temp)

            for file in saves_path.iterdir():
                if file.is_file():
                    shutil.copy2(file, backup_path / file.name)

            self.add_log(f"SAVES PRESERVADOS: {save_count} arquivos salvos", "SUCCESS")
            return True

        self.add_log("Nenhum save encontrado para preservar", "INFO")
        return False

    def restore_saves_preserve(self):
        """RESTAURA os saves do usuario"""
        saves_path = self.game_dir / "src" / "saves"

        saves_path.mkdir(parents=True, exist_ok=True)

        if self.saves_backup_temp:
            backup_path = Path(self.saves_backup_temp)
            if backup_path.exists():
                restored_count = 0
                for file in backup_path.iterdir():
                    if file.is_file():
                        dest = saves_path / file.name
                        shutil.copy2(file, dest)
                        restored_count += 1

                shutil.rmtree(self.saves_backup_temp)
                self.saves_backup_temp = None

                self.add_log(f"SAVES RESTAURADOS: {restored_count} arquivos recuperados", "SUCCESS")
                return True

        self.add_log("Nenhum save para restaurar", "INFO")
        return False

    def get_local_version(self):
        """Le a versao instalada localmente"""
        version_file = self.game_dir / "game_version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.0.0"

    def get_installed_versions(self):
        """Lista todas as versoes instaladas disponiveis"""
        versions = []
        if self.versions_dir.exists():
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir() and version_dir.name != self.current_version:
                    versions.append(version_dir.name)
        return sorted(versions, reverse=True)

    def get_latest_release(self):
        """Pega informacoes da ultima release do GitHub"""
        try:
            self.add_log("Conectando ao GitHub...", "INFO")

            req = urlopen(GITHUB_API, timeout=10)
            data = json.loads(req.read().decode())

            version = data.get("tag_name", "0.0.0")
            if version.startswith('v'):
                version = version[1:]

            zip_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/v{version}.zip"
            changelog = data.get("body", "Sem descricao")

            self.add_log(f"Versao remota: {version}", "INFO")

            return {
                "version": version,
                "download_url": zip_url,
                "changelog": changelog,
                "is_newer": version > self.current_version
            }
        except URLError:
            self.add_log("Sem conexao com a internet", "WARNING")
            self.offline_mode = True
            return None
        except Exception as e:
            self.add_log(f"Erro: {e}", "ERROR")
            return None

    def build_executable(self, game_path):
        """Compila o jogo em executavel usando PyInstaller"""
        try:
            self.add_log("Compilando executavel do jogo...", "INFO")
            self.progress_var.set("Compilando executavel...")

            # Salva diretorio atual
            original_dir = os.getcwd()
            os.chdir(game_path)

            # Cria script batch para compilar
            build_script = game_path / "compile_game.bat"
            build_script.write_text(f"""@echo off
chcp 65001 >nul
echo Compilando Pokemon Tower Defense...
echo.

REM Instalar PyInstaller se necessario
pip install pyinstaller >nul 2>&1

REM Compilar o jogo
python -m PyInstaller --onefile --noconsole --name "PokemonTowerDefense" --add-data "src;src" --add-data "res;res" --hidden-import pygame src/main.py

if errorlevel 1 (
    echo ERRO na compilacao
    exit /b 1
)

echo SUCCESSO
exit /b 0
""")

            # Executa a compilacao
            result = subprocess.run(
                ['cmd', '/c', str(build_script)],
                capture_output=True,
                text=True,
                timeout=300
            )

            os.chdir(original_dir)

            # Verifica se o executavel foi criado
            exe_path = game_path / "dist" / "PokemonTowerDefense.exe"
            if exe_path.exists():
                # Move para a raiz do jogo
                final_exe = game_path / "PokemonTowerDefense.exe"
                if final_exe.exists():
                    final_exe.unlink()
                shutil.move(str(exe_path), str(final_exe))

                # Limpa arquivos temporarios
                for item in ["build", "dist", "compile_game.bat", "PokemonTowerDefense.spec"]:
                    path = game_path / item
                    if path.exists():
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()

                self.add_log("Executavel criado com sucesso!", "SUCCESS")
                return True

            self.add_log("Falha ao criar executavel", "ERROR")
            return False

        except subprocess.TimeoutExpired:
            self.add_log("Tempo esgotado na compilacao", "ERROR")
            return False
        except Exception as e:
            self.add_log(f"Erro na compilacao: {e}", "ERROR")
            return False

    def find_executable(self):
        """Procura o executavel do jogo"""
        exe_path = self.game_dir / "PokemonTowerDefense.exe"
        if exe_path.exists():
            return exe_path
        return None

    def download_version(self, version_info):
        """Baixa uma versao especifica e compila o executavel"""
        try:
            self.is_downloading = True
            self.set_buttons_state(False)

            self.add_log(f"Baixando versao {version_info['version']}...", "INFO")

            if self.game_dir.exists():
                self.backup_saves_preserve()

            self.progress_bar['value'] = 0
            self.progress_var.set("Baixando...")

            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.close()

            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    progress = (block_num * block_size) / total_size * 100
                    self.progress_bar['value'] = progress
                    self.progress_var.set(f"Baixando: {progress:.1f}%")
                    self.root.update()

            urlretrieve(version_info["download_url"], temp_zip.name, reporthook=report_progress)

            version_path = self.versions_dir / version_info["version"]
            if version_path.exists():
                shutil.rmtree(version_path)
            version_path.mkdir(parents=True)

            self.add_log("Extraindo arquivos...", "INFO")
            self.progress_var.set("Extraindo arquivos...")
            self.progress_bar['value'] = 0

            with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                root_folder = None
                for name in zip_ref.namelist():
                    if '/' in name:
                        root_folder = name.split('/')[0]
                        break

                files = zip_ref.namelist()
                total_files = len(files)

                for i, member in enumerate(files):
                    if '__MACOSX' in member or '.DS_Store' in member:
                        continue

                    if root_folder and member.startswith(root_folder):
                        relative_path = member[len(root_folder)+1:]
                        if relative_path:
                            target = version_path / relative_path
                            if member.endswith('/'):
                                target.mkdir(parents=True, exist_ok=True)
                            else:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as src, open(target, 'wb') as dst:
                                    shutil.copyfileobj(src, dst)

                    progress = (i / total_files) * 100
                    self.progress_bar['value'] = progress
                    self.root.update()

            os.unlink(temp_zip.name)

            # COMPILAR EXECUTAVEL
            self.add_log("Compilando executavel...", "INFO")
            self.progress_var.set("Compilando executavel (pode levar alguns minutos)...")
            self.progress_bar['value'] = 0

            if not self.build_executable(version_path):
                self.add_log("Falha na compilacao do executavel", "ERROR")
                return False

            # Salva informacoes da versao
            (version_path / "game_version.txt").write_text(version_info["version"])

            if version_info.get("changelog"):
                (version_path / "changelog.txt").write_text(version_info["changelog"])

            self.add_log("Download e compilacao concluidos", "SUCCESS")
            self.progress_var.set("Pronto")
            return True

        except Exception as e:
            self.add_log(f"Erro no download: {e}", "ERROR")
            self.progress_var.set("Erro no download")
            return False
        finally:
            self.is_downloading = False
            self.set_buttons_state(True)
            self.progress_bar['value'] = 0

    def set_current_version(self, version):
        """Define a versao atual PRESERVANDO saves"""
        version_path = self.versions_dir / version

        if not version_path.exists():
            self.add_log(f"Versao {version} nao encontrada", "ERROR")
            return False

        self.add_log(f"Trocando para versao {version}...", "INFO")

        if self.game_dir.exists():
            shutil.rmtree(self.game_dir)

        shutil.copytree(version_path, self.game_dir)

        self.restore_saves_preserve()

        self.current_version = version

        if self.version_label:
            self.version_label.config(text=f"Versao: {self.current_version}")

        self.add_log(f"Versao {version} carregada com seus saves!", "SUCCESS")
        return True

    def launch_game(self):
        """Inicia o jogo usando o executavel compilado ou fallback"""
        if self.is_downloading:
            self.add_log("Aguarde o download terminar", "WARNING")
            messagebox.showwarning("Download em andamento", "Aguarde o download terminar antes de jogar.")
            return

        # Primeiro tenta usar o executavel
        exe_path = self.find_executable()

        if exe_path and exe_path.exists():
            self.add_log("Iniciando jogo (executavel)...", "INFO")
            self.root.destroy()
            subprocess.Popen([str(exe_path)], shell=True)
            sys.exit(0)

        # Fallback: tenta com Python (caso compilacao falhe)
        main_py = self.find_main_py()
        if main_py:
            self.add_log("Executavel nao encontrado, tentando modo Python...", "WARNING")
            self.add_log("Nota: Pode ser necessario ter Python instalado", "WARNING")

            batch_file = self.launcher_dir / "run_game_temp.bat"
            batch_content = f"""@echo off
cd /d "{self.game_dir}"
python "{main_py}"
"""
            batch_file.write_text(batch_content)

            self.root.destroy()
            subprocess.Popen([str(batch_file)], shell=True)
            sys.exit(0)

        self.add_log("Jogo nao encontrado", "ERROR")
        messagebox.showerror("Erro", "Jogo nao encontrado!\nUse BAIXAR para instalar.")

    def find_main_py(self):
        """Procura o arquivo principal do jogo (fallback)"""
        possible_paths = [
            self.game_dir / "src" / "main.py",
            self.game_dir / "main.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path
        return None

    def check_for_updates(self):
        """Apenas VERIFICA se tem atualizacao"""
        if self.is_downloading:
            self.add_log("Aguarde o download terminar", "WARNING")
            messagebox.showwarning("Download em andamento", "Aguarde o download terminar.")
            return

        self.add_log("=== VERIFICANDO ATUALIZACOES ===", "INFO")

        release = self.get_latest_release()

        if self.offline_mode:
            self.add_log("Modo offline ativado", "WARNING")
            self.show_offline_options()
            return

        if not release:
            self.add_log("Erro ao conectar ao GitHub", "ERROR")
            messagebox.showerror("Erro", "Nao foi possivel conectar ao GitHub")
            return

        if release["is_newer"]:
            self.latest_release = release
            self.add_log(f"Nova versao encontrada: {release['version']}", "INFO")

            ModernDialog.show_update_dialog(
                self.root,
                self.current_version,
                release['version'],
                release['changelog'],
                lambda: self.start_download()
            )
        else:
            self.add_log("Jogo atualizado", "SUCCESS")
            if not self.find_executable() and not self.find_main_py():
                self.add_log("Jogo nao encontrado! Use o botao BAIXAR.", "WARNING")
                messagebox.showwarning("Jogo nao encontrado",
                    "Nenhuma versao do jogo encontrada!\n\nClique em BAIXAR para instalar.")
            else:
                messagebox.showinfo("Atualizado", f"Versao {self.current_version} esta atualizada!")

    def start_download(self):
        """Inicia o download"""
        if self.is_downloading:
            return

        if self.latest_release:
            threading.Thread(target=self.perform_update, daemon=True).start()

    def force_download(self):
        """FORCA o download da versao mais recente"""
        if self.is_downloading:
            self.add_log("Download em andamento", "WARNING")
            messagebox.showwarning("Download em andamento", "Ja existe um download em andamento.")
            return

        self.add_log("=== FORCANDO DOWNLOAD DA ULTIMA VERSAO ===", "INFO")

        release = self.get_latest_release()

        if not release:
            self.add_log("Erro ao obter versao do GitHub", "ERROR")
            messagebox.showerror("Erro", "Nao foi possivel obter informacoes do GitHub")
            return

        self.latest_release = release

        msg = f"Deseja baixar a versao {release['version']}?\n\n"
        if release['changelog']:
            msg += f"Novidades:\n{release['changelog'][:200]}"

        if messagebox.askyesno("Confirmar Download", msg):
            threading.Thread(target=self.perform_update, daemon=True).start()

    def perform_update(self):
        """Executa o download e compilacao"""
        if not self.latest_release:
            self.latest_release = self.get_latest_release()
            if not self.latest_release:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao obter versao"))
                return

        self.add_log(f"Atualizando para versao {self.latest_release['version']}", "INFO")

        success = self.download_version(self.latest_release)

        if success:
            result = self.set_current_version(self.latest_release['version'])
            if result:
                self.root.after(0, lambda: messagebox.showinfo("Sucesso",
                    f"Versao {self.latest_release['version']} instalada!\n\nO jogo foi compilado e nao precisa de Python.\n\nSeus saves foram preservados!"))
                self.add_log("Download e compilacao concluidos com sucesso", "SUCCESS")
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao ativar versao"))
        else:
            self.root.after(0, lambda: messagebox.showerror("Erro", "Falha no download"))

    def show_offline_options(self):
        """Mostra opcoes para modo offline"""
        if self.is_downloading:
            self.add_log("Aguarde o download terminar", "WARNING")
            return

        installed_versions = self.get_installed_versions()

        if installed_versions:
            self.add_log(f"Versoes disponiveis: {', '.join(installed_versions)}", "INFO")

            def on_play(version):
                if version == self.current_version:
                    self.launch_game()
                else:
                    if self.game_dir.exists():
                        self.backup_saves_preserve()

                    if self.set_current_version(version):
                        messagebox.showinfo("Sucesso", f"Versao {version} carregada!\nSeus saves foram preservados!")
                        self.launch_game()
                    else:
                        messagebox.showerror("Erro", "Falha ao carregar versao")

            ModernDialog.show_offline_dialog(
                self.root, installed_versions, self.current_version, on_play
            )
        else:
            self.add_log("Nenhuma versao instalada", "WARNING")
            messagebox.showwarning("Sem Jogo",
                "Nenhuma versao do jogo encontrada!\n\nConecte-se a internet e clique em BAIXAR.")

    def open_github(self):
        """Abre pagina do GitHub"""
        webbrowser.open(GITHUB_RELEASES)
        self.add_log("Abrindo GitHub", "INFO")

    def create_gui(self):
        """Cria a interface grafica"""
        self.root = tk.Tk()
        self.root.title("Pokemon Tower Defense - Launcher")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use('clam')

        bg_color = "#1e1e1e"
        fg_color = "#d4d4d4"
        accent_color = "#0078d4"

        self.root.configure(bg=bg_color)

        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        style.configure("TButton", background="#333333", foreground=fg_color, borderwidth=0, focuscolor="none", padding=8)
        style.map("TButton", background=[("active", accent_color)])
        style.configure("TProgressbar", thickness=10, background=accent_color)

        main_container = ttk.Frame(self.root, padding="25")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Cabecalho
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame, text="POKEMON TOWER DEFENSE",
                               font=("Segoe UI", 26, "bold"))
        title_label.pack()

        subtitle_label = ttk.Label(header_frame, text="Launcher Oficial - Gerenciamento de Versoes",
                                  font=("Segoe UI", 11))
        subtitle_label.pack(pady=(5, 0))

        # Painel de informacoes
        info_panel = ttk.Frame(main_container)
        info_panel.pack(fill=tk.X, pady=15)

        version_card = ttk.Frame(info_panel, relief=tk.RAISED, borderwidth=1)
        version_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.version_label = ttk.Label(version_card, text=f"Versao: {self.current_version}",
                                      font=("Segoe UI", 14, "bold"))
        self.version_label.pack(pady=15)

        # Separador
        separator = ttk.Separator(main_container, orient='horizontal')
        separator.pack(fill=tk.X, pady=15)

        # Barra de progresso
        progress_frame = ttk.Frame(main_container)
        progress_frame.pack(fill=tk.X, pady=10)

        self.progress_var = tk.StringVar(value="Pronto")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var,
                                  font=("Segoe UI", 9), foreground="#888888")
        progress_label.pack()

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=850)
        self.progress_bar.pack(pady=5, fill=tk.X)

        # Console de logs
        log_frame = ttk.LabelFrame(main_container, text="Console de Logs", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(text_container, height=14,
                               bg='#252526', fg='#d4d4d4',
                               font=("Consolas", 9),
                               relief=tk.FLAT, borderwidth=0,
                               wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_text.tag_config("info", foreground="#d4d4d4")
        self.log_text.tag_config("warning", foreground="#ffcc66")
        self.log_text.tag_config("error", foreground="#ff6666")
        self.log_text.tag_config("success", foreground="#66cc66")

        scrollbar = ttk.Scrollbar(text_container, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Botoes principais
        buttons_container = ttk.Frame(main_container)
        buttons_container.pack(fill=tk.X, pady=15)

        button_style = {"width": 16}

        self.play_btn = ttk.Button(buttons_container, text="JOGAR",
                                   command=self.launch_game, **button_style)
        self.play_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.check_btn = ttk.Button(buttons_container, text="VERIFICAR",
                                    command=self.check_for_updates, **button_style)
        self.check_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.download_btn = ttk.Button(buttons_container, text="BAIXAR",
                                       command=self.force_download, **button_style)
        self.download_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Botoes secundarios
        secondary_container = ttk.Frame(main_container)
        secondary_container.pack(fill=tk.X, pady=10)

        sec_button_style = {"width": 12}

        github_btn = ttk.Button(secondary_container, text="GitHub",
                               command=self.open_github, **sec_button_style)
        github_btn.pack(side=tk.LEFT, padx=2)

        self.offline_btn = ttk.Button(secondary_container, text="OFFLINE",
                                      command=self.show_offline_options, **sec_button_style)
        self.offline_btn.pack(side=tk.LEFT, padx=2)

        exit_btn = ttk.Button(secondary_container, text="SAIR",
                             command=lambda: sys.exit(0), **sec_button_style)
        exit_btn.pack(side=tk.LEFT, padx=2)

        # Barra de informacao
        info_bar = ttk.Frame(main_container)
        info_bar.pack(fill=tk.X, pady=(10, 0))

        info_text = "Seus saves sao PRESERVADOS | O jogo e compilado em executavel (nao precisa de Python)"
        info_label = ttk.Label(info_bar, text=info_text,
                              font=("Segoe UI", 9), foreground="#00cc66")
        info_label.pack()

        center_window(self.root, 900, 750)

        # Logs iniciais
        self.add_log("Launcher inicializado", "INFO")
        self.add_log(f"Diretorio: {self.launcher_dir}", "INFO")
        self.add_log(f"Versao atual: {self.current_version}", "INFO")
        self.add_log("SISTEMA DE PRESERVACAO DE SAVES ATIVO", "SUCCESS")
        self.add_log("O jogo sera compilado em executavel - NAO precisa de Python instalado", "SUCCESS")

        if not self.find_executable() and not self.find_main_py():
            self.add_log("Jogo nao encontrado. Clique em BAIXAR para instalar", "WARNING")

    def run(self):
        """Inicia o launcher"""
        self.create_gui()
        self.root.mainloop()


if __name__ == "__main__":
    launcher = PokemonTDLauncher()
    launcher.run()