# src/entities/pokemon.py
import pygame
import math
import random
from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.managers.evolution_manager import evolution_manager


class Pokemon(Entity):
    def __init__(self, x, y, pokemon_id, level=5, is_wild=False, shiny=False, is_boss=False):
        # ===== 1. DADOS BÁSICOS =====
        self.pokedex = Pokedex()
        self.pokemon_data = self.pokedex.get_pokemon(pokemon_id)

        if not self.pokemon_data:
            raise ValueError(f"Pokémon ID {pokemon_id} não encontrado")

        self.id = pokemon_id
        self.name = self.pokemon_data["name"].capitalize()
        self.base_level = level  # Guarda o level base
        self.level = level
        self.is_shiny = shiny
        self.is_boss = is_boss

        # ===== 2. STATUS E ATRIBUTOS BASE =====
        self.is_placed = False
        self.spot_id = None
        self.types = self.pokemon_data["types"]
        self.base_stats = self.pokemon_data["base_stats"]

        # ===== 3. IVs E EVs (ANTES DE CALCULAR STATS) =====
        self.ivs = {
            "hp": random.randint(0, 31),
            "attack": random.randint(0, 31),
            "defense": random.randint(0, 31),
            "special_attack": random.randint(0, 31),
            "special_defense": random.randint(0, 31),
            "speed": random.randint(0, 31)
        }

        self.evs = {
            "hp": 0, "attack": 0, "defense": 0,
            "special_attack": 0, "special_defense": 0, "speed": 0
        }

        # ===== 4. NATUREZA (AFETA STATS) =====
        self.nature_multipliers = self._generate_nature()
        self.nature = self.nature_multipliers["name"]

        # ===== 5. CALCULAR STATS (USA IVs, EVs, NATUREZA) =====
        self._calculate_stats()

        # ===== 6. BOSS: AUMENTA LEVEL E RECALCULA =====
        if is_boss:
            self.level = self.base_level + 3  # Aumenta em 3 níveis
            self._calculate_stats()  # Recalcula stats com o novo level

            # ===== NOVO: BOSS TEM 20% MAIS VIDA =====
            original_hp = self.max_hp
            self.max_hp = int(self.max_hp * 1.5)
            self.current_hp = self.max_hp
            self.defense = int(self.defense * 1.5)
            self.sp_defense = int(self.sp_defense * 1.5)
            self.defense_value = self._calculate_defense()

        # ===== 7. ESTADO ATUAL =====
        self.current_hp = self.max_hp
        self.xp = 0
        self.xp_to_next = self._calculate_xp_needed()

        # ===== 8. SPRITES =====
        self.ui_sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny)
        self.battle_sprite = self.pokedex.get_sprite(pokemon_id, "back", shiny)
        self.inmap_frames = self.pokedex.get_inmap_animation(pokemon_id, shiny)
        self.current_direction = "down"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.1

        # ===== 9. TAMANHO DO SPRITE =====
        self.map_sprite_size = self.pokedex.get_map_sprite_size(pokemon_id, shiny)
        width = self.map_sprite_size
        height = self.map_sprite_size

        # Sprite padrão para o mapa
        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        # ===== 10. ATRIBUTOS DE JOGO =====
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # ===== 11. MOVIMENTO =====
        self.path = []
        self.path_index = 0
        self.speed = 2.0
        self.base_speed = self.speed

        # ===== 12. COMBATE =====
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60
        self.target = None

        # ===== 13. EFEITOS VISUAIS =====
        self.hp_bar_width = 32
        self.hp_bar_height = 3

        # ===== 14. POSIÇÃO E MOVIMENTAÇÃO =====
        self.last_x = x
        self.last_y = y

        # ===== 15. ITENS =====
        self.is_carrying = None
        self.capture_range = 10
        self.is_returning_with_item = False  # NOVO: para boss que está voltando com item

        # ===== 16. ATRIBUTOS DE COMBATE =====
        self.attack_range = 60
        self.combat_state = "idle"
        self.original_spot_x = x
        self.original_spot_y = y

        # ===== 17. COOLDOWNS =====
        self.charge_cooldown = 0.0
        self.charge_cooldown_max = 1.5

        # ===== 18. STATS DE COMBATE =====
        self.attack_damage = self._calculate_attack_damage()
        self.defense_value = self._calculate_defense()

        # ===== 19. RASTREAMENTO DE DANO =====
        self.damage_contributions = {}
        self.last_attacker = None

    def _calculate_stats(self):
        """Calcula stats baseado em level, IVs e EVs"""
        stats = self.pokedex.calculate_stats(self.id, self.level, self.ivs, self.evs)

        self.max_hp = stats["hp"]
        self.attack = stats["attack"]
        self.defense = stats["defense"]
        self.sp_attack = stats["special_attack"]
        self.sp_defense = stats["special_defense"]
        self.speed = stats["speed"]

        # Aplicar natureza
        if hasattr(self, 'nature_multipliers'):
            self.attack = int(self.attack * self.nature_multipliers["attack"])
            self.defense = int(self.defense * self.nature_multipliers["defense"])
            self.sp_attack = int(self.sp_attack * self.nature_multipliers["sp_attack"])
            self.sp_defense = int(self.sp_defense * self.nature_multipliers["sp_defense"])
            self.speed = int(self.speed * self.nature_multipliers["speed"])

    def _calculate_xp_needed(self):
        """Calcula XP necessário para próximo nível (formato medium-fast)"""
        return int(self.level ** 3)

    def _generate_nature(self):
        """Gera multiplicadores de natureza aleatórios"""
        natures = [
            {"name": "Hardy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lonely", "attack": 1.1, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Brave", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Adamant", "attack": 1.1, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Naughty", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Bold", "attack": 0.9, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Relaxed", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Impish", "attack": 1.0, "defense": 1.1, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lax", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Timid", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Hasty", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Jolly", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Naive", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.1},
            {"name": "Modest", "attack": 0.9, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Mild", "attack": 1.0, "defense": 0.9, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Quiet", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Rash", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Calm", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Gentle", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Sassy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 0.9},
            {"name": "Careful", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Quirky", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
        ]
        nature = random.choice(natures)
        self.nature = nature["name"]
        return nature

    def heal(self, amount=None):
        """Cura o Pokémon"""
        if amount is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def check_and_evolve(self):
        """Verifica se o Pokémon pode evoluir e realiza a evolução se possível"""
        # Verifica evolução por nível
        evolution = evolution_manager.check_evolution(
            self.id,
            current_level=self.level
        )

        if evolution:
            evolve_to_id = evolution["evolve_to"]
            evolve_method = evolution["method"]

            print(f"[EVOLUÇÃO] {self.name} está evoluindo para ID {evolve_to_id} por {evolve_method}!")

            # Realiza a evolução
            self._perform_evolution(evolve_to_id)
            return True

        return False

    def _perform_evolution(self, new_id):
        """Realiza a evolução do Pokémon"""
        # Salva dados importantes antes da evolução
        old_name = self.name
        old_level = self.level

        # Obtém os dados do novo Pokémon
        new_pokemon_data = self.pokedex.get_pokemon(new_id)

        if not new_pokemon_data:
            print(f"[ERRO] Pokémon ID {new_id} não encontrado!")
            return

        # Atualiza os dados do Pokémon
        self.id = new_id
        self.name = new_pokemon_data["name"].capitalize()
        self.types = new_pokemon_data["types"]
        self.base_stats = new_pokemon_data["base_stats"]

        # Mantém level, IVs, EVs e natureza
        # Recalcula stats com o novo base_stats
        self._calculate_stats()

        # Cura totalmente após evolução
        self.current_hp = self.max_hp

        # Atualiza sprites
        self.ui_sprite = self.pokedex.get_sprite(new_id, "front", self.is_shiny)
        self.battle_sprite = self.pokedex.get_sprite(new_id, "back", self.is_shiny)

        # Atualiza sprites de mapa
        self.inmap_frames = self.pokedex.get_inmap_animation(new_id, self.is_shiny)
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            self.sprite = self.inmap_frames["down"][0]

        # Atualiza tamanho do sprite no mapa
        self.map_sprite_size = self.pokedex.get_map_sprite_size(new_id, self.is_shiny)

        print(f"[EVOLUÇÃO] ✓ {old_name} (Lv.{old_level}) evoluiu para {self.name}!")

    def gain_xp(self, amount):
        """Ganha XP e verifica level up e evolução"""
        old_level = self.level
        self.xp += amount

        print(f"[XP] {self.name} ganhou {amount} XP (Total: {self.xp}/{self.xp_to_next})")

        leveled_up = False
        while self.xp >= self.xp_to_next:
            self.level_up()
            leveled_up = True

        if leveled_up:
            print(f"[LEVEL UP] ⬆️ {self.name} subiu de {old_level} para {self.level}!")
            self.attack_damage = self._calculate_attack_damage()
            self.defense_value = self._calculate_defense()

            # Verifica se pode evoluir após o level up
            self.check_and_evolve()

    def level_up(self):
        """Sobe de nível"""
        self.xp -= self.xp_to_next
        self.level += 1
        self._calculate_stats()
        self.current_hp = self.max_hp  # Cura ao subir nível
        self.xp_to_next = self._calculate_xp_needed()

    def is_boss_type(self):
        """Verifica se é um boss"""
        return hasattr(self, 'is_boss') and self.is_boss

    def is_alive(self):
        """Verifica se está vivo"""
        return self.current_hp > 0

    def get_hp_percentage(self):
        """Retorna porcentagem de HP"""
        return self.current_hp / self.max_hp

    def _calculate_attack_damage(self):
        """Calcula o poder de ataque baseado na média de Attack e Sp. Attack"""
        return (self.attack + self.sp_attack) / 2

    def _calculate_defense(self):
        """Calcula a defesa baseada na média de Defense e Sp. Defense"""
        return (self.defense + self.sp_defense) / 2

    def find_nearest_enemy(self, enemies):
        """Encontra o inimigo mais próximo dentro do range"""
        if not enemies:
            return None

        nearest = None
        min_distance = float('inf')

        for enemy in enemies:
            if enemy.is_alive() and enemy.is_wild:
                # Calcula distância até o inimigo
                dx = self.x - enemy.x
                dy = self.y - enemy.y
                distance = (dx ** 2 + dy ** 2) ** 0.5

                if distance < self.attack_range and distance < min_distance:
                    min_distance = distance
                    nearest = enemy

        return nearest

    def update_combat(self, dt, enemies):
        """Sistema de combate baseado em investidas"""

        # Atualiza cooldown
        if self.charge_cooldown > 0:
            self.charge_cooldown -= dt

        # Se o alvo morreu, volta imediatamente
        if self.target and not self.target.is_alive():
            self.target = None
            self.combat_state = "returning"
            return

        # Máquina de estados simplificada
        if self.combat_state == "idle":
            self._handle_idle_state(dt, enemies)

        elif self.combat_state == "charging":
            self._handle_charging_state(dt)

        elif self.combat_state == "returning":
            self._handle_returning_state(dt)

    def _handle_idle_state(self, dt, enemies):
        """Estado parado: procura inimigos próximos"""

        # Procura o inimigo mais próximo
        nearest = None
        min_distance = float('inf')

        for enemy in enemies:
            if enemy.is_alive() and enemy.is_wild:
                distance = self.get_distance_to(enemy)
                if distance < self.attack_range and distance < min_distance:
                    min_distance = distance
                    nearest = enemy

        # Se encontrou um inimigo e o cooldown acabou, inicia investida
        if nearest and self.charge_cooldown <= 0:
            self.target = nearest
            self.combat_state = "charging"
            print(f"[COMBATE] {self.name} investindo contra {nearest.name}")

    def _handle_charging_state(self, dt):
        """Estado de investida: move em linha reta até o alvo"""

        if not self.target or not self.target.is_alive():
            # Alvo morreu durante a investida
            self.combat_state = "returning"
            self.target = None
            return

        # Calcula direção até o alvo
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < 5:  # Chegou muito perto (colidiu)
            # CAUSA DANO AO ENCOSTAR
            self._perform_charge_attack(self.target)
            self.combat_state = "returning"
            self.charge_cooldown = self.charge_cooldown_max
            return

        # Move em linha reta com velocidade constante
        if distance > 0:
            # Normaliza o vetor e multiplica pela velocidade
            move_x = (dx / distance) * self.base_speed * dt * 60
            move_y = (dy / distance) * self.base_speed * dt * 60

            # Garante que não ultrapassa o alvo
            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.x += move_x
            self.y += move_y
            self.rect.x, self.rect.y = self.x, self.y

            # Atualiza direção para animação
            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

    def _handle_returning_state(self, dt):
        """Estado de retorno: volta para o spot original"""

        # Calcula direção até o spot
        dx = self.original_spot_x - self.x
        dy = self.original_spot_y - self.y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < 5:  # Chegou no spot
            self.x, self.y = self.original_spot_x, self.original_spot_y
            self.rect.x, self.rect.y = self.x, self.y
            self.combat_state = "idle"
            self.target = None
            return

        # Move de volta com velocidade constante
        if distance > 0:
            move_x = (dx / distance) * self.base_speed * dt * 60
            move_y = (dy / distance) * self.base_speed * dt * 60

            # Garante que não ultrapassa o spot
            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.x += move_x
            self.y += move_y
            self.rect.x, self.rect.y = self.x, self.y

            # Atualiza direção para animação
            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

    def _perform_charge_attack(self, target):
        """Executa o ataque de investida ao encostar no alvo"""

        # Calcula dano base
        base_damage = self.attack_damage * (self.level / 8)

        # Fator aleatório (±15%)
        import random
        damage_multiplier = random.uniform(0.85, 1.15)

        # Dano final
        damage = int(base_damage * damage_multiplier)

        # Aplica dano ao alvo (considerando defesa)
        defense_factor = max(0.4, 1.0 - (target.defense_value / 800))
        final_damage = max(2, int(damage * defense_factor))

        # CORREÇÃO: Passa o atacante (self) como parâmetro
        print(f"[INVESTIDA_DEBUG] {self.name} atacando {target.name} com dano {final_damage}")
        target.take_damage(final_damage, attacker=self)

        print(f"[INVESTIDA] {self.name} causou {final_damage} de dano em {target.name}")

        # Se o alvo morreu, o estado já vai mudar para returning naturalmente
        if not target.is_alive():
            print(f"[COMBATE] {target.name} foi derrotado!")

    def _attack_target(self, target):
        """Executa o ataque contra o alvo"""
        # Calcula dano base
        base_damage = self.attack_damage * (self.level / 10)  # Escala com level

        # Fator aleatório (±20%)
        import random
        damage_multiplier = random.uniform(0.8, 1.2)

        # Dano final
        damage = int(base_damage * damage_multiplier)

        # Aplica dano ao alvo (considerando defesa)
        defense_factor = max(0.5, 1.0 - (target.defense_value / 1000))  # Redução baseada em defesa
        final_damage = max(1, int(damage * defense_factor))

        # Aplica o dano
        target.take_damage(final_damage)

        print(f"[ATAQUE] {self.name} causou {final_damage} de dano em {target.name}")

        # Se o alvo morreu, muda o estado para voltar
        if not target.is_alive():
            print(f"[COMBATE] {target.name} foi derrotado!")
            self.target = None
            self.combat_state = "returning"

    def take_damage(self, damage, attacker=None):
        """
        Recebe dano de um atacante
        """
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - damage)

        # DEBUG: Mostra quem está atacando
        if attacker:
            print(
                f"[DANO_DEBUG] Atacante: {attacker.name}, Alvo: {self.name}, Dano: {damage}, HP restante: {self.current_hp}")

        # Registra contribuição de dano (se for um atacante válido)
        if attacker and self.is_wild:  # Só registra para inimigos selvagens
            attacker_id = id(attacker)
            if attacker_id not in self.damage_contributions:
                self.damage_contributions[attacker_id] = 0
                print(f"[DANO] Primeiro ataque de {attacker.name} em {self.name}")

            # Registra apenas o dano real causado (não excede o HP restante)
            actual_damage = min(damage, old_hp)
            self.damage_contributions[attacker_id] += actual_damage
            self.last_attacker = attacker

            print(f"[DANO] {attacker.name} causou {actual_damage} de dano em {self.name} "
                  f"(total acumulado: {self.damage_contributions[attacker_id]})")
        else:
            if not attacker:
                print(f"[DANO_DEBUG] Ataque sem atacante registrado em {self.name}")
            if not self.is_wild:
                print(f"[DANO_DEBUG] Alvo {self.name} não é selvagem, ignorando registro")

        # Se morreu, solta o item
        if self.current_hp <= 0:
            print(f"[MORTE] {self.name} foi derrotado!")
            print(f"[MORTE] Contribuições de dano: {self.damage_contributions}")
            if self.last_attacker:
                print(f"[MORTE] Último atacante: {self.last_attacker.name}")
            self.drop_item()
            self.combat_state = "idle"
            self.target = None

        return self.current_hp <= 0

    def get_xp_contributors(self):
        """
        Retorna lista de atacantes que contribuíram para a derrota
        Returns: lista de tuplas (attacker_id, damage_done)
        """
        if not self.damage_contributions:
            # Se não houver contribuições, usa o último atacante
            if self.last_attacker:
                return [(id(self.last_attacker), 1)]
            return []

        # Converte para lista e ordena por dano (maior primeiro)
        contributors = [(attacker_id, damage)
                        for attacker_id, damage in self.damage_contributions.items()]
        contributors.sort(key=lambda x: x[1], reverse=True)
        return contributors

    def clear_damage_tracking(self):
        """Limpa o rastreamento de dano (chamar quando o inimigo for removido)"""
        self.damage_contributions.clear()
        self.last_attacker = None

    def drop_item(self):
        """
        Faz o Pokémon soltar o item que está carregando (quando derrotado)
        """
        if self.is_carrying:
            item_name = self.is_carrying.item_name
            print(f"[POKEMON] {self.name} derrotado! Soltando {item_name}")

            # Reseta o item que estava sendo carregado
            self.is_carrying.reset_capture()

            # Limpa a referência no Pokémon
            self.is_carrying = None

    def calculate_damage(self, target):
        """Calcula dano contra um alvo (simplificado)"""
        # Fórmula simplificada: (attack * level) / (defense * 2) + 2
        damage = max(1, int((self.attack * self.level) / (target.defense * 2) + 2))

        # Variação aleatória (85-100%)
        damage = int(damage * random.uniform(0.85, 1.0))

        return damage

    def clear_carrying(self):
        """Limpa a referência ao item carregado (quando o Pokémon é capturado/removido)"""
        if self.is_carrying:
            print(f"[POKEMON] {self.name} não está mais carregando {self.is_carrying.item_name}")
            self.is_carrying = None

    def recalculate_path_after_capture(self):
        """
        Quando captura um item, calcula a rota mais curta:
        - Se está mais perto do início, volta para o início
        - Se está mais perto do fim, vai para o fim
        O objetivo é entregar o item o mais rápido possível!
        """
        if not self.path or self.path_index >= len(self.path):
            print(f"[POKEMON] {self.name}: não tem path válido para recalcular")
            return

        current_idx = self.path_index

        # ===== CALCULAR DISTÂNCIA ATÉ O INÍCIO (PONTO 0) =====
        start_distance = 0

        # Distância até o ponto atual
        if current_idx > 0:
            start_distance += math.hypot(self.x - self.path[current_idx][0],
                                         self.y - self.path[current_idx][1])

        # Soma distâncias dos pontos anteriores
        for i in range(current_idx, 0, -1):
            x1, y1 = self.path[i]
            x2, y2 = self.path[i - 1]
            start_distance += math.hypot(x2 - x1, y2 - y1)

        # ===== CALCULAR DISTÂNCIA ATÉ O FIM (ÚLTIMO PONTO) =====
        end_distance = 0

        # Distância até o ponto atual
        if current_idx < len(self.path) - 1:
            end_distance += math.hypot(self.x - self.path[current_idx][0],
                                       self.y - self.path[current_idx][1])

        # Soma distâncias dos pontos restantes
        for i in range(current_idx, len(self.path) - 1):
            x1, y1 = self.path[i]
            x2, y2 = self.path[i + 1]
            end_distance += math.hypot(x2 - x1, y2 - y1)

        print(f"[DECISAO_ROTA] {self.name}:")
        print(f"  Distância até INÍCIO: {start_distance:.1f}")
        print(f"  Distância até FIM: {end_distance:.1f}")

        # ===== DECIDE A MELHOR ROTA (MAIS CURTA) =====
        if start_distance < end_distance:
            # VAI PARA O INÍCIO
            print(f"[DECISAO_ROTA] {self.name} vai para o INÍCIO! (mais curto)")

            # Guarda path original se necessário
            if not hasattr(self, 'original_path') or self.original_path is None:
                self.original_path = self.path.copy()
                print(f"[POKEMON] Path original guardado para {self.name}")

            # Inverte o path
            self.path = list(reversed(self.original_path.copy()))

            # Encontra o ponto mais próximo no novo path
            min_dist = float('inf')
            closest_idx = 0
            for i, point in enumerate(self.path):
                dist = math.hypot(self.x - point[0], self.y - point[1])
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i

            self.path_index = closest_idx
            print(f"[DECISAO_ROTA] {self.name} vai para INÍCIO, iniciando no índice {closest_idx}")

        else:
            # VAI PARA O FIM
            print(f"[DECISAO_ROTA] {self.name} vai para o FIM! (mais curto)")

            # Se já está indo para o fim, mantém o path original
            if hasattr(self, 'original_path') and self.original_path is not None:
                # Restaura path original se estava invertido
                self.path = self.original_path.copy()
            else:
                self.original_path = self.path.copy()

            # Encontra o ponto mais próximo
            min_dist = float('inf')
            closest_idx = self.path_index
            for i, point in enumerate(self.path):
                if i >= self.path_index:  # Só considera pontos à frente
                    dist = math.hypot(self.x - point[0], self.y - point[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = i

            self.path_index = closest_idx
            print(f"[DECISAO_ROTA] {self.name} vai para FIM, continuando no índice {closest_idx}")

        # Reseta estado de combate
        self.target = None
        self.combat_state = "idle"

        # Para boss, marca que está carregando item (mas velocidade normal)
        if self.is_boss:
            self.is_returning_with_item = True
            print(f"[BOSS] {self.name} está carregando item! Rota escolhida.")

    def update(self, dt, player=None, enemies=None, items=None):
        """Update simplificado - Pokémon segue path e pode carregar itens"""
        # Guarda posição anterior para calcular direção
        self.last_x = self.x
        self.last_y = self.y

        # Cooldown de ataque
        if not self.can_attack:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.can_attack = True

        # Lógica de captura de itens (só para inimigos)
        if self.is_wild and items is not None and not self.is_carrying:
            for item in items:
                if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                    dist = self.get_distance_to(item)
                    if dist < self.capture_range:
                        item.start_capture(self)
                        print(f"[POKEMON] {self.name} começou a carregar {item.item_name}")

                        # Recalcula rota baseado na posição atual
                        self.recalculate_path_after_capture()
                        break
        elif items is None:
            # Log para debug - só mostra às vezes para não floodar
            if random.random() < 0.001:  # 0.1% de chance
                print(f"[POKEMON] {self.name}: items=None, não pode capturar")

        # Movimento em path (sempre segue o path)
        if self.path and len(self.path) > 0:
            # Se já completou o path, não move mais
            if self.path_index >= len(self.path):
                return

            target_x, target_y = self.path[self.path_index]

            # Calcula direção
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            # Atualiza direção baseada no movimento
            if distance > 0:
                if abs(dx) > abs(dy):
                    self.current_direction = "right" if dx > 0 else "left"
                else:
                    self.current_direction = "down" if dy > 0 else "up"

            # Velocidade de movimento (pixels por segundo)
            move_distance = self.speed * dt * 60

            # Verifica se chegou no ponto atual
            if distance <= move_distance:
                # Chegou exatamente no ponto ou está muito próximo
                self.x, self.y = target_x, target_y
                self.path_index += 1
                print(f"[POKEMON] {self.name} chegou no ponto {self.path_index}/{len(self.path)}")

                # Se completou o path, não precisa continuar movimento neste frame
                if self.path_index >= len(self.path):
                    print(f"[POKEMON] {self.name} COMPLETOU o path! Aguardando verificação...")
                    return
            else:
                # Move na direção do próximo ponto
                if distance > 0:
                    move_x = (dx / distance) * move_distance
                    move_y = (dy / distance) * move_distance
                    self.x += move_x
                    self.y += move_y

            self.rect.x, self.rect.y = self.x, self.y

        # Se está carregando um item, atualiza o progresso
        if self.is_carrying:
            self.is_carrying.update_capture(dt)

        # Animação (sempre executa)
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            if (self.inmap_frames and
                    self.current_direction in self.inmap_frames and
                    self.inmap_frames[self.current_direction]):
                frames_list = self.inmap_frames[self.current_direction]
                self.current_frame = (self.current_frame + 1) % len(frames_list)
                self.sprite = frames_list[self.current_frame]

    def get_distance_to(self, entity):
        """Calcula distância até outra entidade"""
        dx = self.x - entity.x
        dy = self.y - entity.y
        return (dx ** 2 + dy ** 2) ** 0.5

    def render_hp(self, screen, camera=None):
        """Renderiza a barra de HP (boss tem barra azul)"""
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        hp_percent = self.current_hp / self.max_hp

        # Tamanhos proporcionais ao zoom
        bar_width = int(32 * zoom_scale)
        bar_height = max(1, int(3 * zoom_scale))

        # Posiciona a barra acima do sprite
        bar_x = screen_x - bar_width // 2

        sprite_height = int(self.map_sprite_size * zoom_scale)
        foot_offset = int(sprite_height * 0.2)
        sprite_top = (screen_y + foot_offset) - sprite_height
        bar_y = sprite_top + 10

        # Fundo da barra
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        # Barra de HP (cor baseada na porcentagem)
        if self.is_boss:
            color = (0, 0, 255)
        else:
            if not self.is_shiny:
                if hp_percent > 0.5:
                    color = (0, 200, 0)
                elif hp_percent > 0.25:
                    color = (255, 255, 0)
                else:
                    color = (255, 0, 0)
            else:
                color = (255, 0, 0)

        # Barra de progresso
        progress_width = int(bar_width * hp_percent)
        if progress_width > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))

        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

    def render(self, screen, camera=None, show_hp=True):
        """Renderiza Pokémon com tamanho especial para boss (64x64)"""

        # 1. OBTÉM POSIÇÃO E ESCALA
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        # 2. PREPARA O SPRITE (OU PLACEHOLDER)
        sprite_to_render = self._prepare_sprite(zoom_scale)

        if sprite_to_render:
            # Tem sprite - renderiza
            sprite_rect = self._render_sprite(screen, sprite_to_render, screen_x, screen_y, zoom_scale)
        else:
            # Não tem sprite - renderiza placeholder
            sprite_rect = self._render_placeholder(screen, screen_x, screen_y, zoom_scale)

        # 3. RENDERIZA TEXTO (se for selvagem)
        if self.is_wild and sprite_rect:
            self._render_wild_text(screen, sprite_rect, zoom_scale)

        # 4. RENDERIZA HP
        if show_hp:
            self.render_hp(screen, camera)

        # 5. DEBUG
        if hasattr(self, 'show_debug') and self.show_debug:
            self._render_debug(screen, screen_x, screen_y, zoom_scale, sprite_rect)

    def _prepare_sprite(self, zoom_scale):
        """Prepara o sprite para renderização (boss em escala inteira)"""
        if not self.sprite:
            return None

        if self.is_boss:
            orig_width, orig_height = self.sprite.get_width(), self.sprite.get_height()

            scale_factor = 2
            new_width = orig_width * scale_factor
            new_height = orig_height * scale_factor

            return pygame.transform.scale(self.sprite, (new_width, new_height))

        return self.sprite

    def _render_sprite(self, screen, sprite, screen_x, screen_y, zoom_scale):
        """Renderiza o sprite com zoom e pivô nos pés"""
        current_width, current_height = sprite.get_width(), sprite.get_height()

        # Aplica zoom
        final_width = max(1, int(current_width * zoom_scale))
        final_height = max(1, int(current_height * zoom_scale))
        scaled_sprite = pygame.transform.scale(sprite, (final_width, final_height))

        # Posiciona com pivô nos pés
        foot_offset = int(final_height * 0.2)
        sprite_rect = scaled_sprite.get_rect()
        sprite_rect.bottom = int(screen_y) + foot_offset
        sprite_rect.centerx = int(screen_x)

        screen.blit(scaled_sprite, sprite_rect)
        return sprite_rect

    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        """Renderiza placeholder quando não tem sprite"""
        size = int((64 if self.is_boss else self.map_sprite_size) * zoom_scale)
        foot_offset = int(size * 0.2)

        rect = pygame.Rect(0, 0, size, size)
        rect.bottom = int(screen_y) + foot_offset
        rect.centerx = int(screen_x)

        pygame.draw.rect(screen, (255, 0, 255), rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        return rect

    def _render_wild_text(self, screen, sprite_rect, zoom_scale):
        """Renderiza nome e nível para Pokémon selvagem"""
        # Tamanhos de fonte
        name_font_size = max(5, int(6 * zoom_scale))
        level_font_size = max(4, int(6 * zoom_scale))

        try:
            name_font = pygame.font.Font(None, name_font_size)
            level_font = pygame.font.Font(None, level_font_size)
        except:
            name_font = pygame.font.SysFont('Arial', name_font_size)
            level_font = pygame.font.SysFont('Arial', level_font_size)

        # Prepara textos
        name_text = f"{self.name} - "
        level_text = f"lv. {self.level:02d}"

        # Cores
        text_color = (255, 255, 255)
        outline_color = (0, 0, 0)

        if self.is_shiny:
            level_color = (255, 215, 0)
        elif self.is_boss:
            level_color = (255, 100, 100)
            text_color = (255, 100, 100)
        else:
            level_color = (255, 255, 255)

        # Renderiza
        name_surface = name_font.render(name_text, True, text_color)
        level_surface = level_font.render(level_text, True, level_color)

        name_outline = name_font.render(name_text, True, outline_color)
        level_outline = level_font.render(level_text, True, outline_color)

        # Posiciona
        total_width = name_surface.get_width() + 2 + level_surface.get_width()
        start_x = sprite_rect.centerx - total_width // 2
        text_y = sprite_rect.top - name_font_size

        name_x, name_y = start_x, text_y
        level_x = start_x + name_surface.get_width() + 2
        level_y = text_y + (name_font_size - level_font_size)

        # Desenha contorno
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

    def _render_debug(self, screen, screen_x, screen_y, zoom_scale, sprite_rect):
        """Renderiza informações de debug"""
        # Calcula offset atual
        if sprite_rect:
            foot_offset = int(sprite_rect.height * 0.2)
        else:
            size = int((64 if self.is_boss else self.map_sprite_size) * zoom_scale)
            foot_offset = int(size * 0.2)

        # Ponto do pivô (vermelho)
        pygame.draw.circle(screen, (255, 0, 0),
                           (int(screen_x), int(screen_y) + foot_offset), 6, 2)

        if sprite_rect:
            # Centro do sprite (verde)
            pygame.draw.circle(screen, (0, 255, 0),
                               (sprite_rect.centerx, sprite_rect.centery), 4, 1)

            # Linha do chão (amarelo)
            pygame.draw.line(screen, (255, 255, 0),
                             (sprite_rect.left, int(screen_y) + foot_offset),
                             (sprite_rect.right, int(screen_y) + foot_offset), 1)

            # Linha do chão original (azul)
            pygame.draw.line(screen, (0, 255, 255),
                             (sprite_rect.left, int(screen_y)),
                             (sprite_rect.right, int(screen_y)), 1)

    def get_info_string(self):
        """Retorna string com informações do Pokémon"""
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")