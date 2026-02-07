# Plan de Desarrollo y Progreso

VocalParam es un proyecto ambicioso que busca redefinir la creación de voicebanks. Este documento detalla nuestra hoja de ruta, los hitos alcanzados y lo que está por venir.

## Estado Actual: v1.0.0-prototype (Sprint 3 Completado)

Estamos operando bajo la filosofía **Zero-Switch**, unificando la grabación y parametrización en una sola experiencia técnica de primer nivel.

---

## Hoja de Ruta (Roadmap)

### 🟢 Sprint 1: Cimientos y Arquitectura Core (Completado)
- [x] Configuración del entorno de desarrollo (Python/PyQt6).
- [x] Implementación del Motor de Audio basado en `sounddevice`.
- [x] Arquitectura MVC para escalabilidad.
- [x] Sistema de logging y manejo de errores.

### 🟢 Sprint 2: Grabación Proactiva y Motor de Audio (Completado)
- [x] **Grabación 7-Moras**: Metrónomo visual y auditivo de alta precisión.
- [x] **Gestión de Archivos**: Selector de destino integrado en el panel de grabación.
- [x] **Control de Calidad**: Botón Play/Listen para verificación inmediata.
- [x] **Sincronización Crítica**: Corrección del desfase en Mora 0 (sincronización instantánea).
- [x] **Motor de Audio V2**: Gestión segura de hardware (Windows Fix) y headers WAV dinámicos.
- [x] **Visualización DSP**: WaveformScope de alta precisión con indicadores de nivel.
- [x] **Sincronización de Tiempo**: Barra de progreso sincronizada en tiempo real (`time.time()`).
- [x] **Grabación Pro-UX**: Implementación de Count-in y metrónomo persistente "Glitch-free".

### 🟢 Sprint 3: Editor Visual y Auto-OTO (Completado)
- [x] **WaveformCanvas**: Visualizador interactivo con Espectrograma STFT y RMS.
- [x] **Sistema de Marcadores**: Controladores visuales sincronizados para los 5 parámetros OTO.
- [x] **Sincronización Bidireccional**: Tabla de parámetros <-> Editor Visual en tiempo real.
- [x] **Algoritmo Auto-OTO**: Detección inteligente de transientes para posicionamiento inicial de Offset.
- [x] **Validación de Reglas**: Implementación de la "Regla de Oro" (Overlap <= Pre-utterance).

### ⚪ Sprint 4: Inteligencia y Automatización (Siguiente)
- [ ] Refinamiento del algoritmo de detección fonética (específico por fonema).
- [ ] Soporte para diferentes idiomas y estilos de grabación.
- [ ] Herramientas de diagnóstico de calidad vocal.

### ⚪ Sprint 5: Exportación y Compatibilidad
- [ ] Exportación completa garantizada para UTAU y OpenUtau.
- [ ] Empaquetado de Voicebanks (.zip).
- [ ] Importador de proyectos legacy de OREMO/SetParam.

### ⚪ Sprint 6: Pulido y Lanzamiento v1.0 Stable
- [ ] Optimización de rendimiento.
- [ ] Temas visuales personalizados.
- [ ] Documentación extensiva y tutoriales en video.

---

## Logros Recientes
- **Febrero 2026**: Finalización del Sprint 3 (Editor Visual y DSP Avanzado).
- **Febrero 2026**: Implementación del flujo de grabación con Count-in y metrónomo de baja latencia.
- **Enero 2026**: Implementación del flujo unificado de grabación.
- **Enero 2026**: Resolución de problemas críticos de hardware de audio en Windows.
- **Enero 2026**: Lanzamiento de la documentación técnica centralizada.

> [!NOTE]
> Nuestro progreso se guía por el feedback de la comunidad y la búsqueda de la perfección técnica en cada mora grabada.
