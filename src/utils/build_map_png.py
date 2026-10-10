# scripts/build_map_png.py
"""
Renderiza o mapa de uma fase pra PNG usando o explorador de arquivos.

Uso SEM argumentos:
    python -m scripts.build_map_png
    → abre o explorador pra escolher o JSON
    → abre o explorador pra escolher onde salvar

Uso COM argumentos (pula os diálogos):
    python -m scripts.build_map_png <json> [--out <png>] [--scale N] [--cols N]
"""
import argparse
import sys
from pathlib import Path

# Garante que `src` esteja no PYTHONPATH quando rodado como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402


DEFAULT_SCALE = 3
DEFAULT_OUT_SUBDIR = "res/PokemonSprites/UI/Maps"
GENERAL_MAPS_DIR = "src/data/minigames/general_maps"


# =====================================================================
# DIÁLOGOS NATIVOS (tkinter)
# =====================================================================
def _init_tk():
    """Importa tkinter e esconde a janela root. Retorna (tk, filedialog) ou None."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception as e:
        print(f"[BUILD] tkinter não disponível: {e}")
        return None, None, None

    root = tk.Tk()
    root.withdraw()
    root.update()
    return root, filedialog, messagebox


def _ask_open_json(initial_dir: Path):
    root, fd, mb = _init_tk()
    if fd is None:
        return None

    path = fd.askopenfilename(
        title="Escolha o JSON da fase",
        initialdir=str(initial_dir) if initial_dir.exists() else str(Path.cwd()),
        filetypes=[
            ("Fases (JSON)", "*.json"),
            ("Todos os arquivos", "*.*"),
        ],
    )
    root.destroy()
    if not path:
        return None
    return Path(path)


def _ask_save_png(initial_dir: Path, default_name: str):
    root, fd, mb = _init_tk()
    if fd is None:
        return None

    path = fd.asksaveasfilename(
        title="Salvar PNG como…",
        initialdir=str(initial_dir) if initial_dir.exists() else str(Path.cwd()),
        initialfile=default_name,
        defaultextension=".png",
        filetypes=[
            ("PNG", "*.png"),
            ("Bitmap", "*.bmp"),
            ("JPEG", "*.jpg"),
        ],
    )
    root.destroy()
    if not path:
        return None
    return Path(path)


def _ask_yes_no_dialog(title: str, message: str) -> bool:
    root, fd, mb = _init_tk()
    if mb is None:
        return True
    answer = mb.askyesno(title, message)
    root.destroy()
    return bool(answer)


def _show_info_dialog(title: str, message: str):
    root, fd, mb = _init_tk()
    if mb is None:
        print(f"[{title}] {message}")
        return
    mb.showinfo(title, message)
    root.destroy()


def _show_error_dialog(title: str, message: str):
    root, fd, mb = _init_tk()
    if mb is None:
        print(f"[{title}] {message}")
        return
    mb.showerror(title, message)
    root.destroy()


# =====================================================================
# HELPERS
# =====================================================================
def _resolve_json_arg(raw: str):
    """Resolve um argumento de linha de comando em Path existente."""
    from src.config.paths import PROJECT_ROOT
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        return None
    if not raw.lower().endswith(".json"):
        raw_with_ext = raw + ".json"
    else:
        raw_with_ext = raw

    p = Path(raw_with_ext)
    if p.is_absolute() and p.exists():
        return p

    for rel in (raw_with_ext, raw):
        cand = PROJECT_ROOT / rel
        if cand.exists():
            return cand
        cand = PROJECT_ROOT / GENERAL_MAPS_DIR / rel
        if cand.exists():
            return cand

    base = PROJECT_ROOT / GENERAL_MAPS_DIR
    if base.exists():
        matches = list(base.rglob(Path(raw_with_ext).name))
        if matches:
            return matches[0]
    return None


def _default_general_maps_dir():
    from src.config.paths import PROJECT_ROOT
    return PROJECT_ROOT / GENERAL_MAPS_DIR


def _default_output_dir():
    from src.config.paths import PROJECT_ROOT
    return PROJECT_ROOT / DEFAULT_OUT_SUBDIR


# =====================================================================
# MAIN
# =====================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Renderiza uma fase pra PNG.",
        add_help=True,
    )
    ap.add_argument("json_path", nargs="?", default=None,
                    help="JSON da fase (opcional — abre o explorador se ausente)")
    ap.add_argument("--out", default=None,
                    help="PNG de saída (opcional — abre o explorador se ausente)")
    ap.add_argument("--scale", type=int, default=None,
                    help=f"Fator de escala inteiro (default: {DEFAULT_SCALE})")
    args = ap.parse_args()

    # ---- JSON ----
    if args.json_path:
        json_path = _resolve_json_arg(args.json_path)
        if json_path is None:
            _show_error_dialog(
                "JSON não encontrado",
                f"Não achei o arquivo:\n{args.json_path}"
            )
            sys.exit(1)
    else:
        json_path = _ask_open_json(_default_general_maps_dir())
        if json_path is None:
            print("[BUILD] Nenhum JSON escolhido. Cancelado.")
            sys.exit(0)

    # ---- Saída ----
    if args.out:
        p = Path(args.out)
        if not p.is_absolute():
            from src.config.paths import PROJECT_ROOT
            p = PROJECT_ROOT / args.out
        out_path = p
    else:
        default_name = json_path.stem + ".png"
        out_path = _ask_save_png(_default_output_dir(), default_name)
        if out_path is None:
            print("[BUILD] Nenhum destino escolhido. Cancelado.")
            sys.exit(0)

    # ---- Escala ----
    scale = max(1, args.scale) if args.scale is not None else DEFAULT_SCALE

    # ---- Confirmação ----
    resumo = (
        f"JSON:    {json_path}\n"
        f"Saída:   {out_path}\n"
        f"Escala:  {scale}x\n"
    )
    print("[BUILD] " + resumo.replace("\n", "\n[BUILD] "))

    if not args.json_path or not args.out:
        if not _ask_yes_no_dialog("Confirmar build", resumo + "\nRodar agora?"):
            print("[BUILD] Cancelado.")
            sys.exit(0)

    # ---- Executa ----
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    from src.utils.map_renderer import save_map_png

    ok = save_map_png(
        level_path=json_path,
        output_path=out_path,
        scale=scale,
    )

    if ok:
        _show_info_dialog("Build concluído", f"PNG salvo em:\n{out_path}")
        print(f"[BUILD] Pronto: {out_path}")
    else:
        _show_error_dialog("Falha no build", "Veja o console para detalhes.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()