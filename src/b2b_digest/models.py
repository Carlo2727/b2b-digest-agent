from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RawItem(BaseModel):
    """Raw data scraped from a public source before LLM analysis."""
    id: str
    title: str
    url: str
    published_date: Optional[str] = None
    source_name: str
    raw_content: str


class ItemCategory(str, Enum):
    BANDO_GARA = "BANDO_GARA"
    NOVITA_NORMATIVA = "NOVITA_NORMATIVA"
    AGEVOLAZIONE_FISCALE = "AGEVOLAZIONE_FISCALE"
    OPPORTUNITA_MERCATO = "OPPORTUNITA_MERCATO"
    ALTRO = "ALTRO"


class PriorityLevel(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BASSA = "BASSA"


class DigestItem(BaseModel):
    """Structured extraction of a single B2B tender or regulatory notice."""
    title: str = Field(
        description="Titolo sintetico e chiaro dell'opportunità o novità normativa."
    )
    category: ItemCategory = Field(
        description="Categoria tematica dell'elemento."
    )
    priority: PriorityLevel = Field(
        description="Livello di priorità/impatto per le imprese (ALTA, MEDIA, BASSA)."
    )
    issuer: Optional[str] = Field(
        default=None,
        description="Ente pubblico, ministero o stazione appaltante che ha emanato l'atto o gestisce l'incentivo."
    )
    importo_o_agevolazione: Optional[str] = Field(
        default=None,
        description="Importo a base d'asta, dotazione o forma di agevolazione (es. 'Fondo perduto fino al 70%', '€ 1.200.000', 'Credito d\\'imposta 45%')."
    )
    data_scadenza: Optional[str] = Field(
        default=None,
        description="Data di scadenza o modalità di apertura (es. '30/11/2026', 'A sportello fino a esaurimento fondi')."
    )
    key_takeaways: List[str] = Field(
        description="Esattamente 2 o 3 punti elenco essenziali: oggetto, requisiti o novità rilevanti."
    )
    target_audience: str = Field(
        description="Destinatari target aziendali (es. 'PMI Digitali & ICT', 'Settore Edile', 'Tutte le imprese')."
    )
    original_url: str = Field(
        description="Link URL alla fonte ufficiale o scheda bando."
    )
    actionable_step: str = Field(
        description="Azione immediata consigliata per l'azienda (es. 'Iscriversi alla piattaforma telematica entro il 10 Ottobre')."
    )


class DailyDigest(BaseModel):
    """Aggregated structured digest produced by Gemini."""
    date: str = Field(
        description="Data di generazione del digest in formato YYYY-MM-DD."
    )
    executive_summary: str = Field(
        description="Breve sommario esecutivo (2-3 frasi) delle tendenze e opportunità del giorno."
    )
    total_items_analyzed: int = Field(
        description="Numero totale di elementi analizzati ed inclusi."
    )
    items: List[DigestItem] = Field(
        default_factory=list,
        description="Lista ordinata degli elementi strutturati, prioritizzando quelli ad alta rilevanza."
    )
