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

        # Tamanho para entidade no mapa
        width = 32
        height = 32

        # Usa o primeiro frame da direção down como sprite padrão
        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        # Atributos de jogo
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # Movimento (para Tower Defense)
        self.path = []
        self.path_index = 0
        self.speed = 1.0

        # Batalha
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60  # frames
        self.target = None

        # Efeitos visuais
        self.hp_bar_width = 40
        self.hp_bar_height = 4

        # Natureza (opcional - para dar variedade)
        self.nature_multipliers = self._generate_nature()

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

    def calculate_damage(self, target):
        """Calcula dano contra um alvo (simplificado)"""
        # Fórmula simplificada: (attack * level) / (defense * 2) + 2
        damage = max(1, int((self.attack * self.level) / (target.defense * 2) + 2))

        # Variação aleatória (85-100%)
        damage = int(damage * random.uniform(0.85, 1.0))

        return damage

    def update(self, dt):
        """Atualiza Pokémon"""
        # Cooldown de ataque
        if not self.can_attack:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.can_attack = True

        # Movimento em path (para Tower Defense)
        if self.path and self.path_index < len(self.path):
            target_x, target_y = self.path[self.path_index]

            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < self.speed:
                self.x, self.y = target_x, target_y
                self.path_index += 1
            else:
                # Move na direção
                direction_x = dx / distance
                direction_y = dy / distance
                self.x += direction_x * self.speed
                self.y += direction_y * self.speed

            self.rect.x, self.rect.y = self.x, self.y

    def render(self, screen, camera=None, show_hp=True):
        """Renderiza Pokémon"""
        screen_x = self.x - (camera.x if camera else 0)
        screen_y = self.y - (camera.y if camera else 0)

        # Sombra (opcional)
        shadow_offset = 2
        shadow_rect = pygame.Rect(screen_x - shadow_offset, screen_y - shadow_offset,
                                  self.width, self.height)
        pygame.draw.rect(screen, (40, 40, 40), shadow_rect)

        # Sprite
        if self.sprite:
            screen.blit(self.sprite, (screen_x, screen_y))

        # Efeito shiny
        if self.is_shiny:
            # Brilho amarelo ao redor
            pygame.draw.rect(screen, (255, 255, 100),
                             (screen_x - 2, screen_y - 2, self.width + 4, self.height + 4), 2)

        # Barra de HP (se necessário)
        if show_hp and (self.is_selected or self.current_hp < self.max_hp):
            hp_percent = self.current_hp / self.max_hp

            # Posição da barra
            bar_x = screen_x + (self.width - self.hp_bar_width) // 2
            bar_y = screen_y - 10

            # Fundo
            pygame.draw.rect(screen, (60, 60, 60),
                             (bar_x, bar_y, self.hp_bar_width, self.hp_bar_height))

            # Barra de HP
            if hp_percent > 0.5:
                color = (0, 200, 0)
            elif hp_percent > 0.25:
                color = (255, 255, 0)
            else:
                color = (255, 0, 0)

            hp_width = int(self.hp_bar_width * hp_percent)
            pygame.draw.rect(screen, color,
                             (bar_x, bar_y, hp_width, self.hp_bar_height))

            # Borda
            pygame.draw.rect(screen, (100, 100, 100),
                             (bar_x, bar_y, self.hp_bar_width, self.hp_bar_height), 1)

        # Nível (opcional)
        if self.is_selected:
            level_font = pygame.font.Font(None, 16)
            level_text = level_font.render(f"Lv.{self.level}", True, (255, 255, 255))
            text_rect = level_text.get_rect(center=(screen_x + self.width // 2, screen_y - 20))
            screen.blit(level_text, text_rect)

    def get_info_string(self):
        """Retorna string com informações do Pokémon"""
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")