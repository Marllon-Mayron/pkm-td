import requests
import json
import time


def get_pokemon_species(pokemon_id):
    """Obtém dados da espécie do pokémon"""
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar espécie {pokemon_id}: {e}")
        return None


def get_evolution_chain(evolution_chain_url):
    """Obtém a cadeia de evolução"""
    try:
        response = requests.get(evolution_chain_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar cadeia de evolução: {e}")
        return None


def extract_evolution_info(evolution_data):
    """Extrai informações de evolução de forma recursiva"""
    evolutions = {}

    def process_evolution(evolution, current_pokemon_id=None):
        # Processa o pokémon atual
        current_species = evolution.get('species', {})
        current_name = current_species.get('name', '')
        current_id = extract_pokemon_id(current_species.get('url', ''))

        if current_id:
            # Busca os detalhes de evolução para o pokémon atual
            evolves_to = evolution.get('evolves_to', [])

            if evolves_to:
                for next_evolution in evolves_to:
                    # Processa a próxima evolução
                    next_species = next_evolution.get('species', {})
                    next_id = extract_pokemon_id(next_species.get('url', ''))

                    if next_id:
                        # Verifica os detalhes da evolução
                        evolution_details = next_evolution.get('evolution_details', [])
                        evolution_method = "none"
                        min_level = "none"

                        if evolution_details:
                            details = evolution_details[0]
                            min_level = details.get('min_level', 'none')

                            # Se não tiver nível mínimo, verifica outros métodos
                            if min_level is None or min_level == 0:
                                # Verifica se é evolução por item
                                if details.get('item'):
                                    item = details.get('item', {})
                                    evolution_method = item.get('name', 'none')
                                    min_level = evolution_method
                                # Verifica se é por troca
                                elif details.get('trade_species'):
                                    evolution_method = "trade"
                                    min_level = "trade"
                                # Verifica se é por pedra
                                elif details.get('trigger'):
                                    trigger = details.get('trigger', {})
                                    if trigger.get('name') == 'use-item':
                                        evolution_method = "use-item"
                                        min_level = "item"
                                    else:
                                        evolution_method = trigger.get('name', 'none')
                                        min_level = evolution_method
                                else:
                                    evolution_method = "other"
                                    min_level = "other"
                            else:
                                evolution_method = "level_up"

                            evolutions[current_id] = {
                                "lvlMin": min_level,
                                "EvolveTo": next_id,
                                "method": evolution_method
                            }

                        # Processa recursivamente as próximas evoluções
                        process_evolution(next_evolution, next_id)

    # Inicia o processamento
    process_evolution(evolution_data.get('chain', {}))

    return evolutions


def extract_pokemon_id(url):
    """Extrai o ID do pokémon da URL"""
    if url:
        parts = url.rstrip('/').split('/')
        return int(parts[-1]) if parts[-1].isdigit() else None
    return None


def get_all_gen1_pokemon():
    """Obtém todos os pokémons da primeira geração (1-151)"""
    pokemon_list = []

    for pokemon_id in range(1, 152):
        print(f"Processando pokémon #{pokemon_id}...")

        # Obtém a espécie do pokémon
        species_data = get_pokemon_species(pokemon_id)
        if species_data:
            # Obtém a cadeia de evolução
            evolution_chain_url = species_data.get('evolution_chain', {}).get('url')
            if evolution_chain_url:
                evolution_data = get_evolution_chain(evolution_chain_url)
                if evolution_data:
                    pokemon_list.append({
                        'id': pokemon_id,
                        'name': species_data.get('name', ''),
                        'evolution_chain': evolution_data
                    })

        # Pequena pausa para não sobrecarregar a API
        time.sleep(0.1)

    return pokemon_list


def build_evolution_json(evolution_info_by_pokemon):
    """Constrói o JSON final com as evoluções"""
    final_evolution = {}

    for pokemon_data in evolution_info_by_pokemon:
        evolution_info = extract_evolution_info(pokemon_data['evolution_chain'])

        # Adiciona informações de evolução para cada pokémon
        for pokemon_id, evo_data in evolution_info.items():
            final_evolution[str(pokemon_id)] = evo_data

    return final_evolution


def main():
    print("Iniciando coleta de dados da PokeAPI para primeira geração...")
    print("Isso pode levar alguns minutos...")

    # Obtém todos os pokémons da primeira geração
    pokemon_data = get_all_gen1_pokemon()

    # Constrói o JSON de evoluções
    evolution_json = build_evolution_json(pokemon_data)

    # Adiciona pokémons que não evoluem (são finais)
    all_pokemon_ids = set(range(1, 152))
    evolving_pokemon = set(map(int, evolution_json.keys()))
    non_evolving_pokemon = all_pokemon_ids - evolving_pokemon

    for pokemon_id in non_evolving_pokemon:
        evolution_json[str(pokemon_id)] = {
            "lvlMin": "none",
            "EvolveTo": "none",
            "method": "none"
        }

    # Ordena o dicionário por ID
    evolution_json = dict(sorted(evolution_json.items(), key=lambda x: int(x[0])))

    # Salva em um arquivo JSON
    output_file = "pokemon_evolutions_gen1.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evolution_json, f, indent=3, ensure_ascii=False)

    print(f"\nArquivo '{output_file}' gerado com sucesso!")
    print(f"Total de pokémons processados: {len(evolution_json)}")
    print(f"Pokémons com evolução: {len(evolving_pokemon)}")
    print(f"Pokémons sem evolução: {len(non_evolving_pokemon)}")

    # Mostra um exemplo do resultado
    print("\nExemplo das primeiras 5 evoluções:")
    for i, (key, value) in enumerate(evolution_json.items()):
        if i < 5:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()