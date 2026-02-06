# gerencia/utils.py
from django.contrib.auth.models import User


def procesar_auditorias(auditorias_queryset):
    """
    Procesa las auditorías para desglosar registros 'asignacion_completa'
    y mostrar de manera coherente
    """
    MAPEO_CAMPOS = {
        'estado': 'Estado',
        'usuario_asignado': 'Usuario Asignado',
        'usuario_digitalizador': 'Digitalizador',  # Mapeo actualizado
        'grupo_asignado': 'Grupo Asignado',
        'motivo_rechazo': 'Motivo de Rechazo',
        'creacion': 'Creación',
        'asignacion_completa': 'Asignación Completa',
        'observaciones': 'Observaciones',
        'asignado_por': 'Asignado Por',
        'fecha_asignacion': 'Fecha de Asignación',
    }

    auditorias_procesadas = []
    # Usar un set para evitar duplicados por timestamp
    registros_vistos = set()

    for audit in auditorias_queryset:
        # Crear una clave única para este registro
        registro_key = f"{audit.fecha}_{audit.campo}_{audit.valor_anterior}_{audit.valor_nuevo}"

        if registro_key in registros_vistos:
            continue  # Saltar duplicados

        registros_vistos.add(registro_key)

        # Manejar cambiado_por que puede ser None
        cambiado_por_display = "Sistema"
        cambiado_por_obj = None

        if audit.cambiado_por:
            cambiado_por_display = audit.cambiado_por.get_full_name() or audit.cambiado_por.username
            cambiado_por_obj = audit.cambiado_por

        if audit.campo == 'asignacion_completa':
            # Desglosar asignación completa
            try:
                anterior = audit.valor_anterior.split(', ')
                nuevo = audit.valor_nuevo.split(', ')

                if len(anterior) >= 2 and len(nuevo) >= 2:
                    estado_anterior = anterior[0].replace('Estado: ', '')
                    usuario_anterior = anterior[1].replace('Usuario: ', '')
                    estado_nuevo = nuevo[0].replace('Estado: ', '')
                    usuario_nuevo = nuevo[1].replace('Usuario: ', '')

                    # Crear dos registros virtuales
                    auditorias_procesadas.append({
                        'fecha': audit.fecha,
                        'cambiado_por_display': cambiado_por_display,
                        'cambiado_por_obj': cambiado_por_obj,
                        'campo': 'estado',
                        'campo_display': 'Estado',
                        'valor_anterior': estado_anterior,
                        'valor_nuevo': estado_nuevo,
                        'comentario': f"Asignación realizada por {cambiado_por_display}",
                        'es_virtual': True
                    })
                    auditorias_procesadas.append({
                        'fecha': audit.fecha,
                        'cambiado_por_display': cambiado_por_display,
                        'cambiado_por_obj': cambiado_por_obj,
                        'campo': 'usuario_asignado',
                        'campo_display': 'Usuario Asignado',
                        'valor_anterior': usuario_anterior,
                        'valor_nuevo': usuario_nuevo,
                        'comentario': audit.comentario,
                        'es_virtual': True
                    })
                else:
                    # Si no se puede desglosar, mantener como está
                    auditorias_procesadas.append({
                        'fecha': audit.fecha,
                        'cambiado_por_display': cambiado_por_display,
                        'cambiado_por_obj': cambiado_por_obj,
                        'campo': audit.campo,
                        'campo_display': MAPEO_CAMPOS.get(audit.campo, audit.campo.replace('_', ' ').title()),
                        'valor_anterior': audit.valor_anterior,
                        'valor_nuevo': audit.valor_nuevo,
                        'comentario': audit.comentario,
                        'es_virtual': False
                    })
            except Exception as e:
                # En caso de error, mantener el registro original
                auditorias_procesadas.append({
                    'fecha': audit.fecha,
                    'cambiado_por_display': cambiado_por_display,
                    'cambiado_por_obj': cambiado_por_obj,
                    'campo': audit.campo,
                    'campo_display': MAPEO_CAMPOS.get(audit.campo, audit.campo.replace('_', ' ').title()),
                    'valor_anterior': audit.valor_anterior,
                    'valor_nuevo': audit.valor_nuevo,
                    'comentario': audit.comentario,
                    'es_virtual': False
                })
        else:
            campo_display = MAPEO_CAMPOS.get(
                audit.campo, audit.campo.replace('_', ' ').title())

            # Formatear valores para mostrar mejor
            valor_anterior = audit.valor_anterior
            valor_nuevo = audit.valor_nuevo

            # Para usuario_digitalizador, extraer solo el username si es una cadena compleja
            if audit.campo == 'usuario_digitalizador':
                if '(' in valor_anterior and ')' in valor_anterior:
                    valor_anterior = valor_anterior.split('(')[0].strip()
                if '(' in valor_nuevo and ')' in valor_nuevo:
                    valor_nuevo = valor_nuevo.split('(')[0].strip()

            auditorias_procesadas.append({
                'fecha': audit.fecha,
                'cambiado_por_display': cambiado_por_display,
                'cambiado_por_obj': cambiado_por_obj,
                'campo': audit.campo,
                'campo_display': campo_display,
                'valor_anterior': valor_anterior,
                'valor_nuevo': valor_nuevo,
                'comentario': audit.comentario,
                'es_virtual': False
            })

    # Ordenar por fecha descendente
    auditorias_procesadas.sort(key=lambda x: x['fecha'], reverse=True)
    return auditorias_procesadas
