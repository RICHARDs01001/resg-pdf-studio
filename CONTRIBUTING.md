# Cómo contribuir a RESG PDF Studio

¡Gracias por querer mejorar el proyecto! Estas son las reglas del juego.

## Preparar el entorno

```bash
git clone https://github.com/USUARIO/RESG-PDF-Studio.git
cd RESG-PDF-Studio
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

## Antes de enviar cambios

Ejecuta las dos pruebas y deja los informes en verde:

```bash
python tools/selftest.py       # backend (todas las herramientas)
python tools/gui_smoke.py      # interfaz (offscreen, sin pantallas)
```

Si añades o cambias la interfaz, adjunta también las capturas:

```bash
python tools/gui_smoke.py --capturas
```

## Estilo de código

- **Español** en nombres de cara al usuario (textos, docstrings, mensajes) y en
  los identificadores del dominio (`dividir_pdf`, `marca_agua_pdf`).
- 4 espacios, líneas de hasta **79 columnas**, sin tabuladores.
- Cada función pública del backend lleva su docstring y su prueba en
  `tools/selftest.py`.
- Nada de dependencias nuevas sin comentarlo antes en una issue: el objetivo es
  que el `.exe` no engorde y que las herramientas funcionen sin instalar nada.

## Añadir una herramienta nueva

1. Escribe la función en `resg_pdf/backend/tools.py` con la firma
   `funcion(files, out, opts, progress)`.
2. Añade su entrada en `resg_pdf/ui/registry.py` (título, icono, categoría,
   opciones). La interfaz se construye sola.
3. Si necesita icono nuevo, dibújalo en `tools/generate_icons.py` y ejecuta
   `python tools/generate_icons.py --nuevos`.
4. Añade su prueba en `tools/selftest.py` (y en `tools/gui_smoke.py` si toca la
   interfaz).
5. Actualiza el `README.md` y el `CHANGELOG.md`.

## Flujo con Git

```bash
git checkout -b feature/mi-mejora
git commit -m "feat(dividir): permitir rangos abiertos al final"
git push origin feature/mi-mejora
```

Usamos mensajes tipo [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## Ideas que encajan bien

- Nuevas herramientas que funcionen en local y sin cuentas.
- Mejoras de accesibilidad y de textos en español.
- Optimizaciones del tiempo de arranque y del tamaño del `.exe`.
- Traducciones de la interfaz a otros idiomas.

## Licencia de tus aportaciones

Al enviar un *pull request* aceptas que tu código se publique bajo la misma
licencia del proyecto (**AGPL-3.0**).
