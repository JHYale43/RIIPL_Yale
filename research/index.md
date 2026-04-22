---
title: Research
nav:
  order: 1
  tooltip: Published works
---

# {% include icon.html icon="fa-solid fa-microscope" %}Research

{% include section.html %}

## Publications

{% assign sorted_citations = site.data.citations | sort: "date" | reverse %}
{% assign current_year = "" %}
{% for citation in sorted_citations -%}
{% assign citation_year = citation.date | slice: 0, 4 -%}
{% if citation_year != current_year %}

### {{ citation_year }}

{% assign current_year = citation_year -%}
{% endif -%}
{% include citation.html title=citation.title authors=citation.authors publisher=citation.publisher date=citation.date id=citation.id link=citation.link style="rich" %}
{% endfor %}
