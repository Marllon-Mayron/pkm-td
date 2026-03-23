# src/battle/projectile.py
"""
Projétil para ataques especiais
"""
import pygame
import math


class Projectile:
    """Projétil que viaja do atacante ao alvo"""

    def __init__(self, attacker, target, move_name, damage, effectiveness, color, speed=300.0):
        self.attacker = attacker
        self.target = target
        self.move_name = move_name
        self.damage = damage
        self.effectiveness = effectiveness
        self.color = color
        self.speed = speed

        # Posição inicial (posição do atacante)
        self.x = attacker.x
        self.y = attacker.y

        # Posição alvo
        self.target_x = target.x
        self.target_y = target.y

        # Calcular direção
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            self.vx = (dx / distance) * speed
            self.vy = (dy / distance) * speed
        else:
            self.vx = 0
            self.vy = 0

        # Estado
        self.is_finished = False
        self.hit = False

        # Para animação
        self.size = 8
        self.trail = []  # Trail de partículas
        self.trail_length = 5

        # Tempo de vida máximo (segundos)
        self.max_lifetime = 3.0
        self.lifetime = 0.0

    def update(self, dt: float):
        """Atualiza posição do projétil"""
        self.lifetime += dt

        # Se já passou do tempo máximo, desaparece
        if self.lifetime >= self.max_lifetime:
            self.is_finished = True
            return

        # Guardar posição anterior para trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)

        # Atualizar posição
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Verificar se atingiu o alvo
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Se estiver perto o suficiente, causa dano
        if distance < self.target.map_sprite_size / 2 and not self.hit:
            self.hit = True
            self._apply_damage()
            self.is_finished = True

        # Verificar se o alvo morreu (desaparece)
        if not self.target.is_alive():
            self.is_finished = True

    def _apply_damage(self):
        """Aplica dano ao alvo"""
        # Aplicar dano ao alvo
        self.target.take_damage(self.damage, attacker=self.attacker)

        # Registrar contribuição de dano
        attacker_id = id(self.attacker)
        self.target.damage_contributions[attacker_id] = \
            self.target.damage_contributions.get(attacker_id, 0) + self.damage

        # Log
        if self.effectiveness > 1.0:
            print(f"[BATTLE] {self.move_name} é super efetivo!")
        elif self.effectiveness < 1.0 and self.effectiveness > 0:
            print(f"[BATTLE] {self.move_name} não é muito efetivo...")
        elif self.effectiveness == 0:
            print(f"[BATTLE] {self.move_name} não afeta {self.target.name}!")

        print(f"[BATTLE] {self.move_name} causou {self.damage} de dano a {self.target.name}!")

    def render(self, screen, camera, screen_manager):
        """Renderiza o projétil"""
        # Converter para coordenadas de tela
        screen_x, screen_y = screen_manager.world_to_screen(self.x, self.y, camera)
        zoom_scale = camera.zoom * screen_manager.render_scale

        # Desenhar trail
        for i, (tx, ty) in enumerate(self.trail):
            trail_x, trail_y = screen_manager.world_to_screen(tx, ty, camera)
            alpha = 255 * (i / len(self.trail))
            size = max(1, int(self.size * zoom_scale * (i / len(self.trail))))

            trail_color = (*self.color, alpha)
            pygame.draw.circle(screen, self.color, (int(trail_x), int(trail_y)), size)

        # Desenhar projétil principal
        size = max(2, int(self.size * zoom_scale))
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), size)

        # Brilho no centro
        inner_size = max(1, size // 2)
        inner_color = (min(255, self.color[0] + 50),
                       min(255, self.color[1] + 50),
                       min(255, self.color[2] + 50))
        pygame.draw.circle(screen, inner_color, (int(screen_x), int(screen_y)), inner_size)