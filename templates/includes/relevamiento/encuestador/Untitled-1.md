GESTION DE MERMAS DE RELEVAMIENTO..
Actúa como un Desarrollador Full Stack Senior experto en Dashboards Administrativos.
PARA LA APP COORDINACION. 
Objetivo: Crear un módulo de "Gestión de Mermas" diseñado para el Rol de Coordinación. Este módulo permite recuperar y gestionar registros de relevamiento fallidos o problemáticos.

Flujo de Usuario y Requerimientos:

Vista Inicial (Lista de Colonias): >    - Mostrar una tabla con las colonias que ya han sido relevadas. (ORDEN DE TRABAJO: ESTADO COMPLETADO)

Cada fila debe incluir una columna de "Acciones" con un botón primario llamado "Obtener Datos" (usar icono fa-sync).

Carga de Datos (Lógica de Filtrado):

Al hacer clic en "Obtener Datos", el sistema debe realizar una consulta filtrando únicamente los registros de esa colonia cuyo estado de entrevista sea: AUSENTE, RECHAZADO o EN CONFLICTO.

Vista de Resultados (Detalle de Mermas):

Una tabla dinámica que muestre: Manzana, Lote, Nombre del Encuestado (si existe) y el Estado de la Entrevista.

Visualización: Usa Badges (etiquetas de color) de Bootstrap para los estados:

RECHAZADO: Rojo (danger).

AUSENTE: Amarillo/Naranja (warning).

EN CONFLICTO: Púrpura o Gris oscuro (secondary / dark).

Especificaciones Técnicas:

Utilizar Bootstrap 5 para el diseño y JavaScript/AJAX para la carga de datos sin recargar la página.

Incluir un "Spinner" de carga mientras se obtienen los datos.

El diseño debe ser limpio, con encabezados claros que indiquen: "Gestión de Relevamientos con Novedades".

Entregable: Código HTML, CSS y la lógica de JS necesaria para simular este comportamiento.