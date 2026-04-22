"""
Fetch recent publications for RIIPL lab members from PubMed.

Each member has a PubMed query tuned to avoid same-initials collisions:

- Strict ``LastName + Initials`` forms (e.g. ``Whitlow CT``) when available,
  because PubMed normalizes authors to that form and it excludes unrelated
  people who share a last name + first initial (e.g. Clysha "Whitlow C").
- ORCID ``[AUID]`` when we have it, as a safety net for papers where the
  initials were recorded slightly differently.
- ``Wake Forest`` or ``Yale`` affiliation filters for lab members whose
  names are common enough to collide with other researchers (anyone other
  than Whitlow).

Results are capped to the last 5 years. The file is regenerated from scratch
on every run, so removing a member here also removes their older papers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen
import json
import re
import time
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_data" / "citations.yaml"

# Rolling window: only keep papers published in the last N years.
YEARS_BACK = 5

# Common institutional filter. Applied inside each non-Whitlow PubMed query
# (Whitlow's ``Whitlow CT`` + ORCID combo is already precise enough that
# a query-time filter would just miss preprints without affiliation data).
AFFIL_FILTER = '(Wake Forest[Affiliation] OR Yale[Affiliation])'

# Post-fetch institutional check: every paper must have "Wake Forest" or
# "Yale" somewhere in its parsed affiliations. Papers with no affiliation
# data at all (typically bioRxiv / medRxiv preprints, which PubMed does
# not ingest affiliations for) bypass this check.
AFFIL_RE = re.compile(r"wake\s*forest|yale", re.IGNORECASE)

# Per-member PubMed queries + an author-name regex that the parsed author
# list must match for the paper to be retained. The regex is the last line
# of defense against same-initial collisions that slip through PubMed's
# normalization (e.g. "Lyu Q" matching both "Qing Lyu" and "Qiang Lyu",
# or papers that match an affiliation but where the target author isn't
# actually on the byline).
#
# Regexes are matched case-insensitively against each raw author string
# from the PubMed record (which can be either "C T Whitlow" or
# "Christopher T Whitlow" depending on what the journal provided).
MEMBERS: list[dict[str, str]] = [
    {
        "name": "Christopher Whitlow",
        "query": "Whitlow CT[Author] OR 0000-0003-2392-8293[AUID]",
        # Whitlow CT query already excludes "Clysha Whitlow", so a plain
        # last-name match is safe here and catches both "C Whitlow" and
        # "Christopher T Whitlow" renderings.
        "author_regex": r"\bwhitlow\b",
    },
    {
        "name": "Qing Lyu",
        "query": f"(Lyu Q[Author] OR 0000-0002-9824-0170[AUID]) AND {AFFIL_FILTER}",
        # Require the given name "Qing" to exclude "Qiang Lyu" namesakes.
        "author_regex": r"\bqing\b.*\blyu\b|\blyu\b.*\bqing\b",
    },
    {
        "name": "Kevin Yu",
        "query": f"Yu KC[Author] AND {AFFIL_FILTER}",
        # Require "Kevin" alongside the "Yu" surname; excludes unrelated
        # Yu K / Yu KC / Yu KM authors at Yale and Wake Forest.
        "author_regex": r"\bkevin\b.*\byu\b",
    },
    {
        "name": "Mohammad Kawas",
        "query": f"Kawas MI[Author] AND {AFFIL_FILTER}",
        "author_regex": r"\bmohammad\b.*\bkawas\b",
    },
]

# Generous per-member cap; none of our members are close to this in 5 years.
RETMAX = 500


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def get_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_xml(url: str) -> ET.Element:
    with urlopen(url) as response:
        return ET.fromstring(response.read())


def date_cutoff() -> str:
    """YYYY/MM/DD string for ``now - YEARS_BACK`` in UTC."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * YEARS_BACK)
    return cutoff.strftime("%Y/%m/%d")


def search_pmids_for(query: str) -> list[str]:
    """Run a single PubMed esearch query, returning a list of PMIDs."""
    full = f"({query}) AND (\"{date_cutoff()}\"[PDAT] : \"3000\"[PDAT])"
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&retmode=json&sort=pub+date&retmax={RETMAX}"
        f"&term={quote_plus(full)}"
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
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
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
    title_node = article.find("ArticleTitle")
    title = "".join(title_node.itertext()) if title_node is not None else ""
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

    affiliations: list[str] = []
    for aff in article.findall(".//AffiliationInfo/Affiliation"):
        text = "".join(aff.itertext())
        text = clean(text)
        if text:
            affiliations.append(text)

    citation = {
        "id": f"pubmed:{pmid}",
        "title": clean(title),
        "authors": authors,
        "publisher": journal,
        "date": format_date(article),
        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "plugin": "pubmed-direct.py",
        "file": "pubmed.yaml",
        # Not written to YAML; used for post-fetch filtering below.
        "_affiliations": affiliations,
    }
    if doi:
        citation["doi"] = doi
    return citation


def fetch_citations(pmids: list[str]) -> list[dict]:
    """Fetch article metadata in batches (PubMed efetch caps around 200)."""
    if not pmids:
        return []

    batch_size = 200
    citations: list[dict] = []
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start:start + batch_size]
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&retmode=xml&id={','.join(batch)}"
        )
        root = get_xml(url)
        for article in root.findall("PubmedArticle"):
            parsed = parse_article(article)
            if parsed:
                citations.append(parsed)
        time.sleep(0.4)
    return citations


def write_yaml(citations: list[dict]) -> None:
    yaml.Dumper.ignore_aliases = lambda *args: True
    body = yaml.dump(citations, default_flow_style=False, sort_keys=False, allow_unicode=True)
    OUTPUT.write_text("# DO NOT EDIT, GENERATED AUTOMATICALLY\n\n" + body, encoding="utf-8")


def pmids_by_member() -> dict[str, set[str]]:
    """Run every member's query and return ``{member_name: {pmids}}``."""
    result: dict[str, set[str]] = {}
    for member in MEMBERS:
        pmids = search_pmids_for(member["query"])
        result[member["name"]] = set(pmids)
        print(f"  {member['name']:<22} {len(pmids):>3} candidate PMIDs")
        time.sleep(0.4)
    return result


def is_author_confirmed(citation: dict, owner_names: set[str]) -> bool:
    """True iff at least one owner's author-regex matches an author string."""
    authors_blob = " | ".join(citation.get("authors", [])).lower()
    for member in MEMBERS:
        if member["name"] not in owner_names:
            continue
        if re.search(member["author_regex"], authors_blob, flags=re.IGNORECASE):
            return True
    return False


def main() -> None:
    print(f"Fetching papers published since {date_cutoff()} for:")
    for m in MEMBERS:
        print(f"  - {m['name']}")
    print()

    per_member = pmids_by_member()
    owners: dict[str, set[str]] = {}
    for name, pmids in per_member.items():
        for pmid in pmids:
            owners.setdefault(pmid, set()).add(name)
    all_pmids = list(owners.keys())
    print(f"\nTotal unique PMIDs across members: {len(all_pmids)}")

    citations = fetch_citations(all_pmids)

    # Strip any paper that fell outside the window because PubMed returned an
    # imprecise MedlineDate like "2020 Summer".
    cutoff = date_cutoff().replace("/", "-")
    citations = [c for c in citations if c.get("date", "") >= cutoff]

    # Drop namesakes that passed the initial esearch but don't actually have
    # one of our members in the byline.
    confirmed, name_rejected = [], []
    for c in citations:
        pmid = c["id"].split(":", 1)[-1]
        if is_author_confirmed(c, owners.get(pmid, set())):
            confirmed.append(c)
        else:
            name_rejected.append(c)

    if name_rejected:
        print(f"\nDropping {len(name_rejected)} paper(s) with no matching author name:")
        for c in name_rejected:
            print(f"  - {c['id']}: {c['title'][:80]}")

    # Institutional check: at least one affiliation must mention Wake Forest
    # or Yale. Preprints / records with empty affiliation data get the
    # benefit of the doubt (PubMed strips affiliations on bioRxiv records).
    affiliated, aff_rejected = [], []
    for c in confirmed:
        affs = c.get("_affiliations") or []
        if not affs or any(AFFIL_RE.search(a) for a in affs):
            affiliated.append(c)
        else:
            aff_rejected.append(c)

    if aff_rejected:
        print(f"\nDropping {len(aff_rejected)} paper(s) with no Wake Forest / Yale affiliation:")
        for c in aff_rejected:
            print(f"  - {c['id']}: {c['title'][:80]}")

    # Strip the private affiliations key before writing.
    for c in affiliated:
        c.pop("_affiliations", None)

    affiliated.sort(key=lambda c: c.get("date") or "", reverse=True)
    write_yaml(affiliated)
    print(f"\nWrote {len(affiliated)} citations to {OUTPUT}")


if __name__ == "__main__":
    main()
