# src/managers/wave/wave_manager.py
import math
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from src.entities.pokemon import Pokemon
from src.scenes.game_scene.components.managers.wave.enemy_spawner import EnemySpawner
from src.scenes.game_scene.components.managers.wave.item_decision import ItemDecision, DirectionDecision
from src.scenes.game_scene.components.managers.wave.path_tracker import PathTracker


class WaveManager:
    """
    Gerenciador de waves com responsabilidades claras:
    - Spawnar inimigos
    - Gerenciar movimento dos inimigos (via PathTracker)
    - Processar chegada ao início/fim
    - Processar captura de itens
    """

    def __init__(self, phase_loader, game_scene):
        self.game_scene = game_scene
        self.spawner = EnemySpawner(phase_loader, self)
        self.path_tracker = PathTracker()
        self.item_decision = ItemDecision()

        # Estado
        self.active_enemies: List['Pokemon'] = []
        self.paused = False
        self.target_items = []

        # Configurações
        self.gold_per_defeat = 10
        self.total_gold_earned = 0

        # Carrega dados das waves
        self._load_wave_data(phase_loader)

    def _load_wave_data(self, phase_loader):
        """Carrega configurações de waves"""
        raw_data = phase_loader.get_waves_data()
        self.waves_data = raw_data if raw_data else []

        # Inicializa estado do spawner
        self.spawner.initialize_waves(self.waves_data)

    def set_paths(self, paths):
        """Define os paths disponíveis"""
        self.path_tracker.set_paths(paths)

    def set_target_items(self, items):
        """Define os itens alvo"""
        self.target_items = items

    def reset_gold(self):
        """Reseta o ouro acumulado"""
        self.total_gold_earned = 0

    def start_all_waves(self):
        """Inicia todas as waves de todos os paths"""
        return self.spawner.start_all_waves()

    def has_more_waves(self) -> bool:
        """Verifica se ainda existem waves"""
        return self.spawner.has_more_waves()

    def is_wave_completely_finished(self) -> bool:
        """
        Verifica se todas as waves terminaram E TODOS os inimigos foram DERROTADOS.
        Inclui bosses - a wave só termina quando todos os inimigos morreram.
        """
        # Se ainda tem inimigos vivos (qualquer tipo), a wave não acabou
        if self.active_enemies:
            return False

        # Verifica se o spawner ainda tem waves para spawnar ou ativas
        if self.spawner.has_more_waves():
            return False

        if self.spawner.has_active_waves():
            return False

        return True

    def get_current_wave_info(self) -> dict:
        """Retorna informações consolidadas das waves"""
        return self.spawner.get_current_wave_info(len(self.active_enemies))

    def get_total_gold_earned(self) -> int:
        """Retorna o total de ouro acumulado"""
        return self.total_gold_earned

    def update(self, dt: float) -> List['Pokemon']:
        """
        Atualiza o sistema de waves
        Retorna lista de inimigos que chegaram ao fim (para processar roubo de item)
        """
        if self.paused:
            return []

        enemies_at_end = []
        enemies_at_start = []

        # 1. Spawnar novos inimigos
        new_enemies = self.spawner.update(dt)
        for enemy in new_enemies:
            # Garante que screen_manager está configurado
            if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
                if not hasattr(enemy, 'screen_manager') or enemy.screen_manager is None:
                    enemy.screen_manager = self.game_scene.screen_manager
                if not hasattr(enemy, 'camera') or enemy.camera is None:
                    enemy.camera = self.game_scene.camera

            self.active_enemies.append(enemy)
            # Configura batalha para o novo inimigo
            if self.game_scene and hasattr(self.game_scene, 'battle_system'):
                enemy.set_battle_system(self.game_scene.battle_system)
                self.game_scene.battle_system.set_effect_manager_for_pokemon(enemy)

            print(f"[WaveManager] SPAWN: {enemy.name} (BOSS={enemy.is_boss}) em ({enemy.x:.0f}, {enemy.y:.0f})")

        # 2. Atualizar movimento de cada inimigo
        for enemy in self.active_enemies[:]:
            # ===== VERIFICA SE O INIMIGO ACABOU DE SPAWNAR =====
            # Apenas atualiza o timer, mas NÃO impede o movimento
            if hasattr(enemy, '_just_spawned') and enemy._just_spawned:
                enemy._spawn_timer -= dt
                if enemy._spawn_timer <= 0:
                    enemy._just_spawned = False
                    print(f"[WaveManager] {enemy.name} terminou período de spawn invulnerável")

            # Garante que screen_manager está configurado para inimigos existentes
            if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
                if not hasattr(enemy, 'screen_manager') or enemy.screen_manager is None:
                    enemy.screen_manager = self.game_scene.screen_manager
                if not hasattr(enemy, 'camera') or enemy.camera is None:
                    enemy.camera = self.game_scene.camera

            # Pula se o inimigo não tem path (não deveria acontecer)
            if not hasattr(enemy, 'path') or not enemy.path:
                print(f"[WaveManager] ERRO: {enemy.name} não tem path atribuído!")
                continue

            # Atualiza movimento via path_tracker - retorna (arrived_at_end, arrived_at_start)
            arrived_at_end, arrived_at_start = self.path_tracker.update_movement(enemy, dt)

            if arrived_at_end:
                print(f"[WaveManager] DETECTADO: {enemy.name} (BOSS={enemy.is_boss}) chegou ao FIM!")
                enemies_at_end.append(enemy)
                continue

            if arrived_at_start:
                print(f"[WaveManager] DETECTADO: {enemy.name} (BOSS={enemy.is_boss}) chegou ao INÍCIO!")
                enemies_at_start.append(enemy)
                continue

            # Verifica captura de item
            self._check_item_capture(enemy)

            # Verifica se o inimigo ainda está vivo
            if not enemy.is_alive():
                if not getattr(enemy, '_marked_for_removal', False):
                    self._handle_enemy_death(enemy)
                continue

            # Atualiza animação
            self._update_animation(enemy, dt)

        # 3. Processar chegadas ao FIM
        for enemy in enemies_at_end:
            if enemy in self.active_enemies and not getattr(enemy, '_marked_for_removal', False):
                self._handle_arrival_at_end(enemy)

        # 4. Processar chegadas ao INÍCIO
        for enemy in enemies_at_start:
            if enemy in self.active_enemies and not getattr(enemy, '_marked_for_removal', False):
                self._handle_arrival_at_start(enemy)

        # 5. Remover inimigos marcados para remoção
        before_cleanup = len(self.active_enemies)
        self.active_enemies = [e for e in self.active_enemies if not getattr(e, '_marked_for_removal', False)]
        after_cleanup = len(self.active_enemies)

        if before_cleanup != after_cleanup:
            print(
                f"[WaveManager] Limpeza: {before_cleanup - after_cleanup} inimigos removidos. Restam: {after_cleanup}")

        return enemies_at_end

    def _check_item_capture(self, enemy: 'Pokemon'):
        """Verifica se o inimigo capturou um item"""
        if not enemy.is_alive():
            return

        if enemy.is_carrying:
            return

        if not self.target_items:
            return

        available_items = [item for item in self.target_items if item.is_protected and not item.carried_by]
        if not available_items:
            return

        for item in available_items:
            if self._is_close_to_item(enemy, item):
                self._capture_item(enemy, item)
                break

    def _is_close_to_item(self, enemy: 'Pokemon', item) -> bool:
        """Verifica se o inimigo está perto do item"""
        item_x, item_y = item.get_capture_position()
        dx = enemy.x - item_x
        dy = enemy.y - item_y
        distance = math.sqrt(dx * dx + dy * dy)
        capture_range = enemy.capture_range
        return distance < capture_range

    def _capture_item(self, enemy: 'Pokemon', item):
        """Captura o item e decide direção"""
        item.start_capture(enemy)
        enemy.is_carrying = item

        # DECISÃO DE DIREÇÃO
        decision = self.item_decision.decide_direction(
            enemy,
            self.path_tracker.get_path(enemy)
        )

        if decision == DirectionDecision.REVERSE:
            # Inverte o path para voltar
            self.path_tracker.reverse_path(enemy)
            enemy.is_returning_with_item = True
            print(f"[ITEM] {enemy.name} decidiu VOLTAR com {item.item_name}")
        else:
            print(f"[ITEM] {enemy.name} decidiu CONTINUAR com {item.item_name}")

    def _is_loop_path(self, enemy: 'Pokemon') -> bool:
        """Verifica se o path é um loop (início = fim)"""
        if not enemy.path or len(enemy.path) < 2:
            return False
        start = enemy.path[0]
        end = enemy.path[-1]
        # Verifica se início e fim são o mesmo ponto (ou muito próximos)
        return math.hypot(start[0] - end[0], start[1] - end[1]) < 10.0

    def _handle_arrival_at_end(self, enemy: 'Pokemon'):
        """Processa quando um inimigo chega ao FIM do path."""
        if getattr(enemy, '_marked_for_removal', False):
            return

        print(f"[WaveManager] {enemy.name} (BOSS={enemy.is_boss}) chegou ao FIM!")

        if enemy.is_carrying:
            self._steal_item(enemy)

        if enemy.is_boss:
            if self._is_loop_path(enemy):
                # Path em loop: reseta para o início e continua
                print(f"[BOSS] {enemy.name} - PATH EM LOOP, resetando para o início")
                enemy.path_index = 0
                # Reseta flags
                self.path_tracker.reset_enemy_state(enemy)
            else:
                # Path linear: inverte direção
                print(f"[BOSS] {enemy.name} - INVERTENDO DIREÇÃO")
                self.path_tracker.reverse_direction_simple(enemy)
        else:
            self._remove_enemy(enemy)

    def _handle_arrival_at_start(self, enemy: 'Pokemon'):
        """Processa quando um inimigo chega ao INÍCIO do path."""
        if getattr(enemy, '_marked_for_removal', False):
            return

        print(f"[WaveManager] {enemy.name} (BOSS={enemy.is_boss}) chegou ao INÍCIO!")

        if enemy.is_carrying:
            self._steal_item(enemy)

        if enemy.is_boss:
            if self._is_loop_path(enemy):
                # Path em loop: apenas continua (não faz nada)
                print(f"[BOSS] {enemy.name} - PATH EM LOOP, continuando...")
                # Não faz nada - o boss já está no caminho certo
            else:
                # Path linear: inverte direção
                print(f"[BOSS] {enemy.name} - INVERTENDO DIREÇÃO")
                self.path_tracker.reverse_direction_simple(enemy)
        else:
            self._remove_enemy(enemy)

    def _handle_enemy_death(self, enemy: 'Pokemon'):
        """Processa morte de um inimigo (inclui boss!)"""
        print(f"[WaveManager] {enemy.name} (BOSS={enemy.is_boss}) MORREU em batalha!")

        # Distribui XP
        self._distribute_xp(enemy)
        self.total_gold_earned += self.gold_per_defeat

        # Se estava carregando item, o item volta para o chão (não é roubado)
        if enemy.is_carrying is not None:
            try:
                item_name = enemy.is_carrying.item_name
                print(f"[ITEM] {enemy.name} morreu carregando {item_name} - item será dropado")
                enemy.is_carrying.reset_capture()
                enemy.is_carrying = None
            except Exception as e:
                print(f"[ERROR] Falha ao processar item de {enemy.name}: {e}")
                enemy.is_carrying = None

        self._remove_enemy(enemy)

    def _steal_item(self, enemy: 'Pokemon'):
        """
        Item é roubado (chegou ao fim OU início com ele)
        Isso causa GAME OVER se todos os itens forem roubados
        """
        if enemy.is_carrying is None:
            print(f"[WARNING] Tentativa de roubar item de {enemy.name} mas ele não está carregando nada")
            return

        item = enemy.is_carrying
        print(f"[ITEM] {enemy.name} ROUBOU {item.item_name}!")

        # Marca o item como roubado
        item.is_protected = False
        item.is_stolen = True
        item.carried_by = None
        enemy.is_carrying = None

        if hasattr(self.game_scene, 'target_item_manager'):
            self.game_scene.target_item_manager.mark_item_as_stolen(item)

        remaining = len([i for i in self.target_items if i.is_protected])
        print(f"[ITEM] {item.item_name} foi ROUBADO! Itens restantes protegidos: {remaining}")

    def _remove_enemy(self, enemy: 'Pokemon'):
        """Remove inimigo da lista ativa"""
        if enemy in self.active_enemies:
            enemy._marked_for_removal = True
            print(f"[WaveManager] Marcando {enemy.name} para remoção")

            if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
                enemy.effect_manager.unregister_pokemon(enemy)
            enemy.clear_damage_tracking()

    def _distribute_xp(self, defeated_enemy: 'Pokemon'):
        """Distribui XP quando um inimigo é derrotado"""
        contributors = defeated_enemy.get_xp_contributors()
        if not contributors:
            return

        base_xp = 15 + (defeated_enemy.level * 5)

        # Bônus para boss
        if defeated_enemy.is_boss:
            base_xp = int(base_xp * 3)  # Boss dá 3x mais XP
            print(f"[XP] BOSS derrotado! XP base: {base_xp}")

        if defeated_enemy.is_shiny:
            base_xp = int(base_xp * 1.5)

        total_contribution = defeated_enemy.get_total_contribution()
        if total_contribution <= 0:
            total_contribution = len(contributors)

        placement_manager = None
        if self.game_scene and hasattr(self.game_scene, 'placement_manager'):
            placement_manager = self.game_scene.placement_manager

        if not placement_manager:
            return

        for attacker_id, contribution in contributors:
            proportion = contribution / total_contribution
            xp_gained = int(base_xp * proportion)

            if xp_gained < 1 and contribution > 0:
                xp_gained = 1

            for pokemon in placement_manager.placed_pokemon:
                if id(pokemon) == attacker_id and pokemon.is_alive():
                    pokemon.gain_xp(xp_gained)
                    break

    def _update_animation(self, enemy: 'Pokemon', dt: float):
        """Atualiza animação do inimigo"""
        if hasattr(enemy, 'animation_timer'):
            enemy.animation_timer += dt
            if enemy.animation_timer >= enemy.animation_speed:
                enemy.animation_timer = 0
                if enemy.inmap_frames and enemy.current_direction in enemy.inmap_frames:
                    frames_list = enemy.inmap_frames[enemy.current_direction]
                    if frames_list:
                        enemy.current_frame = (enemy.current_frame + 1) % len(frames_list)
                        enemy.sprite = frames_list[enemy.current_frame]

    def remove_enemy(self, enemy: 'Pokemon'):
        """Remove um inimigo (para captura)"""
        self._remove_enemy(enemy)