
import os
import json
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Projeto que será analisado
PROJECT_PATH = "."

# Arquivo JSON de saída
OUTPUT_FILE = "project_architecture.json"

# Extensões de arquivos que serão ignoradas
IGNORED_EXTENSIONS = {
    ".png",
}

# Pastas que não serão acessadas
IGNORED_DIRECTORIES = {
    "res",              # Ignorar todas as pastas chamadas Res

    ".git",
    ".svn",
    ".hg",

    "node_modules",

    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",

    ".idea",
    ".vscode",

    "venv",
    ".venv",
    "env",

    "dist",
    "build",
    "target",
    "coverage",

    ".next",
    ".angular",
}

# Arquivos específicos que serão ignorados
IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    OUTPUT_FILE,
}


# ============================================================
# ARQUIVO
# ============================================================

def map_file(file_path: Path):
    """
    Retorna as informações de um arquivo.
    """

    try:
        stat = file_path.stat()

        return {
            "name": file_path.name,
            "type": "file",
            "extension": file_path.suffix.lower() or None,
            "size_bytes": stat.st_size
        }

    except (PermissionError, OSError):

        return {
            "name": file_path.name,
            "type": "file",
            "extension": file_path.suffix.lower() or None,
            "size_bytes": None
        }


# ============================================================
# DIRETÓRIO
# ============================================================

def map_directory(directory: Path):
    """
    Entra recursivamente em todas as pastas
    e lista todos os arquivos encontrados.
    """

    result = {
        "name": directory.name,
        "type": "directory",
        "children": []
    }

    try:
        items = sorted(
            directory.iterdir(),
            key=lambda item: (
                not item.is_dir(),
                item.name.lower()
            )
        )

    except (PermissionError, OSError):

        result["error"] = "Não foi possível acessar esta pasta"
        return result

    for item in items:

        # ====================================================
        # PASTA
        # ====================================================

        if item.is_dir():

            # Ignorar pasta
            if item.name in IGNORED_DIRECTORIES:
                continue

            result["children"].append(
                map_directory(item)
            )

        # ====================================================
        # ARQUIVO
        # ====================================================

        elif item.is_file():

            # Ignorar arquivo específico
            if item.name in IGNORED_FILES:
                continue

            # Ignorar extensão
            if item.suffix.lower() in IGNORED_EXTENSIONS:
                continue

            result["children"].append(
                map_file(item)
            )

    return result


# ============================================================
# ESTATÍSTICAS
# ============================================================

def calculate_statistics(node):
    """
    Calcula quantidade de pastas, arquivos e tamanho total.
    """

    directories = 0
    files = 0
    total_size = 0

    if node["type"] == "directory":

        directories += 1

        for child in node.get("children", []):

            child_dirs, child_files, child_size = (
                calculate_statistics(child)
            )

            directories += child_dirs
            files += child_files
            total_size += child_size

    elif node["type"] == "file":

        files += 1

        if node.get("size_bytes"):
            total_size += node["size_bytes"]

    return directories, files, total_size


# ============================================================
# GERAR ARQUITETURA
# ============================================================

def generate_architecture(project_path):

    project_path = Path(project_path).resolve()

    if not project_path.exists():
        raise FileNotFoundError(
            f"Projeto não encontrado: {project_path}"
        )

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"O caminho informado não é uma pasta: {project_path}"
        )

    architecture = map_directory(project_path)

    directories, files, total_size = (
        calculate_statistics(architecture)
    )

    return {
        "project": {
            "name": project_path.name,
            "path": str(project_path),
            "generated_at": datetime.now().isoformat()
        },

        "statistics": {
            "directories": directories,
            "files": files,
            "total_items": directories + files,
            "total_size_bytes": total_size
        },

        "configuration": {
            "ignored_extensions": sorted(
                IGNORED_EXTENSIONS
            ),

            "ignored_directories": sorted(
                IGNORED_DIRECTORIES
            )
        },

        "architecture": architecture
    }


# ============================================================
# SALVAR JSON
# ============================================================

def save_json(data, output_file):

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PROJECT ARCHITECTURE MAPPER")
    print("=" * 70)

    project = Path(PROJECT_PATH).resolve()

    print(f"\nProjeto:")
    print(project)

    print("\nMapeando arquivos...")

    try:

        architecture = generate_architecture(
            project
        )

        save_json(
            architecture,
            OUTPUT_FILE
        )

        statistics = architecture["statistics"]

        print("\n" + "=" * 70)
        print("MAPEAMENTO CONCLUÍDO")
        print("=" * 70)

        print(
            f"\nPastas:       {statistics['directories']}"
        )

        print(
            f"Arquivos:     {statistics['files']}"
        )

        print(
            f"Total itens:  {statistics['total_items']}"
        )

        print(
            f"Tamanho:      "
            f"{statistics['total_size_bytes']:,} bytes"
        )

        print(
            f"\nJSON:"
            f"\n{Path(OUTPUT_FILE).resolve()}"
        )

    except Exception as error:

        print("\nERRO:")
        print(error)


if __name__ == "__main__":
    main()
