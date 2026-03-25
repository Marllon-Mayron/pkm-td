# src/battle/projectile.py
"""
Projétil para ataques especiais
"""
import pygame
import random
import math


class Projectile:
    """Projétil que viaja do atacante ao alvo"""

    def __init__(self, attacker, target, move_name, damage, effectiveness, color, speed=300.0, will_hit=True):
        self.attacker = attacker
        self.target = target
        self.move_name = move_name
        self.damage = damage
        self.effectiveness = effectiveness
        self.color = color
        self.speed = speed
        self.will_hit = will_hit  # Se o ataque vai acertar ou errar

        # Posição inicial (posição do atacante)
        self.x = attacker.x
        self.y = attacker.y

        # Estado
        self.is_finished = False
        self.hit = False

        # Controle de exibição do texto MISS
        self.miss_text_timer = 0.0
        self.miss_text_duration = 0.6  # Duração do texto MISS em segundos

        # Para animação - AUMENTADO para mais rastros
        self.size = 10  # Aumentado de 8 para 10
        self.trail = []  # Trail de partículas
        self.trail_length = 12  # Aumentado de 5 para 12 (mais rastros)

        # Para efeito de partículas extras
        self.particles = []  # Partículas adicionais que se espalham
        self.particle_timer = 0
        self.particle_interval = 0.05  # Criar partícula a cada 0.05 segundos

        # Tempo de vida máximo (segundos)
        self.max_lifetime = 5.0  # Aumentado de 3 para 5 segundos
        self.lifetime = 0.0

        # Para suavizar a perseguição
        self.angle = 0
        self.last_target_pos = (target.x, target.y)

    def update(self, dt: float):
        """Atualiza posição do projétil com perseguição"""
        self.lifetime += dt

        # Se já passou do tempo máximo, desaparece
        if self.lifetime >= self.max_lifetime:
            self.is_finished = True
            return

        # Verificar se o alvo ainda existe e está vivo
        if not self.target or not self.target.is_alive():
            self.is_finished = True
            return

        # Atualizar timer do texto MISS
        if self.miss_text_timer > 0:
            self.miss_text_timer -= dt

        # Guardar posição anterior para trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)

        # ===== PERSegUIÇÃO EM TEMPO REAL =====
        # Calcular direção para o alvo (atualizado a cada frame)
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # Direção normalizada
            dir_x = dx / distance
            dir_y = dy / distance

            # Atualizar velocidade para mirar no alvo
            self.vx = dir_x * self.speed
            self.vy = dir_y * self.speed

            # Armazenar ângulo para partículas
            self.angle = math.atan2(dy, dx)

        # Atualizar posição
        self.x += self.vx * dt
        self.y += self.vy * dt

        # ===== GERAR PARTÍCULAS ADICIONAIS =====
        self.particle_timer += dt
        if self.particle_timer >= self.particle_interval:
            self.particle_timer = 0
            # Criar partículas ao longo do rastro
            self._create_particles()

        # Atualizar partículas existentes
        for particle in self.particles[:]:
            particle['life'] -= dt
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            if particle['life'] <= 0:
                self.particles.remove(particle)

        # Verificar se atingiu o alvo
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Se estiver perto o suficiente, causa dano ou mostra MISS
        if distance < self.target.map_sprite_size / 2 and not self.hit:
            self.hit = True

            if self.will_hit:
                # Acerrou - aplica dano
                self._apply_damage()
            else:
                # Errou - mostra texto MISS e não aplica dano
                self._apply_miss()

            self.is_finished = True

    def _create_particles(self):
        """Cria partículas de rastro adicionais"""
        # Direção oposta ao movimento (rastro)
        if hasattr(self, 'vx') and hasattr(self, 'vy'):
            speed_magnitude = math.sqrt(self.vx * self.vx + self.vy * self.vy)
            if speed_magnitude > 0:
                # Direção do rastro (oposta ao movimento)
                trail_dir_x = -self.vx / speed_magnitude
                trail_dir_y = -self.vy / speed_magnitude

                # Variação aleatória
                angle_variation = random.uniform(-0.5, 0.5)
                cos_a = math.cos(angle_variation)
                sin_a = math.sin(angle_variation)

                particle_dir_x = trail_dir_x * cos_a - trail_dir_y * sin_a
                particle_dir_y = trail_dir_x * sin_a + trail_dir_y * cos_a

                # Velocidade da partícula
                particle_speed = random.uniform(20, 60)

                self.particles.append({
                    'x': self.x,
                    'y': self.y,
                    'vx': particle_dir_x * particle_speed,
                    'vy': particle_dir_y * particle_speed,
                    'life': random.uniform(0.1, 0.3),
                    'size': random.uniform(2, 4)
                })

    def _apply_damage(self):
        """Aplica dano ao alvo"""
        # Aplicar dano ao alvo
        self.target.take_damage(self.damage, attacker=self.attacker)

        # Registrar contribuição de dano
        attacker_id = id(self.attacker)
        self.target.damage_contributions[attacker_id] = \
            self.target.damage_contributions.get(attacker_id, 0) + self.damage

        # Toca o som de impacto (do alvo)
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_hit_sound(self.move_name)

        # Log
        if self.effectiveness > 1.0:
            print(f"[BATTLE] {self.move_name} é super efetivo!")
        elif self.effectiveness < 1.0 and self.effectiveness > 0:
            print(f"[BATTLE] {self.move_name} não é muito efetivo...")
        elif self.effectiveness == 0:
            print(f"[BATTLE] {self.move_name} não afeta {self.target.name}!")

        print(f"[BATTLE] {self.move_name} causou {self.damage} de dano a {self.target.name}!")

    def _apply_miss(self):
        """Aplica efeito de erro (MISS) - não causa dano, mostra texto no ATACANTE"""
        print(f"[BATTLE] {self.move_name} errou {self.target.name}!")

        # Mostra MISS no ATACANTE (quem usou o golpe)
        if hasattr(self.attacker, 'miss_timer'):
            self.attacker.miss_timer = 0.6
        else:
            self.attacker.miss_timer = 0.6

    def render(self, screen, camera, screen_manager):
        """Renderiza o projétil com efeitos visuais melhorados"""
        # Converter para coordenadas de tela
        screen_x, screen_y = screen_manager.world_to_screen(self.x, self.y, camera)
        zoom_scale = camera.zoom * screen_manager.render_scale

        # ===== 1. DESENHAR PARTÍCULAS ADICIONAIS =====
        for particle in self.particles:
            particle_x, particle_y = screen_manager.world_to_screen(particle['x'], particle['y'], camera)
            particle_size = max(1, int(particle['size'] * zoom_scale))
            if particle_size > 0:
                # Partículas com cor mais clara
                particle_color = (
                    min(255, self.color[0] + 30),
                    min(255, self.color[1] + 30),
                    min(255, self.color[2] + 30)
                )
                alpha = int(255 * (particle['life'] / 0.3))
                pygame.draw.circle(screen, particle_color, (int(particle_x), int(particle_y)), particle_size)

        # ===== 2. DESENHAR TRAIL (MAIS LONGO) =====
        for i, (tx, ty) in enumerate(self.trail):
            trail_x, trail_y = screen_manager.world_to_screen(tx, ty, camera)
            # Tamanho decrescente e mais suave
            progress = i / len(self.trail)
            size = max(1, int(self.size * zoom_scale * (1 - progress) * 0.7))

            if size > 0:
                # Cor do trail com fade out
                fade_factor = progress
                trail_color = (
                    int(self.color[0] * (1 - fade_factor * 0.7)),
                    int(self.color[1] * (1 - fade_factor * 0.7)),
                    int(self.color[2] * (1 - fade_factor * 0.7))
                )
                pygame.draw.circle(screen, trail_color, (int(trail_x), int(trail_y)), size)

        # ===== 3. DESENHAR PROJÉTIL PRINCIPAL =====
        size = max(3, int(self.size * zoom_scale))

        # Efeito de glow (brilho)
        glow_size = size + 2
        glow_color = (
            min(255, self.color[0] + 40),
            min(255, self.color[1] + 40),
            min(255, self.color[2] + 40)
        )
        pygame.draw.circle(screen, glow_color, (int(screen_x), int(screen_y)), glow_size)

        # Projétil principal
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), size)

        # Núcleo brilhante (maior)
        if size > 2:
            inner_size = max(1, size // 2)
            inner_color = (
                min(255, self.color[0] + 80),
                min(255, self.color[1] + 80),
                min(255, self.color[2] + 80)
            )
            pygame.draw.circle(screen, inner_color, (int(screen_x), int(screen_y)), inner_size)

        # ===== 4. EFEITO DE RASTRO DE LUZ =====
        # Desenhar um rastro de luz na direção do movimento
        if hasattr(self, 'vx') and hasattr(self, 'vy'):
            speed_magnitude = math.sqrt(self.vx * self.vx + self.vy * self.vy)
            if speed_magnitude > 0:
                # Direção oposta para o rastro
                trail_dir_x = -self.vx / speed_magnitude
                trail_dir_y = -self.vy / speed_magnitude

                # Desenhar 2-3 "caudas" atrás do projétil
                for offset in [5, 10, 15]:
                    trail_offset = offset * zoom_scale
                    tail_x = screen_x + trail_dir_x * trail_offset
                    tail_y = screen_y + trail_dir_y * trail_offset
                    tail_size = max(1, int(size * 0.6) - offset // 3)
                    if tail_size > 0:
                        tail_color = (
                            int(self.color[0] * 0.7),
                            int(self.color[1] * 0.7),
                            int(self.color[2] * 0.7)
                        )
                        pygame.draw.circle(screen, tail_color, (int(tail_x), int(tail_y)), tail_size)