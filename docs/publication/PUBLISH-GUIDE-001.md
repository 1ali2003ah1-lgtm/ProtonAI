# PUBLISH-GUIDE-001: Pages + Zenodo DOI
## 1. Pages
gh api repos/1ali2003ah1-lgtm/ProtonAI/pages -X POST -f build_type=workflow || true
git push
## 2. Zenodo
zenodo.org -> GitHub -> enable repo -> create Release v0.9.0 -> DOI minted.
