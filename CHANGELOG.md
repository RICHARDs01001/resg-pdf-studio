# Historial de cambios

Todas las versiones relevantes de RESG PDF Studio. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico](https://semver.org/lang/es/).

## [1.1.1] — 2026-10-14

### Corregido
- **Apertura mucho más rápida**: de ~2 300 ms a ~455 ms en el equipo de
  referencia, medido con `tools/medir_arranque.py`.
  - `pypdf` ya no se importa al arrancar: se carga la primera vez que una
    herramienta lo necesita (~714 ms menos).
  - La parrilla de herramientas se monta **después** de que la ventana es
    visible, en lugar de bloquear la apertura (~680 ms menos).
- **Arrastrar las miniaturas con el ratón ya cambia el orden**: la lista estaba
  en modo `Static`, que no permite mover nada. Además, al soltar en la mitad
  derecha de una miniatura ahora se coloca **después** de esa página.
- **Las miniaturas se ven enteras**: `setUniformItemSizes(True)` recortaba las
  páginas con una proporción distinta a la de la primera. Las miniaturas pasan
  de 120×160 a 168×224 px y se ajusta la página completa sin cortes.
- **El PDF completo se ve mucho antes**: cada miniatura hacía su propio
  `pymupdf.open(ruta)`; en un documento de 200 páginas eran 200 aperturas de
  disco. Ahora hay una caché de 12 documentos y se abre **una sola vez por
  archivo**.
- **El editor deja mover los elementos libremente**: el texto entraba en modo
  edición al pulsarlo, así que el ratón no lo arrastraba. Se añade
  `NoTextInteraction`, cursor de movimiento y caché de pintado.

### Añadido
- **Ctrl + rueda** acerca y aleja la página en el editor, y el **botón central**
  del ratón la desplaza (como en cualquier visor de PDF).
- `tools/medir_arranque.py`: mide cuánto tarda cada etapa de la apertura.
- `tools/verificar_arreglos.py`: 13 comprobaciones automáticas de estos arreglos.

### Cambiado
- `tools/gui_smoke.py` fuerza la maquetación de la lista de miniaturas antes de
  probar el arrastre: sin pantalla real no había geometría y daba un falso
  fallo.
- El lote de miniaturas dibujadas de golpe pasa de 200 a 300 páginas.

## [1.1.0] — 2026-08-10

### Añadido
- **Vista de miniaturas con reorganización libre**: al añadir archivos se ven
  las páginas y se arrastran para decidir el orden, con botones para girar,
  duplicar, mover, marcar/desmarcar y quitar páginas.
- **Eliminar páginas** y **Extraer páginas** (nuevas herramientas de organización).
- **Editor visual de PDF**: texto, imágenes, formas, resaltados, líneas y
  enlaces colocados y movidos con el ratón.
- **Firma dibujada a mano**: cuadro para firmar con el ratón que genera un PNG
  transparente y lo estampa en el documento.
- **Resumir PDF**: extracción de ideas clave y palabras clave 100 % local.
- **Traducir PDF**: con el motor local opcional `argostranslate`.
- **Crear formularios rellenables** (campos de texto, casillas, listas y firmas).
- **Buscador de herramientas** en la cabecera y en el inicio (atajo `Ctrl+F`).
- Opción «Guardar junto al archivo original» para no responder al diálogo de
  guardado en cada ejecución.
- Diálogo «Estado del sistema» rediseñado, con enlaces de descarga de los
  motores opcionales.
- Pruebas: `tools/selftest.py` (50 comprobaciones) y `tools/gui_smoke.py`
  (33 comprobaciones de interfaz, con capturas opcionales).

### Cambiado
- **Interfaz rediseñada** por completo: distribución de dos columnas (archivos a
  la izquierda, opciones y botón de acción a la derecha), sin huecos vacíos ni
  bloques de texto plano.
- Las notas de uso ya no ocupan espacio dentro de las pantallas: ahora son
  ayudas emergentes (tooltips) y textos de ejemplo en los campos.
- La parrilla de inicio se reparte en flujo continuo y se adapta al ancho de la
  ventana.
- Los iconos se pueden regenerar en Windows (detección automática de fuentes).

### Corregido
- El campo de imagen admite rutas manuales y previsualiza la miniatura.
- Los hilos de miniaturas se detienen al cerrar la aplicación.

## [1.0.0] — 2026-07-28

### Añadido
- Primera versión con 28 herramientas: unir, dividir, ordenar, rotar,
  comprimir, reparar, OCR, conversiones (PDF ⇄ Word/PowerPoint/Excel/JPG/HTML),
  PDF/A, marca de agua, firmar, números de página, recortar, censurar,
  formularios, proteger, desbloquear y comparar.
- Empaquetado en un único `.exe` con PyInstaller (`build_exe.py`).
- Detección automática de LibreOffice, Tesseract y Ghostscript.
