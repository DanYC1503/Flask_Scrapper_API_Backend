from multiprocessing import Pool, cpu_count
from services.cleaner import TextCleaner

def limpiar_texto(text):
    return TextCleaner.clean(text)

def limpiar_comentarios_parallel(lista_comentarios, key='text'):
    """
    Aplica limpieza de texto paralela usando multiprocessing.
    :param lista_comentarios: lista de diccionarios con al menos la clave 'text'
    :return: misma lista, con los textos limpios
    """
    textos_originales = [c[key] for c in lista_comentarios]

    with Pool(processes=cpu_count()) as pool:
        textos_limpios = pool.map(limpiar_texto, textos_originales)

    for i, texto_limpio in enumerate(textos_limpios):
        lista_comentarios[i][key] = texto_limpio

    return lista_comentarios