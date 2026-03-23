import requests
import json
import time
import re
from typing import Dict, List, Optional, Any


def clean_text(text: str) -> str:
    """
    Limpa o texto removendo caracteres especiais e espaços extras

    Args:
        text: Texto original

    Returns:
        Texto limpo
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


def get_move_data(move_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém dados de um golpe específico da PokeAPI

    Args:
        move_id: ID do golpe

    Returns:
        Dicionário com os dados do golpe ou None se erro
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

    Returns:
        Lista de IDs dos golpes
    """
    moves_ids = []

    # Os golpes da primeira geração são os primeiros 165 golpes
    # (baseado na ordenação da PokeAPI)
    for move_id in range(1, 166):
        print(f"Verificando golpe #{move_id}...")

        move_data = get_move_data(move_id)
        if move_data:
            # Verifica se o golpe é da primeira geração
            generation = move_data.get('generation', {})
            generation_name = generation.get('name', '')

            if generation_name == 'generation-i':
                moves_ids.append(move_id)
                print(f"  -> Golpe #{move_id} ({move_data.get('name', '')}) é da Gen 1")

        time.sleep(0.1)  # Pausa para não sobrecarregar a API

    return moves_ids


def extract_move_info(move_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai as informações relevantes do golpe

    Args:
        move_data: Dados completos do golpe da API

    Returns:
        Dicionário com informações formatadas do golpe
    """
    # Extrai o tipo do golpe
    move_type = move_data.get('type', {})
    type_name = move_type.get('name', 'unknown') if move_type else 'unknown'

    # Extrai a descrição em português (ou inglês como fallback)
    descriptions = move_data.get('flavor_text_entries', [])
    description = ''

    # Procura descrição em português
    for entry in descriptions:
        language = entry.get('language', {})
        if language.get('name') == 'pt-br':
            description = clean_text(entry.get('flavor_text', ''))
            break

    # Se não encontrou português, procura inglês
    if not description:
        for entry in descriptions:
            language = entry.get('language', {})
            if language.get('name') == 'en':
                description = clean_text(entry.get('flavor_text', ''))
                break

    # Se ainda não encontrou, usa a primeira disponível
    if not description and descriptions:
        description = clean_text(descriptions[0].get('flavor_text', ''))

    # Extrai informações de dano
    damage_class = move_data.get('damage_class', {})
    damage_class_name = damage_class.get('name', 'status') if damage_class else 'status'

    # Extrai PP, poder, precisão
    pp = move_data.get('pp', 0)
    power = move_data.get('power')
    accuracy = move_data.get('accuracy')

    # Efeitos especiais
    effect_entries = move_data.get('effect_entries', [])
    effect = ''

    for entry in effect_entries:
        language = entry.get('language', {})
        if language.get('name') == 'en':
            effect = clean_text(entry.get('effect', ''))
            break

    # Verifica se é golpe de status
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
        'effect': effect if effect else None,
        'is_status': is_status,
        'generation': 'generation-i'
    }


def get_gen1_moves_detailed(move_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Obtém informações detalhadas de todos os golpes da primeira geração

    Args:
        move_ids: Lista de IDs dos golpes

    Returns:
        Lista com informações detalhadas dos golpes
    """
    moves_data = []

    for i, move_id in enumerate(move_ids, 1):
        print(f"Processando detalhes do golpe #{move_id} ({i}/{len(move_ids)})...")

        move_data = get_move_data(move_id)
        if move_data:
            move_info = extract_move_info(move_data)
            moves_data.append(move_info)
            print(f"  -> {move_info['name']}: {move_info['type']} - {move_info['damage_class']}")

        time.sleep(0.1)  # Pausa para não sobrecarregar a API

    return moves_data


def save_moves_to_json(moves_data: List[Dict[str, Any]], filename: str = "pokemon_moves_gen1.json") -> None:
    """
    Salva os dados dos golpes em um arquivo JSON

    Args:
        moves_data: Lista com dados dos golpes
        filename: Nome do arquivo de saída
    """
    # Organiza por ID
    moves_data.sort(key=lambda x: x['id'])

    # Cria estrutura final
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
            'effect': move['effect'],
            'is_status': move['is_status']
        }

    # Salva arquivo
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=3, ensure_ascii=False)

    print(f"\nArquivo '{filename}' gerado com sucesso!")


def print_statistics(moves_data: List[Dict[str, Any]]) -> None:
    """
    Exibe estatísticas dos golpes coletados

    Args:
        moves_data: Lista com dados dos golpes
    """
    print("\n" + "=" * 50)
    print("ESTATÍSTICAS DOS GOLPES DA PRIMEIRA GERAÇÃO")
    print("=" * 50)

    # Contagem por tipo
    type_count = {}
    # Contagem por classe de dano
    damage_class_count = {'physical': 0, 'special': 0, 'status': 0}

    for move in moves_data:
        # Contagem por tipo
        move_type = move['type']
        type_count[move_type] = type_count.get(move_type, 0) + 1

        # Contagem por classe de dano
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

    # Golpes com maior PP
    print("\nTop 5 golpes com maior PP:")
    pp_sorted = sorted(moves_data, key=lambda x: x['pp'], reverse=True)[:5]
    for move in pp_sorted:
        print(f"  - {move['name']}: {move['pp']} PP")

    # Golpes com maior poder
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

    # Passo 1: Identificar golpes da primeira geração
    print("PASSO 1: Identificando golpes da primeira geração...")
    print("-" * 40)
    move_ids = get_gen1_moves()

    if not move_ids:
        print("Erro: Nenhum golpe da primeira geração encontrado!")
        return

    print(f"\nEncontrados {len(move_ids)} golpes da primeira geração!")

    # Passo 2: Coletar informações detalhadas
    print("\nPASSO 2: Coletando informações detalhadas...")
    print("-" * 40)
    moves_data = get_gen1_moves_detailed(move_ids)

    if not moves_data:
        print("Erro: Não foi possível coletar os dados dos golpes!")
        return

    # Passo 3: Salvar dados em arquivo
    print("\nPASSO 3: Salvando dados...")
    print("-" * 40)
    save_moves_to_json(moves_data)

    # Passo 4: Exibir estatísticas
    print_statistics(moves_data)

    print("\n" + "=" * 50)
    print("PROCESSO CONCLUÍDO COM SUCESSO!")
    print("=" * 50)

    # Exemplo do formato do arquivo
    print("\nExemplo de um golpe com descrição limpa:")
    if moves_data:
        sample_move = moves_data[0]
        print(f"  ID: {sample_move['id']}")
        print(f"  Nome: {sample_move['name']}")
        print(f"  Tipo: {sample_move['type']}")
        print(f"  Descrição: {sample_move['description']}")
        print(f"  Efeito: {sample_move['effect'][:100]}..." if sample_move['effect'] else "  Efeito: Nenhum")


if __name__ == "__main__":
    main()