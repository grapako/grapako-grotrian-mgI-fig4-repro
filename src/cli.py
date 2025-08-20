#!/usr/bin/env python3
#%% -*- coding: utf-8 -*-
"""
cli.py (former "Grotrian-JIP-NEW.py")
Refactored script (with the help of copilot) to build Grotrian diagrams from SRPM SQL DB.
"""
import argparse
import warnings
import matplotlib
from grotrian_plotter.data_loader import fetch_levels_tables, fetch_transitions
from grotrian_plotter.building import build_levels_list, build_transitions_list
from grotrian_plotter.plotting import plot_levels_and_transitions
# -------------------------
# Utilities / core routines
# -------------------------
def set_backend_if_requested(backend):
    if backend:
        try:
            matplotlib.use(backend, force=True)
            print(f"[INFO] matplotlib backend set to {backend}")
        except Exception as e:
            warnings.warn(f"Could not set backend {backend}: {e}")


def parse_levs_arg(levs_arg):
    """Parse '1-25,30,35' or '1-25' or comma-separated list into sorted unique ints."""
    if levs_arg is None:
        return None
    parts = [p.strip() for p in str(levs_arg).split(',')]
    out = []
    for p in parts:
        if '-' in p:
            a, b = p.split('-', 1)
            out.extend(list(range(int(a), int(b) + 1)))
        else:
            out.append(int(p))
    return sorted(set(out))

# -------------------------
# Main
# -------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Build Grotrian diagram from SRPM SQL DB or local files.")
    p.add_argument("--database", default="AtomicModelsCCA", help="SQL database name")
    p.add_argument("--file-level", default=None, help="Ruta a tabla ModelAtomicIonLevel (archivo .dat/.csv).")
    p.add_argument("--file-sublevel", default=None, help="Ruta a tabla ModelAtomicIonLevelSublevel.")
    p.add_argument("--file-linefine", default=None, help="Ruta a tabla ModelAtomicIonLineFine.")
    p.add_argument("--Z", type=int, default=12, help="Atomic number")
    p.add_argument("--ion", type=int, default=0, help="Ionization state")
    p.add_argument("--levs", default="1-25", help="Levels selection, e.g. '1-25,30,35'")
    p.add_argument("--out", default=None, help="Output figure path (if given, saves instead of showing)")
    p.add_argument("--backend", default=None, help="Matplotlib backend to use (optional, e.g. 'Qt5Agg')")
    p.add_argument("--show", action="store_true", help="Show interactive window (if backend allows)")
    args = p.parse_args(argv)

    if args.backend:
        set_backend_if_requested(args.backend)

    levs_list = parse_levs_arg(args.levs)
    if not levs_list:
        raise ValueError("No levels parsed from --levs argument")

    print("[INFO] 1/4: Fetching tables...")
    Levels_SQL, LevelsSub_SQL = fetch_levels_tables(args.database, args.Z, args.ion, levs_list,
                                                    file_level=args.file_level,
                                                    file_sublevel=args.file_sublevel)

    print("[INFO] 2/4: Building levels list...")
    levels, pos_map = build_levels_list(Levels_SQL, LevelsSub_SQL)

    print("[INFO] 3/4: Fetching and building transitions...")
    levs_str = ','.join([str(l) for l in levs_list])
    DB_trans_raw = fetch_transitions(args.database, args.Z, args.ion, levs_str,
                                    file_linefine=args.file_linefine)
    transitions = build_transitions_list(DB_trans_raw, pos_map)

    print("[INFO] 4/4: Plotting diagram...")
    plot_levels_and_transitions(levels, transitions, outpath=args.out, show=args.show, title=f"{args.Z}:{args.ion}")


# %%
if __name__ == "__main__":
    main()

# %% JIP: Just for running in ipython from VSC / Spyder
'''
# Simular la llamada con argumentos (lista de strings, como sys.argv)
args = [
    "--file-level", "ModelAtomicIonLevel.dat",
    "--file-sublevel", "ModelAtomicIonLevelSublevel.dat",
    "--file-linefine", "ModelAtomicIonLineFine.dat",
    "--levs", "1-25",
    # "--out", "mgI_local.png"
    "--backend", "Qt5Agg",
    "--show"
]

main(args)
'''