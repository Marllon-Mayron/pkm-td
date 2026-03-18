# src/entities/pokemon.py
import pygame
import math
import random
from src.entities.base import Entity
from src.data.pokedex import Pokedex


class Pokemon(Entity):
    def __init__(self, x, y, pokemon_id, level=5, is_wild=False, shiny=False):
        self.pokedex = Pokedex()
        self.pokemon_data = self.pokedex.get_pokemon(pokemon_id)

        if not self.pokemon_data:
            raise ValueError(f"Pokémon ID {pokemon_id} não encontrado")

        self.id = pokemon_id
        self.name = self.pokemon_data["name"].capitalize()
        self.level = level
        self.is_shiny = shiny

        self.is_placed = False  # False = no time, True = no mapa
        self.spot_id = None  # ID do spot onde está colocado

        # Tipos
        self.types = self.pokemon_data["types"]

        # Gerar IVs aleatórios (0-31)
        self.ivs = {
            "hp": random.randint(0, 31),
            "attack": random.randint(0, 31),
            "defense": random.randint(0, 31),
            "special_attack": random.randint(0, 31),
            "special_defense": random.randint(0, 31),
            "speed": random.randint(0, 31)
        }

        # EVs (inicialmente 0)
        self.evs = {
            "hp": 0, "attack": 0, "defense": 0,
            "special_attack": 0, "special_defense": 0, "speed": 0
        }

        # Calcular stats
        self.base_stats = self.pokemon_data["base_stats"]
        self._calculate_stats()

        # Estado atual
        self.current_hp = self.max_hp
        self.xp = 0
        self.xp_to_next = self._calculate_xp_needed()

        # Sprite para UI (front)
        self.ui_sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny)

        # Sprite para batalha (back) - quando é do jogador
        self.battle_sprite = self.pokedex.get_sprite(pokemon_id, "back", shiny)

        # Frames de animação para o mapa
        self.inmap_frames = self.pokedex.get_inmap_animation(pokemon_id, shiny)
        self.current_direction = "down"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.1  # 10 frames por segundo

        # Obtém o tamanho do sprite no mapa da Pokedex
        self.map_sprite_size = self.pokedex.get_map_sprite_size(pokemon_id, shiny)

        # Tamanho para entidade no mapa
        width = self.map_sprite_size
        height = self.map_sprite_size

        # Usa o primeiro frame da direção down como sprite padrão
        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        # Atributos de jogo
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # Movimento (para Tower Defense)
        self.path = []
        self.path_index = 0
        self.speed = 2.0

        # Batalha
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60  # frames
        self.target = None

        # Efeitos visuais - AJUSTADOS para sprite 32x32
        self.hp_bar_width = 32  # Mesmo tamanho do sprite
        self.hp_bar_height = 3  # Mais fina

        # Natureza (opcional - para dar variedade)
        self.nature_multipliers = self._generate_nature()

        # Armazena a última posição para calcular direção
        self.last_x = x
        self.last_y = y

        self.is_carrying = None  # Item que está carregando
        self.capture_range = 20  # Distância para capturar item

        # ATRIBUTOS DE COMBATE
        self.attack_range = 60  # Distância para iniciar investida
        self.combat_state = "idle"  # idle, charging, returning
        self.target = None
        self.original_spot_x = x
        self.original_spot_y = y

        # Velocidade constante (sem aceleração)
        self.base_speed = self.speed  # Preserva a velocidade base

        # Cooldown entre investidas
        self.charge_cooldown = 0.0
        self.charge_cooldown_max = 1.5  # 2 segundos entre investidas

        # Stats de combate
        self.attack_damage = self._calculate_attack_damage()
        self.defense_value = self._calculate_defense()

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

    def take_damage(self, damage):
        """Recebe dano, retorna True se morreu"""
        self.current_hp = max(0, self.current_hp - damage)
        return self.current_hp <= 0

    def heal(self, amount=None):
        """Cura o Pokémon"""
        if amount is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def gain_xp(self, amount):
        """Ganha XP e verifica level up"""
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.level_up()

    def level_up(self):
        """Sobe de nível"""
        self.xp -= self.xp_to_next
        self.level += 1
        self._calculate_stats()
        self.current_hp = self.max_hp  # Cura ao subir nível
        self.xp_to_next = self._calculate_xp_needed()

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
        base_damage = self.attack_damage * (self.level / 8)  # Ajustado para ser mais impactante

        # Fator aleatório (±15%)
        import random
        damage_multiplier = random.uniform(0.85, 1.15)

        # Dano final
        damage = int(base_damage * damage_multiplier)

        # Aplica dano ao alvo (considerando defesa)
        defense_factor = max(0.4, 1.0 - (target.defense_value / 800))
        final_damage = max(2, int(damage * defense_factor))

        # Aplica o dano
        target.take_damage(final_damage)

        print(f"[INVESTIDA] {self.name} causou {final_damage} de dano em {target.name}")

        # Feedback visual (opcional - pode adicionar um efeito de tremor depois)

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

    def take_damage(self, damage):
        """Recebe dano, retorna True se morreu"""
        self.current_hp = max(0, self.current_hp - damage)

        # Se morreu, solta o item que estava carregando
        if self.current_hp <= 0:
            self.drop_item()
            self.combat_state = "idle"
            self.target = None

        return self.current_hp <= 0

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
            # Verifica se há algum item próximo
            for item in items:
                if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                    dist = self.get_distance_to(item)
                    if dist < self.capture_range:
                        # Inicia captura do item (não desvia do path)
                        item.start_capture(self)
                        print(f"[POKEMON] {self.name} começou a carregar {item.item_name}")
                        break  # Pega apenas o primeiro item
        elif items is None:
            # Log para debug - só mostra às vezes para não floodar
            if random.random() < 0.001:  # 0.1% de chance
                print(f"[POKEMON] {self.name}: items=None, não pode capturar")

        # Movimento em path (sempre segue o path)
        if self.path and len(self.path) > 0 and self.path_index < len(self.path):
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

            # Velocidade de movimento
            move_distance = self.speed * dt * 60

            if distance < move_distance:
                # Chegou no ponto
                self.x, self.y = target_x, target_y
                self.path_index += 1
                print(f"[POKEMON] {self.name} chegou no ponto {self.path_index}/{len(self.path)}")
            else:
                # Move na direção
                if distance > 0:
                    self.x += (dx / distance) * self.speed * dt * 60
                    self.y += (dy / distance) * self.speed * dt * 60

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
        sprite_top = (screen_y + foot_offset) - sprite_height  # Ajustado com o offset

        bar_y = sprite_top + 10

        # Fundo da barra
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        # Barra de HP (cor baseada na porcentagem)
        if hp_percent > 0.5:
            color = (0, 200, 0)
        elif hp_percent > 0.25:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)

        # Barra de progresso
        progress_width = int(bar_width * hp_percent)
        if progress_width > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))

        # Borda
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)


    def render(self, screen, camera=None, show_hp=True):
        """Renderiza Pokémon """

        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            # Obtém posição na tela (coordenadas com zoom aplicado)
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)

            # Calcula a escala baseada no zoom da câmera
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        # SPRITE - COM PIVÔ NOS PÉS
        if self.sprite:
            # Obtém tamanho atual
            current_width = self.sprite.get_width()
            current_height = self.sprite.get_height()

            # APLICA O ZOOM da câmera
            final_width = max(1, int(current_width * zoom_scale))
            final_height = max(1, int(current_height * zoom_scale))

            # Redimensiona com o zoom atual
            scaled_sprite = pygame.transform.scale(self.sprite, (final_width, final_height))

            # POSICIONA COM PIVÔ NOS PÉS
            # Ajusta o offset para enterrar os pés no chão
            foot_offset = int(final_height * 0.2)  # 20% do sprite para baixo

            sprite_rect = scaled_sprite.get_rect()
            # Coloca o pivô (pés) mais para baixo do sprite
            sprite_rect.bottom = int(screen_y) + foot_offset  # Parte inferior mais baixa
            sprite_rect.centerx = int(screen_x)  # Centralizado no X

            screen.blit(scaled_sprite, sprite_rect)

            # Debug - mostra o ponto de pivô (pés)
            if hasattr(self, 'show_debug') and self.show_debug:
                # Vermelho: ponto do pivô (pés) - agora mais baixo
                pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y) + foot_offset), 6, 2)
                # Verde: centro do sprite (para referência)
                centro_x = sprite_rect.centerx
                centro_y = sprite_rect.centery
                pygame.draw.circle(screen, (0, 255, 0), (centro_x, centro_y), 4, 1)
                # Amarelo: linha do chão (agora mais baixa)
                pygame.draw.line(screen, (255, 255, 0),
                                 (sprite_rect.left, int(screen_y) + foot_offset),
                                 (sprite_rect.right, int(screen_y) + foot_offset), 1)
                # Azul: linha do chão original (para referência)
                pygame.draw.line(screen, (0, 255, 255),
                                 (sprite_rect.left, int(screen_y)),
                                 (sprite_rect.right, int(screen_y)), 1)
        else:
            # Placeholder - também usa pivô nos pés com offset
            size = int(self.map_sprite_size * zoom_scale)
            foot_offset = int(size * 0.2)  # 20% do placeholder para baixo

            # Desenha um retângulo com a parte inferior na posição do pivô + offset
            rect = pygame.Rect(0, 0, size, size)
            rect.bottom = int(screen_y) + foot_offset
            rect.centerx = int(screen_x)
            pygame.draw.rect(screen, (255, 0, 255), rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)

            # Debug para o placeholder
            if hasattr(self, 'show_debug') and self.show_debug:
                pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y) + foot_offset), 6, 2)

        # Barra de HP
        if show_hp:
            hp_percent = self.current_hp / self.max_hp

            # Tamanhos proporcionais ao zoom
            bar_width = int(32 * zoom_scale)
            bar_height = max(1, int(3 * zoom_scale))

            # Posiciona a barra acima do sprite
            bar_x = screen_x - bar_width // 2

            sprite_height = int(self.map_sprite_size * zoom_scale)

            foot_offset = int(sprite_height * 0.2)
            sprite_top = (screen_y + foot_offset) - sprite_height  # Ajustado com o offset

            bar_y = sprite_top + 10

            # Fundo da barra
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

            # Barra de HP (cor baseada na porcentagem)
            if hp_percent > 0.5:
                color = (0, 200, 0)
            elif hp_percent > 0.25:
                color = (255, 255, 0)
            else:
                color = (255, 0, 0)

            # Barra de progresso
            progress_width = int(bar_width * hp_percent)
            if progress_width > 0:
                pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))

            # Borda
            pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

    def get_info_string(self):
        """Retorna string com informações do Pokémon"""
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")