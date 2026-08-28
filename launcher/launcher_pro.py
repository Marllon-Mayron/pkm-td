
"""
LAUNCHER POKEMON TD - PRESERVAÇÃO GARANTIDA DE SAVES v3
Corrige o caminho dos saves (agora em PokemonTD/saves)
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
import ctypes
import re
import time

# Configuracao
GITHUB_REPO = "Marllon-Mayron/pkm-td"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"

# URL do Python 3.12 especifico
PYTHON_312_URL = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
PYTHON_312_VERSION = "3.12.0"


def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


class ModernDialog:
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
    def show_python_selection_dialog(parent, python_versions, on_select):
        dialog = ModernDialog.create(parent, "Selecionar Python", 500, 400)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Versoes Python Encontradas",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        ttk.Label(main_frame, text="Selecione qual versao Python 3.12 usar:",
                 font=("Segoe UI", 10)).pack()

        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=15)

        listbox = tk.Listbox(listbox_frame, height=6, font=("Segoe UI", 11),
                            bg='#252526', fg='#d4d4d4', selectbackground='#0078d4')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)

        for ver in python_versions:
            listbox.insert(tk.END, ver)

        ttk.Label(main_frame, text="NOTA: O jogo REQUER Python 3.12",
                 font=("Segoe UI", 9), foreground="#ffcc66").pack(pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        def use_selected():
            selection = listbox.curselection()
            if selection:
                selected = listbox.get(selection[0])
                parts = selected.split(' - ')
                python_path = parts[0] if len(parts) > 1 else selected
                dialog.destroy()
                on_select(python_path)

        ttk.Button(btn_frame, text="Usar Esta Versao", command=use_selected,
                  width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Instalar Python 3.12",
                  command=lambda: [dialog.destroy(), on_select("install")],
                  width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Cancelar", command=sys.exit,
                  width=18).pack(side=tk.LEFT, padx=5)

        return dialog

    @staticmethod
    def show_install_dialog(parent, on_confirm):
        dialog = ModernDialog.create(parent, "Instalacao Necessaria", 550, 400)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Python 3.12 Necessario",
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 10))

        ttk.Label(main_frame, text="O Pokemon Tower Defense REQUER Python 3.12",
                 font=("Segoe UI", 11), foreground="#ffcc66").pack()

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Label(info_frame, text="Vamos instalar:",
                 font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)

        ttk.Label(info_frame, text="  • Python 3.12.0 (versao especifica do jogo)",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=5)
        ttk.Label(info_frame, text="  • Pygame (biblioteca do jogo)",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=2)

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        ttk.Label(main_frame, text="A instalacao e automatica e necessaria apenas uma vez.",
                 font=("Segoe UI", 9), foreground="#888888").pack()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        def confirm():
            dialog.destroy()
            on_confirm()

        ttk.Button(btn_frame, text="Instalar Python 3.12", command=confirm,
                  width=22).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Sair", command=sys.exit,
                  width=15).pack(side=tk.LEFT, padx=5)

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

    @staticmethod
    def show_download_progress_dialog(parent, on_cancel):
        """Mostra um diálogo de progresso durante o download"""
        dialog = ModernDialog.create(parent, "Baixando Jogo", 500, 250)

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Download em andamento...",
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        status_label = ttk.Label(main_frame, text="Iniciando download...",
                                font=("Segoe UI", 11))
        status_label.pack(pady=5)

        progress_bar = ttk.Progressbar(main_frame, mode='determinate', length=450)
        progress_bar.pack(pady=10)

        detail_label = ttk.Label(main_frame, text="",
                                font=("Segoe UI", 9), foreground="#888888")
        detail_label.pack(pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        cancel_btn = ttk.Button(btn_frame, text="Cancelar", 
                               command=lambda: [dialog.destroy(), on_cancel()],
                               width=15)
        cancel_btn.pack()

        return dialog, status_label, progress_bar, detail_label, cancel_btn


class DependencyInstaller:
    """Gerencia instalacao de dependencias - FOCADO EM PYTHON 3.12"""

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    @staticmethod
    def find_python_312_installations():
        """Encontra todas instalacoes do Python 3.12"""
        python_paths = []

        # Procura no PATH
        try:
            result = subprocess.run(['where', 'python'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                path = Path(line.strip())
                name = path.name.lower()
                if 'python' in name:
                    # Verifica versao
                    try:
                        ver_result = subprocess.run([str(path), '--version'], capture_output=True, text=True)
                        if '3.12' in ver_result.stdout:
                            python_paths.append(f"{path} - {ver_result.stdout.strip()}")
                    except:
                        pass
        except:
            pass

        # Procura em locais comuns
        common_paths = [
            r"C:\Python312\python.exe",
            r"C:\Program Files\Python312\python.exe",
            r"C:\Program Files (x86)\Python312\python.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
        ]

        for path_str in common_paths:
            path = Path(path_str)
            if path.exists():
                try:
                    ver_result = subprocess.run([str(path), '--version'], capture_output=True, text=True)
                    if '3.12' in ver_result.stdout:
                        python_paths.append(f"{path} - {ver_result.stdout.strip()}")
                except:
                    pass

        return python_paths

    @staticmethod
    def check_python_312():
        """Verifica se Python 3.12 esta disponivel"""
        paths = DependencyInstaller.find_python_312_installations()
        return len(paths) > 0, paths

    @staticmethod
    def check_pygame(python_path):
        """Verifica se Pygame esta instalado no Python especifico"""
        try:
            cmd = [str(python_path), '-c', 'import pygame; print(pygame.version.ver)']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def install_python_312(progress_callback):
        """Instala Python 3.12 silenciosamente"""
        try:
            progress_callback("Baixando Python 3.12...")
            python_installer = Path(tempfile.gettempdir()) / "python_312_installer.exe"
            urlretrieve(PYTHON_312_URL, python_installer)

            progress_callback("Instalando Python 3.12...")
            # Instalacao silenciosa, adiciona ao PATH
            subprocess.run([str(python_installer), '/quiet', 'InstallAllUsers=1', 'PrependPath=1'],
                          timeout=300)

            python_installer.unlink()

            # Aguarda instalacao completar
            import time
            time.sleep(2)

            return True
        except Exception as e:
            return False

    @staticmethod
    def install_pygame(python_path, progress_callback):
        """Instala pygame usando o Python especifico"""
        try:
            progress_callback("Instalando pygame...")
            cmd = [str(python_path), '-m', 'pip', 'install', 'pygame']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            return False


class PokemonTDLauncher:
    def __init__(self):
        self.launcher_dir = Path(sys.argv[0]).parent
        self.game_dir = self.launcher_dir / "PokemonTD"
        self.versions_dir = self.launcher_dir / "Versions"
        self.current_version = self.get_local_version()
        self.offline_mode = False
        self.latest_release = None
        self.is_downloading = False
        self.saves_backup_path = None  # Path para backup dos saves
        self.python_path = None
        self.dependencies_ok = False
        self.download_cancelled = False
        self.download_progress_dialog = None

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
        state = 'normal' if enabled else 'disabled'
        if self.play_btn:
            self.play_btn.config(state=state)
        if self.check_btn:
            self.check_btn.config(state=state)
        if self.download_btn:
            self.download_btn.config(state=state)
        if self.offline_btn:
            self.offline_btn.config(state=state)

    def update_progress_status(self, message):
        self.root.after(0, lambda: self.progress_var.set(message))
        if self.download_progress_dialog:
            try:
                self.download_progress_dialog[1].config(text=message)
            except:
                pass

    def get_saves_path(self, base_dir=None):
        """
        Retorna o caminho correto da pasta de saves
        O jogo salva em: PokemonTD/saves (NÃO em src/saves)
        """
        if base_dir is None:
            base_dir = self.game_dir
        return base_dir / "saves"

    def backup_saves_preserve(self, source_dir=None):
        """
        FAZ BACKUP COMPLETO DOS SAVES
        Salva TODOS os arquivos JSON da pasta saves em um local temporário
        
        Args:
            source_dir: Diretório de origem (se None, usa game_dir)
        """
        if source_dir is None:
            source_dir = self.game_dir
            
        saves_path = self.get_saves_path(source_dir)
        
        if not saves_path.exists():
            self.add_log(f"Pasta saves não existe em: {saves_path}", "INFO")
            return False
        
        # Encontra TODOS os arquivos JSON na pasta saves e subpastas
        json_files = list(saves_path.rglob("*.json"))
        
        if not json_files:
            self.add_log("Nenhum arquivo JSON de save encontrado", "INFO")
            return False
        
        # Cria pasta de backup
        import tempfile
        self.saves_backup_path = Path(tempfile.mkdtemp(prefix="pokemon_saves_backup_"))
        backup_path = self.saves_backup_path
        
        self.add_log(f"Backup criado em: {backup_path}", "INFO")
        
        save_count = 0
        for file in json_files:
            # Mantém a estrutura de pastas relativa
            relative_path = file.relative_to(saves_path)
            dest_file = backup_path / relative_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest_file)
            save_count += 1
            
            # Mostra detalhe de cada arquivo salvo
            self.add_log(f"  • Salvo: {relative_path}", "INFO")
        
        self.add_log(f"SAVES PRESERVADOS: {save_count} arquivos JSON", "SUCCESS")
        return True

    def restore_saves_preserve(self, target_dir=None):
        """
        RESTAURA OS SAVES DO BACKUP
        Copia todos os arquivos JSON do backup para a pasta saves
        
        Args:
            target_dir: Diretório de destino (se None, usa game_dir)
        """
        if target_dir is None:
            target_dir = self.game_dir
            
        saves_path = self.get_saves_path(target_dir)
        saves_path.mkdir(parents=True, exist_ok=True)
        
        if not self.saves_backup_path or not self.saves_backup_path.exists():
            self.add_log("Nenhum backup de save encontrado", "INFO")
            return False
        
        backup_path = self.saves_backup_path
        
        # Encontra TODOS os arquivos JSON no backup
        json_files = list(backup_path.rglob("*.json"))
        
        if not json_files:
            self.add_log("Nenhum arquivo JSON encontrado no backup", "INFO")
            return False
        
        restored_count = 0
        for file in json_files:
            relative_path = file.relative_to(backup_path)
            dest_file = saves_path / relative_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest_file)
            restored_count += 1
            
            self.add_log(f"  • Restaurado: {relative_path}", "INFO")
        
        self.add_log(f"SAVES RESTAURADOS: {restored_count} arquivos JSON", "SUCCESS")
        return True

    def clean_backup(self):
        """Remove a pasta de backup temporária"""
        if self.saves_backup_path and self.saves_backup_path.exists():
            try:
                shutil.rmtree(self.saves_backup_path)
                self.add_log("Backup removido", "INFO")
            except:
                pass
            self.saves_backup_path = None

    def check_and_install_dependencies(self):
        """Verifica Python 3.12 e Pygame"""
        self.add_log("=== VERIFICANDO DEPENDENCIAS ===", "INFO")

        has_python, python_paths = DependencyInstaller.check_python_312()

        if not has_python:
            self.add_log("Python 3.12 nao encontrado!", "WARNING")

            def do_install():
                self.install_python_312()

            ModernDialog.show_install_dialog(self.root, do_install)
            return False

        # Mostra opcoes de Python 3.12 encontrados
        if len(python_paths) == 1:
            # So tem um, usa direto
            self.python_path = python_paths[0].split(' - ')[0]
            self.add_log(f"Python 3.12 encontrado: {self.python_path}", "SUCCESS")
            return self.check_and_install_pygame()
        else:
            # Varios, deixa usuario escolher
            def on_select(selection):
                if selection == "install":
                    self.install_python_312()
                else:
                    self.python_path = selection
                    self.add_log(f"Python 3.12 selecionado: {self.python_path}", "SUCCESS")
                    self.check_and_install_pygame()

            ModernDialog.show_python_selection_dialog(self.root, python_paths, on_select)
            return False

    def check_and_install_pygame(self):
        """Verifica e instala pygame no Python selecionado"""
        if not self.python_path:
            return False

        if DependencyInstaller.check_pygame(self.python_path):
            self.add_log("Pygame ja instalado!", "SUCCESS")
            self.dependencies_ok = True
            return True

        self.add_log("Pygame nao encontrado. Instalando...", "WARNING")

        def install_pygame():
            self.set_buttons_state(False)
            self.progress_var.set("Instalando pygame...")

            if DependencyInstaller.install_pygame(self.python_path, self.update_progress_status):
                self.add_log("Pygame instalado com sucesso!", "SUCCESS")
                self.dependencies_ok = True
                self.progress_var.set("Pronto")
            else:
                self.add_log("Falha ao instalar pygame!", "ERROR")
                messagebox.showerror("Erro", "Falha ao instalar pygame!\n\nTente manualmente: pip install pygame")

            self.set_buttons_state(True)

        threading.Thread(target=install_pygame, daemon=True).start()
        return False

    def install_python_312(self):
        """Instala Python 3.12"""
        self.set_buttons_state(False)

        def install_thread():
            try:
                self.add_log("Iniciando instalacao do Python 3.12...", "INFO")

                if DependencyInstaller.install_python_312(self.update_progress_status):
                    self.add_log("Python 3.12 instalado com sucesso!", "SUCCESS")
                    self.progress_var.set("Python instalado!")

                    # Re-verifica para pegar o novo Python
                    has_python, python_paths = DependencyInstaller.check_python_312()
                    if has_python and python_paths:
                        self.python_path = python_paths[0].split(' - ')[0]
                        self.add_log(f"Python 3.12 detectado: {self.python_path}", "SUCCESS")

                        # Instala pygame no novo Python
                        if DependencyInstaller.install_pygame(self.python_path, self.update_progress_status):
                            self.add_log("Pygame instalado!", "SUCCESS")
                            self.dependencies_ok = True
                            self.progress_var.set("Pronto!")
                            messagebox.showinfo("Sucesso", "Python 3.12 e Pygame instalados com sucesso!")
                        else:
                            self.add_log("Falha ao instalar pygame!", "ERROR")
                    else:
                        self.add_log("Falha ao detectar Python apos instalacao!", "ERROR")
                        messagebox.showerror("Erro", "Python instalado mas nao detectado.\nReinicie o launcher.")
                else:
                    self.add_log("Falha na instalacao do Python!", "ERROR")
                    messagebox.showerror("Erro", "Falha ao instalar Python!\n\nInstale manualmente em: python.org")

            except Exception as e:
                self.add_log(f"Erro: {e}", "ERROR")
            finally:
                self.set_buttons_state(True)
                self.progress_var.set("Pronto")

        threading.Thread(target=install_thread, daemon=True).start()

    def get_local_version(self):
        version_file = self.game_dir / "game_version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.0.0"

    def get_installed_versions(self):
        versions = []
        if self.versions_dir.exists():
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir() and version_dir.name != self.current_version:
                    versions.append(version_dir.name)
        return sorted(versions, reverse=True)

    def get_latest_release(self):
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

    def download_version(self, version_info):
        """Download com feedback detalhado e barra de progresso"""
        try:
            self.is_downloading = True
            self.download_cancelled = False
            self.set_buttons_state(False)

            # Cria diálogo de progresso
            dialog, status_label, progress_bar, detail_label, cancel_btn = ModernDialog.show_download_progress_dialog(
                self.root, self.cancel_download
            )
            self.download_progress_dialog = (dialog, status_label, progress_bar, detail_label, cancel_btn)

            self.add_log(f"Baixando versao {version_info['version']}...", "INFO")

            # ===== PASSO 1: FAZ BACKUP DOS SAVES =====
            if self.game_dir.exists():
                self.add_log("=== FAZENDO BACKUP DOS SAVES ===", "INFO")
                status_label.config(text="Fazendo backup dos saves...")
                if not self.backup_saves_preserve():
                    self.add_log("ATENÇÃO: Nenhum save encontrado para backup", "WARNING")

            # Configuração do progresso
            progress_bar['value'] = 0
            status_label.config(text="Preparando download...")
            detail_label.config(text="Conectando ao servidor...")

            # Download do arquivo
            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.close()

            self.add_log(f"URL do download: {version_info['download_url']}", "INFO")

            def report_progress(block_num, block_size, total_size):
                if self.download_cancelled:
                    raise Exception("Download cancelado pelo usuário")
                    
                if total_size > 0:
                    progress = (block_num * block_size) / total_size * 100
                    current_mb = (block_num * block_size) / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    
                    # Atualiza interfaces
                    self.root.after(0, lambda: progress_bar.config(value=min(progress, 100)))
                    self.root.after(0, lambda: status_label.config(
                        text=f"Baixando: {progress:.1f}%"
                    ))
                    self.root.after(0, lambda: detail_label.config(
                        text=f"{current_mb:.1f} MB / {total_mb:.1f} MB"
                    ))
                    self.root.after(0, lambda: self.progress_var.set(f"Baixando: {progress:.1f}%"))
                    self.root.after(0, lambda: self.progress_bar.config(value=min(progress, 100)))
                    
                    # Log a cada 10%
                    if int(progress) % 10 == 0 and int(progress) > 0:
                        self.add_log(f"Download: {progress:.1f}% completo", "INFO")

            self.add_log("Iniciando download do arquivo...", "INFO")
            status_label.config(text="Baixando arquivo...")
            detail_label.config(text="Aguardando resposta do servidor...")

            # Faz o download com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    urlretrieve(version_info["download_url"], temp_zip.name, reporthook=report_progress)
                    break
                except Exception as e:
                    if attempt < max_retries - 1 and not self.download_cancelled:
                        self.add_log(f"Tentativa {attempt + 1} falhou, tentando novamente...", "WARNING")
                        status_label.config(text=f"Tentativa {attempt + 1} falhou, tentando novamente...")
                        time.sleep(2)
                    else:
                        raise

            if self.download_cancelled:
                self.add_log("Download cancelado pelo usuário", "WARNING")
                status_label.config(text="Download cancelado")
                return False

            status_label.config(text="Download concluído! Extraindo...")
            detail_label.config(text="Extraindo arquivos...")
            self.add_log("Download concluído, extraindo arquivos...", "INFO")

            # ===== PASSO 2: EXTRAI A NOVA VERSÃO =====
            version_path = self.versions_dir / version_info["version"]
            if version_path.exists():
                shutil.rmtree(version_path)
            version_path.mkdir(parents=True)

            self.progress_var.set("Extraindo arquivos...")

            with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                root_folder = None
                for name in zip_ref.namelist():
                    if '/' in name:
                        root_folder = name.split('/')[0]
                        break

                files = zip_ref.namelist()
                total_files = len(files)
                self.add_log(f"Extraindo {total_files} arquivos...", "INFO")

                for i, member in enumerate(files):
                    if self.download_cancelled:
                        raise Exception("Download cancelado pelo usuário")
                        
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
                    self.root.after(0, lambda p=progress: progress_bar.config(value=p))
                    self.root.after(0, lambda p=progress: detail_label.config(
                        text=f"Extraindo: {i+1}/{total_files} arquivos"
                    ))
                    
                    # Log a cada 100 arquivos
                    if i % 100 == 0 and i > 0:
                        self.add_log(f"Extraídos {i+1}/{total_files} arquivos", "INFO")

            os.unlink(temp_zip.name)

            if self.download_cancelled:
                self.add_log("Download cancelado pelo usuário", "WARNING")
                shutil.rmtree(version_path, ignore_errors=True)
                return False

            # ===== PASSO 3: TRANSFERE OS SAVES PARA A NOVA VERSÃO =====
            if self.saves_backup_path and self.saves_backup_path.exists():
                self.add_log("=== TRANSFERINDO SAVES PARA NOVA VERSÃO ===", "INFO")
                
                new_saves_path = self.get_saves_path(version_path)
                new_saves_path.mkdir(parents=True, exist_ok=True)
                
                # Copia todos os JSONs do backup para a nova versão
                backup_saves = list(self.saves_backup_path.rglob("*.json"))
                restored_count = 0
                for save_file in backup_saves:
                    relative_path = save_file.relative_to(self.saves_backup_path)
                    dest_file = new_saves_path / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(save_file, dest_file)
                    restored_count += 1
                    self.add_log(f"  • Transferido: {relative_path}", "INFO")
                
                self.add_log(f"SAVES TRANSFERIDOS: {restored_count} arquivos para nova versão", "SUCCESS")
            else:
                self.add_log("Nenhum save para transferir", "INFO")

            # Salva informações da versão
            (version_path / "game_version.txt").write_text(version_info["version"])
            if version_info.get("changelog"):
                (version_path / "changelog.txt").write_text(version_info["changelog"])

            self.add_log(f"Download da versão {version_info['version']} concluído", "SUCCESS")
            
            # Limpa o backup
            self.clean_backup()

            status_label.config(text="Download concluído com sucesso!")
            detail_label.config(text="Pronto!")
            self.progress_var.set("Pronto")
            
            # Fecha o diálogo após um tempo
            self.root.after(2000, dialog.destroy)
            
            return True

        except Exception as e:
            error_msg = str(e)
            if "cancelado" in error_msg:
                self.add_log("Download cancelado pelo usuário", "WARNING")
                return False
            else:
                self.add_log(f"Erro no download: {error_msg}", "ERROR")
                self.progress_var.set("Erro no download")
                if self.download_progress_dialog:
                    try:
                        self.download_progress_dialog[1].config(text=f"Erro: {error_msg}")
                    except:
                        pass
                return False
        finally:
            self.is_downloading = False
            self.download_progress_dialog = None
            self.set_buttons_state(True)
            if not self.download_cancelled:
                self.progress_bar['value'] = 0

    def cancel_download(self):
        """Cancela o download em andamento"""
        self.download_cancelled = True
        self.add_log("Cancelando download...", "WARNING")

    def set_current_version(self, version):
        """
        Troca para uma versão específica PRESERVANDO OS SAVES
        """
        version_path = self.versions_dir / version

        if not version_path.exists():
            self.add_log(f"Versao {version} nao encontrada", "ERROR")
            return False

        self.add_log(f"Trocando para versao {version}...", "INFO")

        # ===== PASSO 1: FAZ BACKUP DOS SAVES DA VERSÃO ATUAL =====
        if self.game_dir.exists():
            self.add_log("Fazendo backup dos saves da versão atual...", "INFO")
            if not self.backup_saves_preserve():
                self.add_log("Nenhum save encontrado na versão atual", "WARNING")

        # ===== PASSO 2: REMOVE A VERSÃO ATUAL =====
        if self.game_dir.exists():
            self.add_log("Removendo versão atual...", "INFO")
            shutil.rmtree(self.game_dir)

        # ===== PASSO 3: COPIA A NOVA VERSÃO =====
        self.add_log(f"Copiando versão {version}...", "INFO")
        shutil.copytree(version_path, self.game_dir)

        # ===== PASSO 4: RESTAURA OS SAVES NA NOVA VERSÃO =====
        if self.saves_backup_path and self.saves_backup_path.exists():
            self.add_log("Restaurando saves na nova versão...", "INFO")
            self.restore_saves_preserve()
            self.clean_backup()
        else:
            # Tenta restaurar da versão baixada (fallback)
            self.add_log("Tentando restaurar saves da versão baixada...", "INFO")
            saves_from_version = self.get_saves_path(version_path)
            saves_in_game = self.get_saves_path(self.game_dir)
            
            if saves_from_version.exists():
                self.add_log(f"Copiando saves de {saves_from_version}", "INFO")
                saves_in_game.mkdir(parents=True, exist_ok=True)
                shutil.copytree(saves_from_version, saves_in_game, dirs_exist_ok=True)
                self.add_log("Saves restaurados da versão baixada", "SUCCESS")

        self.current_version = version

        if self.version_label:
            self.version_label.config(text=f"Versao: {self.current_version}")

        self.add_log(f"Versao {version} carregada com saves preservados!", "SUCCESS")
        return True

    def find_main_py(self):
        possible_paths = [
            self.game_dir / "src" / "main.py",
            self.game_dir / "main.py",
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return None

    def launch_game(self):
        if self.is_downloading:
            self.add_log("Aguarde o download terminar", "WARNING")
            messagebox.showwarning("Download em andamento", "Aguarde o download terminar.")
            return

        if not self.dependencies_ok:
            if not self.check_and_install_dependencies():
                return

        main_py = self.find_main_py()

        if not main_py:
            self.add_log("Jogo nao encontrado", "ERROR")
            messagebox.showerror("Erro", "Jogo nao encontrado!\nUse BAIXAR para instalar.")
            return

        self.add_log("Iniciando jogo...", "INFO")
        self.add_log(f"Usando Python: {self.python_path}", "INFO")

        batch_file = self.launcher_dir / "run_game_temp.bat"
        batch_content = f"""@echo off
cd /d "{self.game_dir}"
"{self.python_path}" "{main_py}"
"""
        batch_file.write_text(batch_content)

        self.root.destroy()
        subprocess.Popen([str(batch_file)], shell=True)
        sys.exit(0)

    def check_for_updates(self):
        if self.is_downloading:
            self.add_log("Aguarde o download terminar", "WARNING")
            return

        if not self.dependencies_ok:
            if not self.check_and_install_dependencies():
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
            if not self.find_main_py():
                self.add_log("Jogo nao encontrado! Use BAIXAR.", "WARNING")
                messagebox.showwarning("Jogo nao encontrado",
                    "Nenhuma versao do jogo encontrada!\n\nClique em BAIXAR para instalar.")
            else:
                messagebox.showinfo("Atualizado", f"Versao {self.current_version} esta atualizada!")

    def start_download(self):
        if self.is_downloading:
            return
        if self.latest_release:
            threading.Thread(target=self.perform_update, daemon=True).start()

    def force_download(self):
        if self.is_downloading:
            self.add_log("Download em andamento", "WARNING")
            return

        if not self.dependencies_ok:
            if not self.check_and_install_dependencies():
                return

        self.add_log("=== FORCANDO DOWNLOAD ===", "INFO")

        release = self.get_latest_release()

        if not release:
            self.add_log("Erro ao obter versao", "ERROR")
            messagebox.showerror("Erro", "Nao foi possivel obter informacoes do GitHub")
            return

        self.latest_release = release

        msg = f"Deseja baixar a versao {release['version']}?\n\n"
        if release['changelog']:
            msg += f"Novidades:\n{release['changelog'][:200]}"

        if messagebox.askyesno("Confirmar Download", msg):
            threading.Thread(target=self.perform_update, daemon=True).start()

    def perform_update(self):
        if not self.latest_release:
            self.latest_release = self.get_latest_release()
            if not self.latest_release:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao obter versao"))
                return

        self.add_log(f"Atualizando para versao {self.latest_release['version']}", "INFO")

        success = self.download_version(self.latest_release)

        if success and not self.download_cancelled:
            result = self.set_current_version(self.latest_release['version'])
            if result:
                self.root.after(0, lambda: messagebox.showinfo("Sucesso",
                    f"Versao {self.latest_release['version']} instalada!\n\nSeus saves foram preservados!"))
                self.add_log("Atualizacao concluida", "SUCCESS")
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao ativar versao"))
        elif self.download_cancelled:
            self.root.after(0, lambda: messagebox.showinfo("Cancelado", "Download cancelado pelo usuário"))
        else:
            self.root.after(0, lambda: messagebox.showerror("Erro", "Falha no download"))

    def show_offline_options(self):
        if self.is_downloading:
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
                        messagebox.showinfo("Sucesso", f"Versao {version} carregada!")
                        self.launch_game()
                    else:
                        messagebox.showerror("Erro", "Falha ao carregar versao")

            ModernDialog.show_offline_dialog(
                self.root, installed_versions, self.current_version, on_play
            )
        else:
            self.add_log("Nenhuma versao instalada", "WARNING")
            messagebox.showwarning("Sem Jogo", "Nenhuma versao encontrada!\nClique em BAIXAR.")

    def open_github(self):
        webbrowser.open(GITHUB_RELEASES)
        self.add_log("Abrindo GitHub", "INFO")

    def create_gui(self):
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

        subtitle_label = ttk.Label(header_frame, text="Launcher Oficial - Requer Python 3.12",
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

        info_text = "Seus saves sao PRESERVADOS | O jogo REQUER Python 3.12"
        info_label = ttk.Label(info_bar, text=info_text,
                              font=("Segoe UI", 9), foreground="#00cc66")
        info_label.pack()

        center_window(self.root, 900, 750)

        self.add_log("Launcher inicializado", "INFO")
        self.add_log(f"Diretorio: {self.launcher_dir}", "INFO")
        self.add_log(f"Versao atual: {self.current_version}", "INFO")
        self.add_log("SISTEMA DE PRESERVACAO DE SAVES ATIVO", "SUCCESS")
        self.add_log("REQUER Python 3.12 - O launcher instalara se necessario", "INFO")

        # Verifica dependencias ao iniciar
        self.root.after(100, lambda: self.check_and_install_dependencies())

    def run(self):
        self.create_gui()
        self.root.mainloop()


if __name__ == "__main__":
    launcher = PokemonTDLauncher()
    launcher.run()
