# src/data/trainers/trainer_catalog.py
"""
Treinadores NPC para batalhas de arena.

Cada treinador tem:
  - chapter: 1 (1v1), 2 (2v2), 3 (3v3)
  - difficulty: "easy" | "normal" | "hard"
    Afeta a IA (frequência de itens, threshold de cura) e o pool de sorteio.
"""

TRAINERS = [
    # =========================================================
    # CAPÍTULO 1 (1v1)
    # =========================================================
    # --------------------- EASY ---------------------
    {
        "id": "youngster_joey",
        "name": "Youngster Joey",
        "title": "Rato de Academia",
        "chapter": 1, "difficulty": "easy",
        "intro": "Meu Rattata está no topo da porcentagem!",
        "team": [
            {"pokemon_id": 19, "level": 12,
             "moves": ["tackle", "tail-whip", "quick-attack"]},
        ],
        "reward_money": 150, "reward_xp": 80,
    },
    {
        "id": "bug_catcher_rick",
        "name": "Bug Catcher Rick",
        "title": "Colecionador",
        "chapter": 1, "difficulty": "easy",
        "intro": "Vou mostrar o poder dos insetos!",
        "team": [
            {"pokemon_id": 10, "level": 14,
             "moves": ["tackle", "string-shot", "bug-bite"]},
        ],
        "reward_money": 180, "reward_xp": 100,
    },
    {
        "id": "lass_daisy",
        "name": "Lass Daisy",
        "title": "Florista",
        "chapter": 1, "difficulty": "easy",
        "intro": "Meus pokémons são fofos e fortes!",
        "team": [
            {"pokemon_id": 43, "level": 13,
             "moves": ["absorb", "growth", "poison-powder"]},
        ],
        "reward_money": 170, "reward_xp": 90,
    },
    {
        "id": "picnicker_anna",
        "name": "Picnicker Anna",
        "title": "Amante da Natureza",
        "chapter": 1, "difficulty": "easy",
        "intro": "Vamos fazer um piquenique depois da batalha!",
        "team": [
            {"pokemon_id": 69, "level": 15,
             "moves": ["vine-whip", "growth", "wrap"]},
        ],
        "reward_money": 200, "reward_xp": 110,
    },

    # --------------------- NORMAL ---------------------
    {
        "id": "lass_miranda",
        "name": "Lass Miranda",
        "title": "Treinadora Novata",
        "chapter": 1, "difficulty": "normal",
        "intro": "Vamos ver quem é melhor!",
        "team": [
            {"pokemon_id": 16, "level": 18,
             "moves": ["tackle", "gust", "quick-attack", "sand-attack"]},
        ],
        "reward_money": 250, "reward_xp": 150,
    },
    {
        "id": "camper_liam",
        "name": "Camper Liam",
        "title": "Explorador",
        "chapter": 1, "difficulty": "normal",
        "intro": "Acampei a semana toda treinando!",
        "team": [
            {"pokemon_id": 27, "level": 22,
             "moves": ["scratch", "sand-attack", "poison-sting", "slash"]},
        ],
        "reward_money": 350, "reward_xp": 220,
    },
    {
        "id": "hiker_marcos",
        "name": "Hiker Marcos",
        "title": "Montanhista",
        "chapter": 1, "difficulty": "normal",
        "intro": "As montanhas me ensinaram a lutar!",
        "team": [
            {"pokemon_id": 74, "level": 21,
             "moves": ["tackle", "rock-throw", "defense-curl"]},
        ],
        "reward_money": 320, "reward_xp": 200,
    },
    {
        "id": "fisherman_tony",
        "name": "Fisherman Tony",
        "title": "Pescador",
        "chapter": 1, "difficulty": "normal",
        "intro": "O mar me deu meu parceiro!",
        "team": [
            {"pokemon_id": 60, "level": 23,
             "moves": ["water-gun", "bubble", "hypnosis", "pound"]},
        ],
        "reward_money": 380, "reward_xp": 240,
    },

    # --------------------- HARD ---------------------
    {
        "id": "rival_blue",
        "name": "Rival Blue",
        "title": "O Desafiante",
        "chapter": 1, "difficulty": "hard",
        "intro": "Você nunca vai me vencer!",
        "team": [
            {"pokemon_id": 133, "level": 30,
             "moves": ["tackle", "quick-attack", "bite", "sand-attack"]},
        ],
        "reward_money": 800, "reward_xp": 500,
    },
    {
        "id": "veteran_kaiser",
        "name": "Veteran Kaiser",
        "title": "Veterano de Guerra",
        "chapter": 1, "difficulty": "hard",
        "intro": "Já lutei mil batalhas. Você não é nada.",
        "team": [
            {"pokemon_id": 65, "level": 34,
             "moves": ["confusion", "psybeam", "disable"]},
        ],
        "reward_money": 1000, "reward_xp": 650,
    },
    {
        "id": "blackbelt_master",
        "name": "Blackbelt Master",
        "title": "Mestre do Dojo",
        "chapter": 1, "difficulty": "hard",
        "intro": "Vou te mostrar o verdadeiro poder marcial!",
        "team": [
            {"pokemon_id": 67, "level": 35,
             "moves": ["karate-chop", "seismic-toss", "low-kick"]},
        ],
        "reward_money": 1100, "reward_xp": 720,
    },
    {
        "id": "ace_giovanni",
        "name": "Ace Giovanni",
        "title": "Discípulo do Chefe",
        "chapter": 1, "difficulty": "hard",
        "intro": "Só os fortes sobrevivem aqui.",
        "team": [
            {"pokemon_id": 31, "level": 33,
             "moves": ["body-slam", "double-kick", "poison-sting"]},
        ],
        "reward_money": 950, "reward_xp": 600,
    },

    # =========================================================
    # CAPÍTULO 2 (2v2)
    # =========================================================
    # --------------------- EASY ---------------------
    {
        "id": "twins_flora",
        "name": "Gêmeas Flora",
        "title": "Dupla de Brotos",
        "chapter": 2, "difficulty": "easy",
        "intro": "Vamos brincar de lutar!",
        "team": [
            {"pokemon_id": 43, "level": 18,
             "moves": ["absorb", "growth", "poison-powder"]},
            {"pokemon_id": 69, "level": 18,
             "moves": ["vine-whip", "growth", "wrap"]},
        ],
        "reward_money": 400, "reward_xp": 250,
    },
    {
        "id": "young_duo",
        "name": "Young Duo",
        "title": "Aprendizes",
        "chapter": 2, "difficulty": "easy",
        "intro": "Estamos treinando juntos!",
        "team": [
            {"pokemon_id": 19, "level": 17,
             "moves": ["tackle", "quick-attack", "tail-whip"]},
            {"pokemon_id": 10, "level": 17,
             "moves": ["tackle", "string-shot", "bug-bite"]},
        ],
        "reward_money": 450, "reward_xp": 300,
    },
    {
        "id": "bird_keepers",
        "name": "Irmãos Passarinheiros",
        "title": "Dupla Alada",
        "chapter": 2, "difficulty": "easy",
        "intro": "Nossas aves dominam os céus!",
        "team": [
            {"pokemon_id": 16, "level": 19,
             "moves": ["tackle", "gust", "quick-attack"]},
            {"pokemon_id": 21, "level": 20,
             "moves": ["peck", "growl", "fury-attack"]},
        ],
        "reward_money": 480, "reward_xp": 320,
    },

    # --------------------- NORMAL ---------------------
    {
        "id": "ace_duo",
        "name": "Dupla Ace",
        "title": "Especialistas",
        "chapter": 2, "difficulty": "normal",
        "intro": "Nossa sincronia é perfeita!",
        "team": [
            {"pokemon_id": 25, "level": 25,
             "moves": ["thunder-shock", "quick-attack",
                       "thunder-wave", "iron-tail"]},
            {"pokemon_id": 1,  "level": 26,
             "moves": ["tackle", "vine-whip", "razor-leaf", "poison-powder"]},
        ],
        "reward_money": 600, "reward_xp": 400,
    },
    {
        "id": "fisher_brothers",
        "name": "Irmãos Pescadores",
        "title": "Dupla Aquática",
        "chapter": 2, "difficulty": "normal",
        "intro": "Nossos pokémons do mar vão te afogar!",
        "team": [
            {"pokemon_id": 60, "level": 24,
             "moves": ["water-gun", "bubble", "hypnosis", "pound"]},
            {"pokemon_id": 54, "level": 25,
             "moves": ["water-gun", "confusion", "disable"]},
        ],
        "reward_money": 650, "reward_xp": 450,
    },
    {
        "id": "rock_duo",
        "name": "Pedra & Cia",
        "title": "Dupla Rochosa",
        "chapter": 2, "difficulty": "normal",
        "intro": "Ninguém quebra nossa defesa!",
        "team": [
            {"pokemon_id": 74, "level": 26,
             "moves": ["rock-throw", "tackle", "defense-curl"]},
            {"pokemon_id": 95, "level": 25,
             "moves": ["tackle", "screech", "rock-throw"]},
        ],
        "reward_money": 700, "reward_xp": 480,
    },

    # --------------------- HARD ---------------------
    {
        "id": "gym_leaders_duo",
        "name": "Líderes de Ginásio",
        "title": "Elite Dupla",
        "chapter": 2, "difficulty": "hard",
        "intro": "Você não tem chance contra nós dois!",
        "team": [
            {"pokemon_id": 6, "level": 35,
             "moves": ["ember", "flamethrower", "dragon-rage", "slash"]},
            {"pokemon_id": 9, "level": 35,
             "moves": ["water-gun", "bubble-beam", "bite", "withdraw"]},
        ],
        "reward_money": 1200, "reward_xp": 900,
    },
    {
        "id": "psychic_sisters",
        "name": "Irmãs Psíquicas",
        "title": "Mentes Gêmeas",
        "chapter": 2, "difficulty": "hard",
        "intro": "Nós lemos seus pensamentos...",
        "team": [
            {"pokemon_id": 64, "level": 37,
             "moves": ["confusion", "psybeam", "disable"]},
            {"pokemon_id": 65, "level": 38,
             "moves": ["confusion", "psybeam", "psychic", "recover"]},
        ],
        "reward_money": 1300, "reward_xp": 1000,
    },
    {
        "id": "e4_prep",
        "name": "Desafiantes da Elite",
        "title": "Futuros Elite 4",
        "chapter": 2, "difficulty": "hard",
        "intro": "Nós vamos chegar à Elite 4!",
        "team": [
            {"pokemon_id": 130, "level": 38,
             "moves": ["bite", "dragon-rage", "leer", "thrash"]},
            {"pokemon_id": 59, "level": 37,
             "moves": ["ember", "bite", "take-down"]},
        ],
        "reward_money": 1400, "reward_xp": 1100,
    },

    # =========================================================
    # CAPÍTULO 3 (3v3)
    # =========================================================
    # --------------------- EASY ---------------------
    {
        "id": "picnic_trio",
        "name": "Trio do Piquenique",
        "title": "Amigos de Escola",
        "chapter": 3, "difficulty": "easy",
        "intro": "Trouxemos nossos melhores pokémons!",
        "team": [
            {"pokemon_id": 16, "level": 20,
             "moves": ["tackle", "gust", "quick-attack"]},
            {"pokemon_id": 19, "level": 20,
             "moves": ["tackle", "quick-attack", "tail-whip"]},
            {"pokemon_id": 21, "level": 21,
             "moves": ["peck", "growl", "fury-attack"]},
        ],
        "reward_money": 700, "reward_xp": 500,
    },
    {
        "id": "starter_friends",
        "name": "Amigos dos Iniciais",
        "title": "Trio Iniciante",
        "chapter": 3, "difficulty": "easy",
        "intro": "Vamos mostrar o poder dos iniciais!",
        "team": [
            {"pokemon_id": 1, "level": 22,
             "moves": ["tackle", "vine-whip", "razor-leaf"]},
            {"pokemon_id": 4, "level": 22,
             "moves": ["scratch", "ember"]},
            {"pokemon_id": 7, "level": 22,
             "moves": ["tackle", "water-gun", "tail-whip"]},
        ],
        "reward_money": 800, "reward_xp": 550,
    },

    # --------------------- NORMAL ---------------------
    {
        "id": "balanced_trio",
        "name": "Trio Equilibrado",
        "title": "Especialistas em Tipos",
        "chapter": 3, "difficulty": "normal",
        "intro": "Cobrimos todas as fraquezas!",
        "team": [
            {"pokemon_id": 25, "level": 30,
             "moves": ["thunder-shock", "quick-attack",
                       "thunder-wave", "iron-tail"]},
            {"pokemon_id": 37, "level": 30,
             "moves": ["ember", "quick-attack", "flame-wheel"]},
            {"pokemon_id": 54, "level": 30,
             "moves": ["water-gun", "confusion", "disable", "bubble-beam"]},
        ],
        "reward_money": 1000, "reward_xp": 750,
    },
    {
        "id": "gym_trio",
        "name": "Trio de Ginásio",
        "title": "Aspirantes a Líderes",
        "chapter": 3, "difficulty": "normal",
        "intro": "Nosso treino é intenso!",
        "team": [
            {"pokemon_id": 95, "level": 32,
             "moves": ["tackle", "rock-throw", "screech"]},
            {"pokemon_id": 24, "level": 32,
             "moves": ["poison-sting", "bite", "glare", "screech"]},
            {"pokemon_id": 45, "level": 33,
             "moves": ["absorb", "poison-powder", "sleep-powder", "petal-dance"]},
        ],
        "reward_money": 1100, "reward_xp": 850,
    },

    # --------------------- HARD ---------------------
    {
        "id": "elite_trio",
        "name": "Trio de Elite",
        "title": "A Elite",
        "chapter": 3, "difficulty": "hard",
        "intro": "Prepare-se para a batalha final!",
        "team": [
            {"pokemon_id": 3, "level": 45,
             "moves": ["razor-leaf", "solar-beam", "sludge", "sleep-powder"]},
            {"pokemon_id": 6, "level": 45,
             "moves": ["flamethrower", "dragon-rage", "slash", "fire-blast"]},
            {"pokemon_id": 9, "level": 45,
             "moves": ["hydro-pump", "surf", "ice-beam", "bite"]},
        ],
        "reward_money": 2500, "reward_xp": 1800,
    },
    {
        "id": "champion_legacy",
        "name": "Legado do Campeão",
        "title": "Herdeiros do Trono",
        "chapter": 3, "difficulty": "hard",
        "intro": "Somos a nova geração de campeões!",
        "team": [
            {"pokemon_id": 149, "level": 48,
             "moves": ["wing-attack", "dragon-rage", "thunderbolt", "hyper-beam"]},
            {"pokemon_id": 143, "level": 48,
             "moves": ["body-slam", "earthquake", "hyper-beam", "rest"]},
            {"pokemon_id": 130, "level": 48,
             "moves": ["hydro-pump", "dragon-rage", "bite", "thrash"]},
        ],
        "reward_money": 3000, "reward_xp": 2200,
    },
    {
        "id": "shadow_elite",
        "name": "Elite Sombria",
        "title": "Mestres das Sombras",
        "chapter": 3, "difficulty": "hard",
        "intro": "Das sombras viemos. Nas sombras vocês cairão.",
        "team": [
            {"pokemon_id": 94, "level": 46,
             "moves": ["lick", "shadow-ball", "hypnosis", "dream-eater"]},
            {"pokemon_id": 65, "level": 47,
             "moves": ["psychic", "psybeam", "recover", "shadow-ball"]},
            {"pokemon_id": 89, "level": 47,
             "moves": ["sludge", "toxic", "body-slam", "disable"]},
        ],
        "reward_money": 3200, "reward_xp": 2400,
    },
]


def list_trainers(chapter=None, difficulty=None):
    out = TRAINERS
    if chapter is not None:
        out = [t for t in out if t.get("chapter") == chapter]
    if difficulty is not None:
        out = [t for t in out if t.get("difficulty") == difficulty]
    return list(out)


def get_trainer(trainer_id):
    for t in TRAINERS:
        if t["id"] == trainer_id:
            return t
    return None


def pool_for(chapter, difficulty):
    """Pool filtrado por capítulo + dificuldade, com fallback."""
    pool = list_trainers(chapter, difficulty)
    if pool:
        return pool
    # Fallback: qualquer treinador do capítulo (raro)
    return list_trainers(chapter)