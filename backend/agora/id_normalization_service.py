import re
import unicodedata

class IdNormalizationService:
    @staticmethod
    def normalize_id(s: str) -> str:
        if not s:
            return ""
        # Normalización NFD para separar caracteres de acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        # Reemplazar ñ por n
        s = s.replace('ñ', 'n').replace('Ñ', 'N')
        # Reemplazar caracteres no alfanuméricos por _
        s = re.sub(r'[^a-zA-Z0-9]', '_', s)
        # Convertir a minúsculas
        s = s.lower()
        # Eliminar guiones bajos duplicados
        s = re.sub(r'_+', '_', s)
        # Limpiar extremos
        return s.strip('_')

    @staticmethod
    def build_safe_id(value: str) -> str:
        return IdNormalizationService.normalize_id(value)
