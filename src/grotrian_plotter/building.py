# src/grotrian_plotter/building.py
import warnings
from fractions import Fraction


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

