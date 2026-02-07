# Historial de Cambios (Changelog)

Este documento registra todas las actualizaciones significativas y mejoras técnicas de VocalParam, clasificadas por fases y hitos del Plan Maestro.

## [v1.0.0-prototype] - Febrero 2026 (Sprint 3)

### ✨ Nuevas Funcionalidades
- **Editor Visual Interactivo**: Implementación de `WaveformCanvas` con soporte para espectrograma STFT (Hann 2048) y envolvente RMS.
- **Sistema de Marcadores**: 5 marcadores interactivos (Offset, Consonant, Cutoff, Pre-utterance, Overlap) con drag-and-drop sincronizado.
- **Auto-OTO Híbrido**: Generación automática de parámetros basada en transientes de audio y rejilla de BPM.
- **Grabación Pro-UX**: Implementación de cuenta regresiva (3-beat count-in) y metrónomo persistente sin interrupciones ("glitch-free").
- **Garantía de Cola (Right Blank)**: Duración mínima de 4 segundos para asegurar espacio suficiente para la configuración de la nota.
- **Validación en Tiempo Real**: Bloqueo automático de configuraciones inválidas (Regla de Oro: Overlap > Preutterance).

### 🐛 Correcciones y Refinamientos
- **Metrónomo Fluido**: Uso de `sd.OutputStream` persistente para eliminar el audio choppy/trabado en Windows.
- **Sincronización Bidireccional**: Los cambios manuales en la tabla de parámetros actualizan la posición visual del marcador instantáneamente.
- **Detección de Silencio de Preparación**: El algoritmo de OTO ahora ignora inteligentemente el periodo de "Count-in" para fijar el `Offset` con precisión.

---

## [v1.0.0-prototype] - Enero 2026

### ✨ Nuevas Funcionalidades
- **Motor de Audio V2**: Reescritura del sistema de captura para soportar parámetros de hardware dinámicos.
- **WaveformScope DSP**: Nuevo widget de visualización de ondas en tiempo real con alta sensibilidad y indicadores de nivel (Verde/Rojo).
- **Selector de Destino Inteligente**: Permite cambiar la ruta de las grabaciones directamente desde el panel principal.
- **Botón Play/Listen**: Verificación inmediata de la calidad capturada antes de aceptar la toma.
- **Sistema de Puntuación de Dispositivos**: Detección automática y priorización de hardware Pro (ASIO, Focusrite, etc.).

### 🐛 Correcciones Críticas (Fixes)
- **Sincronización Mora 0**: Eliminado el desfase inicial; el metrónomo ahora es píxel-perfecto desde el primer milisegundo.
- **Corrupción de WAV (44 bytes)**: Se corrigió el error donde el buffer se sobreescribía al presionar "Aceptar", garantizando que lo que se graba es lo que se guarda.
- **Corte Prematuro (Tail Recording)**: Implementado el "Tail Beat" de un pulso extra para asegurar que las terminaciones vocales no se corten.
- **Barra de Progreso**: Sincronizada con `time.time()` para ofrecer un movimiento fluido al 100%.
- **Error "Invalid Device" en Windows**: Implementado retraso de seguridad y gestión de bloqueos (`threading.Lock`) para liberar el hardware apropiadamente.

### 📝 Documentación
- Lanzamiento del sitio web oficial con arquitectura técnica y manual de usuario.
- Integración de la filosofía **Zero-Switch** en toda la comunicación del proyecto.
- Nueva página de **Plan y Progreso (Roadmap)** para transparencia total.

---

## Historial de Commits Recientes

| Hash | Mensaje |
| :--- | :--- |
| `d6fce89` | feat: cumulative updates for VocalParam v1.0 master plan (Fases 1-5) |
| `b40ed08` | docs: add development plan and roadmap page |
| `0b86556` | feat: implement path selector, playback button, and metronome sync fix |
| `ba8dd5e` | docs: update with Zero-Switch philosophy |

> [!TIP]
> Puedes ver el detalle completo en el [Repositorio de GitHub](https://github.com/lxisus/VocalParam).
