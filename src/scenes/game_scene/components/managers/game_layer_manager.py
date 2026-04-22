# src/scenes/game_scene/components/renderer/game_layer_manager.py

"""
Gerenciador de camadas para o jogo - Suporte a múltiplos tilesets e tile_size 24
COM CACHE DE SUPERFÍCIE PARA ELIMINAR GAPS
"""
import pygame
import os
from src.core.render_context import render_context


class GameLayer:
    """Camada do mapa para o jogo - COM CACHE OTIMIZADO"""

    def __init__(self, name, layer_type, width, height, tile_size=24):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.visible = True
        self.opacity = 255
        self.tileset = []
        self.tilesets = []
        self.tileset_paths = []
        self._cached_tiles = {}

        # ===== NOVOS CACHES =====
        self._cached_surface = None
        self._cached_scale = None
        self._cached_zoom = None
        self._cached_visible_section = None
        self._last_camera_rect = None
        self._last_screen_pos = None
        self._frame_counter = 0
        self._recreate_counter = 0

    def _invalidate_surface_cache(self):
        """Invalida o cache quando algo muda"""
        self._cached_surface = None
        self._cached_scale = None
        self._cached_zoom = None
        self._cached_visible_section = None
        self._last_camera_rect = None
        self._last_screen_pos = None
        self._recreate_counter += 1

    def set_tile(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = int(tile_id)
            # Quando um tile muda, invalida o cache
            self._invalidate_surface_cache()
            return True
        return False

    def load_tileset_6x8(self, image_path, tile_width, tile_height):
        """
        Carrega um tileset organizado em 6 colunas x 8 linhas
        Retorna lista de tiles e número de tilesets detectados
        """
        try:
            print(f"\n--- GameLayer load_tileset_6x8 ---")
            print(f"Tentando carregar: {image_path}")

            if not os.path.exists(image_path):
                print(f"ERRO: Arquivo não encontrado!")
                return None, 0

            sheet = pygame.image.load(image_path).convert_alpha()
            img_width = sheet.get_width()
            img_height = sheet.get_height()

            COLS_PER_SET = 6
            ROWS_PER_SET = 8
            tileset_width = COLS_PER_SET * tile_width

            num_tilesets = img_width // tileset_width
            print(f"Imagem: {img_width}x{img_height}, tilesets detectados: {num_tilesets}")

            all_tiles = []

            for ts_idx in range(num_tilesets):
                offset_x = ts_idx * tileset_width
                print(f"  Processando tileset {ts_idx + 1}/{num_tilesets}, offset X: {offset_x}")

                for row in range(ROWS_PER_SET):
                    for col in range(COLS_PER_SET):
                        rect = pygame.Rect(
                            offset_x + col * tile_width,
                            row * tile_height,
                            tile_width,
                            tile_height
                        )
                        if rect.right <= img_width and rect.bottom <= img_height:
                            tile = sheet.subsurface(rect)
                            all_tiles.append(tile)
                        else:
                            empty_tile = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)
                            empty_tile.fill((0, 0, 0, 0))
                            all_tiles.append(empty_tile)

            print(f"Total de tiles carregados: {len(all_tiles)}")
            return all_tiles, num_tilesets

        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
            import traceback
            traceback.print_exc()
            return None, 0

    def load_tileset(self, image_path, tile_width, tile_height):
        """Carrega um tileset (primeiro da layer)"""
        all_tiles, num_tilesets = self.load_tileset_6x8(image_path, tile_width, tile_height)

        if all_tiles is None:
            return False

        self.tileset = all_tiles
        self.tilesets = []
        self.tileset_paths = []
        self._invalidate_surface_cache()

        # Cria informações para cada tileset
        current_start = 0
        for ts_idx in range(num_tilesets):
            ts_count = 48  # 6x8 = 48 tiles
            tileset_info = {
                'path': image_path,
                'tiles': all_tiles[current_start:current_start + ts_count],
                'start_id': current_start + 1,
                'count': ts_count,
                'cols': 6,
                'rows': 8,
                'tileset_index': ts_idx
            }
            self.tilesets.append(tileset_info)
            current_start += ts_count

        # Adiciona caminho
        if os.path.isabs(image_path):
            try:
                from src.config.paths import PROJECT_ROOT
                relative_path = os.path.relpath(image_path, PROJECT_ROOT)
                self.tileset_paths.append(relative_path.replace('\\', '/'))
            except:
                self.tileset_paths.append(os.path.basename(image_path))
        else:
            self.tileset_paths.append(image_path)

        print(f"✓ Tileset carregado: {num_tilesets} tilesets, {len(self.tileset)} tiles")
        return True

    def add_tileset(self, image_path, tile_width, tile_height):
        """Adiciona um tileset adicional à layer"""
        all_tiles, num_tilesets = self.load_tileset_6x8(image_path, tile_width, tile_height)

        if all_tiles is None:
            return False

        # Adiciona os novos tiles
        current_start = len(self.tileset)
        self.tileset.extend(all_tiles)
        self._invalidate_surface_cache()

        # Adiciona informações de cada tileset
        for ts_idx in range(num_tilesets):
            ts_count = 48
            tileset_info = {
                'path': image_path,
                'tiles': all_tiles[ts_idx * ts_count:(ts_idx + 1) * ts_count],
                'start_id': current_start + 1,
                'count': ts_count,
                'cols': 6,
                'rows': 8,
                'tileset_index': len(self.tilesets) + ts_idx
            }
            self.tilesets.append(tileset_info)
            current_start += ts_count

        # Adiciona caminho
        if os.path.isabs(image_path):
            try:
                from src.config.paths import PROJECT_ROOT
                relative_path = os.path.relpath(image_path, PROJECT_ROOT)
                rel_path = relative_path.replace('\\', '/')
                if rel_path not in self.tileset_paths:
                    self.tileset_paths.append(rel_path)
            except:
                if image_path not in self.tileset_paths:
                    self.tileset_paths.append(os.path.basename(image_path))
        else:
            if image_path not in self.tileset_paths:
                self.tileset_paths.append(image_path)

        print(f"✓ Tileset adicionado: +{num_tilesets} tilesets, total {len(self.tileset)} tiles")
        return True

    def get_tile_image(self, tile_id):
        """Retorna a imagem do tile pelo ID (1-based)"""
        try:
            tile_index = int(tile_id) - 1
            if 0 <= tile_index < len(self.tileset):
                return self.tileset[tile_index]
            return None
        except (ValueError, TypeError):
            return None

    def _get_scaled_tile(self, tile_index, target_size):
        """Obtém tile escalado do cache - OTIMIZADO"""
        cache_key = (tile_index, target_size)
        if cache_key not in self._cached_tiles:
            original = self.tileset[tile_index]
            # Usa smoothscale para melhor qualidade, mas é mais lento
            # Para performance, use scale() em vez de smoothscale()
            scaled = pygame.transform.scale(original, (target_size, target_size))

            # Limita o tamanho do cache para não crescer infinitamente
            if len(self._cached_tiles) > 1000:
                # Remove metade do cache quando fica muito grande
                keys_to_remove = list(self._cached_tiles.keys())[:500]
                for key in keys_to_remove:
                    del self._cached_tiles[key]

            self._cached_tiles[cache_key] = scaled
        return self._cached_tiles[cache_key]

    def _render_to_surface(self, scale):
        """
        Renderiza toda a camada em uma única superfície - OTIMIZADO
        """
        tile_size_scaled = max(1, int(self.tile_size * scale))

        # Calcula o tamanho total da superfície
        total_width = self.width * tile_size_scaled
        total_height = self.height * tile_size_scaled

        # ===== OTIMIZAÇÃO: Cria superfície diretamente =====
        # Usa SRCALPHA só se necessário (camadas com transparência)
        if self.layer_type in ["decoration", "ceiling"]:
            surface = pygame.Surface((total_width, total_height), pygame.SRCALPHA)
        else:
            # Ground layer não precisa de alpha, é mais rápido
            surface = pygame.Surface((total_width, total_height))

        # ===== OTIMIZAÇÃO: Pré-aloca lista de tiles a renderizar =====
        tiles_to_render = []

        for y in range(self.height):
            for x in range(self.width):
                tile_id = self.tiles[y][x]
                if tile_id == 0:
                    continue

                try:
                    tile_index = int(tile_id) - 1
                except (ValueError, TypeError):
                    continue

                if 0 <= tile_index < len(self.tileset):
                    surface_x = x * tile_size_scaled
                    surface_y = y * tile_size_scaled
                    tiles_to_render.append((tile_index, surface_x, surface_y))

        # ===== OTIMIZAÇÃO: Renderiza em batch =====
        for tile_index, surface_x, surface_y in tiles_to_render:
            tile_img = self._get_scaled_tile(tile_index, tile_size_scaled)
            surface.blit(tile_img, (surface_x, surface_y))

        return surface

    def _get_or_create_cached_surface(self, camera, screen_manager):
        """
        Retorna a superfície cacheada para o zoom atual
        Recria se o zoom ou escala mudaram
        """
        current_scale = render_context.get_scale(camera, screen_manager)
        current_zoom = camera.zoom if camera else 1.0

        # Se a escala ou zoom mudaram, recria o cache
        if (self._cached_surface is None or
                self._cached_scale != current_scale or
                self._cached_zoom != current_zoom):
            self._cached_surface = self._render_to_surface(current_scale)
            self._cached_scale = current_scale
            self._cached_zoom = current_zoom

        return self._cached_surface

    def render(self, screen, camera, screen_manager):
        """Renderiza a camada usando superfície cacheada - OTIMIZADO"""
        if not self.visible or not self.tileset:
            return

        # Obtém a escala atual
        current_scale = render_context.get_scale(camera, screen_manager)
        current_zoom = camera.zoom if camera else 1.0

        # ===== CACHE DA SUPERFÍCIE COMPLETA =====
        # Só recria quando escala ou zoom mudam
        if (self._cached_surface is None or
                self._cached_scale != current_scale or
                self._cached_zoom != current_zoom):
            self._cached_surface = self._render_to_surface(current_scale)
            self._cached_scale = current_scale
            self._cached_zoom = current_zoom
            # Invalida a seção visível também
            self._cached_visible_section = None

        # Calcula a posição do primeiro tile (0,0) na tela
        screen_x, screen_y = render_context.world_to_screen(0, 0, camera, screen_manager)

        # ===== CACHE DA SEÇÃO VISÍVEL =====
        visible_rect = camera.get_visible_rect()

        # Converte a área visível para coordenadas da superfície cacheada
        tile_size_scaled = max(1, int(self.tile_size * current_scale))

        visible_start_x = max(0, int(visible_rect.x / self.tile_size) * tile_size_scaled)
        visible_start_y = max(0, int(visible_rect.y / self.tile_size) * tile_size_scaled)

        visible_end_x = min(self._cached_surface.get_width(),
                            int((
                                            visible_rect.x + visible_rect.width) / self.tile_size) * tile_size_scaled + tile_size_scaled)
        visible_end_y = min(self._cached_surface.get_height(),
                            int((
                                            visible_rect.y + visible_rect.height) / self.tile_size) * tile_size_scaled + tile_size_scaled)

        # Verifica se a área visível mudou significativamente
        current_visible_key = (visible_start_x, visible_start_y, visible_end_x, visible_end_y, screen_x, screen_y)

        if (self._cached_visible_section is None or
                self._last_camera_rect != current_visible_key):

            # Só recria se a área visível mudou
            if visible_start_x < visible_end_x and visible_start_y < visible_end_y:
                try:
                    self._cached_visible_section = self._cached_surface.subsurface((
                        visible_start_x,
                        visible_start_y,
                        visible_end_x - visible_start_x,
                        visible_end_y - visible_start_y
                    ))
                    self._last_camera_rect = current_visible_key
                    self._last_screen_pos = (screen_x + visible_start_x, screen_y + visible_start_y)
                except ValueError:
                    # Fallback se a subsurface for inválida
                    self._cached_visible_section = None
                    return

        # Renderiza a seção visível se existir
        if self._cached_visible_section and self._last_screen_pos:
            screen.blit(self._cached_visible_section,
                        (round(self._last_screen_pos[0]), round(self._last_screen_pos[1])))


class GameLayerManager:
    """Gerenciador de camadas para o jogo"""

    def __init__(self):
        self.layers = []
        self.width = 100
        self.height = 100
        self.tile_size = 24

    def add_layer(self, name, layer_type):
        layer = GameLayer(name, layer_type, self.width, self.height, self.tile_size)
        self.layers.append(layer)
        return layer

    def load_from_dict(self, data, base_path=""):
        """Carrega do dicionário - suporte a múltiplos tilesets"""
        print("\n=== Carregando GameLayerManager ===")

        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.tile_size = data.get("tile_size", 24)
        self.layers = []

        for layer_data in data.get("layers", []):
            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)
            layer_tile_size = layer_data.get("tile_size", self.tile_size)

            layer = GameLayer(
                layer_data["name"],
                layer_data["type"],
                layer_width,
                layer_height,
                layer_tile_size
            )

            # Carrega os tiles
            loaded_tiles = layer_data.get("tiles", [])
            for y in range(min(layer_height, len(loaded_tiles))):
                row = loaded_tiles[y] if y < len(loaded_tiles) else []
                for x in range(min(layer_width, len(row))):
                    try:
                        layer.tiles[y][x] = int(row[x])
                    except (ValueError, TypeError):
                        layer.tiles[y][x] = 0

            # Carrega tilesets (múltiplos)
            tileset_paths = []
            if layer_data.get("tileset_paths"):
                tileset_paths = layer_data["tileset_paths"]
            elif layer_data.get("tileset_path"):
                tileset_paths = [layer_data["tileset_path"]]

            print(f"Layer {layer_data['name']}: {len(tileset_paths)} tileset(s) para carregar")

            for ts_idx, ts_path in enumerate(tileset_paths):
                if not ts_path:
                    continue

                found_path = self._find_tileset_path(ts_path, base_path)
                if found_path:
                    if ts_idx == 0 and not layer.tileset:
                        success = layer.load_tileset(found_path, layer_tile_size, layer_tile_size)
                    else:
                        success = layer.add_tileset(found_path, layer_tile_size, layer_tile_size)

                    if success:
                        print(f"  ✓ Tileset {ts_idx + 1} carregado")
                    else:
                        print(f"  ✗ Falha ao carregar tileset {ts_idx + 1}")
                else:
                    print(f"  ✗ Tileset {ts_idx + 1} não encontrado: {ts_path}")

            self.layers.append(layer)
            print(f"  ✓ Camada {layer.name} carregada com {len(layer.tileset)} tiles")

        print(f"GameLayerManager carregado: {len(self.layers)} camadas, tile_size={self.tile_size}")
        return self

    def _find_tileset_path(self, tileset_path, base_path):
        """Encontra o caminho correto do tileset"""
        basename = os.path.basename(tileset_path)
        possible_paths = []

        # 1. Caminho usando base_path (geralmente PROJECT_ROOT)
        if base_path:
            clean_path = tileset_path
            if clean_path.startswith('pkm-td/'):
                clean_path = clean_path[len('pkm-td/'):]
            if clean_path.startswith('pkm-td\\'):
                clean_path = clean_path[len('pkm-td\\'):]
            possible_paths.append(os.path.join(base_path, clean_path))

        # 2. Caminho direto na pasta res/AllTiles
        possible_paths.append(os.path.join("res", "AllTiles", basename))

        # 3. Caminho com base_path + res/AllTiles
        if base_path:
            possible_paths.append(os.path.join(base_path, "res", "AllTiles", basename))

        # 4. Apenas o nome do arquivo
        possible_paths.append(basename)

        for path in possible_paths:
            normalized = os.path.normpath(path)
            if os.path.exists(normalized):
                print(f"  Encontrado: {normalized}")
                return normalized

        return None

    def render_all(self, screen, camera, screen_manager):
        """Renderiza todas as camadas na ordem correta"""
        # Ordem: ground, decoration, ceiling
        for layer in self.layers:
            if layer.layer_type == "ground":
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == "decoration":
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == "ceiling":
                layer.render(screen, camera, screen_manager)

    def get_dimensions(self):
        return (self.width * self.tile_size, self.height * self.tile_size)

    def invalidate_cache(self):
        """Invalida o cache de todas as camadas"""
        for layer in self.layers:
            layer._invalidate_surface_cache()
            layer._cached_tiles.clear()