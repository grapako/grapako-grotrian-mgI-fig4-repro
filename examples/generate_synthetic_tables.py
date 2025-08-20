#!/usr/bin/env python3
"""
Simple synthetic generator for the three tables required by Grotrian script.
Generates tiny .dat files compatible with the parser (whitespace-separated).
"""
import os
import argparse
import numpy as np
import pandas as pd

def gen_tables(outdir):
    os.makedirs(outdir, exist_ok=True)

    # ModelAtomicIonLevel.dat  (LevelNumber, FullConfig, ElectronConfig)
    lvl = [
        (1, '3s2-1S', '2p6.3s2-1S'),
        (2, '3p2-3P', '2p6.3p2-3P'),
        (3, '3p2-1S', '2p6.3p2-1S'),
        (4, '3d2-1D', '2p6.3d2-1D')
    ]
    df_lvl = pd.DataFrame(lvl, columns=['LevelNumber','FullConfig','ElectronConfig'])
    df_lvl.to_csv(os.path.join(outdir,'ModelAtomicIonLevel.dat'), sep=' ', index=False)

    # ModelAtomicIonLevelSublevel.dat (LevelNumber, SublevelNumber, 2J, ExcitationWaven)
    sub = [
        (1,1,0,0.0),
        (2,1,2,21870.464),
        (2,2,4,21911.178),
        (3,1,0,57812.77),
        (4,1,2,68275.0)
    ]
    df_sub = pd.DataFrame(sub, columns=['LevelNumber','SublevelNumber','2J','ExcitationWaven'])
    df_sub.to_csv(os.path.join(outdir,'ModelAtomicIonLevelSublevel.dat'), sep=' ', index=False)

    # ModelAtomicIonLineFine.dat (LowerLevel, LowerSublevel, UpperLevel, UpperSublevel)
    lines = [
        (1,1,2,1),
        (1,1,2,2),
        (1,1,3,1),
        (2,1,4,1)
    ]
    df_lines = pd.DataFrame(lines, columns=['LowerLevel','LowerSublevel','UpperLevel','UpperSublevel'])
    df_lines.to_csv(os.path.join(outdir,'ModelAtomicIonLineFine.dat'), sep=' ', index=False)

    print(f"Synthetic tables written to {outdir}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", default="examples/tables", help="Output directory for synthetic tables")
    args = p.parse_args()
    gen_tables(args.outdir)
