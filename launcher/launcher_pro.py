"""
LAUNCHER PROFISSIONAL POKEMON TD
Gerenciador de versoes com protecao de saves
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

        # Configurar estilo escuro
        dialog.configure(bg='#1e1e1e')

        # Centralizar
        center_window(dialog, width, height)

        return dialog

    @staticmethod
    def show_update_dialog(parent, current_version, new_version, changelog, on_update):
        dialog = ModernDialog.create(parent, "Atualizacao Disponivel", 550, 480)

        # Frame principal
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(header, text="Nova Versao Disponivel",
                 font=("Segoe UI", 16, "bold")).pack()

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Info versoes
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Label(info_frame, text=f"Versao atual:  {current_version}",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Nova versao:   {new_version}",
                 font=("Segoe UI", 11, "bold"), foreground="#0078d4").pack(anchor=tk.W, pady=2)

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Changelog
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

        # Botoes
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

    @staticmethod
    def show_confirm_dialog(parent, title, message, on_confirm):
        dialog = ModernDialog.create(parent, title, 400, 200)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=message,
                 font=("Segoe UI", 11), wraplength=350).pack(pady=20)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Sim", command=lambda: [dialog.destroy(), on_confirm()],
                  width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Nao", command=dialog.destroy,
                  width=12).pack(side=tk.LEFT, padx=5)

        return dialog


class PokemonTDLauncher:
    def __init__(self):
        self.launcher_dir = Path(sys.argv[0]).parent
        self.game_dir = self.launcher_dir / "PokemonTD"
        self.versions_dir = self.launcher_dir / "Versions"
        self.saves_backup_dir = self.launcher_dir / "SavesBackup"
        self.current_version = self.get_local_version()
        self.offline_mode = False
        self.latest_release = None
        self.is_updating = False

        # Interface
        self.root = None
        self.status_var = None
        self.progress_bar = None
        self.version_label = None
        self.log_text = None
        self.update_btn = None

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

    def backup_saves(self):
        """Faz backup da pasta de saves antes de atualizar"""
        saves_path = self.game_dir / "src" / "saves"
        if saves_path.exists() and any(saves_path.iterdir()):
            self.add_log("Fazendo backup dos saves...", "INFO")
            backup_path = self.saves_backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(saves_path, backup_path)
            self.add_log(f"Backup criado em: {backup_path}", "SUCCESS")
            return backup_path
        return None

    def restore_saves(self, backup_path=None):
        """Restaura os saves apos atualizacao"""
        saves_path = self.game_dir / "src" / "saves"

        if backup_path and backup_path.exists():
            if saves_path.exists():
                shutil.rmtree(saves_path)
            shutil.copytree(backup_path, saves_path)
            self.add_log("Saves restaurados com sucesso!", "SUCCESS")
            return True

        if self.saves_backup_dir.exists():
            backups = sorted(self.saves_backup_dir.glob("backup_*"), reverse=True)
            if backups:
                latest_backup = backups[0]
                if saves_path.exists():
                    shutil.rmtree(saves_path)
                shutil.copytree(latest_backup, saves_path)
                self.add_log(f"Saves restaurados do backup: {latest_backup.name}", "SUCCESS")
                return True

        if not saves_path.exists():
            saves_path.mkdir(parents=True)
            self.add_log("Pasta de saves criada", "INFO")

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
            with urlopen(GITHUB_API, timeout=10) as response:
                data = json.loads(response.read().decode())

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

    def download_version(self, version_info):
        """Baixa uma versao especifica protegendo saves"""
        backup_path = None
        try:
            self.is_updating = True
            self.add_log(f"Baixando versao {version_info['version']}...", "INFO")

            if self.game_dir.exists():
                backup_path = self.backup_saves()

            self.update_btn.config(state='disabled')
            self.progress_bar['value'] = 0

            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.close()

            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    progress = (block_num * block_size) / total_size * 100
                    self.progress_bar['value'] = progress
                    self.root.update()

            urlretrieve(version_info["download_url"], temp_zip.name, reporthook=report_progress)

            version_path = self.versions_dir / version_info["version"]
            if version_path.exists():
                shutil.rmtree(version_path)
            version_path.mkdir(parents=True)

            self.add_log("Extraindo arquivos...", "INFO")
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
            (version_path / "game_version.txt").write_text(version_info["version"])

            if version_info.get("changelog"):
                (version_path / "changelog.txt").write_text(version_info["changelog"])

            self.add_log("Download concluido", "SUCCESS")
            return True, backup_path

        except Exception as e:
            self.add_log(f"Erro no download: {e}", "ERROR")
            return False, backup_path
        finally:
            self.is_updating = False
            self.update_btn.config(state='normal')
            self.progress_bar['value'] = 0

    def set_current_version(self, version, backup_path=None):
        """Define a versao atual protegendo saves"""
        version_path = self.versions_dir / version

        if not version_path.exists():
            self.add_log(f"Versao {version} nao encontrada", "ERROR")
            return False

        self.add_log(f"Trocando para versao {version}...", "INFO")

        if self.game_dir.exists():
            self.backup_saves()

        if self.game_dir.exists():
            shutil.rmtree(self.game_dir)

        shutil.copytree(version_path, self.game_dir)

        if backup_path:
            self.restore_saves(backup_path)
        else:
            self.restore_saves()

        self.current_version = version

        if self.version_label:
            self.version_label.config(text=f"Versao: {self.current_version}")

        self.add_log(f"Versao {version} carregada", "SUCCESS")
        return True

    def find_main_py(self):
        """Procura o arquivo principal do jogo"""
        possible_paths = [
            self.game_dir / "src" / "main.py",
            self.game_dir / "main.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path
        return None

    def launch_game(self):
        """Inicia o jogo"""
        main_py = self.find_main_py()

        if not main_py:
            self.add_log("Jogo nao encontrado", "ERROR")
            messagebox.showerror("Erro", "Jogo nao encontrado!\nUse Verificar para baixar.")
            return

        self.add_log("Iniciando jogo...", "INFO")

        batch_file = self.launcher_dir / "run_game_temp.bat"
        batch_content = f"""@echo off
cd /d "{self.game_dir}"
python "{main_py}"
"""
        batch_file.write_text(batch_content)

        self.root.destroy()
        subprocess.Popen([str(batch_file)], shell=True)
        sys.exit(0)

    def check_for_updates(self):
        """Verifica por atualizacoes"""
        if self.is_updating:
            self.add_log("Atualizacao em andamento", "WARNING")
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

            # Usa o dialog padronizado
            ModernDialog.show_update_dialog(
                self.root,
                self.current_version,
                release['version'],
                release['changelog'],
                lambda: threading.Thread(target=self.perform_update, daemon=True).start()
            )
        else:
            self.add_log("Jogo atualizado", "SUCCESS")
            if not self.find_main_py():
                self.add_log("Jogo nao encontrado, baixando...", "WARNING")
                ModernDialog.show_confirm_dialog(
                    self.root,
                    "Jogo nao encontrado",
                    "Nenhuma versao do jogo encontrada. Deseja baixar agora?",
                    lambda: threading.Thread(target=self.perform_update, daemon=True).start()
                )
            else:
                messagebox.showinfo("Atualizado", f"Versao {self.current_version} esta atualizada!")

    def perform_update(self):
        """Executa a atualizacao"""
        if not self.latest_release:
            self.latest_release = self.get_latest_release()
            if not self.latest_release:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao obter versao"))
                return

        self.add_log(f"Atualizando para versao {self.latest_release['version']}", "INFO")

        success, backup_path = self.download_version(self.latest_release)

        if success:
            result = self.set_current_version(self.latest_release['version'], backup_path)
            if result:
                self.root.after(0, lambda: messagebox.showinfo("Sucesso",
                    f"Atualizado para versao {self.latest_release['version']}!"))
                self.add_log("Atualizacao concluida", "SUCCESS")
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao ativar versao"))
        else:
            self.root.after(0, lambda: messagebox.showerror("Erro", "Falha na atualizacao"))

    def show_offline_options(self):
        """Mostra opcoes para modo offline"""
        installed_versions = self.get_installed_versions()

        if installed_versions:
            self.add_log(f"Versoes disponiveis: {', '.join(installed_versions)}", "INFO")

            def on_play(version):
                if version == self.current_version:
                    self.launch_game()
                else:
                    if self.set_current_version(version):
                        messagebox.showinfo("Sucesso", f"Versao {version} carregada!")
                        self.launch_game()
                    else:
                        messagebox.showerror("Erro", "Falha ao carregar versao")

            ModernDialog.show_offline_dialog(
                self.root, installed_versions, self.current_version, on_play
            )
        else:
            self.add_log("Nenhuma versao instalada", "WARNING")
            messagebox.showwarning("Sem Jogo",
                "Nenhuma versao do jogo encontrada!\n\nConecte-se a internet e clique em Verificar.")

    def open_github(self):
        """Abre pagina do GitHub"""
        webbrowser.open(GITHUB_RELEASES)
        self.add_log("Abrindo GitHub", "INFO")

    def create_gui(self):
        """Cria a interface grafica moderna e responsiva"""
        self.root = tk.Tk()
        self.root.title("Pokemon Tower Defense - Launcher")
        self.root.geometry("850x700")
        self.root.minsize(750, 600)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Configurar estilo moderno
        style = ttk.Style()
        style.theme_use('clam')

        # Cores
        bg_color = "#1e1e1e"
        fg_color = "#d4d4d4"
        accent_color = "#0078d4"

        self.root.configure(bg=bg_color)

        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        style.configure("TButton", background="#333333", foreground=fg_color, borderwidth=0, focuscolor="none", padding=6)
        style.map("TButton", background=[("active", accent_color)])
        style.configure("TProgressbar", thickness=8, background=accent_color)

        # Container principal
        main_container = ttk.Frame(self.root, padding="25")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Cabecalho
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame, text="POKEMON TOWER DEFENSE",
                               font=("Segoe UI", 24, "bold"))
        title_label.pack()

        subtitle_label = ttk.Label(header_frame, text="Launcher Oficial - Gerenciamento de Versoes",
                                  font=("Segoe UI", 10))
        subtitle_label.pack(pady=(5, 0))

        # Painel de informacoes
        info_panel = ttk.Frame(main_container)
        info_panel.pack(fill=tk.X, pady=15)

        # Card de versao
        version_card = ttk.Frame(info_panel, relief=tk.RAISED, borderwidth=1)
        version_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.version_label = ttk.Label(version_card, text=f"Versao: {self.current_version}",
                                      font=("Segoe UI", 13, "bold"))
        self.version_label.pack(pady=15)

        # Separador
        separator = ttk.Separator(main_container, orient='horizontal')
        separator.pack(fill=tk.X, pady=15)

        # Console de logs
        log_frame = ttk.LabelFrame(main_container, text="Console de Logs", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Frame para texto e scrollbar
        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(text_container, height=14,
                               bg='#252526', fg='#d4d4d4',
                               font=("Consolas", 9),
                               relief=tk.FLAT, borderwidth=0,
                               wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configurar tags de cor
        self.log_text.tag_config("info", foreground="#d4d4d4")
        self.log_text.tag_config("warning", foreground="#ffcc66")
        self.log_text.tag_config("error", foreground="#ff6666")
        self.log_text.tag_config("success", foreground="#66cc66")

        scrollbar = ttk.Scrollbar(text_container, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Barra de progresso
        progress_container = ttk.Frame(main_container)
        progress_container.pack(fill=tk.X, pady=10)

        self.progress_bar = ttk.Progressbar(progress_container, mode='determinate', length=800)
        self.progress_bar.pack(fill=tk.X)

        # Status
        self.status_var = tk.StringVar(value="Pronto")
        status_label = ttk.Label(progress_container, textvariable=self.status_var,
                                font=("Segoe UI", 9), foreground="#888888")
        status_label.pack(pady=(8, 0))

        # Botoes principais
        buttons_container = ttk.Frame(main_container)
        buttons_container.pack(fill=tk.X, pady=15)

        button_style = {"width": 18}

        play_btn = ttk.Button(buttons_container, text="JOGAR",
                             command=self.launch_game, **button_style)
        play_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.update_btn = ttk.Button(buttons_container, text="VERIFICAR",
                                     command=self.check_for_updates, **button_style)
        self.update_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        force_btn = ttk.Button(buttons_container, text="BAIXAR",
                              command=lambda: threading.Thread(target=self.perform_update, daemon=True).start(),
                              **button_style)
        force_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Botoes secundarios
        secondary_container = ttk.Frame(main_container)
        secondary_container.pack(fill=tk.X, pady=10)

        sec_button_style = {"width": 12}

        github_btn = ttk.Button(secondary_container, text="GitHub",
                               command=self.open_github, **sec_button_style)
        github_btn.pack(side=tk.LEFT, padx=2)

        offline_btn = ttk.Button(secondary_container, text="OFFLINE",
                                command=self.show_offline_options, **sec_button_style)
        offline_btn.pack(side=tk.LEFT, padx=2)

        exit_btn = ttk.Button(secondary_container, text="SAIR",
                             command=lambda: sys.exit(0), **sec_button_style)
        exit_btn.pack(side=tk.LEFT, padx=2)

        # Barra de informacao
        info_bar = ttk.Frame(main_container)
        info_bar.pack(fill=tk.X, pady=(10, 0))

        info_text = "Saves sao preservados automaticamente durante atualizacoes"
        info_label = ttk.Label(info_bar, text=info_text,
                              font=("Segoe UI", 8), foreground="#666666")
        info_label.pack()

        # Centralizar janela principal
        center_window(self.root, 850, 700)

        # Logs iniciais
        self.add_log("Launcher inicializado", "INFO")
        self.add_log(f"Diretorio: {self.launcher_dir}", "INFO")
        self.add_log(f"Versao atual: {self.current_version}", "INFO")

        if not self.find_main_py():
            self.add_log("Jogo nao encontrado. Clique em VERIFICAR para baixar", "WARNING")

    def run(self):
        """Inicia o launcher"""
        self.create_gui()
        self.root.mainloop()


if __name__ == "__main__":
    launcher = PokemonTDLauncher()
    launcher.run()