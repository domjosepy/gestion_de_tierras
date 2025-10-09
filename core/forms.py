from django import forms
from .models import Distrito, Colonia, Solicitud, Relevamiento


class DistritoForm(forms.ModelForm):
    class Meta:
        model = Distrito
        fields = ["nombre", "departamento"]

    def clean_departamento(self):
        dept = self.cleaned_data.get("departamento")
        if not dept:
            raise forms.ValidationError("El distrito debe estar vinculado a un departamento.")
        return dept
    
class ColoniaForm(forms.ModelForm):
    class Meta:
        model = Colonia
        fields = ["nombre", "distritos", "estado"]

    def clean_distritos(self):
        distritos = self.cleaned_data.get("distritos")
        if not distritos or distritos.count() == 0:
            raise forms.ValidationError("La colonia debe estar asociada a al menos un distrito.")
        return distritos



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
 
    
