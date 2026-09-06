# src/managers/wave/wave_manager.py
import math
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from src.battle.attack_pattern import AttackPattern
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
        self._boss_defeated = False

        # Configurações
        self.gold_per_defeat = 10
        self.total_gold_earned = 0
        self.total_enemies_defeated = 0
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

    def initialize_condition(self):
        """Inicializa a condição atual baseada no estado dia/noite da fase"""
        if self.game_scene and hasattr(self.game_scene, 'day_night_weather'):
            day_night = self.game_scene.day_night_weather.day_night_state
            if day_night and day_night.active:
                condition = day_night.type.value
                self.spawner.set_condition(condition)
                print(f"[WaveManager] Condição inicializada: {condition}")
                return
        # Fallback para "any"
        self.spawner.set_condition("any")
        print("[WaveManager] Condição inicializada: any (fallback)")

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

        # ===== QUANDO A WAVE TERMINA, LIMPA OS PARTICIPANTES DA BATALHA =====
        if self.game_scene and hasattr(self.game_scene, 'battle_system'):
            self.game_scene.battle_system.clear_participants()
            print(f"[XP] Participantes da batalha limpos ao final da wave")

        return True

    def get_current_wave_info(self) -> dict:
        """Retorna informações consolidadas das waves"""
        return self.spawner.get_current_wave_info(len(self.active_enemies))

    def get_total_gold_earned(self) -> int:
        """Retorna o total de ouro acumulado"""
        return self.total_gold_earned

    def _update_enemy_combat(self, enemy: 'Pokemon', dt: float):
        """
        Atualiza combate do inimigo - DELEGA para o sistema unificado.
        A única diferença é que inimigos NÃO param para atacar.
        """
        if not enemy.is_alive() or enemy.is_defeated:
            return

        # Se o inimigo é passivo, não ataca
        if hasattr(enemy, 'attack_pattern') and enemy.attack_pattern == AttackPattern.PASSIVE:
            return

        # DELEGA para o sistema unificado de combate
        # O combat.update_combat já lida com toda a lógica, incluindo a diferença
        # entre wild e not wild (inimigos atacam em movimento)
        if hasattr(self.game_scene, 'placement_manager'):
            all_pokemon = self.game_scene.placement_manager.placed_pokemon
            enemy.combat.update_combat(dt, all_pokemon)

    def update(self, dt: float) -> List['Pokemon']:
        """
        Atualiza o sistema de waves
        Retorna lista de inimigos que chegaram ao fim (para processar roubo de item)
        """
        if self.paused:
            return []

        if self.game_scene and hasattr(self.game_scene, 'day_night_weather'):
            day_night = self.game_scene.day_night_weather.day_night_state
            if day_night:
                condition = day_night.type.value
                self.spawner.set_condition(condition)

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

            # ===== PASSA O PATH TRACKER PARA O INIMIGO =====
            enemy._path_tracker = self.path_tracker

            self.active_enemies.append(enemy)
            # Configura batalha para o novo inimigo
            if self.game_scene and hasattr(self.game_scene, 'battle_system'):
                enemy.set_battle_system(self.game_scene.battle_system)
                self.game_scene.battle_system.set_effect_manager_for_pokemon(enemy)

            print(f"[WaveManager] SPAWN: {enemy.name} (BOSS={enemy.is_boss}) em ({enemy.x:.0f}, {enemy.y:.0f})")

        # 2. Atualizar movimento de cada inimigo
        for enemy in self.active_enemies[:]:
            # ===== VERIFICA SE O INIMIGO ACABOU DE SPAWNAR =====
            if hasattr(enemy, '_just_spawned') and enemy._just_spawned:
                enemy._spawn_timer -= dt
                if enemy._spawn_timer <= 0:
                    enemy._just_spawned = False
                    print(f"[WaveManager] {enemy.name} terminou período de spawn invulnerável")

            # Garante que screen_manager está configurado
            if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
                if not hasattr(enemy, 'screen_manager') or enemy.screen_manager is None:
                    enemy.screen_manager = self.game_scene.screen_manager
                if not hasattr(enemy, 'camera') or enemy.camera is None:
                    enemy.camera = self.game_scene.camera

            # Pula se o inimigo não tem path
            if not hasattr(enemy, 'path') or not enemy.path:
                continue

            # ===== VERIFICA SE ESTÁ PRESO NA TEIA (SPIDER WEB) =====
            if hasattr(enemy, '_spider_web_active') and enemy._spider_web_active:
                # Inimigo preso: NÃO se move, NÃO ataca
                # Força a posição original (caso algo tente mover)
                if hasattr(enemy, '_spider_web_locked_x'):
                    enemy.x = enemy._spider_web_locked_x
                    enemy.y = enemy._spider_web_locked_y
                    enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

                # Apenas atualiza animação (para não congelar visualmente)
                self._update_animation(enemy, dt)

                # Decrementa o contador do Spider Web (a cada atualização, mas limitado)
                # Na verdade, decrementamos ao tentar atacar. Aqui só mantemos
                continue

            # ===== VERIFICA SE DEVE IGNORAR O PATH (EM COMBATE) =====
            should_skip_path = False

            if hasattr(enemy, 'target') and enemy.target and enemy.target.is_alive():
                # Verifica se está perto do alvo ou atacando
                dx = enemy.target.x - enemy.x
                dy = enemy.target.y - enemy.y
                distance_to_target = math.hypot(dx, dy)
                is_attacking = hasattr(enemy, '_attack_animation_active') and enemy._attack_animation_active

                # Obtém o move atual para saber o range necessário
                current_move = None
                if hasattr(enemy, 'get_current_move_for_pattern'):
                    current_move = enemy.get_current_move_for_pattern()
                elif hasattr(enemy, 'get_current_move'):
                    current_move = enemy.get_current_move()

                if current_move and current_move.category == "physical":
                    required_range = 25
                else:
                    required_range = enemy.attack_range

                if distance_to_target < required_range or is_attacking:
                    should_skip_path = True

            # Se deve ignorar o path, apenas atualiza combate e continua
            if should_skip_path:
                self._update_enemy_combat(enemy, dt)
                self._update_animation(enemy, dt)
                continue

            # Atualiza movimento (NÃO interfere no combate)
            arrived_at_end, arrived_at_start = self.path_tracker.update_movement(enemy, dt)

            # ===== ATUALIZA COMBATE ENQUANTO MOVE =====
            self._update_enemy_combat(enemy, dt)

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
        """Processa morte de um inimigo (inclui boss!) """
        print(f"[WaveManager] {enemy.name} (BOSS={enemy.is_boss}) MORREU em batalha!")

        # ===== VERIFICA MULTIPLICADOR DE PAY DAY PARA GOLD =====
        gold_reward = self.gold_per_defeat
        # Incrementa o contador de inimigos derrotados
        self.total_enemies_defeated += 1
        print(f"[DEBUG] total_enemies_defeated agora = {self.total_enemies_defeated}")
        pay_day_gold_mult = 1.0

        if hasattr(enemy, '_pay_day_hit') and enemy._pay_day_hit:
            pay_day_gold_mult = getattr(enemy, '_pay_day_gold_multiplier', 2.0)
            gold_reward = int(gold_reward * pay_day_gold_mult)
            print(f"[PAY_DAY] Bonus de gold! {self.gold_per_defeat} -> {gold_reward} (x{pay_day_gold_mult})")

        # ===== NOVO SISTEMA DE XP: SO QUEM ATACOU ESTE INIMIGO =====
        if self.game_scene and hasattr(self.game_scene, 'battle_system'):
            self.game_scene.battle_system.distribute_xp_for_defeated_enemy(enemy)

        # Adiciona gold (com multiplicador)
        self.total_gold_earned += gold_reward

        # Se estava carregando item, o item volta para o chão
        if enemy.is_carrying is not None:
            try:
                item_name = enemy.is_carrying.item_name
                print(f"[ITEM] {enemy.name} morreu carregando {item_name} - item sera dropado")
                enemy.is_carrying.reset_capture()
                enemy.is_carrying = None
            except Exception as e:
                print(f"[ERROR] Falha ao processar item de {enemy.name}: {e}")
                enemy.is_carrying = None

        # ===== CONQUISTAS: Boss Derrotado (SOMENTE AQUI, QUANDO MORRE) =====
        if enemy.is_boss:
            self._boss_defeated = True
            if self.game_scene and hasattr(self.game_scene, 'player'):
                player = self.game_scene.player
                if hasattr(player, 'achievement_manager'):
                    phase_id = f"{self.game_scene.chapter_id}-{self.game_scene.phase_number}"
                    player.achievement_manager.increment_counter("boss_defeated_count")
                    player.achievement_manager.check_and_unlock("boss_defeated", phase_id)
                    print(f"[ACHIEVEMENT] Boss {enemy.name} derrotado! Verificando conquistas...")

        self._remove_enemy(enemy)
        self.game_scene.player.auto_save()

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
        """Remove inimigo da lista ativa e limpa referências de aliados"""
        if enemy in self.active_enemies:
            enemy._marked_for_removal = True
            enemy.is_placed = False  # Garante que não está mais no mapa

            print(f"[WaveManager] Removendo {enemy.name} (BOSS={enemy.is_boss})")

            # ===== LIMPA REFERÊNCIAS DE OUTROS INIMIGOS =====
            for other in self.active_enemies:
                if other != enemy and hasattr(other, 'target') and other.target == enemy:
                    print(f"[WaveManager] Inimigo {other.name} perdeu o alvo {enemy.name}")
                    other.target = None
                    if hasattr(other, '_attack_attempts'):
                        other._attack_attempts = 0
                    other.combat_state = "idle"
                    # Reseta ignore_path_timer
                    if hasattr(other, '_path_tracker'):
                        other._path_tracker.set_ignore_path(other, 0)

            # ===== LIMPA REFERÊNCIAS DE POKÉMON ALIADOS =====
            if hasattr(self.game_scene, 'placement_manager'):
                for ally in self.game_scene.placement_manager.placed_pokemon:
                    if hasattr(ally, 'target') and ally.target == enemy:
                        print(f"[WaveManager] Aliado {ally.name} perdeu o alvo {enemy.name}")
                        ally.target = None
                        if hasattr(ally, '_attack_attempts'):
                            ally._attack_attempts = 0
                        # Força aliado a voltar para o spot
                        ally.combat_state = "returning"
                        if hasattr(ally, 'has_animation') and ally.has_animation("walk"):
                            ally.set_animation("walk")
                        # Reseta qualquer animação de ataque pendente
                        if hasattr(ally, '_attack_animation_active'):
                            ally._attack_animation_active = False
                        # Limpa flags de ataque pendente
                        if hasattr(ally, '_pending_attack_move'):
                            delattr(ally, '_pending_attack_move')
                        if hasattr(ally, '_pending_attack_target'):
                            delattr(ally, '_pending_attack_target')

            # Limpa effect_manager
            if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
                enemy.effect_manager.unregister_pokemon(enemy)

            enemy.clear_damage_tracking()

            print(f"[WaveManager] {enemy.name} removido com sucesso")

    def _distribute_xp(self, defeated_enemy: 'Pokemon'):
        """
        [DEPRECATED] Método antigo mantido por compatibilidade, mas não usado.
        O novo sistema está em battle_system.distribute_xp_for_defeated_enemy()
        """
        pass

    def _update_animation(self, enemy, dt):
        """Atualiza animação do inimigo"""
        enemy.animation.update(dt)

    def remove_enemy(self, enemy: 'Pokemon'):
        """Remove um inimigo (para captura)"""
        self._remove_enemy(enemy)

    def is_next_wave_boss(self) -> bool:
        """Verifica se a próxima wave (de qualquer path ativo) contém um boss"""
        for path_idx, active in self.spawner.wave_active.items():
            if active:
                waves = self.spawner.waves.get(path_idx, [])
                wave_idx = self.spawner.current_wave_idx.get(path_idx, 0)
                if wave_idx < len(waves):
                    wave = waves[wave_idx]
                    return wave.has_boss
        return False

    def is_boss_defeated(self) -> bool:
        """Retorna se o boss já foi derrotado"""
        return self._boss_defeated

    def is_wave_completed(self, wave_index: int) -> bool:
        """Verifica se uma wave específica já foi completamente spawnada e todos os inimigos mortos"""
        return wave_index in self.spawner.waves_ended