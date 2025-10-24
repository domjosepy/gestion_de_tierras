from django import forms
from .models import Departamento, Distrito, Colonia, Solicitud, Relevamiento


class DistritoForm(forms.ModelForm):
    class Meta:
        model = Distrito
        fields = ['nombre', 'departamento']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'departamento': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.all()


class ColoniaForm(forms.ModelForm):
    distritos = forms.ModelMultipleChoiceField(
        queryset=Distrito.objects.all(),
        widget=forms.SelectMultiple(
            attrs={'class': 'form-control form-control-glow'}),
        required=True
    )

    class Meta:
        model = Colonia
        fields = ['nombre', 'distritos', 'estado',
                  'finca_matriz', 'padron_matriz']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-glow'}),
            'estado': forms.Select(attrs={'class': 'form-control form-control-glow'}),
            'finca_matriz': forms.TextInput(attrs={'class': 'form-control form-control-glow'}),
            'padron_matriz': forms.TextInput(attrs={'class': 'form-control form-control-glow'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar los distritos por nombre para mejor UX
        self.fields['distritos'].queryset = Distrito.objects.select_related(
            'departamento').order_by('nombre')


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ["colonia", "tipo", "observaciones"]

    def clean(self):
        cleaned = super().clean()
        # Ejecutar validaciones del modelo (duplicados)
        obj = Solicitud(**cleaned)
        # Si hay error, pasarlo al formulario
        try:
            obj.full_clean()
        except Exception as e:
            raise forms.ValidationError(e)
        return cleaned
