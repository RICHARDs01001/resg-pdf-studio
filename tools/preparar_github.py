# -*- coding: utf-8 -*-
r"""Prepara una carpeta limpia lista para subir a GitHub.

Copia solo el código y los archivos del repositorio (sin `build/`, `dist/`,
registros de compilación ni archivos temporales) a la carpeta que se indique.

Uso:
    python tools/preparar_github.py                    # ..\RESG-PDF-Studio-GitHub
    python tools/preparar_github.py C:\\ruta\\destino    # carpeta concreta
"""
from __future__ import annotations

import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpetas y archivos que nunca se publican
EXCLUIDOS = {
    "build", "dist", "__pycache__", ".git", ".venv", "venv", "env",
    ".pytest_cache", ".idea", ".vscode", ".ruff_cache",
}
EXT_EXCLUIDAS = (".log", ".pyc", ".pyo", ".spec.bak", ".zip", ".exe")


def _ignorar(nombre):
    if nombre in EXCLUIDOS:
        return True
    if nombre.endswith(EXT_EXCLUIDAS):
        return True
    # archivos temporales de desarrollo del proyecto (_arbol.txt, _dbg.py…)
    if nombre.startswith("_") and not nombre.startswith("__"):
        return True
    return False


def preparar(destino):
    if os.path.abspath(destino) == os.path.abspath(RAIZ):
        raise SystemExit("El destino debe ser distinto de la carpeta del proyecto.")
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    shutil.copytree(RAIZ, destino, ignore=shutil.ignore_patterns(*[
        nombre for nombre in EXCLUIDOS]))

    # Segunda pasada: archivos sueltos que no deben publicarse
    quitados = []
    for carpeta, _dirs, archivos in os.walk(destino):
        for archivo in list(archivos):
            if _ignorar(archivo):
                os.remove(os.path.join(carpeta, archivo))
                quitados.append(archivo)
    return destino, quitados


def main():
    destino = (sys.argv[1] if len(sys.argv) > 1
               else os.path.join(os.path.dirname(RAIZ),
                                 "RESG-PDF-Studio-GitHub"))
    destino, quitados = preparar(destino)
    print(f"Carpeta lista para GitHub: {destino}")
    contador = 0
    for _carpeta, _dirs, archivos in os.walk(destino):
        contador += len(archivos)
    print(f"   {contador} archivos copiados")
    if quitados:
        print(f"   {len(quitados)} archivos temporales descartados")
    print("\nSiguientes pasos:")
    print("   cd " + destino)
    print("   git init && git add . && git commit -m \"chore: versión inicial\"")
    print("   git branch -M main")
    print("   git remote add origin https://github.com/USUARIO/RESG-PDF-Studio.git")
    print("   git push -u origin main")


if __name__ == "__main__":
    main()
