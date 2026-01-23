# Guía de Usuario: VocalParam

VocalParam simplifica la creación de voicebanks UTAU/OpenUtau integrando la grabación y la parametrización.

## Primeros Pasos

### 1. Crear un Proyecto
Al abrir VocalParam, use **Archivo > Nuevo Proyecto**. Especifique el nombre y el BPM (por defecto 120).

### 2. Cargar Reclist
Cargue su archivo `.txt` de reclist. VocalParam validará que siga la arquitectura de **7-Moras**.

### 3. Grabación Proactiva
1. Seleccione una línea en el panel izquierdo.
2. Presione `Space` para iniciar el metrónomo.
3. Pronuncie cada sílaba sincronizada con el click.
4. El sistema guardará el WAV automáticamente al finalizar los 7 golpes.

### 4. Generación de oto.ini
Presione **Proyecto > Generar oto.ini**. El sistema usará el algoritmo híbrido para calcular los parámetros basándose en el ritmo y análisis DSP.

### 5. Ajuste Fino
Use el **Editor Visual** para arrastrar las líneas de parámetros:
- **Cian**: Offset
- **Verde**: Overlap
- **Rojo**: Pre-utterance
- **Azul**: Consonant
- **Rosa**: Cutoff
