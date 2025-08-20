#!/usr/bin/env python3
#%% -*- coding: utf-8 -*-
"""
Grotrian-JIP-NEW.py
Refactored (with the help of copilot) script to build Grotrian diagrams from SRPM SQL DB.

Usage example:
    JIP: Show in interactive window (backend must support it; Qt):
    python Grotrian-JIP-NEW.py --database AtomicModelsCCA --Z 12 --ion 0 --levs 1-25 --out mgI_grotrian.png
    JIP: Save figure (without graphic window)
    python Grotrian-JIP-NEW.py --database AtomicModelsCCA --Z 12 --ion 0 --levs 1-25 --backend Qt5Agg --show
    

Author: Juan I. Peralta (Juani). Starting from the 'jaymz_ubuntu' user idea
Date: 2025-08-19
"""
import argparse
from fractions import Fraction
import warnings
import os
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Import your JIP helpers (assumed to be in PYTHONPATH)
from JIP import SQL_table, SQL_where

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


def read_table_from_file(path, usecols=None):
    """Read whitespace-separated table with pandas, return DataFrame.
    We try to load as strings first and then cast necessary cols where possible.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    # read flexibly; allow comments '#' too
    df = pd.read_csv(path, sep=r'\s+', comment='#', engine='python', dtype=str)
    if usecols:
        # keep only requested columns if present
        cols = [c for c in usecols if c in df.columns]
        df = df.loc[:, cols]
    return df


def fetch_levels_tables(database, atom, ion, levs,
                        file_level=None, file_sublevel=None):
    """Return Levels and LevelsSublevels DataFrames filtered for given levs.
    Si se pasan file_level y file_sublevel, se leen desde archivos locales.
    """
    levs_str = ','.join([str(l) for l in levs])

    if file_level and file_sublevel:
        # --- lectura desde archivos locales ---
        Levels_SQL = pd.read_csv(file_level, sep=r'\s+', comment='#', engine='python', dtype=str)
        LevelsSub_SQL = pd.read_csv(file_sublevel, sep=r'\s+', comment='#', engine='python', dtype=str)

        # Filtrar columnas relevantes si existen
        Levels_SQL = Levels_SQL.loc[:, [c for c in ['LevelNumber','FullConfig','ElectronConfig'] if c in Levels_SQL.columns]]
        LevelsSub_SQL = LevelsSub_SQL.loc[:, [c for c in ['LevelNumber','SublevelNumber','2J','ExcitationWaven'] if c in LevelsSub_SQL.columns]]

        # Convertir a numéricos donde aplique
        for col in ['LevelNumber','SublevelNumber','2J','ExcitationWaven']:
            if col in LevelsSub_SQL.columns:
                LevelsSub_SQL[col] = pd.to_numeric(LevelsSub_SQL[col], errors='coerce')
        if 'LevelNumber' in Levels_SQL.columns:
            Levels_SQL['LevelNumber'] = pd.to_numeric(Levels_SQL['LevelNumber'], errors='coerce')

        # Filtrar por levs
        Levels_SQL = Levels_SQL[Levels_SQL['LevelNumber'].isin(levs)]
        LevelsSub_SQL = LevelsSub_SQL[LevelsSub_SQL['LevelNumber'].isin(levs)]

        return Levels_SQL.reset_index(drop=True), LevelsSub_SQL.reset_index(drop=True)

    else:
        # --- lectura desde SQL (original) ---
        Levels_SQL = SQL_table('ModelAtomicIonLevel',
                               SQL_where(atom=atom, ion=ion) + f" AND LevelNumber IN ({levs_str})",
                               database=database).loc[:, ['LevelNumber','FullConfig','ElectronConfig']]
        LevelsSub_SQL = SQL_table('ModelAtomicIonLevelSublevel',
                                  SQL_where(atom=atom, ion=ion) + f" AND LevelNumber IN ({levs_str})",
                                  database=database).loc[:, ['LevelNumber','SublevelNumber','2J','ExcitationWaven']]
        return Levels_SQL, LevelsSub_SQL


def fetch_transitions(database, atom, ion, levs_str,
                      file_linefine=None):
    """Fetch transitions as list of rows.
    Si se pasa file_linefine, se lee desde archivo local.
    """
    if file_linefine:
        DB_trans = pd.read_csv(file_linefine, sep=r'\s+', comment='#', engine='python', dtype=str)
        DB_trans = DB_trans.loc[:, [c for c in ['LowerLevel','LowerSublevel','UpperLevel','UpperSublevel'] if c in DB_trans.columns]]
        for col in DB_trans.columns:
            DB_trans[col] = pd.to_numeric(DB_trans[col], errors='coerce')
        return DB_trans.values.tolist()
    else:
        DB_trans = SQL_table('ModelAtomicIonLineFine',
                             SQL_where(atom=atom, ion=ion) + f'AND UpperLevel IN ({levs_str})',
                             database=database).loc[:, ['LowerLevel','LowerSublevel','UpperLevel','UpperSublevel']]
        return DB_trans.values.tolist()


def normalize_fullconfig(fullconfig):
    """Apply the small Mg I specific normalization used originally.
    Keep this as a function for clarity and future edits.
    """
    # guard against NaN
    if not isinstance(fullconfig, str):
        return fullconfig

    # Problems with the notation from the input levels for Mg I (usually NIST)
    if fullconfig in ('2p6.3s2-1S', '3s2-1S'):
        return '3s-1S'
    if fullconfig == '3p2-3P':
        return '3p-3P'
    if fullconfig == '3p2-1S':
        return '3p-1S'
    return fullconfig


def build_levels_list(Levels_SQL, LevelsSub_SQL):
    """Produce a list of dicts (levels) with consistent fields and a mapping for positions."""
    # Index Levels_SQL by LevelNumber for faster lookup
    levels_sql_indexed = Levels_SQL.set_index('LevelNumber')
    levels = []

    # --- ITERATE USING iterrows() to access columns by name safely ---
    for idx, row in LevelsSub_SQL.iterrows():
        try:
            LevelNumber = int(row['LevelNumber'])
            SublevelNumber = int(row['SublevelNumber'])
            J2 = row['2J']                      # now safe: dictionary-like access
            E_waven = row['ExcitationWaven']
        except KeyError as e:
            # If a column name is different, warn and continue
            warnings.warn(f"Missing expected column in LevelsSub_SQL: {e}; row index {idx}")
            continue

        # energy in 1e4 cm^-1 (as original)
        try:
            E = float(E_waven) / 1e4
        except Exception:
            warnings.warn(f"Bad ExcitationWaven value for Level {LevelNumber}, Sublevel {SublevelNumber}: {E_waven}")
            continue

        # attempt to get FullConfig; handle missing gracefully
        try:
            fullconfig = levels_sql_indexed.loc[LevelNumber, 'FullConfig']
        except KeyError:
            # fallback: use ElectronConfig if present
            try:
                fullconfig = levels_sql_indexed.loc[LevelNumber, 'ElectronConfig']
            except Exception:
                warnings.warn(f"LevelNumber {LevelNumber} not found in Levels_SQL; skipping")
                continue

        fullconfig = normalize_fullconfig(fullconfig)

        # parsing logic (keeps original behavior)
        J_frac = Fraction(int(J2), 2)

        # Try to split 'FullConfig' by '-' into n and term
        if isinstance(fullconfig, str) and '-' in fullconfig:
            left, right = fullconfig.split('-', 1)
            if len(right) > 0:
                if '.' in left:
                    left = left.split('.')[1]
                n = left[0:-1] if len(left) > 1 else left
                ang = right[0:2]
                label = f"{str(n)}^{ang}_{str(J_frac)}"
            else:
                # superlevel handling: use ElectronConfig (similar to original)
                try:
                    electronconfig = levels_sql_indexed.loc[LevelNumber, 'ElectronConfig']
                    electronconfig = electronconfig.split(',')[-1].split('.')[1]
                    ang = '*'+electronconfig[-1].upper()
                    n = electronconfig[0:len(electronconfig)-1]
                    label = f"{str(n)}^{ang}_{str(J_frac)}"
                except Exception:
                    label = f"{LevelNumber}-{SublevelNumber}_{str(J_frac)}"
        else:
            label = f"{LevelNumber}-{SublevelNumber}_{str(J_frac)}"

        levels.append({
            'LevelNumber': LevelNumber,
            'SublevelNumber': SublevelNumber,
            'energy': E,
            'label': label,
            'J2': J2
        })

    # Rest of function: same as before (derived columns, xstart, pos_map)
    angularletters = {'S': 0, 'P': 1, 'D': 2, 'F': 3, 'G': 4, 'H': 5, 'I': 6, 'K': 7}
    trip_sing_sep = 8
    superl_sep = trip_sing_sep + 8
    terms_sep = 0

    for idx, lv in enumerate(levels):
        st = lv['label']
        try:
            left, rest = st.split('^', 1)
            term_part, jpart = rest.split('_', 1)
        except ValueError:
            left = st.split('^')[0]
            term_part = st.split('_')[0] if '_' in st else ''
            jpart = st.split('_')[-1]
        try:
            lv['n'] = int(left)
        except Exception:
            try:
                lv['n'] = int(left.strip())
            except Exception:
                lv['n'] = None
        try:
            lv['j'] = Fraction(str(jpart))
        except Exception:
            try:
                lv['j'] = Fraction(float(jpart))
            except Exception:
                lv['j'] = jpart
        try:
            mult_char = term_part[0]
            if mult_char.isdigit():
                lv['mult'] = int(mult_char)
            else:
                lv['mult'] = mult_char
        except Exception:
            lv['mult'] = 1
        try:
            lchar = term_part[1]
            lv['l'] = angularletters.get(lchar, -1)
        except Exception:
            lv['l'] = -1
        if lv['mult'] == 1:
            xstart = trip_sing_sep + lv['l'] + terms_sep
        elif lv['mult'] == 3:
            xstart = lv['l'] + terms_sep
        elif lv['mult'] == '*':
            xstart = superl_sep + lv['l'] + terms_sep
        else:
            xstart = lv['l'] + terms_sep
        lv['xstart'] = xstart

    pos_map = {(lv['LevelNumber'], lv['SublevelNumber']): i for i, lv in enumerate(levels)}
    return levels, pos_map


def plot_levels_and_transitions(levels, transitions, outpath=None, show=True, title=''):
    """Plot the levels and transitions. levels: list of dicts (with xstart, energy, label...)."""
    # plotting parameters (kept as in original)
    levelWidth = 0.1
    plt.rcParams["figure.figsize"] = (4.6 * 1.5, 3.46 * 1.5)
    font_size = 10

    fig, ax = plt.subplots()

    temp = []
    for l in levels:
        # draw horizontal level
        ax.plot([l['xstart'] - levelWidth, l['xstart'] + levelWidth],
                [l['energy'], l['energy']], '-0')

        # determine tag text (keeps original mapping)
        if l['energy'] == 0:
            tag = '$3s^2$'
        elif l['energy'] in [6.8275, 6.136555]:
            tag = ''
        elif np.isclose(l['energy'], 5.781276999999999):
            tag = '$3p^2$'
        else:
            # fallback to label parsing similar to original
            try:
                tag = l['label'].split('^')[0] + l['label'].split('_')[0][-1].lower()
            except Exception:
                tag = l['label']

        L = l['label'].split('_')[0][-1]

        # annotation logic preserved
        if (('show_J' in globals() and globals()['show_J'] == 'no') or l['mult'] == '*'):
            ax.annotate(tag, xy=(l['xstart'] + levelWidth, l['energy']), fontsize=font_size)
        elif l['mult'] == 1 or L == 'S':
            ax.annotate(tag + '$_{'+ str(l['j']) + '}$',
                        xy=(l['xstart'] + levelWidth, l['energy']), fontsize=font_size)
        elif isinstance(l['mult'], int) and l['mult'] > 1:
            temp.append([str(l['j']), l['energy']])
            if l['mult'] == len(temp):  # usually 3
                js = ','.join([x[0] for x in temp])
                aver_ener = sum([x[1] for x in temp]) / len([x[1] for x in temp])
                ax.annotate(tag + '$_{'+js+'}$',
                            xy=(l['xstart'] + levelWidth, aver_ener), fontsize=font_size)
                temp = []

    # Manual annotations from original script
    positions = [lv['xstart'] for lv in levels]
    x1, x2 = min(positions) - 0.2, max(positions) + 0.2
    ax.plot([x1, x2], [6.8275, 6.8275], 'blue')
    ax.annotate('$3p^2$', xy=(x2, 6.8275), fontsize=font_size)

    ax.plot([x1, x2], [6.0825, 6.0825], 'green')
    # original placed label at levels[-2]['energy'] - keep similar behavior with safe access
    try:
        y_for_label = levels[-2]['energy']
    except Exception:
        y_for_label = 6.0825
    ax.annotate('nl=9s-20p', xy=(x2, y_for_label), fontsize=font_size)

    # plot transitions as arrows (cyan dotted)
    for t in transitions:
        try:
            i = t['i']; f = t['f']
            ax.arrow(levels[i]['xstart'], levels[i]['energy'],
                     levels[f]['xstart'] - levels[i]['xstart'],
                     levels[f]['energy'] - levels[i]['energy'],
                     head_width=0, head_length=0, linestyle=':', color='cyan')
        except Exception:
            # skip transitions that map out of bounds
            continue

    # xticks and labels
    font_axis_size = 12
    xticks = ['$^3S$','$^3P$','$^3D$','$^3F$','$^3G$','$^3H$','$^3I$','',
              '$^1S$','$^1P$','$^1D$','$^1F$','$^1G$','$^1H$','$^1I$']
    ax.set_xticks([i for i in range(len(xticks))])
    ax.set_xticklabels(xticks)
    ax.set_xlim(-1, 13)
    ax.set_ylabel('Energy ($10^4 \\ cm^{-1}$)', fontsize=font_axis_size)
    ax.tick_params(axis='x', labelsize=font_axis_size)
    plt.tight_layout()

    if outpath:
        fig.savefig(outpath, dpi=200)
        print(f"[INFO] Figure saved to {outpath}")
    if show and not outpath:
        plt.show()
    plt.close(fig)



def build_transitions_list(DB_transitions, pos_map):
    """From DB_transitions rows produce transitions list mapping to indices in levels list using pos_map.
    DB_transitions rows are [low, sublow, up, subup]
    """
    transitions = []
    for (low, sublow, up, subup) in DB_transitions:
        key_low = (int(low), int(sublow))
        key_up = (int(up), int(subup))
        if key_low in pos_map and key_up in pos_map:
            transitions.append({'i': pos_map[key_low], 'f': pos_map[key_up]})
        else:
            # If not found, try fallback: some DB entries may have missing sublevels or index mismatch
            # We simply warn and skip
            warnings.warn(f"Transition {key_low} -> {key_up} not found in pos_map; skipping")
    return transitions


# -------------------------
# Main
# -------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Build Grotrian diagram from SRPM SQL DB.")
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

    # Fetch tables
    Levels_SQL, LevelsSub_SQL = fetch_levels_tables(args.database, args.Z, args.ion, levs_list,
                                                    file_level=args.file_level,
                                                    file_sublevel=args.file_sublevel)

    # Build levels list and pos_map
    levels, pos_map = build_levels_list(Levels_SQL, LevelsSub_SQL)

    # fetch transitions from DB and build transitions mapping
    levs_str = ','.join([str(l) for l in levs_list])
    DB_trans_raw = fetch_transitions(args.database, args.Z, args.ion, levs_str,
                                    file_linefine=args.file_linefine)
    transitions = build_transitions_list(DB_trans_raw, pos_map)

    # plot
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