# Estância Safra — estanciasafra.com.br

Site gerado por `site-src/build.py` a partir de `site-src/fatos.json` (fonte única de preços, estoque e IDs).

## Publicar
1. Mude o que precisar em `site-src/fatos.json` (ou no `build.py` / `site.css`).
2. `python3 site-src/build.py` e confira em `site/` (preview local: `python3 -m http.server 4173 --directory site`).
3. `git commit` e `git push` na `main`: o GitHub Actions gera o site e o SeeDropHost publica direto no ar.
   Depois, o fluxo IndexNow avisa Bing e outros buscadores das URLs do sitemap.

## Medição e buscadores
- Google Analytics 4: conta "Estância Safra", propriedade "estanciasafra.com.br", ID `G-EWY218YNBN`.
- Google Search Console: propriedade `https://estanciasafra.com.br/` (meta tag + Google Analytics).
- Bing Webmaster Tools: `https://estanciasafra.com.br/` (meta `msvalidate.01` + `BingSiteAuth.xml`).
- IndexNow: chave em `fatos.json` → `verificacao.indexnow_chave`, arquivo `/<chave>.txt`.

## Depois do primeiro push (uma vez só)
- Search Console: verificada (meta tag + GA) e `sitemap.xml` enviado.
- Bing Webmaster: verificado (`BingSiteAuth.xml`) e `sitemap.xml` enviado.
- GA4: em Administrador › Eventos, marcar `generate_lead` como evento principal quando ele aparecer.
