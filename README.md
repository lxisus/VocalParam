# VocalParam

**Sistema Unificado de Grabación y Configuración de Voicebanks**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

VocalParam integra el proceso de grabación (OREMO) y configuración (SetParam) de voicebanks para síntesis vocal UTAU/OpenUtau en una sola aplicación.

## Características

- 📋 Importación de Reclist formato 7-Moras
- 🎤 Grabación con metrónomo visual y auditivo
- ⚡ Generación automática de `oto.ini` (algoritmo híbrido BPM + DSP)
- ✏️ Editor visual para ajustes manuales
- 📦 Exportación completa (WAVs + oto.ini)

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
