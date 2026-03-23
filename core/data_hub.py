
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional


class DataHub:
    
    def __init__(self):
        self._predictor = None
        self._predictor_loaded = False
    
    
    def get_alloy(self, name: str) -> Optional[dict]:
        from core.alloy_db import lookup_alloy
        return lookup_alloy(name)
    
    def search_alloys(self, query: str) -> list:
        from core.alloy_db import search_alloys
        return search_alloys(query)
    
    def list_all_alloys(self) -> list:
        from core.alloy_db import ALLOY_DATABASE
        return list(ALLOY_DATABASE.keys())
    
    
    def get_element(self, symbol: str):
        from core.elements import get
        return get(symbol)
    
    def get_element_property(self, symbol: str, prop: str):
        el = self.get_element(symbol)
        return getattr(el, prop, None)
    
    
    def predict_properties(self, composition: dict) -> dict:
        if not self._predictor_loaded:
            try:
                from ml.predict import get_predictor
                self._predictor = get_predictor()
            except Exception:
                self._predictor = None
            self._predictor_loaded = True
        
        if self._predictor and self._predictor.is_available():
            try:
                return self._predictor.predict(composition)
            except Exception:
                return {}
        return {}
    
    
    def search_papers(self, query: str, n_results: int = 5) -> list:
        try:
            from rag.retriever import retrieve, rag_available
            if rag_available():
                return retrieve(query, n_results=n_results)
        except Exception:
            pass
        return []
    
    
    def web_lookup(self, query: str) -> dict:
        try:
            from web.scraper import web_lookup
            return web_lookup(query)
        except Exception:
            return {"found": False}
    
    
    def search(self, query: str) -> dict:
        return {
            "alloy_matches": self.search_alloys(query),
            "papers": self.search_papers(query),
            "web": self.web_lookup(query),
        }
    
    
    ELEMENT_PRICES = {
        "Fe": 0.5, "C": 0.3, "Mn": 2.0, "Si": 2.5, "Cr": 9.0,
        "Ni": 16.0, "Mo": 40.0, "V": 30.0, "W": 35.0, "Co": 55.0,
        "Ti": 10.0, "Al": 2.5, "Cu": 8.0, "Nb": 45.0, "Zr": 35.0,
        "Ta": 150.0, "Hf": 600.0, "Re": 3000.0, "Mg": 3.0,
        "Zn": 2.5, "Sn": 25.0, "N": 1.0, "B": 5.0,
        "Ce": 8.0, "La": 6.0, "Y": 35.0, "Nd": 80.0,
    }
    
    def estimate_cost(self, composition_wt: dict) -> Optional[float]:
        cost = 0.0
        total_w = 0.0
        for sym, frac in composition_wt.items():
            price = self.ELEMENT_PRICES.get(sym, 20.0)
            cost += frac * price
            total_w += frac
        
        if total_w < 0.01:
            return None
        return cost / total_w


_hub = None

def get_hub() -> DataHub:
    global _hub
    if _hub is None:
        _hub = DataHub()
    return _hub
