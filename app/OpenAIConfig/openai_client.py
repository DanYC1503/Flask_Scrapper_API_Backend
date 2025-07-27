import os
from flask import current_app
from openai import OpenAI
import re

class OpenAIClient:
    def __init__(self, model="gpt-3.5-turbo-16k"):
        self.model = model
        api_key = current_app.config.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)

    def analyze_sentiment(self, text):
        prompt = (
            f"Clasifica el sentimiento de este texto: '{text}' "
            "como positivo, negativo o neutral, y devuelve solo el sentimiento "
            "y el puntaje entre -1 y 1, separados por coma. Ejemplo: positivo, 0.8"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0
            )
            content = resp.choices[0].message.content.strip()
            print(f"Respuesta de OpenAI: {content}")

            # Intentar extraer con regex: sentimiento y score separados por coma
            match = re.match(r'(positivo|negativo|neutral)\s*,\s*(-?[\d\.]+)', content, re.IGNORECASE)
            if match:
                sentiment = match.group(1).lower()
                score = float(match.group(2))
                return sentiment, score
            else:
                print("No se pudo parsear la respuesta, retorno neutral")
                return 'neutral', 0.0

        except Exception as e:
            print(f"Error al analizar sentimiento: {e}")
            return 'neutral', 0.0
        
    def get_completion(self, prompt, temperature=0.7, max_tokens=1500):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de reputación digital."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            # Corrección clave: acceso por propiedad en lugar de subíndice
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error en OpenAI API: {str(e)}")
            raise