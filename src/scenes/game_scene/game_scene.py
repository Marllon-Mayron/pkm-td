# src/scenes/game_scene.py
"""
Cena principal do jogo - COM NOVA ARQUITETURA DE WAVES
"""
import pygame
from datetime import datetime

from src.scenes.game_scene.components.managers.move_quick_switch_manager import MoveQuickSwitchManager
from src.scenes.game_scene.components.managers.event_processor import EventProcessor
from src.scenes.game_scene.components.managers.photo_capture_manager import PhotoCaptureManager
from src.scenes.game_scene.components.renderer.camera_photo_renderer import CameraPhotoRenderer
from src.battle.effects.specific.weather.weather_state import WeatherType
from src.battle.battle_system import BattleSystem
from src.config.paths import PROJECT_ROOT
from src.core.performance_monitor import perf_monitor
from src.managers.sounds.sound_manager import SoundEffect, sound_manager
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.managers.overlay_manager import OverlayType, OverlayManager
from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
from src.scenes.game_scene.components.managers.item_drag_manager import ItemDragManager
from src.scenes.game_scene.components.managers.target_item_manager import TargetItemManager
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
from src.scenes.game_scene.components.managers.wave_manager import WaveManager
from src.scenes.game_scene.components.overlays.evolution_overlay import EvolutionOverlay
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.item_bag_renderer import ItemBagRenderer
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer # NOVO
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer
from src.scenes.game_scene.components.overlays.game_over_scene.game_over_scene import GameOverScene
from src.scenes.game_scene.components.overlays.level_complete_scene.level_complete_scene import LevelCompleteScene
from src.managers.notification_manager import notification_manager
from src.ui.toast_renderer import toast_info, toast_warning, toast_battle
from src.scenes.game_scene.components.day_night_weather_system import DayNightWeatherSystem
from src.scenes.game_scene.components.managers.in_game_debug_manager import InGameDebugManager
from src.config.regions import make_phase_id, DEFAULT_REGION_ID

GYM_PHASES = {
    (1, 5): 1,   # 1º Ginásio
    (2, 8): 2,   # 2º Ginásio
    (3, 4): 3,   # 3º Ginásio
    (4, 5): 4,   # 4º Ginásio
    (5, 5): 5,   # 5º Ginásio
    (6, 5): 6,   # 6º Ginásio
    (6, 10): 7,  # 7º Ginásio
    (7, 4): 8,   # 8º Ginásio
}

MYTHICAL_SPAWN_CHANCE = 0.05

class GameScene(BaseScene):
    def __init__(self, game, chapter_id=1, phase_number=1, region_id=DEFAULT_REGION_ID, keep_placement=False, placement_snapshot=None):
        super().__init__(game)

        # ===== REGISTRA ESTA CENA COMO DONA DAS ANIMAÇÕES =====
        # Necessário para que `detach_from_scene(self)` funcione no cleanup
        # e pare as animações de clima/spray/etc ao sair da cena.
        from src.anim.animation_manager import attach_to_scene
        attach_to_scene(self)

        # ===== parâmetros de restauração de placement =====
        self._keep_placement = keep_placement
        self._placement_snapshot = placement_snapshot

        # Flag de debug
        self.debug_in_game = False
        self.move_select_overlay = None
        self.move_learn_overlay = None
        self.pending_move_learn = None
        self.game_paused = False
        self.final_victory_overlay = None
        self._pending_final_victory_delay = None
        self._pokemon_defeated_this_phase = False
        self.capture_shake_animation = None

        self.ui_hidden = False  # True = oculta todas as UIs

        self.region_id = int(region_id) if region_id is not None else DEFAULT_REGION_ID
        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.phase_id = make_phase_id(self.region_id, chapter_id, phase_number)
        self.phase_info = None

        # Carrega informações da fase
        self._load_phase_info()

        # Componentes da fase
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()

        # Cria os gerenciadores
        self.placement_manager = PlacementManager(self)
        self.team_manager = GameTeamManager(game, self)
        self.move_quick_switch_manager = MoveQuickSwitchManager(self)
        self.notification_manager = notification_manager
        self.target_item_manager = TargetItemManager(game)
        self.target_item_renderer = TargetItemRenderer()
        # carrega o event_manager dos dados da fase

        # CARREGA OS DADOS DA FASE (inclui _phase_data)
        self._load_phase_data()  # <--- PRIMEIRO CARREGA OS DADOS
        self.event_manager = phase_loader.get_event_manager()
        self.event_processor = EventProcessor(self)
        # ===== AGORA CARREGA AS CONFIGURAÇÕES =====
        self.day_night_mode = "random"
        self.base_weather = "random"

        if hasattr(self, '_phase_data') and self._phase_data:
            self.day_night_mode = self._phase_data.get("day_night_mode", "random")
            self.base_weather = self._phase_data.get("base_weather", "random")
            print(f"[GAME_SCENE] Configurações da fase: Dia/Noite={self.day_night_mode}, Clima={self.base_weather}")

        # Cria o overlay_manager
        self.overlay_manager = OverlayManager(self)

        self.wave_manager = WaveManager(phase_loader, self)
        self.wave_manager.set_paths(self.path_renderer.paths)

        # Vincula os itens alvo
        self.wave_manager.set_target_items(self.target_item_manager.items)

        # Battle System
        self.battle_system = BattleSystem(self)

        # debug mode
        self.in_game_debug = InGameDebugManager(self)

        # Configurações de mundo
        self._setup_world_dimensions()

        self.player = game.player

        # ===== Sincroniza região atual do AchievementManager =====
        if hasattr(self.player, 'achievement_manager'):
            self.player.achievement_manager.set_current_region(self.region_id)

        # Renderizadores
        self.item_bag_renderer = ItemBagRenderer(game, self.player.bag)
        self.item_drag_manager = ItemDragManager(game, self.player.bag)

        self.photo_manager = PhotoCaptureManager(self)
        self.camera_renderer = CameraPhotoRenderer(
            self.game,
            self.item_bag_renderer,
            self.photo_manager
        )

        # Salvar configurações da bolsa
        self.player.apply_bag_ui_config(self.item_bag_renderer)

        # Controle de música
        self.music_playing = False
        self.current_music = None

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # Estado do jogo
        self.hovered_spot = None
        self.placed_pokemon = []
        self.game_state = "waiting"
        self._pokemon_defeated_this_phase = False
        self.between_waves_timer = 3.0
        self.show_debug = False

        # ===== SISTEMA DIA/NOITE E CLIMA =====
        self.day_night_weather = DayNightWeatherSystem(self)
        self.day_night_weather.initialize()  # Inicializa com valores aleatórios

        # ===== ANIMAÇÕES DE CLIMA (novo sistema) =====
        # Chave + trigger atualmente rodando. Usado pra detectar mudanças
        # e trocar suavemente. Ver `_sync_weather_animations()`.
        self._current_weather_key = None
        self._current_weather_trigger = None

        # Fontes cacheadas
        self._debug_font = pygame.font.Font(None, 18)
        self._debug_font_bold = pygame.font.Font(None, 20)
        self._debug_font_small = pygame.font.Font(None, 16)
        self._ui_font = None
        self._ui_font_small = None

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None
        self.ui_minimized = False  # estado minimizado da UI superior
        self.ui_panel_rect = None  # para detectar clique no botão

        # Cache de referências para otimização
        self._cached_spot_renderer = None
        self._cached_placement_manager = None
        self._cached_team_manager = None
        self._cached_item_bag_renderer = None

        # Inicia o jogo
        self._start_game()

        # RESTAURA POSICIONAMENTO SE SOLICITADO
        if self._keep_placement and self._placement_snapshot:
            self._restore_placement(self._placement_snapshot)

    def toggle_pause(self):
        """Alterna pausa do jogo usando o novo overlay"""
        if self.paused:
            # Se já está pausado, despausa
            self.paused = False
            self.game_paused = False
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = False
            self.overlay_manager.hide()  # Fecha o overlay
            print("Jogo continuando")
        else:
            # Pausa o jogo
            self.paused = True
            self.game_paused = True
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = True
            self.overlay_manager.show(OverlayType.PAUSE)  # Mostra o overlay de pausa
            print("Jogo pausado")

    def toggle_ui_minimize(self):
        self.ui_minimized = not self.ui_minimized

    def toggle_ui_hidden(self):
        """Alterna a visibilidade de todas as UIs do jogo"""
        self.ui_hidden = not self.ui_hidden

        status = "ocultada" if self.ui_hidden else "mostrada"
        print(f"[UI] Todas as UIs foram {status}")

    def _get_ui_font(self, size=24):
        """Obtém fonte da UI com cache"""
        if size == 24:
            if self._ui_font is None:
                self._ui_font = pygame.font.Font(None, 24)
            return self._ui_font
        else:
            if self._ui_font_small is None:
                self._ui_font_small = pygame.font.Font(None, 18)
            return self._ui_font_small

    def _start_game(self):
        """Inicia o jogo"""
        # ===== TUTORIAL: FASE 1:1 =====
        is_tutorial = (self.chapter_id == 1 and self.phase_number == 1)

        # Só chama cleanup se NÃO for tutorial (evita reset duplo)
        if not is_tutorial:
            self.cleanup()
        else:
            self._stop_all_sounds(fade_ms=1000)
            if hasattr(self, 'day_night_weather'):
                self.day_night_weather._initialized = False

            # Limpa apenas os spots, sem resetar os Pokémon
            for spot in self.spot_renderer.get_spots():
                spot.occupied = False

            # Limpa a lista de Pokémon colocados
            self.placed_pokemon.clear()
            self.placement_manager.placed_pokemon.clear()

            # NÃO RESETA OS POKÉMON AQUI

        self.update_box_happiness()
        self._start_battle_music()
        self.wave_manager.initialize_condition()

        # Reseta os Pokémon (cura)
        for pokemon in self.player.team:
            pokemon.reset(self)

        self._pokemon_defeated_this_phase = False

        # Se for tutorial, REDUZ o HP DEPOIS do reset
        if is_tutorial:
            self._apply_tutorial_setup()

        self.wave_manager.reset_gold()
        self.game_state = "waiting"

        import datetime as _dt
        self._phase_started_at = _dt.datetime.now()

        # ===== VERIFICA MÍTICO PENDENTE PARA ESTA FASE =====
        self._check_mythical_spawn()

        if not self.event_manager.triggers:
            self.game_state = "in_wave"
            self.wave_manager.start_all_waves()

        # Força a primeira sincronização (toca o clima inicial, se houver)
        self._sync_weather_animations()

    def restart(self):
        """Recomeça a mesma fase do zero."""
        self.__init__(
            self.game,
            chapter_id=self.chapter_id,
            phase_number=self.phase_number,
            region_id=self.region_id,
        )

        # ==================================================================
        # AVANÇO DE FASE / CAPÍTULO
        # ==================================================================
        def _phase_exists(self, chapter_id, phase_number):
            """Verifica se (chapter, phase) existe no catálogo pra região atual."""
            try:
                from src.config.phase_catalog import phase_catalog
                info = phase_catalog.get_phase_info(
                    self.region_id, chapter_id, phase_number,
                )
                return bool(info)
            except Exception:
                return False

        def _next_chapter_phase1(self, chapter_id):
            """
            Acha o próximo capítulo (>= chapter_id + 1) que tenha pelo menos
            a fase 1. Retorna (chapter, 1) ou (None, None).
            """
            # Limite superior generoso — cobre qualquer jogo.
            MAX_CHAPTERS = 32
            for c in range(chapter_id + 1, MAX_CHAPTERS + 1):
                if self._phase_exists(c, 1):
                    return c, 1
            return None, None

        def advance_level(self):
            """
            Avança pra próxima fase da MESMA região:
              1) tenta (chapter, phase + 1)
              2) se não existir, tenta (chapter + 1, phase 1) — próximo capítulo
              3) se não existir nada, retorna False (cena cai no menu)
            """
            # -------- 1) Próxima fase do capítulo atual --------
            if self._phase_exists(self.chapter_id, self.phase_number + 1):
                next_chapter = self.chapter_id
                next_phase = self.phase_number + 1
                print(f"[ADVANCE] {self.chapter_id}-{self.phase_number} "
                      f"→ {next_chapter}-{next_phase} (mesma capitulo)")
            else:
                # -------- 2) Próximo capítulo, fase 1 --------
                next_chapter, next_phase = self._next_chapter_phase1(self.chapter_id)
                if next_chapter is None:
                    print(f"[ADVANCE] Não há próxima fase nem próximo capítulo. "
                          f"Fim do conteúdo da região {self.region_id}.")
                    return False
                print(f"[ADVANCE] Fim do capítulo {self.chapter_id} "
                      f"→ capitulo {next_chapter}, fase 1")

            # -------- 3) Troca de cena --------
            self.game.current_scene = GameScene(
                self.game,
                chapter_id=next_chapter,
                phase_number=next_phase,
                region_id=self.region_id,
            )
            return True

    def _apply_tutorial_setup(self):
        """
        Aplica configuração especial para o tutorial (fase 1:1):
        - Reduz HP de todos os Pokémon do time pela metade (DEPOIS do reset)
        - Garante que o jogador tenha pelo menos 1 poção
        """
        print("[TUTORIAL] Aplicando setup da fase 1:1...")

        # ===== 1. REDUZ HP PELA METADE =====
        for pokemon in self.player.team:
            # Guarda o HP original antes de reduzir
            original_max_hp = pokemon.max_hp
            original_current_hp = pokemon.current_hp

            pokemon.current_hp = max(1, original_current_hp // 2)

            # Se o Pokémon ficou com 0 HP, garante que tenha pelo menos 1
            if pokemon.current_hp < 1:
                pokemon.current_hp = 1

            print(f"[TUTORIAL] {pokemon.name}: HP {original_max_hp} -> {pokemon.max_hp} | Atual: {pokemon.current_hp}")

        # ===== 2. GARANTE POÇÃO =====
        has_potion = self.player.bag.get_quantity("potion") > 1

        if not has_potion:
            self.player.bag.add_item("potion", 2)
            print("[TUTORIAL] 1 Poção adicionada ao jogador (precisa de 2)")
        else:
            print(f"[TUTORIAL] Jogador já tem {self.player.bag.get_quantity('potion')} poção(ões)")

        # ===== 3. LIMPA FLAGS DO EVENT PROCESSOR PARA O TUTORIAL =====
        if hasattr(self, 'event_processor'):
            self.event_processor.custom_flags.clear()
            print("[TUTORIAL] Flags do event_processor resetadas")

        # ===== 4. FORÇA O ESTADO DO JOGO PARA "WAITING" =====
        self.game_state = "waiting"
        print("[TUTORIAL] Estado do jogo definido como 'waiting' para o tutorial iniciar corretamente")

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        # Tenta novo formato (region, chapter, phase)
        try:
            self.phase_info = phase_catalog.get_phase_info(
                self.region_id, self.chapter_id, self.phase_number
            )
        except TypeError:
            # Fallback catálogo antigo
            self.phase_info = phase_catalog.get_phase_info(
                self.chapter_id, self.phase_number
            )

        if not self.phase_info:
            self.phase_info = {
                "name": f"Fase {self.chapter_id}-{self.phase_number}",
                "number": self.phase_number,
                "chapter": self.chapter_id,
                "region": self.region_id,
            }

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        data = phase_loader.load_phase(
            self.chapter_id,
            self.phase_number,
            region_id=getattr(self, 'region_id', DEFAULT_REGION_ID),
        )

        # ===== ARMAZENA OS DADOS DA FASE =====
        self._phase_data = data

        if not data:
            self.phase_rewards = {
                "money": 0,
                "experience": 0,
                "item_rewards": [],
                "drop_chance": 0.0,
                "max_items": 3,
                "template_name": None
            }
            return

        base_path = PROJECT_ROOT

        # Carrega componentes
        self.map_renderer.load_from_data(phase_loader.get_map_data(), base_path)
        self.path_renderer.load_from_data(phase_loader.get_paths_data())
        self.spot_renderer.load_from_data(phase_loader.get_tower_spots_data())
        self.target_item_manager.load_from_data(data.get("target_items", {}))

        # ===== CARREGA AS RECOMPENSAS (COM TODOS OS CAMPOS) =====
        rewards = data.get("rewards", {})
        self.phase_rewards = {
            "money": rewards.get("money", 0),
            "experience": rewards.get("experience", 0),
            "item_rewards": rewards.get("item_rewards", []),
            "drop_chance": rewards.get("drop_chance", 0.0),
            "max_items": rewards.get("max_items", 3),
            "template_name": rewards.get("template_name", None)
        }
        print(f"[GAME_SCENE] Recompensas carregadas: {self.phase_rewards}")

    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            self.world_width = 2000
            self.world_height = 2000

    # ==================================================================
    # SISTEMA DE MÍTICOS
    # ==================================================================

    def _check_mythical_spawn(self):
        """
        Verifica se há um mítico agendado para ESTA fase.
          - Se for a fase correta: arma o spawner e limpa o estado pendente.
          - Se for fase errada: LIMPA o estado pendente (jogador perdeu a chance)
            e mostra um toast avisando.
        """
        from src.data.mythical_catalog import MythicalCatalog
        from src.ui.toast_renderer import toast_battle

        pending_id = getattr(self.player, 'pending_mythical_id', None)
        pending_phase = getattr(self.player, 'pending_mythical_phase_id', None)

        # Nada agendado
        if not pending_id or not pending_phase:
            return

        # Mítico inválido (catálogo mudou) — limpa e sai
        if not MythicalCatalog.is_mythical(pending_id):
            print(f"[Mythical] ID {pending_id} não está mais no catálogo — limpando.")
            self._clear_pending_mythical()
            return

        entry = MythicalCatalog.get_mythical(pending_id)

        # ===== ACERTOU A FASE =====
        if pending_phase == self.phase_id:
            if hasattr(self, 'wave_manager') and getattr(self.wave_manager, 'spawner', None):
                self.wave_manager.spawner.set_mythical_to_spawn(pending_id)
                print(f"[Mythical]  {entry.name} vai aparecer na fase {self.phase_id}! ✨")
            self._clear_pending_mythical()
            return

        # ===== ERROU A FASE =====
        print(f"[Mythical] Jogador entrou em {self.phase_id} "
              f"mas {entry.name} estava agendado para {pending_phase}. "
              f"Chance perdida!")

        self._clear_pending_mythical()

        # Toast de "escapou"
        toast_battle(
            f"O {entry.name} fugiu... você escolheu a fase errada!",
            duration=5.0,
        )

    def _clear_pending_mythical(self):
        """Limpa o estado do mítico pendente do player e salva."""
        if not hasattr(self, 'player') or not self.player:
            return
        self.player.pending_mythical_id = None
        self.player.pending_mythical_phase_id = None
        self.player.auto_save()

    def _roll_mythical_chance(self):
        """
        Rola 10% de chance de agendar um mítico para uma fase futura.
        Só rola se:
          - jogador tem todas as insígnias (conquista all_badges)
          - não há mítico pendente no momento
        """
        import random
        from src.data.mythical_catalog import MythicalCatalog

        # ===== PRÉ-REQUISITO: TODAS AS INSÍGNIAS =====
        if not hasattr(self, 'player') or not hasattr(self.player, 'achievement_manager'):
            return
        if not self.player.achievement_manager.is_unlocked("all_badges"):
            return

        # ===== JÁ TEM UM PENDENTE? NÃO SORTEIA OUTRO =====
        if getattr(self.player, 'pending_mythical_id', None):
            return

        # ===== 10% DE CHANCE =====
        if random.random() >= MYTHICAL_SPAWN_CHANCE:
            return

        mythicals = MythicalCatalog.get_all()
        if not mythicals:
            return

        # Sorteia mítico + fase
        chosen = random.choice(mythicals)
        if not chosen.phases:
            return
        chosen_phase = random.choice(list(chosen.phases))

        self.player.pending_mythical_id = chosen.pokemon_id
        self.player.pending_mythical_phase_id = chosen_phase
        self.player.auto_save()

        print(f"[Mythical]  {chosen.name} agendado para a fase {chosen_phase} (10% roll)")

    def _show_game_over_scene(self, reason="team_defeated"):
        """
        Substitui `overlay_manager.show(OverlayType.GAME_OVER, ...)`.
        Monta o `stats` com o que temos disponível no estado atual.
        """
        # --- waves: usa a wave mais avançada entre os paths ---
        waves = 0
        try:
            wm = self.wave_manager
            idx_map = getattr(wm, "current_wave_idx", {}) or {}
            if idx_map:
                waves = max(int(v) for v in idx_map.values()) + 1
        except Exception:
            pass

        # --- score (que é o XP total acumulado do jogador) ---
        score = int(getattr(self.player, "score", 0))

        # --- subtítulo por motivo ---
        if reason == "items_stolen":
            subtitle = "Todos os itens foram roubados!"
        else:
            subtitle = "Sua jornada termina aqui... por enquanto."

        self.game.current_scene = GameOverScene(
            self.game,
            self,
            stats={
                "waves": waves,
                "score": score,
                "subtitle": subtitle,
            },
        )

    def _show_level_complete_scene(self):
        """
        Substitui `overlay_manager.show(OverlayType.PHASE_COMPLETE)`.
        Usa `self.phase_complete_data` que já foi montado em `_complete_phase`.
        """
        data = getattr(self, "phase_complete_data", {}) or {}

        # --- tempo decorrido desde o início da fase ---
        time_str = "—"
        started = getattr(self, "_phase_started_at", None)
        if started is not None:
            try:
                import datetime as _dt
                delta = _dt.datetime.now() - started
                total = int(delta.total_seconds())
                time_str = f"{total // 60:02d}:{total % 60:02d}"
            except Exception:
                time_str = "—"

        # --- próximo existe? (mesma fase +1 OU próximo capítulo fase 1) ---
        has_next = False
        try:
            if self._phase_exists(self.chapter_id, self.phase_number + 1):
                has_next = True
            else:
                nc, _np = self._next_chapter_phase1(self.chapter_id)
                has_next = (nc is not None)
        except Exception:
            has_next = True

        stars = int(data.get("stars", 3))
        xp_gained = int(data.get("total_xp", 0))

        self.game.current_scene = LevelCompleteScene(
            self.game,
            self,
            stats={
                "level": self.phase_info.get("name",
                                             f"Fase {self.chapter_id}-{self.phase_number}"),
                "stars": stars,
                "max_stars": 3,
                "score": int(getattr(self.player, "score", 0)),
                "xp_gained": xp_gained,
                "time": time_str,
                "has_next": has_next,
            },
        )

    def _update_perf_monitor(self):
        """Atualiza o estado do monitor de performance baseado no debug"""
        perf_monitor.set_enabled(self.show_debug)
        if self.show_debug:
            # Reseta as métricas quando ativa
            perf_monitor.reset()

    def update_box_happiness(self):
        """
        Diminui felicidade dos Pokémon na PC Box em -1 por fase.
        SIMULA O ABANDONO: Pokémon na box perdem felicidade.
        OTIMIZADO: Trabalha diretamente com dicionários e salva as alterações.
        """
        if not hasattr(self.player, 'pc_box'):
            return

        box_data = self.player.pc_box  # lista de dicionários
        if not box_data:
            return

        # Conjunto de unique_ids dos Pokémon no time (para saber quem está na box)
        team_ids = {p.unique_id for p in self.player.team}

        updated_count = 0
        skipped_count = 0

        for data in box_data:
            unique_id = data.get("unique_id")
            if not unique_id:
                continue

            # Se o Pokémon está no time, NÃO está na box (não perde felicidade)
            if unique_id in team_ids:
                skipped_count += 1
                continue

            # ===== TRABALHA DIRETAMENTE COM O DICIONÁRIO =====
            # Pega a felicidade atual (padrão 0 se não existir)
            current_happiness = data.get("happiness", 0)

            # Aplica -1 (mínimo 0)
            if current_happiness > 0:
                data["happiness"] = current_happiness - 1
                updated_count += 1

                # Se a felicidade caiu abaixo de 255, remove flag de evolução pendente
                if data["happiness"] < 255 and data.get("pending_happiness_evolution"):
                    data["pending_happiness_evolution"] = False
                    print(f"[BOX] {data.get('name', 'Unknown')} perdeu a condição de evoluir por felicidade")
            # Se já está em 0, mantém

        if updated_count > 0:
            print(
                f"[BOX_HAPPINESS] {updated_count} Pokémon perderam -1 de felicidade | {skipped_count} no time ignorados")

            # ===== SALVA AS ALTERAÇÕES =====
            # Importante: Salva para persistir a mudança de felicidade
            self.player.auto_save()
            print(f"[BOX_HAPPINESS] Save atualizado com novas felicidades da box")
        else:
            if skipped_count > 0:
                print(
                    f"[BOX_HAPPINESS] Nenhum Pokémon na box para perder felicidade. {skipped_count} no time ignorados")
            else:
                print(f"[BOX_HAPPINESS] Nenhum Pokémon na box para perder felicidade")

    def is_team_defeated(self) -> bool:
        """
        Verifica se todos os Pokémon do time estão derrotados.
        Retorna True se não houver nenhum Pokémon vivo no time.
        """
        # Verifica se o time está vazio
        if not self.player.team:
            return True

        # Verifica se TODOS os Pokémon estão derrotados
        for pokemon in self.player.team:
            # Se encontrar algum Pokémon vivo, o time ainda está OK
            if pokemon.is_alive():
                return False

        # Se chegou aqui, todos estão derrotados
        toast_info(f"Time inteiro derrotado!", duration=4.0)

        # ===== RESETA DITTOS TRANSFORMADOS EM CASO DE GAME OVER =====
        self.reset_all_transformed_dittos()

        return True

    def _sync_weather_animations(self):
        """Sincroniza a animação visual com o clima/período atual.

        Só age quando a CHAVE muda. As animações de clima SÃO PERMANENTES
        (loop: true no JSON), então o Animator nunca morre sozinho.
        """
        from src.anim.animation_manager import animation_manager

        # ----- 1. Chave desejada -----
        current_weather = None
        if hasattr(self, 'battle_system') and self.battle_system:
            w = self.battle_system.weather_manager.current_weather
            if w and w.active:
                current_weather = w.type.value

        current_period = None
        if (hasattr(self, 'day_night_weather')
                and self.day_night_weather.day_night_state):
            current_period = self.day_night_weather.day_night_state.type.value

        # ----- 2. Define key -----
        if current_weather and current_weather != "none":
            key = f"weather/{current_weather}"
        elif current_period and current_period != "day":
            key = f"weather/{current_period}"
        else:
            key = None

        # ----- 3. Nada mudou? Sai -----
        if self._current_weather_key == key:
            return

        old_key = self._current_weather_key
        self._current_weather_key = key

        # ----- 4. Para a anterior -----
        if old_key:
            animation_manager.stop(old_key)
            print(f"[WEATHER-ANIM] stop {old_key}")

        # ----- 5. Toca a nova -----
        if key:
            cx = (self.screen_manager.viewport_x
                  + self.screen_manager.viewport_width // 2)
            cy = (self.screen_manager.viewport_y
                  + self.screen_manager.viewport_height // 2)
            anim = animation_manager.play(
                key, screen_pos=(cx, cy), loop_override=True,
            )
            print(f"[WEATHER-ANIM] play {key}" if anim else
                  f"[WEATHER-ANIM] ERRO: {key} não encontrada")

    # ===== MÉTODOS DE OVERLAY  =====

    def open_move_select_overlay(self, pokemon):
        if not pokemon or not pokemon.moves:
            return

        if hasattr(self, 'event_processor'):
            expected = self.event_processor.get_next_custom_flag()
            if expected is None:
                pass
            elif expected == "abriu_move_select":
                self.event_processor.custom_flags["abriu_move_select"] = True
            else:
                toast_warning("Complete a etapa anterior primeiro!", duration=5.0)
                return

        from src.scenes.game_scene.components.overlays.move_select.move_select_scene import (
            MoveSelectScene,
        )
        # A cena cuida de pausar o game_scene
        self.game.current_scene = MoveSelectScene(self.game, self, pokemon)

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de moves"""
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    def show_capture_overlay(self, pokemon, is_to_team=True):
        """Mostra o overlay de captura de Pokémon"""
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

        sound_manager.play_effect(SoundEffect.CAUGHT)
        self.overlay_manager.show(OverlayType.CAPTURE, pokemon=pokemon, is_to_team=is_to_team)

    def close_capture_overlay(self):
        """Fecha o overlay de captura"""
        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False
        self.overlay_manager.hide()

    # ==================================================================
    # OVERLAY: MOVE LEARN
    # ==================================================================
    def open_move_learn_overlay(self, pokemon, new_move_name):
        """Abre o overlay de aprendizado de novo move (agora como cena)."""
        from src.scenes.game_scene.components.overlays.move_learn.move_learn_scene import (
            MoveLearnScene,
        )

        # ===== GUARDA 1: evolução ativa? DEFERE =====
        if (hasattr(self, 'evolution_overlay')
                and self.evolution_overlay
                and self.evolution_overlay.active):
            print(f"[MOVE_LEARN] Evolução ativa — adiando '{new_move_name}' em {pokemon.name}")
            self.pending_move_learn = (pokemon, new_move_name)
            return

        # ===== GUARDA 2: já existe um move_learn_scene ativo? DEFERE =====
        from src.scenes.game_scene.components.overlays.move_learn.move_learn_scene import (
            MoveLearnScene as _MLS,
        )
        if isinstance(self.game.current_scene, _MLS):
            print(f"[MOVE_LEARN] Cena já ativa — adiando '{new_move_name}' em {pokemon.name}")
            if not hasattr(pokemon, '_pending_moves_to_learn'):
                pokemon._pending_moves_to_learn = []
            pokemon._pending_moves_to_learn.insert(0, new_move_name)
            return

        # ===== Troca a cena (a cena pausa o game_scene internamente) =====
        self.game.current_scene = MoveLearnScene(
            self.game, self, pokemon, new_move_name,
        )

    def close_move_learn_overlay(self, cancel=False):
        """
        Compatibilidade: agora a cena nova faz o unpause sozinha.
        Este método só existe se algo legado chamar.
        """
        if cancel:
            # Descarta fila de moves pendentes
            if hasattr(self, 'pending_move_learn') and self.pending_move_learn:
                self.pending_move_learn = None
            if hasattr(self, 'player') and self.player and self.player.team:
                for p in self.player.team:
                    if hasattr(p, '_pending_moves_to_learn'):
                        p._pending_moves_to_learn = []

        # Retoma a fila de moves pendentes (level up em cadeia)
        if not cancel:
            # Prioridade A: pending_move_learn (TM adiada)
            if hasattr(self, 'pending_move_learn') and self.pending_move_learn:
                pokemon, move_name = self.pending_move_learn
                self.pending_move_learn = None
                self.open_move_learn_overlay(pokemon, move_name)
                return

            # Prioridade B: fila do pokemon
            pokemon_with_pending = None
            for p in (self.player.team if hasattr(self, 'player') and self.player else []):
                if getattr(p, '_pending_moves_to_learn', None):
                    pokemon_with_pending = p
                    break

            if pokemon_with_pending:
                pokemon_with_pending.evolution._process_pending_moves()
                return

        # Sem pendências: retoma
        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    # ==================================================================
    # OVERLAY: EVOLUÇÃO
    # ==================================================================
    def open_evolution_overlay(self, pokemon, evolution_data):
        """Abre o overlay de evolução. Sempre tem PRIORIDADE máxima."""
        # ===== GUARDA: se já tem um overlay de evolução ativo, ignora =====
        if (hasattr(self, 'evolution_overlay')
                and self.evolution_overlay
                and self.evolution_overlay.active):
            print(f"[EVOLUTION] Overlay já ativo — ignorando chamada para {pokemon.name}")
            return

        # ===== Se houver move_learn_overlay ativo, guarda pra reabrir depois =====
        if self.move_learn_overlay and self.move_learn_overlay.active:
            try:
                pending_pokemon = self.move_learn_overlay.pokemon
                pending_move = self.move_learn_overlay.new_move_name
                # Coloca na frente da fila do pokémon
                if not hasattr(pending_pokemon, '_pending_moves_to_learn'):
                    pending_pokemon._pending_moves_to_learn = []
                pending_pokemon._pending_moves_to_learn.insert(0, pending_move)
                # Fecha o overlay atual (sem processar fila)
                self.move_learn_overlay.active = False
                self.move_learn_overlay = None
                print(f"[EVOLUTION] Move learn overlay fechado para dar prioridade à evolução")
            except Exception as e:
                print(f"[EVOLUTION] Erro ao guardar move pendente: {e}")
                self.move_learn_overlay = None

        # ===== Guarda o método e dados para estatísticas =====
        if hasattr(pokemon, 'evolution'):
            method = evolution_data.get("method", "unknown")
            pokemon.evolution._pending_evolution_method = method

            if method == "happiness" and "time_of_day" in evolution_data:
                pokemon._last_evolution_time_of_day = evolution_data.get("time_of_day")

            pokemon._last_evolution_data = evolution_data

        sound_manager.play_effect(SoundEffect.EVOLUTION)
        self.evolution_overlay = EvolutionOverlay(self, pokemon, evolution_data)
        self.evolution_overlay.active = True

        # Estado de pausa
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_evolution_overlay(self, cancel=False):
        """Fecha o overlay de evolução e processa a fila de moves."""
        sound_manager.stop_effect(SoundEffect.EVOLUTION)

        if hasattr(self, 'evolution_overlay'):
            self.evolution_overlay = None

        # ==================================================================
        # CANCELADO: descarta os moves pendentes e retoma o jogo
        # ==================================================================
        if cancel:
            print(f"[EVOLUTION] Cancelado — descartando moves pendentes")
            # Move pendente (TM)
            if hasattr(self, 'pending_move_learn') and self.pending_move_learn:
                self.pending_move_learn = None
            # Fila de moves do level up
            if hasattr(self, 'player') and self.player and self.player.team:
                for p in self.player.team:
                    if hasattr(p, '_pending_moves_to_learn'):
                        p._pending_moves_to_learn = []

            self.paused = False
            self.game_paused = False
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = False
            return

        # ==================================================================
        # NÃO CANCELADO: verifica se há moves a aprender
        # ==================================================================

        # ----- Prioridade A: pending_move_learn (TM adiada durante evolução) -----
        if hasattr(self, 'pending_move_learn') and self.pending_move_learn:
            pokemon, move_name = self.pending_move_learn
            self.pending_move_learn = None
            print(f"[EVOLUTION] Abrindo move learn pendente (TM): '{move_name}' em {pokemon.name}")
            # Vai setar paused internamente
            self.open_move_learn_overlay(pokemon, move_name)
            return

        # ----- Prioridade B: fila de moves do level up -----
        # Busca no time quem tem fila de moves pendentes
        pokemon_with_pending = None
        for p in (self.player.team if hasattr(self, 'player') and self.player else []):
            if getattr(p, '_pending_moves_to_learn', None):
                pokemon_with_pending = p
                break

        if pokemon_with_pending:
            print(f"[EVOLUTION] Evolução fechada. Processando fila de "
                  f"{len(pokemon_with_pending._pending_moves_to_learn)} move(s) "
                  f"pendente(s) de {pokemon_with_pending.name}")
            # Não desliga o paused: vamos reabrir outro overlay
            pokemon_with_pending.evolution._process_pending_moves()
            return

        # ----- Sem pendências: retoma o jogo -----
        self.paused = False
        self.game_paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    # ===== MÉTODOS DE ITEM E CAPTURA =====

    def _on_item_use(self, target, item_data, target_type):
        """Callback quando um item é usado em um alvo."""
        effect = item_data.get("effect", "")
        category = item_data.get("category", "")

        print(f"[ITEM USE] Categoria: {category}, Efeito: {effect}, Alvo: {target_type}")

        # ===== CURAS DE STATUS =====
        if effect == "cure_status":
            if target_type == "ally":
                from src.battle.effects.status_effect import StatusType
                status_to_cure = item_data.get("effect_value")

                status_map = {
                    "paralysis": StatusType.PARALYSIS,
                    "sleep": StatusType.SLEEP,
                    "poison": StatusType.POISON,
                    "burn": StatusType.BURN,
                    "freeze": StatusType.FREEZE,
                }

                status_type = status_map.get(status_to_cure)
                if status_type:
                    current_status = self.battle_system.effect_manager.get_status(target)
                    if current_status and current_status.type == status_type:
                        self._play_item_spray_animation(item_data.get("id", ""), target)
                        self.battle_system.effect_manager.remove_status(target)
                        toast_battle(f"{target.name} curou {status_to_cure}!", duration=4.0, pokemon=target,
                                     portrait="happy")

                        # ===== CONQUISTAS: CURA DE STATUS =====
                        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                            ach_mgr = self.player.achievement_manager

                            # Cura de Veneno com Antídoto
                            if status_to_cure == "poison" and item_data.get("id") == "antidote":
                                ach_mgr.increment_counter("antidote_count")
                                ach_mgr.check_and_unlock("first_antidote", self.phase_id)
                                ach_mgr.check_and_unlock("antidote_100", self.phase_id)

                            # Cura de Sono com Awakening
                            elif status_to_cure == "sleep" and item_data.get("id") == "awakening":
                                ach_mgr.increment_counter("awake_count")
                                ach_mgr.check_and_unlock("first_awake", self.phase_id)
                                ach_mgr.check_and_unlock("awake_100", self.phase_id)

                            # Cura de Paralisia
                            elif status_to_cure == "paralysis":
                                ach_mgr.increment_counter("paralyze_heal_count")
                                ach_mgr.check_and_unlock("first_paralyze_heal", self.phase_id)
                                ach_mgr.check_and_unlock("paralyze_heal_100", self.phase_id)

                            # Cura de Queimadura =====
                            elif status_to_cure == "burn" and item_data.get("id") == "burn_heal":
                                ach_mgr.increment_counter("burn_heal_count")
                                ach_mgr.check_and_unlock("first_burn_heal", self.phase_id)
                                ach_mgr.check_and_unlock("burn_heal_10", self.phase_id)

                            # Cura de Congelamento =====
                            elif status_to_cure == "freeze" and item_data.get("id") == "ice_heal":
                                ach_mgr.increment_counter("freeze_heal_count")
                                ach_mgr.check_and_unlock("first_freeze_heal", self.phase_id)
                                ach_mgr.check_and_unlock("freeze_heal_10", self.phase_id)

                        return True
                return False

        # ===== CURA TODOS STATUS (full_heal) =====
        elif effect == "cure_all_status":
            if target_type == "ally":
                current_status = self.battle_system.effect_manager.get_status(target)
                if current_status and current_status.type.value != "none":
                    self._play_item_spray_animation(item_data.get("id", ""), target)
                    self.battle_system.effect_manager.remove_status(target)
                    self.battle_system.effect_manager.add_status_text(target, "todos os status curados!")
                    toast_battle(f"{item_data['name']} usado em {target.name}!", duration=4.0, pokemon=target,
                                 portrait="happy")
                    return True
                return False

        # ===== RESTAURA PP =====
        elif effect == "pp_restore":
            if target_type == "ally" and hasattr(target, 'restore_pp'):
                percentage = item_data.get("effect_value", 1.0)
                restored = target.restore_pp(percentage=percentage)
                if restored > 0:
                    toast_battle(f"{item_data['name']} usado em {target.name}! {restored} PP restaurados!!",
                                 duration=4.0, pokemon=target, portrait="happy")
                    return True
                return False

        # ===== ITENS DE BATALHA =====
        elif effect == "battle_stat_boost":
            if target_type == "ally":
                return self._apply_battle_item(target, item_data)

        elif effect == "escape_phase":
            if target_type == "ally":
                # Verifica se o Pokémon está vivo
                if not target.is_alive():
                    toast_warning(f"{target.name} está derrotado! Não pode usar ESCAPEROPE.", duration=2.0)
                    return {"consume_item": False, "success": False}

                # Fuga sem penalidades
                self.escape_phase()
                return {"consume_item": True, "success": True}

        # ===== PEDRA DE EVOLUÇÃO =====
        elif effect == "evolution":
            if target_type == "ally":
                success = self._use_evolution_stone(target, item_data)
                return success

        # ===== TM =====
        elif effect == "teach_move":
            if target_type == "ally":
                move_to_teach = item_data.get("effect_value")
                success = self._teach_move_to_pokemon(target, move_to_teach, item_data)
                return success

        # ===== POKÉBOLA =====
        elif target_type == "enemy" and category == "pokeball":
            if hasattr(target, 'is_boss') and target.is_boss:
                toast_battle(f"Não é possível capturar {target.name}!", duration=2.0, pokemon=target, portrait="angry")
                return False  # BOSS: NÃO consome a pokébola

            self._attempt_capture(target, item_data)
            return True

        elif effect == "level_up":
            if target_type == "ally":
                pokemon = target
                if pokemon.is_defeated:
                    toast_warning(f"{pokemon.name} está derrotado! Não pode usar Rare Candy.", duration=2.0)
                    return False

                old_level = pokemon.level
                xp_needed = pokemon.xp_to_next
                pokemon.gain_xp(xp_needed)
                new_level = pokemon.level

                if new_level > old_level:
                    toast_battle(
                        f"{pokemon.name} subiu para o nível {new_level}!",
                        duration=4.0,
                        pokemon=pokemon,
                        portrait="joyous"
                    )
                    # ===== CONQUISTAS: RARE CANDY =====
                    if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                        ach_mgr = self.player.achievement_manager
                        ach_mgr.increment_counter("rare_candy_count")
                        ach_mgr.check_and_unlock("rare_candy_3", self.phase_id)
                    return True
                else:
                    return False

        # ===== MEDICAMENTOS (poções e revives) =====
        elif target_type == "ally" and category == "medicine":
            if hasattr(self, 'event_processor'):
                expected = self.event_processor.get_next_custom_flag()
                if expected is None:
                    pass
                elif expected == "curou_pokemon":
                    self.event_processor.custom_flags["curou_pokemon"] = True
                else:
                    toast_warning("Complete a etapa anterior primeiro!", duration=5.0)
                    return False

            # ===== ANIMAÇÃO DE SPRAY =====
            # Só toca se o Pokémon estiver vivo (revive tem outro tratamento abaixo)
            if target.is_alive():
                self._play_item_spray_animation(item_data.get("id", ""), target)

            medicine_success = self.use_medicine(target, item_data)
            return medicine_success

        return False

    # ==================================================================
    # ANIMAÇÃO DE SPRAY PARA ITENS MEDICINAIS
    # ==================================================================
    def _play_item_spray_animation(self, item_id: str, target):
        print(f"[SPRAY-DBG] 1. entrou | item={item_id!r} | target={getattr(target, 'name', '?')}")

        if target is None:
            print("[SPRAY-DBG] 2. ABORTADO: target é None")
            return
        if not hasattr(target, 'x'):
            print(f"[SPRAY-DBG] 2. ABORTADO: target sem .x (attrs: {dir(target)[:5]}...)")
            return

        from src.anim.animation_registry import animation_registry
        from src.anim.animation_manager import animation_manager

        print(f"[SPRAY-DBG] 3. registry.loaded={animation_registry.loaded} | "
              f"anims={len(animation_registry._cache)} | "
              f"bindings={len(animation_registry._bindings)}")

        trigger = f"item.{item_id}.use_on_ally"
        print(f"[SPRAY-DBG] 4. trigger={trigger!r}")

        defn = animation_registry.resolve_trigger(trigger)
        if defn is None:
            print(f"[SPRAY-DBG] 5. ABORTADO: resolve_trigger retornou None")
            print(f"[SPRAY-DBG]    bindings disponíveis: {list(animation_registry._bindings.keys())}")
            print(f"[SPRAY-DBG]    keys disponíveis: {animation_registry.all_keys()}")
            return

        print(f"[SPRAY-DBG] 6. defn encontrado: {defn.name} | "
              f"space={defn.space} | anchor={defn.anchor} | "
              f"dur={defn.duration_frames}f")

        anim = animation_manager.play_by_trigger(trigger, anchor_target=target)
        print(f"[SPRAY-DBG] 7. animator criado: {anim is not None} | "
              f"active agora: {animation_manager.count_active()}")

    def _apply_battle_item(self, pokemon, item_data):
        """Aplica um item de batalha (X-Item) ao Pokémon alvo."""
        from src.battle.effects.stat_modifier import StatType

        effect_value = item_data.get("effect_value", {})
        stat_key = effect_value.get("stat")
        stages = effect_value.get("stages", 1)
        duration = effect_value.get("duration", 15.0)

        # Mapeia string para StatType
        stat_map = {
            "attack": StatType.ATTACK,
            "defense": StatType.DEFENSE,
            "sp_attack": StatType.SP_ATTACK,
            "sp_defense": StatType.SP_DEFENSE,
            "speed": StatType.SPEED,
            "accuracy": StatType.ACCURACY,
            "evasion": StatType.EVASION
        }
        stat_type = stat_map.get(stat_key)
        if not stat_type:
            print(f"[BATTLE_ITEM] Stat inválido: {stat_key}")
            return False

        # Verifica se já existe um buff de batalha ativo (qualquer stat)
        battle_buff = self.battle_system.effect_manager.get_battle_item_buff(pokemon)
        if battle_buff:
            # Substitui: remove o antigo
            old_stat = battle_buff["stat"]
            # O modificador antigo será removido automaticamente quando expirar, mas vamos forçar remoção agora
            self.battle_system.effect_manager.remove_battle_item_buff(pokemon)
            # Conquista de substituição
            if hasattr(self.player, 'achievement_manager'):
                self.player.achievement_manager.increment_counter("battle_item_replace_count")
                self.player.achievement_manager.check_and_unlock("battle_item_replace", self.phase_id)
            # Mensagem de substituição
            self.battle_system.effect_manager.add_status_text(
                pokemon,
                f"Buff de batalha substituído!",
                duration=1.5
            )

        # Aplica o novo buff via EffectManager, marcando como item de batalha
        self.battle_system.effect_manager.add_stat_modifier(
            pokemon,
            stat_type,
            stages,
            duration,
            is_battle_item=True
        )

        # Armazena o buff ativo no EffectManager
        self.battle_system.effect_manager.set_battle_item_buff(pokemon, stat_type, duration)

        # Feedback visual
        stat_name_pt = {
            StatType.ATTACK: "Ataque",
            StatType.DEFENSE: "Defesa",
            StatType.SP_ATTACK: "Ataque Especial",
            StatType.SP_DEFENSE: "Defesa Especial",
            StatType.SPEED: "Velocidade",
            StatType.ACCURACY: "Precisão",
            StatType.EVASION: "Evasão"
        }.get(stat_type, stat_key)

        self.battle_system.effect_manager.add_status_text(
            pokemon,
            f"{item_data['name']} usado! {stat_name_pt} +{stages} por {duration:.0f}s!",
            duration=2.0
        )

        # Conquista de uso de item de batalha
        if hasattr(self.player, 'achievement_manager'):
            self.player.achievement_manager.increment_counter("battle_item_use_count")
            self.player.achievement_manager.check_and_unlock("battle_item_use_10", self.phase_id)

        # Consome o item (retorna True)
        return True

    def _use_evolution_stone(self, pokemon, item_data):
        """Usa pedra de evolução em um Pokémon. Bloqueado por Everstone."""
        from src.managers.evolution_manager import evolution_manager

        # ===== EVERSTONE: bloqueia evolução por pedra =====
        if hasattr(pokemon, 'is_holding_everstone') and pokemon.is_holding_everstone():
            toast_battle(
                f"{pokemon.name} está segurando Everstone e não pode evoluir!",
                duration=3.0,
                pokemon=pokemon,
                portrait="sad"
            )
            print(f"[EVERSTONE] {pokemon.name} bloqueou evolução por pedra — item NÃO consumido")
            # NÃO consome a pedra
            return {"consume_item": False, "success": False}

        stone_name = item_data["id"]
        evolution = evolution_manager.check_evolution(pokemon.id, stone_name=stone_name)

        if not evolution:
            return {
                "consume_item": False,
                "success": False,
                "message": f"{pokemon.name} não pode evoluir com {item_data['name']}!"
            }

        evolve_to_id = evolution["evolve_to"]

        if hasattr(pokemon, 'evolution'):
            pokemon.evolution._pending_evolution_method = "stone"

        pokemon._last_evolution_data = evolution

        pokemon._perform_evolution(evolve_to_id)

        self.player.caught_pokemon.add(evolve_to_id)
        self.player.register_seen(evolve_to_id)

        self.player.auto_save()

        toast_battle(
            f"{pokemon.name} evoluiu para {pokemon.get_display_name()}!",
            duration=3.0,
            pokemon=pokemon,
            portrait="joyous"
        )

        sound_manager.play_effect(SoundEffect.EVOLUTION)

        print(f"[STONE_EVOLUTION] {pokemon.name} evoluiu com {item_data['name']}!")

        return {"consume_item": True, "success": True}

    def _teach_move_to_pokemon(self, pokemon, move_name, item_data):
        """Ensina um move a um Pokémon usando TM"""
        from src.entities.move import Move
        from src.data.move_data import MoveData

        move_data = MoveData()
        move_info = move_data.get_move_info(move_name)

        if not move_info:
            print(f"[TM] Move {move_name} não encontrado!")
            self.player.bag.add_item(item_data["id"], 1)
            return False

        # Verifica se já sabe o move
        for existing_move in pokemon.moves:
            if existing_move.name.lower() == move_name.lower():
                print(f"[TM] {pokemon.name} já sabe {move_name}!")
                self.player.bag.add_item(item_data["id"], 1)
                return False

        # Se tem menos de 4 moves, aprende direto
        if len(pokemon.moves) < 4:
            new_move = Move(move_name, move_info)
            pokemon.moves.append(new_move)
            print(f"[TM] {pokemon.name} aprendeu {move_name} via TM!")
            pokemon.add_happiness(5, f"Usou {item_data.get('name', 'Aprendeu um move')}")
            # ===== CONQUISTAS: Ensino de Moves =====
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                ach_mgr = self.player.achievement_manager
                ach_mgr.increment_counter("move_taught_count")
                ach_mgr.check_and_unlock("first_move_taught", self.phase_id)
                ach_mgr.check_and_unlock("move_taught_10", self.phase_id)

            return True

        # ===== Se tem 4 moves, usa o MoveLearnOverlay existente =====
        self.pending_tm_data = {
            "item_id": item_data["id"],
            "move_name": move_name,
            "move_info": move_info
        }
        pokemon.add_happiness(5, f"Usou {item_data.get('name', 'Aprendeu um move')}")
        self.open_move_learn_overlay(pokemon, move_name)
        return True

    def _attempt_capture(self, enemy, item_data):
        """Tenta capturar um Pokémon selvagem (com animação de pokébola)."""
        import random

        # BOSS não pode ser capturado
        if hasattr(enemy, 'is_boss') and enemy.is_boss:
            toast_battle(f"Não é possível capturar {enemy.name}!",
                         duration=2.0, pokemon=enemy, portrait="angry")
            return

        self._last_capture_item = item_data.get("id")

        hp_ratio = enemy.current_hp / enemy.max_hp
        base_chance = (1 - hp_ratio * 0.5)

        multipliers = {
            "pokeball": 1.0,
            "greatball": 1.5,
            "ultraball": 2.0,
            "masterball": 100.0,
            "friendball": 1.0,
        }
        multiplier = multipliers.get(item_data["id"], 1.0)
        chance = min(1.0, base_chance * multiplier)

        roll = random.random()
        print(f"[CAPTURE] Chance: {chance:.2f}, Roll: {roll:.2f}, Item: {item_data['id']}")

        # Decide sucesso/fracasso ANTES da animação (só pra alimentá-la)
        if item_data["id"] == "masterball":
            is_success = True
            num_shakes = 3
        else:
            is_success = roll < chance
            num_shakes = 3 if is_success else random.randint(1, 2)

        self._start_capture_shake(enemy, item_data, num_shakes, is_success)

    def _start_capture_shake(self, enemy, item_data, num_shakes, is_success):
        """Inicia a animação de captura (pokébola + pokémon)."""
        from src.scenes.game_scene.components.capture_shake_animation import (
            CaptureShakeAnimation,
        )
        from src.data.item_bag_catalog import item_bag_catalog

        # Carrega os frames do IN_MAP (closed/impact/half/open)
        ball_frames = item_bag_catalog.get_in_map_frames(item_data["id"])

        # Fallback: sprite normal pra todos os frames
        if ball_frames is None:
            single = item_bag_catalog.get_sprite(item_data["id"], scaled=True)
            if single is None:
                print("[CAPTURE_ANIM] sem sprite de bola — executa direto")
                if is_success:
                    self._perform_capture(enemy)
                else:
                    toast_battle(f"{enemy.name} escapou...",
                                 duration=2.0, pokemon=enemy, portrait="angry")
                    self._last_capture_item = None
                return
            ball_frames = {
                "closed": single, "impact": single,
                "half": single, "open": single,
            }

        # ===== USA O SPRITE ATUAL DO INIMIGO (mesmo que ele renderiza) =====
        # É EXATAMENTE o que o inimigo mostraria no mapa, então casa 1:1.
        pokemon_sprite = getattr(enemy, 'sprite', None)

        # Fallback: se por algum motivo não tiver, pega do inmap "down" frame 0
        if pokemon_sprite is None:
            try:
                from src.data.pokedex import Pokedex
                pokedex = Pokedex()
                inmap_frames = pokedex.get_inmap_animation(enemy.id, enemy.is_shiny)
                if inmap_frames and "down" in inmap_frames and inmap_frames["down"]:
                    pokemon_sprite = inmap_frames["down"][0]
            except Exception as e:
                print(f"[CAPTURE_ANIM] Não consegui pegar in-map sprite: {e}")

        if pokemon_sprite is None:
            print("[CAPTURE_ANIM] sem sprite de pokémon — executa direto")
            if is_success:
                self._perform_capture(enemy)
            else:
                toast_battle(f"{enemy.name} escapou...",
                             duration=2.0, pokemon=enemy, portrait="angry")
                self._last_capture_item = None
            return

        print(f"[CAPTURE_ANIM] _start | sprite="
              f"{'OK' if pokemon_sprite else 'None'} | "
              f"size={pokemon_sprite.get_size()} | "
              f"shakes={num_shakes} | success={is_success}")

        enemy._capture_hidden = True

        anim = CaptureShakeAnimation(
            self, enemy, ball_frames, pokemon_sprite,
            num_shakes, is_success,
            pokemon_base_scale=1.0,  # não precisa mais; sprite já é o certo
        )

        def _on_complete(success):
            print(f"[CAPTURE_ANIM] _on_complete | success={success}")
            if hasattr(enemy, '_capture_hidden'):
                del enemy._capture_hidden
            if success:
                self._perform_capture(enemy)
            else:
                toast_battle(f"{enemy.name} escapou...",
                             duration=2.0, pokemon=enemy, portrait="angry")
                print(f"[CAPTURE] {enemy.name} escapou!")
                self._last_capture_item = None

        anim.on_complete = _on_complete
        self.capture_shake_animation = anim

    def _perform_capture(self, enemy):
        """Executa a captura de um Pokémon"""
        carried_item = enemy.is_carrying
        if carried_item:
            enemy.drop_item()

        self.wave_manager.remove_enemy(enemy)

        from src.entities.pokemon import Pokemon
        caught = Pokemon(
            enemy.x, enemy.y,
            enemy.id,
            level=enemy.level,
            is_wild=False,
            shiny=enemy.is_shiny
        )

        if enemy.held_item:
            # Copia o ID
            caught.held_item = enemy.held_item

            # Copia os dados completos (name, description, sprite_path, etc)
            # Se por algum motivo enemy.held_item_data estiver vazio (ex: save antigo),
            # recarrega direto do catálogo como fallback.
            if getattr(enemy, 'held_item_data', None):
                caught.held_item_data = enemy.held_item_data
            else:
                from src.data.item_bag_catalog import item_bag_catalog
                item_data = item_bag_catalog.get_item(enemy.held_item)
                if item_data and item_data.get("id") == enemy.held_item:
                    caught.held_item_data = item_data
                else:
                    # Item não existe mais no catálogo — limpa pra não quebrar
                    print(f"[CAPTURE] Aviso: item '{enemy.held_item}' não está no catálogo, ignorando.")
                    caught.held_item = None
                    caught.held_item_data = None
        else:
            caught.held_item = None
            caught.held_item_data = None

        # ===== DEFINE DATA E MÉTODO DE CAPTURA =====
        caught.capture_date = datetime.now().isoformat()

        # Verifica qual item foi usado para capturar
        if hasattr(self, '_last_capture_item'):
            if self._last_capture_item == "masterball":
                caught.capture_method = "capture_masterball"
            elif self._last_capture_item == "greatball":
                caught.capture_method = "capture_greatball"
            elif self._last_capture_item == "ultraball":
                caught.capture_method = "capture_ultraball"
            elif self._last_capture_item == "friendball":
                caught.capture_method = "capture_friendball"
            else:
                caught.capture_method = "capture_pokeball"
        else:
            caught.capture_method = "capture"

        caught.current_hp = enemy.current_hp
        caught.max_hp = enemy.max_hp
        caught.ivs = enemy.ivs.copy()
        caught.evs = enemy.evs.copy()
        caught.xp = enemy.xp
        caught.nature = enemy.nature

        # ===== FRIEND BALL: APLICA BÔNUS DE FELICIDADE =====
        # Verifica se foi capturado com Friend Ball
        if hasattr(self, '_last_capture_item') and self._last_capture_item == "friendball":
            happiness_bonus = 60
            caught.set_happiness(happiness_bonus)
            print(f"[FRIEND_BALL] {caught.name} capturado com {happiness_bonus} de felicidade!")
            # Mostra toast especial
            toast_battle(
                f"{caught.name} veio com {happiness_bonus} de felicidade!️",
                duration=4.0,
                pokemon=caught,
                portrait="happy"
            )

            # ===== INCREMENTA CONTADOR DA FRIEND BALL =====
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                ach_mgr = self.player.achievement_manager
                ach_mgr.increment_counter("friendball_capture_count")
                ach_mgr.check_and_unlock("friendball_capture_5", self.phase_id)

            # Limpa a flag
            self._last_capture_item = None

        is_to_team = self.player.has_team_space()
        if is_to_team:
            toast_battle(f"{caught.name} foi adicionado ao time!", duration=4.0, pokemon=caught, portrait="happy")
            self.player.add_to_team(caught)
        else:
            toast_battle(f"{caught.name} foi adicionado à box!", duration=4.0, pokemon=caught)
            self.player.add_to_box(caught)

        self.player.caught_pokemon.add(enemy.id)
        self.player.register_seen(enemy.id)
        self.player.auto_save()

        # ===== CONQUISTAS: Captura =====
        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
            ach_mgr = self.player.achievement_manager

            # Incrementa contador de capturas
            ach_mgr.increment_counter("capture_count")

            # Verifica conquistas de captura (passando a fase atual)
            ach_mgr.check_and_unlock("first_capture", self.phase_id)
            ach_mgr.check_and_unlock("capture_10", self.phase_id)
            ach_mgr.check_and_unlock("capture_50", self.phase_id)

            # ===== CONQUISTAS: SHINY =====
            if enemy.is_shiny:
                ach_mgr.increment_counter("shiny_capture_count")
                ach_mgr.check_and_unlock("first_shiny_capture", self.phase_id)

            # ===== CONQUISTAS: CAPTURA COM ITEM =====
            ach_mgr = self.player.achievement_manager
            ach_mgr.increment_counter("capture_with_item_count")
            ach_mgr.check_and_unlock("capture_with_item", self.phase_id)
            print(f"[CAPTURE] Pokémon capturado segurando item! Conquista verificada.")

        self.show_capture_overlay(caught, is_to_team)

    @staticmethod
    def use_medicine(pokemon, item_data):
        """Usa poção ou revive em um Pokémon aliado - COM SISTEMA DE CONQUISTAS"""
        effect = item_data.get("effect", "heal")
        item_id = item_data.get("id", "")

        # ===== REVIVE =====
        if effect == "revive" or "revive" in item_id:
            if pokemon.is_alive():
                print(f"[MEDICINE] {pokemon.name} já está vivo! Revive não pode ser usado.")
                return False

            revive_percentage = item_data.get("effect_value", 0.5)
            toast_battle(f"{pokemon.name} foi revivido!", duration=4.0, pokemon=pokemon, portrait="happy")

            pokemon.add_happiness(5, f"Usou {item_data.get('name', 'Revive')}")

            pokemon.revive(heal_percentage=revive_percentage)

            # ===== CONQUISTAS: Revive =====
            game_scene = pokemon.game_scene if hasattr(pokemon, 'game_scene') else None
            if game_scene and hasattr(game_scene, 'player'):
                player = game_scene.player
                phase_id = phase_id = game_scene.phase_id
                if hasattr(player, 'achievement_manager'):
                    ach_mgr = player.achievement_manager
                    ach_mgr.increment_counter("revive_count")
                    ach_mgr.check_and_unlock("first_revive", phase_id)
                    ach_mgr.check_and_unlock("revive_25", phase_id)

            # ===== CONQUISTAS: Cura (Revive também conta) =====
            if game_scene and hasattr(game_scene, 'player'):
                player = game_scene.player
                phase_id = phase_id = game_scene.phase_id
                if hasattr(player, 'achievement_manager'):
                    player.achievement_manager.increment_counter("heal_count")
                    player.achievement_manager.check_and_unlock("heal_5", phase_id)
                    player.achievement_manager.check_and_unlock("heal_100", phase_id)

            return True

        # ===== POÇÕES E CURAS =====
        if not pokemon.is_alive():
            print(f"[MEDICINE] {pokemon.name} está derrotado! Use um Revive primeiro.")
            toast_warning(f"{pokemon.name} está derrotado! Use um Revive primeiro.", duration=2.0)
            return False

        heal_amount = item_data.get("effect_value", 0)

        # Cura completa (-1 = Full Heal)
        if heal_amount == -1:
            pokemon.heal()
            toast_battle(f"{pokemon.name} foi completamente curado!", duration=4.0, pokemon=pokemon, portrait="happy")
            pokemon.add_happiness(3, f"Usou {item_data.get('name', 'medicina')}")
            # ===== CONQUISTAS: Cura =====
            game_scene = pokemon.game_scene if hasattr(pokemon, 'game_scene') else None
            if game_scene and hasattr(game_scene, 'player'):
                player = game_scene.player
                phase_id = phase_id = game_scene.phase_id
                if hasattr(player, 'achievement_manager'):
                    player.achievement_manager.increment_counter("heal_count")
                    player.achievement_manager.check_and_unlock("heal_5", phase_id)
                    player.achievement_manager.check_and_unlock("heal_100", phase_id)

            return True

        # Cura parcial
        elif heal_amount > 0:
            old_hp = pokemon.current_hp
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal_amount)
            healed = pokemon.current_hp - old_hp
            toast_battle(f"{pokemon.name} recuperou {healed} HP! ({pokemon.current_hp}/{pokemon.max_hp})",
                         duration=4.0, pokemon=pokemon, portrait="happy")
            pokemon.add_happiness(3, f"Usou {item_data.get('name', 'medicina')}")
            # ===== CONQUISTAS: Cura =====
            game_scene = pokemon.game_scene if hasattr(pokemon, 'game_scene') else None
            if game_scene and hasattr(game_scene, 'player'):
                player = game_scene.player
                phase_id = phase_id = game_scene.phase_id
                if hasattr(player, 'achievement_manager'):
                    player.achievement_manager.increment_counter("heal_count")
                    player.achievement_manager.check_and_unlock("heal_5", phase_id)
                    player.achievement_manager.check_and_unlock("heal_100", phase_id)

            return True

        return False

    def escape_phase(self):
        """
        Escapa da fase usando ESCAPEROPE - SEM penalidades.
        """
        from src.managers.sounds.sound_manager import sound_manager
        from src.ui.toast_renderer import toast_info

        print(f"[ESCAPEROPE] Jogador fugiu da fase {self.phase_id}!")

        # ===== CONQUISTAS =====
        alive_pokemon = [p for p in self.player.team if p.is_alive()]
        is_last_stand = False

        if len(alive_pokemon) == 1:
            pokemon = alive_pokemon[0]
            hp_percentage = pokemon.current_hp / pokemon.max_hp
            if hp_percentage < 0.5:
                is_last_stand = True

        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
            ach_mgr = self.player.achievement_manager

            ach_mgr.increment_counter("escaperope_use_count")
            ach_mgr.check_and_unlock("first_escaperope_use", self.phase_id)

            if is_last_stand:
                ach_mgr.increment_counter("escaperope_last_stand_count")
                ach_mgr.check_and_unlock("escaperope_last_stand", self.phase_id)

        sound_manager.stop_music(fade_ms=500)
        self.reset_all_transformed_dittos()
        self.overlay_manager.hide()

        if hasattr(self, 'move_learn_overlay') and self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay:
            self.evolution_overlay.active = False
            self.evolution_overlay = None
        if hasattr(self, 'move_select_overlay') and self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        self.paused = False
        self.game_paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

        for pokemon in self.player.team:
            pokemon.reset(self)

        # ===== VAI PARA O TEAM_SELECT E FORÇA REFRESH =====
        from src.scenes.team_select_scene.team_select_scene import TeamSelectScene

        # Cria a cena com flag de refresh
        team_scene = TeamSelectScene(self.game, self.chapter_id, self.phase_number,  region_id=self.region_id, )
        team_scene._needs_refresh = True  # Força refresh ao entrar
        self.game.current_scene = team_scene

        toast_info("Você fugiu da fase sem penalidades!", duration=3.0)

    # ===== MÉTODOS DE POSICIONAMENTO =====

    @property
    def placed_pokemon(self):
        """
        Lista real de pokémons colocados no mapa.
        Delegado ao PlacementManager para evitar duas listas separadas.
        """
        if hasattr(self, 'placement_manager') and self.placement_manager is not None:
            return self.placement_manager.placed_pokemon
        return self.__dict__.get('_placed_pokemon_fallback', [])

    @placed_pokemon.setter
    def placed_pokemon(self, value):
        """
        Setter para compatibilidade com `self.placed_pokemon = []` no __init__.
        """
        if hasattr(self, 'placement_manager') and self.placement_manager is not None:
            self.placement_manager.placed_pokemon = value
        else:
            self.__dict__['_placed_pokemon_fallback'] = value

    def _process_evolution_drag(self, evolution_result):
        """
        Processa a evolução resultante de um drag and drop.
        """
        print(f"[EVOLUTION] Processando evolução via drag: {evolution_result}")

        evolution_data = evolution_result['evolution_data']
        drag_pokemon = evolution_result['drag_pokemon']  # Será consumido
        target_pokemon = evolution_result['target_pokemon']  # Este evolui
        drag_spot = evolution_result.get('drag_spot')
        target_spot = evolution_result.get('target_spot')

        # Verifica se a evolução é válida
        evolution_data_for_target = target_pokemon.evolution.check_combination_evolution(drag_pokemon)

        if not evolution_data_for_target:
            print(f"[EVOLUTION] Erro: {target_pokemon.name} não pode evoluir com {drag_pokemon.name}")
            return False

        print(f"[EVOLUTION] {target_pokemon.name} vai evoluir, {drag_pokemon.name} será consumido!")

        # Executa a evolução
        result = target_pokemon.evolution.perform_combination_evolution(evolution_data_for_target)

        if result:
            # Limpeza adicional do drag_pokemon (garantia)

            # Remove do placement_manager
            if drag_pokemon in self.placement_manager.placed_pokemon:
                self.placement_manager.placed_pokemon.remove(drag_pokemon)

            # Remove do time
            if drag_pokemon in self.player.team:
                self.player.team.remove(drag_pokemon)
                print(f"[EVOLUTION] {drag_pokemon.name} removido do time")

            # Remove da Box
            if drag_pokemon in self.player.pc_box:
                self.player.pc_box.remove(drag_pokemon)
                print(f"[EVOLUTION] {drag_pokemon.name} removido da Box ")

            # Libera o spot do drag
            if drag_spot:
                drag_spot.occupied = False

            # Atualiza a posição do Pokémon evoluído
            if target_spot:
                target_spot.occupied = True

                tile_center_x = (
                                            target_spot.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
                tile_center_y = (
                                            target_spot.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

                target_pokemon.x = tile_center_x
                target_pokemon.y = tile_center_y
                target_pokemon.original_spot_x = tile_center_x
                target_pokemon.original_spot_y = tile_center_y
                target_pokemon.placed_tile_x = tile_center_x // self.placement_manager.tile_size
                target_pokemon.placed_tile_y = tile_center_y // self.placement_manager.tile_size
                target_pokemon.is_placed = True

            # Recarrega os sprites
            target_pokemon._load_sprites(target_pokemon.id, target_pokemon.is_shiny)

            # ===== FORÇA ATUALIZAÇÃO DA UI DO TEAM_SELECT =====
            # Se a tela de seleção de time estiver ativa, força recriação do layout
            if hasattr(self.game, 'current_scene'):
                from src.scenes.team_select_scene.team_select_scene import TeamSelectScene
                if isinstance(self.game.current_scene, TeamSelectScene):
                    self.game.current_scene.layout_initialized = False

            # Salva o jogo
            self.player.auto_save()

            return True

        return False

    def _on_pokemon_evolution(self, evolution_result):
        """Callback para evolução via drag - chama o processador principal"""
        self._process_evolution_drag(evolution_result)

    def _on_pokemon_placed(self, placement_data):
        """Callback quando um Pokémon é colocado no mapa OU movido"""
        action = placement_data.get('action', 'place')

        if action == 'place' and hasattr(self, 'event_processor'):
            expected = self.event_processor.get_next_custom_flag()
            if expected is None:
                pass
            elif expected == "colocou_pokemon":
                self.event_processor.custom_flags["colocou_pokemon"] = True
            else:
                toast_warning("Complete a etapa anterior primeiro!", duration=5.0)
                return

        if action == 'swap':
            self._on_pokemon_swap(placement_data)
        elif action == 'move':
            self._move_pokemon_to_spot(placement_data)
        else:
            pokemon = placement_data['pokemon']
            spot = placement_data['spot']
            self.placement_manager.add_pokemon(spot, pokemon)

    def _restore_placement(self, snapshot):
        """
        Restaura pokémons para os spots onde estavam antes de rejogar.
        - Casa por `unique_id` (preferencial) ou por (id, level) como fallback.
        - Usa _add_pokemon_to_spot para evitar checagens de evolução/eventos.
        - Ignora entradas cujo spot não existe ou já está ocupado.
        """
        if not snapshot:
            return

        print(f"[RETRY] Restaurando {len(snapshot)} pokémon(s) para seus spots...")

        tile_size = self.placement_manager.tile_size

        # Mapeia time por unique_id e por (id, level)
        team_by_uid = {}
        team_by_id_level = {}
        for p in self.player.team:
            uid = getattr(p, 'unique_id', None)
            if uid:
                team_by_uid[uid] = p
            team_by_id_level.setdefault((p.id, p.level), p)

        # Mapeia spots por tile
        spots_by_tile = {}
        for spot in self.spot_renderer.get_spots():
            key = (spot.x // tile_size, spot.y // tile_size)
            spots_by_tile[key] = spot

        restored = 0
        skipped = 0

        for entry in snapshot:
            # 1) localiza o pokémon no time atual
            pokemon = None
            uid = entry.get('unique_id')
            if uid and uid in team_by_uid:
                pokemon = team_by_uid[uid]
            else:
                fallback_key = (entry.get('pokemon_id'), entry.get('level'))
                pokemon = team_by_id_level.get(fallback_key)

            if pokemon is None:
                skipped += 1
                continue

            # 2) localiza o spot pelo tile
            tile = (entry.get('tile_x'), entry.get('tile_y'))
            spot = spots_by_tile.get(tile)
            if spot is None or spot.occupied:
                skipped += 1
                continue

            # 3) coloca sem checar evolução por combinação
            try:
                self.placement_manager._add_pokemon_to_spot(spot, pokemon)
                restored += 1
            except Exception as e:
                print(f"[RETRY] Erro ao restaurar {pokemon.name}: {e}")
                skipped += 1

        print(f"[RETRY] {restored} restaurado(s), {skipped} ignorado(s).")
    def _on_pokemon_swap(self, swap_data):
        """Troca as posições de dois Pokémon"""
        pokemon_a = swap_data['pokemon_a']
        pokemon_b = swap_data['pokemon_b']
        spot_a = swap_data['spot_a']
        spot_b = swap_data['spot_b']

        # ===== VALIDAÇÃO DE TIPAGEM =====
        types_a = list(getattr(pokemon_a, 'types', []) or [])
        types_b = list(getattr(pokemon_b, 'types', []) or [])

        if not spot_b.is_type_allowed(types_a) or not spot_a.is_type_allowed(types_b):
            from src.ui.toast_renderer import toast_warning
            toast_warning(
                "Swap bloqueado: tipos incompatíveis com os spots.",
                duration=2.5,
            )
            print(f"[SWAP] Rejeitado — "
                  f"{pokemon_a.name} {types_a} → spot de {pokemon_b.name} "
                  f"({spot_b.allowed_types}) | "
                  f"{pokemon_b.name} {types_b} → spot de {pokemon_a.name} "
                  f"({spot_a.allowed_types})")
            return

        # Guarda as posições originais
        pos_a_x = pokemon_a.x
        pos_a_y = pokemon_a.y
        tile_a_x = pokemon_a.placed_tile_x
        tile_a_y = pokemon_a.placed_tile_y

        # Move Pokémon A para o spot B
        tile_center_x_b = (
                                      spot_b.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y_b = (
                                      spot_b.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon_a.x = tile_center_x_b
        pokemon_a.y = tile_center_y_b
        pokemon_a.original_spot_x = tile_center_x_b
        pokemon_a.original_spot_y = tile_center_y_b
        pokemon_a.placed_tile_x = tile_center_x_b // self.placement_manager.tile_size
        pokemon_a.placed_tile_y = tile_center_y_b // self.placement_manager.tile_size

        # Move Pokémon B para o spot A
        tile_center_x_a = (
                                      spot_a.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y_a = (
                                      spot_a.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon_b.x = tile_center_x_a
        pokemon_b.y = tile_center_y_a
        pokemon_b.original_spot_x = tile_center_x_a
        pokemon_b.original_spot_y = tile_center_y_a
        pokemon_b.placed_tile_x = tile_center_x_a // self.placement_manager.tile_size
        pokemon_b.placed_tile_y = tile_center_y_a // self.placement_manager.tile_size

        print(f"[SWAP] {pokemon_a.name} ↔ {pokemon_b.name} trocaram de posição!")

    def _move_pokemon_to_spot(self, move_data):
        """Move um Pokémon para um novo spot vazio"""
        pokemon = move_data['pokemon']
        from_spot = move_data.get('from_spot')
        to_spot = move_data['to_spot']

        # ===== VALIDAÇÃO DE TIPAGEM =====
        types = list(getattr(pokemon, 'types', []) or [])
        if not to_spot.is_type_allowed(types):
            from src.ui.toast_renderer import toast_warning
            allowed = ", ".join(to_spot.allowed_types) or "?"
            toast_warning(
                f"{pokemon.name} não pode ocupar esse spot. "
                f"Tipos permitidos: {allowed}",
                duration=2.5,
            )
            print(f"[MOVE] Rejeitado — {pokemon.name} {types} "
                  f"não cabe em {to_spot.allowed_types}")
            return

        if from_spot:
            from_spot.occupied = False

        tile_center_x = (
                                    to_spot.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y = (
                                    to_spot.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon.x = tile_center_x
        pokemon.y = tile_center_y
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.placed_tile_x = tile_center_x // self.placement_manager.tile_size
        pokemon.placed_tile_y = tile_center_y // self.placement_manager.tile_size

        to_spot.occupied = True
        print(f"[MOVE] {pokemon.name} movido para novo spot ({to_spot.x}, {to_spot.y})")

    def _try_pose_on_spot_hover(self, spot):
        """
        Tenta fazer o pokémon que está no spot posar para a foto quando o
        jogador passa o mouse em cima.

        Regras:
        - Não faz nada se estiver arrastando algo (item, pokémon, câmera)
        - Não faz nada se o pokémon não está ocioso
        - Cooldown de 3s por pokémon evita spam
        """
        if spot is None:
            return

        # ===== NÃO POSA DURANTE DRAG =====
        if self.item_drag_manager and self.item_drag_manager.is_dragging:
            return
        if self.team_manager and self.team_manager.is_dragging():
            return
        if self.dragging_camera:
            return

        # ===== BUSCA O POKÉMON DO SPOT =====
        pokemon = self.placement_manager.get_pokemon_at_spot(spot)
        if pokemon is None:
            return

        # ===== TENTA POSAR =====
        # O próprio pokémon verifica cooldown, estado ocioso e se tem animação
        pokemon.try_pose_for_photo()

    def _update_pokemon_look_at_mouse(self, placed_pokemon):
        """
        Faz os pokémons ociosos olharem na direção do mouse,
        se ele estiver dentro do attack_range deles.
        """
        if not placed_pokemon:
            return

        mouse_pos = pygame.mouse.get_pos()
        screen_mgr = self.screen_manager

        if not screen_mgr.is_mouse_in_viewport(mouse_pos):
            return

        world_pos = screen_mgr.get_mouse_world_position(mouse_pos, self.camera)
        if world_pos is None:
            return

        mouse_world_x, mouse_world_y = world_pos

        for pokemon in placed_pokemon:
            pokemon.look_at_mouse(mouse_world_x, mouse_world_y)

    # ===== MÉTODOS DE LIMPEZA =====

    def cleanup(self):
        """Limpa o estado da fase antes de sair - INCLUI RESET DOS DITTOS"""
        # ===== PARA TODOS OS SONS (substitui _stop_battle_music) =====
        self._stop_all_sounds(fade_ms=1000)

        self.placement_manager.stop_victory_celebration()

        # ===== PARA TODAS AS ANIMAÇÕES DESTA CENA (clima, spray, etc) =====
        # Agora funciona porque __init__ chamou attach_to_scene(self).
        from src.anim.animation_manager import detach_from_scene
        detach_from_scene(self)

        # ===== LIMPA DIA/NOITE E CLIMA =====
        if hasattr(self, 'day_night_weather'):
            self.day_night_weather._initialized = False

        # Zera as chaves de animação de clima
        self._current_weather_key = None
        self._current_weather_trigger = None

        # Reseta câmera
        if hasattr(self, 'camera_renderer'):
            self.camera_renderer.flash_active = False
            self.camera_renderer.flash_alpha = 0

        if hasattr(self, 'capture_shake_animation'):
            self.capture_shake_animation = None

        # ===== RESETA TODOS OS DITTOS TRANSFORMADOS =====
        self.reset_all_transformed_dittos()

        for spot in self.spot_renderer.get_spots():
            spot.occupied = False

        self.battle_system = BattleSystem(self)
        self.placed_pokemon.clear()
        self.placement_manager.placed_pokemon.clear()

        for pokemon in self.player.team:
            pokemon.reset(self)

        # ===== LIMPA FLAGS DE PAY DAY DE TODOS OS INIMIGOS =====
        for enemy in self.wave_manager.active_enemies:
            if hasattr(enemy, '_pay_day_hit'):
                delattr(enemy, '_pay_day_hit')
            if hasattr(enemy, '_pay_day_hit_count'):
                delattr(enemy, '_pay_day_hit_count')
            if hasattr(enemy, '_pay_day_gold_multiplier'):
                delattr(enemy, '_pay_day_gold_multiplier')
            if hasattr(enemy, '_pay_day_xp_multiplier'):
                delattr(enemy, '_pay_day_xp_multiplier')

        self.wave_manager.active_enemies.clear()

    def reset_all_transformed_dittos(self):
        """
        Reseta todos os Dittos transformados no time do jogador.
        Deve ser chamado quando a partida termina (game over, fase completa, ou sair com ESC).
        """
        reset_count = 0
        for pokemon in self.player.team:
            # Verifica se é Ditto (ID 132) E está transformado
            if pokemon.id == 132 and hasattr(pokemon, '_is_transformed') and pokemon._is_transformed:
                if hasattr(pokemon, 'reset_transform'):
                    pokemon.reset_transform()
                    reset_count += 1
                    print(f"[GAME_SCENE] Ditto {pokemon.name} resetado após fim da partida")

        if reset_count > 0:
            print(f"[GAME_SCENE] {reset_count} Ditto(s) transformado(s) foram resetados!")

    # ===== MÉTODOS DE MÚSICA =====

    def _start_battle_music(self):
        """Inicia a música de batalha aleatória"""
        sound_manager.play_random_battle_music()
        self.music_playing = True

    def _stop_all_sounds(self, fade_ms: int = 500):
        """
        Para TODOS os sons do jogo:
        - Música de batalha
        - Efeitos sonoros
        - Sons de ambiente (clima, chuva, tempestade)
        - Sons de moves
        """
        print("[GAME_SCENE] Parando todos os sons...")

        # 1. Para a música de batalha
        if self.music_playing:
            sound_manager.stop_music(fade_ms)
            self.music_playing = False
            print("[GAME_SCENE] Música parada")

        # 2. Para todos os efeitos sonoros (como evolução, captura, etc)
        try:
            # Para todos os efeitos que possam estar tocando
            for effect in SoundEffect:
                sound_manager.stop_effect(effect)
            print("[GAME_SCENE] Efeitos sonoros parados")
        except Exception as e:
            print(f"[GAME_SCENE] Erro ao parar efeitos: {e}")

        # 3. Para os sons de ambiente (chuva, tempestade, etc)
        try:
            from src.managers.sounds.ambient_sound_manager import ambient_sound_manager
            ambient_sound_manager.stop_ambient(fade_ms)
            print("[GAME_SCENE] Sons de ambiente parados")
        except Exception as e:
            print(f"[GAME_SCENE] Erro ao parar sons de ambiente: {e}")

        # 4. Para os sons de moves (se estiverem tocando)
        try:
            from src.managers.sounds.move_sound_manager import move_sound_manager
            # O move_sound_manager não tem um método stop_all diretamente,
            # mas podemos forçar a parada parando todos os canais
            # ou apenas confiar que os sons são curtos
            print("[GAME_SCENE] Sons de moves parados (se estavam tocando)")
        except Exception as e:
            print(f"[GAME_SCENE] Erro ao parar sons de moves: {e}")

        # Para todos os canais do mixer (mais drástico)
        # pygame.mixer.stop()  #

        print("[GAME_SCENE] Todos os sons foram parados!")

    # ===== MÉTODO HANDLE_EVENT =====

    def handle_event(self, event):
        """Processa eventos do jogo"""
        # Cache de referências
        overlay_active = self.overlay_manager.is_active
        drag_manager = self.item_drag_manager
        bag_renderer = self.item_bag_renderer
        team_manager = self.team_manager
        placement_mgr = self.placement_manager
        spot_renderer = self.spot_renderer
        player = self.player
        camera = self.camera
        screen_mgr = self.screen_manager

        # ===== IN-GAME DEBUG (prioridade máxima) =====
        if self.in_game_debug.handle_event(event):
            return None

        # ===== OVERLAYS PRIORITÁRIOS =====
        if self.final_victory_overlay is not None:
            self.final_victory_overlay.handle_event(event)
            return None

        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.handle_event(event)
            return None

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.handle_event(event)
            return None

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return None

        if hasattr(self, 'event_processor') and self.event_processor.current_dialog:
            if self.event_processor.current_dialog.handle_event(event):
                return None
            # Se o diálogo foi fechado, o event_processor já o removeu
            if not self.event_processor.current_dialog.active:
                self.event_processor.current_dialog = None
            # Consome o evento (não passa para outros handlers)
            return None

        # ===== OVERLAY DE PAUSA =====
        # O overlay de pausa é tratado antes dos outros overlays
        # para garantir que ele capture eventos mesmo com outros overlays ativos
        if self.overlay_manager.is_active and self.overlay_manager.current_type == OverlayType.PAUSE:
            if self.overlay_manager.handle_event(event):
                return None
            # Não retorna None aqui para permitir que outros eventos sejam processados
            # Mas o overlay de pausa já trata ESC e P internamente

        if overlay_active:
            if self.overlay_manager.handle_event(event):
                return None
            return None

        # ===== QUICK SWITCH DE MOVES (prioridade sobre drag/mapa) =====
        if self.move_quick_switch_manager.handle_event(event, self.camera, self.screen_manager):
            return None

        # ===== DRAG DE ITENS =====
        if drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                world_pos = screen_mgr.get_mouse_world_position(event.pos, camera)
                if world_pos:
                    drag_manager.update_drag(
                        event.pos, world_pos,
                        placement_mgr.placed_pokemon,
                        self.wave_manager.active_enemies,
                        camera
                    )
                return None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drag_manager.stop_drag(self._on_item_use)
                return None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                drag_manager.cancel_drag()
                return None

        # ===== ITEM BAG =====
        if bag_renderer and bag_renderer.handle_event(event):
            return None

        # ===== CÂMERA FOTOGRÁFICA =====
        if self.camera_renderer and self.camera_renderer.handle_event(event):
            return None

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(player, 'bag'):
                    player.bag.cycle_category()
                return None
            elif event.key == pygame.K_h:
                self.toggle_ui_hidden()
                return None
            elif event.key == pygame.K_p:
                self.toggle_pause()  # Agora usa o novo sistema de pausa
                return None
            elif event.key == pygame.K_ESCAPE:
                # ESC agora abre o overlay de pausa em vez de sair
                self.toggle_pause()
                return None
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                self._update_perf_monitor()
                return None
            elif event.key == pygame.K_c:
                # Abre/fecha a câmera (toggle minimizar/maximizar)
                if hasattr(self, 'camera_renderer') and self.camera_renderer:
                    self.camera_renderer.minimized = not self.camera_renderer.minimized
                    if not self.camera_renderer.minimized:
                        self.camera_renderer._set_slider_from_area()
                    # Toca som de clique
                    try:
                        from src.managers.sounds.sound_manager import sound_manager, SoundEffect
                        sound_manager.play_effect(SoundEffect.CLICK)
                    except Exception:
                        pass
                return None
            elif event.key == pygame.K_SPACE:
                # Tira foto (se a câmera estiver visível)
                if hasattr(self, 'camera_renderer') and self.camera_renderer:
                    if self.camera_renderer.visible:
                        self.camera_renderer._do_capture()
                return None

        # ===== MOUSE WHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            if bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui:
                if event.y > 0:
                    player.bag.prev_item()
                elif event.y < 0:
                    player.bag.next_item()
                bag_renderer.hovered_index = player.bag.selected_item_index
                return None
            elif not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if screen_mgr.is_mouse_in_viewport(mouse_pos):
                    world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                    if world_pos:
                        target_x, target_y = world_pos
                        camera.handle_zoom(event.y > 0)
                        new_world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                        if new_world_pos:
                            dx = target_x - new_world_pos[0]
                            dy = target_y - new_world_pos[1]
                            camera.x += dx
                            camera.y += dy
                            camera._clamp_position()
                return None

        # ===== MOUSE BUTTON DOWN =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            if hasattr(self, 'ui_panel_rect') and self.ui_panel_rect:
                btn_rect = pygame.Rect(self.ui_panel_rect.right - 30, self.ui_panel_rect.y + 8, 22, 22)
                if btn_rect.collidepoint(event.pos):
                    self.toggle_ui_minimize()
                    return None

            # Verifica clique na bag
            if bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui:
                hovered_index = bag_renderer.hovered_index
                if hovered_index >= 0:
                    items = player.bag.get_items_for_render()
                    if hovered_index < len(items):
                        item = items[hovered_index]
                        player.bag.selected_item_index = hovered_index
                        world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                        if world_pos:
                            drag_manager.start_drag(item["id"], mouse_pos, world_pos)
                return None

            # Verifica clique em Pokémon colocado
            if not self.item_drag_manager.is_dragging and not team_manager.is_dragging():
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        clicked_pokemon = placement_mgr.get_pokemon_at_world_pos(
                            world_pos[0], world_pos[1], tolerance=30
                        )
                        if clicked_pokemon:
                            for spot in spot_renderer.get_spots():
                                spot_tile_x = spot.x // placement_mgr.tile_size
                                spot_tile_y = spot.y // placement_mgr.tile_size
                                if (hasattr(clicked_pokemon, 'placed_tile_x') and
                                        spot_tile_x == clicked_pokemon.placed_tile_x and
                                        spot_tile_y == clicked_pokemon.placed_tile_y):
                                    clicked_spot = spot
                                    break

                            if clicked_spot:
                                team_manager.drag_manager.start_drag_placed(
                                    clicked_pokemon,
                                    clicked_spot,
                                    mouse_pos,
                                    world_pos
                                )
                                return None
                            else:
                                if clicked_pokemon.moves:
                                    self.open_move_select_overlay(clicked_pokemon)
                                    return None

        # ===== NOTIFICATION SCROLL =====
        if self.notification_manager.handle_event(event):
            return None

        if team_manager:
            result = team_manager.handle_event(
                event,
                spot_renderer.get_spots(),
                camera,
                self._on_pokemon_placed,
                self._on_pokemon_swap,
                self._on_pokemon_evolution  # Callback de evolução
            )
            if result:
                # Se for um dicionário com ação de evolução
                if isinstance(result, dict) and result.get('action') == 'evolution':
                    self._process_evolution_drag(result)
                return None

        # ===== CÂMERA E REMOÇÃO =====
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            in_viewport = screen_mgr.is_mouse_in_viewport(mouse_pos)

            if event.button == 2:
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return None
            elif event.button == 3:
                if not (bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui):
                    world_pos = screen_mgr.get_mouse_world_position(event.pos, camera)
                    if world_pos:
                        placement_mgr.remove_pokemon_by_right_click(world_pos[0], world_pos[1])
                return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2 and self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return None



        elif event.type == pygame.MOUSEMOTION:

            if self.dragging_camera and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]

                dy = event.pos[1] - self.last_mouse_pos[1]

                camera.x -= dx / camera.zoom

                camera.y -= dy / camera.zoom

                camera._clamp_position()

                self.last_mouse_pos = event.pos

                return None

            if self.game_state != "game_over":

                if bag_renderer and hasattr(bag_renderer, 'update_hover'):
                    bag_renderer.update_hover(event.pos)

                mouse_pos = pygame.mouse.get_pos()

                if screen_mgr.is_mouse_in_viewport(mouse_pos):

                    world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)

                    if world_pos:

                        # ===== DETECTA MUDANÇA DE SPOT (entrou em um novo) =====

                        previous_spot = self.hovered_spot

                        self.hovered_spot = spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])

                        # Só tenta posar se ENTROU em um spot DIFERENTE do anterior

                        if self.hovered_spot is not None and self.hovered_spot is not previous_spot:
                            self._try_pose_on_spot_hover(self.hovered_spot)

            return None

    def handle_give_up(self):
        """
        Lida com a desistência do jogador (via botão DESISTIR! no pause overlay).
        Conta como derrota: remove felicidade e mostra game over.
        """
        print(f"[GAME_SCENE] Jogador desistiu da fase {self.phase_id}!")

        # ===== PARA O CLIMA VISUAL JUNTO =====
        # (o cleanup vai rodar depois, mas garante que já pare agora)
        from src.anim.animation_manager import animation_manager
        if self._current_weather_key:
            animation_manager.stop(self._current_weather_key)
            print(f"[WEATHER-ANIM] stop {self._current_weather_key} (desistência)")
            self._current_weather_key = None
            self._current_weather_trigger = None

        # Remove felicidade dos Pokémon (penalidade por desistir)
        for pokemon in self.player.team:
            pokemon.add_happiness(-15, "Desistiu da fase")

        # Reseta Dittos transformados
        self.reset_all_transformed_dittos()

        # Reseta o estado da fase
        self.paused = False
        self.game_paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

        # Reseta os Pokémon (cura) para o próximo jogo
        for pokemon in self.player.team:
            pokemon.reset(self)

        # Marca como game over (motivo: desistência)
        self.game_state = "game_over"

        # Mostra overlay de game over
        self._show_game_over_scene(reason="team_defeated")

        print(f"[GAME_SCENE] Desistência registrada como derrota!")

    # ===== MÉTODO FIXED_UPDATE  =====

    def fixed_update(self, dt):
        """Update da lógica do jogo - COM NOVO SISTEMA DE PERFORMANCE"""

        perf_monitor.start_frame()

        self.in_game_debug.update(dt)
        dt = dt * self.in_game_debug.get_time_multiplier()

        # ===== ANIMAÇÕES GLOBAIS DO EDITOR =====
        from src.anim.animation_manager import animation_manager
        animation_manager.update(dt)

        # ===== GUARDA O DT PARA USO NO RENDER (partículas de clima) =====
        self._last_dt = dt

        # ===== QUICK SWITCH UPDATE (limpa widgets órfãos) =====
        if hasattr(self, 'move_quick_switch_manager'):
            self.move_quick_switch_manager.update(dt)

        # ===== DELAY DA VITORIA FINAL =====
        # Criado durante _complete_phase; so vira overlay depois de alguns
        # segundos, para a celebracao de vitoria rolar primeiro.
        if self._pending_final_victory_delay is not None:
            if self._pending_final_victory_delay > 0:
                self._pending_final_victory_delay -= dt
            else:
                self._pending_final_victory_delay = None
                from src.scenes.game_scene.components.overlays.final_victory_overlay import (
                    FinalVictoryOverlay,
                )
                self.final_victory_overlay = FinalVictoryOverlay(self)
                print("[FINAL_VICTORY] Overlay Hall of Fame ativado!")

        # ===== OVERLAYS PRIORITÁRIOS =====
        perf_monitor.start_section("OVERLAYS")

        if getattr(self, 'capture_shake_animation', None) is not None:
            if self.capture_shake_animation.active:
                self.capture_shake_animation.update(dt)
            else:
                self.capture_shake_animation = None

        # ===== VITORIA FINAL (prioridade máxima — cobre tudo) =====
        if self.final_victory_overlay is not None:
            self.final_victory_overlay.update(dt)
            perf_monitor.end_section()
            perf_monitor.end_frame()
            return

        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.update(dt)
            perf_monitor.end_section()
            perf_monitor.end_frame()
            return

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.update(dt)
            perf_monitor.end_section()
            perf_monitor.end_frame()
            return

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
            perf_monitor.end_section()
            perf_monitor.end_frame()
            return

        perf_monitor.end_section()

        # ===== PAUSA =====
        if self.game_paused or self.paused:
            perf_monitor.end_frame()
            return

        # ===== ATUALIZAÇÃO NORMAL =====
        self.event_processor.update(dt)
        wave_mgr = self.wave_manager
        target_mgr = self.target_item_manager
        placement_mgr = self.placement_manager
        spot_renderer = self.spot_renderer
        team_mgr = self.team_manager
        bag_renderer = self.item_bag_renderer
        placed_pokemon = self.placed_pokemon
        screen_mgr = self.screen_manager
        path_renderer = self.path_renderer

        # Battle System
        perf_monitor.start_section("BATTLE_SYSTEM")
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        # ===== DIA/NOITE E CLIMA =====
        if hasattr(self, 'day_night_weather'):
            self.day_night_weather.update(dt)
            self._sync_weather_animations()

        perf_monitor.end_section()

        # Bag Renderer
        perf_monitor.start_section("BAG_RENDERER_UPDATE")
        if bag_renderer:
            bag_renderer.update(dt)
        perf_monitor.end_section()

        # ===== CÂMERA FOTOGRÁFICA =====
        perf_monitor.start_section("CAMERA_RENDERER_UPDATE")
        if hasattr(self, 'camera_renderer'):
            self.camera_renderer.update(dt)
        perf_monitor.end_section()

        # Team Manager
        perf_monitor.start_section("TEAM_MANAGER_UPDATE")
        if team_mgr:
            team_mgr.update(dt)
        perf_monitor.end_section()

        # Placement Manager
        perf_monitor.start_section("PLACEMENT_MANAGER_UPDATE")
        if placement_mgr:
            placement_mgr.update(dt, wave_mgr.active_enemies)
        perf_monitor.end_section()

        # Spot Renderer
        perf_monitor.start_section("SPOT_RENDERER_UPDATE")
        if spot_renderer:
            spot_renderer.update(dt)
        perf_monitor.end_section()

        # Pokémon Updates
        perf_monitor.start_section("POKEMON_UPDATES")
        for pokemon in placed_pokemon:
            pokemon.update(dt)
        perf_monitor.end_section()

        # ===== POKÉMONS OLHAM PARA O MOUSE (SE ESTIVER NO RANGE) =====
        # IMPORTANTE: executar DEPOIS do placement_mgr.update(), pois é lá
        # que o combat.update_combat() roda. Assim o combat_state já foi
        # atualizado (idle/returning/attacking) e podemos sobrescrever a
        # direção quando o pokémon estiver ocioso.
        perf_monitor.start_section("POKEMON_LOOK_AT_MOUSE")
        self._update_pokemon_look_at_mouse(placed_pokemon)
        perf_monitor.end_section()

        # Target Items Update
        perf_monitor.start_section("TARGET_ITEMS_UPDATE")
        target_mgr.update(dt)
        perf_monitor.end_section()

        # ===== VERIFICA CONQUISTAS DE FELICIDADE =====
        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
            ach_mgr = self.player.achievement_manager

            if not ach_mgr.is_unlocked("full_team_max_happiness"):
                ach_mgr.check_and_unlock("full_team_max_happiness", self.phase_id)

            if not ach_mgr.is_unlocked("max_happiness"):
                ach_mgr.check_and_unlock("max_happiness", self.phase_id)

        # Effect Manager
        if hasattr(self, 'battle_system') and self.battle_system:
            perf_monitor.start_section("EFFECT_MANAGER")
            self.battle_system.effect_manager.update(dt)
            perf_monitor.end_section()

        self.notification_manager.update(dt)

        # Qualquer pokémon do time que ficar sem vida durante a fase
        if not self._pokemon_defeated_this_phase:
            for p in self.player.team:
                if p is None:
                    continue
                if not getattr(p, 'is_placed', False):
                    continue
                if not p.is_alive():
                    self._pokemon_defeated_this_phase = True
                    print(f"[STARS] {p.name} caiu em combate! "
                          f"HP={p.current_hp}/{p.max_hp} | "
                          f"is_defeated={getattr(p, 'is_defeated', '?')} "
                          f"— estrelas travadas em 1★")
                    break

        # ===== GAME OVER CHECK =====
        perf_monitor.start_section("GAME_OVER_CHECK")
        team_defeated = self.is_team_defeated()
        items_lost = target_mgr.items_protected <= 0
        perf_monitor.end_section()

        if team_defeated:
            print(f"[GAME_OVER] Time derrotado! Fim de jogo.")
            self._stop_all_sounds(fade_ms=1000)
            self.game_state = "game_over"
            for pokemon in self.player.team:
                pokemon.add_happiness(-5, "Fase perdida")
            for pokemon in self.player.team:
                pokemon.reset(self)
            self._show_game_over_scene(reason="team_defeated")
            perf_monitor.end_frame()
            return

        if items_lost:
            print(f"[GAME_OVER] Todos os itens foram roubados!")
            self.game_state = "game_over"
            for pokemon in self.player.team:
                pokemon.add_happiness(-5, "Fase perdida")
            for pokemon in self.player.team:
                pokemon.reset(self)
            self._show_game_over_scene(reason="items_stolen")
            perf_monitor.end_frame()
            return

        # ===== Wave Manager Update =====
        perf_monitor.start_section("WAVE_MANAGER_UPDATE")
        enemies_at_end = wave_mgr.update(dt)
        perf_monitor.end_section()

        # ===== TRANSIÇÕES DE ESTADO =====
        if self.game_state == "in_wave":
            if wave_mgr.is_wave_completely_finished():
                has_after_boss_pending = False
                for trigger in self.event_manager.triggers:
                    if trigger.trigger_type == "after_boss_defeat":
                        idx = self.event_manager.triggers.index(trigger)
                        if not self.event_processor.triggered[idx]:
                            has_after_boss_pending = True
                            break

                has_pending_events = bool(self.event_processor.pending_events)

                if has_after_boss_pending or has_pending_events:
                    if has_after_boss_pending:
                        print("[GAME] Aguardando gatilho AFTER_BOSS_DEFEAT antes de completar fase")
                    if has_pending_events:
                        print(f"[GAME] Aguardando {len(self.event_processor.pending_events)} evento(s) pendente(s)")
                else:
                    if target_mgr.items_protected > 0:
                        print("[GAME] Fase COMPLETA! Todos os inimigos foram derrotados e eventos processados!")
                        self.game_state = "completed"
                        self._complete_phase()
                    else:
                        print("[GAME] GAME OVER! Todos os itens foram roubados!")
                        self.game_state = "game_over"
                        self._show_game_over_scene(reason="items_stolen")

        perf_monitor.end_section()

        perf_monitor.end_frame()

    def _complete_phase(self):
        """
        Completa a fase com sucesso.
        Calcula recompensas, estrelas, e mostra a cena de conclusão.

        Regra de score/XP:
          - `player.score` É o XP acumulado (persiste no save, nunca diminui).
          - Nesta função, somamos o XP da fase ao score.
          - O nível do jogador é DERIVADO do score (player.get_level()).
        """
        from src.config.progress import progress_manager
        import random

        # ===== PARA A MÚSICA DE BATALHA =====
        self._stop_all_sounds(fade_ms=1000)

        # ===== PARA O CLIMA VISUAL JUNTO =====
        # Evita que a animação de clima continue tocando enquanto a cena
        # de fase completa está na tela, e previne "animações zumbis".
        from src.anim.animation_manager import animation_manager
        if self._current_weather_key:
            animation_manager.stop(self._current_weather_key)
            print(f"[WEATHER-ANIM] stop {self._current_weather_key} (fase completa)")
            self._current_weather_key = None
            self._current_weather_trigger = None

        # Reset Dittos transformados
        self.reset_all_transformed_dittos()

        # Adiciona felicidade aos Pokémon do time
        for pokemon in self.player.team:
            pokemon.add_happiness(5, "Fase completada")

        self.placement_manager.start_victory_celebration()

        # ===== VERIFICA SE É GINÁSIO =====
        if (self.chapter_id, self.phase_number) in GYM_PHASES:
            gym_number = GYM_PHASES[(self.chapter_id, self.phase_number)]
            print(f"[GYM] Ginásio {gym_number} completado!")

            ach_mgr = self.player.achievement_manager

            # ===== SÓ CONTA A INSÍGNIA UMA VEZ POR GINÁSIO =====
            gym_key = f"gym_{gym_number}_completed"
            already_done = ach_mgr.get_counter(gym_key) > 0

            if not already_done:
                ach_mgr.set_counter(gym_key, 1)
                ach_mgr.increment_counter("badge_count")

                ach_mgr.check_and_unlock("first_badge", self.phase_id)
                ach_mgr.check_and_unlock("all_badges", self.phase_id)
                print(f"[GYM] Insígnia {gym_number} contabilizada "
                      f"(total: {ach_mgr.get_counter('badge_count')}/8)")
            else:
                print(f"[GYM] Ginásio {gym_number} já havia sido concluído — "
                      f"badge_count NÃO incrementado")

        # ===== RECOMPENSAS BASE =====
        base_reward = self.phase_rewards.get('money', 100)
        gold_from_defeats = self.wave_manager.get_total_gold_earned()
        total_items = len(self.target_item_manager.items)
        stolen_items = self.target_item_manager.items_stolen

        # ===== BÔNUS POR FASE PERFEITA =====
        bonus_amount = 0
        perfect_run = False
        if stolen_items == 0 and total_items > 0:
            bonus_amount = int(gold_from_defeats * 0.3)
            perfect_run = True
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                self.player.achievement_manager.increment_counter("perfect_phase_count")
                self.player.achievement_manager.check_and_unlock("perfect_phase", self.phase_id)
                print(f"[ACHIEVEMENT] Fase perfeita! Verificando conquistas...")

        # ===== GOLD TOTAL =====
        gold_total = base_reward + gold_from_defeats + bonus_amount
        self.player.money += gold_total

        # ===== RECOMPENSAS DE ITENS =====
        item_rewards_config = self.phase_rewards.get('item_rewards', [])
        drop_chance = self.phase_rewards.get('drop_chance', 0.0)
        max_items = self.phase_rewards.get('max_items', 3)
        earned_items = []

        if item_rewards_config and drop_chance > 0 and max_items > 0:
            total_kills = self.wave_manager.total_enemies_defeated
            print(f"[DEBUG] total_kills em _complete_phase = {total_kills}")

            items_pool = []
            weights = []
            for entry in item_rewards_config:
                items_pool.append(entry['item_id'])
                weights.append(entry.get('weight', 100))

            drops = 0
            for _ in range(total_kills):
                if drops >= max_items:
                    break
                if random.random() < drop_chance:
                    chosen = random.choices(items_pool, weights=weights, k=1)[0]
                    earned_items.append(chosen)
                    drops += 1

            for item_id in earned_items:
                self.player.bag.add_item(item_id, 1)
                print(f"[REWARD] Item ganho: {item_id}")

        # ===== XP (score do jogador) =====
        # `phase_rewards["experience"]` é o XP fixo desta fase.
        # Somamos ao score acumulado. O nível é derivado depois.
        xp_ganho = int(self.phase_rewards.get('experience', 50))
        score_antes = int(getattr(self.player, 'score', 0))
        self.player.score += xp_ganho
        level_antes = self.player.get_level()   # (já é o novo, pois score mudou)

        # Descobre se o jogador SUBIU de nível agora (comparando pelo XP)
        # Truque: subtrai temporariamente o xp_ganho pra ver o nível anterior.
        try:
            self.player.score -= xp_ganho
            level_antes = self.player.get_level()
            self.player.score += xp_ganho
        except Exception:
            level_antes = self.player.get_level()

        level_depois = self.player.get_level()
        subiu = level_depois > level_antes

        print(f"[SCORE] +{xp_ganho} XP  →  total: {self.player.score}  "
              f"(Nivel {level_antes} → {level_depois})"
              + ("  ⭐ LEVEL UP!" if subiu else ""))

        self._roll_mythical_chance()

        # ===== ESTRELAS =====
        # 3: nenhum pokémon derrotado E nenhum item perdido
        # 2: nenhum pokémon derrotado, mas perdeu item
        # 1: qualquer pokémon derrotado (independente dos itens)
        items_stolen = self.target_item_manager.items_stolen

        any_pokemon_defeated = self._pokemon_defeated_this_phase
        no_items_lost = (items_stolen == 0)

        if any_pokemon_defeated:
            stars = 1
        elif not no_items_lost:
            stars = 2
        else:
            stars = 3

        print(
            f"[STARS] itens_perdidos={items_stolen} | "
            f"pokemon_caiu={any_pokemon_defeated} | "
            f"-> {stars}★"
        )

        # ===== DADOS PARA A CENA DE FASE COMPLETA =====
        self.phase_complete_data = {
            "base_reward": base_reward,
            "gold_from_defeats": gold_from_defeats,
            "bonus_amount": bonus_amount,
            "gold_total": gold_total,
            "total_xp": xp_ganho,           # XP GANHO NESTA FASE
            "perfect_run": perfect_run,
            "stars": stars,
            "earned_items": earned_items
        }

        # ===== SALVA PROGRESSO =====
        progress_manager.complete_phase(self.phase_id, stars=stars)
        self.player.auto_save()

        # ===== MOSTRA A CENA DE FASE COMPLETA =====
        if self.chapter_id == 8 and self.phase_number == 1:
            # Fase final → agenda o Hall of Fame em 3.5s (não abre a cena)
            self._pending_final_victory_delay = 3.5
            print("[FINAL_VICTORY] Fase final detectada! Hall of Fame em 3.5s.")
        else:
            self._show_level_complete_scene()

    # ===== MÉTODOS DE RENDER =====

    def render(self, screen):
        """Renderiza o jogo - COM NOVO SISTEMA DE PERFORMANCE E OCULTAÇÃO DE UI"""

        perf_monitor.start_section("RENDER_TOTAL")

        perf_monitor.start_section("RENDER_CLEAR")
        screen.fill((0, 0, 0))
        perf_monitor.end_section()

        camera = self.camera
        screen_mgr = self.screen_manager
        map_renderer = self.map_renderer
        path_renderer = self.path_renderer
        spot_renderer = self.spot_renderer
        target_mgr = self.target_item_manager
        wave_mgr = self.wave_manager
        placement_mgr = self.placement_manager
        bag_renderer = self.item_bag_renderer
        team_mgr = self.team_manager
        drag_mgr = self.item_drag_manager
        overlay_mgr = self.overlay_manager
        show_debug = self.show_debug

        # =========================================================
        # RENDER ORDEM
        #   chão → decoração → entidades → teto → efeitos
        # =========================================================

        # 1. CHÃO
        perf_monitor.start_section("RENDER_MAP_GROUND")
        map_renderer.render_ground(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # 2. Spots de torre (nível do chão)
        perf_monitor.start_section("RENDER_SPOTS")
        if spot_renderer:
            spot_renderer.render(
                screen, camera, screen_mgr,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )
        perf_monitor.end_section()

        # 3. DECORAÇÃO (agora ABAIXO das entidades)
        perf_monitor.start_section("RENDER_MAP_DECORATION")
        map_renderer.render_decoration(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # 4. Paths (apenas debug)
        if show_debug:
            perf_monitor.start_section("RENDER_PATHS")
            path_renderer.render(screen, camera, screen_mgr, show_editing=False)
            perf_monitor.end_section()

        # 5. Itens alvo no chão
        perf_monitor.start_section("RENDER_TARGET_ITEMS_GROUND")
        target_mgr.render_in_ground(screen, camera)
        perf_monitor.end_section()

        # 6. INIMIGOS (acima da decoração)
        perf_monitor.start_section("RENDER_ENEMIES")
        for enemy in wave_mgr.active_enemies:
            if getattr(enemy, '_capture_hidden', False):
                continue
            enemy.render(screen, camera, show_hp=False)

        # 6.5. ANIMAÇÃO DE CAPTURA (pokébola balançando)
        if getattr(self, 'capture_shake_animation', None) is not None:
            if self.capture_shake_animation.active:
                self.capture_shake_animation.render(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # 7. POKÉMON COLOCADOS (acima da decoração)
        perf_monitor.start_section("RENDER_PLACED_POKEMON")
        if placement_mgr:
            placement_mgr.render(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # 8. TETO (por cima de tudo — arcos, copas grandes, cavernas)
        perf_monitor.start_section("RENDER_MAP_CEILING")
        map_renderer.render_ceiling(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # Animações do editor — camada world
        from src.anim.animation_manager import animation_manager
        animation_manager.render(screen, camera, self.screen_manager, space="world")

        # 9. Projéteis (acima do teto — sempre visíveis)
        perf_monitor.start_section("RENDER_PROJECTILES")
        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, camera, self.screen_manager)
        perf_monitor.end_section()

        # 10. Itens sendo carregados
        perf_monitor.start_section("RENDER_TARGET_ITEMS_POKEMON")
        target_mgr.render_in_pokemon(screen, camera)
        perf_monitor.end_section()

        # 11. HP Bars
        perf_monitor.start_section("RENDER_ENEMY_HP")
        for enemy in wave_mgr.active_enemies:
            if getattr(enemy, '_capture_hidden', False):
                continue
            enemy.render_hp_enemy(screen, camera)
        perf_monitor.end_section()

        perf_monitor.start_section("RENDER_POKEMON_HP")
        if placement_mgr:
            placement_mgr.render_hp(screen, camera)
        perf_monitor.end_section()

        # ===== UI =====
        if not self.ui_hidden:
            perf_monitor.start_section("RENDER_GAME_UI")
            self._render_game_ui(screen)
            perf_monitor.end_section()

            animation_manager.render(screen, camera, self.screen_manager, space="screen")

            perf_monitor.start_section("RENDER_TEAM_MANAGER")
            if team_mgr:
                team_mgr.render(screen, camera, spot_renderer.get_spots() if spot_renderer else [])
            perf_monitor.end_section()

            perf_monitor.start_section("RENDER_DRAG_MANAGER")
            if drag_mgr:
                drag_mgr.render(screen, camera)
            perf_monitor.end_section()

            perf_monitor.start_section("RENDER_CAMERA")
            if hasattr(self, 'camera_renderer'):
                self.camera_renderer.render(screen)
            perf_monitor.end_section()

            perf_monitor.start_section("RENDER_ITEM_BAG")
            if bag_renderer:
                bag_renderer.render(screen)
            perf_monitor.end_section()

            perf_monitor.start_section("RENDER_VIEWPORT_BORDER")
            pygame.draw.rect(screen, (80, 80, 80),
                             (screen_mgr.viewport_x, screen_mgr.viewport_y,
                              screen_mgr.viewport_width, screen_mgr.viewport_height), 1)
            perf_monitor.end_section()
        else:
            # UI oculta: ainda renderiza as animações de clima (screen)
            animation_manager.render(screen, camera, self.screen_manager, space="screen")
        # ===== QUICK SWITCH =====
        perf_monitor.start_section("RENDER_QUICK_SWITCH")
        if hasattr(self, 'move_quick_switch_manager'):
            self.move_quick_switch_manager.render(screen, self.camera, self.screen_manager)
        perf_monitor.end_section()

        # ===== NOTIFICATIONS =====
        viewport_rect = pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height
        )
        self.notification_manager.render(screen, viewport_rect)

        # ===== OVERLAY MANAGER =====
        perf_monitor.start_section("RENDER_OVERLAY_MANAGER")
        if overlay_mgr:
            overlay_mgr.render(screen)
        perf_monitor.end_section()

        # ===== EVENT PROCESSOR DIALOG =====
        if hasattr(self, 'event_processor') and self.event_processor.current_dialog:
            self.event_processor.current_dialog.render(screen)

        # ===== OVERLAYS =====
        if self.move_learn_overlay and self.move_learn_overlay.active:
            perf_monitor.start_section("RENDER_MOVE_LEARN")
            self.move_learn_overlay.render(screen)
            perf_monitor.end_section()

        if self.move_select_overlay and self.move_select_overlay.active:
            perf_monitor.start_section("RENDER_MOVE_SELECT")
            self.move_select_overlay.render(screen)
            perf_monitor.end_section()

        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            perf_monitor.start_section("RENDER_EVOLUTION")
            self.evolution_overlay.render(screen)
            perf_monitor.end_section()

        # ===== DEBUG =====
        if show_debug:
            perf_monitor.start_section("RENDER_DEBUG")
            self._render_debug_info(screen)
            perf_monitor.end_section()

        # ===== UI OCULTA =====
        if self.ui_hidden:
            hint_font = pygame.font.Font(None, 20)
            hint_text = hint_font.render("[H] Mostrar UI", True, (150, 150, 180))
            hint_x = screen_mgr.viewport_x + screen_mgr.viewport_width - hint_text.get_width() - 15
            hint_y = screen_mgr.viewport_y + 15

            bg_rect = hint_text.get_rect(topleft=(hint_x - 8, hint_y - 4))
            bg_rect.width += 16
            bg_rect.height += 8
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 150))
            screen.blit(bg_surface, bg_rect)
            screen.blit(hint_text, (hint_x, hint_y))

        # ===== VITÓRIA FINAL =====
        if self.final_victory_overlay is not None:
            perf_monitor.start_section("RENDER_FINAL_VICTORY")
            self.final_victory_overlay.render(screen)
            perf_monitor.end_section()

        perf_monitor.start_section("RENDER_IN_GAME_DEBUG")
        self.in_game_debug.render(screen)
        perf_monitor.end_section()

        perf_monitor.end_section()

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo – com botão de minimizar funcional e layout compacto."""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        font = self._get_ui_font(20)
        font_small = self._get_ui_font(14)
        font_tiny = self._get_ui_font(12)

        # Dimensões do painel
        if self.ui_minimized:
            panel_width = 240
            panel_height = 40
        else:
            panel_width = 380
            panel_height = 140

        panel_x = viewport_x + 12
        panel_y = viewport_y + 12

        # Salva o retângulo do painel para detecção de clique
        self.ui_panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # Sombra
        shadow_rect = pygame.Rect(panel_x + 4, panel_y + 4, panel_width, panel_height)
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=10)

        # Fundo gradiente
        bg_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        for i in range(panel_height):
            alpha = int(200 - (i / panel_height) * 60)
            color = (10, 15, 30, alpha)
            pygame.draw.line(bg_surf, color, (0, i), (panel_width, i))
        pygame.draw.rect(bg_surf, (80, 120, 200, 80), bg_surf.get_rect(), 2, border_radius=10)
        screen.blit(bg_surf, (panel_x, panel_y))

        # Botão de minimizar
        btn_size = 20
        if self.ui_minimized:
            btn_x = panel_x + panel_width - btn_size - 4
            btn_y = panel_y + (panel_height - btn_size) // 2
        else:
            btn_x = panel_x + panel_width - btn_size - 8
            btn_y = panel_y + 6
        btn_rect = pygame.Rect(btn_x, btn_y, btn_size, btn_size)

        mouse_pos = pygame.mouse.get_pos()
        hover = btn_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (60, 70, 90) if not hover else (100, 120, 180), btn_rect, border_radius=4)
        pygame.draw.rect(screen, (180, 180, 200), btn_rect, 1, border_radius=4)
        icon = "−" if not self.ui_minimized else "+"
        icon_font = pygame.font.Font(None, 18)
        icon_surf = icon_font.render(icon, True, (255, 255, 255))
        icon_rect = icon_surf.get_rect(center=btn_rect.center)
        screen.blit(icon_surf, icon_rect)

        # ===== INDICADOR DE ATALHO PARA OCULTAR UI =====
        # Mostra um pequeno texto informando que H oculta a UI
        hint_font = pygame.font.Font(None, 13)
        hint_text = hint_font.render("[H] Ocultar UI", True, (120, 120, 160))
        hint_x = panel_x + panel_width - hint_text.get_width() - 8
        hint_y = panel_y + panel_height - 18
        screen.blit(hint_text, (hint_x, hint_y))

        # ===== MODO MINIMIZADO =====
        if self.ui_minimized:
            if self.game_state == "in_wave":
                wave_info = self.wave_manager.get_current_wave_info()
                progress = wave_info.get('progress', 0)
                # Barra ocupa o espaço disponível (deixando margem)
                bar_x = panel_x + 8
                bar_y = panel_y + (panel_height - 16) // 2
                bar_width = panel_width - 32  # margem para o botão
                bar_height = 16
                pygame.draw.rect(screen, (40, 45, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
                if progress > 0:
                    pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, int(bar_width * progress), bar_height),
                                     border_radius=5)
                pygame.draw.rect(screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 1, border_radius=5)
                # Texto resumido
                text = f"{wave_info['enemies_spawned']}/{wave_info['enemies_total']}"
                txt = font_tiny.render(text, True, (255, 255, 255))
                text_x = bar_x + (bar_width - txt.get_width()) // 2
                text_y = bar_y + (bar_height - txt.get_height()) // 2
                screen.blit(txt, (text_x, text_y))
            return

        # ===== MODO COMPLETO =====
        x_offset = panel_x + 14
        y_offset = panel_y + 8

        # Linha 1: Nome da fase
        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (x_offset, y_offset))
        y_offset += 20

        # Linha 2: Período e Clima
        info_parts = []
        if hasattr(self, 'day_night_weather') and self.day_night_weather.day_night_state:
            dn = self.day_night_weather.day_night_state
            period_text = dn.get_display_name()
            period_colors = {
                "Dia": (255, 200, 100),
                "Noite": (100, 150, 255),
                "Entardecer": (255, 180, 80),
                "Amanhecer": (255, 200, 200),
                "Caverna": (150, 150, 150),
                "Fundo do Mar": (80, 180, 255),
            }
            info_parts.append((period_text, period_colors.get(period_text, (255, 200, 100))))

        if hasattr(self, 'battle_system') and self.battle_system:
            weather = self.battle_system.weather_manager.current_weather
            if weather and weather.active:
                weather_name = weather.get_display_name()
                weather_color = {
                    "sandstorm": (194, 178, 128),
                    "rain": (100, 150, 255),
                    "sunny": (255, 215, 0)
                }.get(weather.type.value, (200, 200, 200))
                info_parts.append((weather_name, weather_color))

        info_x = x_offset
        for text, color in info_parts:
            txt = font_small.render(text, True, color)
            screen.blit(txt, (info_x, y_offset))
            info_x += txt.get_width() + 10
        y_offset += 18

        # Linha 3: Itens
        items_color = (100, 255, 100) if self.target_item_manager.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {self.target_item_manager.items_protected} protegidos  •  {self.target_item_manager.items_stolen} levados",
            True, items_color)
        screen.blit(items_text, (x_offset, y_offset))
        y_offset += 20

        # Wave info
        if self.game_state == "waiting":
            state_text = font_small.render("Aguardando início...", True, (200, 200, 200))
            screen.blit(state_text, (x_offset, y_offset))
        elif self.game_state == "in_wave":
            # Calcula altura máxima para as barras
            max_bar_height = panel_height - y_offset - 6
            self._draw_wave_progress_bars(screen, x_offset, y_offset, panel_width - 30, max_bar_height)
        elif self.game_state == "completed":
            complete_text = font.render("FASE COMPLETA!", True, (255, 215, 0))
            screen.blit(complete_text, (x_offset, y_offset))

    def _draw_minimized_progress(self, screen, x, y, width, height):
        """Desenha a barra de progresso resumida (modo minimizado)."""
        if self.game_state != "in_wave":
            return

        wave_info = self.wave_manager.get_current_wave_info()
        progress = wave_info.get('progress', 0)

        pygame.draw.rect(screen, (40, 45, 60), (x, y, width, height), border_radius=5)
        if progress > 0:
            pygame.draw.rect(screen, (0, 200, 0), (x, y, int(width * progress), height), border_radius=5)
        pygame.draw.rect(screen, (100, 100, 120), (x, y, width, height), 1, border_radius=5)

        # Texto resumido
        font = self._get_ui_font(12)
        text = f"{wave_info['enemies_spawned']}/{wave_info['enemies_total']}"
        txt = font.render(text, True, (255, 255, 255))
        text_x = x + (width - txt.get_width()) // 2
        text_y = y + (height - txt.get_height()) // 2
        screen.blit(txt, (text_x, text_y))

    def _draw_wave_progress_bars(self, screen, x, y, max_width, max_height):
        """Desenha barras de progresso para cada path/wave ativo – com divisores verticais."""
        spawner = self.wave_manager.spawner
        bars_data = []

        # Itera sobre todos os paths com waves
        for path_idx, waves in spawner.waves.items():
            wave_idx = spawner.current_wave_idx.get(path_idx, 0)
            if wave_idx >= len(waves):
                continue
            wave = waves[wave_idx]
            active = spawner.wave_active.get(path_idx, False)
            if not active:
                continue

            spawned = spawner.spawned_count.get(path_idx, 0)
            wave_size = wave.wave_size
            progress = min(1.0, spawned / wave_size) if wave_size > 0 else 0

            path_name = f"P{path_idx + 1}"
            bars_data.append((path_name, progress, spawned, wave_size))

        # Se não houver active, mostra uma única barra consolidada
        if not bars_data:
            wave_info = self.wave_manager.get_current_wave_info()
            progress = wave_info.get('progress', 0)
            bars_data = [("W", progress, wave_info['enemies_spawned'], wave_info['enemies_total'])]

        # Calcula altura disponível e distribui
        bar_height = 14
        spacing = 4
        total_height = len(bars_data) * (bar_height + spacing) - spacing
        if total_height > max_height:
            # Se não couber, reduz a altura
            bar_height = max(8, (max_height - (len(bars_data) - 1) * spacing) // len(bars_data))
            total_height = len(bars_data) * (bar_height + spacing) - spacing

        y_offset = y

        for i, (name, progress, spawned, total) in enumerate(bars_data):
            # Nome da wave
            name_font = self._get_ui_font(13)
            name_surf = name_font.render(name, True, (200, 200, 220))
            screen.blit(name_surf, (x, y_offset))
            name_width = name_surf.get_width() + 6

            # Barra
            bar_x = x + name_width
            bar_width = max_width - name_width - 10
            bar_y = y_offset + (bar_height - 14) // 2  # centraliza verticalmente

            # Fundo da barra
            pygame.draw.rect(screen, (40, 45, 60), (bar_x, bar_y, bar_width, 14), border_radius=4)
            # Preenchimento
            if progress > 0:
                pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, int(bar_width * progress), 14), border_radius=4)
            # Borda
            pygame.draw.rect(screen, (100, 100, 120), (bar_x, bar_y, bar_width, 14), 1, border_radius=4)

            # ===== DIVISORES VERTICAIS (em toda a largura da barra) =====
            if total > 0:
                segment_width = bar_width / total
                for seg in range(1, total):
                    line_x = bar_x + int(segment_width * seg)
                    pygame.draw.line(screen, (60, 70, 80), (line_x, bar_y), (line_x, bar_y + 14), 1)

            # Texto da contagem
            count_text = f"{spawned}/{total}"
            count_font = self._get_ui_font(11)
            count_surf = count_font.render(count_text, True, (255, 255, 255))
            count_x = bar_x + (bar_width - count_surf.get_width()) // 2
            count_y = bar_y + (14 - count_surf.get_height()) // 2
            screen.blit(count_surf, (count_x, count_y))

            y_offset += bar_height + spacing

    def _render_debug_info(self, screen):
        """Informações de debug"""
        mouse_pos = pygame.mouse.get_pos()
        screen_mgr = self.screen_manager
        camera = self.camera

        in_viewport = screen_mgr.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                tile_x = int(world_pos[0] // 16)
                tile_y = int(world_pos[1] // 16)
                tile_info = f"Tile: ({tile_x}, {tile_y})"

                path_info = "Nenhum path"
                for i, path in enumerate(self.path_renderer.paths):
                    for node in path.nodes:
                        dx = node[0] - world_pos[0]
                        dy = node[1] - world_pos[1]
                        if dx * dx + dy * dy < 400:
                            path_info = f"Próximo ao Path {i + 1}"
                            break
            else:
                world_text = "World: invalid position"
                tile_info = "Tile: N/A"
                path_info = "N/A"
        else:
            world_text = "World: outside viewport"
            tile_info = "Tile: outside"
            path_info = "N/A"

        wave_info = self.wave_manager.get_current_wave_info()

        debug_lines = [
            "=== DEBUG INFO ===",
            f"FPS: {screen_mgr.get_fps():.1f}",
            f"Game State: {self.game_state}",
            "",
            "=== WAVES ===",
            f"Status: {wave_info['name']}",
            f"Progresso: {wave_info['progress'] * 100:.1f}%",
            f"Vivos: {len(self.wave_manager.active_enemies)}",
            "",
            "=== CAMERA ===",
            f"Position: ({camera.x:.0f}, {camera.y:.0f})",
            f"Zoom: {camera.zoom:.2f}",
            "",
            "=== MOUSE ===",
            world_text,
            tile_info,
            path_info,
            "",
            "=== MAPA ===",
            f"Pixels: {self.world_width}x{self.world_height}",
            f"Paths: {len(self.path_renderer.paths)}",
            f"Pokémon: {len(self.placement_manager.placed_pokemon)}",
            f"Spots: {sum(1 for s in self.spot_renderer.get_spots() if s.occupied)}/{len(self.spot_renderer.get_spots())}",
        ]

        y_offset = screen_mgr.viewport_y + 40
        x_offset = screen_mgr.viewport_x + 10
        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 350
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(200)
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                text = self._debug_font_bold.render(line, True, (255, 255, 0))
            else:
                text = self._debug_font.render(line, True, (0, 255, 0))
            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height