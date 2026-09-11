import logging
import warnings
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from b2b_digest.models import RawItem
from b2b_digest.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

# Suppress XML-parsed-as-HTML warnings when using html.parser fallback
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class RssFeedScraper(BaseScraper):
    """Scrapes RSS / Atom feeds from institutions, tender boards, and B2B sources."""

    def __init__(self, feed_url: str, source_name: str, max_items: int = 10):
        super().__init__()
        self.feed_url = feed_url
        self.source_name = source_name
        self.max_items = max_items

    def scrape(self) -> List[RawItem]:
        logger.info("Fetching RSS feed: %s (%s)", self.source_name, self.feed_url)
        content = self.fetch(self.feed_url)
        if not content:
            return []

        # 1. First attempt robust standard library XML ElementTree
        items = self._parse_with_element_tree(content)
        if items:
            logger.info("Retrieved %d items from %s (via XML)", len(items), self.source_name)
            return items

        # 2. Fallback to BeautifulSoup HTML parser
        items = self._parse_with_beautifulsoup(content)
        logger.info("Retrieved %d items from %s (via HTML parser)", len(items), self.source_name)
        return items

    def _parse_with_element_tree(self, content: str) -> List[RawItem]:
        results: List[RawItem] = []
        try:
            root = ET.fromstring(content.encode("utf-8") if isinstance(content, str) else content)
            raw_items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for elem in raw_items[: self.max_items]:
                # Title
                title_el = elem.find("title") or elem.find("{http://www.w3.org/2005/Atom}title")
                title = title_el.text.strip() if title_el is not None and title_el.text else "Senza titolo"

                # Link
                url = ""
                link_el = elem.find("link") or elem.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    url = link_el.get("href") or (link_el.text.strip() if link_el.text else "")

                if not url:
                    guid_el = elem.find("guid") or elem.find("id")
                    if guid_el is not None and guid_el.text and guid_el.text.strip().startswith("http"):
                        url = guid_el.text.strip()

                if not url:
                    continue

                # PubDate
                pub_date_el = elem.find("pubDate") or elem.find("published") or elem.find("updated")
                pub_date = pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else None

                # Description / Content
                desc_el = elem.find("description") or elem.find("content") or elem.find("summary")
                raw_text = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                cleaned_text = self.clean_html_text(raw_text)

                item_id = self.generate_item_id(url, title)
                results.append(
                    RawItem(
                        id=item_id,
                        title=title,
                        url=url,
                        published_date=pub_date,
                        source_name=self.source_name,
                        raw_content=cleaned_text or title,
                    )
                )
        except Exception as e:
            logger.debug("ElementTree parse did not succeed for %s (%s). Falling back.", self.source_name, e)

        return results

    def _parse_with_beautifulsoup(self, content: str) -> List[RawItem]:
        results: List[RawItem] = []
        soup = BeautifulSoup(content, "html.parser")
        items = soup.find_all("item") or soup.find_all("entry")

        for tag in items[: self.max_items]:
            title_el = tag.find("title")
            title = title_el.get_text(strip=True) if title_el else "Senza titolo"

            # Handle both standard XML and HTML5-parsed link tags
            link_el = tag.find("link")
            url = ""
            if link_el:
                if link_el.get("href"):
                    url = link_el.get("href").strip()
                elif link_el.get_text(strip=True):
                    url = link_el.get_text(strip=True)
                elif (
                    link_el.next_sibling
                    and isinstance(link_el.next_sibling, str)
                    and link_el.next_sibling.strip().startswith("http")
                ):
                    url = link_el.next_sibling.strip()

            if not url:
                guid_el = tag.find("guid") or tag.find("id")
                if guid_el and guid_el.get_text(strip=True).startswith("http"):
                    url = guid_el.get_text(strip=True)

            if not url:
                continue

            pub_date_el = tag.find("pubdate") or tag.find("published") or tag.find("updated")
            pub_date = pub_date_el.get_text(strip=True) if pub_date_el else None

            desc_el = tag.find("description") or tag.find("content") or tag.find("summary")
            raw_text = desc_el.get_text(strip=True) if desc_el else ""
            cleaned_text = self.clean_html_text(raw_text)

            item_id = self.generate_item_id(url, title)
            results.append(
                RawItem(
                    id=item_id,
                    title=title,
                    url=url,
                    published_date=pub_date,
                    source_name=self.source_name,
                    raw_content=cleaned_text or title,
                )
            )

        return results


class InvitaliaBandiCollector(BaseScraper):
    """Scrapes official Invitalia tenders, grants, and enterprise incentives."""

    INVITALIA_RSS = "https://www.invitalia.it/rss"
    INVITALIA_INCENTIVI_URL = "https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti"

    def scrape(self, max_items: int = 5) -> List[RawItem]:
        logger.info("Collecting from Invitalia News & Bandi...")
        # 1. Try RSS endpoint first
        rss_scraper = RssFeedScraper(self.INVITALIA_RSS, "Invitalia - News & Bandi", max_items=max_items)
        items = rss_scraper.scrape()
        if items:
            return items

        # 2. Resilient fallback to live active incentives portal
        logger.info("RSS feed empty or 404. Scraping Invitalia active incentives portal (%s)...", self.INVITALIA_INCENTIVI_URL)
        html = self.fetch(self.INVITALIA_INCENTIVI_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        collected: List[RawItem] = []
        seen_urls = set()

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "/incentivi-e-strumenti/" in href and not href.endswith("/incentivi-e-strumenti"):
                title = a.get_text(strip=True)
                if not title or len(title) < 5 or title.lower().startswith("leggi tutto"):
                    continue

                full_url = urljoin("https://www.invitalia.it", href.split("?")[0])
                if full_url in seen_urls:
                    continue

                seen_urls.add(full_url)
                item_id = self.generate_item_id(full_url, title)
                collected.append(
                    RawItem(
                        id=item_id,
                        title=f"Incentivo Invitalia: {title}",
                        url=full_url,
                        published_date=None,
                        source_name="Invitalia - Incentivi e Strumenti per le Imprese",
                        raw_content=(
                            f"Misura agevolativa gestita da Invitalia per le imprese: {title}. "
                            f"Offre agevolazioni per investimenti, contributi a fondo perduto e finanziamenti agevolati. "
                            f"Consultare il bando operativo su {full_url}"
                        ),
                    )
                )

                if len(collected) >= max_items:
                    break

        logger.info("Extracted %d active incentives from Invitalia portal.", len(collected))
        return collected


class PublicSourcesCollector:
    """Orchestrates collection exclusively from B2B tender, contract, and incentive sources."""

    DEFAULT_SOURCES = [
        {
            "name": "PMI.it - Finanziamenti & Agevolazioni Imprese",
            "url": "https://www.pmi.it/economia-e-finanza/finanziamenti/feed",
            "type": "rss",
        },
        {
            "name": "ANCE - Appalti Pubblici & Edilizia",
            "url": "https://ance.it/feed/",
            "type": "rss",
        },
        {
            "name": "Il Sole 24 Ore - Norme & Tributi",
            "url": "https://www.ilsole24ore.com/rss/norme-e-tributi.xml",
            "type": "rss",
        },
        {
            "name": "Gazzetta Ufficiale - Contratti Pubblici (5S)",
            "url": "https://www.gazzettaufficiale.it/rss/5S",
            "type": "rss",
        },
    ]

    def __init__(self, custom_sources: Optional[List[dict]] = None):
        self.sources = custom_sources or self.DEFAULT_SOURCES

    def collect(self, limit_per_source: int = 5) -> List[RawItem]:
        """Collect raw items across all configured sources."""
        all_items: List[RawItem] = []

        # 1. Collect from Invitalia (with RSS + active portal fallback)
        try:
            invitalia = InvitaliaBandiCollector()
            all_items.extend(invitalia.scrape(max_items=limit_per_source))
        except Exception as e:
            logger.error("Failed to collect from Invitalia: %s", e)

        # 2. Collect from configured RSS feeds
        for src in self.sources:
            try:
                scraper = RssFeedScraper(
                    feed_url=src["url"],
                    source_name=src["name"],
                    max_items=limit_per_source,
                )
                items = scraper.scrape()
                all_items.extend(items)
            except Exception as e:
                logger.error("Failed to collect from source %s: %s", src.get("name"), e)

        return all_items

    @staticmethod
    def get_sample_items() -> List[RawItem]:
        """Provide realistic sample items for testing or offline dry-runs."""
        return [
            RawItem(
                id="sample-001",
                title="Bando PNRR Transizione 5.0 - Digitalizzazione e Risparmio Energetico PMI",
                url="https://www.mimit.gov.it/it/incentivi/transizione-5-0",
                published_date="2026-09-10",
                source_name="Ministero delle Imprese e del Made in Italy",
                raw_content=(
                    "Il MIMIT ha pubblicato il decreto direttoriale recante le modalità operative per "
                    "l'accesso al credito d'imposta per la Transizione 5.0. Sono previsti 6,3 miliardi "
                    "di euro destinati alle imprese di qualsiasi dimensione residenti in Italia che investono "
                    "in software, sistemi IoT, efficienza energetica e formazione del personale. Agevolazioni "
                    "fino al 45% delle spese ammissibili. Apertura domande a sportello telematico dal 15 ottobre."
                ),
            ),
            RawItem(
                id="sample-002",
                title="Procedura Aperta: Affidamento Servizi Cloud e Cybersecurity per Pubbliche Amministrazioni",
                url="https://www.acquistinretepa.it/bandi/gara-cloud-cyber-2026",
                published_date="2026-09-09",
                source_name="Consip / AcquistinretePA",
                raw_content=(
                    "Bando di gara a procedura aperta per l'attivazione di un Accordo Quadro avente a oggetto "
                    "la prestazione di servizi di migrazione cloud sicura, SOC as a Service e vulnerability "
                    "management per gli enti locali e le PA centrali. Base d'asta complessiva pari a 45.000.000 € "
                    "suddivisa in 4 lotti geografici. Scadenza presentazione offerte: 30 novembre 2026, ore 12:00. "
                    "Requisiti minimi: certificazione ISO 27001 e fatturato specifico triennale."
                ),
            ),
            RawItem(
                id="sample-003",
                title="Novità Normativa: Nuove regole su fatturazione elettronica transfrontaliera e Whistleblowing B2B",
                url="https://www.gazzettaufficiale.it/atto/normativa-b2b-2026",
                published_date="2026-09-08",
                source_name="Gazzetta Ufficiale della Repubblica Italiana",
                raw_content=(
                    "Pubblicato in Gazzetta Ufficiale il decreto legislativo di recepimento della direttiva UE "
                    "sui requisiti di compliance digitale per i contratti interaziendali transfrontalieri. Le "
                    "società con oltre 50 dipendenti o con contratti verso la PA hanno 60 giorni per adeguare "
                    "le piattaforme di scambio dati e i canali interni di conformità fiscale e procedurale."
                ),
            ),
        ]
