### ROL Y CONTEXTO
Actúa como un Desarrollador Full Stack experto en Django, Bootstrap 5, JavaScript/AJAX y arquitectura de interfaces administrativas. 

Necesito refactorizar/adaptar una plantilla HTML basada en Django (`detalle_solicitud.html`) para crear un nuevo template dedicado al **Detalle de Asignación de Colonias Relevadas** dentro del **Módulo de Análisis**.

---

### OBJETIVO
Tomar la estructura visual, jerarquía de diseño y patrones de la plantilla actual de "Detalle de Solicitud", y adaptarla para reflejar el flujo de trabajo del **Analista/Módulo de Análisis** al revisar y gestionar la asignación de colonias relevadas.

---

### REQUERIMIENTOS DE ADAPTACIÓN DE NEGOCIO Y UI

1. **Encabezado y Acciones Principales:**
   - **Título principal:** Debe indicar la colonia relevada en revisión de análisis.
   - **Indicadores de Estado:** Utilizar indicadores visuales consistentes (círculos de color con texto descriptivo adyacente para el estado de análisis/relevamiento).
   - **Menu de Acciones (Dropdown):** Reorganizar los permisos y modales para las acciones específicas del rol de Analista/Líder de Análisis (ej. Asignar analista, Devolver a digitalización, Validar análisis de colonia, Generar dictamen/informe técnico).

2. **Estructura de Tarjetas de Información (Grid principal):**
   - **Tarjeta 1 - Datos Geográficos y Cobertura:** Departamento, Distrito, Colonia, lista de sectores/manzanas relevadas y datos cuantitativos clave (hectáreas aproximadas, número de lotes relevados, áreas reservadas/comunales). 
   - **Tarjeta 2 - Información General de la Colonia Relevada:** Código de asignación/solicitud, estado del proceso de análisis, tipo de relevamiento y fechas de recepción vs. asignación.
   - **Tarjeta 3 - Asignación de Análisis:** Analista asignado, grupo técnico responsable, fechas de asignación y líder a cargo.

3. **Sección de Documentación y Archivos Adjuntos (Ajustado a Análisis):**
   - Adaptar las tarjetas de archivos para mostrar de forma independiente y clara la documentación técnica clave del proceso de Análisis:
     * **Antecedentes (PDF):** Documento escaneado que contiene el listado de personas y posibles adjudicatarios de la colonia relevada.
     * **Archivos SENATICS (PDF):** Informes y certificaciones oficiales en PDF sobre los posibles adjudicatarios y sus cónyuges.
     * **Planos y Documentación GIS:** Muestreo o enlaces a los planos finales y archivos espaciales adjuntos procedentes de la etapa de digitalización/SIG.

4. **Sección de Observaciones y Anotaciones Técnicas:**
   - Visualización clara de las notas técnicas dejadas por el equipo de digitalización/campo, y un área dedicada para dictámenes u observaciones del equipo de análisis.

5. **Historial y Auditoría:**
   - Mantener el componente de historial colapsable (`#collapseHistorial`), adaptado al registro de eventos de análisis.

6. **JavaScript / Event Delegation:**
   - Mantener la arquitectura de JavaScript mediante delegación de eventos (`document.addEventListener('click', ...)`).
   - Actualizar los nombres de las clases CSS de los botones (`.btn-asignar-analista`, `.btn-aprobar-analisis`, etc.), modales correspondientes e interactividad AJAX limpiando adecuadamente las variables de estado.
7. **Validación y Manejo de Errores:**
   - Asegurarse de que los mensajes de error y validación sean claros y específicos para el flujo de trabajo del módulo de análisis, incluyendo validaciones de archivos PDF, campos obligatorios y estados de asignación.
8. **Compatibilidad y Responsividad:**
   - Garantizar que la plantilla sea completamente responsiva y compatible con los estándares de Bootstrap 5, adaptando las tarjetas, tablas y modales para dispositivos móviles y pantallas de escritorio.
9. **Boton detalle:**
   - agregar boton ver detalle de asignacion de relevamiento en la columna acciones: que muestre el resultado del detalle_asignacion_relevamiento.html.
   ---
### REQUERIMIENTO ESPECIAL: ANÁLISIS Y ADAPTACIÓN DE MODELOS (SIG vs. ANÁLISIS)

Teniendo en cuenta que el módulo de **Análisis** cuenta con su propio modelo de datos (`models.py`) y que este se relaciona o complementa con el modelo del módulo `SIG`:

1. **Comparación e Integración de Modelos:**
   - Compara la estructura típica de la entidad de `Solicitud` o `Asignacion` en `SIG` con la entidad correspondiente en `Análisis`.
   - Reutiliza las relaciones existentes (ej. `Colonia`, `Departamento`, `Distrito`, `Auditoría`) donde sea conveniente.
   - Si se requieren campos adicionales en el modelo de `Análisis` para soportar esta plantilla (por ejemplo: `archivo_antecedentes`, `archivo_senatics`, `analista_asignado`, `estado_analisis`, etc.), indícame explícitamente qué campos agregar o modificar en el `models.py` de análisis.

2. **Adaptación de Contexto para la Vista (Views):**
   - Asegúrate de que las variables de contexto utilizadas en la plantilla (como `antecedentes_pdf`, `senatics_pdf`, `analisis.estado`, `analista_asignado`) reflejen de forma consistente la lógica del nuevo modelo o las vistas adaptadas para el módulo de análisis.

---

### CÓDIGO FUENTE DE REFERENCIA (TEMPLATE ORIGINAL: templates/sig/detalle_solicitud.html)
TEMPLATE EN EL CUAL TRABAJAR PARA INICIAR LA ADAPTACIÓN: `analisis/templates/analisis/detalle_asignacion_relevamiento.html.html`


