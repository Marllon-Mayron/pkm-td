# src/battle/effects/animation_mapper.py
"""
Mapeamento de animações para golpes específicos.
Separa a lógica de animação dos efeitos de batalha.
"""


class AnimationMapper:
    """
    Gerencia qual animação cada golpe deve usar.
    Prioridade:
    1. Mapeamento específico do golpe
    2. Categoria do golpe (physical/special/status)
    3. Fallback padrão
    """

    # ===== MAPEAMENTO ESPECÍFICO DE GOLPES =====
    # Formato: "nome_do_golpe": "animacao_a_usar"
    MOVE_ANIMATIONS = {
        # Golpes físicos com animações específicas
        "scratch": "strike",
        "slash": "strike",
        "cut": "strike",
        "fury-swipes": "strike",

        # Golpes de soco
        "pound": "punch",
        "mega-punch": "punch",
        "dynamic-punch": "punch",
        "fire-punch": "punch",
        "ice-punch": "punch",
        "thunder-punch": "punch",
        "focus-punch": "punch",

        # Golpes especiais (projéteis)
        "water-gun": "shoot",
        "ember": "shoot",
        "thunder-shock": "shoot",
        "ice-beam": "shoot",
        "flamethrower": "shoot",
        "shadow-ball": "shoot",
        "energy-ball": "shoot",
        "aura-sphere": "shoot",

        # Golpes de status
        "sleep-powder": "rotate",
        "stun-spore": "rotate",
        "poison-powder": "rotate",
        "string-shot": "shoot",
        "double-team": "double",

        # Golpes que usam animação padrão de ataque
        "tackle": "attack",
        "body-slam": "attack",
        "take-down": "attack",
        "headbutt": "attack",
        "bite": "attack",
        "crunch": "attack",

        "double-kick": "kick",
        "mega-kick": "kick",
        "jump-kick": "kick",
        "rolling-kick": "kick",
        "low-kick": "kick",

    }

    # ===== FALLBACK POR CATEGORIA =====
    CATEGORY_FALLBACKS = {
        "physical": "attack",  # Padrão para físicos
        "special": "shoot",  # Padrão para especiais
        "status": "shoot",  # Padrão para status
    }

    # ===== ANIMAÇÕES DISPONÍVEIS NO SISTEMA =====
    VALID_ANIMATIONS = {
        "idle", "walk", "run", "attack", "strike", "punch",
        "shoot", "swing", "charge", "sleep", "hurt"
    }

    @classmethod
    def get_animation_for_move(cls, move_name: str, move_category: str = "physical") -> str:
        """
        Retorna a animação apropriada para um golpe.

        Args:
            move_name: Nome do golpe (ex: "scratch", "water-gun")
            move_category: Categoria do golpe ("physical", "special", "status")

        Returns:
            Nome da animação a ser usada
        """
        # Normaliza o nome
        normalized_name = move_name.lower().replace(" ", "-").replace("'", "")

        # 1. Verifica mapeamento específico
        if normalized_name in cls.MOVE_ANIMATIONS:
            animation = cls.MOVE_ANIMATIONS[normalized_name]
            print(f"[ANIM_MAP] {move_name} -> animação específica: {animation}")
            return animation

        # 2. Usa fallback por categoria
        fallback = cls.CATEGORY_FALLBACKS.get(move_category, "attack")
        print(f"[ANIM_MAP] {move_name} ({move_category}) -> fallback: {fallback}")
        return fallback

    @classmethod
    def register_custom_animation(cls, move_name: str, animation_name: str):
        """
        Registra uma animação personalizada para um golpe.
        Útil para adicionar configurações em tempo de execução.
        """
        normalized_name = move_name.lower().replace(" ", "-").replace("'", "")
        cls.MOVE_ANIMATIONS[normalized_name] = animation_name
        print(f"[ANIM_MAP] Registrado: {move_name} -> {animation_name}")

    @classmethod
    def get_all_mappings(cls) -> dict:
        """Retorna todos os mapeamentos atuais"""
        return cls.MOVE_ANIMATIONS.copy()