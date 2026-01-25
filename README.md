# VocalParam

**Sistema Unificado de Grabación y Configuración de Voicebanks**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

VocalParam integra el proceso de grabación (**OREMO**) y configuración (**SetParam**) de voicebanks en una sola experiencia fluida, eliminando la fricción técnica y permitiendo que te enfoques en la calidad vocal desde el primer milisegundo.

## Características

- 🎯 **Flujo Unificado**: Graba y configura parámetros de forma simultánea.
- 📋 **Soporte Reclist 7-Moras**: Validación y parseo automático de estructuras fonéticas.
- 🎤 **Grabación de Alta Precisión**: Metrónomo visual y auditivo con sincronización perfecta (mora 0 iniciada instantáneamente).
- 📂 **Gestión de Destinos**: Elige dónde guardar tus muestras directamente desde la interfaz de grabación.
- ▶️ **Escucha Integrada**: Botón Play/Listen para verificar tomas antes de aceptarlas.
- ⚡ **Auto-Oto**: Generación de `oto.ini` mediante algoritmo híbrido (BPM + DSP).
- ✏️ **Editor Visual**: Ajuste fino de parámetros con feedback visual en tiempo real.

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/[org]/vocalparam.git
cd vocalparam

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python src/main.py
```

## Requisitos

- Python 3.11+
- Windows 10/11, macOS 11+, o Linux (Ubuntu 20.04+)

## Uso Rápido

1. Crear nuevo proyecto
2. Cargar archivo Reclist (.txt)
3. Grabar cada línea siguiendo el metrónomo
4. Generar oto.ini automáticamente
5. Ajustar parámetros si es necesario
6. Exportar voicebank

## Licencia

MIT License - Ver [LICENSE](LICENSE)

## Versión

v1.0.0-prototype (Fase 1 MVP)
