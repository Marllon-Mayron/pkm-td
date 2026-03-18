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
        # Converte progresso antigo para o novo formato
        self._migrate_old_progress()

    def _migrate_old_progress(self):
        """Converte progresso antigo (números) para novo formato (strings)"""
        changed = False

        # Converte unlocked_phases de int para string
        new_unlocked = []
        for phase in self.progress["unlocked_phases"]:
            if isinstance(phase, int):
                new_unlocked.append(str(phase))
                changed = True
            else:
                new_unlocked.append(phase)
        if changed:
            self.progress["unlocked_phases"] = new_unlocked

        # Converte completed_phases de int para string
        new_completed = []
        for phase in self.progress["completed_phases"]:
            if isinstance(phase, int):
                new_completed.append(str(phase))
                changed = True
            else:
                new_completed.append(phase)
        if changed:
            self.progress["completed_phases"] = new_completed

        # Converte stars keys de int para string
        new_stars = {}
        for key, value in self.progress["stars"].items():
            if isinstance(key, int):
                new_stars[str(key)] = value
                changed = True
            else:
                new_stars[key] = value
        if changed:
            self.progress["stars"] = new_stars

        if changed:
            self.save_progress()
            print("Progresso migrado para novo formato (strings)")

    def load_progress(self):
        """Carrega o progresso salvo"""
        default_progress = {
            "unlocked_phases": ["1-1"],  # Fase 1-1 sempre desbloqueada
            "completed_phases": [],      # Fases completadas
            "current_chapter": 1,
            "stars": {},                  # Estrelas por fase (para futuro)
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