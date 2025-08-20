import os
from subprocess import run, PIPE

def test_demo_run(tmp_path):
    outdir = tmp_path / "tables"
    outdir.mkdir()
    # create synthetic tables using the generator script
    cmd = ["python", "examples/generate_synthetic_tables.py", "--outdir", str(outdir)]
    r = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    assert r.returncode == 0

    outfig = tmp_path / "mg_demo.png"
    cmd2 = [
        "python", "src/cli.py",
        "--file-level", str(outdir / "ModelAtomicIonLevel.dat"),
        "--file-sublevel", str(outdir / "ModelAtomicIonLevelSublevel.dat"),
        "--file-linefine", str(outdir / "ModelAtomicIonLineFine.dat"),
        "--levs", "1-4",
        "--out", str(outfig)
    ]
    r2 = run(cmd2, stdout=PIPE, stderr=PIPE, text=True)
    # script should exit with 0
    assert r2.returncode == 0
    assert outfig.exists()
