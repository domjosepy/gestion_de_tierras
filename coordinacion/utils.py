# coordinacion/utils.py
from datetime import timedelta


def contar_dias_habiles(inicio, fin):
    """
    Cuenta los días hábiles (lunes a viernes) entre dos fechas (inclusive).
    """
    dias = 0
    dia = inicio
    while dia <= fin:
        if dia.weekday() < 5:  # 0-4 = lunes a viernes
            dias += 1
        dia += timedelta(days=1)
    return dias
