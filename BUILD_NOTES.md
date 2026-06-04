# Build Notes

## Verze a EXE

- Každá funkční úprava zvyšuje `APP_VERSION` v `porady_app.py`.
- Pro každou novou verzi se vytváří samostatný PyInstaller spec soubor.
- Výsledné EXE se ukládá do složky `dist`.
- `dist`, `build*` a `*.exe` jsou ignorované Gitem, aby se do repozitáře nedostávaly objemné binární výstupy.

## Aktuální build

- Verze: `4.47`
- Spec: `porady_4_47_rolovani_bunek_kalendare.spec`
- EXE: `dist/porady_4_47_rolovani_bunek_kalendare.exe`
