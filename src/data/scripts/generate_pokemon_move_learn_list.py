import requests
import json
import time
import re
from typing import Dict, List, Optional, Any
from collections import defaultdict


def clean_text(text: str) -> str:
    """Limpa o texto removendo caracteres especiais e espaços extras"""
    if not text:
        return ""

    text = text.replace('\f', ' ')
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def get_pokemon_data(pokemon_id: int) -> Optional[Dict[str, Any]]:
    """Obtém dados de um Pokémon específico da PokeAPI"""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar Pokémon {pokemon_id}: {e}")
        return None


def extract_id_from_url(url: str) -> Optional[int]:
    """Extrai o ID da URL da API"""
    if url:
        parts = url.rstrip('/').split('/')
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return None
    return None


def get_pokemon_moves(pokemon_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extrai todos os golpes que o Pokémon aprende com detalhes
    Consolida informações de diferentes versões para evitar duplicatas
    """
    moves_data = {}

    for move_entry in pokemon_data.get('moves', []):
        move = move_entry.get('move', {})
        move_url = move.get('url', '')
        move_id = extract_id_from_url(move_url)
        move_name = move.get('name', '')

        if move_id:
            version_details = move_entry.get('version_group_details', [])

            # Dicionário para consolidar informações por método de aprendizado
            methods_info = {
                'level-up': {'level': None, 'versions': []},
                'machine': {'level': None, 'versions': []},
                'egg': {'level': None, 'versions': []},
                'tutor': {'level': None, 'versions': []}
            }

            for detail in version_details:
                version_group = detail.get('version_group', {})
                version_group_name = version_group.get('name', '')

                # Filtra apenas versões da primeira geração
                if 'red-blue' in version_group_name or 'yellow' in version_group_name:
                    move_learn_method = detail.get('move_learn_method', {})
                    method_name = move_learn_method.get('name', 'unknown')
                    level_learned = detail.get('level_learned_at', 0)

                    # Mapeia método para chave padronizada
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

                    # Atualiza informações do método
                    if method_key in methods_info:
                        if method_key == 'level-up':
                            if methods_info[method_key]['level'] is None or level_learned < methods_info[method_key][
                                'level']:
                                methods_info[method_key]['level'] = level_learned

                        if version_group_name not in methods_info[method_key]['versions']:
                            methods_info[method_key]['versions'].append(version_group_name)

            # Adiciona o golpe apenas se é aprendido por pelo menos um método
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


def get_all_gen1_pokemon_moves() -> Dict[int, Dict[str, Any]]:
    """Coleta todos os golpes aprendidos por cada Pokémon da primeira geração"""
    all_pokemon_moves = {}

    for pokemon_id in range(1, 152):
        print(f"\nProcessando Pokémon #{pokemon_id}...")

        pokemon_data = get_pokemon_data(pokemon_id)
        if not pokemon_data:
            print(f"  -> Falha ao obter dados do Pokémon {pokemon_id}")
            continue

        pokemon_name = pokemon_data.get('name', 'unknown')
        print(f"  -> Nome: {pokemon_name}")

        # Extrai golpes
        moves_data = get_pokemon_moves(pokemon_data)

        if moves_data:
            # Organiza os golpes por método de aprendizado
            level_up_moves = []
            tm_hm_moves = []
            egg_moves = []
            tutor_moves = []

            for move_id, move_info in moves_data.items():
                learning_methods = move_info.get('learning_methods', {})

                # Level-up moves
                if 'level-up' in learning_methods:
                    level_info = learning_methods['level-up']
                    level_up_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name'],
                        'level': level_info['level']
                    })

                # TM/HM moves
                if 'machine' in learning_methods:
                    tm_hm_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

                # Egg moves
                if 'egg' in learning_methods:
                    egg_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

                # Tutor moves
                if 'tutor' in learning_methods:
                    tutor_moves.append({
                        'id': move_info['id'],
                        'name': move_info['name']
                    })

            # Ordena os golpes
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

        time.sleep(0.2)

    return all_pokemon_moves


def save_pokemon_learnset(pokemon_moves: Dict[int, Dict[str, Any]],
                          filename: str = "pokemon_gen1_learnset.json") -> None:
    """
    Salva o arquivo único com todos os dados de aprendizado dos Pokémon
    """
    # Organiza os dados em ordem crescente por ID
    organized_pokemon = {}

    for pokemon_id in sorted(pokemon_moves.keys()):
        pokemon_data = pokemon_moves[pokemon_id]

        organized_pokemon[str(pokemon_id)] = {
            'name': pokemon_data['name'],
            'types': pokemon_data['types'],
            'moves': {
                'level_up': [
                    {
                        'name': move['name'],
                        'level': move['level'],
                        'id': move['id']
                    }
                    for move in pokemon_data['moves']['level_up']
                ],
                'tm_hm': [
                    {
                        'name': move['name'],
                        'id': move['id']
                    }
                    for move in pokemon_data['moves']['tm_hm']
                ],
                'egg': [
                    {
                        'name': move['name'],
                        'id': move['id']
                    }
                    for move in pokemon_data['moves']['egg']
                ],
                'tutor': [
                    {
                        'name': move['name'],
                        'id': move['id']
                    }
                    for move in pokemon_data['moves']['tutor']
                ]
            }
        }

    # Estrutura final do JSON com título em inglês
    output_data = {
        "title": "Pokémon Gen 1 Learnset - Moves Learned by Pokémon",
        "description": "Complete list of moves that each Pokémon from Generation 1 (Red/Blue/Yellow) can learn, organized by learning method (level-up, TM/HM, egg moves, and tutor moves)",
        "generation": "Generation I",
        "games": ["Red", "Blue", "Yellow"],
        "total_pokemon": len(pokemon_moves),
        "data_collected": time.strftime('%Y-%m-%d %H:%M:%S'),
        "pokemon": organized_pokemon
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Arquivo gerado com sucesso: {filename}")
    print(f"  • Tamanho: {len(pokemon_moves)} Pokémon")
    print(f"  • Local: {filename}")


def print_summary(pokemon_moves: Dict[int, Dict[str, Any]]) -> None:
    """Exibe um resumo dos dados coletados"""
    print("\n" + "=" * 70)
    print("POKÉMON GEN 1 LEARNSET SUMMARY")
    print("=" * 70)

    total_level_up = 0
    total_tm_hm = 0
    total_egg = 0
    total_tutor = 0
    pokemon_with_moves = 0

    for pokemon_data in pokemon_moves.values():
        if pokemon_data['total_moves'] > 0:
            pokemon_with_moves += 1
            total_level_up += len(pokemon_data['moves']['level_up'])
            total_tm_hm += len(pokemon_data['moves']['tm_hm'])
            total_egg += len(pokemon_data['moves']['egg'])
            total_tutor += len(pokemon_data['moves']['tutor'])

    print(f"\n📊 Statistics:")
    print(f"   • Total Pokémon processed: {len(pokemon_moves)}")
    print(f"   • Pokémon that learn moves: {pokemon_with_moves}")
    print(f"   • Total level-up moves: {total_level_up}")
    print(f"   • Total TM/HM moves: {total_tm_hm}")
    print(f"   • Total egg moves: {total_egg}")
    print(f"   • Total tutor moves: {total_tutor}")
    print(f"   • Average moves per Pokémon: {total_level_up / len(pokemon_moves):.1f} (level-up)")

    # Top 5 Pokémon with most moves
    print("\n🏆 Top 5 Pokémon with most level-up moves:")
    top_pokemon = sorted(
        [(pid, data) for pid, data in pokemon_moves.items()],
        key=lambda x: len(x[1]['moves']['level_up']),
        reverse=True
    )[:5]

    for pokemon_id, pokemon_data in top_pokemon:
        level_up_count = len(pokemon_data['moves']['level_up'])
        print(f"   #{pokemon_id:3d} - {pokemon_data['name'].capitalize():15s}: {level_up_count:2d} moves")

    # Example for Pikachu
    print("\n" + "=" * 70)
    print("📖 EXAMPLE - PIKACHU (#25):")
    print("=" * 70)

    if 25 in pokemon_moves:
        pikachu = pokemon_moves[25]
        print(f"\n{pikachu['name'].upper()} - Types: {', '.join(pikachu['types']).capitalize()}")

        print("\n🎯 Level-up moves:")
        for move in pikachu['moves']['level_up']:
            print(f"   Level {move['level']:2d}: {move['name'].capitalize()}")

        print(f"\n💿 TM/HM moves ({len(pikachu['moves']['tm_hm'])}):")
        tm_names = [m['name'].capitalize() for m in pikachu['moves']['tm_hm']]
        print(f"   {', '.join(tm_names)}")

        if pikachu['moves']['egg']:
            print(f"\n🥚 Egg moves:")
            egg_names = [m['name'].capitalize() for m in pikachu['moves']['egg']]
            print(f"   {', '.join(egg_names)}")


def main():
    """Função principal do script"""
    print("=" * 70)
    print("🐱‍👤 POKÉMON GEN 1 LEARNSET COLLECTOR")
    print("=" * 70)
    print("\nThis script collects all moves that each Generation 1 Pokémon can learn")
    print("Including learning methods: level-up, TM/HM, egg moves, and tutor moves")
    print("⏱️  This may take a few minutes...\n")

    # Coleta todos os dados
    pokemon_moves = get_all_gen1_pokemon_moves()

    if not pokemon_moves:
        print("❌ Error: No data collected!")
        return

    # Salva em arquivo único
    print("\n" + "-" * 70)
    print("💾 SAVING FILE...")
    print("-" * 70)

    save_pokemon_learnset(pokemon_moves)

    # Exibe resumo
    print_summary(pokemon_moves)

    print("\n" + "=" * 70)
    print("✅ PROCESS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()