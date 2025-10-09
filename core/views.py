from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Departamento, Distrito, Colonia 
from .forms import ColoniaForm, DistritoForm
from django.contrib.auth.mixins import LoginRequiredMixin


class ColoniaListView(LoginRequiredMixin, ListView):
    model = Colonia
    paginate_by = 25
    template_name = "gerencia/colonias_list.html"
    context_object_name = "colonias"

    def get_queryset(self):
        qs = Colonia.objects.prefetch_related("distritos").all()
        q = self.request.GET.get("q")
        estado = self.request.GET.get("estado")
        distrito = self.request.GET.get("distrito")
        if q:
            qs = qs.filter(nombre__icontains=q)
        if estado:
            qs = qs.filter(estado=estado)
        if distrito:
            qs = qs.filter(distritos__id=distrito)
        return qs.distinct()
#Crear colonia
class ColoniaCreateView(LoginRequiredMixin, CreateView):
    model = Colonia
    form_class = ColoniaForm
    template_name = "gerencia/colonia_form.html"
    success_url = reverse_lazy("gerencia:colonias_list")

#Editar colonia
class ColoniaUpdateView(LoginRequiredMixin, UpdateView):
    model = Colonia
    form_class = ColoniaForm
    template_name = "gerencia/colonia_form.html"
    success_url = reverse_lazy("gerencia:colonias_list")

#Eliminar colonia
class ColoniaDeleteView(LoginRequiredMixin, DeleteView):
    model = Colonia
    template_name = "gerencia/colonia_confirm_delete.html"
    success_url = reverse_lazy("gerencia:colonias_list")