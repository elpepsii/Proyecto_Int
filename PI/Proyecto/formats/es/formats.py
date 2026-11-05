"""
Formatos para español de Chile (LANGUAGE_CODE = 'es' + FORMAT_MODULE_PATH).

El locale 'es' genérico de Django separa los miles con un espacio fino
("18 990"); en Chile los precios CLP se escriben con punto ("18.990").
Solo sobrescribimos lo que difiere; fechas y demás heredan el formato 'es'.
"""

THOUSAND_SEPARATOR = '.'
