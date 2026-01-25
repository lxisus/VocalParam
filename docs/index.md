# Bienvenido a VocalParam

VocalParam es un sistema de código abierto diseñado para unificar el proceso de grabación y configuración de voicebanks para síntesis vocal (UTAU/OpenUtau).

## Status Quo: Sprint 2 Finalizado

Actualmente el proyecto ha alcanzado un nivel de madurez técnica crítico para la grabación profesional. Hemos resuelto los principales puntos de dolor de hardware y sincronización, permitiendo un flujo de trabajo confiable.

## Filosofía del Proyecto: El "Zero-Switch"

Desde su concepción, VocalParam ha sido diseñado bajo la premisa de eliminar el cambio constante de aplicaciones durante la creación de un voicebank. Tradicionalmente, un creador debe grabar en OREMO y luego parametrizar en SetParam o vLabeler. 

Nuestra filosofía **Zero-Switch** unifica estas fases:
- **Calidad en el Origen**: Al visualizar y escuchar mientras grabas, detectas errores fonéticos al instante.
- **Flujo Sofisticado**: Una interfaz premium que respeta la precisión técnica exigida por los motores de síntesis vocal modernos.

## Características Principales

- **Grabación 7-Moras Pro**: Metrónomo de alta precisión y sistema de "mora zero" instantánea.
- **WaveformScope DSP**: Visualización en tiempo real de la intensidad y calidad del audio capturado.
- **Auto-Oto Híbrido**: Generación automática de parámetros basándose en BPM y análisis DSP.
- **Gestión de Recursos**: Control total sobre carpetas de destino y escucha integrada (Play/Listen).

## Estructura del Proyecto

El proyecto sigue una arquitectura **MVC** (Modelo-Vista-Controlador) para asegurar que sea fácil de mantener y escalar.

```mermaid
graph TD
    UI[Interfaz de Usuario] --> Controller[Controladores]
    Controller --> Core[Lógica Core / Modelos]
    Core --> Files[(Archivos WAV/INI)]
```

Consulte la [Guía de Usuario](user_guide.md) para empezar.
