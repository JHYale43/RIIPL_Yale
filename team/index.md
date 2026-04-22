---
title: Team
nav:
  order: 3
  tooltip: About our team
---

# {% include icon.html icon="fa-solid fa-users" %}Team

Meet the remarkable minds behind RIIPL, a diverse team of multi-disciplinary talents dedicated to research and development in medical imaging. Each member brings a unique set of skills and insights, driving innovation and excellence in our work.

<blockquote>
"The strength of the team is each individual member. The strength of each member is the team."
</blockquote>

{% include section.html %}

{% include list.html data="members" component="portrait" filters="role: pi" %}
{% include list.html data="members" component="portrait" filters="role: ^(?!pi$)" %}

