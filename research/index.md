---
title: Research
nav:
  order: 1
  tooltip: Published works
---

# {% include icon.html icon="fa-solid fa-microscope" %}Research

{% include section.html %}

## Latest Research

{% assign latest_citations = site.data.citations | sort: "date" | reverse | slice: 0, 10 %}
{% for citation in latest_citations %}
  {% include citation.html title=citation.title authors=citation.authors publisher=citation.publisher date=citation.date id=citation.id link=citation.link style="rich" %}
{% endfor %}
