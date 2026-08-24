# ADR 001: Arquitectura base del sistema "gestion_de_tierras"

## Contexto
El proyecto "gestion_de_tierras" es una aplicación Django orientada a la gestión de expedientes, relevamientos y módulos SIG. Durante el proceso de indexación se detectaron 1719 nodos y 6146 relaciones, lo que refleja una arquitectura modular con múltiples dependencias internas.

## Decisión
Se adopta una arquitectura **modular basada en apps Django**, con separación por dominio:

- **gerencia**: administración y comandos de gestión.
- **coordinación**: gestión de ordenes de trabajos y control.
- **sig**: gestión de mapas y coordenadas, asigna tareas a digitalizador.
- **digitalizador**: gestión de planos, superficies y coordenadas. responde a sig.
- **análisis**: gestión de colonias relevadas, asigna tareas al analista.
- **analista**: análisis y mapeo de colonias, clasificación y depuración de información. responde a análisis.
- **titulación**: manejo de expedientes y títulos.
- **relevamiento**: registro de colonias y datos territoriales; coordinador de campo, subcoordinador, encuestador.
- **expedienteo**: soporte a expedientes, seguimiento de situación de expedientes.

Patrones detectados:
- **MVC (Model-View-Controller)** propio de Django.
- **Repository pattern** en algunos módulos para acceso a datos.
- Uso de **migrations** y `__pycache__` excluidos del indexado.

## Consecuencias
- La modularidad facilita el mantenimiento y escalabilidad.
- La separación clara por dominio permite asignar responsabilidades a equipos distintos.
- El uso de Django asegura compatibilidad con librerías y buenas prácticas de seguridad.
- Se recomienda documentar dependencias críticas entre módulos (ejemplo: `relevamiento` depende de `coordinacion`).

## Estado
Aceptado.
