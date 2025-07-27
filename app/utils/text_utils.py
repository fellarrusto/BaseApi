import re

def clean_text(text: str, max_word_length: int = 30, max_nonalpha_ratio: float = 0.4) -> str:

    # Rimuove solo trattini di sillabazione su newline
    text = re.sub(r'(?<=\w)-\n(?=\w)', '', text)
    text = text.replace('\n', ' ').replace('\r', ' ')

    # Inserisce spazio dopo lettere accentate se seguite da lettera o numero
    text = re.sub(r'([\u00E0\u00E8\u00E9\u00EC\u00F2\u00F9])(\w)', r'\1 \2', text)

    # Inserisce spazio prima delle lettere maiuscole
    text = re.sub(r'(?<=[a-zàèéìòù])(?=[A-Z])', r' ', text)

    # Inserisce spazio tra lettere e numeri
    text = re.sub(r'(?<=[a-zàèéìòùA-Z])(?=\d)', r' ', text)
    text = re.sub(r'(?<=\d)(?=[a-zàèéìòùA-Z])', r' ', text)

    cleaned_text = re.sub(r"[^\w\s.,!?;:'àèéìòù]", '', text, flags=re.UNICODE)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = cleaned_text.lower()
    
    clean_text = clean_text.replace("scanned by cam scanner", "")

    # Rimuove parole troppo lunghe o con troppi caratteri non alfabetici
    def is_valid(word):
        if len(word) > max_word_length:
            return False
        nonalpha = sum(1 for c in word if not c.isalpha())
        return (nonalpha / len(word)) <= max_nonalpha_ratio

    cleaned_text = ' '.join(word for word in cleaned_text.split() if is_valid(word))

    return cleaned_text