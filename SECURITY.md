# Política de seguridad

## Modelo de seguridad de la aplicación

RESG PDF Studio procesa los documentos **en el propio equipo**:

- No hay servidores propios, telemetría, analítica ni envío de archivos.
- No hay cuentas ni credenciales almacenadas.
- La única función que abre una conexión de red es «HTML a PDF» cuando le
  pasas una dirección web (para descargar esa página y convertirla); si usas
  archivos `.html` locales, tampoco hay red.
- «Traducir PDF» funciona con un modelo local (`argostranslate`): el texto no
  sale del ordenador.

## Cifrado

- «Proteger PDF» usa **AES-256** (mediante `pypdf`).
- Las contraseñas se piden en el momento y no se guardan en disco.

## Versiones compatibles

Se aplican correcciones a la última versión publicada en la rama `main`.

## Cómo informar de un problema de seguridad

1. **No abras una issue pública** con detalles explotables.
2. Usa la pestaña *Security → Report a vulnerability* del repositorio (avisos
   privados de GitHub) o escribe a la persona mantenedora indicada en el perfil.
3. Incluye: versión (`Ayuda → Estado del sistema`), sistema operativo, pasos
   para reproducirlo y el archivo de ejemplo si es imprescindible (recórtalo
   antes: puede contener datos personales).

Responderemos lo antes posible y, si procede, publicaremos una nota de versión
con el agradecimiento.

## Dependencias

El proyecto se apoya en librerías de terceros (`PyMuPDF`, `pypdf`, `pdf2docx`,
`pdfplumber`, `python-pptx`, `openpyxl`, `Pillow`, `numpy`). Si encuentras una
vulnerabilidad en alguna de ellas, avísanos igualmente para actualizar la
dependencia y publicar una versión nueva.
