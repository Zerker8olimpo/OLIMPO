import statistics
from typing import List, Dict, Any

class OutlierFilter:
    """
    TAREA 6: Filtro de outliers para precios de mercado.
    Elimina precios que se desvían demasiado de la mediana para evitar contaminantes.
    """
    
    def filter_price_outliers(
        self,
        observations: List[Dict[str, Any]],
        min_samples: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Filtra observaciones basadas en la mediana.
        """
        if len(observations) < min_samples:
            # Si hay pocas muestras, no filtramos pero marcamos como baja confianza
            return observations
            
        prices = [obs["normalized_unit_price"] for obs in observations]
        median_price = statistics.median(prices)
        
        if median_price <= 0:
            return observations
            
        valid_observations = []
        
        # Umbrales: 0.25x a 4.0x la mediana
        # (Esto permite captar variaciones reales pero excluye errores de carga o packs mal detectados)
        lower_bound = median_price * 0.25
        upper_bound = median_price * 4.0
        
        for obs in observations:
            p = obs["normalized_unit_price"]
            if lower_bound <= p <= upper_bound:
                valid_observations.append(obs)
                
        # Si el filtro eliminó TODO (caso raro), devolvemos el original para no quedar en cero
        if not valid_observations:
            return observations
            
        return valid_observations
