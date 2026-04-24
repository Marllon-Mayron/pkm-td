# src/managers/progress.py

"""
Sistema de progresso do jogador - Integrado com SaveManager
"""
import json
import os
from typing import Dict, List, Optional


class ProgressManager:
    def __init__(self):
        from managers.save_manager import save_manager
        from src.config.settings import settings

        self.save_manager = save_manager
        self.settings = settings
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
            "stars": converted_stars
        }

    def _load_settings_from_save(self):
        """Carrega configurações do save atual"""
        if self.save_manager.current_save_file:
            settings_data = self.save_manager.save_data.get("settings", {})
            if settings_data:
                # Aplica configurações ao objeto settings global
                self.settings.sfx_volume = settings_data.get("sfx_volume", 0.7)
                self.settings.music_volume = settings_data.get("music_volume", 0.5)
                self.settings.music_enabled = settings_data.get("music_enabled", True)
                self.settings.sfx_enabled = settings_data.get("sfx_enabled", True)
                self.settings.fullscreen = settings_data.get("fullscreen", False)
                self.settings.vsync = settings_data.get("vsync", True)
                self.settings.target_fps = settings_data.get("target_fps", 60)

                # Aplica volumes no sound_manager
                from managers.sounds.sound_manager import sound_manager
                if self.settings.sfx_enabled:
                    sound_manager.set_sfx_volume(self.settings.sfx_volume)
                else:
                    sound_manager.set_sfx_volume(0)

                if self.settings.music_enabled:
                    sound_manager.set_music_volume(self.settings.music_volume)
                else:
                    sound_manager.set_music_volume(0)

                print(
                    f"[PROGRESS] Configurações carregadas do save: Música={self.settings.music_volume} ({'ON' if self.settings.music_enabled else 'OFF'}), SFX={self.settings.sfx_volume}")
                return True

        return False

    def _save_settings_to_save(self):
        """Salva as configurações atuais no save manager"""
        if self.save_manager.current_save_file:
            self.save_manager.save_settings(self.settings)

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

        # Salva as configurações atuais
        self.save_manager.save_data["settings"] = {
            "sfx_volume": self.settings.sfx_volume,
            "music_volume": self.settings.music_volume,
            "music_enabled": self.settings.music_enabled,
            "sfx_enabled": self.settings.sfx_enabled,
            "fullscreen": self.settings.fullscreen,
            "vsync": self.settings.vsync,
            "target_fps": self.settings.target_fps
        }

        # Salva no arquivo atual usando o SaveManager
        if self.save_manager.current_save_file:
            # Salva o arquivo completo
            filename = f"save_{self.save_manager.current_save_file}.json"
            filepath = os.path.join(self.save_manager.save_dir, filename)

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.save_manager.save_data, f, indent=2, ensure_ascii=False)
                print(f"[PROGRESS] Progresso sincronizado com save {self.save_manager.current_save_file}")
                print(
                    f"[PROGRESS] Configurações salvas: Música={self.settings.music_volume}, SFX={self.settings.sfx_volume}")
            except Exception as e:
                print(f"[ERRO] Falha ao sincronizar progresso: {e}")

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
        self._load_settings_from_save()  # Também recarrega as configurações
        print("[PROGRESS] Progresso recarregado do SaveManager")

    def reset_progress(self):
        """Reseta todo o progresso"""
        self.progress = {
            "unlocked_phases": ["1-1"],
            "completed_phases": [],
            "current_chapter": 1,
            "current_phase": 1,
            "stars": {}
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