---
description: Flujo de trabajo para el Editor de Parámetros (OTO Editor)
---

Este workflow describe el proceso para parametrizar grabaciones de forma efectiva, asegurando que los datos se persistan correctamente.

1. **Grabación y Transición**:
   - Selecciona una línea en la Reclist y realiza la grabación en el `Recorder`.
   - Al presionar **Aceptar**, el sistema generará una estimación inicial de parámetros y te redirigirá automáticamente al `Editor`.
   - **IMPORTANTE**: Cada nueva grabación se añade a la tabla global de parámetros. Puedes ver todas las parametrizaciones anteriores en la tabla inferior del Editor.

2. **Ajuste Fino de Parámetros**:
   - Usa los atajos de teclado para posicionar marcadores rápidamente:
     - `F1`: Posicionar **Left Blank** (Offset).
     - `F2`: Posicionar **Overlap**.
     - `F3`: Posicionar **Pre-Utterance**.
     - `F4`: Posicionar **Fixed** (Consonant).
     - `F5`: Posicionar **Right Blank** (Cutoff).
   - Los marcadores pueden arrastrarse manualmente con el ratón.
   - El sistema valida automáticamente la "Regla de Oro": En ningún momento el **Overlap** puede ser mayor que el **Pre-Utterance**.

3. **Navegación y Búsqueda**:
   - Usa la **Barra de Búsqueda** en el Editor para filtrar grabaciones por alias o nombre de archivo.
   - Selecciona cualquier fila en la **Tabla de Parámetros** para cargar instantáneamente su audio y marcadores en el visualizador.
   - Usa los botones **Prev** / **Next** para navegar secuencialmente por las muestras cargadas.

4. **Persistencia**:
   - Los cambios realizados en los marcadores o en la tabla se guardan automáticamente en la memoria del proyecto.
   - Para asegurar la persistencia en disco, utiliza `Ctrl+S` o el menú `Archivo > Guardar`.
   - **NOTA**: Si grabas la misma muestra nuevamente, la anterior será reemplazada, pero sus parámetros serán recalculados y actualizados en la tabla.
