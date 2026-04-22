"""
Fetch the latest Christopher Whitlow papers from PubMed and write citations.yaml.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen
import json
import re
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_data" / "citations.yaml"
RETMAX = 10
QUERY = (
    '"Christopher T Whitlow"[Author] OR '
    '"Christopher Whitlow"[Author] OR '
    '"Whitlow CT"[Author] OR '
    '"Whitlow C"[Author]'
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def get_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_xml(url: str) -> ET.Element:
    with urlopen(url) as response:
        return ET.fromstring(response.read())


def search_pmids() -> list[str]:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&retmode=json&sort=pub+date&retmax={RETMAX}"
        f"&term={quote_plus(QUERY)}"
    )
    data = get_json(url)
    return data.get("esearchresult", {}).get("idlist", [])


def format_date(article: ET.Element) -> str:
    pub_date = article.find(".//PubDate")
    if pub_date is None:
        return ""

    year = clean(pub_date.findtext("Year"))
    medline_date = clean(pub_date.findtext("MedlineDate"))
    if not year and medline_date:
        match = re.search(r"(19|20)\d{2}", medline_date)
        year = match.group(0) if match else ""
    if not year:
        return ""

    month_text = clean(pub_date.findtext("Month"))
    day = clean(pub_date.findtext("Day")) or "01"
    month_lookup = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    month = month_lookup.get(month_text[:3].lower(), "01") if month_text else "01"
    day = day.zfill(2)
    return f"{year}-{month}-{day}"


def parse_article(pubmed_article: ET.Element) -> dict:
    medline = pubmed_article.find("MedlineCitation")
    article = medline.find("Article") if medline is not None else None
    if medline is None or article is None:
        return {}

    pmid = clean(medline.findtext("PMID"))
    title = "".join(article.find("ArticleTitle").itertext()) if article.find("ArticleTitle") is not None else ""
    journal = clean(article.findtext("Journal/Title"))

    authors = []
    for author in article.findall("AuthorList/Author"):
        collective = clean(author.findtext("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        given = clean(author.findtext("ForeName"))
        family = clean(author.findtext("LastName"))
        name = clean(f"{given} {family}")
        if name:
            authors.append(name)

    doi = ""
    for article_id in pubmed_article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            doi = clean(article_id.text or "")
            break

    citation = {
        "id": f"pubmed:{pmid}",
        "title": clean(title),
        "authors": authors,
        "publisher": journal,
        "date": format_date(article),
        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "plugin": "pubmed-direct.py",
        "file": "pubmed.yaml",
    }
    if doi:
        citation["doi"] = doi
    return citation


def fetch_citations(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&retmode=xml&id={','.join(pmids)}"
    )
    root = get_xml(url)
    citations = []
    for article in root.findall("PubmedArticle"):
        citation = parse_article(article)
        if citation:
            citations.append(citation)

    pmid_order = {pmid: index for index, pmid in enumerate(pmids)}
    citations.sort(key=lambda c: pmid_order.get(c["id"].split(":")[-1], 9999))
    return citations


def write_yaml(citations: list[dict]) -> None:
    yaml.Dumper.ignore_aliases = lambda *args: True
    body = yaml.dump(citations, default_flow_style=False, sort_keys=False, allow_unicode=True)
    OUTPUT.write_text("# DO NOT EDIT, GENERATED AUTOMATICALLY\n\n" + body, encoding="utf-8")


def main() -> None:
    pmids = search_pmids()
    citations = fetch_citations(pmids)
    write_yaml(citations)
    print(f"Wrote {len(citations)} PubMed citations to {OUTPUT}")


if __name__ == "__main__":
    main()
