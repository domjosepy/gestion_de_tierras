"""
Tests para las funciones de upload_to personalizadas
"""
from django.test import TestCase
from relevamiento.models import limpiar_nombre_carpeta


class LimpiarNombreCarpetaTest(TestCase):
    """Tests para la función limpiar_nombre_carpeta"""
    
    def test_elimina_espacios(self):
        """Debe reemplazar espacios por guiones bajos"""
        resultado = limpiar_nombre_carpeta("San Pedro del Paraná")
        self.assertEqual(resultado, "san_pedro_del_parana")
    
    def test_elimina_caracteres_especiales(self):
        """Debe eliminar caracteres especiales"""
        resultado = limpiar_nombre_carpeta("Colonia N° 24")
        self.assertEqual(resultado, "colonia_n_24")
    
    def test_convierte_minusculas(self):
        """Debe convertir todo a minúsculas"""
        resultado = limpiar_nombre_carpeta("DISTRITO NORTE")
        self.assertEqual(resultado, "distrito_norte")
    
    def test_nombre_vacio(self):
        """Debe retornar 'sin_nombre' si el nombre está vacío"""
        resultado = limpiar_nombre_carpeta("")
        self.assertEqual(resultado, "sin_nombre")
    
    def test_nombre_none(self):
        """Debe retornar 'sin_nombre' si el nombre es None"""
        resultado = limpiar_nombre_carpeta(None)
        self.assertEqual(resultado, "sin_nombre")
    
    def test_mantiene_guiones(self):
        """Debe mantener guiones y guiones bajos"""
        resultado = limpiar_nombre_carpeta("test-nombre_archivo")
        self.assertEqual(resultado, "test-nombre_archivo")
    
    def test_multiples_espacios(self):
        """Debe manejar múltiples espacios consecutivos"""
        resultado = limpiar_nombre_carpeta("San     Pedro   Norte")
        self.assertEqual(resultado, "san_____pedro___norte")
    
    def test_caracteres_latinos(self):
        """Debe manejar caracteres acentuados (no los transforma)"""
        resultado = limpiar_nombre_carpeta("Asunción")
        # Los acentos se eliminan porque no son alfanuméricos ASCII
        self.assertEqual(resultado, "asuncin")
    
    def test_numeros(self):
        """Debe mantener números"""
        resultado = limpiar_nombre_carpeta("Colonia 123")
        self.assertEqual(resultado, "colonia_123")


# Para ejecutar los tests:
# python manage.py test relevamiento.test_upload_paths.LimpiarNombreCarpetaTest -v 2


class PathRelevamientoUploadTest(TestCase):
    """Tests para las funciones de upload_to"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Crear departamento
        self.departamento = Departamento.objects.create(
            nombre="San Pedro",
            codigo="SP01"
        )
        
        # Crear distrito
        self.distrito = Distrito.objects.create(
            nombre="Distrito Central",
            codigo="DC01",
            departamento=self.departamento
        )
        
        # Crear colonia
        self.colonia = Colonia.objects.create(
            nombre="Nueva Esperanza",
            codigo="COL001"
        )
        self.colonia.distritos.add(self.distrito)
        
        # Crear grupo
        self.grupo = GrupoTrabajo.objects.create(
            nombre="Grupo Test",
            lider=self.user
        )
        
        # Crear orden de trabajo
        self.orden = OrdenTrabajo.objects.create(
            colonia=self.colonia,
            grupo=self.grupo,
            fecha_creacion=datetime(2026, 2, 25, 10, 30, 0),
            estado='pendiente'
        )
    
    def test_path_relevamiento_upload_estructura(self):
        """Debe generar la ruta correcta para archivos generales"""
        # Crear instancia mock con orden_trabajo
        class MockInstance:
            def __init__(self, orden):
                self.orden_trabajo = orden
        
        instance = MockInstance(self.orden)
        filename = "archivo_test.zip"
        
        ruta = path_relevamiento_upload(instance, filename)
        
        # Verificar que la ruta tiene el formato correcto
        self.assertIn("relevamiento/", ruta)
        self.assertIn("san_pedro/", ruta)
        self.assertIn("distrito_central/", ruta)
        self.assertIn("nueva_esperanza/", ruta)
        self.assertIn("2026-02-25/", ruta)
        self.assertIn("archivo_test.zip", ruta)
    
    def test_path_relevamiento_fotos_upload_estructura(self):
        """Debe generar la ruta correcta para fotos con subcarpeta FOTOS"""
        # Crear instancia mock con orden_trabajo
        class MockInstance:
            def __init__(self, orden):
                self.orden_trabajo = orden
        
        instance = MockInstance(self.orden)
        filename = "foto_vivienda.jpg"
        
        ruta = path_relevamiento_fotos_upload(instance, filename)
        
        # Verificar que la ruta tiene el formato correcto y subcarpeta FOTOS
        self.assertIn("relevamiento/", ruta)
        self.assertIn("san_pedro/", ruta)
        self.assertIn("distrito_central/", ruta)
        self.assertIn("nueva_esperanza/", ruta)
        self.assertIn("2026-02-25/", ruta)
        self.assertIn("FOTOS/", ruta)
        self.assertIn("foto_vivienda.jpg", ruta)
    
    def test_path_con_relevamiento_intermediario(self):
        """Debe funcionar cuando la instancia tiene relevamiento.orden_trabajo"""
        # Crear relevamiento
        relevamiento = Relevamiento.objects.create(
            orden_trabajo=self.orden,
            colonia=self.colonia,
            distrito=self.distrito,
            departamento=self.departamento
        )
        
        # Mock de instancia con relevamiento
        class MockInstance:
            def __init__(self, relev):
                self.relevamiento = relev
        
        instance = MockInstance(relevamiento)
        filename = "documento.pdf"
        
        ruta = path_relevamiento_fotos_upload(instance, filename)
        
        # Verificar que se generó correctamente
        self.assertIn("relevamiento/", ruta)
        self.assertIn("FOTOS/", ruta)
        self.assertIn("documento.pdf", ruta)


class ModelosFileFieldTest(TestCase):
    """Tests para verificar que los modelos usan las funciones correctas"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.departamento = Departamento.objects.create(
            nombre="Test Depto",
            codigo="TD01"
        )
        
        self.distrito = Distrito.objects.create(
            nombre="Test Distrito",
            codigo="TDI01",
            departamento=self.departamento
        )
        
        self.colonia = Colonia.objects.create(
            nombre="Test Colonia",
            codigo="TC001"
        )
        self.colonia.distritos.add(self.distrito)
        
        self.grupo = GrupoTrabajo.objects.create(
            nombre="Grupo Test",
            lider=self.user
        )
        
        self.orden = OrdenTrabajo.objects.create(
            colonia=self.colonia,
            grupo=self.grupo,
            fecha_creacion=datetime.now(),
            estado='pendiente'
        )
        
        self.relevamiento = Relevamiento.objects.create(
            orden_trabajo=self.orden,
            colonia=self.colonia,
            distrito=self.distrito,
            departamento=self.departamento
        )
    
    def test_archivo_subcoordinador_usa_path_correcto(self):
        """ArchivoSubcoordinador debe usar path_relevamiento_upload"""
        campo = ArchivoSubcoordinador._meta.get_field('archivo')
        # Verificar que upload_to es una función (no un string)
        self.assertTrue(callable(campo.upload_to))
        self.assertEqual(campo.upload_to.__name__, 'path_relevamiento_upload')
    
    def test_documento_usa_path_fotos(self):
        """Documento debe usar path_relevamiento_fotos_upload"""
        campo = Documento._meta.get_field('archivo')
        self.assertTrue(callable(campo.upload_to))
        self.assertEqual(campo.upload_to.__name__, 'path_relevamiento_fotos_upload')
    
    def test_foto_relevamiento_usa_path_fotos(self):
        """FotoRelevamiento debe usar path_relevamiento_fotos_upload"""
        campo = FotoRelevamiento._meta.get_field('foto')
        self.assertTrue(callable(campo.upload_to))
        self.assertEqual(campo.upload_to.__name__, 'path_relevamiento_fotos_upload')


class IntegracionModelosTest(TestCase):
    """Tests de integración verificando creación de modelos"""
    
    def setUp(self):
        """Configurar datos de prueba completos"""
        self.user = User.objects.create_user(
            username='encuestador',
            password='pass123'
        )
        
        self.departamento = Departamento.objects.create(
            nombre="Caaguazú",
            codigo="CG"
        )
        
        self.distrito = Distrito.objects.create(
            nombre="Coronel Oviedo",
            codigo="CO",
            departamento=self.departamento
        )
        
        self.colonia = Colonia.objects.create(
            nombre="Colonia Primavera",
            codigo="PRIM01"
        )
        self.colonia.distritos.add(self.distrito)
        
        self.grupo = GrupoTrabajo.objects.create(
            nombre="Equipo 1",
            lider=self.user
        )
        
        self.orden = OrdenTrabajo.objects.create(
            colonia=self.colonia,
            grupo=self.grupo,
            fecha_creacion=datetime(2026, 3, 15, 8, 0, 0),
            estado='activa'
        )
        
        self.relevamiento = Relevamiento.objects.create(
            orden_trabajo=self.orden,
            colonia=self.colonia,
            distrito=self.distrito,
            departamento=self.departamento,
            encuestador=self.user
        )
    
    def test_crear_archivo_subcoordinador(self):
        """Debe poder crear un ArchivoSubcoordinador"""
        archivo = ArchivoSubcoordinador.objects.create(
            orden_trabajo=self.orden,
            # archivo se asignaría desde un form con archivo real
            nombre_archivo="test_archivo.zip",
            subido_por=self.user
        )
        
        self.assertIsNotNone(archivo.id)
        self.assertEqual(archivo.nombre_archivo, "test_archivo.zip")
        self.assertEqual(archivo.orden_trabajo, self.orden)
    
    def test_crear_foto_relevamiento(self):
        """Debe poder crear una FotoRelevamiento"""
        foto = FotoRelevamiento.objects.create(
            relevamiento=self.relevamiento,
            # foto se asignaría desde un form con imagen real
            tipo_foto='vivienda_frente',
            descripcion='Fachada principal',
            encuestador=self.user,
            latitud=-25.4450,
            longitud=-56.5000
        )
        
        self.assertIsNotNone(foto.id)
        self.assertEqual(foto.tipo_foto, 'vivienda_frente')
        self.assertEqual(foto.relevamiento, self.relevamiento)
    
    def test_crear_documento(self):
        """Debe poder crear un Documento"""
        documento = Documento.objects.create(
            relevamiento=self.relevamiento,
            tipo='recibo',
            nombre_archivo='recibo_001.pdf'
        )
        
        self.assertIsNotNone(documento.id)
        self.assertEqual(documento.tipo, 'recibo')
        self.assertEqual(documento.relevamiento, self.relevamiento)


# Para ejecutar los tests:
# python manage.py test relevamiento.test_upload_paths
