# Arquitectura del Sistema

VocalParam está construido con una arquitectura **MVC** desacoplada para permitir escalabilidad y portabilidad a C++.

## Componentes

### Core (Modelo)
Contiene la lógica de negocio pura:
- `ReclistParser`: Análisis fonético.
- `AudioEngine`: I/O de audio (sounddevice).
- `DSPAnalyzer`: Algoritmos de pitch y transientes.
- `OtoGenerator`: Cálculo de parámetros.

### UI (Vista)
Widgets de PyQt6:
- `MainWindow`: Contenedor principal.
- `RecorderWidget`: Metrónomo y visualización en tiempo real.
- `EditorWidget`: Edición visual de parámetros.

### Controllers (Controlador)
Orquestan la interacción entre el usuario y el core.

## Flujo de Datos

1. El usuario interactúa con la UI.
2. El Controlador recibe la señal y solicita datos al Core.
3. El Core procesa y devuelve objetos de datos (`OtoEntry`, `PhoneticLine`).
4. El Controlador actualiza la UI.
