# generate_moves_and_learnset_unified.py

import requests
import json
import time
import re
from typing import Dict, List, Optional, Any
from collections import defaultdict

# ==================== CONSTANTES ====================
GENERATION_MAPPING = {
    1: "generation-i",
    2: "generation-ii",
    3: "generation-iii",
    4: "generation-iv",
    5: "generation-v",
    6: "generation-vi",
    7: "generation-vii",
    8: "generation-viii"
}

GENERATION_RANGES = {
    1: (1, 151),  # Kanto
    2: (152, 251),  # Johto
    3: (252, 386),  # Hoenn
    4: (387, 493),  # Sinnoh
    5: (494, 649),  # Unova
    6: (650, 721),  # Kalos
    7: (722, 809),  # Alola
    8: (810, 905)  # Galar
}

VERSION_GROUPS_BY_GEN = {
    1: ["red-blue", "yellow"],
    2: ["gold-silver", "crystal"],
    3: ["ruby-sapphire", "emerald", "firered-leafgreen"],
    4: ["diamond-pearl", "platinum", "heartgold-soulsilver"],
    5: ["black-white", "black-2-white-2"],
    6: ["x-y", "omega-ruby-alpha-sapphire"],
    7: ["sun-moon", "ultra-sun-ultra-moon"],
    8: ["sword-shield"]
}

KNOWN_MOVE_RANGES = {
    1: list(range(1, 166)),
    2: list(range(166, 252)),
    3: list(range(252, 356)),
    4: list(range(356, 468)),
    5: list(range(468, 560)),
    6: list(range(560, 622)),
    7: list(range(622, 743)),
    8: list(range(743, 846))
}


# ==================== FUNÇÕES AUXILIARES ====================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\f', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def render_effect_text(effect_text: str, effect_chance: Optional[int]) -> str:
    if not effect_text:
        return ""
    rendered = effect_text.replace('$effect_chance%', str(effect_chance) if effect_chance is not None else '?')
    return clean_text(rendered)


def extract_id_from_url(url: str) -> Optional[int]:
    if url:
        parts = url.rstrip('/').split('/')
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return None
    return None


def make_request(url: str, retries: int = 3) -> Optional[Dict]:
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                print(f"  Erro após {retries} tentativas: {e}")
                return None
            time.sleep(1)
    return None


# ==================== MOVES DATA ====================
def get_moves_until_gen(max_gen: int) -> List[int]:
    moves_ids = []
    for gen in range(1, max_gen + 1):
        if gen in KNOWN_MOVE_RANGES:
            moves_ids.extend(KNOWN_MOVE_RANGES[gen])
            print(
                f"  Gen {gen}: {len(KNOWN_MOVE_RANGES[gen])} golpes (IDs {KNOWN_MOVE_RANGES[gen][0]}-{KNOWN_MOVE_RANGES[gen][-1]})")

    max_known_id = max([max(r) for r in KNOWN_MOVE_RANGES.values() if r]) if moves_ids else 0
    check_id = max_known_id + 1
    found_new = True

    while found_new and check_id < 1000:
        move_data = make_request(f"https://pokeapi.co/api/v2/move/{check_id}")
        if move_data:
            generation = move_data.get('generation', {})
            generation_name = generation.get('name', '')
            for gen_num, gen_name in GENERATION_MAPPING.items():
                if generation_name == gen_name and gen_num <= max_gen:
                    if check_id not in moves_ids:
                        moves_ids.append(check_id)
                        print(f"  Novo golpe encontrado: ID {check_id}")
                    break
            else:
                for gen_num, gen_name in GENERATION_MAPPING.items():
                    if generation_name == gen_name and gen_num > max_gen:
                        found_new = False
                        break
        else:
            found_new = False
        check_id += 1
        time.sleep(0.05)

    return sorted(moves_ids)


def extract_move_info(move_data: Dict[str, Any], max_gen: int) -> Optional[Dict[str, Any]]:
    generation = move_data.get('generation', {})
    generation_name = generation.get('name', '')

    gen_num = None
    for gen, gen_name in GENERATION_MAPPING.items():
        if generation_name == gen_name:
            gen_num = gen
            break

    if gen_num is None or gen_num > max_gen:
        return None

    move_type = move_data.get('type', {})
    type_name = move_type.get('name', 'unknown') if move_type else 'unknown'
    effect_chance = move_data.get('effect_chance')

    descriptions = move_data.get('flavor_text_entries', [])
    description = ''
    for entry in descriptions:
        language = entry.get('language', {})
        if language.get('name') == 'pt-br':
            description = clean_text(entry.get('flavor_text', ''))
            break
    if not description:
        for entry in descriptions:
            language = entry.get('language', {})
            if language.get('name') == 'en':
                description = clean_text(entry.get('flavor_text', ''))
                break
    if not description and descriptions:
        description = clean_text(descriptions[0].get('flavor_text', ''))

    damage_class = move_data.get('damage_class', {})
    damage_class_name = damage_class.get('name', 'status') if damage_class else 'status'
    pp = move_data.get('pp', 0)
    power = move_data.get('power')
    accuracy = move_data.get('accuracy')

    effect_entries = move_data.get('effect_entries', [])
    raw_effect = ''
    for entry in effect_entries:
        language = entry.get('language', {})
        if language.get('name') == 'en':
            raw_effect = entry.get('effect', '')
            break

    rendered_effect = render_effect_text(raw_effect, effect_chance)
    is_status = damage_class_name == 'status'

    return {
        'id': move_data.get('id'),
        'name': move_data.get('name'),
        'type': type_name,
        'damage_class': damage_class_name,
        'pp': pp,
        'power': power if power else None,
        'accuracy': accuracy if accuracy else None,
        'description': description,
        'effect_chance': effect_chance,
        'effect': rendered_effect,
        'is_status': is_status,
        'generation': generation_name
    }


def get_moves_detailed_until_gen(max_gen: int, move_ids: List[int]) -> List[Dict[str, Any]]:
    moves_data = []
    for i, move_id in enumerate(move_ids, 1):
        print(f"Processando detalhes do golpe #{move_id} ({i}/{len(move_ids)})...")
        move_data = make_request(f"https://pokeapi.co/api/v2/move/{move_id}")
        if move_data:
            move_info = extract_move_info(move_data, max_gen)
            if move_info:
                moves_data.append(move_info)
                if i % 50 == 0 or i == len(move_ids):
                    print(f"  -> Progresso: {i}/{len(move_ids)} - Último: {move_info['name']}")
        time.sleep(0.05)
    return moves_data


def save_moves_to_json(moves_data: List[Dict[str, Any]], max_gen: int) -> None:
    filename = f"pokemon_moves_gen{max_gen}.json"
    moves_data.sort(key=lambda x: x['id'])

    output_data = {
        'generation': f'generation-{max_gen}',
        'total_moves': len(moves_data),
        'moves': {}
    }

    for move in moves_data:
        move_id = str(move['id'])
        output_data['moves'][move_id] = {
            'name': move['name'],
            'type': move['type'],
            'damage_class': move['damage_class'],  # Mantém damage_class
            'pp': move['pp'],
            'power': move['power'],
            'accuracy': move['accuracy'],
            'description': move['description'],
            'effect_chance': move['effect_chance'],
            'effect': move['effect'],
            'is_status': move['is_status']
        }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=3, ensure_ascii=False)
    print(f"\n✓ Arquivo '{filename}' gerado com sucesso!")


# ==================== POKEMON LEARNSET DATA ====================
def get_pokemon_moves_until_gen(pokemon_data: Dict[str, Any], max_gen: int) -> Dict[str, Dict[str, Any]]:
    moves_data = {}
    valid_version_groups = []

    for gen in range(1, max_gen + 1):
        valid_version_groups.extend(VERSION_GROUPS_BY_GEN[gen])

    for move_entry in pokemon_data.get('moves', []):
        move = move_entry.get('move', {})
        move_url = move.get('url', '')
        move_id = extract_id_from_url(move_url)
        move_name = move.get('name', '')

        if move_id:
            version_details = move_entry.get('version_group_details', [])
            methods_info = {
                'level-up': {'level': None, 'versions': []},
                'machine': {'level': None, 'versions': []},
                'egg': {'level': None, 'versions': []},
                'tutor': {'level': None, 'versions': []}
            }

            for detail in version_details:
                version_group = detail.get('version_group', {})
                version_group_name = version_group.get('name', '')

                if version_group_name in valid_version_groups:
                    move_learn_method = detail.get('move_learn_method', {})
                    method_name = move_learn_method.get('name', 'unknown')
                    level_learned = detail.get('level_learned_at', 0)

                    if method_name == 'level-up':
                        method_key = 'level-up'
                    elif method_name == 'machine':
                        method_key = 'machine'
                    elif method_name == 'egg':
                        method_key = 'egg'
                    elif method_name == 'tutor':
                        method_key = 'tutor'
                    else:
                        continue

                    if method_key in methods_info:
                        if method_key == 'level-up':
                            if methods_info[method_key]['level'] is None or level_learned < methods_info[method_key][
                                'level']:
                                methods_info[method_key]['level'] = level_learned
                        if version_group_name not in methods_info[method_key]['versions']:
                            methods_info[method_key]['versions'].append(version_group_name)

            has_method = any(methods_info[method]['versions'] for method in methods_info)

            if has_method:
                organized_methods = {}
                for method, info in methods_info.items():
                    if info['versions']:
                        organized_methods[method] = {
                            'level': info['level'],
                            'versions': sorted(info['versions'])
                        }

                moves_data[str(move_id)] = {
                    'id': move_id,
                    'name': move_name,
                    'learning_methods': organized_methods,
                    'min_level': methods_info['level-up']['level'] if methods_info['level-up']['versions'] else None
                }

    return moves_data


def get_pokemon_ranges_until_gen(max_gen: int) -> List[tuple]:
    ranges = []
    for gen in range(1, max_gen + 1):
        if gen in GENERATION_RANGES:
            ranges.append(GENERATION_RANGES[gen])
    return ranges


def get_all_pokemon_moves_until_gen(max_gen: int) -> Dict[int, Dict[str, Any]]:
    all_pokemon_moves = {}
    pokemon_ranges = get_pokemon_ranges_until_gen(max_gen)
    max_pokemon_id = pokemon_ranges[-1][1]

    for pokemon_id in range(1, max_pokemon_id + 1):
        print(f"\nProcessando Pokémon #{pokemon_id}...")
        pokemon_data = make_request(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
        if not pokemon_data:
            print(f"  -> Falha ao obter dados do Pokémon {pokemon_id}")
            continue

        pokemon_name = pokemon_data.get('name', 'unknown')
        print(f"  -> Nome: {pokemon_name}")

        moves_data = get_pokemon_moves_until_gen(pokemon_data, max_gen)

        if moves_data:
            level_up_moves = []
            tm_hm_moves = []
            egg_moves = []
            tutor_moves = []

            for move_id, move_info in moves_data.items():
                learning_methods = move_info.get('learning_methods', {})

                if 'level-up' in learning_methods:
                    level_info = learning_methods['level-up']
                    level_up_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name'],
                        'level': level_info['level']
                    })

                if 'machine' in learning_methods:
                    tm_hm_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

                if 'egg' in learning_methods:
                    egg_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

                if 'tutor' in learning_methods:
                    tutor_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

            level_up_moves.sort(key=lambda x: (x['level'], x['id']))
            tm_hm_moves.sort(key=lambda x: x['id'])
            egg_moves.sort(key=lambda x: x['id'])
            tutor_moves.sort(key=lambda x: x['id'])

            total_moves = len(level_up_moves) + len(tm_hm_moves) + len(egg_moves) + len(tutor_moves)

            print(f"  -> Total de golpes únicos: {total_moves}")
            print(f"     - Level Up: {len(level_up_moves)}")
            print(f"     - TM/HM: {len(tm_hm_moves)}")
            print(f"     - Egg: {len(egg_moves)}")
            print(f"     - Tutor: {len(tutor_moves)}")

            all_pokemon_moves[pokemon_id] = {
                'id': pokemon_id,
                'name': pokemon_name,
                'types': [t['type']['name'] for t in pokemon_data.get('types', [])],
                'moves': {
                    'level_up': level_up_moves,
                    'tm_hm': tm_hm_moves,
                    'egg': egg_moves,
                    'tutor': tutor_moves
                },
                'total_moves': total_moves
            }
        else:
            print(f"  -> Nenhum golpe encontrado")
            all_pokemon_moves[pokemon_id] = {
                'id': pokemon_id,
                'name': pokemon_name,
                'types': [t['type']['name'] for t in pokemon_data.get('types', [])],
                'moves': {
                    'level_up': [],
                    'tm_hm': [],
                    'egg': [],
                    'tutor': []
                },
                'total_moves': 0
            }

        time.sleep(0.1)

    return all_pokemon_moves


def save_pokemon_learnset(pokemon_moves: Dict[int, Dict[str, Any]], max_gen: int) -> None:
    filename = f"pokemon_gen{max_gen}_learnset.json"

    organized_pokemon = {}
    for pokemon_id in sorted(pokemon_moves.keys()):
        pokemon_data = pokemon_moves[pokemon_id]
        organized_pokemon[str(pokemon_id)] = {
            'name': pokemon_data['name'],
            'types': pokemon_data['types'],
            'moves': {
                'level_up': [
                    {'name': move['name'], 'level': move['level'], 'id': move['id']}
                    for move in pokemon_data['moves']['level_up']
                ],
                'tm_hm': [
                    {'name': move['name'], 'id': move['id']}
                    for move in pokemon_data['moves']['tm_hm']
                ],
                'egg': [
                    {'name': move['name'], 'id': move['id']}
                    for move in pokemon_data['moves']['egg']
                ],
                'tutor': [
                    {'name': move['name'], 'id': move['id']}
                    for move in pokemon_data['moves']['tutor']
                ]
            }
        }

    output_data = {
        "title": f"Pokémon Gen {max_gen} Learnset - Moves Learned by Pokémon",
        "description": f"Complete list of moves that each Pokémon from Generation 1 to {max_gen} can learn",
        "generation": f"Generation {max_gen}",
        "games": [f"Games up to Gen {max_gen}"],
        "total_pokemon": len(pokemon_moves),
        "data_collected": time.strftime('%Y-%m-%d %H:%M:%S'),
        "pokemon": organized_pokemon
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Arquivo '{filename}' gerado com sucesso!")


# ==================== FUNÇÃO PRINCIPAL ====================
def main():
    print("=" * 60)
    print("🐱 POKÉMON MOVES & LEARNSET GENERATOR (UNIFIED)")
    print("=" * 60)

    while True:
        try:
            max_gen = int(input("\n📌 Até qual geração deseja gerar os dados? (1-8): "))
            if 1 <= max_gen <= 8:
                break
            print("Por favor, digite um número entre 1 e 8.")
        except ValueError:
            print("Por favor, digite um número válido.")

    print(f"\nGerando dados para as gerações 1 até {max_gen}...")
    print("Isso pode levar alguns minutos.\n")

    # PASSO 1: Coletar Moves
    print("=" * 60)
    print("📦 PASSO 1: COLETANDO GOLPES")
    print("=" * 60)

    move_ids = get_moves_until_gen(max_gen)
    if not move_ids:
        print("Erro: Nenhum golpe encontrado!")
        return

    print(f"\nEncontrados {len(move_ids)} golpes!")
    moves_data = get_moves_detailed_until_gen(max_gen, move_ids)

    if not moves_data:
        print("Erro: Não foi possível coletar os dados dos golpes!")
        return

    save_moves_to_json(moves_data, max_gen)

    # PASSO 2: Coletar Learnset
    print("\n" + "=" * 60)
    print("🎯 PASSO 2: COLETANDO LEARNSET DOS POKÉMON")
    print("=" * 60)

    pokemon_moves = get_all_pokemon_moves_until_gen(max_gen)

    if not pokemon_moves:
        print("Erro: Nenhum dado de Pokémon coletado!")
        return

    save_pokemon_learnset(pokemon_moves, max_gen)

    print("\n" + "=" * 60)
    print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 60)
    print(f"\nArquivos gerados:")
    print(f"  📄 pokemon_moves_gen{max_gen}.json")
    print(f"  📄 pokemon_gen{max_gen}_learnset.json")


if __name__ == "__main__":
    main()