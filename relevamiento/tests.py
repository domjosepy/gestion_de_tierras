from django.test import SimpleTestCase
from django.template.loader import render_to_string

from .forms import RelevamientoCierreForm, RelevamientoServicioParte1Form


class MejorasInfraestructuraTemplateTests(SimpleTestCase):
    def test_servicio_parte1_renderiza_todas_las_mejoras(self):
        form = RelevamientoServicioParte1Form()

        html = render_to_string(
            "includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/extras/datos_mejoras_infraestructura.html",
            {"form": form},
        )

        self.assertEqual(html.count('type="checkbox"'), len(form.fields["mejoras"].choices))
        self.assertIn("Galpón", html)
        self.assertIn("Agua Potable", html)

    def test_cierre_renderiza_sus_campos(self):
        form = RelevamientoCierreForm()

        html = render_to_string(
            "includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/extras/cierre_cuestionario.html",
            {"form": form},
        )

        self.assertIn('name="estado_entrevista"', html)
        self.assertIn('name="firmo_solicitud"', html)
        self.assertIn('name="observacion_encuesta"', html)
