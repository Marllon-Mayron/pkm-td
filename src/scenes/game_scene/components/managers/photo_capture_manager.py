# src/scenes/game_scene/components/managers/photo_capture_manager.py
"""
Gerencia a captura de fotos do jogo.
- Captura apenas o mundo (pokémons + cenário + clima + dia/noite)
- SEM UI
- Salva em res/PokemonSprites/screenshots/player_screenshots/
"""
import pygame
import os
from datetime import datetime
from pathlib import Path

from src.config.paths import SPRITES_PATH


class PhotoCaptureManager:
    """Captura screenshots limpas (sem UI) da cena do jogo."""

    def __init__(self, game_scene):
        self.game_scene = game_scene

        # Pasta de destino
        self.output_dir = SPRITES_PATH / "screenshots" / "player_screenshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configurações da área de captura
        # Valores em fração da viewport (0.0 a 1.0)
        self.capture_area = {
            "x": 0.25,        # 25% da largura
            "y": 0.25,        # 25% da altura
            "width": 0.50,    # 50% da largura (metade da tela = padrão)
            "height": 0.50,   # 50% da altura
        }

        # Cooldown para evitar spam
        self._last_capture_time = 0.0
        self._capture_cooldown = 0.3  # segundos

        print(f"[PHOTO] Pasta de destino: {self.output_dir}")

    # ------------------------------------------------------------------
    # CONFIGURAÇÃO DA ÁREA
    # ------------------------------------------------------------------
    def set_capture_area(self, x: float, y: float, width: float, height: float):
        """Define a área de captura (frações 0.0-1.0 da viewport)."""
        # Clamp para garantir que a área fique dentro da viewport
        width = max(0.1, min(1.0, width))
        height = max(0.1, min(1.0, height))
        x = max(0.0, min(1.0 - width, x))
        y = max(0.0, min(1.0 - height, y))

        self.capture_area = {
            "x": x, "y": y, "width": width, "height": height
        }

    def resize_capture_area(self, delta: float):
        """Aumenta/diminui a área mantendo o centro."""
        area = self.capture_area
        center_x = area["x"] + area["width"] / 2
        center_y = area["y"] + area["height"] / 2

        new_w = max(0.1, min(1.0, area["width"] + delta))
        new_h = max(0.1, min(1.0, area["height"] + delta))

        new_x = max(0.0, min(1.0 - new_w, center_x - new_w / 2))
        new_y = max(0.0, min(1.0 - new_h, center_y - new_h / 2))

        self.capture_area = {
            "x": new_x, "y": new_y, "width": new_w, "height": new_h
        }

    def get_capture_rect_screen(self) -> pygame.Rect:
        """Retorna o rect da área de captura em coordenadas de tela."""
        sm = self.game_scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        a = self.capture_area
        return pygame.Rect(
            int(vx + a["x"] * vw),
            int(vy + a["y"] * vh),
            int(a["width"] * vw),
            int(a["height"] * vh),
        )

    # ------------------------------------------------------------------
    # CAPTURA
    # ------------------------------------------------------------------
    def capture(self) -> str | None:
        """
        Captura a área definida SEM UI.
        Retorna o caminho do arquivo salvo, ou None se falhar.
        """
        now = pygame.time.get_ticks() / 1000.0
        if now - self._last_capture_time < self._capture_cooldown:
            print("[PHOTO] Cooldown ativo, aguarde...")
            return None
        self._last_capture_time = now

        screen = pygame.display.get_surface()
        if screen is None:
            print("[PHOTO] ERRO: display não inicializado")
            return None

        capture_rect = self.get_capture_rect_screen()

        # Cria superfície limpa (sem UI)
        clean_surface = pygame.Surface(
            (capture_rect.width, capture_rect.height), pygame.SRCALPHA
        )
        clean_surface.fill((0, 0, 0, 255))

        # ============================================================
        # RENDERIZA APENAS O MUNDO (sem UI)
        # ============================================================
        try:
            self._render_world_only(clean_surface, capture_rect)
        except Exception as e:
            print(f"[PHOTO] Erro ao renderizar mundo: {e}")
            import traceback
            traceback.print_exc()
            return None

        # Salva o arquivo
        return self._save_surface(clean_surface)

    def _render_world_only(self, target_surface: pygame.Surface, capture_rect: pygame.Rect):
        """
        Renderiza APENAS os elementos do mundo no target_surface:
        - Mapa
        - Target items (chão)
        - Inimigos (SEM nome, SEM HP bar)
        - Pokémons colocados (SEM nome, SEM HP bar)
        - Projéteis
        - Target items (pokémon)
        - Efeitos de status (visuais)
        - Filtros de clima e dia/noite

        NÃO renderiza:
        - Spots de torre
        - Nome do pokémon (wild text)
        - Barras de HP
        - UI do jogo (painel de fase)
        - Team manager
        - Item bag
        - Drag manager
        - Notifications
        - Overlays
        - Debug info
        """
        gs = self.game_scene
        camera = gs.camera
        sm = gs.screen_manager

        # ===== TRUQUE: renderizar em uma superfície full-screen temporária =====
        # e depois recortar a área desejada. Isso garante que as transformações
        # de câmera e filtros (que dependem de coordenadas absolutas) funcionem.
        full_surface = pygame.Surface(
            (sm.viewport_width, sm.viewport_height), pygame.SRCALPHA
        )
        full_surface.fill((0, 0, 0, 0))

        # Converte o capture_rect para coordenadas relativas à viewport
        local_rect = pygame.Rect(
            capture_rect.x - sm.viewport_x,
            capture_rect.y - sm.viewport_y,
            capture_rect.width,
            capture_rect.height,
        )

        # ---- Mapa ----
        gs.map_renderer.render(full_surface, camera, sm)

        # ---- Target items (chão) ----
        gs.target_item_manager.render_in_ground(full_surface, camera)

        # ---- Inimigos (SEM nome, SEM HP bar) ----
        for enemy in gs.wave_manager.active_enemies:
            # show_hp=False para não desenhar a barra de vida
            # _render_wild_text é chamado dentro de enemy.render() apenas se show_debug
            # ou se chamado explicitamente. Para garantir que o nome NÃO apareça,
            # vamos renderizar apenas o sprite via _prepare_sprite + _render_sprite.
            self._render_pokemon_sprite_only(full_surface, enemy, camera, sm)

        # ---- Pokémons colocados (SEM nome, SEM HP bar) ----
        if gs.placement_manager:
            for pokemon in gs.placement_manager.placed_pokemon:
                self._render_pokemon_sprite_only(full_surface, pokemon, camera, sm)

        # ---- Projéteis ----
        if hasattr(gs, 'battle_system'):
            gs.battle_system.render_projectiles(full_surface, camera, sm)

        # ---- Target items (nos pokémons) ----
        gs.target_item_manager.render_in_pokemon(full_surface, camera)

        # ---- Filtros de clima e dia/noite ----
        viewport_rect_local = pygame.Rect(
            0, 0, sm.viewport_width, sm.viewport_height
        )

        if hasattr(gs, 'battle_system') and gs.battle_system:
            weather = gs.battle_system.weather_manager.current_weather
            if weather and weather.active:
                gs.weather_filter.render(
                    full_surface, weather, viewport_rect_local,
                    dt=getattr(gs, '_last_dt', 0.0),
                )
            else:
                # Garante que o sistema de partículas é parado quando o clima acaba
                gs.weather_filter.render(
                    full_surface, None, viewport_rect_local,
                    dt=getattr(gs, '_last_dt', 0.0),
                )

        if hasattr(gs, 'day_night_weather'):
            day_night = gs.day_night_weather.day_night_state
            if day_night and day_night.active:
                gs.day_night_filter.render(full_surface, day_night, viewport_rect_local)

        # ---- Recorta a área desejada para o target_surface ----
        try:
            cropped = full_surface.subsurface(local_rect).copy()
            target_surface.blit(cropped, (0, 0))
        except ValueError:
            # Fallback: preenche com preto
            target_surface.fill((0, 0, 0))

    def _render_pokemon_sprite_only(self, surface, pokemon, camera, screen_manager):
        """
        Renderiza APENAS o sprite do pokémon (sem nome, sem HP bar),
        mas MANTÉM os efeitos de status visuais (textos flutuantes,
        modificadores de stat, indicadores de status).
        """
        # Salva a referência da câmera (alguns métodos internos usam self.camera)
        pokemon.camera = camera

        # Calcula posição na tela
        if camera and hasattr(pokemon, 'screen_manager') and pokemon.screen_manager:
            screen_x, screen_y = screen_manager.world_to_screen(pokemon.x, pokemon.y, camera)
            zoom_scale = camera.zoom * screen_manager.render_scale
        else:
            screen_x = pokemon.x
            screen_y = pokemon.y
            zoom_scale = 1.0

        # Prepara e renderiza o sprite
        sprite_to_render = pokemon._prepare_sprite(zoom_scale)
        sprite_rect = None

        if sprite_to_render:
            sprite_rect = pokemon._render_sprite(
                surface, sprite_to_render, screen_x, screen_y, zoom_scale
            )
        else:
            sprite_rect = pokemon._render_placeholder(
                surface, screen_x, screen_y, zoom_scale
            )

        # ===== EFEITOS DE STATUS (MANTIDOS NA FOTO) =====
        if (hasattr(pokemon, 'battle_system') and pokemon.battle_system
                and pokemon.battle_system.effect_manager
                and sprite_rect):
            from src.entities.pokemon.pokemon import _FONT_CACHE

            pokemon.battle_system.effect_manager.render_status_texts(
                surface, pokemon, sprite_rect, zoom_scale, _FONT_CACHE
            )
            pokemon.battle_system.effect_manager.render_stat_modifiers(
                surface, pokemon, sprite_rect, zoom_scale, _FONT_CACHE
            )
            pokemon.battle_system.effect_manager.render_status_indicators(
                surface, pokemon, sprite_rect, zoom_scale, _FONT_CACHE
            )

        # NÃO renderiza:
        # - pokemon._render_wild_text()      ← nome + nível do selvagem
        # - pokemon._render_hp_bar()          ← barra de vida
        # - pokemon._render_miss_text()       ← texto de MISS
        # - pokemon._render_debug()           ← informações de debug

    # ------------------------------------------------------------------
    # SALVAMENTO
    # ------------------------------------------------------------------
    def _save_surface(self, surface: pygame.Surface) -> str | None:
        """Salva a superfície como PNG com timestamp."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"photo_{timestamp}.png"
            filepath = self.output_dir / filename

            pygame.image.save(surface, str(filepath))
            print(f"[PHOTO] ✅ Foto salva: {filepath}")
            return str(filepath)

        except Exception as e:
            print(f"[PHOTO] ❌ Erro ao salvar: {e}")
            return None

    def get_last_photo_path(self) -> str | None:
        """Retorna o caminho da última foto salva (útil para preview)."""
        try:
            files = sorted(
                self.output_dir.glob("photo_*.png"),
                key=os.path.getmtime,
                reverse=True,
            )
            return str(files[0]) if files else None
        except Exception:
            return None