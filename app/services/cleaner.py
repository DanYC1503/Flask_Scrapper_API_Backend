import re
import unicodedata

class TextCleaner:
    @staticmethod
    def to_lowercase(text):
        return text.lower()

    @staticmethod
    def remove_emojis(text):
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002500-\U00002BEF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001f926-\U0001f937"
            u"\U00010000-\U0010ffff"
            u"\u2640-\u2642"
            u"\u2600-\u2B55"
            u"\u200d"
            u"\u23cf"
            u"\u23e9"
            u"\u231a"
            u"\ufe0f"
            u"\u3030"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)

    @staticmethod
    def remove_accents(text):
        return ''.join(
            c for c in unicodedata.normalize('NFKD', text)
            if not unicodedata.combining(c)
        )

    @staticmethod
    def remove_special_chars(text):
        return re.sub(r'[^\w\s]', '', text)

    @classmethod
    def clean(cls, text):
        text = cls.to_lowercase(text)
        text = cls.remove_emojis(text)
        text = cls.remove_accents(text)
        text = cls.remove_special_chars(text)
        return text.strip()