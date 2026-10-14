# Arquitectura del proyecto

```
RESG-PDF-Studio/
├── main.py                     # punto de entrada (QApplication + MainWindow)
├── build_exe.py                # build del .exe en un comando
├── resg_pdf_studio.spec        # configuración de PyInstaller
├── requirements.txt            # dependencias de ejecución
├── run.bat / build_exe.bat     # atajos para Windows
├── assets/
│   ├── icono.ico|png           # icono de la aplicación
│   ├── logo*.png               # logotipos RESG-tech
│   └── icons/*.png             # un icono por herramienta (33)
├── tools/
│   ├── selftest.py             # pruebas del backend (50 comprobaciones)
│   ├── gui_smoke.py            # pruebas de interfaz + capturas
│   ├── generate_icons.py       # genera los iconos PNG
│   ├── preparar_github.py      # crea la carpeta limpia para publicar
│   └── probe.py                # comprobación rápida de la API de PyMuPDF
└── resg_pdf/
    ├── __init__.py             # versión y rutas de recursos
    ├── backend/
    │   └── tools.py            # TODA la lógica PDF (una función por herramienta)
    └── ui/
        ├── registry.py         # catálogo de herramientas y sus opciones
        ├── main_window.py      # cabecera, inicio y parrilla con buscador
        ├── pages.py            # página de herramienta (archivos + opciones)
        ├── preview.py          # miniaturas de páginas con arrastre
        ├── editor.py           # editor visual de PDF
        ├── widgets.py          # piezas reutilizables (tarjetas, firma, hilos…)
        ├── styles.py           # hoja de estilos QSS y paleta
        └── diagnostico.py      # diálogo «Estado del sistema»
```

## Las tres capas

### 1. Backend (`resg_pdf/backend/tools.py`)

Cada herramienta es una función con la misma firma:

```python
def mi_herramienta(files: list[str], out: str, opts: dict, progress=None) -> str:
    """Devuelve la ruta del resultado."""
```

- `files`: rutas de entrada (uno o varios archivos).
- `out`: archivo o carpeta de salida.
- `opts`: opciones elegidas en la interfaz (más `plan` y `elementos` cuando la
  herramienta usa miniaturas o el editor).
- `progress(pct, mensaje)`: aviso opcional para la barra de progreso.

No hay estado global ni ventanas: se puede llamar desde un script, desde la
interfaz o desde otra aplicación.

### 2. Registro (`resg_pdf/ui/registry.py`)

Declara cada herramienta (id, título, icono, categoría, función, filtro de
archivos, tipo de salida y esquema de opciones) y los extras de la interfaz:

- `previsualiza`: muestra las páginas como miniaturas ordenables.
- `plan`: `'paginas'` (envía el orden exacto con `opts['plan']`) o `'rangos'`
  (traduce la selección visual a un texto de rangos).
- `seleccion_inicial`: `'todas'` o `'ninguna'` (cómo empiezan las casillas).
- `editor`: usa el editor visual.
- `ext_por_opcion`: la extensión de salida depende de una opción.

Añadir una herramienta = una función en el backend + una entrada aquí.

### 3. Interfaz (`resg_pdf/ui/`)

- `main_window.py`: cabecera con buscador y parrilla de tarjetas en flujo.
- `pages.py`: construye la página de una herramienta a partir del registro
  (zona de archivos a la izquierda, opciones y botón a la derecha).
- `preview.py`: `VistaMiniaturas` (lista en modo icono con arrastre interno) y
  `VistaPrevia` (barra de acciones + miniaturas).
- `widgets.py`: tarjetas, zona de soltar, fichas de archivo, campo de imagen,
  papel de firma y los hilos (`Worker` de trabajo y `CargadorMiniaturas`).
- `editor.py`: lienzo con `QGraphicsScene` que convierte las posiciones a
  porcentajes de página al guardar.
- `styles.py`: tema completo en QSS.

## El plan de páginas

La vista de miniaturas y el backend se comunican con una lista sencilla:

```python
opts["plan"] = [
    {"file": "C:/docs/a.pdf", "page": 0, "rot": 0},   # 1ª página del documento final
    {"file": "C:/docs/a.pdf", "page": 2, "rot": 90},  # girada 90°
    {"file": "C:/fotos/foto.png", "page": 0, "rot": 0},  # una imagen como página
]
```

`aplicar_plan()` en el backend construye el PDF definitivo con `PyMuPDF`,
mezclando PDFs e imágenes sin importar cuántas páginas haya.

## Hilos y rendimiento

| Hilo | Para qué |
|---|---|
| `Worker` | Ejecuta la herramienta elegida para que la ventana no se congele. |
| `CargadorMiniaturas` | Dibuja las páginas en segundo plano y guarda cada miniatura en memoria (una sola vez). |

Con documentos de cientos de páginas, la vista dibuja las primeras 200 y ofrece
«+ Mostrar más páginas»; el resto se genera solo cuando se pide.

## Estilos

Todo el aspecto vive en `resg_pdf/ui/styles.py`: colores, tipografías, tarjetas,
botones y diálogos. Se aplica con `app.setStyleSheet(QSS)`, así que un cambio de
tema es cuestión de editar un archivo.
