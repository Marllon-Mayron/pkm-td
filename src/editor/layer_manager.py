# src/editor/layer_manager.py

"""
Gerenciador de layers do mapa com suporte a múltiplos tilesets em grade 6x8
"""
import pygame
import json
import os
from enum import Enum

try:
    from src.config.paths import PROJECT_ROOT, RES_PATH
except ImportError:
    PROJECT_ROOT = ""
    RES_PATH = ""
class LayerType(Enum):
    GROUND = "ground"
    DECORATION = "decoration"
    CEILING = "ceiling"


class Layer:
    def __init__(self, name, layer_type, width, height, tile_size=24):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.visible = True
        self.opacity = 255
        self.tileset_path = None
        self.tileset = []

        # Suporte para múltiplos tilesets
        self.tilesets = []  # Lista de dicts com path, tiles, start_id
        self.tileset_paths = []

    def set_tile(self, x, y, tile_id):
        """Define um tile na posição especificada"""
        if 0 <= x < self.width and 0 <= y < self.height:
            try:
                self.tiles[y][x] = int(tile_id)
            except (ValueError, TypeError):
                self.tiles[y][x] = 0
            return True
        return False

    def get_tile(self, x, y):
        """Retorna o tile na posição especificada"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0

    def get_all_tiles_with_boundaries(self):
        """
        Retorna (tiles_concatenados, boundaries)
        tiles_concatenados: lista com todos os tiles de todos os tilesets
        boundaries: lista de índices onde cada tileset começa (0-indexed)
        """
        all_tiles = []
        boundaries = []

        for ts_info in self.tilesets:
            boundaries.append(len(all_tiles))  # Marca onde começa este tileset
            all_tiles.extend(ts_info['tiles'])

        print(f"[get_all_tiles] Total tiles: {len(all_tiles)}, Boundaries: {boundaries}")
        return all_tiles, boundaries

    def load_tileset_6x8(self, image_path, tile_width, tile_height):
        """
        Carrega um tileset organizado em 6 colunas x 8 linhas
        Agora suporta múltiplos tilesets na mesma imagem (horizontalmente)
        """
        try:
            print(f"\n--- load_tileset_6x8 ---")
            print(f"Tentando carregar: {image_path}")
            print(f"Tile size: {tile_width}x{tile_height}")

            if not os.path.exists(image_path):
                print(f"ERRO: Arquivo não encontrado!")
                return None

            sheet = pygame.image.load(image_path).convert_alpha()
            img_width = sheet.get_width()
            img_height = sheet.get_height()
            print(f"Imagem carregada: {img_width}x{img_height}")

            # Configuração fixa: 6 colunas x 8 linhas por tileset
            COLS_PER_SET = 6
            ROWS_PER_SET = 8

            # Calcula quantos tilesets cabem na largura da imagem
            tileset_width = COLS_PER_SET * tile_width  # 6 * 24 = 144
            num_tilesets = img_width // tileset_width

            print(f"Tileset width: {tileset_width}px")
            print(f"Total de tilesets detectados: {num_tilesets}")

            all_tiles = []
            tilesets_info = []

            # Para cada tileset na imagem
            for ts_idx in range(num_tilesets):
                offset_x = ts_idx * tileset_width
                print(f"\n--- Processando tileset {ts_idx + 1}/{num_tilesets} ---")
                print(f"Offset X: {offset_x}")

                tileset_tiles = []

                # Extrai os tiles na ordem: linha por linha, coluna por coluna
                for row in range(ROWS_PER_SET):
                    for col in range(COLS_PER_SET):
                        rect = pygame.Rect(
                            offset_x + col * tile_width,
                            row * tile_height,
                            tile_width,
                            tile_height
                        )
                        # Verifica se o rect está dentro da imagem
                        if rect.right <= img_width and rect.bottom <= img_height:
                            tile = sheet.subsurface(rect)
                            tileset_tiles.append(tile)
                        else:
                            # Cria tile vazio se fora dos limites
                            empty_tile = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)
                            empty_tile.fill((0, 0, 0, 0))
                            tileset_tiles.append(empty_tile)
                            print(f"  Aviso: Tile ({col}, {row}) fora dos limites")

                print(f"Extraídos {len(tileset_tiles)} tiles do tileset {ts_idx + 1}")
                all_tiles.extend(tileset_tiles)

                tilesets_info.append({
                    'index': ts_idx,
                    'offset_x': offset_x,
                    'count': len(tileset_tiles),
                    'start_id': len(all_tiles) - len(tileset_tiles) + 1
                })

            print(f"\nTotal de tiles carregados: {len(all_tiles)}")
            print(f"Total de tilesets: {num_tilesets}")

            return all_tiles, tilesets_info, num_tilesets

        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
            import traceback
            traceback.print_exc()
            return None, None, 0

    def load_tileset(self, image_path, tile_width, tile_height):
        """
        Carrega um tileset - detecta múltiplos tilesets na mesma imagem
        """
        all_tiles, tilesets_info, num_tilesets = self.load_tileset_6x8(image_path, tile_width, tile_height)

        if all_tiles is None:
            return False

        # Limpa tilesets existentes
        self.tileset = []
        self.tilesets = []
        self.tileset_paths = []

        # Adiciona todos os tiles
        self.tileset = all_tiles

        # Cria informações para cada tileset
        current_start = 0
        for ts_idx in range(num_tilesets):
            ts_count = 48  # 6x8 = 48 tiles por tileset
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

        # Converte para caminho relativo
        if os.path.isabs(image_path):
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                relative_path = os.path.relpath(image_path, project_root)
                self.tileset_path = relative_path.replace('\\', '/')
                self.tileset_paths = [self.tileset_path]  # Todos vêm do mesmo arquivo
            except:
                self.tileset_path = os.path.basename(image_path)
                self.tileset_paths = [self.tileset_path]
        else:
            self.tileset_path = image_path
            self.tileset_paths = [self.tileset_path]

        print(f"\n✓ Tileset(s) carregado(s): {num_tilesets} tilesets, {len(self.tileset)} tiles")
        return True

    def add_tileset_6x8(self, image_path, tile_width, tile_height):
        """
        Adiciona um novo arquivo de tileset à layer existente
        Cada arquivo pode conter múltiplos tilesets (6x8 cada) lado a lado
        """
        all_tiles, tilesets_info, num_tilesets = self.load_tileset_6x8(image_path, tile_width, tile_height)

        if all_tiles is None:
            return False

        print(f"\n--- add_tileset_6x8 ---")
        print(f"Arquivo: {image_path}")
        print(f"Tilesets detectados: {num_tilesets}")
        print(f"Total de tiles no arquivo: {len(all_tiles)}")

        # Calcula o próximo start_id
        next_start_id = len(self.tileset) + 1

        # Adiciona todos os novos tiles
        self.tileset.extend(all_tiles)

        # Adiciona informações de cada tileset encontrado no arquivo
        current_start = len(self.tileset) - len(all_tiles)
        for ts_idx in range(num_tilesets):
            ts_count = 48  # 6x8 = 48 tiles por tileset
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
            print(
                f"  - Tileset {len(self.tilesets)}: IDs {tileset_info['start_id']} a {tileset_info['start_id'] + ts_count - 1}")
            current_start += ts_count

        # Adiciona o caminho (todos vêm do mesmo arquivo)
        if os.path.isabs(image_path):
            try:
                project_root = self._get_project_root()
                relative_path = os.path.relpath(image_path, project_root)
                rel_path = relative_path.replace('\\', '/')
                if rel_path not in self.tileset_paths:
                    self.tileset_paths.append(rel_path)
            except:
                if image_path not in self.tileset_paths:
                    self.tileset_paths.append(os.path.basename(image_path))
        else:
            if image_path not in self.tileset_paths:
                self.tileset_paths.append(image_path)

        print(f"\n✓ Tileset(s) adicionado(s): {num_tilesets} novos tilesets")
        print(f"  Total de tiles: {len(self.tileset)}")
        print(f"  Total de tilesets: {len(self.tilesets)}")
        return True

    def _load_single_tileset_6x8(self, image_path, tile_width, tile_height):
        """Carrega um único arquivo de tileset (pode conter múltiplos tilesets)"""
        try:
            print(f"\n--- _load_single_tileset_6x8 ---")
            print(f"Tentando carregar: {image_path}")

            all_tiles, tilesets_info, num_tilesets = self.load_tileset_6x8(image_path, tile_width, tile_height)

            if all_tiles is None:
                return False

            # Limpa tilesets existentes (apenas se for o primeiro carregamento)
            self.tileset = []
            self.tilesets = []
            self.tileset_paths = []

            # Adiciona todos os tiles
            self.tileset = all_tiles

            # Cria informações para cada tileset encontrado no arquivo
            current_start = 0
            for ts_idx in range(num_tilesets):
                ts_count = 48  # 6x8 = 48 tiles por tileset
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
                print(
                    f"  - Tileset {ts_idx + 1}: IDs {tileset_info['start_id']} a {tileset_info['start_id'] + ts_count - 1}")
                current_start += ts_count

            # Converte para caminho relativo
            if os.path.isabs(image_path):
                try:
                    project_root = self._get_project_root()
                    relative_path = os.path.relpath(image_path, project_root)
                    self.tileset_path = relative_path.replace('\\', '/')
                    self.tileset_paths.append(self.tileset_path)
                except:
                    self.tileset_path = os.path.basename(image_path)
                    self.tileset_paths.append(self.tileset_path)
            else:
                self.tileset_path = image_path
                self.tileset_paths.append(self.tileset_path)

            print(f"\n✓ Carregados {num_tilesets} tilesets do arquivo, total {len(self.tileset)} tiles")
            return True

        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_tileset_info(self, tile_id):
        """
        Retorna informações sobre qual tileset contém o tile
        Retorna (tileset_index, local_index, tileset_info)
        """
        try:
            tile_index = int(tile_id) - 1
            if tile_index < 0:
                return None

            current_start = 0
            for i, ts_info in enumerate(self.tilesets):
                if tile_index < current_start + ts_info['count']:
                    local_index = tile_index - current_start
                    # Calcula posição na grade 6x8
                    row = local_index // ts_info['cols']
                    col = local_index % ts_info['cols']
                    return (i, local_index, ts_info, row, col)
                current_start += ts_info['count']
            return None
        except (ValueError, TypeError):
            return None

    def get_tile_image(self, tile_id):
        """Retorna a imagem do tile pelo ID"""
        try:
            tile_index = int(tile_id) - 1
            if 0 <= tile_index < len(self.tileset):
                return self.tileset[tile_index]
            return None
        except (ValueError, TypeError):
            return None

    def resize(self, new_width, new_height, default_tile=0):
        """Redimensiona a layer"""
        if new_width == self.width and new_height == self.height:
            return True

        print(f"Redimensionando layer '{self.name}' de {self.width}x{self.height} para {new_width}x{new_height}")

        try:
            default_tile = int(default_tile)
        except (ValueError, TypeError):
            default_tile = 0

        new_tiles = [[default_tile for _ in range(new_width)] for _ in range(new_height)]

        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_tiles[y][x] = self.tiles[y][x]

        self.tiles = new_tiles
        self.width = new_width
        self.height = new_height

        return True

    def render(self, screen, camera, screen_manager):
        """Renderiza a layer com tile_size 24"""
        if not self.visible or not self.tileset:
            return

        # Calcula offset da câmera
        cam_offset_x = round((-camera.x * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_width / 2) * screen_manager.render_scale +
                              screen_manager.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_height / 2) * screen_manager.render_scale +
                              screen_manager.viewport_y))

        # Tamanho do tile escalado
        tile_size_scaled = max(1, round(self.tile_size * camera.zoom * screen_manager.render_scale))

        # Calcula tiles visíveis
        start_x = max(0, (-cam_offset_x) // tile_size_scaled)
        start_y = max(0, (-cam_offset_y) // tile_size_scaled)
        end_x = min(self.width, start_x + (screen_manager.viewport_width // tile_size_scaled) + 2)
        end_y = min(self.height, start_y + (screen_manager.viewport_height // tile_size_scaled) + 2)

        # Renderiza tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]

                try:
                    tile_index = int(tile_id) - 1
                except (ValueError, TypeError):
                    tile_index = -1

                if tile_index >= 0 and tile_index < len(self.tileset):
                    screen_x = x * tile_size_scaled + cam_offset_x
                    screen_y = y * tile_size_scaled + cam_offset_y

                    if (screen_x + tile_size_scaled > screen_manager.viewport_x and
                            screen_x < screen_manager.viewport_x + screen_manager.viewport_width and
                            screen_y + tile_size_scaled > screen_manager.viewport_y and
                            screen_y < screen_manager.viewport_y + screen_manager.viewport_height):

                        tile_img = self.tileset[tile_index]

                        if (tile_img.get_width() != tile_size_scaled or
                                tile_img.get_height() != tile_size_scaled):
                            scaled_tile = pygame.transform.scale(
                                tile_img,
                                (tile_size_scaled, tile_size_scaled)
                            )
                            scaled_tile.set_alpha(self.opacity)
                            screen.blit(scaled_tile, (screen_x, screen_y))
                        else:
                            tile_img.set_alpha(self.opacity)
                            screen.blit(tile_img, (screen_x, screen_y))

    def _get_project_root(self):
        """Retorna o caminho da raiz do projeto"""
        try:
            from src.config.paths import PROJECT_ROOT
            return PROJECT_ROOT
        except ImportError:
            # Fallback: sobe até encontrar a raiz
            current = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                if os.path.exists(os.path.join(current, "src", "main.py")):
                    return current
                current = os.path.dirname(current)
            return ""

class LayerManager:
    def __init__(self):
        self.layers = []
        self.current_layer = 0
        self.width = 100
        self.height = 100
        self.tile_size = 24

    def add_layer(self, name, layer_type):
        layer = Layer(name, layer_type, self.width, self.height, self.tile_size)
        self.layers.append(layer)
        return layer

    def remove_layer(self, index):
        if 0 <= index < len(self.layers):
            del self.layers[index]
            if self.current_layer >= len(self.layers):
                self.current_layer = max(0, len(self.layers) - 1)

    def resize_all_layers(self, new_width, new_height, default_tile=0):
        if new_width == self.width and new_height == self.height:
            return True

        print(f"Redimensionando todas as layers de {self.width}x{self.height} para {new_width}x{new_height}")

        try:
            default_tile = int(default_tile)
        except (ValueError, TypeError):
            default_tile = 0

        for layer in self.layers:
            layer.resize(new_width, new_height, default_tile)

        self.width = new_width
        self.height = new_height
        return True

    def get_current_layer(self):
        if 0 <= self.current_layer < len(self.layers):
            return self.layers[self.current_layer]
        return None

    def set_tile(self, x, y, tile_id):
        layer = self.get_current_layer()
        if layer:
            return layer.set_tile(x, y, tile_id)
        return False

    def get_tile(self, x, y, layer_index=None):
        if layer_index is None:
            layer_index = self.current_layer
        if 0 <= layer_index < len(self.layers):
            return self.layers[layer_index].get_tile(x, y)
        return 0

    def render_all(self, screen, camera, screen_manager):
        for layer in self.layers:
            if layer.layer_type == LayerType.GROUND:
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == LayerType.DECORATION:
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == LayerType.CEILING:
                layer.render(screen, camera, screen_manager)

    def to_dict(self):
        max_width = 0
        max_height = 0

        for layer in self.layers:
            max_width = max(max_width, layer.width)
            max_height = max(max_height, layer.height)

        layers_data = []
        for layer in self.layers:
            layer_dict = {
                "name": layer.name,
                "type": layer.layer_type.value,
                "tiles": layer.tiles,
                "width": layer.width,
                "height": layer.height,
                "tile_size": layer.tile_size
            }

            if hasattr(layer, 'tileset_paths') and layer.tileset_paths:
                layer_dict["tileset_paths"] = layer.tileset_paths
            elif layer.tileset_path:
                layer_dict["tileset_path"] = layer.tileset_path

            layers_data.append(layer_dict)

        return {
            "width": max_width,
            "height": max_height,
            "tile_size": self.tile_size,
            "layers": layers_data
        }

    def from_dict(self, data, base_path=""):
        """Carrega do dicionário - suporte a múltiplos tilesets"""
        print("\n=== INÍCIO do from_dict ===")
        print(f"Base path recebido: {base_path}")
        print(f"PROJECT_ROOT: {self._get_project_root()}")

        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.tile_size = data.get("tile_size", 24)
        self.layers = []

        for layer_idx, layer_data in enumerate(data["layers"]):
            print(f"\n--- Processando layer {layer_idx}: {layer_data['name']} ---")

            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)
            layer_tile_size = layer_data.get("tile_size", self.tile_size)
            print(f"Dimensões: {layer_width}x{layer_height}, Tile size: {layer_tile_size}")

            loaded_tiles = layer_data["tiles"]

            # Cria a layer
            layer = Layer(
                layer_data["name"],
                LayerType(layer_data["type"]),
                layer_width,
                layer_height,
                layer_tile_size
            )

            # COPIA OS TILES
            for y in range(layer_height):
                for x in range(layer_width):
                    if y < len(loaded_tiles) and x < len(loaded_tiles[y]):
                        try:
                            layer.tiles[y][x] = int(loaded_tiles[y][x])
                        except (ValueError, TypeError):
                            layer.tiles[y][x] = 0
                    else:
                        layer.tiles[y][x] = 0

            # Carrega tilesets
            tileset_paths = []
            if layer_data.get("tileset_paths"):
                tileset_paths = layer_data["tileset_paths"]
            elif layer_data.get("tileset_path"):
                tileset_paths = [layer_data["tileset_path"]]

            print(f"Tileset paths encontrados: {tileset_paths}")

            for ts_idx, ts_path in enumerate(tileset_paths):
                if not ts_path:
                    continue

                print(f"\n--- Carregando tileset {ts_idx + 1}/{len(tileset_paths)}: {ts_path} ---")

                # Lista de possíveis caminhos para procurar
                possible_paths = []

                # Obtém o nome base do arquivo
                basename = os.path.basename(ts_path)

                # 1. Caminho a partir da raiz do projeto (PROJECT_ROOT)
                project_root = self._get_project_root()
                if project_root:
                    # Remove qualquer "pkm-td/" duplicado no início
                    clean_path = ts_path
                    if clean_path.startswith('pkm-td/'):
                        clean_path = clean_path[len('pkm-td/'):]
                    if clean_path.startswith('pkm-td\\'):
                        clean_path = clean_path[len('pkm-td\\'):]

                    full_path = os.path.join(project_root, clean_path)
                    possible_paths.append(full_path)
                    print(f"  Path 1 (project_root): {full_path}")

                # 2. Caminho usando base_path (se fornecido)
                if base_path:
                    full_path = os.path.join(base_path, ts_path)
                    possible_paths.append(full_path)
                    print(f"  Path 2 (base_path): {full_path}")

                # 3. Caminho direto na pasta res/AllTiles
                res_path = os.path.join(RES_PATH, "AllTiles", basename)
                possible_paths.append(res_path)
                print(f"  Path 3 (res/AllTiles): {res_path}")

                # 4. Apenas o nome do arquivo
                possible_paths.append(basename)
                print(f"  Path 4 (filename only): {basename}")

                # Tenta cada caminho
                loaded = False
                for path in possible_paths:
                    normalized = os.path.normpath(path)
                    print(f"  Verificando: {normalized}")
                    print(f"    Existe? {os.path.exists(normalized)}")

                    if os.path.exists(normalized):
                        print(f"  ✓ ENCONTRADO: {normalized}")

                        if ts_idx == 0 and not layer.tileset:
                            success = layer._load_single_tileset_6x8(normalized, layer_tile_size, layer_tile_size)
                        else:
                            success = layer.add_tileset_6x8(normalized, layer_tile_size, layer_tile_size)

                        if success:
                            print(f"  ✓ Tileset {ts_idx + 1} carregado")
                            loaded = True
                            break
                        else:
                            print(f"  ✗ Falha ao carregar tileset")

                if not loaded:
                    print(f"  ✗ NENHUM CAMINHO FUNCIONOU para {ts_path}")
                    print(f"  Arquivo não encontrado. Verifique se o tileset existe em res/AllTiles/")

            self.layers.append(layer)

        print("\n=== FIM do from_dict ===")
        return self

    def _get_project_root(self):
        """Retorna o caminho da raiz do projeto"""
        try:
            from src.config.paths import PROJECT_ROOT
            return PROJECT_ROOT
        except ImportError:
            # Fallback: sobe até encontrar a raiz
            current = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                if os.path.exists(os.path.join(current, "src", "main.py")):
                    return current
                current = os.path.dirname(current)
            return ""