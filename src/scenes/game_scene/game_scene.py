# src/scenes/game_scene.py
"""
Cena principal do jogo - COM NOVA ARQUITETURA DE WAVES
"""
import pygame

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
from src.battle.effects.specific.weather.weather_filter import WeatherFilter
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
from src.scenes.game_scene.components.managers.wave_manager import WaveManager
from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay
from src.scenes.game_scene.components.overlays.evolution_overlay import EvolutionOverlay
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.item_bag_renderer import ItemBagRenderer
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer # NOVO
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer
from src.managers.notification_manager import notification_manager
from src.ui.toast_renderer import toast_info, toast_warning, toast_battle
from src.battle.effects.specific.day_night.day_night_filter import DayNightFilter
from src.battle.effects.specific.day_night.day_night_state import DayNightType
from src.scenes.game_scene.components.day_night_weather_system import DayNightWeatherSystem

class GameScene(BaseScene):
    def __init__(self, game, chapter_id=1, phase_number=1):
        super().__init__(game)

        # Flag de debug
        self.debug_in_game = False
        self.move_select_overlay = None
        self.move_learn_overlay = None
        self.game_paused = False

        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.phase_id = f"{chapter_id}-{phase_number}"
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
        self.notification_manager = notification_manager
        self.target_item_manager = TargetItemManager(game)
        self.target_item_renderer = TargetItemRenderer()

        # Weather filter
        self.weather_filter = WeatherFilter()

        # CARREGA OS DADOS DA FASE (inclui _phase_data)
        self._load_phase_data()  # <--- PRIMEIRO CARREGA OS DADOS

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

        # Configurações de mundo
        self._setup_world_dimensions()

        self.player = game.player

        # Renderizadores
        self.item_bag_renderer = ItemBagRenderer(game, self.player.bag)
        self.item_drag_manager = ItemDragManager(game, self.player.bag)

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
        self.between_waves_timer = 3.0
        self.show_debug = False

        # Weather filter
        self.weather_filter = WeatherFilter()

        # Day/Night filter
        self.day_night_filter = DayNightFilter()

        # ===== SISTEMA DIA/NOITE E CLIMA =====
        self.day_night_weather = DayNightWeatherSystem(self)
        self.day_night_weather.initialize()  # Inicializa com valores aleatórios

        # Fontes cacheadas
        self._debug_font = pygame.font.Font(None, 18)
        self._debug_font_bold = pygame.font.Font(None, 20)
        self._debug_font_small = pygame.font.Font(None, 16)
        self._ui_font = None
        self._ui_font_small = None

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Cache de referências para otimização
        self._cached_spot_renderer = None
        self._cached_placement_manager = None
        self._cached_team_manager = None
        self._cached_item_bag_renderer = None

        # Inicia o jogo
        self._start_game()

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

    def _start_test_weather(self):
        """
        Inicia um clima de teste automaticamente ao carregar a fase.
        Para testar o filtro visual.
        """
        # Escolha um clima para teste: SANDSTORM, RAIN ou SUNNY
        test_weather = WeatherType.SANDSTORM

        # Duração: 30 segundos
        duration = 30.0

        # Aplica o clima
        self.battle_system.weather_manager.set_weather(test_weather, duration, source=None)

        # Mensagem no console
        weather_names = {
            WeatherType.SANDSTORM: "🌪️ TEMPESTADE DE AREIA (TESTE)",
            WeatherType.RAIN: "🌧️ CHUVA (TESTE)",
            WeatherType.SUNNY: "☀️ SOL FORTE (TESTE)"
        }
        print(f"\n{'=' * 50}")
        print(f"[WEATHER TEST] {weather_names.get(test_weather, 'CLIMA')} iniciado!")
        print(f"[WEATHER TEST] Duração: {duration}s")
        print(f"[WEATHER TEST] Filtro visual deve aparecer na tela")
        print(f"{'=' * 50}\n")

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
        # ===== RESTAURA COMPLETAMENTE TODOS OS POKÉMON =====
        self.cleanup()

        self.update_box_happiness()

        self._start_battle_music()

        self.wave_manager.initialize_condition()

        for pokemon in self.player.team:
            pokemon.reset(self)

        # Reseta ouro acumulado
        self.wave_manager.reset_gold()

        # Inicia as waves
        if self.wave_manager.has_more_waves():
            self.game_state = "in_wave"
            self.wave_manager.start_all_waves()

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        self.phase_info = phase_catalog.get_phase_info(self.chapter_id, self.phase_number)
        if not self.phase_info:
            self.phase_info = {
                "name": f"Fase {self.chapter_id}-{self.phase_number}",
                "number": self.phase_number,
                "chapter": self.chapter_id
            }

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        data = phase_loader.load_phase(self.chapter_id, self.phase_number)

        # ===== ARMAZENA OS DADOS DA FASE =====
        self._phase_data = data  # <--- ADICIONE ESTA LINHA

        if not data:
            self.phase_rewards = {"money": 0, "experience": 0}
            return

        base_path = PROJECT_ROOT

        # Carrega componentes
        self.map_renderer.load_from_data(phase_loader.get_map_data(), base_path)
        self.path_renderer.load_from_data(phase_loader.get_paths_data())
        self.spot_renderer.load_from_data(phase_loader.get_tower_spots_data())
        self.target_item_manager.load_from_data(data.get("target_items", {}))

        # Carrega recompensas
        rewards = data.get("rewards", {})
        self.phase_rewards = {
            "money": rewards.get("money", 0),
            "experience": rewards.get("experience", 0)
        }

    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            self.world_width = 2000
            self.world_height = 2000

    def _update_perf_monitor(self):
        """Atualiza o estado do monitor de performance baseado no debug"""
        perf_monitor.set_enabled(self.show_debug)
        if self.show_debug:
            # Reseta as métricas quando ativa
            perf_monitor.reset()

    def update_box_happiness(self):
        """Atualiza felicidade dos Pokémon na Box (-1 por fase)."""
        if not hasattr(self.player, 'pc_box'):
            return

        box_pokemon = self.player.pc_box
        if not box_pokemon:
            return

        team_ids = set(id(p) for p in self.player.team)

        for pokemon in box_pokemon:
            if id(pokemon) not in team_ids:
                pokemon.add_happiness(-1, "Na Box")

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
    # ===== MÉTODOS DE OVERLAY  =====

    def open_move_select_overlay(self, pokemon):
        """Abre o overlay de seleção de moves para um Pokémon"""
        if not pokemon or not pokemon.moves:
            return

        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de moves"""
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    def open_move_learn_overlay(self, pokemon, new_move_name):
        """Abre o overlay de aprendizado de novo move"""
        from src.scenes.game_scene.components.overlays.move_learn_overlay import MoveLearnOverlay

        self.move_learn_overlay = MoveLearnOverlay(self, pokemon, new_move_name)
        self.move_learn_overlay.active = True
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_learn_overlay(self, cancel=False):
        """Fecha o overlay de aprendizado de moves (MODIFICADO para TMs)"""
        if self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None

        # Se NÃO foi cancelado e temos dados pendentes de TM, aplica o aprendizado
        if not cancel and hasattr(self, 'pending_tm_data') and self.pending_tm_data:
            # O Pokémon já aprendeu o move via replace_move no overlay
            print(f"[TM] {self.pending_tm_data['move_name']} aprendido com sucesso!")

            # ===== CONQUISTAS: Ensino de Moves =====
            phase_id = f"{self.chapter_id}-{self.phase_number}"
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                ach_mgr = self.player.achievement_manager
                ach_mgr.increment_counter("move_taught_count")
                ach_mgr.check_and_unlock("first_move_taught", phase_id)
                ach_mgr.check_and_unlock("move_taught_10", phase_id)

            self.pending_tm_data = None

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

    def open_evolution_overlay(self, pokemon, evolution_data):
        """Abre o overlay de evolução para um Pokémon"""
        # Guarda o método de evolução para contagem depois
        if hasattr(pokemon, 'evolution'):
            method = evolution_data.get("method", "unknown")
            pokemon.evolution._pending_evolution_method = method

            # Se for evolução por felicidade com horário (Espeon/Umbreon)
            if method == "happiness" and "time_of_day" in evolution_data:
                pokemon._last_evolution_time_of_day = evolution_data.get("time_of_day")

            # Guarda os dados para referência
            pokemon._last_evolution_data = evolution_data

        sound_manager.play_effect(SoundEffect.EVOLUTION)
        self.evolution_overlay = EvolutionOverlay(self, pokemon, evolution_data)
        self.evolution_overlay.active = True

        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_evolution_overlay(self, cancel=False):
        """Fecha o overlay de evolução"""
        sound_manager.stop_effect(SoundEffect.EVOLUTION)

        if hasattr(self, 'evolution_overlay'):
            self.evolution_overlay = None

        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    # ===== MÉTODOS DE ITEM E CAPTURA =====

    def _on_item_use(self, target, item_data, target_type):
        """Callback quando um item é usado em um alvo. """
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
                        self.battle_system.effect_manager.remove_status(target)
                        toast_battle(f"{target.name} curou {status_to_cure}!", duration=4.0, pokemon=target,
                                     portrait="happy")

                        # ===== CONQUISTAS: CURA DE STATUS =====
                        phase_id = f"{self.chapter_id}-{self.phase_number}"
                        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                            ach_mgr = self.player.achievement_manager

                            # Cura de Veneno com Antídoto
                            if status_to_cure == "poison" and item_data.get("id") == "antidote":
                                ach_mgr.increment_counter("antidote_count")
                                ach_mgr.check_and_unlock("first_antidote", phase_id)
                                ach_mgr.check_and_unlock("antidote_100", phase_id)

                            # Cura de Sono com Awake
                            elif status_to_cure == "sleep" and item_data.get("id") == "awake":
                                ach_mgr.increment_counter("awake_count")
                                ach_mgr.check_and_unlock("first_awake", phase_id)
                                ach_mgr.check_and_unlock("awake_100", phase_id)

                            # Cura de Paralisia
                            elif status_to_cure == "paralysis":
                                ach_mgr.increment_counter("paralyze_heal_count")
                                ach_mgr.check_and_unlock("first_paralyze_heal", phase_id)
                                ach_mgr.check_and_unlock("paralyze_heal_100", phase_id)

                        return True
                return False

        # ===== CURA TODOS STATUS =====
        elif effect == "cure_all_status":
            if target_type == "ally":
                current_status = self.battle_system.effect_manager.get_status(target)
                if current_status and current_status.type.value != "none":
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

        elif effect == "battle_stat_boost":
            if target_type == "ally":
                return self._apply_battle_item(target, item_data)

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
            # Verifica se é BOSS primeiro
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
                pokemon.gain_xp(xp_needed)  # ganha XP exato para subir 1 nível
                new_level = pokemon.level

                if new_level > old_level:
                    toast_battle(
                        f"{pokemon.name} subiu para o nível {new_level}!",
                        duration=4.0,
                        pokemon=pokemon,
                        portrait="joyous"
                    )
                    # ===== CONQUISTA: RARE CANDY =====
                    phase_id = f"{self.chapter_id}-{self.phase_number}"
                    if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                        ach_mgr = self.player.achievement_manager
                        ach_mgr.increment_counter("rare_candy_count")
                        ach_mgr.check_and_unlock("rare_candy_3", phase_id)
                    return True
                else:
                    # Caso raro: não subiu (ex: nível máximo?) – não consome o item
                    return False
        # ===== MEDICAMENTOS =====
        elif target_type == "ally" and category == "medicine":
            medicine_success = self.use_medicine(target, item_data)
            return medicine_success


        return False

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
                phase_id = f"{self.chapter_id}-{self.phase_number}"
                self.player.achievement_manager.check_and_unlock("battle_item_replace", phase_id)
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
            phase_id = f"{self.chapter_id}-{self.phase_number}"
            self.player.achievement_manager.check_and_unlock("battle_item_use_10", phase_id)

        # Consome o item (retorna True)
        return True

    def _use_evolution_stone(self, pokemon, item_data):
        """Usa pedra de evolução em um Pokémon"""
        from src.managers.evolution_manager import evolution_manager

        stone_name = item_data["id"]
        evolution = evolution_manager.check_evolution(pokemon.id, stone_name=stone_name)

        if not evolution:
            self.player.bag.add_item(item_data["id"], 1)
            return False

        evolve_to_id = evolution["evolve_to"]
        pokemon._perform_evolution(evolve_to_id)

        self.player.caught_pokemon.add(evolve_to_id)
        self.player.register_seen(evolve_to_id)
        self.player.auto_save()
        return True

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
            phase_id = f"{self.chapter_id}-{self.phase_number}"
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                ach_mgr = self.player.achievement_manager
                ach_mgr.increment_counter("move_taught_count")
                ach_mgr.check_and_unlock("first_move_taught", phase_id)
                ach_mgr.check_and_unlock("move_taught_10", phase_id)

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
        """Tenta capturar um Pokémon selvagem."""
        # BOSS não pode ser capturado
        if hasattr(enemy, 'is_boss') and enemy.is_boss:
            toast_battle(f"Não é possível capturar {enemy.name}!", duration=2.0, pokemon=enemy, portrait="angry")
            return  # Sai sem fazer nada, mas a pokébola já foi consumida

        hp_ratio = enemy.current_hp / enemy.max_hp
        base_chance = (1 - hp_ratio * 0.5)

        multipliers = {
            "pokeball": 1.0,
            "greatball": 1.5,
            "ultraball": 2.0,
            "masterball": 100.0
        }
        multiplier = multipliers.get(item_data["id"], 1.0)
        chance = min(1.0, base_chance * multiplier)

        import random
        roll = random.random()

        print(f"[CAPTURE] Chance: {chance:.2f}, Roll: {roll:.2f}, Item: {item_data['id']}")

        # Master Ball sempre captura
        if item_data["id"] == "masterball":
            self._perform_capture(enemy)
            return

        # Tentativa de captura normal
        if roll < chance:
            self._perform_capture(enemy)
        else:
            # Captura falhou
            toast_battle(f"{enemy.name} escapou...", duration=2.0, pokemon=enemy, portrait="angry")
            print(f"[CAPTURE] {enemy.name} escapou! Pokébola foi consumida.")

    def _perform_capture(self, enemy):
        """Executa a captura de um Pokémon - COM SISTEMA DE CONQUISTAS"""
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
        caught.current_hp = enemy.current_hp
        caught.max_hp = enemy.max_hp
        caught.ivs = enemy.ivs.copy()
        caught.evs = enemy.evs.copy()
        caught.xp = enemy.xp
        caught.nature = enemy.nature

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
            phase_id = f"{self.chapter_id}-{self.phase_number}"

            # Incrementa contador de capturas
            self.player.achievement_manager.increment_counter("capture_count")

            # Verifica conquistas de captura (passando a fase atual)
            self.player.achievement_manager.check_and_unlock("first_capture", phase_id)
            self.player.achievement_manager.check_and_unlock("capture_10", phase_id)
            self.player.achievement_manager.check_and_unlock("capture_50", phase_id)

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
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
                if hasattr(player, 'achievement_manager'):
                    ach_mgr = player.achievement_manager
                    ach_mgr.increment_counter("revive_count")
                    ach_mgr.check_and_unlock("first_revive", phase_id)
                    ach_mgr.check_and_unlock("revive_25", phase_id)

            # ===== CONQUISTAS: Cura (Revive também conta) =====
            if game_scene and hasattr(game_scene, 'player'):
                player = game_scene.player
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
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
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
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
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
                if hasattr(player, 'achievement_manager'):
                    player.achievement_manager.increment_counter("heal_count")
                    player.achievement_manager.check_and_unlock("heal_5", phase_id)
                    player.achievement_manager.check_and_unlock("heal_100", phase_id)

            return True

        return False

    # ===== MÉTODOS DE POSICIONAMENTO =====

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

        if action == 'swap':
            self._on_pokemon_swap(placement_data)
        elif action == 'move':
            self._move_pokemon_to_spot(placement_data)
        else:
            pokemon = placement_data['pokemon']
            spot = placement_data['spot']
            self.placement_manager.add_pokemon(spot, pokemon)

    def _on_pokemon_swap(self, swap_data):
        """Troca as posições de dois Pokémon"""
        pokemon_a = swap_data['pokemon_a']
        pokemon_b = swap_data['pokemon_b']
        spot_a = swap_data['spot_a']
        spot_b = swap_data['spot_b']

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

    # ===== MÉTODOS DE LIMPEZA =====

    def cleanup(self):
        """Limpa o estado da fase antes de sair - INCLUI RESET DOS DITTOS"""
        self._stop_battle_music(fade_ms=500)

        # ===== LIMPA DIA/NOITE E CLIMA =====
        self.day_night_filter.clear()
        self.weather_filter.clear()
        if hasattr(self, 'day_night_weather'):
            self.day_night_weather._initialized = False

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

    def _stop_battle_music(self, fade_ms=1000):
        """Para a música de batalha"""
        if self.music_playing:
            sound_manager.stop_music(fade_ms)
            self.music_playing = False

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

        # ===== OVERLAYS PRIORITÁRIOS =====
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.handle_event(event)
            return None

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.handle_event(event)
            return None

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
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

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(player, 'bag'):
                    player.bag.cycle_category()
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
                        self.hovered_spot = spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
            return None

        return None

    # ===== MÉTODO FIXED_UPDATE  =====

    def fixed_update(self, dt):
        """Update da lógica do jogo - COM NOVO SISTEMA DE PERFORMANCE"""

        perf_monitor.start_frame()

        # ===== OVERLAYS =====
        perf_monitor.start_section("OVERLAYS")

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

        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            perf_monitor.end_section()
            perf_monitor.end_frame()
            return

        perf_monitor.end_section()

        # ===== PAUSA =====
        if self.game_paused or self.paused:
            perf_monitor.end_frame()
            return

        # ===== ATUALIZAÇÃO NORMAL =====
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

        perf_monitor.end_section()

        # Bag Renderer
        perf_monitor.start_section("BAG_RENDERER_UPDATE")
        if bag_renderer:
            bag_renderer.update(dt)
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

        # Target Items Update
        perf_monitor.start_section("TARGET_ITEMS_UPDATE")
        target_mgr.update(dt)
        perf_monitor.end_section()

        # ===== VERIFICA CONQUISTAS DE FELICIDADE =====
        if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
            ach_mgr = self.player.achievement_manager
            phase_id = f"{self.chapter_id}-{self.phase_number}"

            # Verifica conquista de felicidade máxima do time
            if not ach_mgr.is_unlocked("full_team_max_happiness"):
                ach_mgr.check_and_unlock("full_team_max_happiness", phase_id)

            # Verifica se algum Pokémon alcançou 100 de felicidade
            if not ach_mgr.is_unlocked("max_happiness"):
                ach_mgr.check_and_unlock("max_happiness", phase_id)

        # Effect Manager
        if hasattr(self, 'battle_system') and self.battle_system:
            perf_monitor.start_section("EFFECT_MANAGER")
            self.battle_system.effect_manager.update(dt)
            perf_monitor.end_section()


        self.notification_manager.update(dt)
        # ===== GAME OVER CHECK - MODIFICADO =====
        perf_monitor.start_section("GAME_OVER_CHECK")
        # Verifica se o time inteiro foi derrotado
        team_defeated = self.is_team_defeated()
        # Verifica se todos os itens foram roubados
        items_lost = target_mgr.items_protected <= 0
        perf_monitor.end_section()

        if team_defeated:
            print(f"[GAME_OVER] Time derrotado! Fim de jogo.")
            self._stop_battle_music(fade_ms=1000)
            self.game_state = "game_over"
            for pokemon in self.player.team:
                pokemon.add_happiness(-5, "Fase perdida")
            self.overlay_manager.show(OverlayType.GAME_OVER)

            for pokemon in self.player.team:
                pokemon.reset(self)

            perf_monitor.end_frame()
            return

        if items_lost:
            print(f"[GAME_OVER] Todos os itens foram roubados!")
            self.game_state = "game_over"
            for pokemon in self.player.team:
                pokemon.add_happiness(-5, "Fase perdida")
            self.overlay_manager.show(OverlayType.GAME_OVER)

            for pokemon in self.player.team:
                pokemon.reset(self)

            perf_monitor.end_frame()
            return

        # ===== Wave Manager Update =====
        perf_monitor.start_section("WAVE_MANAGER_UPDATE")
        enemies_at_end = wave_mgr.update(dt)
        perf_monitor.end_section()

        # ===== TRANSIÇÕES DE ESTADO =====
        perf_monitor.start_section("STATE_TRANSITIONS")
        if self.game_state == "in_wave":
            # Verifica se a wave está completamente finalizada
            # (sem inimigos vivos E sem waves pendentes)
            if wave_mgr.is_wave_completely_finished():
                if target_mgr.items_protected > 0:
                    print(f"[GAME] Fase COMPLETA! Todos os inimigos foram derrotados!")
                    self.game_state = "completed"
                    self._complete_phase()
                else:
                    print(f"[GAME] GAME OVER! Todos os itens foram roubados!")
                    self.game_state = "game_over"
                    self.overlay_manager.show(OverlayType.GAME_OVER)
        perf_monitor.end_section()

        perf_monitor.end_frame()

    def _complete_phase(self):
        """Marca a fase como completada e dá as recompensas"""
        from src.config.progress import progress_manager

        self._stop_battle_music(fade_ms=1000)

        # ===== RESETA TODOS OS DITTOS TRANSFORMADOS =====
        self.reset_all_transformed_dittos()

        for pokemon in self.player.team:
            pokemon.add_happiness(5, "Fase completada")

        base_reward = self.phase_rewards['money']
        gold_from_defeats = self.wave_manager.get_total_gold_earned()

        total_items = len(self.target_item_manager.items)
        stolen_items = self.target_item_manager.items_stolen

        bonus_amount = 0
        perfect_run = False

        if stolen_items == 0 and total_items > 0:
            bonus_amount = int(gold_from_defeats * 0.3)
            perfect_run = True

            # ===== CONQUISTAS: Fase Perfeita =====
            if hasattr(self, 'player') and hasattr(self.player, 'achievement_manager'):
                phase_id = f"{self.chapter_id}-{self.phase_number}"
                self.player.achievement_manager.increment_counter("perfect_phase_count")
                self.player.achievement_manager.check_and_unlock("perfect_phase", phase_id)
                print(f"[ACHIEVEMENT] Fase perfeita! Verificando conquistas...")

        gold_total = base_reward + gold_from_defeats + bonus_amount

        self.player.money += gold_total
        print(f"[REWARD] Ouro adicionado: {gold_total}")

        for pokemon in self.player.team:
            pokemon.reset(self)

        self.player.score += self.phase_rewards['experience']

        if total_items > 0:
            protected_items = self.target_item_manager.items_protected
            stars = int((protected_items / total_items) * 3)
            stars = max(1, min(3, stars))
        else:
            stars = 3

        self.phase_complete_data = {
            "base_reward": base_reward,
            "gold_from_defeats": gold_from_defeats,
            "bonus_amount": bonus_amount,
            "gold_total": gold_total,
            "total_xp": self.phase_rewards['experience'],
            "perfect_run": perfect_run,
            "stars": stars
        }

        progress_manager.complete_phase(self.phase_id, stars=stars)
        self.player.auto_save()
        self.overlay_manager.show(OverlayType.PHASE_COMPLETE)

    # ===== MÉTODOS DE RENDER =====

    def render(self, screen):
        """Renderiza o jogo - COM NOVO SISTEMA DE PERFORMANCE"""

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

        # Mapa
        perf_monitor.start_section("RENDER_MAP")
        map_renderer.render(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # Paths (apenas debug)
        if show_debug:
            perf_monitor.start_section("RENDER_PATHS")
            path_renderer.render(screen, camera, screen_mgr, show_editing=False)
            perf_monitor.end_section()

        # Spots
        perf_monitor.start_section("RENDER_SPOTS")
        if spot_renderer:
            spot_renderer.render(
                screen, camera, screen_mgr,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )
        perf_monitor.end_section()

        # Target items (ground)
        perf_monitor.start_section("RENDER_TARGET_ITEMS_GROUND")
        target_mgr.render_in_ground(screen, camera)
        perf_monitor.end_section()

        # Inimigos
        perf_monitor.start_section("RENDER_ENEMIES")
        for enemy in wave_mgr.active_enemies:
            enemy.render(screen, camera, show_hp=False)
        perf_monitor.end_section()

        # Pokémon colocados
        perf_monitor.start_section("RENDER_PLACED_POKEMON")
        if placement_mgr:
            placement_mgr.render(screen, camera, screen_mgr)
        perf_monitor.end_section()

        # Projéteis
        perf_monitor.start_section("RENDER_PROJECTILES")
        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, camera, self.screen_manager)
        perf_monitor.end_section()

        # Target items (on pokemon)
        perf_monitor.start_section("RENDER_TARGET_ITEMS_POKEMON")
        target_mgr.render_in_pokemon(screen, camera)
        perf_monitor.end_section()

        # HP Bars - Inimigos
        perf_monitor.start_section("RENDER_ENEMY_HP")
        for enemy in wave_mgr.active_enemies:
            enemy.render_hp_enemy(screen, camera)
        perf_monitor.end_section()

        # HP Bars - Pokémon
        perf_monitor.start_section("RENDER_POKEMON_HP")
        if placement_mgr:
            placement_mgr.render_hp(screen, camera)
        perf_monitor.end_section()

        # ===== RENDERIZAÇÃO DOS FILTROS DE CLIMA E DIA/NOITE =====
        # IMPORTANTE: A ORDEM É: 1. CLIMA, 2. DIA/NOITE
        perf_monitor.start_section("RENDER_WEATHER_AND_DAYNIGHT")

        viewport_rect = pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height
        )

        # ===== 1. FILTRO DE CLIMA (CHUVA, AREIA, SOL) =====
        if hasattr(self, 'battle_system') and self.battle_system:
            weather = self.battle_system.weather_manager.current_weather
            if weather and weather.active:
                self.weather_filter.render(screen, weather, viewport_rect)

        # ===== 2. FILTRO DE DIA/NOITE (POR CIMA DO CLIMA) =====
        if hasattr(self, 'day_night_weather'):
            day_night = self.day_night_weather.day_night_state
            if day_night and day_night.active:
                self.day_night_filter.render(screen, day_night, viewport_rect)

        perf_monitor.end_section()

        # UI do jogo
        perf_monitor.start_section("RENDER_GAME_UI")
        self._render_game_ui(screen)
        perf_monitor.end_section()

        # Team Manager UI
        perf_monitor.start_section("RENDER_TEAM_MANAGER")
        if team_mgr:
            team_mgr.render(screen, camera, spot_renderer.get_spots() if spot_renderer else [])
        perf_monitor.end_section()

        # Drag Manager
        perf_monitor.start_section("RENDER_DRAG_MANAGER")
        if drag_mgr:
            drag_mgr.render(screen, camera)
        perf_monitor.end_section()

        # Item Bag
        perf_monitor.start_section("RENDER_ITEM_BAG")
        if bag_renderer:
            bag_renderer.render(screen)
        perf_monitor.end_section()

        # Borda da viewport
        perf_monitor.start_section("RENDER_VIEWPORT_BORDER")
        pygame.draw.rect(screen, (80, 80, 80),
                         (screen_mgr.viewport_x, screen_mgr.viewport_y,
                          screen_mgr.viewport_width, screen_mgr.viewport_height), 1)
        perf_monitor.end_section()

        # Overlay Manager
        viewport_rect = pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height
        )
        self.notification_manager.render(screen, viewport_rect)

        perf_monitor.start_section("RENDER_OVERLAY_MANAGER")
        if overlay_mgr:
            overlay_mgr.render(screen)
        perf_monitor.end_section()

        # Move Learn Overlay
        if self.move_learn_overlay and self.move_learn_overlay.active:
            perf_monitor.start_section("RENDER_MOVE_LEARN")
            self.move_learn_overlay.render(screen)
            perf_monitor.end_section()

        # Move Select Overlay
        if self.move_select_overlay and self.move_select_overlay.active:
            perf_monitor.start_section("RENDER_MOVE_SELECT")
            self.move_select_overlay.render(screen)
            perf_monitor.end_section()

        # Evolution Overlay
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            perf_monitor.start_section("RENDER_EVOLUTION")
            self.evolution_overlay.render(screen)
            perf_monitor.end_section()

        # Debug Info
        if show_debug:
            perf_monitor.start_section("RENDER_DEBUG")
            self._render_debug_info(screen)
            perf_monitor.end_section()

        perf_monitor.end_section()

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo"""
        font = self._get_ui_font(24)
        font_small = self._get_ui_font(18)

        wave_info = self.wave_manager.get_current_wave_info()
        target_mgr = self.target_item_manager
        screen_mgr = self.screen_manager
        wave_mgr = self.wave_manager

        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        ui_bg = pygame.Surface((400, 180))  # Aumentado para acomodar clima
        ui_bg.set_alpha(180)
        ui_bg.fill((20, 20, 30))
        screen.blit(ui_bg, (viewport_x + 10, viewport_y + 10))

        y_offset = viewport_y + 15

        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (viewport_x + 15, y_offset))
        y_offset += 25

        # ===== PERIODO (DIA/NOITE) =====
        if hasattr(self, 'day_night_weather'):
            day_night = self.day_night_weather.day_night_state
            if day_night:
                period_text = day_night.get_display_name()
                # Cores específicas para cada tipo
                period_colors = {
                    "Dia": (255, 200, 100),
                    "Noite": (100, 150, 255),
                    "Entardecer": (255, 180, 80),
                    "Amanhecer": (255, 200, 200),
                    "Caverna": (150, 150, 150),
                    "Fundo do Mar": (80, 180, 255),
                }
                period_color = period_colors.get(period_text, (255, 200, 100))
                period_display = font_small.render(f"Periodo: {period_text}", True, period_color)
                screen.blit(period_display, (viewport_x + 15, y_offset))
                y_offset += 20

        # ===== CLIMA =====
        if hasattr(self, 'battle_system') and self.battle_system:
            weather = self.battle_system.weather_manager.current_weather
            if weather and weather.active:
                weather_name = weather.get_display_name()
                weather_color = {
                    "sandstorm": (194, 178, 128),
                    "rain": (100, 150, 255),
                    "sunny": (255, 215, 0)
                }.get(weather.type.value, (200, 200, 200))

                weather_display = font_small.render(f"Clima: {weather_name}", True, weather_color)
                screen.blit(weather_display, (viewport_x + 15, y_offset))
                y_offset += 20

        # ===== ITENS =====
        items_color = (100, 255, 100) if target_mgr.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {target_mgr.items_protected} protegidos | {target_mgr.items_stolen} levados",
            True, items_color
        )
        screen.blit(items_text, (viewport_x + 15, y_offset))
        y_offset += 20

        # ===== ESTADO DO JOGO =====
        if self.game_state == "waiting":
            state_text = font_small.render("Aguardando inicio...", True, (200, 200, 200))
            screen.blit(state_text, (viewport_x + 15, y_offset))

        elif self.game_state == "in_wave":
            active_paths = wave_info.get('active_paths', 0)
            if active_paths > 1:
                wave_text = font_small.render(
                    f"{active_paths} paths ativos | {wave_info['name']}",
                    True, (100, 255, 100))
            else:
                wave_text = font_small.render(
                    f"Wave {wave_info['index']}/{wave_info['total']}: {wave_info['name']}",
                    True, (100, 255, 100))
            screen.blit(wave_text, (viewport_x + 15, y_offset))
            y_offset += 20

            # ===== BARRA DE PROGRESSO =====
            bar_x = viewport_x + 15
            bar_y = y_offset
            bar_width = 370
            bar_height = 15

            pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))
            progress_width = int(bar_width * wave_info['progress'])
            pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, progress_width, bar_height))
            pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

            progress_text = font_small.render(
                f"{wave_info['enemies_spawned']}/{wave_info['enemies_total']}",
                True, (255, 255, 255))
            text_x = bar_x + (bar_width - progress_text.get_width()) // 2
            screen.blit(progress_text, (text_x, bar_y + 2))

            y_offset += 25

            # ===== INIMIGOS VIVOS =====
            enemies_color = (255, 100, 100) if wave_mgr.active_enemies else (100, 255, 100)
            enemies_text = font_small.render(
                f"Inimigos vivos: {len(wave_mgr.active_enemies)}",
                True, enemies_color)
            screen.blit(enemies_text, (viewport_x + 15, y_offset))

        elif self.game_state == "completed":
            complete_text = font.render("FASE COMPLETA!", True, (255, 215, 0))
            screen.blit(complete_text, (viewport_x + 15, y_offset))

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