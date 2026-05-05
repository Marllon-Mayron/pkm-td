# src/entities/pokemon/combat.py

import math
from typing import List, Optional

from src.battle.effects import StatusType


class PokemonCombat:
    """Gerencia combate do Pokémon para aliados e inimigos"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    # ===== MÉTODOS DE STATUS =====
    def is_stunned(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                return status.is_stunned()
        return False

    def update_stun(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                return status.update_paralysis(dt, self.pokemon)
        return False

    def is_asleep(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                return status.is_asleep()
        return False

    def update_sleep(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                return status.update_sleep(dt)
        return False

    def is_frozen(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.is_frozen()
        return False

    def update_freeze(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.update_freeze(dt)
        return False

    def thaw(self):
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.thaw()
        return False

    def _remove_spider_web(self):
        """Remove o efeito Spider Web do Pokémon"""
        if hasattr(self.pokemon, '_spider_web_active'):
            self.pokemon._spider_web_active = False

            if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                self.pokemon.effect_manager.add_status_text(
                    self.pokemon,
                    f"{self.pokemon.name} se libertou da teia!",
                    duration=1.0
                )
            print(f"[SPIDER_WEB] {self.pokemon.name} se libertou!")

        # Limpa atributos
        if hasattr(self.pokemon, '_spider_web_remaining'):
            delattr(self.pokemon, '_spider_web_remaining')
        if hasattr(self.pokemon, '_spider_web_source'):
            delattr(self.pokemon, '_spider_web_source')
        if hasattr(self.pokemon, '_spider_web_locked_x'):
            delattr(self.pokemon, '_spider_web_locked_x')
        if hasattr(self.pokemon, '_spider_web_locked_y'):
            delattr(self.pokemon, '_spider_web_locked_y')

    # ===== MÉTODOS DE BUSCA DE ALVO =====
    def find_nearest_enemy(self, all_entities: List) -> Optional['Pokemon']:
        """Encontra o inimigo mais próximo"""
        if not all_entities:
            return None

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.pokemon.attack_range * self.pokemon.attack_range

        for entity in all_entities:
            # ===== VERIFICA SE A ENTIDADE ESTÁ ATIVA NO MAPA =====
            # Para aliados (not wild): precisa estar placed
            if not entity.is_wild:
                if not hasattr(entity, 'is_placed') or not entity.is_placed:
                    continue
            # Para inimigos (wild): sempre considerados (se vivos)

            # Pula entidades mortas
            if not entity.is_alive() or entity.is_defeated:
                continue

            # Determina se é alvo válido
            is_valid_target = False
            if self.pokemon.is_wild:
                is_valid_target = not entity.is_wild  # Inimigo procura aliado
            else:
                is_valid_target = entity.is_wild  # Aliado procura inimigo

            if is_valid_target:
                dx = self.pokemon.x - entity.x
                dy = self.pokemon.y - entity.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = entity

        return nearest

    def find_nearest_enemy_in_path(self, all_entities: List, path_assignment=None) -> Optional['Pokemon']:
        """
        Encontra o inimigo mais próximo no MESMO PATH.
        Usado APENAS no minigame Survival.

        Args:
            all_entities: Lista de entidades
            path_assignment: PathAssignmentManager do minigame (opcional)
        """
        if not all_entities:
            return None

        # Se não tem path_assignment, fallback para comportamento normal
        if path_assignment is None:
            return self.find_nearest_enemy(all_entities)

        # Obtém o path do Pokémon
        pokemon_path = path_assignment.get_path_for_pokemon(self.pokemon)
        if pokemon_path is None:
            return self.find_nearest_enemy(all_entities)

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.pokemon.attack_range * self.pokemon.attack_range

        for entity in all_entities:
            # ===== VERIFICA SE A ENTIDADE ESTÁ ATIVA NO MAPA =====
            if not entity.is_wild:
                if not hasattr(entity, 'is_placed') or not entity.is_placed:
                    continue

            if not entity.is_alive() or entity.is_defeated:
                continue

            # Determina se é alvo válido
            is_valid_target = False
            if self.pokemon.is_wild:
                is_valid_target = not entity.is_wild
            else:
                is_valid_target = entity.is_wild

            if is_valid_target:
                # ===== VERIFICA SE ESTÁ NO MESMO PATH =====
                enemy_path = path_assignment.get_path_for_enemy(entity)
                if enemy_path != pokemon_path:
                    continue

                dx = self.pokemon.x - entity.x
                dy = self.pokemon.y - entity.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = entity

        return nearest

    def find_nearest_enemy_in_path_for_enemy(self, all_entities: List, path_assignment=None) -> Optional['Pokemon']:
        """
        Encontra o ALIADO mais próximo no MESMO PATH.
        Usado APENAS para INIMIGOS no minigame Survival.

        Args:
            all_entities: Lista de entidades (aliados)
            path_assignment: PathAssignmentManager do minigame (opcional)
        """
        if not all_entities:
            return None

        # Se não tem path_assignment, fallback para comportamento normal
        if path_assignment is None:
            return self.find_nearest_enemy(all_entities)

        # Obtém o path do INIMIGO (self.pokemon é o inimigo)
        enemy_path = path_assignment.get_path_for_enemy(self.pokemon)
        if enemy_path is None:
            return self.find_nearest_enemy(all_entities)

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.pokemon.attack_range * self.pokemon.attack_range

        for entity in all_entities:
            # Pula entidades mortas
            if not entity.is_alive() or entity.is_defeated:
                continue

            # Verifica se é aliado (not wild)
            is_valid_target = not entity.is_wild

            if is_valid_target:
                # ===== VERIFICA SE O ALIADO ESTÁ NO MESMO PATH =====
                ally_path = path_assignment.get_path_for_pokemon(entity)
                if ally_path != enemy_path:
                    continue

                dx = self.pokemon.x - entity.x
                dy = self.pokemon.y - entity.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = entity

        return nearest

    def is_target_in_range(self, target: 'Pokemon') -> bool:
        """
        Verifica se o alvo está dentro do range de ataque.
        Retorna False se o alvo estiver fora do range OU se não for mais válido.
        """
        if not target or not target.is_alive() or target.is_defeated:
            return False

        # Calcula distância
        dx = target.x - self.pokemon.x
        dy = target.y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Obtém o move atual para saber o range necessário
        current_move = self._get_current_move()

        if current_move:
            if current_move.category == "physical":
                required_range = 25  # Distância para ataque físico
            elif current_move.category in ["special", "status"]:
                required_range = self.pokemon.attack_range  # Range padrão para especiais
            else:
                required_range = self.pokemon.attack_range
        else:
            required_range = self.pokemon.attack_range

        # Define uma margem de tolerância (30% a mais que o range)
        # Isso evita que o Pokémon perca o target muito facilmente
        tolerance = required_range * 1.3

        in_range = distance <= tolerance

        if not in_range:
            print(f"[RANGE] {self.pokemon.name}: alvo {target.name} fora do range! "
                  f"Distância: {distance:.0f} > {tolerance:.0f}")

        return in_range

    def lose_target(self, reason: str = "desconhecido"):
        """Faz o Pokémon perder o alvo atual e resetar estado de combate"""
        if self.pokemon.target:
            print(f"[TARGET_LOST] {self.pokemon.name} perdeu o alvo {self.pokemon.target.name}. Motivo: {reason}")
            self.pokemon.target = None

        if (hasattr(self.pokemon, 'battle_system') and
                self.pokemon.battle_system and
                self.pokemon.battle_system.active_charge_move and
                self.pokemon.battle_system.active_charge_move['attacker'] == self.pokemon):
            print(f"[TWO_TURN] Carga de {self.pokemon.name} foi cancelada!")
            self.pokemon.battle_system.active_charge_move = None

        # Reseta estado de combate
        self.pokemon.combat_state = "idle"

        # Reseta tentativas de ataque
        if hasattr(self.pokemon, '_attack_attempts'):
            self.pokemon._attack_attempts = 0

        # Reseta ignore_path se for selvagem
        if self.pokemon.is_wild and hasattr(self.pokemon, '_path_tracker'):
            self.pokemon._path_tracker.set_ignore_path(self.pokemon, 0)

        # ===== CORREÇÃO: PARA ALIADOS, FORÇA RETORNO AO SPOT =====
        if not self.pokemon.is_wild:
            print(f"[TARGET_LOST] {self.pokemon.name}: voltando para o spot (motivo: {reason})")
            self.pokemon.combat_state = "returning"

            # ===== FORÇA RESET DAS FLAGS DE MOVIMENTO =====
            self.pokemon.is_moving = False
            self.pokemon.last_x = self.pokemon.x
            self.pokemon.last_y = self.pokemon.y

            # ===== FORÇA ANIMAÇÃO DE WALK =====
            if hasattr(self.pokemon, 'has_animation') and self.pokemon.has_animation("walk"):
                self.pokemon.set_animation("walk")

            # ===== CANCELA QUALQUER ANIMAÇÃO DE ATAQUE PENDENTE =====
            if hasattr(self.pokemon, '_attack_animation_active'):
                self.pokemon._attack_animation_active = False
                # Limpa flags relacionadas
                if hasattr(self.pokemon, '_pending_attack_move'):
                    delattr(self.pokemon, '_pending_attack_move')
                if hasattr(self.pokemon, '_pending_attack_target'):
                    delattr(self.pokemon, '_pending_attack_target')
        else:
            # Para selvagens: voltam para idle e seguirão o path
            if hasattr(self.pokemon, 'has_animation') and self.pokemon.has_animation("idle"):
                self.pokemon.set_animation("idle")

    # ===== MÉTODO PRINCIPAL DE COMBATE =====
    def update_combat(self, dt: float, all_entities: List):
        """
        Atualiza a lógica de combate - UNIFICADA.
        """
        # ===== PRIORIDADE 1: RETORNANDO PARA O SPOT =====
        if self.pokemon.combat_state == "returning":
            self._handle_returning_state(dt)
            return

        # ===== PRIORIDADE 2: VERIFICAÇÕES DE STATUS =====
        if not self._can_act(dt):
            return

        # ===== PRIORIDADE 3: EM ANIMAÇÃO DE ATAQUE =====
        is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
        if is_attacking:
            return

        # Atualiza cooldown
        if self.pokemon.charge_cooldown > 0:
            self.pokemon.charge_cooldown -= dt

        # ===== VERIFICA SE O ALVO AINDA É VÁLIDO =====
        if self.pokemon.target:
            # Verifica se o alvo ainda está vivo
            if not self.pokemon.target.is_alive() or self.pokemon.target.is_defeated:
                print(f"[COMBAT] {self.pokemon.name}: alvo {self.pokemon.target.name} foi derrotado!")
                self.pokemon.target = None

                # ===== ALIADOS: VOLTAM PARA O SPOT =====
                if not self.pokemon.is_wild:
                    print(f"[COMBAT] {self.pokemon.name}: voltando para o spot (alvo morto)")
                    self.pokemon.combat_state = "returning"
                    # Reseta qualquer estado de ataque pendente
                    if hasattr(self.pokemon, '_attack_animation_active'):
                        self.pokemon._attack_animation_active = False
                    # ===== FORÇA RESET DAS FLAGS DE MOVIMENTO =====
                    self.pokemon.is_moving = False
                    self.pokemon.last_x = self.pokemon.x
                    self.pokemon.last_y = self.pokemon.y
                    # Garante animação de walk
                    if self.pokemon.has_animation("walk"):
                        self.pokemon.set_animation("walk")
                    # Reseta cooldown
                    self.pokemon.charge_cooldown = 0
                    # Não retorna - continua para processar o movimento de retorno
                    # return  # <-- REMOVA ESTE RETURN!
                else:
                    self.pokemon.combat_state = "idle"
                    if self.pokemon.has_animation("idle"):
                        self.pokemon.set_animation("idle")
                    return

        # Se não tem alvo, procura um
        if not self.pokemon.target:
            # ===== VERIFICA SE TEM PATH_ASSIGNMENT TEMPORÁRIO (MINIGAME) =====
            path_assignment = getattr(self.pokemon, '_temp_path_assignment', None)

            if path_assignment is not None:
                # Modo minigame: usa busca com restrição de path
                if self.pokemon.is_wild:
                    # INIMIGO: busca aliados no mesmo path
                    self.pokemon.target = self.find_nearest_enemy_in_path_for_enemy(all_entities, path_assignment)
                else:
                    # ALIADO: busca inimigos no mesmo path
                    self.pokemon.target = self.find_nearest_enemy_in_path(all_entities, path_assignment)
            else:
                # Modo normal: busca padrão
                self.pokemon.target = self.find_nearest_enemy(all_entities)


            if self.pokemon.target:
                print(f"[COMBAT] {self.pokemon.name} encontrou novo alvo: {self.pokemon.target.name}")
                self.pokemon.combat_state = "attacking"
            else:
                # Sem alvos disponíveis
                if self.pokemon.combat_state != "idle":
                    # ===== ALIADOS: VOLTAM PARA O SPOT QUANDO NÃO HÁ INIMIGOS =====
                    if not self.pokemon.is_wild:
                        if hasattr(self.pokemon, 'original_spot_x') and hasattr(self.pokemon, 'original_spot_y'):
                            dx = self.pokemon.original_spot_x - self.pokemon.x
                            dy = self.pokemon.original_spot_y - self.pokemon.y
                            distance_to_spot = math.sqrt(dx * dx + dy * dy)

                            if distance_to_spot > 5:
                                print(f"[COMBAT] {self.pokemon.name}: sem inimigos, voltando para o spot")
                                self.pokemon.combat_state = "returning"
                                if self.pokemon.has_animation("walk"):
                                    self.pokemon.set_animation("walk")
                                return
                            else:
                                # Já está no spot
                                self.pokemon.combat_state = "idle"
                                if self.pokemon.has_animation("idle"):
                                    self.pokemon.set_animation("idle")
                        else:
                            self.pokemon.combat_state = "idle"
                            if self.pokemon.has_animation("idle"):
                                self.pokemon.set_animation("idle")
                    else:
                        self.pokemon.combat_state = "idle"
                        if self.pokemon.has_animation("idle"):
                            self.pokemon.set_animation("idle")
                return

        # Se tem alvo e pode atacar
        if self.pokemon.target and self.pokemon.charge_cooldown <= 0:
            if self.pokemon.is_wild:
                if not self.pokemon.target.is_placed:
                    self.pokemon.target = None
                    self.pokemon.combat_state = "idle"
                else:
                    self._try_attack(self.pokemon.target, dt)
            else:
                self._try_attack(self.pokemon.target, dt)

    def _try_attack(self, target: 'Pokemon', dt: float):
        """Tenta atacar o alvo - UNIFICADO para aliados e inimigos"""
        # Verifica se está em animação de ataque
        is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
        if is_attacking:
            return

        # Verifica se o alvo ainda está vivo (double-check)
        if not target.is_alive() or target.is_defeated:
            print(f"[COMBAT] {self.pokemon.name}: alvo {target.name} morreu antes do ataque!")
            self.pokemon.target = None
            self.pokemon.combat_state = "idle"

            if not self.pokemon.is_wild and self.pokemon.has_animation("idle"):
                self.pokemon.set_animation("idle")
            return

        # ===== VERIFICA SE ESTÁ PRESO NA TEIA (SPIDER WEB) =====
        if hasattr(self.pokemon, '_spider_web_active') and self.pokemon._spider_web_active:
            if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                self.pokemon.effect_manager.add_status_text(
                    self.pokemon,
                    f"{self.pokemon.name} está preso na teia e não pode atacar!",
                    duration=1.0
                )

            # Decrementa o contador
            self.pokemon._spider_web_remaining -= 1

            print(f"[SPIDER_WEB] {self.pokemon.name} preso! Restam {self.pokemon._spider_web_remaining} turnos")

            # Se acabou, liberta
            if self.pokemon._spider_web_remaining <= 0:
                self._remove_spider_web()

            # Aplica cooldown
            self.pokemon.attack_cooldown = max(0.3, 1.0 - (self.pokemon.speed_stat / 500))
            return

        # ===== VERIFICA SE O ALVO AINDA ESTÁ NO RANGE DURANTE PERSEGUIÇÃO =====
        # Se for aliado e já está se movendo para o alvo, verifica se o alvo ainda está no range
        if not self.pokemon.is_wild and self.pokemon.combat_state == "moving_to_target":
            dx_check = target.x - self.pokemon.x
            dy_check = target.y - self.pokemon.y
            distance_check = math.sqrt(dx_check * dx_check + dy_check * dy_check)

            # Se o alvo saiu do range (com margem de 30% a mais), desiste
            if distance_check > self.pokemon.attack_range * 1.3:
                print(f"[COMBAT] {self.pokemon.name}: alvo {target.name} saiu do range durante perseguição! "
                      f"Distância: {distance_check:.0f} > {self.pokemon.attack_range:.0f}")
                self.pokemon.target = None
                self.pokemon.combat_state = "returning"
                if self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
                return

        # ===== ANTI-SPAM: Evita ficar tentando atacar sem PP a cada frame =====
        if hasattr(self.pokemon, '_no_move_cooldown') and self.pokemon._no_move_cooldown > 0:
            self.pokemon._no_move_cooldown -= dt
            return

        # ===== OBTÉM O MOVE SELECIONADO (NÃO TROCA AUTOMATICAMENTE) =====
        current_move = self._get_current_move()

        # Se não tem move disponível (sem PP ou nenhum move selecionado)
        if not current_move:
            print(f"[COMBAT] {self.pokemon.name} não tem move disponível para atacar!")
            self.pokemon.has_no_pp = True

            # Aplica cooldown de 0.5 segundos para não spammar
            self.pokemon._no_move_cooldown = 0.5

            self._handle_no_moves()
            return

        # ===== SÓ STRUGGLE SE NÃO TIVER NENHUM MOVE COM PP =====
        all_moves_no_pp = True
        for move in self.pokemon.moves:
            if move.current_pp > 0:
                all_moves_no_pp = False
                break

        if current_move.current_pp <= 0 and not all_moves_no_pp:
            print(
                f"[COMBAT] {self.pokemon.name}: {current_move.name} sem PP, mas há outros moves com PP. O player precisa trocar!")
            self.pokemon.has_no_pp = True
            self.pokemon._no_move_cooldown = 0.5
            self._handle_no_moves()
            return

        self.pokemon._no_move_cooldown = 0

        if all_moves_no_pp:
            struggle = self._get_struggle_move()
            if struggle:
                current_move = struggle
                print(f"[STRUGGLE] {self.pokemon.name} está sem PP em TODOS os moves! Usando Struggle!")
            else:
                return

        # Calcula distância até o alvo
        dx = target.x - self.pokemon.x
        dy = target.y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Atualiza direção para olhar para o alvo
        self._update_direction_to_target(dx, dy)

        # ===== ALIADOS (NOT WILD) =====
        if not self.pokemon.is_wild:
            attack_distance = 12
            is_status_move = current_move.category == "status"
            is_special_move = current_move.category == "special"

            if is_status_move or is_special_move:
                self._start_attack_animation(target, current_move)
                return

            if distance > attack_distance:
                self.pokemon.combat_state = "moving_to_target"
                # ===== FORÇA ANIMAÇÃO WALK ANTES DE MOVER =====
                if self.pokemon.current_animation != "walk" and self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
                    print(f"[MOVE] {self.pokemon.name} indo atacar (walk)")
                self._move_towards_target(target, dx, dy, distance, dt)
            else:
                self._start_attack_animation(target, current_move)
            return

        # ===== INIMIGOS (WILD) =====
        if current_move.category == "physical":
            attack_distance = 25
        else:
            attack_distance = self.pokemon.attack_range

        if distance <= attack_distance:
            if hasattr(self.pokemon, '_attack_attempts'):
                self.pokemon._attack_attempts = 0
            self._start_attack_animation(target, current_move)
        else:
            if not hasattr(self.pokemon, '_attack_attempts'):
                self.pokemon._attack_attempts = 0
            self.pokemon._attack_attempts += 1
            # ===== FORÇA ANIMAÇÃO WALK ANTES DE MOVER =====
            if self.pokemon.current_animation != "walk" and self.pokemon.has_animation("walk"):
                self.pokemon.set_animation("walk")
                print(f"[MOVE] {self.pokemon.name} indo atacar (walk)")
            self._move_towards_target(target, dx, dy, distance, dt)

            if self.pokemon._attack_attempts > 5:
                print(f"[COMBAT] {self.pokemon.name}: abandonando alvo {target.name}")
                self.pokemon.target = None
                self.pokemon.combat_state = "idle"
                self.pokemon._attack_attempts = 0

    def _move_towards_target(self, target: 'Pokemon', dx: float, dy: float, distance: float, dt: float):
        """Move em direção ao alvo (para aliados E inimigos)"""
        # Verifica se o alvo ainda existe antes de mover
        if not target.is_alive() or target.is_defeated:
            print(f"[MOVE] {self.pokemon.name}: alvo {target.name} morreu, parando movimento!")
            self.pokemon.target = None

            if not self.pokemon.is_wild:
                print(f"[MOVE] {self.pokemon.name}: voltando para o spot (alvo morto durante movimento)")
                self.pokemon.combat_state = "returning"
                if self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
            else:
                self.pokemon.combat_state = "idle"
                if self.pokemon.has_animation("idle"):
                    self.pokemon.set_animation("idle")
            return

        # ===== VERIFICA SE O ALVO ESTÁ MUITO LONGE DURANTE O MOVIMENTO =====
        if not self.pokemon.is_wild:
            dx_check = target.x - self.pokemon.x
            dy_check = target.y - self.pokemon.y
            distance_check = math.sqrt(dx_check * dx_check + dy_check * dy_check)

            # Se o alvo estiver a mais de 1.5x o range, desiste
            if distance_check > self.pokemon.attack_range * 1.5:
                print(f"[MOVE] {self.pokemon.name}: alvo {target.name} muito longe durante movimento! "
                      f"Distância: {distance_check:.0f} > {self.pokemon.attack_range * 1.5:.0f}")
                self.pokemon.target = None
                self.pokemon.combat_state = "returning"
                if self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
                return

        # Garante animação de walk
        is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
        if not is_attacking and self.pokemon.current_animation != "walk":
            if self.pokemon.has_animation("walk"):
                self.pokemon.set_animation("walk")

        move_distance = self.pokemon.move_speed * dt * 60

        # Evita divisão por zero
        if distance <= 0:
            return

        move_x = (dx / distance) * move_distance
        move_y = (dy / distance) * move_distance

        # Não ultrapassar o alvo
        if abs(move_x) > abs(dx):
            move_x = dx
        if abs(move_y) > abs(dy):
            move_y = dy

        self.pokemon.x += move_x
        self.pokemon.y += move_y
        self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

    def _can_act(self, dt: float) -> bool:
        """Verifica se o Pokémon pode agir"""
        if self.update_stun(dt):
            return False
        if self.update_sleep(dt):
            return False
        if self.is_frozen():
            if self.update_freeze(dt):
                return False
        return True

    def _get_current_move(self):
        """
        Obtém o move atual.
        Só retorna o move que está selecionado pelo player.
        NUNCA troca de golpe automaticamente.
        """
        # Tenta o move padrão (selecionado pelo player)
        move = self.pokemon.get_current_move()

        # Se não tem move selecionado, retorna None
        if not move:
            return None

        # Se o move tem PP, retorna ele
        if move.current_pp > 0:
            return move

        # ===== MOVE SELECIONADO ESTÁ SEM PP =====
        # NÃO TROCA AUTOMATICAMENTE!
        # Retorna None para indicar que não pode atacar
        print(f"[PP] {self.pokemon.name}: move {move.name} está sem PP! Aguardando o player trocar.")

        # Mostra mensagem visual
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            self.pokemon.effect_manager.add_status_text(
                self.pokemon,
                f"{move.name} está sem PP!",
                duration=2.0
            )

        return None  # Sem move disponível

    def _get_struggle_move(self):
        """
        Cria e retorna o movimento Struggle APENAS para uso imediato.
        NÃO salva no moveset do Pokémon.
        """
        from src.entities.move import Move

        struggle_info = {
            "name": "Struggle",
            "type": "normal",
            "power": 50,
            "accuracy": 100,
            "pp": 1,
            "max_pp": 1,
            "category": "physical",
            "description": "Usado quando todos os PP acabam. Causa dano e dano de retorno."
        }

        # Cria uma instância TEMPORÁRIA
        struggle_move = Move("struggle", struggle_info)
        struggle_move.current_pp = 1  # Sempre disponível

        return struggle_move

    def _start_attack_animation(self, target: 'Pokemon', move):
        """Inicia a animação de ataque"""

        # ===== AVISA O PATH TRACKER PARA IGNORAR O PATH =====
        if self.pokemon.is_wild and hasattr(self.pokemon, '_path_tracker'):
            self.pokemon._path_tracker.set_ignore_path(self.pokemon, 1.5)

        from src.battle.effects.animation_mapper import AnimationMapper

        animation_to_use = AnimationMapper.get_animation_for_move(move.name, move.category)

        # Verifica se o Pokémon tem a animação
        if not self.pokemon.has_animation(animation_to_use):
            if animation_to_use == "attack" and self.pokemon.has_animation("strike"):
                animation_to_use = "strike"
            elif animation_to_use == "shoot" and self.pokemon.has_animation("attack"):
                animation_to_use = "attack"
            elif not self.pokemon.has_animation(animation_to_use):
                if self.pokemon.has_animation("attack"):
                    animation_to_use = "attack"
                elif self.pokemon._available_animations:
                    animation_to_use = self.pokemon._available_animations[0]
                else:
                    # Sem animação, ataca diretamente
                    self._execute_attack(target, move)
                    return

        # Salva animação anterior
        self.pokemon._saved_animation_before_attack = self.pokemon.current_animation
        self.pokemon.set_animation_direct(animation_to_use)
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon._attack_animation_active = True
        self.pokemon._pending_attack_move = move.name  # Salva o nome do move
        self.pokemon._pending_attack_target = target  # Salva o alvo
        self.pokemon._damage_frame_percent = 0.5
        self.pokemon._damage_applied = False

        print(f"[ANIM] {self.pokemon.name} usou animação '{animation_to_use}' para {move.name}")

    def _execute_attack(self, target: 'Pokemon', move):
        """Executa o ataque real"""
        # Verifica se o alvo já está morto ANTES do ataque
        if not target or not target.is_alive() or target.is_defeated:
            self.pokemon.target = None

            # ===== ALIADOS: VOLTAM PARA O SPOT =====
            if not self.pokemon.is_wild:
                print(f"[ATTACK] {self.pokemon.name}: alvo já estava morto, voltando para o spot")
                self.pokemon.combat_state = "returning"
                if self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
            else:
                self.pokemon.combat_state = "idle"
                if self.pokemon.has_animation("idle"):
                    self.pokemon.set_animation("idle")

            if self.pokemon.is_wild and hasattr(self.pokemon, '_path_tracker'):
                self.pokemon._path_tracker.set_ignore_path(self.pokemon, 0)
            return

        # ===== VERIFICA PP DO MOVE =====
        # Struggle é um caso especial - sempre tem PP=1
        if move.name.lower() != "struggle" and move.current_pp <= 0:
            print(f"[COMBAT] {self.pokemon.name} move {move.name} sem PP!")

            # Tenta encontrar outro move com PP
            for m in self.pokemon.moves:
                if m.current_pp > 0:
                    move = m
                    break
            else:
                # Se não tem nenhum move com PP, tenta Struggle
                struggle = self._get_struggle_move()
                if struggle:
                    move = struggle
                    print(f"[COMBAT] {self.pokemon.name} usando Struggle por falta de PP!")
                else:
                    print(f"[COMBAT] {self.pokemon.name} está sem PP e não consegue atacar!")
                    self.pokemon.has_no_pp = True

                    if not self.pokemon.is_wild:
                        self.pokemon.combat_state = "returning"
                        if self.pokemon.has_animation("walk"):
                            self.pokemon.set_animation("walk")
                    else:
                        self.pokemon.combat_state = "idle"
                        if self.pokemon.has_animation("idle"):
                            self.pokemon.set_animation("idle")
                    return

        # Executa o ataque
        target_was_alive_before = target.is_alive() and not target.is_defeated

        if self.pokemon.battle_system:
            success = self.pokemon.battle_system.attempt_attack(self.pokemon, target)
            if success:
                print(f"[ATTACK] {self.pokemon.name} usou {move.name} em {target.name}!")
                if hasattr(self.pokemon, '_rage_active') and self.pokemon._rage_active:
                    self._clear_rage_after_attack()

        self.pokemon.charge_cooldown = self.pokemon.charge_cooldown_max

        # ===== PERISH SONG: DECREMENTA CONTADOR APÓS ATACAR =====
        if hasattr(self.pokemon, '_perish_song_active') and self.pokemon._perish_song_active:
            self.pokemon._perish_song_turns_left -= 1

            # Mostra mensagem
            if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                self.pokemon.effect_manager.add_status_text(
                    self.pokemon,
                    f"Canção do Perecer: {self.pokemon._perish_song_turns_left} ataques restantes!",
                    duration=1.0
                )

            print(f"[PERISH_SONG] {self.pokemon.name} atacou! Restam {self.pokemon._perish_song_turns_left} ataques")

            # ===== VERIFICA SE CHEGOU A 0 =====
            if self.pokemon._perish_song_turns_left <= 0:
                # Desmaia APÓS o ataque (mas antes de verificar se o alvo morreu)
                if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                    self.pokemon.effect_manager.add_status_text(
                        self.pokemon,
                        f"{self.pokemon.name} desmaiou pela Canção do Perecer!",
                        duration=1.5
                    )

                print(f"[PERISH_SONG] {self.pokemon.name} desmaiou após atacar!")

                # Marca como derrotado
                self.pokemon.set_defeated(True)

                # Remove o efeito
                self.pokemon._perish_song_active = False

                # Se for aliado, notifica
                if not self.pokemon.is_wild:
                    from src.ui.toast_renderer import toast_battle
                    toast_battle(f"{self.pokemon.name} desmaiou pela Canção do Perecer!",
                                 duration=3.0, pokemon=self.pokemon, portrait="dizzy")

                # Não continua para verificar alvo (já vai desmaiar)
                return

        # ===== VERIFICA SE O ALVO MORREU COM O ATAQUE =====
        target_is_dead_now = not target.is_alive() or target.is_defeated

        if not self.pokemon.is_wild:
            # ===== ALIADOS =====
            if target_is_dead_now:
                print(f"[ATTACK] {self.pokemon.name}: matou {target.name}! Voltando para o spot.")
                self.pokemon.target = None
            else:
                print(f"[ATTACK] {self.pokemon.name}: atacou {target.name}, voltando para o spot.")

            # SEMPRE volta para o spot após atacar
            self.pokemon.combat_state = "returning"
            # Força animação walk APENAS se não estiver já em walk
            if self.pokemon.current_animation != "walk" and self.pokemon.has_animation("walk"):
                self.pokemon.set_animation("walk")
        else:
            # ===== INIMIGOS =====
            self.pokemon.combat_state = "attacking"
            if hasattr(self.pokemon, '_path_tracker'):
                self.pokemon._path_tracker.set_ignore_path(self.pokemon, 0)

    def _handle_returning_state(self, dt: float):
        """GERENCIA O RETORNO DO POKÉMON AO SPOT ORIGINAL"""
        # Verifica se tem spot original definido
        if not hasattr(self.pokemon, 'original_spot_x') or not hasattr(self.pokemon, 'original_spot_y'):
            print(f"[RETURN] {self.pokemon.name} não tem spot original! Voltando para idle.")
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None
            if hasattr(self.pokemon, 'has_animation') and self.pokemon.has_animation("idle"):
                self.pokemon.set_animation("idle")
            return

        target_x = self.pokemon.original_spot_x
        target_y = self.pokemon.original_spot_y
        dx = target_x - self.pokemon.x
        dy = target_y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Se chegou perto o suficiente
        if distance < 3:
            # Posiciona exatamente no spot
            self.pokemon.x = target_x
            self.pokemon.y = target_y
            if hasattr(self.pokemon, 'rect'):
                self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

            # Reseta estado
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None

            # ===== FORÇA RESET DAS FLAGS DE MOVIMENTO =====
            self.pokemon.is_moving = False
            self.pokemon.last_x = self.pokemon.x
            self.pokemon.last_y = self.pokemon.y

            # ===== FORÇA ANIMAÇÃO IDLE =====
            if hasattr(self.pokemon, 'has_animation') and self.pokemon.has_animation("idle"):
                self.pokemon.set_animation("idle")
                print(f"[RETURN] {self.pokemon.name} retornou ao spot! Posição: ({self.pokemon.x:.0f}, {self.pokemon.y:.0f})")
            else:
                print(f"[RETURN] {self.pokemon.name} retornou ao spot, mas não tem animação idle!")
            return

        # ===== AINDA VOLTANDO =====
        # Verifica se não está em animação de ataque
        is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active

        if not is_attacking:
            # Força animação walk APENAS se não estiver já em walk
            if hasattr(self.pokemon, 'current_animation') and self.pokemon.current_animation != "walk":
                if hasattr(self.pokemon, 'has_animation') and self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
                    print(f"[RETURN] {self.pokemon.name} voltando ao spot (walk)")

        # Move em direção ao spot
        move_distance = self.pokemon.move_speed * dt * 60

        # Evita divisão por zero
        if distance <= 0:
            return

        move_x = (dx / distance) * move_distance
        move_y = (dy / distance) * move_distance

        # Não ultrapassar o spot
        if abs(move_x) > abs(dx):
            move_x = dx
        if abs(move_y) > abs(dy):
            move_y = dy

        self.pokemon.x += move_x
        self.pokemon.y += move_y
        if hasattr(self.pokemon, 'rect'):
            self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

        # Atualiza direção baseada no movimento
        self._update_direction_to_target(dx, dy)

    def show_miss_on_self(self):
        """Mostra o texto MISS no próprio Pokémon"""
        self.pokemon.miss_timer = 0.6

    def _update_direction_to_target(self, dx: float, dy: float):
        """Atualiza direção baseada no alvo (8 direções)"""
        if dx == 0 and dy == 0:
            return

        abs_dx = abs(dx)
        abs_dy = abs(dy)
        THRESHOLD = 0.41421356

        if abs_dx >= abs_dy:
            if dx > 0:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "down-right"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "up-right"
                else:
                    self.pokemon.current_direction = "right"
            else:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "down-left"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "up-left"
                else:
                    self.pokemon.current_direction = "left"
        else:
            if dy > 0:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "down-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "down-left"
                else:
                    self.pokemon.current_direction = "down"
            else:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "up-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "up-left"
                else:
                    self.pokemon.current_direction = "up"

    def _handle_no_moves(self):
        """Lida com a situação onde não há moves disponíveis (sem PP)"""
        print(f"[NO_MOVES] {self.pokemon.name} sem moves disponíveis!")

        if not self.pokemon.is_wild:
            # Para aliados: volta para o spot
            if self.pokemon.combat_state != "returning":
                self.pokemon.combat_state = "returning"
                # Só define walk se não estiver já em walk
                if self.pokemon.current_animation != "walk" and self.pokemon.has_animation("walk"):
                    self.pokemon.set_animation("walk")
        else:
            # Para selvagens: fica idle
            if self.pokemon.combat_state != "idle":
                self.pokemon.combat_state = "idle"
                if self.pokemon.has_animation("idle"):
                    self.pokemon.set_animation("idle")

    # ===== MÉTODOS DE DANO =====
    def take_damage(self, damage, attacker=None):
        """Recebe dano"""
        # ===== DECREMENTA SAFEGUARD AO RECEBER DANO =====
        if hasattr(self.pokemon, '_safeguard_active') and self.pokemon._safeguard_active:
            self.pokemon._safeguard_remaining -= 1
            print(f"[SAFEGUARD] {self.pokemon.name} recebeu dano! Restam {self.pokemon._safeguard_remaining} proteções")

            if self.pokemon._safeguard_remaining <= 0:
                self.pokemon._safeguard_active = False
                if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                    self.pokemon.effect_manager.add_status_text(
                        self.pokemon,
                        f"O Safeguard de {self.pokemon.name} acabou!",
                        duration=1.0
                    )

        if self.pokemon.is_defeated:
            return self.pokemon.current_hp <= 0

        old_hp = self.pokemon.current_hp
        self.pokemon.current_hp = max(0, self.pokemon.current_hp - damage)

        if damage > 0 and self.pokemon.current_hp > 0:
            self.pokemon.play_hurt_animation()

        if self.pokemon.current_hp <= 0:
            from src.managers.sounds.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("faint")
            print(f"[BATTLE] {self.pokemon.name} foi derrotado!")

            self.pokemon.set_defeated(True)

            if self.pokemon.is_wild and self.pokemon.is_carrying:
                carried_item = self.pokemon.is_carrying
                print(f"[ITEM] {carried_item.item_name} será liberado com a morte de {self.pokemon.name}")
                carried_item.reset_capture()
                carried_item.is_protected = True
                carried_item.is_stolen = False
                carried_item.carried_by = None
                self.pokemon.is_carrying = None

        # ===== CALLBACK DO RAGE =====
        if hasattr(self, '_rage_active') and self._rage_active and hasattr(self, '_rage_callback'):
            self._rage_callback(self, damage)
        return self.pokemon.current_hp <= 0

    def _clear_rage_after_attack(self):
        """Limpa o modo Rage após o Pokémon atacar"""
        if hasattr(self.pokemon, '_rage_active') and self.pokemon._rage_active:
            self.pokemon._rage_active = False
            self.pokemon._rage_callback = None
            print(f"[RAGE] {self.pokemon.name} atacou e saiu do modo fúria!")

            # Opcional: mostra mensagem visual
            if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
                self.pokemon.effect_manager.add_status_text(
                    self.pokemon,
                    f"{self.pokemon.name} saiu da fúria!",
                    duration=1.0
                )

    def get_enemies_in_range(self, all_entities: List) -> List['Pokemon']:
        """
        Retorna lista de todos os inimigos dentro do range de ataque.
        Útil para ataques em área futuramente.
        """
        enemies_in_range = []

        if not all_entities:
            return enemies_in_range

        # ===== USA O RANGE PADRÃO DO POKÉMON (NÃO DEPENDE DO MOVE) =====
        # Para ataques em área como Earthquake, sempre usa o attack_range padrão
        required_range = self.pokemon.attack_range

        range_sq = required_range * required_range

        print(f"[AREA_RANGE] {self.pokemon.name} verificando range {required_range} para {len(all_entities)} entidades")

        for entity in all_entities:
            # Pula entidades mortas
            if not entity.is_alive() or entity.is_defeated:
                continue

            # Verifica se é inimigo
            is_valid_target = False
            if self.pokemon.is_wild:
                is_valid_target = not entity.is_wild
            else:
                is_valid_target = entity.is_wild

            if is_valid_target:
                dx = self.pokemon.x - entity.x
                dy = self.pokemon.y - entity.y
                distance_sq = dx * dx + dy * dy

                if distance_sq <= range_sq:
                    enemies_in_range.append(entity)
        return enemies_in_range

    def get_range_radius(self) -> float:
        """
        Retorna o raio atual do range de ataque.
        """
        current_move = self._get_current_move()

        if current_move:
            if current_move.category == "physical":
                return float(self.pokemon.attack_range)
            else:
                return float(self.pokemon.attack_range)
        else:
            return float(self.pokemon.attack_range)