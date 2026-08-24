# ADR 002: Gestión de datos SIG y relevamientos


## Contexto
El sistema `gestion_de_tierras` integra módulos especializados para el manejo de información geográfica (SIG) y el levantamiento de datos en colonias. Dada la naturaleza crítica de estos datos para la administración territorial, la gestión eficiente de tierras y la emisión de títulos, es imperativo establecer una arquitectura coherente. El análisis de las dependencias actuales revela interconexiones críticas entre los módulos: `gerencia`, `coordinacion`, `sig`, `analisis` y `relevamiento`.

## Decisión
Se ha definido adoptar un **enfoque de centralización de datos SIG** estructurado bajo las siguientes pautas operativas y funcionales:

*   **Gestión Estratégica (Módulo Gerencia):** Actúa como el origen de las solicitudes de relevamiento y la autoridad para la aprobación de informes resultantes.
*   **Gestión Operativa (Módulo Coordinación):** Ejerce como generador de órdenes de trabajo, gestionando tanto el despliegue de relevamientos como las actualizaciones territoriales necesarias.
*   **Núcleo Geoespacial (Módulo SIG):** Funciona como proveedor central de servicios geográficos, suministrando mapas, coordenadas y capas de información. Se mantiene la integración con el componente de digitalización para asegurar la trazabilidad entre los estudios de relevamiento y los datos geográficos.
*   **Captura de Campo (Módulo Relevamiento):** Se integra como consumidor de servicios SIG, registrando formalmente colonias y atributos territoriales. Mantiene una relación directa con el coordinador de campo, el subcoordinador y el encuestador para garantizar la precisión en el registro de los datos de los ocupantes.
*   **Validación y Análisis (Módulo Análisis):** Actúa como el filtro y depurador de los datos coloniales recolectados (incluyendo adjudicaciones e informes). Se vincula con el perfil de analista para la revisión técnica de las colonias estudiadas.

**Integración Complementaria:**
*   **Vinculación Documental:** Se establece una conexión robusta con el módulo de `titulación` para asegurar que cada relevamiento esté debidamente vinculado a su expediente y título correspondiente.
*   **Limpieza de Repositorio:** Para mantener la claridad arquitectónica, se excluyen explícitamente del indexado todos los archivos binarios y directorios temporales o generados automáticamente (`__pycache__`, `migrations`).

## Consecuencias

### Beneficios
*   **Consistencia y Calidad:** La centralización garantiza una fuente única de verdad para mapas y coordenadas, eliminando discrepancias.
*   **Trazabilidad Integral:** Cada relevamiento queda documentado con una línea de tiempo y propiedad clara, conectando datos de campo con expedientes legales y títulos finales.
*   **Interoperabilidad:** La estandarización de los servicios SIG facilita la integración futura con otros sistemas administrativos o geográficos.

### Riesgos y Mitigación
*   **Acoplamiento:** La dependencia centralizada sobre el módulo `SIG` representa un riesgo potencial de cuello de botella o rigidez arquitectónica.
*   **Mitigación:** Se requiere como práctica obligatoria la documentación exhaustiva de todas las interfaces y APIs del sistema para minimizar el acoplamiento excesivo y permitir la evolución independiente de los módulos.


## Estado
Aceptado