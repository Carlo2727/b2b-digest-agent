import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from b2b_digest.config import Config
from b2b_digest.models import DailyDigest, DigestItem, ItemCategory, PriorityLevel, RawItem

logger = logging.getLogger(__name__)


SYSTEM_INSTRUCTION = """
Sei un analista esperto di intelligence commerciale B2B, finanza agevolata e contratti pubblici.
Il tuo obiettivo è analizzare testi grezzi provenienti da fonti istituzionali ed estrarre SOLTANTO opportunità concrete di business, agevolazioni e gare per le imprese italiane.

REGOLE CRITICHE DI FILTRAGGIO ED ESCLUSIONE:
1. SCARTA CATEGORICAMENTE ed IGNORA:
   - Articoli di opinione, saggi, editoriali o commenti generali.
   - Recensioni tecnologiche, annunci generici di prodotto o riflessioni teoriche su AI/software privi di bandi o gare.
   - Notizie di cronaca o politica generale prive di bandi di gara, incentivi o adempimenti normativi vincolanti per le imprese.
   Se un testo appartiene a queste categorie, NON deve comparire nella lista 'items'.

2. INCLUDI NEL DIGEST SOLAMENTE:
   - Bandi di gara e appalti pubblici aperti o in imminente apertura con scadenze.
   - Agevolazioni economiche: contributi a fondo perduto, finanziamenti agevolati, crediti d'imposta (es. Transizione 5.0, PNRR, incentivi MIMIT/Invitalia).
   - Decreti attuativi e normative vincolanti con obblighi e scadenze perentorie per aziende.

3. ASSEGNAZIONE PRIORITÀ:
   - Priorità ALTA: Bandi aperti con budget ingenti (> € 500.000), contributi a fondo perduto elevati, crediti d'imposta diretti o scadenze perentorie.
   - Priorità MEDIA: Bandi settoriali, opportunità per specifiche PMI o novità normative con adempimenti operativi.
   - Priorità BASSA: Aggiornamenti minori o pre-avvisi di gara.

4. CAMPI CHIAVE:
   - 'importo_o_agevolazione': Esplicita chiaramente il beneficio economico (es. 'Fondo perduto fino al 75%', '€ 45.000.000', 'Credito d\\'imposta 45%').
   - 'data_scadenza': Termine perentorio (es. '30/11/2026', 'A sportello dal 15/10/2026', 'Entro 60 giorni').
"""


class GeminiDigestAnalyzer:
    """Invokes Google Gemini Pro with structured Pydantic schema output."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL

    def _build_prompt(self, items: List[RawItem]) -> str:
        """Compose the structured prompt containing all raw items to analyze."""
        formatted_items = []
        for idx, item in enumerate(items, 1):
            formatted_items.append(
                f"--- ITEM #{idx} ---\n"
                f"ID: {item.id}\n"
                f"Fonte: {item.source_name}\n"
                f"Titolo Originale: {item.title}\n"
                f"URL: {item.url}\n"
                f"Data Pubblicazione: {item.published_date or 'N/D'}\n"
                f"Contenuto Grezzo:\n{item.raw_content}\n"
            )

        items_text = "\n".join(formatted_items)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return (
            f"Oggi è il {today_str}. Analizza i seguenti {len(items)} elementi grezzi "
            f"ed estrai un report intelligence B2B strutturato secondo lo schema richiesto.\n\n"
            f"{items_text}"
        )

    def analyze(self, raw_items: List[RawItem]) -> DailyDigest:
        """Send raw items to Gemini Pro and return structured DailyDigest model."""
        if not raw_items:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return DailyDigest(
                date=today_str,
                executive_summary="Nessun nuovo bando o aggiornamento normativo da segnalare per oggi.",
                total_items_analyzed=0,
                items=[],
            )

        prompt = self._build_prompt(raw_items)

        # Attempt to use modern google-genai SDK
        try:
            from google import genai
            from google.genai import types

            logger.info("Connecting to Gemini API using google-genai SDK (Model: %s)", self.model_name)
            client = genai.Client(api_key=self.api_key)

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=DailyDigest,
                    temperature=0.2,
                ),
            )

            if not response.text:
                raise ValueError("Gemini returned empty response text.")

            digest = DailyDigest.model_validate_json(response.text)
            logger.info("Successfully received structured digest with %d items.", len(digest.items))
            return digest

        except ImportError:
            logger.warning(
                "google-genai SDK not installed or failed to import. Falling back to google-generativeai or mock parser."
            )
            return self._fallback_analyze(prompt, raw_items)
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            raise

    def _fallback_analyze(self, prompt: str, raw_items: List[RawItem]) -> DailyDigest:
        """Secondary fallback using google-generativeai SDK if installed."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={"response_mime_type": "application/json"},
            )
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            return DailyDigest.model_validate(data)
        except Exception as e:
            logger.warning("Fallback via google-generativeai also failed: %s. Generating local fallback structure.", e)
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            fallback_items = [
                DigestItem(
                    title=item.title,
                    category=ItemCategory.BANDO_GARA,
                    priority=PriorityLevel.MEDIA,
                    issuer=item.source_name,
                    importo_o_agevolazione="In fase di definizione",
                    data_scadenza="Vedi bando",
                    key_takeaways=[item.raw_content[:150] + "..."],
                    target_audience="Imprese del settore",
                    original_url=item.url,
                    actionable_step="Consultare il link ufficiale per i dettagli.",
                )
                for item in raw_items
            ]
            return DailyDigest(
                date=today_str,
                executive_summary="Digest elaborato in modalità fallback locale.",
                total_items_analyzed=len(fallback_items),
                items=fallback_items,
            )
