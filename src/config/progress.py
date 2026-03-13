"""
Sistema de progresso do jogador
"""
import json
import os
from pathlib import Path


class ProgressManager:
    def __init__(self):
        self.save_file = Path("save_data.json")
        self.progress = self.load_progress()

    def load_progress(self):
        """Carrega o progresso salvo"""
        default_progress = {
            "unlocked_phases": [1],  # Fase 1 sempre desbloqueada
            "completed_phases": [],  # Fases completadas
            "current_chapter": 1,
            "stars": {},  # Estrelas por fase (para futuro)
            "settings": {
                "sound_volume": 0.7,
                "music_volume": 0.5,
                "show_fps": False
            }
        }

        if self.save_file.exists():
            try:
                with open(self.save_file, 'r') as f:
                    saved_data = json.load(f)
                    # Merge com default para garantir campos
                    for key in default_progress:
                        if key not in saved_data:
                            saved_data[key] = default_progress[key]
                    return saved_data
            except:
                print("Erro ao carregar save, criando novo progresso")
                return default_progress
        else:
            print("Nenhum save encontrado, criando novo progresso")
            return default_progress

    def save_progress(self):
        """Salva o progresso"""
        try:
            with open(self.save_file, 'w') as f:
                json.dump(self.progress, f, indent=4)
            print("Progresso salvo com sucesso")
        except:
            print("Erro ao salvar progresso")

    def unlock_next_phase(self, completed_phase):
        """Desbloqueia a próxima fase após completar a atual"""
        next_phase = completed_phase + 1
        if next_phase not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(next_phase)
            self.progress["unlocked_phases"].sort()
            print(f"Fase {next_phase} desbloqueada!")
            self.save_progress()

    def complete_phase(self, phase_number, stars=0):
        """Marca uma fase como completada"""
        if phase_number not in self.progress["completed_phases"]:
            self.progress["completed_phases"].append(phase_number)
            self.progress["completed_phases"].sort()
            self.progress["stars"][str(phase_number)] = stars
            self.unlock_next_phase(phase_number)
            self.save_progress()

    def is_phase_unlocked(self, phase_number):
        """Verifica se uma fase está desbloqueada"""
        return phase_number in self.progress["unlocked_phases"]

    def is_phase_completed(self, phase_number):
        """Verifica se uma fase foi completada"""
        return phase_number in self.progress["completed_phases"]

    def get_chapter_progress(self, chapter_id, chapter_phases):
        """Retorna progresso de um capítulo"""
        total = len(chapter_phases)
        unlocked = sum(1 for p in chapter_phases if self.is_phase_unlocked(p))
        completed = sum(1 for p in chapter_phases if self.is_phase_completed(p))
        return {
            "total": total,
            "unlocked": unlocked,
            "completed": completed,
            "percentage": (completed / total * 100) if total > 0 else 0
        }

    def reset_progress(self):
        """Reseta todo o progresso (para testes)"""
        self.progress = {
            "unlocked_phases": [1],
            "completed_phases": [],
            "current_chapter": 1,
            "stars": {},
            "settings": self.progress["settings"]
        }
        self.save_progress()
        print("Progresso resetado!")


# Instância global
progress_manager = ProgressManager()