"""
Script de prueba para verificar el módulo Control de Relevamiento
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_de_tierras.settings')
django.setup()

from coordinacion.models import OrdenTrabajo
from core.models import Colonia

print("=== Test de Control de Relevamiento ===\n")

# 1. Verificar órdenes completadas
print("1. Verificando órdenes completadas...")
ordenes_completadas = OrdenTrabajo.objects.filter(estado='completada')
print(f"   Total órdenes completadas: {ordenes_completadas.count()}")

if ordenes_completadas.exists():
    orden = ordenes_completadas.first()
    print(f"   Primera orden: ID={orden.id}, Estado={orden.estado}")
    if orden.solicitud and orden.solicitud.colonia:
        colonia = orden.solicitud.colonia
        print(f"   Colonia asociada: {colonia.nombre} (ID={colonia.id})")
        
        # 2. Verificar relevamientos de esa colonia
        from relevamiento.models import Relevamiento
        from django.db.models import Q
        
        print(f"\n2. Verificando relevamientos de colonia '{colonia.nombre}'...")
        total_relevamientos = Relevamiento.objects.filter(colonia=colonia).count()
        print(f"   Total relevamientos: {total_relevamientos}")
        
        # 3. Verificar mermas
        print(f"\n3. Verificando mermas...")
        mermas = Relevamiento.objects.filter(
            colonia=colonia
        ).filter(
            Q(condicion_vivienda='ausente') |
            Q(estado_entrevista='rechazo') |
            Q(estado_entrevista='en_conflicto')
        )
        print(f"   Total mermas: {mermas.count()}")
        
        if mermas.exists():
            print(f"\n   Detalle de mermas:")
            for merma in mermas[:5]:  # Mostrar solo las primeras 5
                estado = ''
                if merma.condicion_vivienda == 'ausente':
                    estado = 'AUSENTE'
                elif merma.estado_entrevista == 'rechazo':
                    estado = 'RECHAZADO'
                elif merma.estado_entrevista == 'en_conflicto':
                    estado = 'EN CONFLICTO'
                print(f"   - ID={merma.id}, Manzana={merma.manzana}, Lote={merma.lote_sirt}, Estado={estado}")
        
        # 4. Verificar URL
        print(f"\n4. URL de prueba:")
        print(f"   /coordinacion/control-relevamiento/mermas/{colonia.id}/")
        
    else:
        print("   ⚠ La orden no tiene solicitud o colonia asociada")
else:
    print("   ⚠ No hay órdenes completadas en el sistema")

print("\n=== Test completado ===")
print("\nPara probar manualmente, accede a:")
print("   http://localhost:8000/coordinacion/control-relevamiento/")
