import requests
import json
import time
import re
from typing import Dict, List, Optional, Any


def clean_text(text: str) -> str:
    """
    Limpa o texto removendo caracteres especiais e espaços extras
    """
    if not text:
        return ""

    # Remove caracteres de controle especiais
    text = text.replace('\f', ' ')  # Form feed
    text = text.replace('\n', ' ')  # New line
    text = text.replace('\r', ' ')  # Carriage return
    text = text.replace('\t', ' ')  # Tab

    # Remove espaços múltiplos
    text = re.sub(r'\s+', ' ', text)

    # Remove espaços no início e fim
    text = text.strip()

    return text

def render_effect_text(effect_text: str, effect_chance: Optional[int]) -> str:
    """
    Substitui o placeholder $effect_chance% pelo valor real, se disponível.
    """
    if not effect_text:
        return ""

    if effect_chance is not None:
        # Substitui o placeholder pelo número real, sem o símbolo de % para não duplicar
        rendered_text = effect_text.replace('$effect_chance%', str(effect_chance))
    else:
        # Se não houver chance de efeito, remove o placeholder
        rendered_text = effect_text.replace('$effect_chance%', '?')

    return clean_text(rendered_text)

def get_move_data(move_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém dados de um golpe específico da PokeAPI
    """
    url = f"https://pokeapi.co/api/v2/move/{move_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar golpe {move_id}: {e}")
        return None


def get_gen1_moves() -> List[int]:
    """
    Obtém a lista de IDs dos golpes da primeira geração
    """
    moves_ids = []

    # Os golpes da primeira geração são os primeiros 165 golpes
    for move_id in range(1, 166):
        print(f"Verificando golpe #{move_id}...")

        move_data = get_move_data(move_id)
        if move_data:
            generation = move_data.get('generation', {})
            generation_name = generation.get('name', '')

            if generation_name == 'generation-i':
                moves_ids.append(move_id)
                print(f"  -> Golpe #{move_id} ({move_data.get('name', '')}) é da Gen 1")

        time.sleep(0.1)

    return moves_ids


def extract_move_info(move_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai as informações relevantes do golpe, incluindo effect_chance.
    """
    move_type = move_data.get('type', {})
    type_name = move_type.get('name', 'unknown') if move_type else 'unknown'

    # --- NOVO: Extrai effect_chance ---
    effect_chance = move_data.get('effect_chance')

    # Descrição em português
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

    # Efeitos especiais
    effect_entries = move_data.get('effect_entries', [])
    raw_effect = ''
    for entry in effect_entries:
        language = entry.get('language', {})
        if language.get('name') == 'en':
            raw_effect = entry.get('effect', '')
            break

    # --- NOVO: Cria uma versão renderizada do efeito com o valor real da chance ---
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
        'effect_chance': effect_chance,          # <-- NOVO CAMPO
        'effect_raw': raw_effect,                # <-- NOVO CAMPO (opcional)
        'effect': rendered_effect,               # <-- AGORA É A VERSÃO RENDERIZADA
        'is_status': is_status,
        'generation': 'generation-i'
    }


def get_gen1_moves_detailed(move_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Obtém informações detalhadas de todos os golpes da primeira geração
    """
    moves_data = []

    for i, move_id in enumerate(move_ids, 1):
        print(f"Processando detalhes do golpe #{move_id} ({i}/{len(move_ids)})...")

        move_data = get_move_data(move_id)
        if move_data:
            move_info = extract_move_info(move_data)
            moves_data.append(move_info)
            print(f"  -> {move_info['name']}: {move_info['type']} - {move_info['damage_class']} (Chance: {move_info['effect_chance']})")

        time.sleep(0.1)

    return moves_data


def save_moves_to_json(moves_data: List[Dict[str, Any]], filename: str = "pokemon_moves_gen1.json") -> None:
    """
    Salva os dados dos golpes em um arquivo JSON, incluindo effect_chance.
    """
    moves_data.sort(key=lambda x: x['id'])

    output_data = {
        'generation': 'generation-i',
        'total_moves': len(moves_data),
        'moves': {}
    }

    for move in moves_data:
        move_id = str(move['id'])
        output_data['moves'][move_id] = {
            'name': move['name'],
            'type': move['type'],
            'damage_class': move['damage_class'],
            'pp': move['pp'],
            'power': move['power'],
            'accuracy': move['accuracy'],
            'description': move['description'],
            'effect_chance': move['effect_chance'],  # <-- NOVO CAMPO
            'effect': move['effect'],                # <-- AGORA É A VERSÃO RENDERIZADA
            'is_status': move['is_status']
        }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=3, ensure_ascii=False)

    print(f"\nArquivo '{filename}' gerado com sucesso!")


def print_statistics(moves_data: List[Dict[str, Any]]) -> None:
    """
    Exibe estatísticas dos golpes coletados
    """
    print("\n" + "=" * 50)
    print("ESTATÍSTICAS DOS GOLPES DA PRIMEIRA GERAÇÃO")
    print("=" * 50)

    type_count = {}
    damage_class_count = {'physical': 0, 'special': 0, 'status': 0}

    for move in moves_data:
        move_type = move['type']
        type_count[move_type] = type_count.get(move_type, 0) + 1

        damage_class = move['damage_class']
        if damage_class in damage_class_count:
            damage_class_count[damage_class] += 1

    print(f"\nTotal de golpes: {len(moves_data)}")

    print("\nGolpes por classe de dano:")
    for class_name, count in damage_class_count.items():
        print(f"  - {class_name}: {count} golpes")

    print("\nTop 10 tipos mais comuns:")
    sorted_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)[:10]
    for move_type, count in sorted_types:
        print(f"  - {move_type}: {count} golpes")

    print("\nTop 5 golpes com maior PP:")
    pp_sorted = sorted(moves_data, key=lambda x: x['pp'], reverse=True)[:5]
    for move in pp_sorted:
        print(f"  - {move['name']}: {move['pp']} PP")

    print("\nTop 5 golpes com maior poder:")
    power_moves = [m for m in moves_data if m['power'] is not None]
    if power_moves:
        power_sorted = sorted(power_moves, key=lambda x: x['power'], reverse=True)[:5]
        for move in power_sorted:
            print(f"  - {move['name']}: {move['power']} poder ({move['type']})")


def main():
    """
    Função principal do script
    """
    print("=" * 50)
    print("COLETANDO GOLPES DA PRIMEIRA GERAÇÃO DE POKÉMON")
    print("=" * 50)
    print("\nEste script irá coletar todos os golpes da Gen 1 da PokeAPI")
    print("Isso pode levar alguns minutos...\n")

    print("PASSO 1: Identificando golpes da primeira geração...")
    print("-" * 40)
    move_ids = get_gen1_moves()

    if not move_ids:
        print("Erro: Nenhum golpe da primeira geração encontrado!")
        return

    print(f"\nEncontrados {len(move_ids)} golpes da primeira geração!")

    print("\nPASSO 2: Coletando informações detalhadas...")
    print("-" * 40)
    moves_data = get_gen1_moves_detailed(move_ids)

    if not moves_data:
        print("Erro: Não foi possível coletar os dados dos golpes!")
        return

    print("\nPASSO 3: Salvando dados...")
    print("-" * 40)
    save_moves_to_json(moves_data)

    print_statistics(moves_data)

    print("\n" + "=" * 50)
    print("PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 50)

    print("\nExemplo de um golpe com effect_chance e efeito renderizado:")
    if moves_data:
        # Procura um golpe que tenha effect_chance para exemplificar
        sample_move = next((m for m in moves_data if m['effect_chance'] is not None), moves_data[0])
        print(f"  ID: {sample_move['id']}")
        print(f"  Nome: {sample_move['name']}")
        print(f"  Tipo: {sample_move['type']}")
        print(f"  Chance de Efeito: {sample_move['effect_chance']}%")
        print(f"  Descrição: {sample_move['description']}")
        print(f"  Efeito (Renderizado): {sample_move['effect'][:100]}..." if sample_move['effect'] else "  Efeito: Nenhum")


if __name__ == "__main__":
    main()