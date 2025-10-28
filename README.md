# wizvod

Desktop alat za automatsko preuzimanje PDF bankovnih izvoda iz emaila, prepoznavanje broja izvoda i snimanje u folder klijenta kao `<broj_izvoda>.pdf`.

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m wizvod.main
