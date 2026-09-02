# src/battle/effects/effect_manager.py
from typing import Dict, List, Optional, Tuple
from .status_effect import StatusEffect, StatusType
from .stat_modifier import StatModifier, StatType, StatStage
import pygame

from src.ui.toast_renderer import toast_battle


class EffectManager:
    """
    Gerencia todos os efeitos aplicados aos Pokémon
    """

    def __init__(self):
        # Status effects por Pokémon (não-voláteis: poison, burn, paralysis, sleep, freeze)
        self.status_effects: Dict[int, StatusEffect] = {}

        # Confusion effects por Pokémon (status volátil)
        self.confusion_effects: Dict[int, object] = {}

        # Stat modifiers por Pokémon
        self.stat_modifiers: Dict[int, List[StatModifier]] = {}

        self._pokemon_refs: Dict[int, object] = {}

        # Stat stages por Pokémon
        self.stat_stages: Dict[int, StatStage] = {}

        # Feedback visual (APENAS para efeitos temporários como "MISS", "Drenou", etc)
        self.status_texts: List[Tuple[int, str, float]] = []

        self.battle_item_buffs: Dict[int, dict] = {}

        # Tempo para ticks de status (a cada 2 segundos)
        self.status_timer: float = 0.0
        self.STATUS_TICK_INTERVAL = 2.0
        self.font_cache = {}

    def apply_status(self, pokemon, status: StatusEffect, source=None):
        """Aplica um efeito de status a um Pokémon (com verificação de imunidade)"""
        from .status_effect import TypeImmunity

        # ===== VERIFICA SAFEGUARD =====
        if hasattr(pokemon, '_safeguard_active') and pokemon._safeguard_active:
            # Safeguard previne status, exceto se for auto-aplicado (Rest, etc)
            if source != pokemon:  # Não bloqueia status auto-aplicados
                # Decrementa o contador
                pokemon._safeguard_remaining -= 1

                self.add_status_text(
                    pokemon,
                    f"O Safeguard protegeu {pokemon.name} de {status.name}! ({pokemon._safeguard_remaining} proteções restantes)",
                    duration=1.5
                )
                print(
                    f"[SAFEGUARD] {pokemon.name} está protegido contra {status.name}! Restam {pokemon._safeguard_remaining}")

                # Se acabaram as proteções, remove o efeito
                if pokemon._safeguard_remaining <= 0:
                    pokemon._safeguard_active = False
                    self.add_status_text(
                        pokemon,
                        f"O Safeguard de {pokemon.name} acabou!",
                        duration=1.0
                    )
                    print(f"[SAFEGUARD] Proteção de {pokemon.name} acabou!")

                return False

        pokemon_id = id(pokemon)

        # ===== VERIFICAÇÃO DE IMUNIDADE =====
        if TypeImmunity.is_immune_to_status(pokemon, status.type):
            # Mostra mensagem de imunidade
            message = TypeImmunity.get_immunity_message(pokemon, status.type)
            self.add_status_text(pokemon, message, duration=1.5)
            print(f"[IMMUNITY] {pokemon.name} é imune a {status.type.value}! Não aplicando status.")
            return False

        # Verifica se já tem status
        if pokemon_id in self.status_effects:
            existing = self.status_effects[pokemon_id]
            if existing.type != StatusType.NONE:
                # Verifica conflitos de status
                conflicting = [StatusType.PARALYSIS, StatusType.BURN, StatusType.POISON, StatusType.TOXIC_POISON]
                if existing.type in conflicting and status.type in conflicting:
                    print(f"[STATUS] {pokemon.name} já está com {existing.name}, não pode aplicar {status.name}!")
                    return False
                if existing.type in [StatusType.SLEEP, StatusType.FREEZE]:
                    self.remove_status(pokemon)
                else:
                    return False

        self.status_effects[pokemon_id] = status
        status.apply(pokemon, self)

        # Mostra mensagem de aplicação
        status_messages = {
            StatusType.POISON: f"{pokemon.name} foi envenenado!",
            StatusType.TOXIC_POISON: f"{pokemon.name} foi gravemente envenenado!",
            StatusType.BURN: f"{pokemon.name} foi queimado!",
            StatusType.PARALYSIS: f"{pokemon.name} está paralisado!",
            StatusType.SLEEP: f"{pokemon.name} caiu no sono!",
            StatusType.FREEZE: f"{pokemon.name} está congelado!",
            StatusType.CONFUSION: f"{pokemon.name} está confuso!"
        }

        if not pokemon.is_wild and status.type in status_messages:
            toast_battle(f"{status_messages[status.type]}", duration=5.0, pokemon=pokemon, portrait="pain")

        # ===== FORÇA ATUALIZAÇÃO DA ANIMAÇÃO =====
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()

        return True

    def remove_status(self, pokemon):
        """Remove efeito de status do Pokémon"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.status_effects:
            status = self.status_effects[pokemon_id]
            status.remove(pokemon, self)
            del self.status_effects[pokemon_id]

            # Remove modificador de velocidade da paralisia
            if status.type == StatusType.PARALYSIS:
                # Remove o modificador de speed (aplica +2 para compensar)
                if pokemon_id in self.stat_stages:
                    self.stat_stages[pokemon_id].modify(StatType.SPEED, 2)

            # ===== FORÇA ATUALIZAÇÃO DA ANIMAÇÃO =====
            if hasattr(pokemon, 'update_status_animation'):
                pokemon.update_status_animation()

            return True

        return False

    def get_status(self, pokemon) -> Optional[StatusEffect]:
        """Retorna o status atual do Pokémon"""
        return self.status_effects.get(id(pokemon))

    # ===== MÉTODOS DE CONFUSÃO (STATUS VOLÁTIL) =====

    def apply_confusion(self, pokemon, source=None, duration: int = None):
        """Aplica confusão a um Pokémon (status volátil)"""
        from .confusion_effect import ConfusionEffect

        pokemon_id = id(pokemon)

        # Verifica imunidade (Own Tempo / Ritmo Próprio)
        if hasattr(pokemon, 'has_ability') and pokemon.has_ability("Own Tempo"):
            self.add_status_text(pokemon, f"{pokemon.name} tem Ritmo Próprio e não ficou confuso!")
            print(f"[CONFUSION] {pokemon.name} é imune à confusão (Own Tempo)")
            return False

        # Remove confusão existente (substitui)
        if pokemon_id in self.confusion_effects:
            self.remove_confusion(pokemon)

        # Cria novo efeito
        effect = ConfusionEffect(source=source)
        if duration:
            effect.remaining_turns = duration

        self.confusion_effects[pokemon_id] = effect
        effect.apply(pokemon, self)
        return True

    def remove_confusion(self, pokemon):
        """Remove confusão de um Pokémon"""
        pokemon_id = id(pokemon)
        if pokemon_id in self.confusion_effects:
            effect = self.confusion_effects[pokemon_id]
            effect.remove(pokemon, self)
            del self.confusion_effects[pokemon_id]
            return True
        return False

    def is_confused(self, pokemon) -> bool:
        """Verifica se o Pokémon está confuso"""
        return id(pokemon) in self.confusion_effects

    def get_confusion(self, pokemon):
        """Retorna o efeito de confusão se existir"""
        return self.confusion_effects.get(id(pokemon))

    def register_pokemon(self, pokemon):
        """Registra um Pokémon para poder atualizá-lo quando necessário"""
        self._pokemon_refs[id(pokemon)] = pokemon
        print(f"[EFFECT] Pokémon {pokemon.name} registrado (id={id(pokemon)})")

    def unregister_pokemon(self, pokemon):
        """Remove um Pokémon do registro"""
        pokemon_id = id(pokemon)
        if pokemon_id in self._pokemon_refs:
            del self._pokemon_refs[pokemon_id]
            print(f"[EFFECT] Pokémon {pokemon.name} removido do registro")

    def add_stat_modifier(self, pokemon, stat_type: StatType, stages: int, duration: float = None,
                          is_battle_item: bool = False):
        """Adiciona um modificador de stat a um Pokémon"""
        pokemon_id = id(pokemon)

        # ===== VERIFICA FORESIGHT - IMPEDE AUMENTO DE EVASÃO =====
        if stat_type == StatType.EVASION and stages > 0:  # Tentando aumentar evasão
            if hasattr(pokemon, '_foresight_active') and pokemon._foresight_active:
                # Impede o aumento
                self.add_status_text(
                    pokemon,
                    f"Foresight impede o aumento de evasão de {pokemon.name}!",
                    duration=1.0
                )
                print(f"[FORESIGHT] {pokemon.name} não pode aumentar evasão devido a Foresight!")
                return False

        print(
            f"[EFFECT] Aplicando modificador em {pokemon.name}: {stat_type} {stages:+d} (duração: {duration if duration else 'permanente'}, battle_item: {is_battle_item})")

        # Inicializa stage se necessário
        if pokemon_id not in self.stat_stages:
            self.stat_stages[pokemon_id] = StatStage()

        # Aplica a modificação nos estágios
        old_stage = self.stat_stages[pokemon_id].get_stage(stat_type)
        new_stage = self.stat_stages[pokemon_id].modify(stat_type, stages)

        print(f"[EFFECT] {pokemon.name} - {stat_type}: {old_stage:+d} -> {new_stage:+d}")

        # Guarda o modificador para controle de duração
        if pokemon_id not in self.stat_modifiers:
            self.stat_modifiers[pokemon_id] = []

        modifier = StatModifier(stat_type, stages, duration, is_battle_item=is_battle_item)
        self.stat_modifiers[pokemon_id].append(modifier)

        # ===== FORÇA ATUALIZAÇÃO DA VELOCIDADE IMEDIATAMENTE =====
        if stat_type == StatType.SPEED and hasattr(pokemon, 'update_move_speed_from_effects'):
            pokemon.update_move_speed_from_effects()
            print(f"[SPEED] Velocidade de {pokemon.name} atualizada imediatamente após aplicar modificador")

        return True

    def _get_stat_name(self, stat_type: StatType) -> str:
        """Retorna o nome do stat em português (para uso interno)"""
        names = {
            StatType.ATTACK: "Ataque",
            StatType.DEFENSE: "Defesa",
            StatType.SP_ATTACK: "Ataque Especial",
            StatType.SP_DEFENSE: "Defesa Especial",
            StatType.SPEED: "Velocidade",
            StatType.ACCURACY: "Precisão",
            StatType.EVASION: "Evasão"
        }
        return names.get(stat_type, stat_type.value)

    def get_stat_multiplier(self, pokemon, stat_type: StatType) -> float:
        """Retorna o multiplicador total para um stat"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.stat_stages:
            stage = self.stat_stages[pokemon_id].get_stage(stat_type)
            multiplier = self.stat_stages[pokemon_id].get_multiplier(stat_type)
            return multiplier
        else:
            return 1.0

    def get_stat_stage(self, pokemon, stat_type: StatType) -> int:
        """Retorna o estágio atual de um stat"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.stat_stages:
            return self.stat_stages[pokemon_id].get_stage(stat_type)

        return 0

    def get_all_modifiers(self, pokemon) -> Dict[str, int]:
        """Retorna todos os modificadores ativos para um Pokémon"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.stat_stages:
            return self.stat_stages[pokemon_id].get_all_active_modifiers()

        return {}

    def set_battle_item_buff(self, pokemon, stat_type: StatType, duration: float):
        """Registra um buff de batalha ativo para o Pokémon."""
        import time
        pokemon_id = id(pokemon)
        self.battle_item_buffs[pokemon_id] = {
            "stat": stat_type,
            "expires": time.time() + duration
        }

    def get_battle_item_buff(self, pokemon) -> Optional[dict]:
        """Retorna o buff de batalha ativo, se houver."""
        pokemon_id = id(pokemon)
        return self.battle_item_buffs.get(pokemon_id)

    def remove_battle_item_buff(self, pokemon):
        """Remove o buff de batalha ativo manualmente."""
        pokemon_id = id(pokemon)
        if pokemon_id in self.battle_item_buffs:
            del self.battle_item_buffs[pokemon_id]

    def clear_battle_item_buffs(self):
        """Limpa todos os buffs de batalha (usado ao terminar batalha)."""
        self.battle_item_buffs.clear()

    def update(self, dt: float):
        """Atualiza todos os efeitos - dt em segundos"""

        # Atualiza modificadores com duração limitada
        expired_modifiers = []
        pokemon_to_update = set()

        for pokemon_id, modifiers in self.stat_modifiers.items():
            for modifier in modifiers[:]:
                if not modifier.is_permanent:
                    if not modifier.update(dt):
                        expired_modifiers.append((pokemon_id, modifier))
                        modifiers.remove(modifier)
                        pokemon_to_update.add(pokemon_id)

        # Aplica a remoção de estágios
        for pokemon_id, modifier in expired_modifiers:
            if pokemon_id in self.stat_stages:
                old_stage = self.stat_stages[pokemon_id].get_stage(modifier.stat_type)
                self.stat_stages[pokemon_id].modify(modifier.stat_type, -modifier.stages)
                new_stage = self.stat_stages[pokemon_id].get_stage(modifier.stat_type)

                # Se o estágio voltou a 0, remove o StatStage se não tiver outros modificadores
                if new_stage == 0 and not any(s != 0 for s in self.stat_stages[pokemon_id].stages.values()):
                    del self.stat_stages[pokemon_id]

            # ===== REMOVE DO DICIONÁRIO DE BUFFS DE BATALHA SE FOR UM =====
            if modifier.is_battle_item and pokemon_id in self.battle_item_buffs:
                # Verifica se o buff ainda é o mesmo stat (pode ter sido substituído manualmente)
                buff = self.battle_item_buffs[pokemon_id]
                if buff["stat"] == modifier.stat_type:
                    del self.battle_item_buffs[pokemon_id]
                    # Mensagem visual de expiração
                    if pokemon_id in self._pokemon_refs:
                        pokemon = self._pokemon_refs[pokemon_id]
                        self.add_status_text(pokemon, f"O buff de batalha de {pokemon.name} acabou!", duration=1.5)
                    print(f"[BATTLE_ITEM] Buff de {modifier.stat_type.value} expirou para Pokémon {pokemon_id}")

        # Atualiza velocidade
        self._update_speed_for_pokemon_ids(pokemon_to_update)

        # ===== ATUALIZA STATUS EFFECTS (não-voláteis) =====
        status_to_remove = []

        # Cria uma lista de tuplas (pokemon_id, status) para iterar com segurança
        status_items = list(self.status_effects.items())

        for pokemon_id, status in status_items:
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]

                # ===== PULA SE O POKÉMON ESTÁ DERROTADO =====
                if hasattr(pokemon, 'is_defeated') and pokemon.is_defeated:
                    # Pokémon derrotado não deve mais ter status
                    print(f"[EFFECT] {pokemon.name} está derrotado mas ainda tem status! Removendo...")
                    status_to_remove.append(pokemon_id)
                    continue

                # Para congelamento, o update retorna False se descongelou
                if status.type == StatusType.FREEZE:
                    is_still_frozen = status.update_freeze(dt)
                    if not is_still_frozen:
                        status_to_remove.append(pokemon_id)
                    continue

                # update retorna False se o status acabou
                if not status.update(pokemon, self, dt):
                    status_to_remove.append(pokemon_id)

        for pokemon_id in status_to_remove:
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]
                self.remove_status(pokemon)

        # Limpa textos temporários
        novos_textos = []
        for pokemon_id, text, duration in self.status_texts:
            nova_duracao = duration - dt
            if nova_duracao > 0:
                novos_textos.append((pokemon_id, text, nova_duracao))

        self.status_texts = novos_textos

    def _update_speed_for_pokemon_ids(self, pokemon_ids: set):
        """Força atualização da velocidade para Pokémon com IDs específicos"""
        for pokemon_id in pokemon_ids:
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]
                if hasattr(pokemon, 'update_move_speed_from_effects'):
                    old_speed = pokemon.move_speed
                    pokemon.update_move_speed_from_effects()
                    if old_speed != pokemon.move_speed:
                        print(
                            f"[SPEED] {pokemon.name} velocidade: {old_speed:.2f} -> {pokemon.move_speed:.2f} (após expiração de modificador)")

    def add_status_text(self, pokemon, text: str, duration: float = 1.5):
        """Adiciona um texto de feedback visual acima do Pokémon (APENAS para temporários)"""
        pokemon_id = id(pokemon)
        self.status_texts.append((pokemon_id, text, duration))

    def get_status_texts(self, pokemon) -> List[Tuple[str, float]]:
        """Retorna os textos ativos para um Pokémon"""
        pokemon_id = id(pokemon)
        return [(text, duration) for pid, text, duration in self.status_texts if pid == pokemon_id]

    def render_status_texts(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """Renderiza os textos de status temporários (MISS, Drenou, etc) - MAIS ACIMA AINDA"""
        texts = self.get_status_texts(pokemon)

        if not texts:
            return

        font_size = max(12, int(16 * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]
        sprite_height = sprite_rect.height

        # Textos temporários ficam BEM no topo (offset -100%)
        base_offset = -sprite_height * 1.2

        for i, (text, duration) in enumerate(texts):
            # Cor baseada no tipo de mensagem
            if "Drenou" in text or "cura" in text or "+" in text:
                color = (100, 255, 100)
            elif "MISS" in text or "-" in text:
                color = (255, 100, 100)
            else:
                color = (255, 255, 255)

            text_surf = font.render(text, True, color)
            text_rect = text_surf.get_rect()
            text_rect.centerx = sprite_rect.centerx
            text_rect.bottom = sprite_rect.top + base_offset - (i * (font_size + 4))

            screen.blit(text_surf, text_rect)

    def render_stat_modifiers(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """
        Renderiza os modificadores de stat (como Atk -3, Spd -2)
        Posicionados ABAIXO do status e ACIMA do nome
        """
        pokemon_id = id(pokemon)

        # Obtém modificadores ativos do StatStage
        if pokemon_id not in self.stat_stages:
            return

        # Obtém lista ordenada de modificadores
        ordered_modifiers = self.stat_stages[pokemon_id].get_ordered_modifiers()

        if not ordered_modifiers:
            return

        # ===== ESCALA DA FONTE =====
        base_font_size = 11

        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(9, int(base_font_size * total_scale))
        else:
            font_size = max(9, int(base_font_size * zoom_scale))

        # Usar cache de fontes
        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Cria as strings dos modificadores
        modifier_parts = []
        has_debuff = False
        has_buff = False

        for stat_name, stage in ordered_modifiers:
            if stage > 0:
                modifier_parts.append(f"{stat_name}+{stage}")
                has_buff = True
            elif stage < 0:
                modifier_parts.append(f"{stat_name}{stage}")
                has_debuff = True

        if not modifier_parts:
            return

        combined_text = " ".join(modifier_parts)

        # Define a cor
        if has_debuff and has_buff:
            color = (255, 255, 150)
        elif has_debuff:
            color = (255, 150, 150)
        elif has_buff:
            color = (150, 255, 150)
        else:
            color = (200, 200, 200)

        # Renderiza o texto
        text_surf = font.render(combined_text, True, color)
        text_rect = text_surf.get_rect()

        # ===== POSICIONAMENTO: ABAIXO DO STATUS, ACIMA DO NOME =====
        sprite_height = sprite_rect.height

        # Status está em -100% (mais acima)
        # Modificadores ficam em -80% (abaixo do status)
        relative_offset = -sprite_height * 0.7

        text_rect.centerx = sprite_rect.centerx
        text_rect.bottom = sprite_rect.top + relative_offset

        # Fundo semi-transparente
        bg_width = text_rect.width + 8
        bg_height = text_rect.height + 4
        bg_surf = pygame.Surface((bg_width, bg_height))
        bg_surf.set_alpha(180)
        bg_surf.fill((0, 0, 0))
        screen.blit(bg_surf, (text_rect.x - 4, text_rect.y - 2))

        screen.blit(text_surf, text_rect)

    def render_status_indicators(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """
        Renderiza indicadores de status permanentes (PAR, BRN, PSN, SLP, FRZ)
        E também o indicador de CONFUSÃO (CON)
        Posicionados MAIS ACIMA de todos
        """
        sprite_height = sprite_rect.height
        base_offset = -sprite_height * 1.1
        status_indicators = []
        font_size = 12

        # Escala da fonte
        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(10, int(12 * total_scale))
        else:
            font_size = max(10, int(12 * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # ===== STATUS NÃO-VOLÁTEIS (PSN, BRN, PAR, SLP, FRZ) =====
        status = self.get_status(pokemon)
        if status and status.type != StatusType.NONE:
            status_text = status.display_name
            color = status.color
            text_surf = font.render(status_text, True, color)
            text_rect = text_surf.get_rect()
            text_rect.centerx = sprite_rect.centerx
            text_rect.bottom = sprite_rect.top + base_offset
            status_indicators.append((text_surf, text_rect))

        # ===== CONFUSÃO (CON) - POSICIONADO À ESQUERDA DO STATUS PRINCIPAL =====
        if self.is_confused(pokemon):
            confusion_text = "CON"
            confusion_color = (248, 88, 136)  # Rosa
            text_surf = font.render(confusion_text, True, confusion_color)
            text_rect = text_surf.get_rect()

            # Posiciona à esquerda do status principal (se houver)
            if status_indicators:
                # Ao lado esquerdo do status principal
                text_rect.right = sprite_rect.centerx - 15
            else:
                # Centralizado se não houver status principal
                text_rect.centerx = sprite_rect.centerx - 20

            text_rect.bottom = sprite_rect.top + base_offset
            status_indicators.append((text_surf, text_rect))

        # ===== RENDERIZA TODOS OS INDICADORES COM FUNDO =====
        for text_surf, text_rect in status_indicators:
            # Fundo semi-transparente
            bg_width = text_surf.get_width() + 8
            bg_height = text_surf.get_height() + 4
            bg_surf = pygame.Surface((bg_width, bg_height))
            bg_surf.set_alpha(180)
            bg_surf.fill((0, 0, 0))
            screen.blit(bg_surf, (text_rect.x - 4, text_rect.y - 2))
            screen.blit(text_surf, text_rect)

    def clear_all(self):
        """Limpa todos os efeitos"""
        self.status_effects.clear()
        self.confusion_effects.clear()
        self.stat_modifiers.clear()
        self.stat_stages.clear()
        self.status_texts.clear()

    def clear_all_effects_for_pokemon(self, pokemon):
        """
        Remove TODOS os efeitos (status, confusão, modificadores de stat) de um Pokémon.
        Usado quando o Pokémon é derrotado.
        """
        if not pokemon:
            return

        pokemon_id = id(pokemon)

        print(f"[EFFECT_MANAGER] Limpando todos os efeitos de {pokemon.name}...")

        # Remove status não-volátil (veneno, queimadura, paralisia, sono, congelamento)
        if pokemon_id in self.status_effects:
            status = self.status_effects[pokemon_id]
            # Remove o status (isso vai chamar status.remove e atualizar animação)
            status.remove(pokemon, self)
            del self.status_effects[pokemon_id]
            print(f"  └─ Status {status.name} removido")

        # Remove confusão
        if pokemon_id in self.confusion_effects:
            effect = self.confusion_effects[pokemon_id]
            effect.remove(pokemon, self)
            del self.confusion_effects[pokemon_id]
            print(f"  └─ Confusão removida")

        # Remove modificadores de stat
        if pokemon_id in self.stat_modifiers:
            del self.stat_modifiers[pokemon_id]
            print(f"  └─ Modificadores de stat removidos")

        # Remove estágios de stat
        if pokemon_id in self.stat_stages:
            del self.stat_stages[pokemon_id]
            print(f"  └─ Estágios de stat removidos")

        # Força atualização da animação para estado normal
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()

        print(f"[EFFECT_MANAGER] Todos os efeitos de {pokemon.name} foram limpos!")