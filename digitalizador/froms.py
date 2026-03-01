from django import forms
from django.core.validators import FileExtensionValidator
from .models import PrecatArchivo


class PrecatSubirForm(forms.Form):
    """
    Formulario para subir archivos de Precat y Planos
    """
    archivo_precat = forms.FileField(
        label='Archivo Precat Final',
        required=True,
        validators=[FileExtensionValidator(['zip', 'rar', 'jpg', 'jpeg', 'png'])],
        help_text='Formato .zip, .rar o imagen (.jpg/.jpeg/.png) (Máx. 200MB)'
    )
    archivo_planos = forms.FileField(
        label='Planos de Referencia',
        required=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Formato .pdf o imagen (.jpg/.jpeg/.png) (Máx. 50MB por archivo)'
    )
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Describa el trabajo realizado, observaciones importantes, etc.'
        }),
        help_text='Descripción detallada del trabajo de digitalización'
    )
    
    # Campos de anotación solicitados
    lotes_digitalizados = forms.IntegerField(
        label='Lotes digitalizados',
        required=True,
        min_value=0,
        help_text='Cantidad de lotes digitalizados'
    )
    calles = forms.IntegerField(
        label='Calles',
        required=False,
        min_value=0,
        help_text='Cantidad de calles (opcional)'
    )
    reservas = forms.IntegerField(
        label='Reservas',
        required=False,
        min_value=0,
        help_text='Cantidad de reservas (opcional)'
    )
    campos_comunales = forms.IntegerField(
        label='Campos comunales',
        required=False,
        min_value=0,
        help_text='Cantidad de campos comunales (opcional)'
    )
    hectareas_aprox = forms.DecimalField(
        label='Hectáreas aproximadas',
        required=False,
        max_digits=10,
        decimal_places=4,
        min_value=0,
        help_text='Superficie aproximada en hectáreas (opcional)'
    )
    metros_aprox = forms.IntegerField(
        label='Metros aproximados',
        required=False,
        min_value=0,
        help_text='Superficie aproximada en metros (opcional)'
    )

    def clean_archivo_precat(self):
        archivo = self.cleaned_data.get('archivo_precat')
        if archivo:
            # Validar tamaño máximo (200MB)
            max_size = 200 * 1024 * 1024  # 200MB
            if archivo.size > max_size:
                raise forms.ValidationError(
                    f'El archivo Precat no puede superar los 200MB. Tamaño actual: {archivo.size/(1024*1024):.2f}MB'
                )
        return archivo

    def clean_archivo_planos(self):
        archivo = self.cleaned_data.get('archivo_planos')
        if archivo:
            # Validar tamaño máximo (50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if archivo.size > max_size:
                raise forms.ValidationError(
                    f'Los planos no pueden superar los 50MB. Tamaño actual: {archivo.size/(1024*1024):.2f}MB'
                )
        return archivo
