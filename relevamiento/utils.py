import os
import re
import unicodedata


def limpiar_nombre_carpeta(valor):
    """Devuelve una versión 'segura' de `valor` para usar en nombres de archivo.

    - Quita acentos y la ñ (á → a, ñ → n).
    - Pasa todo a minúsculas.
    - Reemplaza espacios y guiones por guion bajo.
    - Elimina cualquier caracter que no sea letra, número o guion bajo.
    - Colapsa guiones bajos repetidos.
    - Si queda vacío, devuelve 'sin_dato'.
    """
    if valor is None:
        return 'sin_dato'

    valor = str(valor).strip()
    if not valor:
        return 'sin_dato'

    # 1) Normalizar Unicode: á → a + combining, ñ → n + combining
    valor = unicodedata.normalize('NFKD', valor)
    # 2) Quitar los "combining marks" (tildes, diéresis, etc.)
    valor = valor.encode('ascii', 'ignore').decode('ascii')

    # 3) Minúsculas
    valor = valor.lower()

    # 4) Espacios y guiones → guion bajo
    valor = re.sub(r'[\s\-]+', '_', valor)

    # 5) Solo letras, números y guion bajo
    valor = re.sub(r'[^a-z0-9_]', '', valor)

    # 6) Colapsar guiones bajos repetidos y limpiar extremos
    valor = re.sub(r'_+', '_', valor).strip('_')

    return valor or 'sin_dato'


def extension_segura(nombre_original, default='.jpg'):
    """Devuelve la extensión en minúsculas del archivo, o `default` si no tiene."""
    ext = os.path.splitext(nombre_original or '')[1].lower()
    return ext if ext else default