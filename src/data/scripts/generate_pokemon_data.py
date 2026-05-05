import requests
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EvolutionMethod:
    """Classe para armazenar métodos de evolução"""
    name: str
    description: str


class PokemonCompleteGenerator:
    def __init__(self, max_gen=5, delay_between_requests=0.1):
        """
        Inicializa o gerador para a geração especificada
        """
        self.max_gen = max_gen
        self.delay = delay_between_requests
        self.gen_ranges = {
            1: (1, 151),
            2: (152, 251),
            3: (252, 386),
            4: (387, 493),
            5: (494, 649)
        }

        # Mapeamento de métodos de evolução para descrições amigáveis
        self.evolution_methods = {
            "level-up": EvolutionMethod("level_up", "Subir de nível"),
            "trade": EvolutionMethod("trade", "Trocar com outro jogador"),
            "use-item": EvolutionMethod("use_item", "Usar item"),
            "shed": EvolutionMethod("shed", "Evolução especial (ex: Ninjask)"),
            "spin": EvolutionMethod("spin", "Girar o console"),
            "tower-of-darkness": EvolutionMethod("special", "Torre das Trevas"),
            "tower-of-waters": EvolutionMethod("special", "Torre da Água"),
            "three-critical-hits": EvolutionMethod("special", "3 acertos críticos"),
            "take-damage": EvolutionMethod("special", "Tomar dano"),
            "other": EvolutionMethod("other", "Outro método"),
            "affection": EvolutionMethod("affection", "Carinho (Pokémon Amie/Refresh)"),
            "happiness": EvolutionMethod("happiness", "Felicidade"),
            "beauty": EvolutionMethod("beauty", "Beleza (Pokémon Contests)"),
            "location": EvolutionMethod("location", "Local específico"),
            "time-of-day": EvolutionMethod("time_of_day", "Horário do dia"),
            "gender": EvolutionMethod("gender", "Gênero específico"),
            "move": EvolutionMethod("move", "Saber um movimento específico"),
            "party-species": EvolutionMethod("party", "Ter Pokémon específico no time"),
            "party-type": EvolutionMethod("party", "Ter tipo específico no time"),
            "turn-over": EvolutionMethod("special", "Virar o console"),
            "upside-down": EvolutionMethod("special", "Console de cabeça para baixo")
        }

    def get_pokemon_by_gen(self) -> List[int]:
        """Retorna a lista de IDs dos Pokémon baseado na geração"""
        start_id, end_id = self.gen_ranges[self.max_gen]
        print(f"Configurado para Geração {self.max_gen} (Pokémon #{start_id} até #{end_id})")
        return list(range(start_id, end_id + 1))

    def convert_gender_to_male_ratio(self, api_gender_rate: int) -> float:
        """
        Converte gender_rate da API (-1 a 8) para chance de ser MACHO:
        - -1 → -1 (sem gênero)
        - 0 → 1.0 (100% macho)
        - 4 → 0.5 (50% macho)
        - 7 → 0.125 (12.5% macho - starters)
        - 8 → 0.0 (100% fêmea)
        """
        if api_gender_rate == -1:
            return -1.0
        return 1.0 - (api_gender_rate / 8.0)

    def get_pokemon_data(self, pokemon_id: int) -> Dict[str, Any]:
        """Busca todos os dados do Pokémon na PokéAPI"""
        try:
            # Busca dados principais
            response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
            response.raise_for_status()
            pokemon_data = response.json()

            # Busca dados da espécie
            species_response = requests.get(pokemon_data['species']['url'])
            species_response.raise_for_status()
            species_data = species_response.json()

            # Busca dados da cadeia de evolução
            evolution_chain_url = species_data['evolution_chain']['url']
            evolution_response = requests.get(evolution_chain_url)
            evolution_response.raise_for_status()
            evolution_data = evolution_response.json()

            # Processa EVs
            ev_yield = {
                "hp": 0, "attack": 0, "defense": 0,
                "special-attack": 0, "special-defense": 0, "speed": 0
            }

            for stat in pokemon_data['stats']:
                stat_name = stat['stat']['name']
                stat_value = stat['effort']
                ev_yield[stat_name] = stat_value

            # Processa habilidades
            abilities = [ability['ability']['name'] for ability in pokemon_data['abilities']]

            # Habilidade oculta
            hidden_ability = None
            for ability in pokemon_data['abilities']:
                if ability['is_hidden']:
                    hidden_ability = ability['ability']['name']
                    break

            # ===== PESO E ALTURA =====
            weight_hg = pokemon_data.get('weight', 0)
            weight_kg = weight_hg / 10.0 if weight_hg > 0 else 0.0

            height_dm = pokemon_data.get('height', 0)
            height_m = height_dm / 10.0 if height_dm > 0 else 0.0

            # ===== GÊNERO =====
            api_gender_rate = species_data.get('gender_rate', -1)
            gender_ratio = self.convert_gender_to_male_ratio(api_gender_rate)

            # ===== PROCESSA EVOLUÇÃO COMPLETA =====
            evolution_info = self.process_evolution_data(pokemon_id, evolution_data, species_data)

            pokemon_info = {
                "id": pokemon_data['id'],
                "name": pokemon_data['name'],
                "generation": self.get_pokemon_generation(pokemon_data['id']),
                "is_legendary": species_data['is_legendary'],
                "is_mythical": species_data['is_mythical'],
                "type": [t['type']['name'] for t in pokemon_data['types']],
                "base": {
                    "hp": pokemon_data['stats'][0]['base_stat'],
                    "attack": pokemon_data['stats'][1]['base_stat'],
                    "defense": pokemon_data['stats'][2]['base_stat'],
                    "special-attack": pokemon_data['stats'][3]['base_stat'],
                    "special-defense": pokemon_data['stats'][4]['base_stat'],
                    "speed": pokemon_data['stats'][5]['base_stat']
                },
                "ev": ev_yield,
                "capture_rate": species_data['capture_rate'],
                "base_happiness": species_data['base_happiness'],
                "abilities": abilities,
                "hidden_ability": hidden_ability,
                # ===== NOVOS CAMPOS =====
                "weight_kg": weight_kg,
                "height_m": height_m,
                "gender_ratio": gender_ratio,
                # ===== EVOLUÇÃO COMPLETA =====
                "evolution": evolution_info
            }

            # Mostra informações no console
            if gender_ratio == -1:
                gender_text = "Sem gênero"
            elif gender_ratio == 1.0:
                gender_text = "100% Macho"
            elif gender_ratio == 0.0:
                gender_text = "100% Fêmea"
            else:
                gender_text = f"{gender_ratio * 100:.1f}% Macho / {(1 - gender_ratio) * 100:.1f}% Fêmea"

            evo_text = ""
            if evolution_info.get('evolution_details'):
                evo_text = f" → {evolution_info['evolution_details'][0]['evolves_to_name']}"
            elif evolution_info.get('is_last_evolution'):
                evo_text = " (Final)"

            print(f"   #{pokemon_info['id']:03d} {pokemon_info['name']}{evo_text}: "
                  f"Peso:{weight_kg}kg | Alt:{height_m}m | Gênero:{gender_text}")

            time.sleep(self.delay)
            return pokemon_info

        except requests.RequestException as e:
            print(f"Erro ao buscar Pokémon ID {pokemon_id}: {e}")
            return None

    def get_pokemon_generation(self, pokemon_id: int) -> int:
        """Determina a geração do Pokémon baseado no ID"""
        for gen, (start, end) in self.gen_ranges.items():
            if start <= pokemon_id <= end:
                return gen
        return 5

    def process_evolution_data(self, pokemon_id: int, evolution_data: Dict, species_data: Dict) -> Dict:
        """
        Processa a cadeia de evolução completa incluindo métodos especiais
        """
        chain = evolution_data['chain']

        # Encontra o Pokémon na cadeia
        pokemon_node = self.find_pokemon_in_chain(chain, pokemon_id)

        if not pokemon_node:
            return {
                "evolves_from": None,
                "evolution_details": [],
                "variants": [],
                "family_members": [],
                "evolution_chain_id": evolution_data.get('id'),
                "is_last_evolution": True,
                "evolution_methods_info": "Não evolui"
            }

        # Busca todos os membros da família
        family_members = self.extract_family_with_ids(chain)

        # Encontra de qual Pokémon evolui
        evolves_from = self.find_evolution_source(chain, pokemon_id)

        # Processa detalhes da evolução (para onde evolui)
        evolution_details = self.get_evolution_details(pokemon_node)

        # Processa variantes (múltiplas opções de evolução)
        variants = self.get_evolution_variants(pokemon_node)

        is_last = len(evolution_details) == 0 and len(variants) == 0

        return {
            "evolves_from": evolves_from,
            "evolution_details": evolution_details,
            "variants": variants,
            "family_members": family_members,
            "evolution_chain_id": evolution_data.get('id'),
            "is_last_evolution": is_last,
            "evolution_methods_info": self.get_evolution_methods_description(evolution_details + variants)
        }

    def find_pokemon_in_chain(self, chain: Dict, target_id: int) -> Optional[Dict]:
        """Encontra o nó do Pokémon na cadeia de evolução"""
        current_name = chain['species']['name']
        try:
            response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{current_name}")
            if response.status_code == 200:
                current_data = response.json()
                if current_data['id'] == target_id:
                    return chain
        except:
            pass

        for evolution in chain.get('evolves_to', []):
            result = self.find_pokemon_in_chain(evolution, target_id)
            if result:
                return result

        return None

    def extract_family_with_ids(self, chain: Dict) -> List[Dict]:
        """Extrai todos os membros da família com seus IDs"""
        family = []

        def extract(node):
            name = node['species']['name']
            try:
                response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{name}")
                if response.status_code == 200:
                    data = response.json()
                    family.append({"id": data['id'], "name": name})
                else:
                    family.append({"id": None, "name": name})
            except:
                family.append({"id": None, "name": name})

            for evolution in node.get('evolves_to', []):
                extract(evolution)

        extract(chain)
        return family

    def find_evolution_source(self, chain: Dict, target_id: int) -> Optional[Dict]:
        """Encontra de qual Pokémon este evolui"""

        def search(node):
            for evolution in node.get('evolves_to', []):
                evo_name = evolution['species']['name']
                try:
                    response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{evo_name}")
                    if response.status_code == 200:
                        evo_data = response.json()
                        if evo_data['id'] == target_id:
                            current_name = node['species']['name']
                            current_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{current_name}")
                            if current_response.status_code == 200:
                                current_data = current_response.json()
                                return {
                                    "id": current_data['id'],
                                    "name": current_name
                                }
                except:
                    pass

                result = search(evolution)
                if result:
                    return result
            return None

        return search(chain)

    def get_evolution_details(self, pokemon_node: Dict) -> List[Dict]:
        """Obtém detalhes de para onde o Pokémon evolui"""
        details = []

        for evolution in pokemon_node.get('evolves_to', []):
            evo_name = evolution['species']['name']

            try:
                response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{evo_name}")
                if response.status_code == 200:
                    evo_data = response.json()
                    evo_id = evo_data['id']
                else:
                    evo_id = None
            except:
                evo_id = None

            for evo_detail in evolution.get('evolution_details', [{}]):
                detail = {
                    "evolves_to_id": evo_id,
                    "evolves_to_name": evo_name,
                    "method": self.format_evolution_method(evo_detail)
                }

                if evo_detail.get('min_level'):
                    detail["min_level"] = evo_detail['min_level']
                if evo_detail.get('min_happiness'):
                    detail["min_happiness"] = evo_detail['min_happiness']
                if evo_detail.get('min_beauty'):
                    detail["min_beauty"] = evo_detail['min_beauty']
                if evo_detail.get('item'):
                    detail["item"] = evo_detail['item']['name']
                if evo_detail.get('gender'):
                    detail["gender"] = evo_detail['gender']
                if evo_detail.get('location'):
                    detail["location"] = evo_detail['location']['name']
                if evo_detail.get('known_move'):
                    detail["known_move"] = evo_detail['known_move']['name']
                if evo_detail.get('time_of_day'):
                    detail["time_of_day"] = evo_detail['time_of_day']
                if evo_detail.get('party_species'):
                    detail["party_species"] = evo_detail['party_species']['name']
                if evo_detail.get('party_type'):
                    detail["party_type"] = evo_detail['party_type']['name']
                if evo_detail.get('trade_species'):
                    detail["trade_species"] = evo_detail['trade_species']['name']
                if evo_detail.get('needs_overworld_rain'):
                    detail["needs_rain"] = True
                if evo_detail.get('turn_upside_down'):
                    detail["turn_upside_down"] = True

                details.append(detail)

        return details

    def get_evolution_variants(self, pokemon_node: Dict) -> List[Dict]:
        """Obtém todas as variantes de evolução (múltiplas opções)"""
        variants = []

        if len(pokemon_node.get('evolves_to', [])) > 1:
            for evolution in pokemon_node.get('evolves_to', []):
                evo_name = evolution['species']['name']

                try:
                    response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{evo_name}")
                    if response.status_code == 200:
                        evo_data = response.json()
                        evo_id = evo_data['id']
                    else:
                        evo_id = None
                except:
                    evo_id = None

                for evo_detail in evolution.get('evolution_details', [{}]):
                    variant = {
                        "evolves_to_id": evo_id,
                        "evolves_to_name": evo_name,
                        "method": self.format_evolution_method(evo_detail)
                    }

                    if evo_detail.get('item'):
                        variant["item"] = evo_detail['item']['name']
                    if evo_detail.get('min_happiness'):
                        variant["min_happiness"] = evo_detail['min_happiness']
                    if evo_detail.get('time_of_day'):
                        variant["time_of_day"] = evo_detail['time_of_day']
                    if evo_detail.get('min_level'):
                        variant["min_level"] = evo_detail['min_level']

                    variants.append(variant)

        return variants

    def format_evolution_method(self, evo_detail: Dict) -> str:
        """Formata o método de evolução de forma legível"""
        trigger = evo_detail.get('trigger', {}).get('name', 'unknown')

        method_map = {
            'level-up': 'level_up',
            'trade': 'trade',
            'use-item': 'use_item',
            'shed': 'shed',
            'spin': 'spin',
            'tower-of-darkness': 'special',
            'tower-of-waters': 'special',
            'three-critical-hits': 'special',
            'take-damage': 'special',
            'other': 'other'
        }

        if evo_detail.get('min_happiness'):
            return 'happiness'
        if evo_detail.get('min_beauty'):
            return 'beauty'
        if evo_detail.get('location'):
            return 'location'
        if evo_detail.get('time_of_day'):
            return 'time_of_day'
        if evo_detail.get('gender'):
            return 'gender'
        if evo_detail.get('known_move'):
            return 'move'
        if evo_detail.get('party_species') or evo_detail.get('party_type'):
            return 'party'

        return method_map.get(trigger, trigger)

    def get_evolution_methods_description(self, evolutions: List[Dict]) -> str:
        """Gera descrição amigável dos métodos de evolução"""
        if not evolutions:
            return "Não evolui"

        descriptions = []
        for evo in evolutions:
            method = evo.get('method', 'unknown')

            if method == 'level_up':
                level = evo.get('min_level', '?')
                descriptions.append(f"Nível {level}")
            elif method == 'happiness':
                happiness = evo.get('min_happiness', 220)
                time = evo.get('time_of_day', '')
                desc = f"Felicidade ≥ {happiness}"
                if time:
                    desc += f" ({time})"
                descriptions.append(desc)
            elif method == 'use_item':
                item = evo.get('item', 'item desconhecido')
                descriptions.append(f"Usar {item}")
            elif method == 'trade':
                item = evo.get('item', None)
                if item:
                    descriptions.append(f"Trocar segurando {item}")
                else:
                    descriptions.append("Trocar")
            elif method == 'beauty':
                descriptions.append("Beleza máxima")
            elif method == 'location':
                location = evo.get('location', 'local específico')
                descriptions.append(f"No {location}")
            elif method == 'time_of_day':
                time = evo.get('time_of_day', '')
                descriptions.append(f"{time.capitalize()}")
            elif method == 'move':
                move = evo.get('known_move', 'movimento')
                descriptions.append(f"Saber {move}")
            elif method == 'gender':
                gender = evo.get('gender', 1)
                gender_text = "Macho" if gender == 1 else "Fêmea" if gender == 2 else "Específico"
                descriptions.append(f"Gênero: {gender_text}")
            else:
                descriptions.append("Método especial")

        return " ou ".join(descriptions)

    def generate_pokemon_list(self, output_file: str = "pokemon_completo.json", save_every=50):
        """Gera a lista completa de Pokémon com todas as informações"""
        pokemon_ids = self.get_pokemon_by_gen()
        all_pokemon = []

        print(f"\n🎮 GERANDO POKÉMON DA {self.max_gen}ª GERAÇÃO")
        print("=" * 60)
        print(f"Total de Pokémon: {len(pokemon_ids)}")
        print(f"Delay entre requisições: {self.delay}s")
        print(f"Salvando a cada {save_every} Pokémon\n")

        for i, pokemon_id in enumerate(pokemon_ids, 1):
            print(f"🔄 [{i}/{len(pokemon_ids)}] Processando #{pokemon_id:03d}...", end=" ")

            pokemon_data = self.get_pokemon_data(pokemon_id)

            if pokemon_data:
                all_pokemon.append(pokemon_data)
                print(f"✅ {pokemon_data['name']}")

                if i % save_every == 0:
                    self.save_checkpoint(all_pokemon, f"{output_file}.tmp")
                    print(f"   💾 Checkpoint salvo ({i} Pokémon)")
            else:
                print(f"❌ Falha ao processar")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_pokemon, f, indent=4, ensure_ascii=False)

        import os
        if os.path.exists(f"{output_file}.tmp"):
            os.remove(f"{output_file}.tmp")

        print(f"\n✨ ARQUIVO FINAL GERADO: {output_file}")
        print(f"📦 Total de Pokémon processados: {len(all_pokemon)}")
        self.print_detailed_statistics(all_pokemon)

        return all_pokemon

    def save_checkpoint(self, pokemon_list: List[Dict], filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(pokemon_list, f, indent=4, ensure_ascii=False)

    def print_detailed_statistics(self, pokemon_list: List[Dict]):
        """Exibe estatísticas detalhadas dos dados gerados"""
        total = len(pokemon_list)

        stats = {
            "legendary": 0,
            "mythical": 0,
            "evolves": 0,
            "multiple_variants": 0,
            "evolution_methods": {}
        }

        for pokemon in pokemon_list:
            if pokemon['is_legendary']:
                stats["legendary"] += 1
            if pokemon['is_mythical']:
                stats["mythical"] += 1
            if pokemon['evolution']['evolution_details']:
                stats["evolves"] += 1
            if pokemon['evolution']['variants']:
                stats["multiple_variants"] += 1

            for evo in pokemon['evolution']['evolution_details'] + pokemon['evolution']['variants']:
                method = evo.get('method', 'unknown')
                stats["evolution_methods"][method] = stats["evolution_methods"].get(method, 0) + 1

        # Estatísticas de gênero
        no_gender = sum(1 for p in pokemon_list if p.get('gender_ratio') == -1)
        male_only = sum(1 for p in pokemon_list if p.get('gender_ratio') == 1.0)
        female_only = sum(1 for p in pokemon_list if p.get('gender_ratio') == 0.0)
        mixed = total - no_gender - male_only - female_only

        print("\n📊 ESTATÍSTICAS COMPLETAS:")
        print(f"   🎯 Total de Pokémon: {total}")
        print(f"   ⭐ Lendários: {stats['legendary']}")
        print(f"   ✨ Míticos: {stats['mythical']}")
        print(f"   📈 Pokémon que evoluem: {stats['evolves']}")
        print(f"   🔀 Pokémon com múltiplas variantes: {stats['multiple_variants']}")

        print("\n⚥ GÊNERO (gender_ratio = chance de ser MACHO):")
        print(f"   🚫 Sem gênero (-1): {no_gender}")
        print(f"   ♂️  100% macho (1.0): {male_only}")
        print(f"   ♀️  100% fêmea (0.0): {female_only}")
        print(f"   ⚥ Misto (0.0 < x < 1.0): {mixed}")

        print("\n   🔧 Métodos de evolução encontrados:")
        for method, count in sorted(stats["evolution_methods"].items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                method_name = self.evolution_methods.get(method, EvolutionMethod(method, method)).description
                print(f"      • {method_name}: {count}")


def main():
    """Função principal"""
    print("🎮 GERADOR COMPLETO DE POKÉMON (1ª à 5ª Geração)")
    print("=" * 60)

    try:
        print("\n⚙️  CONFIGURAÇÕES:")
        print("   1ª Geração: Pokémon #001-151")
        print("   2ª Geração: Pokémon #152-251")
        print("   3ª Geração: Pokémon #252-386")
        print("   4ª Geração: Pokémon #387-493")
        print("   5ª Geração: Pokémon #494-649")

        gen = int(input("\n Qual geração você quer processar? (1-5): "))

        if gen < 1 or gen > 5:
            print("❌ Geração inválida! Usando 5ª geração como padrão.")
            gen = 5

        use_delay = input("\n⏱️  Usar delay entre requisições? (s/n): ").lower()
        delay = 0.1 if use_delay == 's' else 0

        generator = PokemonCompleteGenerator(max_gen=gen, delay_between_requests=delay)

        print("\n🎯 OPÇÕES:")
        print("   1 - Processar todos os Pokémon da geração")
        print("   2 - Processar intervalo específico")

        option = input("\nEscolha uma opção (1/2): ")

        if option == '2':
            start_id = int(input("ID inicial: "))
            end_id = int(input("ID final: "))
            pokemon_ids = list(range(start_id, end_id + 1))

            all_pokemon = []
            for i, pokemon_id in enumerate(pokemon_ids, 1):
                print(f"🔄 [{i}/{len(pokemon_ids)}] Processando #{pokemon_id:03d}...", end=" ")
                pokemon_data = generator.get_pokemon_data(pokemon_id)
                if pokemon_data:
                    all_pokemon.append(pokemon_data)
                    print(f"✅ {pokemon_data['name']}")
                else:
                    print(f"❌ Falha")

            output_file = f"pokemon_{start_id}_{end_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_pokemon, f, indent=4, ensure_ascii=False)

            print(f"\n✨ Arquivo salvo: {output_file}")
        else:
            output_file = f"pokemon_gen{gen}_completo.json"
            generator.generate_pokemon_list(output_file)

        print("\n✅ Processo concluído com sucesso!")

    except ValueError as e:
        print(f"❌ Erro: {e}")
    except KeyboardInterrupt:
        print("\n⏹️  Processo interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    main()