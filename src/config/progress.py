# src/managers/progress.py

"""
Sistema de progresso do jogador - Integrado com SaveManager
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# src/managers/progress.py

"""
Sistema de progresso do jogador - Integrado com SaveManager
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class ProgressManager:
    def __init__(self):
        # Agora usa o SaveManager como fonte única de dados
        from src.managers.save_manager import save_manager
        self.save_manager = save_manager
        self.progress = self._load_from_save_manager()

    def _load_from_save_manager(self) -> Dict:
        """Carrega o progresso do SaveManager (dados do save atual)"""
        # Pega os dados de progresso do save atual
        game_state = self.save_manager.save_data.get("game_state", {})

        # Converte unlocked_phases para lista de strings
        unlocked_phases = game_state.get("unlocked_phases", ["1-1"])
        unlocked_phases = [str(phase) for phase in unlocked_phases]

        # Converte completed_phases
        completed_phases = game_state.get("completed_phases", [])
        completed_phases = [str(phase) for phase in completed_phases]

        # Converte stars
        stars = game_state.get("stars", {})
        converted_stars = {}
        for key, value in stars.items():
            converted_stars[str(key)] = value

        return {
            "unlocked_phases": unlocked_phases,
            "completed_phases": completed_phases,
            "current_chapter": game_state.get("current_chapter", 1),
            "current_phase": game_state.get("current_phase", 1),
            "stars": converted_stars,
            "settings": self._load_settings()
        }

    def _load_settings(self) -> Dict:
        """Carrega configurações"""
        config_path = Path('config.json')
        default_settings = {
            "sound_volume": 0.7,
            "music_volume": 0.5,
            "show_fps": False
        }

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    return {
                        "sound_volume": data.get("sound_volume", default_settings["sound_volume"]),
                        "music_volume": data.get("music_volume", default_settings["music_volume"]),
                        "show_fps": data.get("show_fps", default_settings["show_fps"])
                    }
            except:
                pass

        return default_settings

    def _sync_with_save_manager(self):
        """Sincroniza o progresso atual com o SaveManager e salva imediatamente"""
        # Atualiza o game_state no save_data
        if "game_state" not in self.save_manager.save_data:
            self.save_manager.save_data["game_state"] = {}

        self.save_manager.save_data["game_state"].update({
            "unlocked_phases": self.progress["unlocked_phases"],
            "completed_phases": self.progress["completed_phases"],
            "current_chapter": self.progress["current_chapter"],
            "current_phase": self.progress["current_phase"],
            "stars": self.progress["stars"]
        })

        # Salva no arquivo atual usando o SaveManager
        if self.save_manager.current_save_file:
            # Importante: usar save_game do SaveManager diretamente
            self.save_manager.save_game(
                player=None,  # O jogador será salvo separadamente pelo auto_save()
                game_state=self.save_manager.save_data["game_state"],
                save_name=self.save_manager.save_data["meta"]["save_name"],
                slot=self.save_manager.current_save_file
            )
            print(f"[PROGRESS] Progresso sincronizado com save {self.save_manager.current_save_file}")

    def get_next_phase(self, phase_id: str) -> Optional[str]:
        """Retorna o ID da próxima fase"""
        if "-" not in phase_id:
            return None

        chapter, phase = map(int, phase_id.split("-"))

        from src.config.phase_catalog import phase_catalog
        chapter_phases = phase_catalog.get_chapter_phases(chapter)

        if not chapter_phases:
            return None

        current_index = None
        for i, p in enumerate(chapter_phases):
            if p["number"] == phase:
                current_index = i
                break

        if current_index is None:
            return None

        if current_index < len(chapter_phases) - 1:
            next_phase = chapter_phases[current_index + 1]
            return f"{chapter}-{next_phase['number']}"
        else:
            next_chapter = chapter + 1
            next_chapter_phases = phase_catalog.get_chapter_phases(next_chapter)
            if next_chapter_phases:
                return f"{next_chapter}-{next_chapter_phases[0]['number']}"

        return None

    def unlock_next_phase(self, completed_phase_id: str) -> bool:
        """Desbloqueia a próxima fase após completar a atual"""
        next_phase_id = self.get_next_phase(completed_phase_id)

        if next_phase_id and next_phase_id not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(next_phase_id)
            self.progress["unlocked_phases"].sort()
            print(f"🎉 Nova fase desbloqueada: {next_phase_id}!")
            return True
        elif next_phase_id:
            print(f"Fase {next_phase_id} já estava desbloqueada")
        else:
            print("🏆 Parabéns! Você completou todas as fases disponíveis!")
        return False

    def complete_phase(self, phase_id: str, stars: int = 0):
        """Marca uma fase como completada e salva imediatamente"""
        phase_id = str(phase_id)

        print(f"\n[PROGRESS] ===== COMPLETING PHASE: {phase_id} with {stars} stars =====")
        print(f"[PROGRESS] Estado atual:")
        print(f"  Unlocked: {self.progress['unlocked_phases']}")
        print(f"  Completed: {self.progress['completed_phases']}")

        # Verifica se já foi completada
        if phase_id in self.progress["completed_phases"]:
            if stars > self.progress["stars"].get(phase_id, 0):
                self.progress["stars"][phase_id] = stars
                print(f"⭐ Nova pontuação na fase {phase_id}: {stars} estrelas!")
            else:
                print(f"[PROGRESS] Fase {phase_id} já estava completada")
        else:
            # Primeira vez completando a fase
            self.progress["completed_phases"].append(phase_id)
            self.progress["completed_phases"].sort()
            self.progress["stars"][phase_id] = stars
            print(f"✅ Fase {phase_id} completada com {stars} estrelas!")

            # Desbloqueia a próxima fase
            next_phase = self.get_next_phase(phase_id)
            print(f"[PROGRESS] Próxima fase seria: {next_phase}")
            self.unlock_next_phase(phase_id)

        print(f"[PROGRESS] Estado após atualização:")
        print(f"  Unlocked: {self.progress['unlocked_phases']}")
        print(f"  Completed: {self.progress['completed_phases']}")

        # SINCRONIZA IMEDIATAMENTE COM O SAVE MANAGER
        self._sync_with_save_manager()
        print(f"[PROGRESS] Sync com SaveManager concluído")

    def is_phase_unlocked(self, phase_id: str) -> bool:
        """Verifica se uma fase está desbloqueada"""
        phase_id = str(phase_id)
        return phase_id in self.progress["unlocked_phases"]

    def is_phase_completed(self, phase_id: str) -> bool:
        """Verifica se uma fase foi completada"""
        phase_id = str(phase_id)
        return phase_id in self.progress["completed_phases"]

    def get_chapter_progress(self, chapter_id: int, chapter_phases: List[str]) -> Dict:
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

    def reload_progress(self):
        """Recarrega o progresso do save atual"""
        self.progress = self._load_from_save_manager()
        print("[PROGRESS] Progresso recarregado do SaveManager")

    def reset_progress(self):
        """Reseta todo o progresso"""
        self.progress = {
            "unlocked_phases": ["1-1"],
            "completed_phases": [],
            "current_chapter": 1,
            "current_phase": 1,
            "stars": {},
            "settings": self.progress.get("settings", {})
        }
        self._sync_with_save_manager()
        print("Progresso resetado!")

    def unlock_specific_phase(self, phase_id: str) -> bool:
        """Desbloqueia uma fase específica manualmente"""
        phase_id = str(phase_id)

        if phase_id not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(phase_id)
            self.progress["unlocked_phases"].sort()
            self._sync_with_save_manager()
            print(f"Fase {phase_id} desbloqueada manualmente!")
            return True
        return False


# Instância global
progress_manager = ProgressManager()
