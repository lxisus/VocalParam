# Guía de Usuario: VocalParam

VocalParam simplifica la creación de voicebanks UTAU/OpenUtau integrando la grabación y la parametrización.

## Primeros Pasos

### 1. Crear un Proyecto
Al abrir VocalParam, use **Archivo > Nuevo Proyecto**. Especifique el nombre y el BPM (por defecto 120).

### 2. Cargar Reclist
Cargue su archivo `.txt` de reclist. VocalParam validará que siga la arquitectura de **7-Moras**.

### 3. Grabación Proactiva y Control de Calidad
1. Seleccione una línea en el panel izquierdo.
2. **Configure el Destino**: En la parte superior del panel de grabación, verifique o cambie la carpeta donde se guardarán los WAVs usando el botón `...`.
3. Presione `Space` para iniciar el metrónomo.
4. **Sincronización Perfecta**: Pronuncie cada sílaba sincronizada con el click. Note que el primer recuadro se activa instantáneamente al iniciar para una referencia precisa.
5. Al finalizar los 7 golpes, use el botón **▶ Escuchar / Listen** para verificar su toma.
6. Si la toma es correcta, presione **Aceptar (Enter)** para guardar el archivo y avanzar. De lo contrario, presione **R** para repetir.

### 4. Generación de oto.ini
Presione **Proyecto > Generar oto.ini**. El sistema usará el algoritmo híbrido para calcular los parámetros basándose en el ritmo y análisis DSP.

### 5. Ajuste Fino
Use el **Editor Visual** para arrastrar las líneas de parámetros:
- **Cian**: Offset
- **Verde**: Overlap
- **Rojo**: Pre-utterance
- **Azul**: Consonant
- **Rosa**: Cutoff
