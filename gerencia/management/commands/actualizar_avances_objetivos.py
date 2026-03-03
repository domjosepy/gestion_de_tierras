"""
Comando de management para actualizar automáticamente los avances de los objetivos
basándose en los datos reales del sistema.

Uso:
    python manage.py actualizar_avances_objetivos [--anio YYYY]

Lógica:
- Para objetivos relacionados con "colonias relevadas": cuenta SolicitudRelevamiento con relevamiento_terminado=True
- Para objetivos relacionados con "encuestas": cuenta Relevamiento con estado_entrevista='completa'
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from gerencia.models import Objetivo, SolicitudRelevamiento
from coordinacion.models import OrdenTrabajo
from relevamiento.models import Relevamiento


class Command(BaseCommand):
    help = 'Actualiza automáticamente los avances de los objetivos basándose en datos reales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--anio',
            type=int,
            default=None,
            help='Año específico para actualizar (por defecto: año actual)'
        )
        parser.add_argument(
            '--objetivo-id',
            type=int,
            default=None,
            help='ID específico de un objetivo para actualizar (opcional)'
        )

    def handle(self, *args, **options):
        anio = options['anio'] or timezone.now().year
        objetivo_id = options['objetivo_id']

        self.stdout.write(self.style.WARNING(f'\n=== Actualizando avances de objetivos (Año: {anio}) ===\n'))

        # Filtrar objetivos
        if objetivo_id:
            objetivos = Objetivo.objects.filter(id=objetivo_id, activo=True)
        else:
            objetivos = Objetivo.objects.filter(anio=anio, activo=True).select_related('grupo', 'tipo_objetivo')

        if not objetivos.exists():
            self.stdout.write(self.style.ERROR(f'No se encontraron objetivos activos para el año {anio}'))
            return

        total_actualizados = 0
        total_sin_cambios = 0
        errores = 0

        for objetivo in objetivos:
            try:
                avance_anterior = objetivo.avance_actual
                nuevo_avance = self._calcular_avance(objetivo, anio)

                if nuevo_avance != avance_anterior:
                    objetivo.avance_actual = nuevo_avance
                    objetivo.save()
                    total_actualizados += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {objetivo.grupo.nombre} - {objetivo.tipo_objetivo.nombre}: '
                            f'{avance_anterior} → {nuevo_avance} ({objetivo.porcentaje_avance}%)'
                        )
                    )
                else:
                    total_sin_cambios += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'○ {objetivo.grupo.nombre} - {objetivo.tipo_objetivo.nombre}: '
                            f'{avance_anterior} (sin cambios)'
                        )
                    )

            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error en {objetivo.grupo.nombre} - {objetivo.tipo_objetivo.nombre}: {str(e)}'
                    )
                )

        # Resumen final
        self.stdout.write(self.style.WARNING(f'\n=== Resumen ==='))
        self.stdout.write(f'Total objetivos procesados: {objetivos.count()}')
        self.stdout.write(self.style.SUCCESS(f'Actualizados: {total_actualizados}'))
        self.stdout.write(self.style.WARNING(f'Sin cambios: {total_sin_cambios}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'Errores: {errores}'))
        self.stdout.write('')

    def _calcular_avance(self, objetivo, anio):
        """
        Calcula el avance real basándose en el tipo de objetivo.
        
        Args:
            objetivo: Instancia de Objetivo
            anio: Año a filtrar
            
        Returns:
            int: Avance calculado
        """
        tipo_nombre = objetivo.tipo_objetivo.nombre.lower()
        grupo_nombre = objetivo.grupo.nombre.lower()

        # Detectar tipo de objetivo por palabras clave
        # IMPORTANTE: Verificar encuestas primero, ya que es más específico
        if self._es_objetivo_encuestas(tipo_nombre, grupo_nombre):
            return self._contar_encuestas_completas(anio)
        
        elif self._es_objetivo_colonias(tipo_nombre, grupo_nombre):
            return self._contar_colonias_relevadas(anio)
        
        else:
            # Para otros tipos de objetivos, mantener el valor actual (actualización manual)
            return objetivo.avance_actual

    def _es_objetivo_colonias(self, tipo_nombre, grupo_nombre):
        """Determina si el objetivo es de tipo 'colonias relevadas'"""
        palabras_clave = ['colonia', 'relevada']
        return any(palabra in tipo_nombre for palabra in palabras_clave)

    def _es_objetivo_encuestas(self, tipo_nombre, grupo_nombre):
        """Determina si el objetivo es de tipo 'encuestas'"""
        palabras_clave = ['encuesta', 'solicitud', 'formulario', 'entrevista']
        return any(palabra in tipo_nombre for palabra in palabras_clave)

    def _contar_colonias_relevadas(self, anio):
        """
        Cuenta las solicitudes con relevamiento_terminado=True en el año especificado.
        
        Args:
            anio: Año a filtrar
            
        Returns:
            int: Cantidad de solicitudes con relevamiento terminado
        """
        return SolicitudRelevamiento.objects.filter(
            relevamiento_terminado=True,
            fecha_modificacion__year=anio
        ).count()

    def _contar_encuestas_completas(self, anio):
        """
        Cuenta los relevamientos con estado_entrevista='completa' en el año especificado.
        
        Args:
            anio: Año a filtrar
            
        Returns:
            int: Cantidad de encuestas completas
        """
        return Relevamiento.objects.filter(
            estado_entrevista='completa',
            creado_en__year=anio
        ).count()
