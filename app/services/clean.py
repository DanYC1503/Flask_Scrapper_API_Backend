import re
import unicodedata

def remove_emojis(text):
    # Elimina caracteres que no son letra, número, puntuación estándar
    return text.encode('ascii', 'ignore').decode('ascii')

def clean_text(text):
    if not text:
        return ""

    # Eliminar emojis y caracteres no ASCII
    text = remove_emojis(text)

    # Pasar a minúsculas
    text = text.lower()

    # Eliminar enlaces en formato markdown: [texto](url)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)

    # Eliminar URLs comunes (http, https, www)
    text = re.sub(r'http\S+|www\.\S+|\S+\.com\S*|\S+\.org\S*|\S+\.net\S*', '', text, flags=re.IGNORECASE)

    # Eliminar cualquier otro patrón tipo dominio
    text = re.sub(r'\S+\.(io|co|ai|tv|gov|edu)\S*', '', text, flags=re.IGNORECASE)

    # Eliminar caracteres no alfanuméricos innecesarios (excepto .,!?-)
    text = re.sub(r"[^a-z0-9\s\.\,\!\?\-]", '', text)

    # Eliminar espacios múltiples
    text = re.sub(r"\s+", ' ', text)

    return text.strip()