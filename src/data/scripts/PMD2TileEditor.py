import pygame
import sys
import json
import os
from pathlib import Path
from tkinter import filedialog, Tk
import tkinter as tk

from numpy.ma.core import copy


class PMD2TileEditor:
    """
    Editor de tiles estilo Pokémon Mystery Dungeon 2
    Com seletor de arquivos e design melhorado
    """

    def __init__(self, tile_size=32, grid_width=15, grid_height=12):
        pygame.init()

        self.tile_size = tile_size
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.screen_width = grid_width * tile_size + 400  # Mais espaço para UI
        self.screen_height = max(grid_height * tile_size, 700)

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("PMD2 Tile Editor - Pokémon Mystery Dungeon 2 Style")
        #pygame.display.set_icon(self.create_icon())

        # Cores - Paleta melhorada
        self.COLORS = {
            'bg': (30, 30, 35),
            'bg_dark': (20, 20, 25),
            'bg_light': (45, 45, 50),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'gray': (128, 128, 128),
            'light_gray': (200, 200, 200),
            'red': (255, 80, 80),
            'blue': (80, 150, 255),
            'green': (80, 255, 80),
            'yellow': (255, 255, 80),
            'orange': (255, 165, 80),
            'purple': (180, 80, 255),
            'cyan': (80, 255, 255),
            'hover': (100, 100, 150, 128),
            'selection': (255, 200, 80, 200),
        }

        # Carregar tileset
        self.tileset_path = None
        self.tileset = None
        self.tiles = []
        self.current_tileset_name = "Nenhum tileset carregado"

        # Inicializar fontes
        self.font_title = pygame.font.Font(None, 32)
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_bold = pygame.font.Font(None, 24)
        self.font_bold.set_bold(True)

        # Mapa do editor
        self.map_grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]

        # Seleção
        self.selected_tile = 0
        self.hover_tile = -1
        self.hover_grid_pos = None

        # Modos
        self.autopath_mode = True
        self.show_grid = True
        self.show_preview = True
        self.brush_size = 1
        self.brush_shapes = ['single', 'cross', 'square']
        self.brush_shape = 0  # 0=single, 1=cross, 2=square

        # Câmera/scroll
        self.palette_scroll = 0
        self.tiles_per_row = 6
        self.palette_tile_size = 42

        # Interface
        self.clock = pygame.time.Clock()
        self.running = True
        self.dragging = False
        self.last_mouse_pos = None

        # Histórico
        self.history = []
        self.history_limit = 30
        self.save_state()  # Salvar estado inicial

        # UI elements
        self.button_rects = {}
        self.panel_rect = None
        self.grid_rect = None
        self.palette_rect = None

        # Animação
        self.animation_counter = 0
        self.message = ""
        self.message_timer = 0

        # Zoom
        self.zoom_level = 1
        self.grid_offset_x = 0
        self.grid_offset_y = 0

        # Buscar tilesets automaticamente
        self.available_tilesets = []
        self.scan_tilesets()

        print("Editor inicializado. Pressione 'O' para abrir um tileset ou 'Ctrl+O' para procurar automaticamente")

    def create_icon(self):
        """Cria um ícone para a janela"""
        icon = pygame.Surface((32, 32))
        icon.fill(self.COLORS['blue'])
        pygame.draw.rect(icon, self.COLORS['green'], (8, 8, 16, 16))
        pygame.draw.polygon(icon, self.COLORS['yellow'], [(16, 4), (12, 12), (20, 12)])
        return icon

    def scan_tilesets(self):
        """Procura automaticamente por tilesets em diretórios comuns"""
        common_paths = [
            ".",  # Diretório atual
            "tilesets",
            "../tilesets",
            "../../tilesets",
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Pictures"),
        ]

        extensions = ('.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG', '.bmp', '.BMP')
        found = []

        for search_path in common_paths:
            if os.path.exists(search_path):
                for file in os.listdir(search_path):
                    if file.lower().endswith(extensions):
                        full_path = os.path.join(search_path, file)
                        found.append(full_path)

        self.available_tilesets = found[:20]  # Limitar a 20 arquivos
        if self.available_tilesets:
            print(f"Encontrados {len(self.available_tilesets)} arquivos de imagem:")
            for ts in self.available_tilesets[:5]:
                print(f"  - {ts}")
            if len(self.available_tilesets) > 5:
                print(f"  ... e mais {len(self.available_tilesets) - 5} arquivos")

    def open_file_dialog(self):
        """Abre diálogo para selecionar arquivo"""
        # Esconder a janela do pygame temporariamente
        pygame.display.iconify()

        # Usar tkinter para diálogo
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_path = filedialog.askopenfilename(
            title="Selecione o tilesheet",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )

        root.destroy()

        # Restaurar janela do pygame
        pygame.display.set_mode((self.screen_width, self.screen_height))

        if file_path:
            self.load_tileset(file_path)
            self.show_message(f"Tileset carregado: {os.path.basename(file_path)}")
        else:
            self.show_message("Nenhum arquivo selecionado")

    def load_tileset(self, path):
        """Carrega o spritesheet especificado"""
        try:
            # Verificar se arquivo existe
            if not os.path.exists(path):
                self.show_message(f"Arquivo não encontrado: {path}")
                return False

            # Carregar imagem
            self.tileset = pygame.image.load(path).convert_alpha()
            self.tileset_path = path
            self.current_tileset_name = os.path.basename(path)

            # Obter dimensões
            sheet_width = self.tileset.get_width()
            sheet_height = self.tileset.get_height()

            print(f"Spritesheet carregado: {sheet_width}x{sheet_height}")

            # Calcular quantos tiles cabem
            tiles_x = sheet_width // self.tile_size
            tiles_y = sheet_height // self.tile_size

            print(f"Tiles por linha: {tiles_x}, por coluna: {tiles_y}")

            # Extrair tiles
            self.tiles = []
            for row in range(tiles_y):
                for col in range(tiles_x):
                    x = col * self.tile_size
                    y = row * self.tile_size
                    tile_rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                    tile = self.tileset.subsurface(tile_rect).copy()
                    self.tiles.append(tile)

            print(f"✓ Extraídos {len(self.tiles)} tiles")

            # Resetar seleção
            self.selected_tile = 0
            self.palette_scroll = 0

            # Resetar mapa se desejar (opcional)
            # self.clear_map()

            return True

        except Exception as e:
            print(f"Erro ao carregar {path}: {e}")
            self.show_message(f"Erro: {e}")
            return False

    def show_message(self, msg, duration=120):
        """Mostra uma mensagem temporária"""
        self.message = msg
        self.message_timer = duration

    def save_state(self):
        """Salva estado atual para undo"""
        import copy
        state = copy.deepcopy(self.map_grid)
        self.history.append(state)
        if len(self.history) > self.history_limit:
            self.history.pop(0)

    def undo(self):
        """Desfaz última ação"""
        if len(self.history) > 1:
            self.history.pop()  # Remove estado atual
            self.map_grid = copy.deepcopy(self.history[-1])
            self.show_message("Undo realizado")
            return True
        else:
            self.show_message("Nada para desfazer")
            return False

    def clear_map(self):
        """Limpa o mapa"""
        self.save_state()
        self.map_grid = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        self.show_message("Mapa limpo")

    def get_neighbor_mask(self, grid, x, y):
        """Calcula máscara de vizinhança para autotiling"""
        mask = 0
        height = len(grid)
        width = len(grid[0])

        neighbors = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ]

        for i, (dx, dy) in enumerate(neighbors):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if grid[ny][nx] != 0:
                    mask |= (1 << i)

        return mask

    def get_autotile_index(self, mask, base_tile):
        """Retorna o tile correto baseado na máscara"""
        # Sistema melhorado de autotiling
        patterns = {
            0b00000000: 0,  # Isolado
            0b10001000: 1,  # Norte
            0b00010010: 2,  # Sul
            0b01000100: 3,  # Leste
            0b00100001: 4,  # Oeste
            0b10001001: 5,  # Norte + Oeste
            0b11001000: 6,  # Norte + Leste
            0b00011011: 7,  # Sul + Oeste
            0b00110010: 8,  # Sul + Leste
            0b10101000: 9,  # Norte + Sul
            0b01000101: 10,  # Leste + Oeste
            0b11101000: 11,  # T Norte
            0b00011110: 12,  # T Sul
            0b01110100: 13,  # T Leste
            0b10110001: 14,  # T Oeste
            0b11101110: 15,  # Cruz
        }

        return patterns.get(mask, base_tile % 16)

    def apply_autopath(self, grid, x, y):
        """Aplica autotiling em uma área"""
        height = len(grid)
        width = len(grid[0])

        # Posições para atualizar
        positions = [(x, y)]
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] != 0:
                    positions.append((nx, ny))

        positions = list(set(positions))

        for px, py in positions:
            if grid[py][px] != 0:
                mask = self.get_neighbor_mask(grid, px, py)
                base_type = (grid[py][px] // 16) * 16
                new_tile = self.get_autotile_index(mask, grid[py][px])
                grid[py][px] = base_type + new_tile

    def paint_tile(self, x, y, tile_idx, is_erase=False):
        """Pinta tile com suporte a brush shapes"""
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return

        self.save_state()

        # Aplicar brush shape
        if self.brush_shape == 0:  # Single
            positions = [(x, y)]
        elif self.brush_shape == 1:  # Cross
            positions = [(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        else:  # Square
            positions = [(x + dx, y + dy) for dx in range(-self.brush_size + 1, self.brush_size)
                         for dy in range(-self.brush_size + 1, self.brush_size)]

        for px, py in positions:
            if 0 <= px < self.grid_width and 0 <= py < self.grid_height:
                if is_erase:
                    self.map_grid[py][px] = 0
                else:
                    self.map_grid[py][px] = tile_idx

                if self.autopath_mode and not is_erase:
                    self.apply_autopath(self.map_grid, px, py)

    def draw_background(self):
        """Desenha fundo gradiente"""
        for i in range(self.screen_height):
            color_value = 30 + (i * 15 // self.screen_height)
            color = (color_value, color_value, color_value + 10)
            pygame.draw.line(self.screen, color, (0, i), (self.screen_width, i))

    def draw_grid_area(self):
        """Desenha a área do grid principal"""
        # Fundo do grid
        grid_width_px = self.grid_width * self.tile_size
        grid_height_px = self.grid_height * self.tile_size

        self.grid_rect = pygame.Rect(0, 0, grid_width_px, grid_height_px)
        pygame.draw.rect(self.screen, self.COLORS['bg_dark'], self.grid_rect)

        # Desenhar tiles
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                rect = pygame.Rect(x * self.tile_size, y * self.tile_size,
                                   self.tile_size, self.tile_size)

                tile_idx = self.map_grid[y][x]
                if 0 <= tile_idx < len(self.tiles):
                    self.screen.blit(self.tiles[tile_idx], rect)
                else:
                    # Padrão quadriculado para tiles vazios
                    if (x + y) % 2 == 0:
                        pygame.draw.rect(self.screen, (50, 50, 55), rect)
                    else:
                        pygame.draw.rect(self.screen, (45, 45, 50), rect)

                # Grid overlay
                if self.show_grid:
                    pygame.draw.rect(self.screen, self.COLORS['gray'], rect, 1)

        # Borda do grid
        pygame.draw.rect(self.screen, self.COLORS['blue'], self.grid_rect, 3)

    def draw_hover_effect(self):
        """Desenha efeito de hover no grid"""
        if self.hover_grid_pos:
            x, y = self.hover_grid_pos
            if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                rect = pygame.Rect(x * self.tile_size, y * self.tile_size,
                                   self.tile_size, self.tile_size)

                # Efeito de brilho
                s = pygame.Surface((self.tile_size, self.tile_size))
                s.set_alpha(100)

                if self.brush_size > 1:
                    # Mostrar área do brush
                    for dy in range(self.brush_size):
                        for dx in range(self.brush_size):
                            bx, by = x + dx, y + dy
                            if 0 <= bx < self.grid_width and 0 <= by < self.grid_height:
                                brush_rect = pygame.Rect(bx * self.tile_size, by * self.tile_size,
                                                         self.tile_size, self.tile_size)
                                pygame.draw.rect(self.screen, self.COLORS['yellow'], brush_rect, 3)
                else:
                    s.fill(self.COLORS['hover'][:3])
                    self.screen.blit(s, rect)
                    pygame.draw.rect(self.screen, self.COLORS['cyan'], rect, 2)

    def draw_palette(self):
        """Desenha a paleta de tiles estilizada"""
        palette_x = self.grid_width * self.tile_size + 10
        palette_width = self.screen_width - palette_x - 10

        # Fundo da paleta
        self.palette_rect = pygame.Rect(palette_x - 5, 0, palette_width + 10, self.screen_height)
        pygame.draw.rect(self.screen, self.COLORS['bg'], self.palette_rect)
        pygame.draw.rect(self.screen, self.COLORS['blue'], self.palette_rect, 2)

        # Título da paleta
        title_y = 10
        title = self.font_title.render("TILE PALETTE", True, self.COLORS['white'])
        title_rect = title.get_rect(center=(palette_x + palette_width // 2, title_y + 10))
        self.screen.blit(title, title_rect)

        # Informação do tileset
        ts_info = self.font_small.render(self.current_tileset_name[:30], True, self.COLORS['gray'])
        self.screen.blit(ts_info, (palette_x, title_y + 35))

        # Botão de carregar tileset
        load_btn = pygame.Rect(palette_x + palette_width - 120, title_y + 30, 110, 25)
        pygame.draw.rect(self.screen, self.COLORS['bg_light'], load_btn)
        pygame.draw.rect(self.screen, self.COLORS['green'], load_btn, 2)
        load_text = self.font_small.render("Load Tileset", True, self.COLORS['green'])
        self.screen.blit(load_text, (load_btn.x + 10, load_btn.y + 4))
        self.button_rects['load_tileset'] = load_btn

        # Scroll buttons
        scroll_y = title_y + 65
        up_btn = pygame.Rect(palette_x + palette_width - 40, scroll_y, 30, 25)
        down_btn = pygame.Rect(palette_x + palette_width - 40, scroll_y + 30, 30, 25)

        pygame.draw.rect(self.screen, self.COLORS['bg_light'], up_btn)
        pygame.draw.rect(self.screen, self.COLORS['bg_light'], down_btn)
        pygame.draw.rect(self.screen, self.COLORS['white'], up_btn, 1)
        pygame.draw.rect(self.screen, self.COLORS['white'], down_btn, 1)

        up_text = self.font.render("▲", True, self.COLORS['white'])
        down_text = self.font.render("▼", True, self.COLORS['white'])
        self.screen.blit(up_text, (up_btn.x + 10, up_btn.y + 2))
        self.screen.blit(down_text, (down_btn.x + 10, down_btn.y + 2))

        self.button_rects['palette_up'] = up_btn
        self.button_rects['palette_down'] = down_btn

        # Mostrar tiles
        if self.tiles:
            cols = self.tiles_per_row
            start_idx = self.palette_scroll * cols
            tile_y = scroll_y + 70

            self.hover_tile = -1

            for i in range(start_idx, min(start_idx + (cols * 10), len(self.tiles))):
                row = (i - start_idx) // cols
                col = (i - start_idx) % cols

                x = palette_x + col * (self.palette_tile_size + 8)
                y = tile_y + row * (self.palette_tile_size + 8)

                # Fundo do tile
                tile_bg = pygame.Rect(x - 2, y - 2, self.palette_tile_size + 4, self.palette_tile_size + 4)
                pygame.draw.rect(self.screen, self.COLORS['bg_dark'], tile_bg)

                # Desenhar tile
                scaled_tile = pygame.transform.scale(self.tiles[i],
                                                     (self.palette_tile_size, self.palette_tile_size))
                self.screen.blit(scaled_tile, (x, y))

                # Borda de seleção
                if i == self.selected_tile:
                    pygame.draw.rect(self.screen, self.COLORS['orange'], tile_bg, 3)
                else:
                    pygame.draw.rect(self.screen, self.COLORS['gray'], tile_bg, 1)

                # Número do tile
                num_text = self.font_small.render(str(i), True, self.COLORS['white'])
                num_bg = pygame.Surface((num_text.get_width() + 4, num_text.get_height() + 2))
                num_bg.fill(self.COLORS['black'])
                num_bg.set_alpha(180)
                self.screen.blit(num_bg, (x + 2, y + self.palette_tile_size - 16))
                self.screen.blit(num_text, (x + 4, y + self.palette_tile_size - 15))

                # Hover effect
                mouse_pos = pygame.mouse.get_pos()
                if tile_bg.collidepoint(mouse_pos):
                    self.hover_tile = i
                    pygame.draw.rect(self.screen, self.COLORS['cyan'], tile_bg, 2)
        else:
            # Mensagem sem tileset
            no_ts_text = self.font.render("No tileset loaded", True, self.COLORS['gray'])
            no_ts_rect = no_ts_text.get_rect(center=(palette_x + palette_width // 2, self.screen_height // 2))
            self.screen.blit(no_ts_text, no_ts_rect)

            no_ts_text2 = self.font_small.render("Press 'O' to open a tileset", True, self.COLORS['gray'])
            no_ts_rect2 = no_ts_text2.get_rect(center=(palette_x + palette_width // 2, self.screen_height // 2 + 30))
            self.screen.blit(no_ts_text2, no_ts_rect2)

    def draw_controls_panel(self):
        """Desenha o painel de controles inferior"""
        panel_y = self.grid_height * self.tile_size + 10
        panel_height = self.screen_height - panel_y - 10

        self.panel_rect = pygame.Rect(0, panel_y, self.grid_width * self.tile_size, panel_height)
        pygame.draw.rect(self.screen, self.COLORS['bg'], self.panel_rect)
        pygame.draw.rect(self.screen, self.COLORS['blue'], self.panel_rect, 2)

        # Botões
        buttons = [
            ("AUTOPATH", 10, self.COLORS['green'] if self.autopath_mode else self.COLORS['gray']),
            ("GRID", 120, self.COLORS['cyan'] if self.show_grid else self.COLORS['gray']),
            ("BRUSH +", 230, self.COLORS['orange']),
            ("BRUSH -", 330, self.COLORS['orange']),
            ("UNDO", 430, self.COLORS['yellow']),
            ("CLEAR", 530, self.COLORS['red']),
            ("SAVE", 630, self.COLORS['blue']),
        ]

        for text, x, color in buttons:
            btn_rect = pygame.Rect(x, panel_y + 10, 90, 30)
            pygame.draw.rect(self.screen, self.COLORS['bg_light'], btn_rect)
            pygame.draw.rect(self.screen, color, btn_rect, 2)
            btn_text = self.font_small.render(text, True, color)
            text_rect = btn_text.get_rect(center=btn_rect.center)
            self.screen.blit(btn_text, text_rect)
            self.button_rects[text] = btn_rect

        # Informações
        info_y = panel_y + 55
        info_texts = [
            f"Selected Tile: {self.selected_tile}",
            f"Brush Size: {self.brush_size}x{self.brush_size}",
            f"Total Tiles: {len(self.tiles)}",
            f"Map Size: {self.grid_width}x{self.grid_height}",
        ]

        for i, text in enumerate(info_texts):
            info = self.font_small.render(text, True, self.COLORS['light_gray'])
            self.screen.blit(info, (10, info_y + i * 20))

        # Instruções rápidas
        instr_y = panel_y + 140
        instr_title = self.font_small.render("QUICK CONTROLS:", True, self.COLORS['yellow'])
        self.screen.blit(instr_title, (10, instr_y))

        shortcuts = [
            "LMB: Paint | RMB: Erase",
            "1-9: Select tile | Space: Toggle Autopath",
            "Ctrl+Z: Undo | Ctrl+S: Save",
            "O: Open tileset | ESC: Exit"
        ]

        for i, shortcut in enumerate(shortcuts):
            instr = self.font_small.render(shortcut, True, self.COLORS['gray'])
            self.screen.blit(instr, (10, instr_y + 25 + i * 18))

    def draw_message(self):
        """Desenha mensagem temporária"""
        if self.message_timer > 0:
            self.message_timer -= 1

            # Fundo da mensagem
            msg_surf = self.font.render(self.message, True, self.COLORS['white'])
            msg_bg = pygame.Surface((msg_surf.get_width() + 20, msg_surf.get_height() + 10))
            msg_bg.fill(self.COLORS['black'])
            msg_bg.set_alpha(200)

            x = (self.screen_width - msg_bg.get_width()) // 2
            y = self.screen_height - 50

            self.screen.blit(msg_bg, (x, y))
            self.screen.blit(msg_surf, (x + 10, y + 5))

    def handle_events(self):
        """Processa eventos"""
        mouse_buttons = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        # Hover no grid
        if self.grid_rect and self.grid_rect.collidepoint(mouse_pos):
            grid_x = mouse_pos[0] // self.tile_size
            grid_y = mouse_pos[1] // self.tile_size
            self.hover_grid_pos = (grid_x, grid_y)

            # Paint com mouse
            if mouse_buttons[0] or mouse_buttons[2]:
                if mouse_buttons[0]:
                    self.paint_tile(grid_x, grid_y, self.selected_tile, False)
                elif mouse_buttons[2]:
                    self.paint_tile(grid_x, grid_y, 0, True)
        else:
            self.hover_grid_pos = None

        # Click na paleta
        if mouse_buttons[0] and self.hover_tile >= 0:
            self.selected_tile = self.hover_tile
            self.show_message(f"Tile {self.selected_tile} selecionado")

    def run(self):
        """Loop principal"""
        while self.running:
            dt = self.clock.tick(60)
            self.animation_counter += 1

            # Desenhar
            self.draw_background()
            self.draw_grid_area()
            self.draw_hover_effect()
            self.draw_palette()
            self.draw_controls_panel()
            self.draw_message()

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.autopath_mode = not self.autopath_mode
                        self.show_message(f"Autopath: {'ON' if self.autopath_mode else 'OFF'}")
                    elif event.key == pygame.K_g:
                        self.show_grid = not self.show_grid
                    elif event.key == pygame.K_o:
                        self.open_file_dialog()
                    elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.undo()
                    elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.save_map()
                    elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                       pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                        num = int(pygame.key.name(event.key))
                        if num - 1 < len(self.tiles):
                            self.selected_tile = num - 1
                            self.show_message(f"Tile {self.selected_tile} selecionado")
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self.brush_size = min(5, self.brush_size + 1)
                    elif event.key == pygame.K_MINUS:
                        self.brush_size = max(1, self.brush_size - 1)

                elif event.type == pygame.MOUSEWHEEL:
                    if self.tiles:
                        max_scroll = max(0, (len(self.tiles) // self.tiles_per_row) - 8)
                        self.palette_scroll = max(0, min(max_scroll,
                                                         self.palette_scroll - event.y))

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for btn_name, btn_rect in self.button_rects.items():
                        if btn_rect.collidepoint(event.pos):
                            if btn_name == "AUTOPATH":
                                self.autopath_mode = not self.autopath_mode
                            elif btn_name == "GRID":
                                self.show_grid = not self.show_grid
                            elif btn_name == "BRUSH +":
                                self.brush_size = min(5, self.brush_size + 1)
                            elif btn_name == "BRUSH -":
                                self.brush_size = max(1, self.brush_size - 1)
                            elif btn_name == "UNDO":
                                self.undo()
                            elif btn_name == "CLEAR":
                                self.clear_map()
                            elif btn_name == "SAVE":
                                self.save_map()
                            elif btn_name == "load_tileset":
                                self.open_file_dialog()
                            elif btn_name == "palette_up":
                                self.palette_scroll = max(0, self.palette_scroll - 1)
                            elif btn_name == "palette_down":
                                if self.tiles:
                                    max_scroll = max(0, (len(self.tiles) // self.tiles_per_row) - 8)
                                    self.palette_scroll = min(max_scroll, self.palette_scroll + 1)

            self.handle_events()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def save_map(self, filename=None):
        """Salva o mapa"""
        if filename is None:
            from tkinter import filedialog, Tk
            root = Tk()
            root.withdraw()
            filename = filedialog.asksaveasfilename(
                title="Salvar mapa como",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            root.destroy()

            if not filename:
                return

        map_data = {
            "version": "1.0",
            "tile_size": self.tile_size,
            "width": self.grid_width,
            "height": self.grid_height,
            "tileset": self.tileset_path,
            "tileset_name": self.current_tileset_name,
            "grid": self.map_grid,
            "autopath_enabled": self.autopath_mode
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, indent=2, ensure_ascii=False)
            self.show_message(f"Mapa salvo: {os.path.basename(filename)}")
        except Exception as e:
            self.show_message(f"Erro ao salvar: {e}")


# Executar
if __name__ == "__main__":
    editor = PMD2TileEditor(
        tile_size=32,
        grid_width=15,
        grid_height=12
    )
    editor.run()