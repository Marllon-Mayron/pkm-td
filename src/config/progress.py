"""
Sistema de progresso do jogador - Agora usando SaveManager
"""
import json
import os
from pathlib import Path
from src.managers.save_manager import save_manager


class ProgressManager:
    def __init__(self):
        # Remove o save_file antigo
        # self.save_file = Path("save_data.json")

        # Usa o SaveManager
        self.save_manager = save_manager

        # Carrega o progresso do SaveManager
        self.progress = self.load_progress()

        # Converte progresso antigo para o novo formato (se necessário)
        self._migrate_old_progress()

    def _migrate_old_progress(self):
        """Converte progresso antigo (save_data.json) para o novo formato"""
        # Verifica se existe o arquivo antigo
        old_save = Path("save_data.json")
        if old_save.exists():
            try:
                with open(old_save, 'r') as f:
                    old_data = json.load(f)

                print("[PROGRESS] Encontrado save_data.json antigo. Convertendo...")

                # Tenta carregar o save atual do SaveManager (slot 1)
                current_save = self.save_manager.list_saves()[0] if self.save_manager.list_saves() else None

                # Se não houver save no novo formato, cria um
                if current_save is None or current_save.get("empty", True):
                    print("[PROGRESS] Criando novo save a partir do antigo...")

                    # Atualiza o SaveManager com os dados antigos
                    # Precisamos de um objeto player temporário para isso
                    from src.entities.player import Player
                    temp_player = Player(0, 0)
                    temp_player.money = old_data.get("money", 100)
                    temp_player.score = old_data.get("score", 0)

                    # Converte o progresso antigo
                    game_state = {
                        "current_chapter": old_data.get("current_chapter", 1),
                        "current_phase": old_data.get("current_phase", 1),
                        "unlocked_phases": old_data.get("unlocked_phases", ["1-1"]),
                        "completed_phases": old_data.get("completed_phases", []),
                        "stars": old_data.get("stars", {})
                    }

                    # Salva no novo formato
                    self.save_manager.save_game(temp_player, game_state, "Save 1", slot=1)

                    # Agora carrega o progresso do novo save
                    self.progress = self.load_progress()

                    # Faz backup do arquivo antigo
                    backup_name = f"save_data_backup_{old_save.stat().st_mtime}.json"
                    old_save.rename(backup_name)
                    print(f"[PROGRESS] Save antigo convertido e movido para {backup_name}")

            except Exception as e:
                print(f"[PROGRESS] Erro ao converter save antigo: {e}")

        # Agora converte os dados do progress atual para garantir formato correto
        self._ensure_correct_format()

    def _ensure_correct_format(self):
        """Garante que o progresso está no formato correto"""
        changed = False

        # Verifica se unlocked_phases está no formato correto
        if "unlocked_phases" not in self.progress:
            self.progress["unlocked_phases"] = ["1-1"]
            changed = True
        else:
            new_unlocked = []
            for phase in self.progress["unlocked_phases"]:
                if isinstance(phase, int):
                    new_unlocked.append(str(phase))
                    changed = True
                else:
                    new_unlocked.append(phase)
            if changed:
                self.progress["unlocked_phases"] = new_unlocked

        # Verifica completed_phases
        if "completed_phases" not in self.progress:
            self.progress["completed_phases"] = []
            changed = True
        else:
            new_completed = []
            for phase in self.progress["completed_phases"]:
                if isinstance(phase, int):
                    new_completed.append(str(phase))
                    changed = True
                else:
                    new_completed.append(phase)
            if changed:
                self.progress["completed_phases"] = new_completed

        # Verifica stars
        if "stars" not in self.progress:
            self.progress["stars"] = {}
            changed = True
        else:
            new_stars = {}
            for key, value in self.progress["stars"].items():
                if isinstance(key, int):
                    new_stars[str(key)] = value
                    changed = True
                else:
                    new_stars[key] = value
            if changed:
                self.progress["stars"] = new_stars

        # Verifica outros campos obrigatórios
        if "current_chapter" not in self.progress:
            self.progress["current_chapter"] = 1
            changed = True

        if "settings" not in self.progress:
            self.progress["settings"] = {
                "sound_volume": 0.7,
                "music_volume": 0.5,
                "show_fps": False
            }
            changed = True

        if changed:
            self.save_progress()
            print("[PROGRESS] Formato do progresso corrigido")

    def load_progress(self):
        """Carrega o progresso do SaveManager"""
        # Tenta carregar do slot 1
        saved_data = self._load_from_save_slot(1)

        if saved_data:
            return saved_data

        # Se não houver save, cria o progresso padrão
        default_progress = {
            "unlocked_phases": ["1-1"],  # Fase 1-1 sempre desbloqueada
            "completed_phases": [],      # Fases completadas
            "current_chapter": 1,
            "stars": {},                  # Estrelas por fase
            "settings": {
                "sound_volume": 0.7,
                "music_volume": 0.5,
                "show_fps": False
            }
        }

        print("[PROGRESS] Nenhum save encontrado, criando novo progresso")
        return default_progress

    def _load_from_save_slot(self, slot=1):
        """Carrega os dados de progresso de um slot de save"""
        # Obtém a lista de saves
        saves = self.save_manager.list_saves()

        # Verifica se o slot existe e não está vazio
        if slot-1 < len(saves):
            slot_info = saves[slot-1]
            if slot_info.get("empty") or slot_info.get("error"):
                return None

            # Tenta carregar o save completo
            try:
                # Cria um player temporário para carregar o save
                from src.entities.player import Player
                temp_player = Player(0, 0)

                if self.save_manager.load_game(temp_player, slot):
                    # Extrai os dados de progresso
                    game_state = self.save_manager.save_data.get("game_state", {})

                    # Converte o formato do save_manager para o formato do progress_manager
                    progress_data = {
                        "unlocked_phases": game_state.get("unlocked_phases", ["1-1"]),
                        "completed_phases": game_state.get("completed_phases", []),
                        "current_chapter": game_state.get("current_chapter", 1),
                        "stars": game_state.get("stars", {}),
                        "settings": self._get_settings_from_save()
                    }

                    print(f"[PROGRESS] Progresso carregado do slot {slot}")
                    return progress_data

            except Exception as e:
                print(f"[PROGRESS] Erro ao carregar progresso do slot {slot}: {e}")
                return None

        return None

    def _get_settings_from_save(self):
        """Extrai as configurações do save"""
        # Por enquanto, retorna padrão
        # Futuramente, podemos salvar settings no save_manager também
        return {
            "sound_volume": 0.7,
            "music_volume": 0.5,
            "show_fps": False
        }

    def save_progress(self):
        """Salva o progresso usando o SaveManager"""
        try:
            # Cria um player temporário para salvar os dados
            from src.entities.player import Player
            temp_player = Player(0, 0)

            # Prepara o game_state com os dados de progresso
            game_state = {
                "current_chapter": self.progress["current_chapter"],
                "current_phase": self._get_current_phase(),
                "unlocked_phases": self.progress["unlocked_phases"],
                "completed_phases": self.progress["completed_phases"],
                "stars": self.progress["stars"]
            }

            # Salva no slot 1 (padrão)
            # Você pode modificar para usar o slot atual se necessário
            self.save_manager.save_game(temp_player, game_state, "Save 1", slot=1)
            print("[PROGRESS] Progresso salvo com sucesso")

        except Exception as e:
            print(f"[PROGRESS] Erro ao salvar progresso: {e}")

    def _get_current_phase(self):
        """Retorna o número da fase atual baseado nas fases desbloqueadas"""
        unlocked = self.progress["unlocked_phases"]
        if unlocked:
            # Pega a última fase desbloqueada
            last_phase = unlocked[-1]
            if "-" in last_phase:
                return int(last_phase.split("-")[1])
        return 1

    def get_next_phase(self, phase_id):
        """
        Retorna o ID da próxima fase baseado no formato capitulo-fase
        Agora consulta o catálogo para saber quantas fases existem em cada capítulo
        """
        if "-" not in phase_id:
            return None

        chapter, phase = map(int, phase_id.split("-"))

        # Importa o catálogo aqui para evitar circular imports
        from src.config.phase_catalog import phase_catalog

        # Pega as fases do capítulo atual
        chapter_phases = phase_catalog.get_chapter_phases(chapter)

        if not chapter_phases:
            return None

        # Encontra o índice da fase atual
        current_index = None
        for i, p in enumerate(chapter_phases):
            if p["number"] == phase:
                current_index = i
                break

        if current_index is None:
            return None

        # Se não for a última fase do capítulo
        if current_index < len(chapter_phases) - 1:
            next_phase = chapter_phases[current_index + 1]
            return f"{chapter}-{next_phase['number']}"
        else:
            # Última fase do capítulo - verifica se existe próximo capítulo
            next_chapter = chapter + 1
            next_chapter_phases = phase_catalog.get_chapter_phases(next_chapter)
            if next_chapter_phases:
                # Primeira fase do próximo capítulo
                return f"{next_chapter}-{next_chapter_phases[0]['number']}"

        return None  # Não há próxima fase

    def unlock_next_phase(self, completed_phase_id):
        """Desbloqueia a próxima fase após completar a atual"""
        next_phase_id = self.get_next_phase(completed_phase_id)

        if next_phase_id and next_phase_id not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(next_phase_id)
            self.progress["unlocked_phases"].sort()
            print(f"🎉 Nova fase desbloqueada: {next_phase_id}!")
            self.save_progress()
            return True
        elif next_phase_id:
            print(f"Fase {next_phase_id} já estava desbloqueada")
        else:
            print("🏆 Parabéns! Você completou todas as fases disponíveis!")
        return False

    def complete_phase(self, phase_id, stars=0):
        """Marca uma fase como completada"""
        # Garante que phase_id é string
        phase_id = str(phase_id)

        # Se a fase já foi completada, só atualiza as estrelas se for melhor
        if phase_id in self.progress["completed_phases"]:
            if stars > self.progress["stars"].get(phase_id, 0):
                self.progress["stars"][phase_id] = stars
                print(f"⭐ Nova pontuação na fase {phase_id}: {stars} estrelas!")
        else:
            # Primeira vez completando a fase
            self.progress["completed_phases"].append(phase_id)
            self.progress["completed_phases"].sort()
            self.progress["stars"][phase_id] = stars

            print(f"✅ Fase {phase_id} completada com {stars} estrelas!")

            # Desbloqueia a próxima fase
            self.unlock_next_phase(phase_id)

        self.save_progress()

    def is_phase_unlocked(self, phase_id):
        """Verifica se uma fase está desbloqueada"""
        # Garante que phase_id é string
        phase_id = str(phase_id)
        return phase_id in self.progress["unlocked_phases"]

    def is_phase_completed(self, phase_id):
        """Verifica se uma fase foi completada"""
        # Garante que phase_id é string
        phase_id = str(phase_id)
        return phase_id in self.progress["completed_phases"]

    def get_chapter_progress(self, chapter_id, chapter_phases):
        """Retorna progresso de um capítulo"""
        total = len(chapter_phases)
        unlocked = sum(1 for phase in chapter_phases if self.is_phase_unlocked(phase))
        completed = sum(1 for phase in chapter_phases if self.is_phase_completed(phase))
        return {
            "total": total,
            "unlocked": unlocked,
            "completed": completed,
            "percentage": (completed / total * 100) if total > 0 else 0
        }

    def reset_progress(self):
        """Reseta todo o progresso (para testes)"""
        self.progress = {
            "unlocked_phases": ["1-1"],
            "completed_phases": [],
            "current_chapter": 1,
            "stars": {},
            "settings": self.progress["settings"]
        }
        self.save_progress()
        print("Progresso resetado!")

    # Métodos para teste/desenvolvimento
    def unlock_specific_phase(self, phase_id):
        """Desbloqueia uma fase específica manualmente"""
        # Garante que phase_id é string
        phase_id = str(phase_id)

        if phase_id not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(phase_id)
            self.progress["unlocked_phases"].sort()
            self.save_progress()
            print(f"Fase {phase_id} desbloqueada manualmente!")
            return True
        return False

    def unlock_chapter(self, chapter_id, chapter_phases):
        """Desbloqueia todas as fases de um capítulo"""
        for phase_id in chapter_phases:
            # Garante que cada phase_id é string
            phase_id = str(phase_id)
            if phase_id not in self.progress["unlocked_phases"]:
                self.progress["unlocked_phases"].append(phase_id)

        self.progress["unlocked_phases"].sort()
        self.save_progress()
        print(f"Capítulo {chapter_id} totalmente desbloqueado! Fases: {chapter_phases}")

    def unlock_all_for_testing(self, max_chapter=3, phases_per_chapter=5):
        """Desbloqueia todas as fases para teste"""
        for chapter in range(1, max_chapter + 1):
            for phase in range(1, phases_per_chapter + 1):
                phase_id = f"{chapter}-{phase}"
                if phase_id not in self.progress["unlocked_phases"]:
                    self.progress["unlocked_phases"].append(phase_id)

        self.progress["unlocked_phases"].sort()
        self.save_progress()
        print(f"Todas as fases até o capítulo {max_chapter} desbloqueadas!")


# Instância global
progress_manager = ProgressManager()