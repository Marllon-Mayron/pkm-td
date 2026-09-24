# src/scenes/game_scene/components/managers/placement_manager.py
import pygame, random, math

from src.ui.toast_renderer import toast_warning


class PlacementManager:
    """Gerencia os Pokémon colocados no mapa"""

    def __init__(self, game):
        self.game = game
        self.placed_pokemon = []  # Lista de Pokémon no mapa
        self.tile_size = 24
        # ===== NOVO: flag de celebração de vitória =====
        self._victory_celebration_active = False

        # ===== NOVO: Ghosts de teleporte (efeito visual) =====
        self.teleport_ghosts = []  # Lista de dicts com os ghosts ativos

    def _check_combination_evolution_on_placement(self, pokemon, spot):
        """
        Verifica se o Pokémon que está sendo colocado pode evoluir
        em combinação com algum Pokémon já existente no mapa.
        Retorna True se evoluiu, False caso contrário.
        """
        if pokemon.is_wild:
            return False

        tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

        # Verifica TODOS os Pokémon já colocados
        for placed in self.placed_pokemon:
            if placed == pokemon:
                continue
            if not placed.is_alive() or placed.is_defeated:
                continue

            # Calcula distância entre os Pokémon
            dx = abs(placed.x - tile_center_x)
            dy = abs(placed.y - tile_center_y)
            distance = (dx * dx + dy * dy) ** 0.5

            # Se estiverem no mesmo tile ou muito próximos (menos de 30 pixels)
            if distance < 30:
                # Verifica se o novo Pokémon evolui com o existente
                evolution_data = pokemon.evolution.check_combination_evolution(placed)

                # Se não, verifica se o existente evolui com o novo
                if not evolution_data:
                    evolution_data = placed.evolution.check_combination_evolution(pokemon)

                if evolution_data:
                    print(f"[COMBINATION] Evolução detectada entre {pokemon.name} e {placed.name}!")

                    # Determina qual vai evoluir (ambos podem evoluir em casos especiais)
                    if evolution_data["evolve_to"] is not None:
                        # Executa a evolução
                        result = pokemon.evolution.perform_combination_evolution(evolution_data)
                        return True

                    # Se chegou aqui, não houve evolução
                    return False

        return False

    # =========================================================
    # NOVO: EFEITO VISUAL DE TELEPORTE (GHOSTS)
    # =========================================================
    def spawn_teleport_ghost(self, pokemon):
        """
        Cria DOIS ghosts visuais quando o Pokémon teleporta:
        - Um na ORIGEM (onde ele estava) → fade out simulando "saída"
        - Um no DESTINO (spot original) → fade in simulando "materialização"

        O efeito dura ~0.5s. Não interfere em nada no gameplay.
        """
        # Pega o sprite atual do Pokémon (na direção/animação em que está)
        sprite = None
        if hasattr(pokemon, 'sprite') and pokemon.sprite:
            sprite = pokemon.sprite
        elif hasattr(pokemon, 'inmap_frames') and pokemon.inmap_frames:
            # Fallback: pega a primeira frame da direção atual
            direction = getattr(pokemon, 'current_direction', 'down')
            frames = pokemon.inmap_frames.get(direction)
            if frames:
                sprite = frames[0]

        if not sprite:
            return  # Sem sprite disponível, não cria ghost

        # ===== GHOST DA ORIGEM (onde ele estava) =====
        origin_ghost = {
            'x': pokemon.x,
            'y': pokemon.y,
            'sprite': sprite.copy(),
            'alpha': 200,
            'life': 0.45,
            'max_life': 0.45,
            'scale_start': 1.0,
            'scale_end': 1.25,   # cresce um pouco enquanto desaparece
            'current_scale': 1.0,
            'is_destination': False,
        }
        self.teleport_ghosts.append(origin_ghost)

        # ===== GHOST DO DESTINO (spot) =====
        dest_x = getattr(pokemon, 'original_spot_x', pokemon.x)
        dest_y = getattr(pokemon, 'original_spot_y', pokemon.y)

        dest_ghost = {
            'x': dest_x,
            'y': dest_y,
            'sprite': sprite.copy(),
            'alpha': 0,
            'life': 0.5,
            'max_life': 0.5,
            'scale_start': 0.7,  # começa pequeno
            'scale_end': 1.0,    # cresce até o tamanho normal
            'current_scale': 0.7,
            'is_destination': True,
        }
        self.teleport_ghosts.append(dest_ghost)

        print(f"[TELEPORT_GHOST] Ghosts criados para {pokemon.name}")

    def update_ghosts(self, dt):
        """Atualiza os ghosts de teleporte (fade in/out + escala)."""
        for ghost in self.teleport_ghosts[:]:
            ghost['life'] -= dt

            if ghost['life'] <= 0:
                self.teleport_ghosts.remove(ghost)
                continue

            # progress: 1.0 (recém-criado) → 0.0 (expirando)
            progress = ghost['life'] / ghost['max_life']

            # Escala interpolada
            scale_range = ghost['scale_end'] - ghost['scale_start']
            ghost['current_scale'] = ghost['scale_end'] - scale_range * progress

            # ===== ALPHA =====
            if ghost['is_destination']:
                # Destino: FADE IN (0 → 220) e depois FADE OUT
                # Nos primeiros 30% da vida: fade in
                # Depois: fade out
                if progress > 0.7:
                    # Ainda subindo (fase de materialização)
                    t = (1.0 - progress) / 0.3  # 0 -> 1
                    ghost['alpha'] = int(220 * t)
                else:
                    # Fade out
                    t = progress / 0.7  # 1 -> 0
                    ghost['alpha'] = int(220 * t)
            else:
                # Origem: só fade out
                ghost['alpha'] = int(200 * progress)

    def render_ghosts(self, screen, camera):
        """Renderiza os ghosts de teleporte (chamado ANTES dos Pokémons)."""
        if not self.teleport_ghosts:
            return

        # Obtém screen_manager para conversão de coordenadas
        sm = getattr(self.game, 'screen_manager', None)

        for ghost in self.teleport_ghosts:
            sprite = ghost['sprite']
            if not sprite:
                continue

            # ===== CONVERTE PARA COORDENADAS DE TELA =====
            if camera and sm:
                screen_x, screen_y = sm.world_to_screen(ghost['x'], ghost['y'], camera)
                zoom_scale = camera.zoom * sm.render_scale
            else:
                screen_x, screen_y = ghost['x'], ghost['y']
                zoom_scale = 1.0

            # ===== APLICA ESCALA =====
            scale = ghost.get('current_scale', 1.0)
            w = max(1, int(sprite.get_width() * zoom_scale * scale))
            h = max(1, int(sprite.get_height() * zoom_scale * scale))

            if w <= 0 or h <= 0:
                continue

            scaled = pygame.transform.scale(sprite, (w, h))

            # ===== TINT AZUL (fica "fantasmagórico") =====
            # Cria uma cópia colorida por cima com blend aditivo suave
            tinted = scaled.copy()
            tint_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            # Cor azul-clara (ciano) com alpha baixo
            if ghost['is_destination']:
                tint_color = (120, 200, 255, 70)  # ciano claro
            else:
                tint_color = (180, 140, 255, 60)  # lilás (saída)
            tint_surface.fill(tint_color)
            tinted.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # ===== APLICA ALPHA =====
            alpha = max(0, min(255, ghost['alpha']))
            tinted.set_alpha(alpha)

            # ===== DESENHA =====
            rect = tinted.get_rect()
            rect.center = (int(screen_x), int(screen_y))
            screen.blit(tinted, rect)

    # =========================================================
    # FIM NOVO
    # =========================================================

    def add_pokemon(self, spot, pokemon):
        """Adiciona um Pokémon no spot"""
        # Verificações básicas
        existing = self.get_pokemon_at_spot(spot)
        if existing:
            print(f"[PLACEMENT] Spot já ocupado por {existing.name}")
            return None

        if spot.occupied:
            print(f"[PLACEMENT] Spot já marcado como ocupado")
            return None

        if hasattr(pokemon, 'is_placed') and pokemon.is_placed:
            print(f"[PLACEMENT] {pokemon.name} já está no mapa!")
            return None

        # ===== VERIFICA EVOLUÇÃO POR COMBINAÇÃO ANTES DE COLOCAR =====
        if self._check_combination_evolution_on_placement(pokemon, spot):
            # Se evoluiu, o Pokémon original foi transformado/removido
            # Não adiciona o Pokémon original ao spot (pois ele já evoluiu)
            print(f"[COMBINATION] {pokemon.name} evoluiu durante o placement!")

            # Procura o Pokémon evoluído (agora está no placed_pokemon)
            for placed in self.placed_pokemon:
                if placed.id == pokemon.id and placed != pokemon:
                    # Atualiza a posição do Pokémon evoluído para o spot correto
                    tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
                    tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2
                    placed.x = tile_center_x
                    placed.y = tile_center_y
                    placed.original_spot_x = tile_center_x
                    placed.original_spot_y = tile_center_y
                    placed.placed_tile_x = tile_center_x // self.tile_size
                    placed.placed_tile_y = tile_center_y // self.tile_size
                    placed.is_placed = True
                    spot.occupied = True
                    return placed

            return None

        # Se não evoluiu, coloca normalmente
        return self._add_pokemon_to_spot(spot, pokemon)

    def _add_pokemon_to_spot(self, spot, pokemon):
        """Adiciona o Pokémon ao spot (lógica interna)"""
        tile_size = self.tile_size

        # Calcula o centro do tile
        tile_center_x = (spot.x // tile_size) * tile_size + tile_size // 2
        tile_center_y = (spot.y // tile_size) * tile_size + tile_size // 2

        pokemon.x = tile_center_x
        pokemon.y = tile_center_y
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.screen_manager = self.game.screen_manager

        pokemon.is_placed = True
        pokemon.placed_tile_x = tile_center_x // tile_size
        pokemon.placed_tile_y = tile_center_y // tile_size
        pokemon.combat_state = "idle"
        pokemon.game_scene = self.game

        spot.occupied = True
        self.placed_pokemon.append(pokemon)

        if hasattr(self.game, 'battle_system'):
            pokemon.set_battle_system(self.game.battle_system)

        print(f"[PLACEMENT] {pokemon.name} colocado no spot ({spot.x}, {spot.y})")
        return pokemon

    def get_pokemon_at_world_pos(self, world_x, world_y, tolerance=20):
        """Retorna o Pokémon na posição do mundo (para seleção)"""
        tolerance_sq = tolerance * tolerance
        for pokemon in self.placed_pokemon:
            dx = pokemon.x - world_x
            dy = pokemon.y - world_y
            if dx * dx + dy * dy < tolerance_sq:
                return pokemon
        return None

    # =========================================================
    # NOVO: CELEBRAÇÃO DE VITÓRIA
    # =========================================================
    def start_victory_celebration(self):
        """
        Inicia a animação de comemoração (hop) para todos os Pokémon vivos
        que estão colocados no mapa e possuem a animação 'hop'.
        Cada Pokémon começa com um pequeno delay aleatório para não pular tudo junto.
        """
        if self._victory_celebration_active:
            print("[VICTORY] Celebração já está ativa, ignorando chamada duplicada.")
            return

        self._victory_celebration_active = True
        celebrating_count = 0

        for pokemon in self.placed_pokemon:
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            # Delay aleatório entre 0.0 e 1.2 segundos
            delay = random.uniform(0.0, 1.2)

            if pokemon.celebrate_victory(delay=delay):
                celebrating_count += 1

        if celebrating_count > 0:
            print(f"[VICTORY] {celebrating_count} Pokémon vão comemorar (com delay escalonado)!")
        else:
            print("[VICTORY] Nenhum Pokémon possui a animação 'hop' disponível.")

    def stop_victory_celebration(self):
        """Para a animação de comemoração de todos os Pokémon."""
        if not self._victory_celebration_active:
            return

        self._victory_celebration_active = False

        for pokemon in self.placed_pokemon:
            pokemon.stop_celebrating()

        print("[VICTORY] Celebração encerrada.")

    def is_celebrating(self) -> bool:
        """Retorna True se a celebração de vitória está ativa."""
        return self._victory_celebration_active

    def update_animations_only(self, dt):
        """
        Atualiza APENAS as animações dos Pokémon, sem lógica de combate.
        Usado quando o gameplay está pausado mas queremos animações (ex: vitória).
        """
        for pokemon in self.placed_pokemon:
            pokemon.update(dt, enemies=None)

    # =========================================================
    # FIM NOVO
    # =========================================================

    def remove_pokemon_by_right_click(self, world_x, world_y, tolerance=20):
        """Remove o Pokémon na posição do mundo (para clique direito)"""
        if (hasattr(self.game, 'chapter_id') and hasattr(self.game, 'phase_number') and
                self.game.chapter_id == 1 and self.game.phase_number == 1):
            from src.ui.toast_renderer import toast_warning
            toast_warning("Não é possível remover Pokémon durante o tutorial, siga as etapas informadas!", duration=3.0)
            return False

        pokemon = self.get_pokemon_at_world_pos(world_x, world_y, tolerance)

        if pokemon:
            print(f"[PLACEMENT] Recolhendo {pokemon.name} com clique direito")

            # Remove da lista de colocados
            if pokemon in self.placed_pokemon:
                self.placed_pokemon.remove(pokemon)

                # ===== CORREÇÃO: DESOCUPA O SPOT USANDO COORDENADAS DE TILE =====
                # Usa as coordenadas de tile armazenadas no Pokémon
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y

                # Procura e desocupa o spot correspondente
                spot_found = False
                for spot in self.game.spot_renderer.get_spots():
                    spot_tile_x = spot.x // self.tile_size
                    spot_tile_y = spot.y // self.tile_size

                    if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                        spot.occupied = False
                        spot_found = True
                        print(f"[PLACEMENT] Spot ({spot.x}, {spot.y}) desocupado")
                        break

                if not spot_found:
                    print(f"[PLACEMENT] ERRO: Spot não encontrado para tile ({pokemon_tile_x}, {pokemon_tile_y})")

                # Marca o Pokémon como não colocado (é o mesmo objeto do time!)
                pokemon.is_placed = False

                return pokemon

        return None

    def get_free_spots(self):
        """Retorna lista de spots livres"""
        spots = self.game.spot_renderer.get_spots()
        return [spot for spot in spots if not spot.occupied]

    def get_ally_at_spot(self, spot):
        """Retorna o aliado em um spot específico"""
        spot_tile_x = spot.x // self.tile_size
        spot_tile_y = spot.y // self.tile_size

        for pokemon in self.placed_pokemon:
            if hasattr(pokemon, 'placed_tile_x'):
                if pokemon.placed_tile_x == spot_tile_x and pokemon.placed_tile_y == spot_tile_y:
                    return pokemon
        return None

    def get_pokemon_at_spot(self, spot):
        """Verifica se já existe um Pokémon no spot baseado no tile"""
        # Converte spot para coordenadas de tile
        spot_tile_x = spot.x // self.tile_size
        spot_tile_y = spot.y // self.tile_size

        for pokemon in self.placed_pokemon:
            # Usa as coordenadas armazenadas ou calcula
            if hasattr(pokemon, 'placed_tile_x'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            if pokemon_tile_x == spot_tile_x and pokemon_tile_y == spot_tile_y:
                return pokemon
        return None

    def update(self, dt, enemies):
        """Atualiza todos os Pokémon colocados"""
        # ===== NOVO: Atualiza ghosts de teleporte (sempre, em qualquer modo) =====
        self.update_ghosts(dt)

        # ===== MODO CELEBRAÇÃO: Pokémon terminam ações pendentes mas não engajam novas =====
        if self._victory_celebration_active:
            for pokemon in self.placed_pokemon:
                # Atualiza animação e lógica básica (sempre)
                pokemon.update(dt, enemies=None)

                # Permite que Pokémon terminem ações pendentes (retorno/ataque em andamento)
                # mas NÃO inicia novas buscas de alvo
                if pokemon.is_alive():
                    # Se está retornando ao spot, continua
                    if getattr(pokemon, 'combat_state', None) == "returning":
                        pokemon.update_combat(dt, [])  # sem inimigos, só termina o retorno
                    # Se está no meio de um ataque (animação ativa), continua
                    elif hasattr(pokemon, '_attack_animation_active') and pokemon._attack_animation_active:
                        # A animação de ataque está sendo processada dentro de animation.update
                        # (mas o hop tem prioridade 0, então na verdade ele já foi interrompido)
                        pass
            return

        # ===== MODO NORMAL =====
        for pokemon in self.placed_pokemon:
            pokemon.update(dt, enemies=enemies)
            if pokemon.is_alive():
                pokemon.update_combat(dt, enemies)

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa """
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)

            # ===== CORREÇÃO: LIBERA O SPOT USANDO COORDENADAS DE TILE =====
            # Usa as coordenadas de tile armazenadas
            if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                # Fallback: calcula da posição atual
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            spot_found = False
            for spot in self.game.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                    spot.occupied = False
                    spot_found = True
                    print(f"[COMBATE] Spot ({spot.x}, {spot.y}) liberado")
                    break

            if not spot_found:
                print(f"[COMBATE] ERRO: Spot não encontrado para tile ({pokemon_tile_x}, {pokemon_tile_y})")

            # Marca como não colocado (é o mesmo objeto do time!)
            pokemon.is_placed = False

    def clear(self):
        """Remove todos os Pokémon do mapa"""
        # Para celebração se estiver ativa
        if self._victory_celebration_active:
            self.stop_victory_celebration()

        for pokemon in self.placed_pokemon:
            # Libera os spots usando coordenadas de tile
            if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            for spot in self.game.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                    spot.occupied = False
                    break

            # Reseta is_placed no time
            for team_pokemon in self.game.player.team:
                if (team_pokemon.id == pokemon.id and
                        team_pokemon.level == pokemon.level):
                    team_pokemon.is_placed = False
                    break

        self.placed_pokemon.clear()

        # ===== NOVO: Limpa ghosts de teleporte pendentes =====
        self.teleport_ghosts.clear()

    def render_hp(self, screen, camera):
        """Renderiza as barras de HP de todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            # Agora usamos o método interno _render_hp_bar
            # Mas precisamos passar os parâmetros corretos
            if camera and hasattr(pokemon, 'screen_manager') and pokemon.screen_manager:
                screen_x, screen_y = pokemon.screen_manager.world_to_screen(pokemon.x, pokemon.y, camera)
                zoom_scale = camera.zoom * pokemon.screen_manager.render_scale

                # Calcula o sprite_rect para posicionar a barra
                sprite_to_render = pokemon._prepare_sprite(zoom_scale)
                if sprite_to_render:
                    current_width, current_height = sprite_to_render.get_width(), sprite_to_render.get_height()
                    final_width = max(1, int(current_width * zoom_scale))
                    final_height = max(1, int(current_height * zoom_scale))

                    if final_width != current_width or final_height != current_height:
                        scaled_sprite = pygame.transform.scale(sprite_to_render, (final_width, final_height))
                    else:
                        scaled_sprite = sprite_to_render

                    sprite_rect = scaled_sprite.get_rect()
                    sprite_rect.center = (int(screen_x), int(screen_y))

                    # Renderiza a barra de HP
                    pokemon._render_hp_bar(screen, sprite_rect, zoom_scale)

    def render_astral_bodies(self, screen, camera):
        """
        Desenha um 'corpo astral' (ghost fixo) no spot de cada Pokémon
        que saiu para atacar/andar.

        Simboliza que o corpo físico ficou no spot enquanto a 'alma' viaja.
        Some automaticamente quando o Pokémon retorna ao spot (teleporte).
        """
        if not self.placed_pokemon:
            return

        sm = getattr(self.game, 'screen_manager', None)
        if sm is None:
            return

        # ===== PULSAÇÃO GLOBAL (respiração etérea) =====
        # Frequência baixa (~0.3 Hz) para parecer "respirando" lentamente
        t = pygame.time.get_ticks() / 1000.0
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)  # 0..1

        for pokemon in self.placed_pokemon:
            # Pula mortos / derrotados
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            # Pula se não tem spot original
            spot_x = getattr(pokemon, 'original_spot_x', None)
            spot_y = getattr(pokemon, 'original_spot_y', None)
            if spot_x is None or spot_y is None:
                continue

            # ===== SÓ DESENHA SE ESTIVER FORA DO SPOT =====
            dx = pokemon.x - spot_x
            dy = pokemon.y - spot_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < 25:  # ~5px de tolerância — está no spot, não desenha
                continue

            # ===== PEGA O SPRITE ATUAL =====
            sprite = None
            if hasattr(pokemon, 'sprite') and pokemon.sprite:
                sprite = pokemon.sprite
            elif hasattr(pokemon, 'inmap_frames') and pokemon.inmap_frames:
                direction = getattr(pokemon, 'current_direction', 'down')
                frames = pokemon.inmap_frames.get(direction)
                if frames:
                    sprite = frames[0]

            if not sprite:
                continue

            # ===== CONVERSÃO PARA COORDENADAS DE TELA =====
            screen_x, screen_y = sm.world_to_screen(spot_x, spot_y, camera)
            zoom_scale = camera.zoom * sm.render_scale

            w = max(1, int(sprite.get_width() * zoom_scale))
            h = max(1, int(sprite.get_height() * zoom_scale))

            if w <= 0 or h <= 0:
                continue

            scaled = pygame.transform.scale(sprite, (w, h))

            # ===== TINT AZUL-ETÉREO =====
            # Blend aditivo suave com azul claro (dá ar de "alma/corpo astral")
            tinted = scaled.copy()
            tint_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            tint_surface.fill((90, 150, 230, 100))
            tinted.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # ===== ALPHA PULSANTE =====
            # Base 70 + oscilação até 130 → fica "respirando" sem piscar demais
            alpha = int(70 + 60 * pulse)
            tinted.set_alpha(alpha)

            # ===== DESENHA =====
            rect = tinted.get_rect()
            rect.center = (int(screen_x), int(screen_y))
            screen.blit(tinted, rect)

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os Pokémon colocados"""
        # 1. Ghosts de teleporte (efeito pontual de fade — 0.5s)
        self.render_ghosts(screen, camera)

        # 2. Corpos astrais (ghost fixo no spot enquanto o Pokémon está fora)
        self.render_astral_bodies(screen, camera)

        # 3. Pokémons reais (por cima de tudo)
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, camera, show_hp=False)