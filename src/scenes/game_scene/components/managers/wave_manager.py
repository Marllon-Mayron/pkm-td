# src/managers/wave/wave_manager.py
import math
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from src.entities.pokemon import Pokemon
from src.scenes.game_scene.components.managers.wave.enemy_spawner import EnemySpawner
from src.scenes.game_scene.components.managers.wave.item_decision import ItemDecision, DirectionDecision
from src.scenes.game_scene.components.managers.wave.path_tracker import PathTracker


# CORRIGIR: os imports estão apontando para o caminho errado


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
        Verifica se todas as waves terminaram.
        Boss NÃO impede a conclusão (ele continua andando).
        """
        # Verifica se há inimigos NÃO-BOSS vivos
        non_boss_enemies = [e for e in self.active_enemies if not getattr(e, 'is_boss', False)]
        if non_boss_enemies:
            return False

        # Verifica se o spawner ainda tem waves ativas
        return not self.spawner.has_active_waves()

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

        # 2. Atualizar movimento de cada inimigo
        for enemy in self.active_enemies[:]:
            # Garante que screen_manager está configurado para inimigos existentes
            if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
                if not hasattr(enemy, 'screen_manager') or enemy.screen_manager is None:
                    enemy.screen_manager = self.game_scene.screen_manager
                if not hasattr(enemy, 'camera') or enemy.camera is None:
                    enemy.camera = self.game_scene.camera

            # Pula se o inimigo não tem path (não deveria acontecer)
            if not hasattr(enemy, 'path') or not enemy.path:
                continue

            # Atualiza movimento via path_tracker
            arrived_at_end = self.path_tracker.update_movement(enemy, dt)

            if arrived_at_end:
                enemies_at_end.append(enemy)
                continue

            # Verifica captura de item
            self._check_item_capture(enemy)

            # ===== CORREÇÃO: Verifica se o inimigo ainda está vivo =====
            if not enemy.is_alive():
                # Verifica se já não foi marcado para remoção
                if not getattr(enemy, '_marked_for_removal', False):
                    self._handle_enemy_death(enemy)
                continue

            # Atualiza animação
            self._update_animation(enemy, dt)

        # 3. Processar chegadas ao fim
        for enemy in enemies_at_end:
            # ===== CORREÇÃO: Verifica se o inimigo ainda não foi removido =====
            if enemy in self.active_enemies and not getattr(enemy, '_marked_for_removal', False):
                self._handle_arrival_at_end(enemy)

        # 4. Remover inimigos marcados para remoção
        self.active_enemies = [e for e in self.active_enemies if not getattr(e, '_marked_for_removal', False)]

        return enemies_at_end

    def _check_item_capture(self, enemy: 'Pokemon'):
        """Verifica se o inimigo capturou um item"""
        if not enemy.is_alive():
            return

        if enemy.is_carrying:
            return

        if not self.target_items:
            return

        # ===== DEBUG: Mostra quantos itens disponíveis =====
        available_items = [item for item in self.target_items if item.is_protected and not item.carried_by]
        if not available_items:
            return

        for item in available_items:
            if self._is_close_to_item(enemy, item):
                self._capture_item(enemy, item)
                break

    def _is_close_to_item(self, enemy: 'Pokemon', item) -> bool:
        """Verifica se o inimigo está perto do item"""
        # Usa o método get_capture_position do item
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

        # DECISÃO DE DIREÇÃO - centralizada no ItemDecision
        decision = self.item_decision.decide_direction(
            enemy,
            self.path_tracker.get_path(enemy)
        )

        if decision == DirectionDecision.REVERSE:
            self.path_tracker.reverse_direction(enemy)
            enemy.is_returning_with_item = True
        # Se for CONTINUE, não faz nada

    def _handle_arrival_at_end(self, enemy: 'Pokemon'):
        """Processa quando um inimigo chega ao fim do path"""
        if getattr(enemy, 'is_boss', False):
            # Boss: remove item se tiver e volta
            if enemy.is_carrying:
                self._steal_item(enemy)
            self.path_tracker.reverse_direction(enemy)
        else:
            # Comum: some e rouba item se tiver
            if enemy.is_carrying:
                self._steal_item(enemy)
            self._remove_enemy(enemy)

    def _handle_enemy_death(self, enemy: 'Pokemon'):
        """Processa morte de um inimigo"""
        # Distribui XP
        self._distribute_xp(enemy)
        self.total_gold_earned += self.gold_per_defeat

        # ===== CORREÇÃO: Verifica se enemy.is_carrying não é None antes de acessar =====
        if enemy.is_carrying is not None:
            try:
                # Libera item se estiver carregando (volta ao chão)
                item_name = enemy.is_carrying.item_name
                print(f"[ITEM] {enemy.name} morreu carregando {item_name} - item será dropado")
                enemy.is_carrying.reset_capture()
                enemy.is_carrying = None
            except Exception as e:
                print(f"[ERROR] Falha ao processar item de {enemy.name}: {e}")
                enemy.is_carrying = None
        else:
            print(f"[ITEM] {enemy.name} morreu sem carregar item")

        self._remove_enemy(enemy)

    def _steal_item(self, enemy: 'Pokemon'):
        """Item é roubado (chegou ao fim com ele)"""
        # ===== CORREÇÃO: Verifica se enemy.is_carrying não é None =====
        if enemy.is_carrying is None:
            print(f"[WARNING] Tentativa de roubar item de {enemy.name} mas ele não está carregando nada")
            return

        item = enemy.is_carrying
        print(f"[ITEM] {enemy.name} roubou {item.item_name}!")
        item.is_protected = False
        item.is_stolen = True
        item.carried_by = None
        enemy.is_carrying = None

        if hasattr(self.game_scene, 'target_item_manager'):
            self.game_scene.target_item_manager.mark_item_as_stolen(item)

        print(f"[ITEM] {item.item_name} foi ROUBADO por {enemy.name}!")

    def _remove_enemy(self, enemy: 'Pokemon'):
        """Remove inimigo da lista ativa"""
        if enemy in self.active_enemies:
            # Marca para remoção (evita modificar lista durante iteração)
            enemy._marked_for_removal = True

            if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
                enemy.effect_manager.unregister_pokemon(enemy)
            enemy.clear_damage_tracking()

    def _distribute_xp(self, defeated_enemy: 'Pokemon'):
        """Distribui XP quando um inimigo é derrotado"""
        contributors = defeated_enemy.get_xp_contributors()
        if not contributors:
            return

        # Base XP: maior para inimigos mais fortes
        base_xp = 15 + (defeated_enemy.level * 5)

        # Bônus para shiny
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

            # Encontra o Pokémon pelo ID
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