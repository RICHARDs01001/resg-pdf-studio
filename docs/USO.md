# Guía de uso

## La pantalla de inicio

Al abrir RESG PDF Studio verás todas las herramientas agrupadas por categoría y
un buscador arriba:

- Escribe en el buscador (o pulsa `Ctrl+F`) para filtrar: por ejemplo `unir`,
  `firmar` o `excel`.
- Pulsa una tarjeta para entrar en la herramienta.
- `Esc` o el botón «‹ Todas las herramientas» te devuelve al inicio.

## Añadir archivos

En cada herramienta hay dos formas de añadir documentos:

1. **Arrastrar y soltar** los archivos desde el Explorador sobre la zona con
   borde discontinuo.
2. Pulsar **«Elegir archivos»** (o **«Añadir archivos»** en las herramientas con
   miniaturas).

No hay límite de cantidad: puedes añadir 1 o 400 archivos, y no hace falta
crear ninguna cuenta.

## Vista de miniaturas y orden de las páginas

Las herramientas de organización (unir, dividir, ordenar, rotar, eliminar y
extraer) —y también «JPG a PDF»— muestran **cada página como una miniatura**:

| Acción | Cómo |
|---|---|
| **Cambiar el orden** | Arrastra la miniatura con el ratón a donde quieras (también con los botones «◀ Mover» y «▶ Mover»). |
| **Girar 90°** | Selecciona una o varias miniaturas y pulsa «↺ Girar izq.» o «↻ Girar der.». |
| **Duplicar** | Selecciona y pulsa «Duplicar»: la copia queda justo después. |
| **Quitar de la lista** | Selecciona y pulsa «Quitar». |
| **Marcar / desmarcar** | Usa la casilla de cada miniatura, o los botones «Marcar todo» / «Desmarcar todo». |
| **Ver todas las páginas** | Con documentos muy largos se dibujan por lotes: pulsa «+ Mostrar más páginas». |

El significado de la casilla depende de la herramienta:

- **Unir, Ordenar, Rotar**: todas las páginas marcadas se incluyen en el orden
  que se ve en pantalla.
- **Eliminar páginas**: se conservan las marcadas (desmarca lo que sobra).
- **Extraer, Dividir**: solo se procesan las páginas marcadas.

## Opciones y ejecución

La columna derecha reúne las opciones de cada herramienta, una ficha
**RESUMEN** con lo que se va a procesar (archivos, páginas y formato de salida)
y el botón de acción. Dos detalles útiles:

- Marca **«Guardar junto al archivo original»** para no responder al diálogo de
  guardado: el resultado se crea en la misma carpeta con el sufijo `_nombre` de
  la herramienta (por ejemplo `informe_unir.pdf`).
- Al terminar aparece un aviso verde con la ruta del resultado y el botón
  «Abrir resultado».

## El editor visual (Editar PDF)

1. Añade el PDF y espera a ver la página.
2. Usa la barra superior para colocar elementos con el ratón: **Texto**,
   **Imagen**, **Rectángulo**, **Elipse**, **Línea**, **Resaltar** y **Enlace**.
3. Arrastra cada elemento a su sitio. Con un elemento seleccionado puedes
   cambiar color, tamaño, fuente y opacidad desde los controles de abajo.
4. El campo «Texto» cambia el contenido del texto seleccionado; el campo
   «Enlace» guarda la dirección del próximo enlace que coloques.
5. «Deshacer» quita el último elemento y «Borrar» elimina lo seleccionado.
6. Pulsa el botón de la derecha para guardar el PDF con los cambios.

## Firmar con el ratón

1. En «Firmar PDF», pulsa **«Dibujar firma»** en el campo «Firma».
2. Firma con el ratón (o con el lápiz de la tableta). «Limpiar» borra y vuelve
   a empezar.
3. «Usar esta firma» la convierte en un PNG con fondo transparente y la deja
   lista para estamparla donde indiques.

## Inteligencia de documento

- **Resumir PDF** funciona en local: extrae las ideas clave y las palabras más
  relevantes. Puede exportar `.md`, `.txt` o un PDF nuevo. Si el documento es un
  escaneo sin texto, primero pásalo por «OCR PDF».
- **Traducir PDF** necesita el motor local opcional:

  ```bash
  pip install argostranslate
  argospm update
  argospm install translate-es_en
  ```

  Consulta los idiomas disponibles en *Estado del sistema*.

## Motores opcionales

El botón «⚙ Estado del sistema» indica qué hay instalado y enlaza a las
descargas de lo que falte. Nada de la lista es obligatorio:

| Componente | Para qué |
|---|---|
| LibreOffice | Word/Excel/PowerPoint a PDF con máxima fidelidad |
| Tesseract OCR | OCR PDF (instala el idioma *Spanish*) |
| Ghostscript | PDF a PDF/A |
| argostranslate | Traducir PDF |

## Preguntas frecuentes

**¿Se sube algo a internet?**
No. Salvo «HTML a PDF» con una URL (para descargar esa página), todo el
procesamiento es local.

**¿Por qué el `.exe` pesa tanto?**
Incluye Python y todos los motores de conversión (conversión a Word, OCR,
comparación por píxeles…). No necesita instalar nada más.

**¿Puedo usarlo en el trabajo y en mis servidores?**
Sí, es software libre bajo licencia AGPL-3.0.
