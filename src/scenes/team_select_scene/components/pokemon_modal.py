# src/ui/pokemon_modal.py

import pygame
import math
import random
import unicodedata

from data.item_bag_catalog import item_bag_catalog
from src.scenes.team_select_scene.components.held_item_dropdown import HeldItemDropdown
from src.data.pokedex import Pokedex
from src.battle.effects.effect_factory import EffectFactory
from src.data.move_data import MoveData


TYPE_PT = {
    'normal': 'Normal', 'fire': 'Fogo', 'water': 'Agua',
    'electric': 'Eletrico', 'grass': 'Planta', 'ice': 'Gelo',
    'fighting': 'Lutador', 'poison': 'Venenoso', 'ground': 'Terra',
    'flying': 'Voador', 'psychic': 'Psiquico', 'bug': 'Inseto',
    'rock': 'Pedra', 'ghost': 'Fantasma', 'dragon': 'Dragao',
    'dark': 'Sombrio', 'steel': 'Aco', 'fairy': 'Fada',
}

TYPE_CHART = {
    'normal':   {'fighting': 2, 'ghost': 0},
    'fire':     {'water': 2, 'ground': 2, 'rock': 2,
                 'fire': 0.5, 'grass': 0.5, 'ice': 0.5, 'bug': 0.5,
                 'steel': 0.5, 'fairy': 0.5},
    'water':    {'electric': 2, 'grass': 2,
                 'fire': 0.5, 'water': 0.5, 'ice': 0.5, 'steel': 0.5},
    'electric': {'ground': 2,
                 'electric': 0.5, 'flying': 0.5, 'steel': 0.5},
    'grass':    {'fire': 2, 'ice': 2, 'poison': 2, 'flying': 2, 'bug': 2,
                 'water': 0.5, 'electric': 0.5, 'grass': 0.5, 'ground': 0.5},
    'ice':      {'fire': 2, 'fighting': 2, 'rock': 2, 'steel': 2,
                 'ice': 0.5},
    'fighting': {'flying': 2, 'psychic': 2, 'fairy': 2,
                 'bug': 0.5, 'rock': 0.5, 'dark': 0.5},
    'poison':   {'ground': 2, 'psychic': 2,
                 'grass': 0.5, 'fighting': 0.5, 'poison': 0.5,
                 'bug': 0.5, 'fairy': 0.5},
    'ground':   {'water': 2, 'grass': 2, 'ice': 2,
                 'poison': 0.5, 'rock': 0.5, 'electric': 0},
    'flying':   {'electric': 2, 'ice': 2, 'rock': 2,
                 'grass': 0.5, 'fighting': 0.5, 'bug': 0.5, 'ground': 0},
    'psychic':  {'bug': 2, 'ghost': 2, 'dark': 2,
                 'fighting': 0.5, 'psychic': 0.5},
    'bug':      {'fire': 2, 'flying': 2, 'rock': 2,
                 'grass': 0.5, 'fighting': 0.5, 'ground': 0.5},
    'rock':     {'water': 2, 'grass': 2, 'fighting': 2, 'ground': 2, 'steel': 2,
                 'normal': 0.5, 'fire': 0.5, 'poison': 0.5, 'flying': 0.5},
    'ghost':    {'ghost': 2, 'dark': 2,
                 'poison': 0.5, 'bug': 0.5, 'normal': 0, 'fighting': 0},
    'dragon':   {'ice': 2, 'dragon': 2, 'fairy': 2,
                 'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'grass': 0.5},
    'dark':     {'fighting': 2, 'bug': 2, 'fairy': 2,
                 'ghost': 0.5, 'dark': 0.5, 'psychic': 0},
    'steel':    {'fire': 2, 'fighting': 2, 'ground': 2,
                 'normal': 0.5, 'grass': 0.5, 'ice': 0.5, 'flying': 0.5,
                 'psychic': 0.5, 'bug': 0.5, 'rock': 0.5, 'dragon': 0.5,
                 'steel': 0.5, 'fairy': 0.5, 'poison': 0},
    'fairy':    {'poison': 2, 'steel': 2,
                 'fighting': 0.5, 'bug': 0.5, 'dark': 0.5, 'dragon': 0},
}


def _analyze_types(pokemon_types):
    all_atk = list(TYPE_CHART.keys())
    weak, resist, immune = [], [], []
    for atk in all_atk:
        mult = 1.0
        for t in pokemon_types:
            t_lower = t.lower()
            if t_lower in TYPE_CHART:
                mult *= TYPE_CHART[t_lower].get(atk, 1.0)
        if mult > 1.0:
            weak.append(atk)
        elif mult < 1.0 and mult > 0:
            resist.append(atk)
        elif mult == 0:
            immune.append(atk)
    return weak, resist, immune


def _sanitize(text):
    if text is None:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(text))
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


HELP_TEXT = {
    'stats': ("Stats Atuais",
              "Atributos calculados com Level, IVs, EVs e Natureza. "
              "HP = vida. ATAQUE = dano fisico. DEFESA = resistencia fisica. "
              "SP. ATAQUE = dano especial. SP. DEFESA = resistencia especial. "
              "VELOCIDADE = ordem de acao, velocidade de projeteis e "
              "velocidade de movimento no mapa."),
    'hp': ("HP (Hit Points)",
           "Pontos de vida. Quando chega a 0, o Pokemon desmaia."),
    'speed': ("Velocidade",
              "A Velocidade afeta tres coisas: 1) quem age primeiro em combate, "
              "2) a velocidade com que este Pokemon dispara projeteis, e "
              "3) a velocidade com que ele se move pelo mapa."),
    'nature': ("Natureza",
               "A Natureza da +10% em um atributo e -10% em outro. "
               "Natures neutras (Hardy, Docile, Serious, Bashful, Quirky) "
               "nao afetam nada."),
    'ivs': ("Valores Individuais (IVs)",
            "Cada IV vai de 0 a 31. IVs maiores geram stats maiores no Nivel 100. "
            "31 e perfeito. IVs sao definidos ao nascer/capturar e nunca mudam."),
    'evs': ("Esforco (EVs)",
            "EVs sao ganhos ao derrotar Pokemon. Cada 8 EVs concedem +1 ponto "
            "no atributo. Total maximo: 1020. Maximo por atributo: 504."),
    'xp': ("Experiencia",
           "Progresso rumo ao proximo nivel. Ganhe XP derrotando inimigos."),
    'happiness': ("Felicidade",
                  "Felicidade vai de 0 a 255. Aumenta com vitorias, level up e itens. "
                  "Alguns Pokemon evoluem com felicidade alta."),
    'type': ("Tipo",
             "O tipo define fraquezas e resistencias contra outros tipos em batalha."),
    'held_item': ("Item Segurado",
                  "Um Pokemon pode segurar 1 item. Itens podem dar bonus, curar "
                  "automaticamente ou evoluir o Pokemon."),
    'power': ("Poder + STAB",
              "Dano base do movimento. Valores maiores causam mais dano. "
              "Movimentos de status nao possuem Poder. "
              "STAB (Same Type Attack Bonus): se o tipo do movimento for "
              "igual a um dos tipos do Pokemon, ele ganha 50% de bonus de dano!"),
    'accuracy': ("Precisao",
                 "Chance percentual de acertar o alvo. "
                 "Movimentos com '--' nunca erram. "
                 "Precisoes baixas (abaixo de 75%) podem falhar muito."),
    'pp': ("PP (Power Points)",
           "Quantas vezes o movimento pode ser usado antes de esgotar. "
           "Recuperado com itens ou no Centro Pokemon."),
    'category': ("Categoria do Movimento",
                 "FISICO: usa ATAQUE vs DEFESA do alvo. "
                 "ESPECIAL: usa SP. ATAQUE vs SP. DEFESA do alvo. "
                 "STATUS: nao causa dano, apenas efeitos."),
    'gender': ("Sexo",
               "MACHO ou FEMEA. Alguns Pokemon nao tem sexo. "
               "Afeta ataques como Attract e evolucoes especificas."),
    'height': ("Altura",
               "Varia +-10% do padrao da especie. Apenas cosmetico."),
    'weight': ("Peso",
               "Varia +-10% do padrao. Afeta golpes como Heavy Slam e Low Kick."),
    'origin': ("Origem",
               "Como voce obteve este Pokemon: Inicial, Capturado, Presente, "
               "Trocado, Fossil, Ovo, Evolucao, Evento ou Migracao."),
    'location': ("Localizacao",
                 "Onde o Pokemon esta: no seu TIME de batalha ou na BOX do PC."),
    'moves_page': ("Movimentos",
                   "Sao os 4 golpes que o Pokemon usa em batalha. "
                   "Cada um tem tipo, categoria, poder, precisao e PP. "
                   "Dica: movimentos do mesmo tipo do Pokemon recebem STAB "
                   "(Same Type Attack Bonus) de +50% no dano."),
    'species': ("Especie",
                "O nome verdadeiro da especie. Nao muda, mesmo com apelido."),
    'nickname': ("Apelido",
                 "Nome personalizado dado pelo jogador. Se vazio, usa o nome da especie."),
    'id': ("ID Pokedex",
           "Numero do Pokemon na Pokedex nacional (1-151 para Kanto)."),
    'summary': ("Resumo do Pokemon",
                "Analise automatica baseada em stats base da especie, seus IVs, "
                "EVs, natureza, moveset e tipagem. Serve para entender rapidamente "
                "o papel do Pokemon no seu time. Clique no botao para expandir."),
}


class PokemonModal:
    TABS = [
        {'key': 'stats', 'label': 'STATS'},
        {'key': 'moves', 'label': 'MOVIMENTOS'},
        {'key': 'info',  'label': 'FICHA'},
    ]

    def __init__(self, game, unique_id):
        self.game = game
        self.unique_id = unique_id

        self.pokemon = self.game.player.get_pokemon_instance(unique_id)
        if not self.pokemon:
            raise ValueError(f"Pokémon com unique_id {unique_id} não encontrado")

        self.pokedex = Pokedex()
        self.move_data = MoveData()
        self.visible = True
        self.current_tab = 0
        self.confirmation_active = False

        self._last_window_size = None
        self.layout = {}
        self.fonts = {}

        self.scroll_y = 0.0
        self.max_scroll = 0

        self._hover_tab = -1
        self._mouse_virtual = None
        self._active_help = None
        self._help_zones = []

        self._summary_cache = None
        self._summary_signature = None
        self._summary_expanded = False
        self._summary_toggle_rect = None

        self.held_item_dropdown = HeldItemDropdown(x=0, y=0, width=280, max_visible=4)
        self.held_item_dropdown.on_select = self._on_held_item_selected
        self.held_item_dropdown.on_close = self._on_held_item_closed
        self._equip_button_rect = None
        self._remove_button_rect = None

        self.feedback_message = None
        self.feedback_timer = 0.0
        self.feedback_color = (255, 255, 255)

        self._cached_sprite = None
        self._cached_sprite_id = None
        self._cached_shiny = None

        self.particle_timer = 0
        self.particles = []

        self.C = {
            'bg_modal':      (16, 19, 26),
            'bg_panel':      (23, 27, 36),
            'bg_row':        (33, 38, 50),
            'bg_row_alt':    (37, 43, 56),
            'bg_title':      (36, 41, 54),
            'bg_track':      (18, 21, 28),
            'border_panel':  (56, 65, 88),
            'border_row':    (48, 56, 74),
            'border_light':  (78, 90, 120),
            'hover_border':  (255, 215, 0),
            'gold':          (218, 175, 90),
            'gold_bright':   (255, 215, 0),
            'blue':          (100, 150, 220),
            'green':         (100, 210, 120),
            'red':           (220, 90, 90),
            'orange':        (235, 150, 70),
            'purple':        (170, 120, 210),
            'text':          (240, 244, 250),
            'text_dim':      (160, 168, 185),
            'text_muted':    (110, 118, 135),
            'type_normal': (168, 168, 120), 'type_fire': (240, 128, 48),
            'type_water': (104, 144, 240), 'type_electric': (248, 208, 48),
            'type_grass': (120, 200, 80), 'type_ice': (152, 216, 216),
            'type_fighting': (192, 48, 40), 'type_poison': (160, 64, 160),
            'type_ground': (224, 192, 104), 'type_flying': (168, 144, 240),
            'type_psychic': (248, 88, 136), 'type_bug': (168, 184, 32),
            'type_rock': (184, 160, 56), 'type_ghost': (112, 88, 152),
            'type_dragon': (112, 56, 248), 'type_dark': (112, 88, 72),
            'type_steel': (184, 184, 208), 'type_fairy': (238, 153, 172),
            'iv_perfect': (255, 215, 0), 'iv_great': (80, 200, 80),
            'iv_good': (80, 150, 220), 'iv_median': (100, 130, 200),
            'iv_bad': (220, 100, 80), 'iv_very_bad': (180, 60, 60),
            'iv_horrible': (160, 80, 200),
        }

        self._setup_dimensions()
        self._update_held_items_list()

    NATURE_EFFECTS = {
        "Hardy": (None, None, "", ""), "Lonely": ("attack", "defense", "Atk", "Def"),
        "Brave": ("attack", "speed", "Atk", "Spd"),
        "Adamant": ("attack", "sp_attack", "Atk", "SpAtk"),
        "Naughty": ("attack", "sp_defense", "Atk", "SpDef"),
        "Bold": ("defense", "attack", "Def", "Atk"),
        "Relaxed": ("defense", "speed", "Def", "Spd"),
        "Impish": ("defense", "sp_attack", "Def", "SpAtk"),
        "Lax": ("defense", "sp_defense", "Def", "SpDef"),
        "Timid": ("speed", "attack", "Spd", "Atk"),
        "Hasty": ("speed", "defense", "Spd", "Def"),
        "Jolly": ("speed", "sp_attack", "Spd", "SpAtk"),
        "Naive": ("speed", "sp_defense", "Spd", "SpDef"),
        "Modest": ("sp_attack", "attack", "SpAtk", "Atk"),
        "Mild": ("sp_attack", "defense", "SpAtk", "Def"),
        "Quiet": ("sp_attack", "speed", "SpAtk", "Spd"),
        "Rash": ("sp_attack", "sp_defense", "SpAtk", "SpDef"),
        "Calm": ("sp_defense", "attack", "SpDef", "Atk"),
        "Gentle": ("sp_defense", "defense", "SpDef", "Def"),
        "Sassy": ("sp_defense", "speed", "SpDef", "Spd"),
        "Careful": ("sp_defense", "sp_attack", "SpDef", "SpAtk"),
        "Quirky": (None, None, "", ""),
    }

    @property
    def current_page(self): return self.current_tab

    @current_page.setter
    def current_page(self, v):
        self.current_tab = max(0, min(len(self.TABS) - 1, v))

    @property
    def total_pages(self): return len(self.TABS)

    def _tab_key(self): return self.TABS[self.current_tab]['key']

    # =================================================================
    # RESIZE / FONTS / LAYOUT
    # =================================================================
    def _check_resize(self):
        cur = (self.game.screen_manager.window_width,
               self.game.screen_manager.window_height)
        if cur != self._last_window_size:
            self._last_window_size = cur
            self._setup_dimensions()
            return True
        return False

    def _create_fonts(self, vh):
        base = max(12, int(vh * 0.021))
        self.fonts = {
            'hero':       pygame.font.Font(None, int(base * 2.0)),
            'title':      pygame.font.Font(None, int(base * 1.5)),
            'section':    pygame.font.Font(None, int(base * 1.28)),
            'move':       pygame.font.Font(None, int(base * 1.5)),
            'move_desc':  pygame.font.Font(None, int(base * 1.05)),
            'tab':        pygame.font.Font(None, int(base * 1.1)),
            'value':      pygame.font.Font(None, int(base * 1.05)),
            'summary':    pygame.font.Font(None, int(base * 1.02)),
            'disclaim':   pygame.font.Font(None, int(base * 0.85)),
            'label':      pygame.font.Font(None, int(base * 0.9)),
            'small':      pygame.font.Font(None, int(base * 0.85)),
            'tiny':       pygame.font.Font(None, int(base * 0.72)),
            'button':     pygame.font.Font(None, int(base * 1.0)),
            'tooltip_t':  pygame.font.Font(None, int(base * 1.15)),
            'tooltip_b':  pygame.font.Font(None, int(base * 0.95)),
        }

    def _setup_dimensions(self):
        ww = self.game.screen_manager.window_width
        wh = self.game.screen_manager.window_height

        self.width  = int(ww * 0.94)
        self.height = int(wh * 0.94)
        self.x = (ww - self.width) // 2
        self.y = (wh - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self._create_fonts(wh)
        pad = max(14, int(self.width * 0.016))

        cs = max(32, int(wh * 0.046))
        self.close_button = pygame.Rect(
            self.rect.right - cs - pad, self.rect.y + pad, cs, cs)

        sprite_size = int(self.width * 0.13)

        header_x = self.rect.x + pad
        header_y = self.rect.y + pad
        sprite_card = pygame.Rect(header_x, header_y, sprite_size, sprite_size)

        info_x = sprite_card.right + int(pad * 0.6)
        info_w = (self.rect.right - pad) - info_x

        text_w = info_w - 40
        if self._summary_expanded:
            summary_h = self._calc_summary_height(text_w)
        else:
            summary_h = 46

        name_area_h = 96
        header_h = name_area_h + summary_h + 18
        header_h = max(header_h, sprite_size)

        header = pygame.Rect(header_x, header_y, self.rect.width - pad * 2, header_h)
        info_card = pygame.Rect(info_x, header_y, info_w, header_h)

        self.layout['header'] = header
        self.layout['sprite_card'] = sprite_card
        self.layout['info_card'] = info_card

        tabs_y = header.bottom + int(self.height * 0.014)
        tabs_h = max(38, int(self.height * 0.055))
        tabs_rect = pygame.Rect(
            self.rect.x + pad, tabs_y,
            self.rect.width - pad * 2, tabs_h)
        self.layout['tabs_rect'] = tabs_rect

        n = max(1, len(self.TABS))
        gap = max(6, int(self.width * 0.006))
        tab_w = (tabs_rect.width - (n - 1) * gap) // n
        self.layout['tabs'] = [
            pygame.Rect(tabs_rect.x + i * (tab_w + gap),
                        tabs_rect.y, tab_w, tabs_rect.height)
            for i in range(n)
        ]

        footer_h = max(40, int(self.height * 0.06))
        footer_y = self.rect.bottom - pad - footer_h
        bw = max(150, int(self.width * 0.16))
        gap_b = max(10, int(self.width * 0.012))
        total = bw * 2 + gap_b
        bx = self.rect.centerx - total // 2
        self.layout['action_btn']  = pygame.Rect(bx, footer_y, bw, footer_h)
        self.layout['release_btn'] = pygame.Rect(bx + bw + gap_b, footer_y, bw, footer_h)
        self.action_button  = self.layout['action_btn']
        self.release_button = self.layout['release_btn']

        self.prev_page_button = pygame.Rect(0, 0, 1, 1)
        self.next_page_button = pygame.Rect(0, 0, 1, 1)

        content_top = tabs_rect.bottom + int(self.height * 0.012)
        content_bottom = footer_y - int(self.height * 0.012)
        content = pygame.Rect(
            self.rect.x + pad, content_top,
            self.rect.width - pad * 2 - 14,
            content_bottom - content_top)
        self.layout['content'] = content
        self.layout['scrollbar_x'] = content.right + 6

        cw = max(110, int(self.width * 0.11))
        ch = max(36, int(self.height * 0.052))
        cgap = max(12, int(self.width * 0.016))
        cy = self.rect.centery + int(self.height * 0.05)
        cx = self.rect.centerx - (cw * 2 + cgap) // 2
        self.confirm_yes_button = pygame.Rect(cx, cy, cw, ch)
        self.confirm_no_button  = pygame.Rect(cx + cw + cgap, cy, cw, ch)

        self.scroll_y = 0
        self._recompute_scroll()

    def _recompute_scroll(self):
        cr = self.layout.get('content')
        if not cr:
            self.max_scroll = 0
            return
        vh = max(self._virtual_height(), cr.height)
        self.max_scroll = max(0, vh - cr.height)
        self.scroll_y = max(0.0, min(float(self.max_scroll), float(self.scroll_y)))

    def _virtual_height(self):
        key = self._tab_key()
        if key == 'stats':
            return 720
        if key == 'moves':
            return 360
        if key == 'info':
            return 500
        return 500

    def _calc_summary_height(self, avail_w):
        try:
            paragraphs = self._generate_summary()
        except Exception:
            return 100

        header_h = 36 + 8

        disclaim_font = self.fonts['disclaim']
        disclaim = ("Esse resumo e gerado com base nos dados do seu Pokemon e "
                    "pode nao representar fielmente suas funcoes em gameplay.")
        disclaim_lines = self._wrap_text(disclaim, disclaim_font, avail_w)
        disclaim_h = len(disclaim_lines) * (disclaim_font.get_height() + 2) + 8

        para_font = self.fonts['summary']
        para_line_h = para_font.get_height() + 4

        total = header_h + disclaim_h

        for idx, segs in enumerate(paragraphs):
            if idx > 0:
                total += 10
            lines = self._wrap_segments(segs, para_font, avail_w)
            total += len(lines) * para_line_h

        return total

    # =================================================================
    # GERACAO DO RESUMO
    # =================================================================
    def _generate_summary(self):
        p = self.pokemon
        sig = (
            p.level,
            tuple(sorted(p.ivs.items())),
            tuple(sorted(p.evs.items())),
            tuple(m.name for m in p.moves),
            p.nature,
            tuple(p.types),
        )
        if sig == self._summary_signature:
            return self._summary_cache

        C = self.C
        base = p.base_stats
        ivs = p.ivs
        evs = p.evs
        moves = p.moves

        def norm(v, cap=130):
            return min(1.0, v / cap)

        base_hp  = norm(base['hp'], 120)
        base_atk = norm(base['attack'])
        base_def = norm(base['defense'])
        base_spa = norm(base['special_attack'])
        base_spd = norm(base['special_defense'])
        base_spe = norm(base['speed'])

        bulk = (base_hp + base_def + base_spd) / 3
        off_phys = base_atk
        off_spec = base_spa
        offense = max(off_phys, off_spec)
        speed = base_spe

        stat_names = {
            'hp': 'HP', 'attack': 'Ataque', 'defense': 'Defesa',
            'special_attack': 'Ataque Especial',
            'special_defense': 'Defesa Especial', 'speed': 'Velocidade',
        }

        # ---- PARAGRAFO 1: Perfil + Tipagem ----
        para1 = []

        profile_parts = []
        if speed > 0.7 and offense > 0.65:
            profile_parts.append("um atacante veloz")
        elif speed < 0.4 and bulk > 0.55:
            profile_parts.append("um tanque lento")
        elif bulk > 0.6 and offense < 0.5:
            profile_parts.append("um tanque defensivo")
        elif offense > 0.7:
            profile_parts.append("um atacante poderoso")
        elif bulk > 0.55:
            profile_parts.append("um Pokemon resistente")
        elif speed > 0.65:
            profile_parts.append("um Pokemon agil")
        else:
            profile_parts.append("um Pokemon equilibrado")

        details = []
        if speed > 0.75:
            details.append("se destaca pela alta Velocidade")
        elif speed < 0.35:
            details.append("tem Velocidade muito baixa")
        if off_phys > 0.65 and off_phys >= off_spec:
            details.append("Ataque fisico acima da media")
        if off_spec > 0.65 and off_spec > off_phys:
            details.append("Ataque Especial acima da media")
        if bulk > 0.65:
            details.append("boa resistencia fisica e especial")
        elif bulk < 0.3:
            details.append("defesas frageis")

        p1 = f"{p.name} e {', '.join(profile_parts)}"
        if details:
            p1 += ", que " + " e ".join(details)
        p1 += "."
        para1.append((_sanitize(p1) + " ", C['text']))

        weak, resist, immune = _analyze_types(p.types)
        n_weak = len(weak)
        n_res = len(resist)

        if n_weak == 0:
            weak_txt = "nenhuma fraqueza"
        elif n_weak == 1:
            weak_txt = "apenas 1 fraqueza"
        elif n_weak <= 3:
            weak_txt = "poucas fraquezas"
        elif n_weak <= 4:
            weak_txt = "uma quantidade moderada de fraquezas"
        else:
            weak_txt = "varias fraquezas"

        if n_res == 0:
            res_txt = "nenhuma resistencia"
        elif n_res == 1:
            res_txt = "1 resistencia"
        elif n_res <= 3:
            res_txt = "poucas resistencias"
        else:
            res_txt = "varias resistencias"

        if n_weak <= 2 and n_res >= 3:
            concl = ", o que faz dele uma opcao muito segura no geral."
        elif n_weak <= 2:
            concl = ", o que faz dele uma opcao segura no geral."
        elif n_weak <= 4 and n_res >= 3:
            concl = ", o que ainda faz dele uma opcao razoavel."
        elif n_weak <= 4:
            concl = ", o que faz dele uma boa opcao no geral."
        else:
            concl = ", entao tome cuidado ao enfrentar esses tipos."

        para1.append(("Do tipo ", C['text']))
        for i, t in enumerate(p.types):
            if i > 0:
                para1.append((" / ", C['text_dim']))
            pt = TYPE_PT.get(t.lower(), t.capitalize())
            para1.append((_sanitize(pt), C['gold']))
        para1.append((f", possui {weak_txt} e {res_txt}{concl}", C['text']))

        # ---- PARAGRAFO 2: Fraquezas/Resistencias + Base vs IV + EVs + Moveset ----
        para2 = []

        if weak:
            para2.append(("Fraquezas: ", C['red']))
            for i, w in enumerate(weak):
                if i > 0:
                    para2.append((", ", C['text_dim']))
                para2.append((_sanitize(TYPE_PT.get(w, w.capitalize())), C['red']))
            para2.append((". ", C['text']))

        if resist:
            para2.append(("Resiste: ", C['green']))
            for i, r in enumerate(resist):
                if i > 0:
                    para2.append((", ", C['text_dim']))
                para2.append((_sanitize(TYPE_PT.get(r, r.capitalize())), C['green']))
            para2.append((". ", C['text']))

        if immune:
            para2.append(("Imune a: ", C['text']))
            for i, im in enumerate(immune):
                if i > 0:
                    para2.append((", ", C['text_dim']))
                para2.append((_sanitize(TYPE_PT.get(im, im.capitalize())), C['text']))
            para2.append((". ", C['text']))

        if not resist and not immune and n_weak <= 2:
            para2.append(("Sem resistencias ou imunidades relevantes. ", C['text']))

        best_base_key = max(base, key=base.get)
        best_base_val = base[best_base_key]
        p3_parts = []
        if best_base_val >= 90:
            p3_parts.append(
                f"Naturalmente, a especie se sobressai em "
                f"{stat_names[best_base_key]} (base {best_base_val})."
            )
        if ivs.get(best_base_key, 0) >= 25:
            p3_parts.append(
                f"Otimo: o IV desse atributo tambem e alto "
                f"({ivs[best_base_key]}/31), entao esse e um ponto forte consolidado."
            )
        elif ivs.get(best_base_key, 0) <= 10:
            p3_parts.append(
                f"Porem, o IV de {stat_names[best_base_key]} esta baixo "
                f"({ivs[best_base_key]}/31) para o potencial da especie."
            )
        for k in ['hp', 'attack', 'defense', 'special_attack',
                  'special_defense', 'speed']:
            if k == best_base_key:
                continue
            if base.get(k, 0) >= 90 and ivs.get(k, 0) <= 8:
                p3_parts.append(
                    f"Atencao: IV de {stat_names[k]} muito baixo ({ivs[k]}/31), "
                    f"mas o stat base da especie e {base[k]} - "
                    f"ele ainda sera util por natureza."
                )
                break
        if p3_parts:
            para2.append((_sanitize(" ".join(p3_parts)) + " ", C['text']))

        ev_sorted = sorted(evs.items(), key=lambda x: -x[1])
        top_evs = [(k, v) for k, v in ev_sorted if v > 30][:2]
        if top_evs:
            ev_list = " e ".join([f"{stat_names[k]} ({v} EV)" for k, v in top_evs])
            para2.append((_sanitize(
                f"Voce esta desenvolvendo principalmente {ev_list}. "
            ), C['text']))
        else:
            para2.append((_sanitize(
                "Este Pokemon ainda nao tem EVs treinados. "
                "Derrote inimigos para desenvolve-lo. "
            ), C['text']))

        # ===== MOVESET — analise detalhada + sinergia com stats =====
        n_phys = n_spec = n_stat = 0
        total = len(moves) if moves else 0

        if moves:
            n_phys = sum(1 for m in moves
                         if getattr(m, 'power', 0) > 0 and m.category == 'physical')
            n_spec = sum(1 for m in moves
                         if getattr(m, 'power', 0) > 0 and m.category == 'special')
            n_stat = sum(1 for m in moves if getattr(m, 'power', 0) == 0)

            if n_stat == total:
                style = "puramente de suporte (todos os movimentos sao de status)"
            elif n_stat == 0:
                if n_phys == 0:
                    style = f"de atacante especial puro ({n_spec} especiais)"
                elif n_spec == 0:
                    style = f"de atacante fisico puro ({n_phys} fisicos)"
                elif n_phys == n_spec:
                    style = f"de atacante misto ({n_phys} fisicos e {n_spec} especiais)"
                elif n_phys > n_spec:
                    style = (f"de atacante misto com foco fisico "
                             f"({n_phys} fisicos, {n_spec} especiais)")
                else:
                    style = (f"de atacante misto com foco especial "
                             f"({n_spec} especiais, {n_phys} fisicos)")
            elif n_stat * 2 >= total:
                if n_phys == 0 and n_spec == 0:
                    style = "puramente de suporte"
                elif n_phys > 0 and n_spec == 0:
                    style = (f"de suporte com 1 ataque fisico "
                             f"({n_stat} status, {n_phys} fisico)")
                elif n_spec > 0 and n_phys == 0:
                    style = (f"de suporte com 1 ataque especial "
                             f"({n_stat} status, {n_spec} especial)")
                elif n_phys == n_spec:
                    style = (f"de suporte equilibrado "
                             f"({n_stat} status, {n_phys} fisico e {n_spec} especial)")
                elif n_phys > n_spec:
                    style = (f"de suporte com foco fisico "
                             f"({n_stat} status, {n_phys} fisicos, {n_spec} especial)")
                else:
                    style = (f"de suporte com foco especial "
                             f"({n_stat} status, {n_spec} especiais, {n_phys} fisico)")
            elif n_stat == 1:
                if n_phys == 3:
                    style = "de atacante fisico com 1 golpe de suporte"
                elif n_spec == 3:
                    style = "de atacante especial com 1 golpe de suporte"
                elif n_phys == 2 and n_spec == 1:
                    style = "de atacante fisico com apoio especial e 1 suporte"
                elif n_spec == 2 and n_phys == 1:
                    style = "de atacante especial com apoio fisico e 1 suporte"
                else:
                    style = "equilibrado com 1 golpe de suporte"
            elif n_phys == 2 and n_spec == 2:
                style = "de atacante misto (2 fisicos e 2 especiais)"
            else:
                style = (f"misto ({n_phys} fisicos, {n_spec} especiais, "
                         f"{n_stat} status)")

            para2.append((_sanitize(f"Seu moveset esta {style}."), C['text']))

            if n_phys > 0 or n_spec > 0:
                best_off = "fisico" if off_phys > off_spec else "especial"
                matches = ((best_off == "fisico" and n_phys >= n_spec) or
                           (best_off == "especial" and n_spec >= n_phys))
                mismatch = ((best_off == "fisico" and n_phys == 0) or
                            (best_off == "especial" and n_spec == 0))

                if mismatch:
                    para2.append((_sanitize(
                        f" Porem, o stat ofensivo principal e {best_off.upper()}, "
                        f"e nenhum movimento atual aproveita isso. "
                        f"Considere ensinar golpes de {best_off}."
                    ), C['gold']))
                elif matches and (n_phys + n_spec) >= 2:
                    para2.append((_sanitize(
                        f" Boa sinergia: o moveset combina com o stat "
                        f"ofensivo principal ({best_off})."
                    ), C['green']))
        else:
            para2.append((_sanitize("Este Pokemon ainda nao tem movimentos equipados."),
                          C['text']))

        # =================================================================
        # PARAGRAFO 2.5: NATUREZA vs BUILD (base + moves + EVs)
        # =================================================================
        para_nature = []
        nature = p.nature
        eff = self.NATURE_EFFECTS.get(nature, (None, None, "", ""))

        if eff[0] is None:
            para_nature.append((_sanitize(
                f"A natureza {nature} e neutra: nao altera nenhum atributo. "
                f"Funciona como um coringa que nao penaliza nada."
            ), C['text']))
        else:
            boost_key, reduce_key = eff[0], eff[1]
            boost_pt, reduce_pt = eff[2], eff[3]

            # ---------------------------------------------------------
            # Prioridade de cada stat = base + moves + EVs
            # ---------------------------------------------------------
            max_ev = max(evs.values()) if evs else 0
            denom_moves = max(1, total)

            def _priority(stat_key):
                # Fonte 1: stat base da especie (normalizado)
                if stat_key == 'hp':
                    base_sc = min(1.0, base.get('hp', 0) / 120)
                else:
                    base_sc = min(1.0, base.get(stat_key, 0) / 130)

                # Fonte 2: moveset atual
                move_sc = 0.0
                if stat_key == 'attack' and n_phys > 0:
                    move_sc = n_phys / denom_moves
                elif stat_key == 'special_attack' and n_spec > 0:
                    move_sc = n_spec / denom_moves
                elif stat_key in ('defense', 'special_defense') and n_stat > 0:
                    # Suporte (ex: Reflect, Light Screen) valoriza defesas
                    move_sc = 0.15 * (n_stat / denom_moves)
                elif stat_key == 'speed' and n_stat > 0:
                    # Status geralmente se beneficia de agir primeiro
                    move_sc = 0.20

                # Fonte 3: EVs investidos
                if max_ev > 0:
                    ev_sc = evs.get(stat_key, 0) / max_ev
                else:
                    ev_sc = 0.0

                # Pesos: base 45% + moves 35% + EVs 20%
                return base_sc * 0.45 + move_sc * 0.35 + ev_sc * 0.20

            priorities = {k: _priority(k) for k in
                          ['hp', 'attack', 'defense', 'special_attack',
                           'special_defense', 'speed']}

            sorted_stats = sorted(priorities.items(), key=lambda x: -x[1])
            top_3 = {k for k, _ in sorted_stats[:3]}

            boost_score = priorities[boost_key]
            reduce_score = priorities[reduce_key]

            boost_helps = (boost_key in top_3) or (boost_score >= 0.5)
            reduce_hurts = (reduce_key in top_3) or (reduce_score >= 0.6)

            # Fontes que apoiam cada stat (para explicar ao jogador)
            def _sources(stat_key):
                srcs = []
                if stat_key == 'attack' and n_phys > 0:
                    srcs.append(f"{n_phys} golpe(s) fisico(s)")
                if stat_key == 'special_attack' and n_spec > 0:
                    srcs.append(f"{n_spec} golpe(s) especial(is)")
                ev_val = evs.get(stat_key, 0)
                if ev_val > 30:
                    srcs.append(f"{ev_val} EV")
                bv = base.get(stat_key, 0)
                if bv >= 90:
                    srcs.append(f"base {bv}")
                return srcs

            # ---------------------------------------------------------
            # Monta a mensagem
            # ---------------------------------------------------------
            boost_srcs = _sources(boost_key)
            reduce_srcs = _sources(reduce_key)

            boost_extra = f" ({', '.join(boost_srcs)})" if boost_srcs else ""
            reduce_extra = f" ({', '.join(reduce_srcs)})" if reduce_srcs else ""

            if boost_helps and not reduce_hurts:
                msg = (f"A natureza {nature} da +10% em {boost_pt}{boost_extra} "
                       f"e -10% em {reduce_pt}, o que combina bem com a build "
                       f"atual.")
                color = C['green']
            elif boost_helps and reduce_hurts:
                msg = (f"A natureza {nature} da +10% em {boost_pt}{boost_extra} "
                       f"e -10% em {reduce_pt}{reduce_extra}. O bonus ajuda, "
                       f"mas a penalidade tambem prejudica um stat que voce usa.")
                color = C['gold']
            elif (not boost_helps) and reduce_hurts:
                msg = (f"A natureza {nature} da +10% em {boost_pt} e -10% em "
                       f"{reduce_pt}{reduce_extra}. O bonus nao ajuda muito, e "
                       f"a penalidade atrapalha um stat importante. Considere "
                       f"trocar a natureza.")
                color = C['red']
            else:
                msg = (f"A natureza {nature} da +10% em {boost_pt} e -10% em "
                       f"{reduce_pt}. Neutra para a build atual: nem ajuda "
                       f"nem atrapalha.")
                color = C['text']

            para_nature.append((_sanitize(msg), color))

        # ---- PARAGRAFO 3: Dica Final ----
        is_tank = bulk > 0.55 and offense < 0.65
        is_fragile = bulk < 0.4
        is_offensive = offense > 0.65
        is_fast = speed > 0.65
        is_slow = speed < 0.4

        if is_tank and not is_offensive:
            tip = ("Dica final: este Pokemon e um bom tanque. "
                   "Coloque-o na frente dos bosses para absorver os golpes "
                   "enquanto seus outros Pokemon atacam com seguranca.")
        elif is_fragile and is_offensive:
            tip = ("Dica final: seu Pokemon e fragil mas tem grande poder ofensivo. "
                   "Proteja-o atras de um tanque ou posicione-o em locais "
                   "estrategicos para atacar sem ser atingido.")
        elif is_fast and is_offensive:
            tip = ("Dica final: Pokemon rapido e ofensivo. Use-o para flanquear "
                   "inimigos e eliminar alvos rapidamente antes que eles revidem.")
        elif is_tank and is_slow:
            tip = ("Dica final: tanque lento. Ele nao vai alcancar inimigos rapidos, "
                   "mas segura a linha de frente muito bem. Use-o para bloquear "
                   "passagens e proteger aliados.")
        elif bulk > 0.5 and offense > 0.5:
            tip = ("Dica final: Pokemon equilibrado. Pode atuar tanto na linha "
                   "de frente quanto como atacante secundario.")
        elif is_fragile and is_fast:
            tip = ("Dica final: rapido mas fragil. Use-o para atacar e recuar "
                   "rapidamente, aproveitando a velocidade.")
        else:
            tip = ("Dica final: Pokemon sem especializacao clara. Experimente "
                   "diferentes posicoes para descobrir onde ele se encaixa melhor.")

        para3 = [(_sanitize(tip), C['gold_bright'])]

        self._summary_cache = [para1, para2, para_nature, para3]
        self._summary_signature = sig
        return self._summary_cache

    # =================================================================
    # HELPERS DE DESENHO
    # =================================================================
    def _rounded(self, surf, color, rect, radius=8, border=0, border_color=None):
        pygame.draw.rect(surf, color, rect, border_radius=radius)
        if border > 0 and border_color:
            pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

    def _wrap_text(self, text, font, max_w):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines or [""]

    def _segments_to_words(self, segments):
        words = []
        for text, color in segments:
            parts = text.split(' ')
            for i, p in enumerate(parts):
                if p:
                    words.append((p, color))
                if i < len(parts) - 1:
                    words.append((' ', color))
        return words

    def _wrap_segments(self, segments, font, max_w):
        words = self._segments_to_words(segments)
        lines, cur = [], []
        cur_w = 0
        space_w = font.size(' ')[0]

        for word, color in words:
            if word == ' ':
                if cur:
                    cur.append((' ', color))
                    cur_w += space_w
                continue
            w = font.size(word)[0]
            if cur_w + w > max_w and cur:
                while cur and cur[-1][0] == ' ':
                    cur.pop(); cur_w -= space_w
                lines.append(cur)
                cur = [(word, color)]
                cur_w = w
            else:
                cur.append((word, color))
                cur_w += w
        if cur:
            while cur and cur[-1][0] == ' ':
                cur.pop()
            lines.append(cur)
        return lines

    def _register_help(self, rect, help_key, space='virtual'):
        self._help_zones.append({
            'rect': pygame.Rect(rect),
            'key': help_key,
            'space': space,
        })

    def _is_field_hovered(self, rect, space='virtual'):
        mx, my = pygame.mouse.get_pos()
        if space == 'screen':
            return rect.collidepoint(mx, my)
        cr = self.layout.get('content')
        if not cr or not cr.collidepoint(mx, my):
            return False
        vx = mx - cr.x
        vy = my - cr.y + int(self.scroll_y)
        return rect.collidepoint(vx, vy)

    def _draw_panel(self, surf, x, y, w, h, title, accent=None, help_key=None):
        r = pygame.Rect(x, y, w, h)
        accent = accent or self.C['gold']

        pygame.draw.rect(surf, self.C['bg_panel'], r, border_radius=10)
        pygame.draw.rect(surf, self.C['border_panel'], r, 2, border_radius=10)
        pygame.draw.line(surf, (78, 90, 120),
                         (r.x + 12, r.y + 3), (r.right - 12, r.y + 3), 1)

        tb_h = 34
        tb = pygame.Rect(r.x + 8, r.y + 8, r.width - 16, tb_h)
        pygame.draw.rect(surf, self.C['bg_title'], tb, border_radius=6)
        pygame.draw.rect(surf, accent,
                         (tb.x, tb.y + 3, 4, tb.height - 6), border_radius=2)

        font = self.fonts['section']
        txt = font.render(_sanitize(title).upper(), True, accent)
        surf.blit(txt, (tb.x + 14, tb.centery - txt.get_height() // 2))

        if help_key:
            self._register_help(tb, help_key)
            if self._is_field_hovered(tb):
                pygame.draw.rect(surf, self.C['hover_border'], tb, 2, border_radius=6)

        inner = pygame.Rect(
            r.x + 10, tb.bottom + 8,
            r.width - 20, r.bottom - tb.bottom - 18)
        return inner

    def _draw_stat_row(self, surf, rect, name, value, max_val,
                       value_text=None, show_bar=True, accent_override=None,
                       help_key=None, rank_reserved=0):
        pygame.draw.rect(surf, self.C['bg_row'], rect, border_radius=6)
        pygame.draw.rect(surf, self.C['border_row'], rect, 1, border_radius=6)

        if accent_override:
            accent = accent_override
        elif show_bar and max_val > 0:
            pct = value / max_val
            if pct > 0.7: accent = self.C['green']
            elif pct > 0.4: accent = self.C['gold']
            else: accent = self.C['red']
        else:
            accent = self.C['border_light']

        pygame.draw.rect(surf, accent,
                         (rect.x + 1, rect.y + 4, 3, rect.height - 8),
                         border_radius=2)

        if help_key:
            self._register_help(rect, help_key)
            if self._is_field_hovered(rect):
                pygame.draw.rect(surf, self.C['hover_border'], rect, 2, border_radius=6)

        n = self.fonts['small'].render(name, True, self.C['text_dim'])
        surf.blit(n, (rect.x + 14, rect.centery - n.get_height() // 2))

        if value_text is None:
            value_text = str(value)
        v = self.fonts['value'].render(value_text, True, accent)
        vx = rect.x + int(rect.width * 0.30)
        surf.blit(v, (vx, rect.centery - v.get_height() // 2))

        if show_bar and max_val > 0:
            bx = rect.x + int(rect.width * 0.42)
            bw = rect.right - bx - rank_reserved - 12
            if bw > 20:
                bh = 10
                by = rect.centery - bh // 2
                pygame.draw.rect(surf, self.C['bg_track'],
                                 (bx, by, bw, bh), border_radius=5)
                pct = min(1.0, value / max_val)
                if pct > 0:
                    pygame.draw.rect(surf, accent,
                                     (bx, by, int(bw * pct), bh), border_radius=5)
                pygame.draw.rect(surf, self.C['border_light'],
                                 (bx, by, bw, bh), 1, border_radius=5)

    def _kv_block(self, surf, x, y, w, label, value, color=None,
                  help_key=None, small_value=False):
        color = color or self.C['text']
        lab = self.fonts['small'].render(_sanitize(label).upper(),
                                          True, self.C['text_muted'])
        f = self.fonts['small'] if small_value else self.fonts['value']
        val = f.render(_sanitize(value), True, color)
        total_h = lab.get_height() + val.get_height() + 6
        block = pygame.Rect(x, y, w, total_h)

        if help_key:
            self._register_help(block, help_key)
            if self._is_field_hovered(block):
                pygame.draw.rect(surf, self.C['hover_border'],
                                 block.inflate(6, 4), 2, border_radius=6)

        surf.blit(lab, (x, y))
        surf.blit(val, (x, y + lab.get_height() + 2))
        return y + lab.get_height() + val.get_height() + 4

    def _type_badge(self, surf, rect, type_name):
        tc = self.C.get(f"type_{type_name.lower()}", (128, 128, 128))
        pygame.draw.rect(surf, tc, rect, border_radius=5)
        pygame.draw.rect(surf, (0, 0, 0, 60), rect, 1, border_radius=5)
        pygame.draw.line(surf, tuple(min(255, c + 40) for c in tc),
                         (rect.x + 4, rect.y + 2), (rect.right - 4, rect.y + 2), 1)
        t = self.fonts['small'].render(_sanitize(type_name).upper(),
                                       True, (255, 255, 255))
        surf.blit(t, t.get_rect(center=rect.center))

    def _draw_star(self, surf, cx, cy, size, color):
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            r = size if i % 2 == 0 else size * 0.45
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (255, 240, 180), pts, 1)

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if not self.visible:
            return None

        self._check_resize()

        if self.held_item_dropdown.is_visible():
            if self.held_item_dropdown.handle_event(event):
                return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._switch_tab(-1); return None
            if event.key == pygame.K_RIGHT:
                self._switch_tab(1); return None
            if event.key == pygame.K_ESCAPE:
                self.visible = False
                self.confirmation_active = False
                return "close"

        if event.type == pygame.MOUSEWHEEL:
            if self.max_scroll > 0:
                mx, my = pygame.mouse.get_pos()
                cr = self.layout['content']
                if cr.collidepoint(mx, my):
                    self.scroll_y -= event.y * 60
                    self.scroll_y = max(0.0, min(float(self.max_scroll),
                                                  float(self.scroll_y)))
            return None

        if event.type == pygame.MOUSEMOTION:
            self._hover_tab = -1
            for i, r in enumerate(self.layout.get('tabs', [])):
                if r.collidepoint(event.pos):
                    self._hover_tab = i
                    break
            self._update_help_hover(event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                self.confirmation_active = False
                return "close"

            if (self._summary_toggle_rect and
                    self._summary_toggle_rect.collidepoint(event.pos)):
                self._summary_expanded = not self._summary_expanded
                self._setup_dimensions()
                return None

            for i, tab_rect in enumerate(self.layout.get('tabs', [])):
                if tab_rect.collidepoint(event.pos):
                    if i != self.current_tab:
                        self.current_tab = i
                        self.scroll_y = 0
                        self._recompute_scroll()
                    return None

            if self.confirmation_active:
                if self.confirm_yes_button.collidepoint(event.pos):
                    self.confirmation_active = False
                    if self._can_release():
                        return "release_confirm"
                    return None
                if self.confirm_no_button.collidepoint(event.pos):
                    self.confirmation_active = False
                    return None
                return None

            if self.action_button.collidepoint(event.pos):
                if not self.pokemon.is_in_team and len(self.game.player.team) >= 6:
                    return None
                return "action"

            if self.release_button.collidepoint(event.pos):
                if self._can_release():
                    self.confirmation_active = True
                return None

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                self.confirmation_active = False
                return "close"

            if self._handle_held_item_click(event):
                return None

        return None

    def _update_help_hover(self, mouse_pos):
        self._active_help = None

        for zone in reversed(self._help_zones):
            if zone.get('space', 'virtual') == 'screen':
                if zone['rect'].collidepoint(mouse_pos):
                    self._active_help = zone['key']
                    return

        cr = self.layout.get('content')
        if not cr or not cr.collidepoint(mouse_pos):
            return
        vx = mouse_pos[0] - cr.x
        vy = mouse_pos[1] - cr.y + self.scroll_y
        self._mouse_virtual = (vx, vy)
        for zone in reversed(self._help_zones):
            if zone.get('space', 'virtual') == 'virtual':
                if zone['rect'].collidepoint(vx, vy):
                    self._active_help = zone['key']
                    return

    def _switch_tab(self, delta):
        n = self.total_pages
        self.current_tab = (self.current_tab + delta) % n
        self.scroll_y = 0
        self._recompute_scroll()

    # =================================================================
    # REGRAS / ITEM
    # =================================================================
    def _can_release(self):
        tt, tb = len(self.game.player.team), len(self.game.player.pc_box)
        tp = tt + tb
        if tp <= 1: return False
        if self.pokemon.is_in_team and tt == 1 and tb > 0: return True
        if self.pokemon.is_in_team and tt > 1: return True
        if not self.pokemon.is_in_team and tp > 1: return True
        return False

    def _get_release_warning(self):
        tt, tb = len(self.game.player.team), len(self.game.player.pc_box)
        if self.pokemon.is_in_team and tt == 1 and tb > 0:
            return "Ultimo Pokemon do time!"
        return None

    def _update_held_items_list(self):
        held = self.game.player.bag.get_held_items()
        items = []
        cur = self.pokemon.held_item
        for it in held:
            if cur and it["id"] == cur: continue
            if it["quantity"] <= 0: continue
            items.append({"id": it["id"], "data": it["data"], "quantity": it["quantity"]})
        self.held_item_dropdown.set_items(items)

    def _on_held_item_selected(self, item):
        ok, _ = self.game.player.bag.equip_held_item(self.pokemon, item["id"])
        if ok:
            self._update_held_items_list()
            self._remove_button_rect = None
            self._equip_button_rect = None

    def _on_held_item_closed(self):
        pass

    def _handle_held_item_click(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.held_item_dropdown.is_visible():
            return self.held_item_dropdown.handle_event(event)

        cr = self.layout['content']
        vpos = (event.pos[0] - cr.x, event.pos[1] - cr.y + self.scroll_y)

        if self._remove_button_rect and self._remove_button_rect.collidepoint(vpos):
            ok, _ = self.game.player.bag.unequip_held_item(self.pokemon)
            if ok:
                self._update_held_items_list()
                self._remove_button_rect = None
                self._equip_button_rect = None
                self.game.player.auto_save()
            return True

        if self._equip_button_rect and self._equip_button_rect.collidepoint(vpos):
            held = self.game.player.bag.get_held_items()
            avail = [it for it in held if it["quantity"] > 0]
            if self.pokemon.held_item:
                avail = [it for it in avail if it["id"] != self.pokemon.held_item]
            if avail:
                self.held_item_dropdown.set_screen_height(
                    self.game.screen_manager.window_height)
                self.held_item_dropdown.show()
                self.held_item_dropdown.set_items([
                    {"id": it["id"], "data": it["data"], "quantity": it["quantity"]}
                    for it in avail
                ])
            return True
        return False

    # =================================================================
    # HELPERS DE VALOR
    # =================================================================
    def _get_move_description(self, move_name):
        key = move_name.lower().replace(" ", "-").replace("'", "")
        ef = EffectFactory.create_effect(key)
        if ef and getattr(ef, 'description', None):
            return _sanitize(ef.description)
        cfg = EffectFactory.MOVE_EFFECTS.get(key)
        if cfg and cfg.get("description"):
            return _sanitize(cfg["description"])
        info = self.move_data.get_move_info(move_name)
        if info and info.get("description"):
            d = info["description"]
            if d and not d.startswith(f"Usa {move_name}"):
                return _sanitize(d)
        return "Um movimento que causa dano ao oponente."

    def _get_current_sprite(self):
        cid, csh = self.pokemon.id, self.pokemon.is_shiny
        if (self._cached_sprite is None or self._cached_sprite_id != cid
                or self._cached_shiny != csh):
            self._cached_sprite = self.pokedex.get_sprite(cid, "front", csh)
            self._cached_sprite_id = cid
            self._cached_shiny = csh
        return self._cached_sprite

    def _iv_bar_color(self, v):
        if v == 31: return self.C['iv_perfect']
        if v >= 27: return self.C['iv_great']
        if v >= 22: return self.C['iv_good']
        if v >= 16: return self.C['iv_median']
        if v >= 9:  return self.C['iv_bad']
        if v >= 1:  return self.C['iv_very_bad']
        return self.C['iv_horrible']

    def _iv_rank(self, v):
        if v == 31:  return "PERFEITO",  self.C['iv_perfect']
        if v >= 27:  return "OTIMO",     self.C['iv_great']
        if v >= 22:  return "BOM",       self.C['iv_good']
        if v >= 16:  return "MEDIO",     self.C['iv_median']
        if v >= 9:   return "RUIM",      self.C['iv_bad']
        if v >= 1:   return "M.RUIM",    self.C['iv_very_bad']
        return "HORRIVEL", self.C['iv_horrible']

    def _ev_color(self, ev):
        if ev >= 252: return self.C['iv_perfect']
        if ev >= 200: return self.C['iv_great']
        if ev >= 126: return self.C['iv_good']
        if ev >= 64:  return self.C['iv_median']
        return self.C['text']

    def _ev_bonus(self, stat):
        ev = self.pokemon.evs.get(stat, 0)
        eb = ev // 8
        if eb == 0: return 0
        base = self.pokemon.base_stats[stat]
        iv = self.pokemon.ivs.get(stat, 0)
        lv = self.pokemon.level
        if stat == 'hp':
            a = ((2 * base + iv + eb) * lv) // 100 + lv + 10
            b = ((2 * base + iv) * lv) // 100 + lv + 10
        else:
            a = ((2 * base + iv + eb) * lv) // 100 + 5
            b = ((2 * base + iv) * lv) // 100 + 5
        return a - b

    def _happiness_color(self, h):
        if h >= 200: return (255, 215, 0)
        if h >= 150: return (100, 220, 100)
        if h >= 100: return (255, 220, 100)
        if h >= 50:  return (255, 150, 100)
        return (255, 100, 100)

    def _xp_color(self, pct):
        if pct >= 0.75: return self.C['gold_bright']
        if pct >= 0.4:  return self.C['gold']
        return (180, 140, 70)

    # =================================================================
    # PARTICULAS
    # =================================================================
    def _create_shiny_particles(self, sx, sy, size):
        for _ in range(4):
            ang = random.uniform(0, math.pi * 2)
            rad = random.uniform(size // 2 + 5, size // 2 + 25)
            self.particles.append({
                'x': sx + size // 2 + math.cos(ang) * rad,
                'y': sy + size // 2 + math.sin(ang) * rad,
                'vx': random.uniform(-0.2, 0.2),
                'vy': random.uniform(-0.2, 0.2),
                'life': random.uniform(0.7, 1.0),
                'size': random.randint(1, 3),
                'color': random.choice([(255, 215, 0), (255, 200, 0), (255, 220, 50)]),
            })

    def _update_shiny_particles(self):
        for p in self.particles[:]:
            p['x'] += p['vx']; p['y'] += p['vy']; p['life'] -= 0.01
            if p['life'] <= 0:
                self.particles.remove(p)

    def _draw_shiny_particles(self, screen):
        for p in self.particles:
            pygame.draw.circle(screen, p['color'],
                               (int(p['x']), int(p['y'])), p['size'])

    # =================================================================
    # RENDER PRINCIPAL
    # =================================================================
    def render(self, screen):
        if not self.visible:
            return
        self._check_resize()

        mx, my = pygame.mouse.get_pos()
        cr = self.layout['content']
        if cr.collidepoint(mx, my):
            self._mouse_virtual = (mx - cr.x, my - cr.y + int(self.scroll_y))
        else:
            self._mouse_virtual = None

        ov = pygame.Surface((self.game.screen_manager.window_width,
                             self.game.screen_manager.window_height))
        ov.set_alpha(200); ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        self._rounded(screen, self.C['bg_modal'], self.rect, radius=16)
        self._rounded(screen, self.C['gold'], self.rect, radius=16, border=2)
        self._rounded(screen, self.C['border_panel'],
                      self.rect.inflate(-6, -6), radius=14, border=1)

        self._help_zones = []

        self._render_header(screen)
        self._render_tabs(screen)
        self._render_content(screen)
        self._render_footer(screen)
        self._render_close(screen)

        if self.confirmation_active:
            self._render_release_confirmation(screen)

        if self.feedback_message and self.feedback_timer > 0:
            self._render_feedback(screen)

        if self.held_item_dropdown.is_visible():
            self.held_item_dropdown.render(screen)

        if self._active_help and not self.confirmation_active:
            self._render_tooltip(screen)

    # =================================================================
    # HEADER
    # =================================================================
    def _render_header(self, screen):
        sc = self.layout['sprite_card']
        ic = self.layout['info_card']

        self._rounded(screen, (22, 26, 35), sc, radius=12)
        self._rounded(screen, self.C['border_panel'], sc, radius=12, border=2)

        glow_color = (255, 215, 0) if self.pokemon.is_shiny else (90, 130, 190)
        glow = pygame.Surface((sc.width, sc.height), pygame.SRCALPHA)
        cx, cy = sc.width // 2, sc.height // 2
        for r in range(sc.width // 2, 0, -4):
            a = int(30 * (1 - r / (sc.width // 2)))
            pygame.draw.circle(glow, (*glow_color, a), (cx, cy), r)
        screen.blit(glow, sc.topleft)

        sp = self._get_current_sprite()
        if sp:
            size = int(sc.width * 0.84)
            s = pygame.transform.smoothscale(sp, (size, size))
            screen.blit(s, (sc.centerx - size // 2, sc.centery - size // 2))
            if self.pokemon.is_shiny:
                self.particle_timer += 1
                if self.particle_timer > 20:
                    self.particle_timer = 0
                    self._create_shiny_particles(sc.x, sc.y, sc.width)
                self._update_shiny_particles()
                self._draw_shiny_particles(screen)

        if getattr(self.pokemon, 'is_boss', False):
            bb = pygame.Rect(sc.x + 6, sc.y + 6,
                             int(sc.width * 0.46), max(20, int(sc.height * 0.10)))
            self._rounded(screen, (170, 55, 55), bb, radius=4)
            self._rounded(screen, (240, 90, 90), bb, radius=4, border=1)
            t = self.fonts['tiny'].render("CHEFE", True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=bb.center))

        self._rounded(screen, (22, 26, 35), ic, radius=12)
        self._rounded(screen, self.C['border_panel'], ic, radius=12, border=2)

        pygame.draw.rect(screen, self.C['gold'],
                         (ic.x + 1, ic.y + 14, 3, ic.height - 28),
                         border_radius=2)

        x = ic.x + 20
        y = ic.y + 14

        name_s = self.fonts['hero'].render(_sanitize(self.pokemon.name).upper(),
                                           True, self.C['text'])
        screen.blit(name_s, (x, y))

        lvl_s = self.fonts['title'].render(f"Nv. {self.pokemon.level}",
                                           True, self.C['gold'])
        screen.blit(lvl_s, (x + name_s.get_width() + 14,
                            y + name_s.get_height() - lvl_s.get_height() - 2))

        if self.pokemon.is_shiny:
            sx = x + name_s.get_width() + 14 + lvl_s.get_width() + 14
            sy = y + name_s.get_height() // 2
            self._draw_star(screen, sx, sy, 11, self.C['gold_bright'])

        y += name_s.get_height() + 4

        id_s = self.fonts['small'].render(f"#{self.pokemon.id:04d}",
                                          True, self.C['text_muted'])
        screen.blit(id_s, (x, y))

        tx = x + id_s.get_width() + 20
        bw = max(70, int(ic.width * 0.10))
        bh = max(24, int(self.fonts['small'].get_height() + 6))
        for t in self.pokemon.types:
            b = pygame.Rect(tx, y - 4, bw, bh)
            self._type_badge(screen, b, t)
            tx += bw + 6

        summary_y = y + bh + 10
        summary_rect = pygame.Rect(
            ic.x + 20, summary_y,
            ic.width - 40, ic.bottom - summary_y - 12)
        if summary_rect.height > 20:
            self._render_summary_text(screen, summary_rect)

    def _render_summary_text(self, screen, rect):
        paragraphs = self._generate_summary()

        inner_x = rect.x
        inner_w = rect.width

        # CABECALHO
        tb_h = 30
        tb = pygame.Rect(inner_x, rect.y, inner_w, tb_h)
        pygame.draw.rect(screen, self.C['bg_title'], tb, border_radius=6)
        pygame.draw.rect(screen, self.C['gold'],
                         (tb.x, tb.y + 4, 4, tb.height - 8), border_radius=2)

        title = self.fonts['section'].render("RESUMO DO POKEMON",
                                             True, self.C['gold'])
        screen.blit(title, (tb.x + 16, tb.centery - title.get_height() // 2))

        # Help zone — excluindo botão
        help_zone = pygame.Rect(tb.x, tb.y, tb.width - 44, tb.height)
        self._register_help(help_zone, 'summary', space='screen')
        if self._is_field_hovered(help_zone, space='screen'):
            pygame.draw.rect(screen, self.C['hover_border'], help_zone, 2,
                             border_radius=6)

        # BOTAO TOGGLE (+/-)
        btn_size = 24
        btn_x = tb.right - btn_size - 6
        btn_y = tb.y + (tb.height - btn_size) // 2
        btn_rect = pygame.Rect(btn_x, btn_y, btn_size, btn_size)
        self._summary_toggle_rect = btn_rect

        mx, my = pygame.mouse.get_pos()
        btn_hover = btn_rect.collidepoint(mx, my)

        btn_bg = (60, 90, 130) if btn_hover else (40, 48, 62)
        btn_border = self.C['gold_bright'] if btn_hover else self.C['border_light']

        self._rounded(screen, btn_bg, btn_rect, radius=5)
        self._rounded(screen, btn_border, btn_rect, radius=5, border=2)

        # Desenha "+" ou "-"
        cx = btn_rect.centerx
        cy = btn_rect.centery
        line_len = 7
        thickness = 2

        # Horizontal (sempre)
        pygame.draw.line(screen, btn_border,
                         (cx - line_len, cy), (cx + line_len, cy), thickness)

        # Vertical apenas se fechado (+)
        if not self._summary_expanded:
            pygame.draw.line(screen, btn_border,
                             (cx, cy - line_len), (cx, cy + line_len), thickness)

        if not self._summary_expanded:
            return

        y = tb.bottom + 8

        disclaim_font = self.fonts['disclaim']
        disclaim = ("Esse resumo e gerado com base nos dados do seu Pokemon e "
                    "pode nao representar fielmente suas funcoes em gameplay.")
        disclaim_lines = self._wrap_text(disclaim, disclaim_font, inner_w)
        for line in disclaim_lines:
            s = disclaim_font.render(line, True, self.C['text_muted'])
            screen.blit(s, (inner_x, y))
            y += disclaim_font.get_height() + 2

        y += 8

        para_font = self.fonts['summary']
        para_line_h = para_font.get_height() + 4
        space_w = para_font.size(' ')[0]

        for idx, segs in enumerate(paragraphs):
            if idx > 0:
                y += 10

            lines = self._wrap_segments(segs, para_font, inner_w)
            for line in lines:
                cx2 = inner_x
                for word, color in line:
                    if word == ' ':
                        cx2 += space_w
                        continue
                    s = para_font.render(word, True, color)
                    screen.blit(s, (cx2, y))
                    cx2 += s.get_width()
                y += para_line_h

    # =================================================================
    # TABS
    # =================================================================
    def _render_tabs(self, screen):
        tabs_rect = self.layout['tabs_rect']
        self._rounded(screen, (12, 15, 21), tabs_rect, radius=12)
        self._rounded(screen, self.C['border_panel'], tabs_rect, radius=12, border=2)

        for i, tab in enumerate(self.TABS):
            r = self.layout['tabs'][i]
            is_active = (i == self.current_tab)
            is_hover = (i == self._hover_tab)

            if is_active:
                glow = pygame.Surface((r.width + 20, r.height + 20), pygame.SRCALPHA)
                for g_r in range(10, 0, -1):
                    a = int(50 * (1 - g_r / 10))
                    pygame.draw.rect(
                        glow, (*self.C['gold_bright'], a),
                        (10 - g_r, 10 - g_r, r.width + 2 * g_r, r.height + 2 * g_r),
                        border_radius=12)
                screen.blit(glow, (r.x - 10, r.y - 10))

                bg = (72, 92, 140)
                border = self.C['gold_bright']
                border_w = 3
                tc = (255, 255, 255)
            elif is_hover:
                bg = (46, 54, 70)
                border = self.C['border_light']
                border_w = 2
                tc = self.C['text']
            else:
                bg = (26, 30, 38)
                border = self.C['border_panel']
                border_w = 1
                tc = self.C['text_dim']

            self._rounded(screen, bg, r, radius=10)

            hl = pygame.Rect(r.x + 4, r.y + 3, r.width - 8, 2)
            pygame.draw.rect(screen, tuple(min(255, c + 30) for c in bg), hl,
                             border_radius=1)

            self._rounded(screen, border, r, radius=10, border=border_w)

            if is_active:
                ul_w = r.width - 32
                ul_x = r.x + 16
                ul_y = r.bottom - 8
                pygame.draw.rect(screen, self.C['gold_bright'],
                                 (ul_x, ul_y, ul_w, 5), border_radius=3)
                pygame.draw.rect(screen, (255, 240, 180),
                                 (ul_x + 4, ul_y + 1, ul_w - 8, 2), border_radius=2)

                tri_y = r.bottom + 4
                tri_cx = r.centerx
                pygame.draw.polygon(screen, self.C['gold_bright'], [
                    (tri_cx - 7, tri_y), (tri_cx + 7, tri_y), (tri_cx, tri_y + 7)
                ])

            txt = self.fonts['tab'].render(_sanitize(tab['label']), True, tc)
            screen.blit(txt, txt.get_rect(center=r.center))

    # =================================================================
    # CONTEUDO
    # =================================================================
    def _render_content(self, screen):
        cr = self.layout['content']
        self._recompute_scroll()
        vh = max(self._virtual_height(), cr.height)

        self._rounded(screen, (18, 21, 28), cr, radius=10)

        vs = pygame.Surface((cr.width, vh), pygame.SRCALPHA)
        vr = pygame.Rect(0, 0, cr.width, vh)
        self._draw_page(vs, vr)

        screen.set_clip(cr)
        screen.blit(vs, (cr.x, cr.y - int(self.scroll_y)))
        screen.set_clip(None)

        if self.max_scroll > 0:
            self._render_scrollbar(screen, cr)

    def _render_scrollbar(self, screen, cr):
        x = self.layout['scrollbar_x']
        w = 6
        h = cr.height
        self._rounded(screen, (25, 28, 38), (x, cr.y, w, h), radius=3)
        ratio = cr.height / (cr.height + self.max_scroll)
        thumb_h = max(36, int(h * ratio))
        thumb_y = cr.y + int((self.scroll_y / self.max_scroll) * (h - thumb_h))
        self._rounded(screen, (95, 110, 145), (x, thumb_y, w, thumb_h), radius=3)

    def _draw_page(self, surf, rect):
        key = self._tab_key()
        if key == 'stats':   self._draw_stats_page(surf, rect)
        elif key == 'moves': self._draw_moves_page(surf, rect)
        elif key == 'info':  self._draw_info_page(surf, rect)

    # =================================================================
    # PAGINA STATS
    # =================================================================
    def _draw_stats_page(self, surf, cr):
        gap = max(10, int(cr.width * 0.012))
        cw = (cr.width - gap) // 2

        left = pygame.Rect(cr.x, cr.y, cw, 9999)
        right = pygame.Rect(cr.x + cw + gap, cr.y, cw, 9999)

        lh = self._draw_stats_panel(surf, left, cr.y)
        lh = self._draw_nature_panel(surf, left, lh + gap)
        self._draw_held_panel(surf, left, lh + gap)

        rh = self._draw_ivs_panel(surf, right, cr.y)
        rh = self._draw_evs_panel(surf, right, rh + gap)
        self._draw_xp_panel(surf, right, rh + gap)

    def _draw_stats_panel(self, surf, col, y):
        h = 60 + 6 * 40
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Stats Atuais", help_key='stats')

        stats = [
            ("HP",         self.pokemon.max_hp,      255, 'hp'),
            ("ATAQUE",     self.pokemon.attack,      255, None),
            ("DEFESA",     self.pokemon.defense,     255, None),
            ("SP. ATAQUE", self.pokemon.sp_attack,   255, None),
            ("SP. DEFESA", self.pokemon.sp_defense,  255, None),
            ("VELOCIDADE", self.pokemon.speed_stat,  255, 'speed'),
        ]

        row_h = 34
        ry = inner.y
        for name, val, mx, hk in stats:
            row = pygame.Rect(inner.x, ry, inner.width, row_h)
            self._draw_stat_row(surf, row, name, val, mx, help_key=hk)
            ry += row_h + 6

        return y + h

    def _draw_nature_panel(self, surf, col, y):
        h = 100
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Natureza", help_key='nature')

        nature = self.pokemon.nature
        eff = self.NATURE_EFFECTS.get(nature, (None, None, "", ""))

        nm = self.fonts['title'].render(_sanitize(nature).upper(),
                                        True, self.C['text'])
        pill_h = max(26, int(h * 0.30))
        pill_y = inner.y + (nm.get_height() - pill_h) // 2 + 4
        x = inner.x + 4

        surf.blit(nm, (x, inner.y + 4))
        x = inner.x + nm.get_width() + 14

        if eff[0] is not None:
            f = self.fonts['small']
            up_txt = f"+10% {eff[2]}"
            dn_txt = f"-10% {eff[3]}"

            up_s = f.render(up_txt, True, (255, 255, 255))
            up_w = up_s.get_width() + 22
            up_r = pygame.Rect(x, pill_y, up_w, pill_h)
            self._rounded(surf, (55, 130, 75), up_r, radius=5)
            self._rounded(surf, (110, 220, 140), up_r, radius=5, border=1)
            surf.blit(up_s, up_s.get_rect(center=up_r.center))

            x = up_r.right + 8
            dn_s = f.render(dn_txt, True, (255, 255, 255))
            dn_w = dn_s.get_width() + 22
            dn_r = pygame.Rect(x, pill_y, dn_w, pill_h)
            self._rounded(surf, (150, 55, 55), dn_r, radius=5)
            self._rounded(surf, (230, 110, 110), dn_r, radius=5, border=1)
            surf.blit(dn_s, dn_s.get_rect(center=dn_r.center))
        else:
            neutral = self.fonts['small'].render("NEUTRA", True, self.C['text_muted'])
            ny = inner.y + nm.get_height() + 8
            surf.blit(neutral, (inner.x + 4, ny))

        return y + h

    def _draw_held_panel(self, surf, col, y):
        h = 240
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Item Segurado", help_key='held_item')

        if self.pokemon.held_item and self.pokemon.held_item_data:
            data = self.pokemon.held_item_data
            card_h = 62
            card = pygame.Rect(inner.x, inner.y, inner.width, card_h)
            self._rounded(surf, self.C['bg_row'], card, radius=8)
            self._rounded(surf, self.C['border_light'], card, radius=8, border=1)

            sp = item_bag_catalog.get_sprite(self.pokemon.held_item, scaled=True)
            icon = card_h - 14
            tx = card.x + 10
            if sp:
                s = pygame.transform.smoothscale(sp, (icon, icon))
                bg = pygame.Rect(card.x + 8, card.centery - icon // 2, icon, icon)
                pygame.draw.rect(surf, (60, 68, 90), bg, border_radius=6)
                pygame.draw.rect(surf, self.C['border_light'], bg, 1, border_radius=6)
                surf.blit(s, (bg.x, bg.y))
                tx = bg.right + 12

            nm = self.fonts['value'].render(_sanitize(data['name']),
                                             True, self.C['text'])
            surf.blit(nm, (tx, card.y + 8))

            d = _sanitize(data.get('description', ''))
            if len(d) > 42: d = d[:40] + "..."
            ds = self.fonts['small'].render(d, True, self.C['text_dim'])
            surf.blit(ds, (tx, card.y + 8 + nm.get_height() + 3))

            rw = max(70, int(inner.width * 0.22))
            rh = card_h - 16
            rem = pygame.Rect(card.right - rw - 8, card.centery - rh // 2, rw, rh)
            self._rounded(surf, (150, 50, 50), rem, radius=6)
            self._rounded(surf, (220, 90, 90), rem, radius=6, border=1)
            rt = self.fonts['small'].render("REMOVER", True, (255, 255, 255))
            surf.blit(rt, rt.get_rect(center=rem.center))
            self._remove_button_rect = rem
            y_btn = card.bottom + 12
        else:
            card_h = 54
            card = pygame.Rect(inner.x, inner.y, inner.width, card_h)
            self._rounded(surf, (28, 32, 42), card, radius=8)
            self._rounded(surf, self.C['border_row'], card, radius=8, border=1)
            t = self.fonts['value'].render("Nenhum item equipado",
                                           True, self.C['text_muted'])
            surf.blit(t, t.get_rect(center=card.center))
            self._remove_button_rect = None
            y_btn = card.bottom + 12

        avail = [it for it in self.game.player.bag.get_held_items() if it["quantity"] > 0]
        if self.pokemon.held_item:
            avail = [it for it in avail if it["id"] != self.pokemon.held_item]

        ew = inner.width
        eh = max(34, int(h * 0.15))
        eq = pygame.Rect(inner.x, y_btn, ew, eh)

        if avail:
            self._rounded(surf, (55, 95, 165), eq, radius=8)
            self._rounded(surf, (110, 150, 220), eq, radius=8, border=1)
            t = self.fonts['button'].render("EQUIPAR ITEM", True, (255, 255, 255))
            surf.blit(t, t.get_rect(center=eq.center))
            self._equip_button_rect = eq
        else:
            self._rounded(surf, (48, 48, 58), eq, radius=8)
            self._rounded(surf, (80, 80, 90), eq, radius=8, border=1)
            t = self.fonts['button'].render("SEM ITENS DISPONIVEIS",
                                            True, (140, 140, 150))
            surf.blit(t, t.get_rect(center=eq.center))
            self._equip_button_rect = None

        return y + h

    def _draw_ivs_panel(self, surf, col, y):
        h = 60 + 6 * 36
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Valores Individuais",
                                 accent=self.C['blue'], help_key='ivs')

        ivs = [
            ("HP",         self.pokemon.ivs.get('hp', 0)),
            ("ATAQUE",     self.pokemon.ivs.get('attack', 0)),
            ("DEFESA",     self.pokemon.ivs.get('defense', 0)),
            ("SP. ATAQUE", self.pokemon.ivs.get('special_attack', 0)),
            ("SP. DEFESA", self.pokemon.ivs.get('special_defense', 0)),
            ("VELOCIDADE", self.pokemon.ivs.get('speed', 0)),
        ]

        row_h = 30
        ry = inner.y
        for name, val in ivs:
            row = pygame.Rect(inner.x, ry, inner.width, row_h)
            color = self._iv_bar_color(val)
            rank, rc = self._iv_rank(val)
            rk = self.fonts['tiny'].render(rank, True, rc)
            rank_space = rk.get_width() + 16

            self._draw_stat_row(surf, row, name, val, 31,
                                value_text=f"{val}/31",
                                accent_override=color,
                                rank_reserved=rank_space)

            surf.blit(rk, (row.right - rk.get_width() - 10,
                           row.centery - rk.get_height() // 2))
            ry += row_h + 6

        return y + h

    def _draw_evs_panel(self, surf, col, y):
        h = 60 + 3 * 44 + 50
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Esforco (EVs)",
                                 accent=self.C['green'], help_key='evs')

        evs = [
            ("HP",      self.pokemon.evs.get('hp', 0), 'hp'),
            ("ATAQUE",  self.pokemon.evs.get('attack', 0), 'attack'),
            ("DEFESA",  self.pokemon.evs.get('defense', 0), 'defense'),
            ("SP. ATK", self.pokemon.evs.get('special_attack', 0), 'special_attack'),
            ("SP. DEF", self.pokemon.evs.get('special_defense', 0), 'special_defense'),
            ("VELOC.",  self.pokemon.evs.get('speed', 0), 'speed'),
        ]

        cols = 2
        cw = (inner.width - 8) // cols
        ch = 40
        ry = inner.y
        for i, (name, ev, key) in enumerate(evs):
            r_ = i // cols
            c_ = i % cols
            card = pygame.Rect(
                inner.x + c_ * (cw + 8),
                ry + r_ * (ch + 6),
                cw, ch)

            bg = self.C['bg_row'] if ev > 0 else (22, 25, 33)
            self._rounded(surf, bg, card, radius=6)
            self._rounded(surf, self.C['border_row'], card, radius=6, border=1)

            if ev > 0:
                pygame.draw.rect(surf, self._ev_color(ev),
                                 (card.x + 1, card.y + 4, 3, card.height - 8),
                                 border_radius=2)

            lab = self.fonts['tiny'].render(name, True, self.C['text_muted'])
            surf.blit(lab, (card.x + 10, card.y + 4))

            bonus = self._ev_bonus(key)
            bt = f"+{bonus}" if bonus > 0 else "+0"
            bc = self.C['green'] if bonus > 0 else self.C['text_muted']
            bs = self.fonts['tiny'].render(bt, True, bc)
            surf.blit(bs, (card.right - bs.get_width() - 8, card.y + 4))

            vc = self._ev_color(ev) if ev > 0 else self.C['text_muted']
            vv = self.fonts['value'].render(str(ev), True, vc)
            surf.blit(vv, (card.x + 10, card.bottom - vv.get_height() - 4))

        ry += 3 * (ch + 6) + 6

        total = self.pokemon.stats.get_ev_total()
        mx = self.pokemon.stats.MAX_TOTAL_EVS
        pct = total / mx if mx > 0 else 0

        t = self.fonts['small'].render(
            f"TOTAL: {total} / {mx}", True, self.C['gold'])
        surf.blit(t, (inner.x, ry))
        ry += t.get_height() + 4

        bar = pygame.Rect(inner.x, ry, inner.width, 14)
        pygame.draw.rect(surf, self.C['bg_track'], bar, border_radius=7)
        if total > 0:
            pygame.draw.rect(surf, self.C['green'],
                             (bar.x, bar.y, int(bar.width * pct), bar.height),
                             border_radius=7)
        pygame.draw.rect(surf, self.C['border_light'], bar, 2, border_radius=7)
        return y + h

    def _draw_xp_panel(self, surf, col, y):
        h = 90
        inner = self._draw_panel(surf, col.x, y, col.width, h,
                                 "Experiencia",
                                 accent=self.C['gold'], help_key='xp')

        xp = self.pokemon.xp
        xp_next = self.pokemon.xp_to_next
        pct = xp / xp_next if xp_next > 0 else 0
        xp_c = self._xp_color(pct)

        lab = self.fonts['small'].render("PROXIMO NIVEL", True, self.C['text_muted'])
        surf.blit(lab, (inner.x, inner.y))
        val = self.fonts['value'].render(f"{xp} / {xp_next}", True, xp_c)
        surf.blit(val, (inner.right - val.get_width(), inner.y))

        by = inner.y + lab.get_height() + 10
        bar = pygame.Rect(inner.x, by, inner.width, 16)
        pygame.draw.rect(surf, self.C['bg_track'], bar, border_radius=8)
        fill = int(bar.width * pct)
        if fill > 0:
            pygame.draw.rect(surf, xp_c,
                             (bar.x, bar.y, fill, bar.height), border_radius=8)
        pygame.draw.rect(surf, self.C['border_light'], bar, 2, border_radius=8)

        pct_s = self.fonts['small'].render(f"{pct * 100:.1f}%",
                                            True, self.C['text_dim'])
        surf.blit(pct_s, (inner.right - pct_s.get_width(),
                          by + bar.height + 6))

        return y + h

    # =================================================================
    # PAGINA MOVES
    # =================================================================
    def _draw_moves_page(self, surf, cr):
        title_h = 36
        side_margin = int(cr.width * 0.035)
        inner_x = cr.x + side_margin
        inner_w = cr.width - side_margin * 2

        tb = pygame.Rect(inner_x, cr.y, inner_w, title_h)
        self._rounded(surf, self.C['bg_panel'], tb, radius=8)
        self._rounded(surf, self.C['border_panel'], tb, radius=8, border=1)
        pygame.draw.rect(surf, self.C['gold'],
                         (tb.x + 2, tb.y + 6, 4, tb.height - 12),
                         border_radius=2)

        self._register_help(tb, 'moves_page')
        if self._is_field_hovered(tb):
            pygame.draw.rect(surf, self.C['hover_border'], tb, 2, border_radius=8)

        title = self.fonts['section'].render("MOVIMENTOS EQUIPADOS",
                                             True, self.C['gold'])
        surf.blit(title, (tb.x + 16, tb.centery - title.get_height() // 2))

        cnt = self.fonts['small'].render(
            f"{len(self.pokemon.moves)} / 4", True, self.C['text_muted'])
        surf.blit(cnt, (tb.right - cnt.get_width() - 14,
                        tb.centery - cnt.get_height() // 2))

        y_start = tb.bottom + 10
        gap = max(8, int(inner_w * 0.012))
        cols = 2
        cw = (inner_w - gap) // cols
        ch = 130

        for i in range(4):
            r_ = i // cols
            c_ = i % cols
            card = pygame.Rect(
                inner_x + c_ * (cw + gap),
                y_start + r_ * (ch + gap),
                cw, ch)
            if i < len(self.pokemon.moves):
                self._draw_move_card(surf, self.pokemon.moves[i], card)
            else:
                self._draw_empty_move_card(surf, card)

    def _draw_empty_move_card(self, surf, card):
        self._rounded(surf, (22, 25, 33), card, radius=8)
        self._rounded(surf, (40, 44, 55), card, radius=8, border=2)
        t = self.fonts['small'].render("VAZIO", True, self.C['text_muted'])
        surf.blit(t, t.get_rect(center=card.center))

    def _draw_move_card(self, surf, move, card):
        tc = self.C.get(f"type_{move.type.lower()}", (128, 128, 128))

        self._rounded(surf, (30, 34, 44), card, radius=8)
        self._rounded(surf, self.C['border_panel'], card, radius=8, border=2)

        pygame.draw.rect(surf, tc,
                         (card.x + 2, card.y + 8, 5, card.height - 16),
                         border_radius=3)

        hdr_y = card.y + 10
        hdr_h = 30
        move_name = _sanitize(move.name).upper()
        nm = self.fonts['title'].render(move_name, True, self.C['text'])
        surf.blit(nm, (card.x + 14, hdr_y + (hdr_h - nm.get_height()) // 2))

        bw = max(72, int(card.width * 0.17))
        bh = 22
        badge = pygame.Rect(card.right - bw - 12, hdr_y + 4, bw, bh)
        self._type_badge(surf, badge, move.type)

        y2 = hdr_y + hdr_h + 4
        cat_h = 22

        if move.power > 0:
            if move.category == 'physical':
                cat_txt, cat_c = "FISICO", (255, 175, 90)
            else:
                cat_txt, cat_c = "ESPECIAL", (110, 180, 250)
        else:
            cat_txt, cat_c = "STATUS", (180, 190, 200)

        ct = self.fonts['small'].render(cat_txt, True, cat_c)
        surf.blit(ct, (card.x + 14, y2 + (cat_h - ct.get_height()) // 2))

        cat_zone = pygame.Rect(card.x + 12, y2, ct.get_width() + 8, cat_h)
        self._register_help(cat_zone, 'category')
        if self._is_field_hovered(cat_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             cat_zone.inflate(4, 2), 2, border_radius=4)

        pp_pct = move.current_pp / max(1, move.max_pp)
        if pp_pct > 0.4: pp_c = self.C['green']
        elif pp_pct > 0.2: pp_c = self.C['gold']
        else: pp_c = self.C['red']

        segments = []
        segments.append(('power',
                         f"PWR {move.power if move.power > 0 else '--'}",
                         self.C['text']))
        segments.append((None, "  |  ", self.C['text_muted']))
        segments.append(('accuracy',
                         f"ACC {move.accuracy}%" if move.accuracy > 0 else "ACC --",
                         self.C['text']))
        segments.append((None, "  |  ", self.C['text_muted']))
        segments.append(('pp',
                         f"PP {move.current_pp}/{move.max_pp}", pp_c))

        total_w = sum(self.fonts['small'].size(t)[0] for _, t, _ in segments)
        cx = card.right - 12 - total_w
        cy = y2 + (cat_h - self.fonts['small'].get_height()) // 2

        for key, text, color in segments:
            s = self.fonts['small'].render(text, True, color)
            surf.blit(s, (cx, cy))

            if key is not None:
                zone = pygame.Rect(cx - 2, y2, s.get_width() + 4, cat_h)
                self._register_help(zone, key)
                if self._is_field_hovered(zone):
                    pygame.draw.rect(surf, self.C['hover_border'],
                                     zone, 2, border_radius=4)
            cx += s.get_width()

        sep_y = y2 + cat_h + 6
        pygame.draw.line(surf, self.C['border_row'],
                         (card.x + 12, sep_y), (card.right - 12, sep_y), 1)

        desc = self._get_move_description(move.name)
        f = self.fonts['small']
        lines = self._wrap_text(desc, f, card.width - 30)

        dy = sep_y + 6
        line_h = f.get_height() + 1
        max_lines = max(1, (card.bottom - dy - 6) // line_h)
        for line in lines[:max_lines]:
            s = f.render(line, True, self.C['text_dim'])
            surf.blit(s, (card.x + 14, dy))
            dy += line_h

    # =================================================================
    # PAGINA INFO
    # =================================================================
    def _draw_info_page(self, surf, cr):
        gap = max(10, int(cr.width * 0.012))
        cw = (cr.width - gap) // 2
        left = pygame.Rect(cr.x, cr.y, cw, cr.height)
        right = pygame.Rect(cr.x + cw + gap, cr.y, cw, cr.height)
        self._draw_info_left(surf, left)
        self._draw_info_right(surf, right)

    def _draw_info_left(self, surf, col):
        inner = self._draw_panel(surf, col.x, col.y, col.width, col.height,
                                 "Identificacao", accent=self.C['blue'])

        from src.utils.pokemon_origin import (
            get_capture_label, get_capture_color,
            format_capture_date, split_origin_for_display, is_traded,
        )

        method_raw = getattr(self.pokemon, 'capture_method', 'unknown') or 'unknown'
        pad = 4
        x = inner.x + pad
        y = inner.y + 4

        y = self._kv_block(surf, x, y, inner.width, "Especie",
                           self.pokemon.name, help_key='species')
        apelido = self.pokemon.custom_name.strip() if self.pokemon.custom_name \
            else "sem apelido"
        y = self._kv_block(surf, x, y, inner.width, "Apelido", apelido,
                           help_key='nickname')
        y = self._kv_block(surf, x, y, inner.width, "ID Pokedex",
                           f"#{self.pokemon.id:04d}", self.C['gold'],
                           help_key='id')

        if self.pokemon.is_in_team:
            pos = self.game.player.team.index(self.pokemon) + 1
            loc = f"No time - pos. {pos}"
        else:
            loc = "Box do PC"
        y = self._kv_block(surf, x, y, inner.width, "Localizacao", loc,
                           help_key='location')

        y += 6
        pygame.draw.line(surf, self.C['border_row'],
                         (x, y), (inner.right - pad, y), 1)
        y += 8

        origin_lab = self.fonts['small'].render("ORIGEM", True, self.C['gold'])
        surf.blit(origin_lab, (x, y))
        origin_zone = pygame.Rect(x, y, 200, origin_lab.get_height() + 80)
        self._register_help(origin_zone, 'origin')
        if self._is_field_hovered(origin_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             origin_zone.inflate(6, 4), 2, border_radius=6)
        y += origin_lab.get_height() + 4

        lab = self.fonts['small'].render("METODO", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        y += lab.get_height() + 2

        if is_traded(method_raw):
            lines = split_origin_for_display(method_raw, max_chars=38)
            base = method_raw.split(" | ")[0].strip()
            base_color = get_capture_color(base)
            for i, line in enumerate(lines):
                c = base_color if i == 0 else self.C['blue']
                s = self.fonts['value'].render(_sanitize(line), True, c)
                surf.blit(s, (x, y))
                y += s.get_height() + 2
        else:
            s = self.fonts['value'].render(_sanitize(get_capture_label(method_raw)),
                                           True, get_capture_color(method_raw))
            surf.blit(s, (x, y))
            y += s.get_height() + 6

        lab = self.fonts['small'].render("DATA DE CAPTURA", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        y += lab.get_height() + 2

        dt = format_capture_date(getattr(self.pokemon, 'capture_date', None))
        dc = self.C['gold'] if getattr(self.pokemon, 'capture_date', None) \
            else self.C['text_muted']
        s = self.fonts['value'].render(_sanitize(dt), True, dc)
        surf.blit(s, (x, y))

    def _draw_info_right(self, surf, col):
        inner = self._draw_panel(surf, col.x, col.y, col.width, col.height,
                                 "Caracteristicas", accent=self.C['purple'])

        x = inner.x + 4
        y = inner.y + 4
        pad = 4

        lab = self.fonts['small'].render("TIPO(S)", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        type_zone = pygame.Rect(x, y, lab.get_width() + 220, lab.get_height() + 34)
        self._register_help(type_zone, 'type')
        if self._is_field_hovered(type_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             type_zone.inflate(6, 4), 2, border_radius=6)
        tx = x + lab.get_width() + 14
        for t in self.pokemon.types:
            bw = max(70, int(inner.width * 0.22))
            bh = max(22, int(col.height * 0.06))
            b = pygame.Rect(tx, y - 3, bw, bh)
            self._type_badge(surf, b, t)
            tx += bw + 6
        y += max(34, int(col.height * 0.09))

        pygame.draw.line(surf, self.C['border_row'],
                         (x, y), (inner.right - pad, y), 1)
        y += 8

        nature = self.pokemon.nature
        eff = self.NATURE_EFFECTS.get(nature, (None, None, "", ""))
        nc = (100, 220, 200) if eff[0] is not None else self.C['text']
        lab = self.fonts['small'].render("NATUREZA", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        nat_zone = pygame.Rect(x, y, inner.width, lab.get_height() + 6)
        self._register_help(nat_zone, 'nature')
        if self._is_field_hovered(nat_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             nat_zone.inflate(6, 4), 2, border_radius=6)
        val = self.fonts['value'].render(_sanitize(nature), True, nc)
        surf.blit(val, (inner.right - val.get_width() - pad, y))
        y += lab.get_height() + 8

        g = getattr(self.pokemon, 'gender', None)
        if g == "male":
            gv, gc = "MACHO", (95, 150, 230)
        elif g == "female":
            gv, gc = "FEMEA", (235, 105, 145)
        else:
            gv, gc = "SEM GENERO", self.C['text_muted']

        lab = self.fonts['small'].render("SEXO", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        sex_zone = pygame.Rect(x, y, inner.width, lab.get_height() + 6)
        self._register_help(sex_zone, 'gender')
        if self._is_field_hovered(sex_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             sex_zone.inflate(6, 4), 2, border_radius=6)
        val = self.fonts['value'].render(gv, True, gc)
        surf.blit(val, (inner.right - val.get_width() - pad, y))
        y += lab.get_height() + 8

        h = getattr(self.pokemon, 'height_m', None)
        hv = f"{h:.2f} m" if h else "??? m"
        w = getattr(self.pokemon, 'weight_kg', None)
        wv = f"{w:.1f} kg" if w else "??? kg"

        cw = (inner.width - pad * 2 - 8) // 2
        hb = pygame.Rect(x, y, cw, 50)
        wb = pygame.Rect(x + cw + 8, y, cw, 50)

        for box, l, v, hk in [(hb, "ALTURA", hv, 'height'),
                              (wb, "PESO", wv, 'weight')]:
            self._rounded(surf, self.C['bg_row'], box, radius=6)
            self._rounded(surf, self.C['border_row'], box, radius=6, border=1)
            pygame.draw.rect(surf, self.C['purple'],
                             (box.x + 1, box.y + 4, 3, box.height - 8),
                             border_radius=2)
            lb = self.fonts['tiny'].render(l, True, self.C['text_muted'])
            surf.blit(lb, (box.x + 10, box.y + 5))
            vb = self.fonts['value'].render(v, True, self.C['text'])
            surf.blit(vb, (box.x + 10, box.y + 5 + lb.get_height() + 3))
            self._register_help(box, hk)
            if self._is_field_hovered(box):
                pygame.draw.rect(surf, self.C['hover_border'], box, 2, border_radius=6)

        y += 60

        lab = self.fonts['small'].render("FELICIDADE", True, self.C['text_muted'])
        surf.blit(lab, (x, y))
        hap = self.pokemon.get_happiness()
        mx = 255
        hc = self._happiness_color(hap)
        val = self.fonts['value'].render(f"{hap} / {mx}", True, hc)
        surf.blit(val, (inner.right - val.get_width() - pad, y))
        hap_zone = pygame.Rect(x, y, inner.width, lab.get_height() + 22)
        self._register_help(hap_zone, 'happiness')
        if self._is_field_hovered(hap_zone):
            pygame.draw.rect(surf, self.C['hover_border'],
                             hap_zone.inflate(6, 4), 2, border_radius=6)
        y += lab.get_height() + 6

        bar = pygame.Rect(x, y, inner.width - pad * 2, 14)
        pygame.draw.rect(surf, self.C['bg_track'], bar, border_radius=7)
        fill = int(bar.width * (hap / mx))
        if fill > 0:
            pygame.draw.rect(surf, hc,
                             (bar.x, bar.y, fill, bar.height), border_radius=7)
        pygame.draw.rect(surf, self.C['border_light'], bar, 2, border_radius=7)

    # =================================================================
    # FOOTER
    # =================================================================
    def _render_footer(self, screen):
        b = self.layout['action_btn']
        if self.pokemon.is_in_team:
            bg, bd, label = (130, 50, 50), (220, 90, 90), "REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                bg, bd, label = (48, 115, 68), (100, 200, 120), "ADICIONAR AO TIME"
            else:
                bg, bd, label = (50, 53, 62), (80, 85, 95), "TIME CHEIO"

        self._rounded(screen, bg, b, radius=10)
        self._rounded(screen, bd, b, radius=10, border=2)
        t = self.fonts['button'].render(label, True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=b.center))

        b2 = self.layout['release_btn']
        if self._can_release():
            self._rounded(screen, (150, 42, 42), b2, radius=10)
            self._rounded(screen, (230, 90, 90), b2, radius=10, border=2)
            t = self.fonts['button'].render("LIBERTAR", True, (255, 255, 255))
        else:
            self._rounded(screen, (38, 34, 38), b2, radius=10)
            self._rounded(screen, (60, 55, 60), b2, radius=10, border=1)
            t = self.fonts['button'].render("BLOQUEADO", True, (110, 95, 105))
        screen.blit(t, t.get_rect(center=b2.center))

    def _render_close(self, screen):
        self._rounded(screen, (36, 40, 48), self.close_button, radius=8)
        self._rounded(screen, self.C['border_panel'], self.close_button,
                      radius=8, border=1)
        t = self.fonts['title'].render("X", True, self.C['text_dim'])
        screen.blit(t, t.get_rect(center=self.close_button.center))

    # =================================================================
    # FEEDBACK
    # =================================================================
    def _render_feedback(self, screen):
        f = self.fonts['section']
        t = f.render(_sanitize(self.feedback_message), True, self.feedback_color)
        r = t.get_rect(center=(self.rect.centerx,
                                self.rect.y + int(self.height * 0.02)))
        bg = r.inflate(36, 18)
        self._rounded(screen, (20, 20, 30), bg, radius=8)
        self._rounded(screen, self.feedback_color, bg, radius=8, border=2)
        screen.blit(t, r)
        self.feedback_timer -= 0.016
        if self.feedback_timer <= 0:
            self.feedback_message = None

    # =================================================================
    # TOOLTIP
    # =================================================================
    def _render_tooltip(self, screen):
        if not self._active_help or self._active_help not in HELP_TEXT:
            return

        title, desc = HELP_TEXT[self._active_help]
        font_t = self.fonts['tooltip_t']
        font_d = self.fonts['tooltip_b']

        max_w = max(280, int(self.width * 0.32))
        lines = self._wrap_text(desc, font_d, max_w)

        title_s = font_t.render(_sanitize(title), True, self.C['gold'])
        line_h = font_d.get_height() + 3
        box_w = max_w + 30
        box_h = 16 + title_s.get_height() + 10 + len(lines) * line_h + 12

        mx, my = pygame.mouse.get_pos()
        bx = mx + 20
        by = my + 20
        sw = self.game.screen_manager.window_width
        sh = self.game.screen_manager.window_height
        if bx + box_w > sw - 10: bx = mx - box_w - 20
        if by + box_h > sh - 10: by = my - box_h - 20
        if bx < 10: bx = 10
        if by < 10: by = 10

        box = pygame.Rect(bx, by, box_w, box_h)

        self._rounded(screen, (24, 30, 42), box, radius=10)
        self._rounded(screen, self.C['gold'], box, radius=10, border=2)
        self._rounded(screen, self.C['border_panel'],
                      box.inflate(-4, -4), radius=8, border=1)

        pygame.draw.rect(screen, self.C['gold'],
                         (box.x + 1, box.y + 10, 3, title_s.get_height() + 4),
                         border_radius=2)
        screen.blit(title_s, (box.x + 14, box.y + 12))

        y = box.y + 12 + title_s.get_height() + 10
        for line in lines:
            s = font_d.render(line, True, self.C['text'])
            screen.blit(s, (box.x + 14, y))
            y += line_h

    # =================================================================
    # CONFIRMACAO
    # =================================================================
    def _render_release_confirmation(self, screen):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        screen.blit(ov, (self.x, self.y))

        bw = int(self.width * 0.58)
        bh = int(self.height * 0.30)
        box = pygame.Rect(0, 0, bw, bh)
        box.center = self.rect.center

        self._rounded(screen, self.C['bg_panel'], box, radius=14)
        self._rounded(screen, (200, 80, 80), box, radius=14, border=2)

        y = box.y + int(bh * 0.14)
        t = self.fonts['title'].render("Tem certeza que deseja LIBERTAR?",
                                       True, (255, 200, 200))
        screen.blit(t, t.get_rect(center=(box.centerx, y)))
        y += int(bh * 0.18)

        t2 = self.fonts['small'].render("Esta acao e IRREVERSIVEL!",
                                        True, (255, 100, 100))
        screen.blit(t2, t2.get_rect(center=(box.centerx, y)))
        y += int(bh * 0.16)

        warn = self._get_release_warning()
        if warn:
            t3 = self.fonts['small'].render(_sanitize(warn), True, (255, 200, 50))
            screen.blit(t3, t3.get_rect(center=(box.centerx, y)))

        for r, label, color in [
            (self.confirm_yes_button, "SIM, LIBERTAR", (160, 50, 50)),
            (self.confirm_no_button,  "NAO, CANCELAR",  (55, 55, 75)),
        ]:
            self._rounded(screen, color, r, radius=8)
            self._rounded(screen, (255, 255, 255), r, radius=8, border=1)
            t = self.fonts['button'].render(label, True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=r.center))