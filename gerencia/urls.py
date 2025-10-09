from django.urls import path
from . import views 

app_name = "gerencia"

urlpatterns = [
    path('gerente-dashboard/', views.GerenciaView.as_view(), name='gerente_dashboard'),
    

]