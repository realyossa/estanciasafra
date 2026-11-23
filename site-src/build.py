#!/usr/bin/env python3
"""Gera o site da Safra em ../site a partir de fatos.json. Uso: python3 site-src/build.py"""
import json, re, shutil, sys, hashlib
from pathlib import Path
from urllib.parse import quote
from html import escape

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / "site"
F = json.loads((SRC / "fatos.json").read_text(encoding="utf-8"))
VER = hashlib.sha1((SRC / "site.css").read_bytes() + (SRC / "site.js").read_bytes()).hexdigest()[:8]

DOM = F["dominio"].rstrip("/")
NOME, MARCA, CID, UF = F["nome"], F["marca"], F["cidade"], F["uf"]
LOCAL = f"{CID} ({UF})"
ZAP = F["whatsapp"]
S, P = F["silagem"], F["presecado"]
RAIO = F["raio_km"]
MESES = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
a, m, d = F["atualizado_em"].split("-")
DATA = f"{int(d)} de {MESES[int(m)-1]} de {a}"


def data_br(iso):
    aa, mm, dd = iso.split("-")
    return f"{int(dd)} de {MESES[int(mm)-1]} de {aa}"

MESANO = f"{MESES[int(m)-1]} de {a}"


def br(n, casas=0):
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


T = br(S["toneladas"])                      # 1.400
PT = br(S["preco_tonelada"])                # 500
PKG = br(S["preco_tonelada"] / 1000, 2)     # 0,50
PB = br(P["preco_bola"])                    # 400
KG = br(P["peso_bola_kg"])                  # 400
KMIN, KMAX = P["peso_bola_kg"] - P["variacao_kg"], P["peso_bola_kg"] + P["variacao_kg"]
PKG_MIN = br(P["preco_bola"] / KMAX, 2)     # 0,89
PKG_MAX = br(P["preco_bola"] / KMIN, 2)     # 1,14
CIDADES = F["cidades_proximas"]
CID_TXT = ", ".join(CIDADES[:-1]) + " e " + CIDADES[-1]
CD = json.loads((SRC / "cidades.json").read_text(encoding="utf-8"))
MUNS = CD["municipios"]                     # até RAIO km em linha reta, do mais perto ao mais longe
EMAX = F["estrada_max_km"]                  # limite de entrega pela estrada
MUNS_E = [z for z in MUNS if z["estrada_km"] <= EMAX]   # entrega normal
MUNS_C = [z for z in MUNS if z["estrada_km"] > EMAX]    # dentro do raio, mas sob consulta
N_ENT = len(MUNS_E) + 1                     # municípios com entrega, contando Lindóia do Sul
ALC = f"até cerca de {EMAX} km de estrada ({RAIO} km em linha reta)"   # alcance da entrega, por extenso
C1, C2 = F["carga_fechada_t"]               # carga fechada: um caminhão de C1 a C2 toneladas
MIN = S["carga_minima_t"]                   # a partir daqui vale o preço cheio da carga fechada
PTM = br(S["preco_tonelada_menor"])         # 550: abaixo de MIN t, sob consulta
CARGA = f"{C1} a {C2} toneladas"
PC1, PC2 = br(C1 * S["preco_tonelada"]), br(C2 * S["preco_tonelada"])   # 4.000, 5.000
N_CARGAS = br(S["toneladas"] // C2)         # cargas de C2 t no estoque
REGRA_ENTREGA = (f"A carga fechada, de {CARGA} num caminhão, é o pedido ideal: a tonelada sai a R$ {PT} e o frete se divide por mais toneladas. "
                 f"Abaixo de {MIN} t, a tonelada sai a R$ {PTM} e o pedido depende de disponibilidade.")


def tempo(minutos):
    h, m = divmod(int(minutos), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def cargas(t):
    n = int(-(-t // C2))
    return f"{n} cargas de {C2} t" if n > 1 else "1 carga"


def preco_t(t):
    return S["preco_tonelada"] if t >= MIN else S["preco_tonelada_menor"]


SPEC_SIL = [  # as duas faixas de preço da silagem, para máquinas
    {"@type": "UnitPriceSpecification", "price": S["preco_tonelada"], "priceCurrency": "BRL", "unitCode": "TNE", "unitText": "tonelada",
     "eligibleQuantity": {"@type": "QuantitativeValue", "minValue": MIN, "unitCode": "TNE"}},
    {"@type": "UnitPriceSpecification", "price": S["preco_tonelada_menor"], "priceCurrency": "BRL", "unitCode": "TNE", "unitText": "tonelada",
     "eligibleQuantity": {"@type": "QuantitativeValue", "maxValue": MIN - 0.01, "unitCode": "TNE"},
     "description": f"Pedidos abaixo de {MIN} t, sob consulta de disponibilidade"}]
PRECO_REGRA = f"R$ {PT} a tonelada a partir de {MIN} t; abaixo de {MIN} t, R$ {PTM} a tonelada, sob consulta de disponibilidade"


AV = F.get("avaliacoes_google")
PROVA = (f'<p class="prova"><span class="estrelas" aria-hidden="true">★★★★★</span> <strong>{br(AV["nota"], 1)} de 5 no Google</strong>, em {AV["total"]} avaliações. '
         f'<a href="{F["perfil_google"]}" rel="noopener">Ler as avaliações</a></p>') if AV else ""
DATA_HTML = f'<time datetime="{F["atualizado_em"]}">{DATA}</time>'


def faq(itens):
    """Perguntas visíveis (h3 + p) e o mesmo conteúdo em FAQPage para máquinas."""
    html = '<div class="pergs">' + "".join(f'<div><h3>{q}</h3><p>{r}</p></div>' for q, r in itens) + "</div>"
    limpa = lambda s: re.sub(r"<[^>]+>", "", s)
    ld = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": limpa(q),
          "acceptedAnswer": {"@type": "Answer", "text": limpa(r)}} for q, r in itens]}
    return html, ld


def wa(msg, origem, rotulo, classe="bt"):
    return (f'<a class="{classe}" data-lead="{origem}" rel="nofollow" '
            f'href="https://wa.me/{ZAP}?text={quote(msg)}">{rotulo}</a>')


TAM_PADRAO = "(min-width:901px) 50vw, 100vw"


def img(nome, alt, w=720, h=1280, lazy=True, extra="", sizes=TAM_PADRAO):
    l = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    # versões menores geradas em site-src/fotos (nome-360.webp, nome-540.webp, nome-640.webp)
    var = [(int(m), f"/fotos/{nome}-{m}.webp") for m in ("360", "540", "640") if (SRC / "fotos" / f"{nome}-{m}.webp").exists()]
    ss = (f' srcset="{", ".join(f"{u} {m}w" for m, u in var)}, /fotos/{nome}.webp {w}w" sizes="{sizes}"') if var else ""
    return f'<img src="/fotos/{nome}.webp"{ss} alt="{escape(alt)}" width="{w}" height="{h}"{l}{extra}>'


NAV = [("/silagem-de-milho/", "Silagem de milho"), ("/carga-de-silagem/", "Carga fechada"), ("/pre-secado-de-azevem/", "Pré-secado"),
       ("/regiao/", "Entrega e região"), ("/contato/", "Contato")]

NEGOCIO = {
    "@type": "LocalBusiness", "@id": f"{DOM}/#estancia", "name": NOME, "alternateName": [MARCA, "Estância Safra"],
    "url": f"{DOM}/", "logo": f"{DOM}/assets/safra-emblema.png", "image": f"{DOM}/fotos/og.jpg",
    "description": f"Propriedade rural em {LOCAL} que vende silagem de milho a granel por tonelada, também em carga fechada de {CARGA}, e pré-secado de azevém em bolas, com entrega {ALC} (frete orçado) ou retirada no local.",
    "address": {"@type": "PostalAddress", "addressLocality": CID, "addressRegion": UF, "addressCountry": "BR"},
    "geo": {"@type": "GeoCoordinates", "latitude": CD["origem"]["lat"], "longitude": CD["origem"]["lon"]},
    "areaServed": [{"@type": "GeoCircle", "geoMidpoint": {"@type": "GeoCoordinates", "latitude": CD["origem"]["lat"], "longitude": CD["origem"]["lon"]},
                    "geoRadius": RAIO * 1000}] + [{"@type": "City", "name": f'{z["nome"]}, {z["uf"]}'} for z in [CD["origem"]] + MUNS_E],
    "hasMap": F["perfil_google"], "priceRange": "R$", "currenciesAccepted": "BRL",
}
if F.get("whatsapp_definitivo"):
    NEGOCIO["telephone"] = "+" + ZAP


def oferta(preco, unit_code, unidade_txt, estoque=None):
    o = {"@type": "Offer", "price": preco, "priceCurrency": "BRL", "availability": "https://schema.org/InStock",
         "priceSpecification": {"@type": "UnitPriceSpecification", "price": preco, "priceCurrency": "BRL",
                                "unitCode": unit_code, "unitText": unidade_txt},
         "availableDeliveryMethod": "https://schema.org/OnSitePickup",
         "availableAtOrFrom": {"@type": "Place", "name": NOME, "address": NEGOCIO["address"]},
         "seller": {"@id": f"{DOM}/#estancia"}, "areaServed": NEGOCIO["areaServed"]}
    if estoque:
        o["inventoryLevel"] = {"@type": "QuantitativeValue", "value": estoque, "unitCode": "TNE"}
    return o


def migalha(rotulo, caminho):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Início", "item": f"{DOM}/"},
        {"@type": "ListItem", "position": 2, "name": rotulo, "item": f"{DOM}{caminho}"}]}


V = F.get("verificacao", {})
VERIF = ((f'<meta name="google-site-verification" content="{V["google_meta"]}">\n' if V.get("google_meta") else "") +
         (f'<meta name="msvalidate.01" content="{V["bing"]}">\n' if V.get("bing") else ""))


def pagina(caminho, title, desc, corpo, grafo, barra_msg, barra_txt, og="og.jpg", extra=None):
    url = f"{DOM}{caminho}"
    par = f" ({RAIO} km em linha reta)"
    if par in corpo:
        k = corpo.index(par) + len(par)
        corpo = corpo[:k] + corpo[k:].replace(par, "")
    atual = ' aria-current="page"'
    nav = "".join(f'<a href="{h}"{atual if h == caminho else ""}>{t}</a>' for h, t in NAV)
    mh = re.search(r'<img src="([^"]+)"(?: srcset="([^"]+)" sizes="([^"]+)")?[^>]*fetchpriority="high"', corpo)
    pre = ""
    if mh:
        resp = f' imagesrcset="{mh.group(2)}" imagesizes="{mh.group(3)}"' if mh.group(2) else ""
        pre = f'<link rel="preload" as="image" href="{mh.group(1)}"{resp} fetchpriority="high">\n'
    pre += ('<link rel="preload" as="font" type="font/woff2" href="/assets/pt-sans-400.woff2" crossorigin>\n'
            '<link rel="preload" as="font" type="font/woff2" href="/assets/pt-sans-700.woff2" crossorigin>\n')
    gid = F.get("ga4_id", "")
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
          f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{gid}")</script>\n') if gid else ""
    erro = caminho == "/404.html"
    if not erro:
        mi = re.search(r'<img src="/fotos/([^"]+)"[^>]*fetchpriority="high"', corpo)
        grafo = grafo + [{
            "@type": "WebPage", "@id": f"{url}#pagina", "url": url, "name": title, "description": desc,
            "inLanguage": "pt-BR", "isPartOf": {"@id": f"{DOM}/#site"}, "about": {"@id": f"{DOM}/#estancia"},
            "publisher": {"@id": f"{DOM}/#estancia"}, "dateModified": F["atualizado_em"],
            **({"primaryImageOfPage": {"@type": "ImageObject", "url": f"{DOM}/fotos/{mi.group(1)}",
                                       "contentLocation": LOCAL}} if mi else {}), **(extra or {})}]
        if caminho != "/" and not any(g.get("@type") == "WebSite" for g in grafo):
            grafo = grafo + [{"@type": "WebSite", "@id": f"{DOM}/#site", "url": f"{DOM}/", "name": "Estância Safra"}]
    robots = "noindex,follow" if erro else "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    ld = json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False, separators=(",", ":"))
    html = f"""<!doctype html>
<html lang="pt-BR" data-zap="{ZAP}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<meta name="robots" content="{robots}">
<meta name="author" content="{NOME}">
<meta name="publisher" content="{NOME}">
<meta name="geo.region" content="BR-{UF}">
<meta name="geo.placename" content="{CID}">
{"" if erro else f'<link rel="canonical" href="{url}">'}
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{MARCA} · {NOME}">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOM}/fotos/{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Silos e volumoso da {NOME}, em {LOCAL}">
<meta property="og:updated_time" content="{F['atualizado_em']}">
<meta name="twitter:card" content="summary_large_image">
<link rel="sitemap" type="application/xml" href="/sitemap.xml">
<link rel="alternate" type="text/plain" title="Resumo para IA" href="/llms.txt">
{VERIF}<meta name="theme-color" content="#0B4D2D">
<script>document.documentElement.classList.add("js")</script>
{pre}{ga}<link rel="icon" href="/assets/safra-icone.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/safra-icone.png">
<link rel="stylesheet" href="/assets/site.css?v={VER}">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><div class="wrap">
<a class="logo" href="/" aria-label="{MARCA} · {NOME}, página inicial"><img src="/assets/safra-horizontal.svg" alt="{MARCA} · {NOME}" width="159" height="44"></a>
<nav aria-label="Principal">{nav}{wa(barra_msg, "topo", "WhatsApp", "bt pq")}</nav>
</div></header>
<div class="listra" aria-hidden="true"></div>
<nav class="trilho" aria-label="Seções">{nav}</nav>
<main id="conteudo">
{corpo}
</main>
<footer class="rod"><div class="wrap">
<div><img src="/assets/safra-emblema-negativo.svg" alt="Emblema da Estância Safra" width="130" height="96" loading="lazy">
<p><strong>{NOME}</strong> ({MARCA})<br>{CID}, Santa Catarina, Brasil</p>
<p>Preços e estoque atualizados em {DATA_HTML}.</p>{PROVA}</div>
<div><b>À venda</b><ul>
<li><a href="/silagem-de-milho/">Silagem de milho, R$ {PT} a tonelada</a></li>
<li><a href="/carga-de-silagem/">Carga fechada de {CARGA}</a></li>
<li><a href="/pre-secado-de-azevem/">Pré-secado de azevém, R$ {PB} a bola</a></li>
<li><a href="/silagem-a-venda-sc/">Silagem à venda em SC</a></li>
<li><a href="/pre-secado-a-venda/">Pré-secado à venda</a></li></ul></div>
<div><b>Atendimento</b><ul>
<li><a href="/regiao/">Entrega e região</a></li>
<li><a href="/contato/">Contato e pedido</a></li>
<li><a href="{F['perfil_google']}" rel="noopener">Ver a estância no Google</a></li>
<li><a href="/privacidade/">Política de privacidade</a></li></ul></div>
</div></footer>
<div class="barra"><span>{barra_txt}</span>{wa(barra_msg, "barra-celular", "Chamar no WhatsApp", "bt claro pq")}</div>
<script src="/assets/site.js?v={VER}" defer></script>
</body>
</html>
"""
    destino = OUT / caminho.strip("/") / "index.html" if caminho != "/404.html" else OUT / "404.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")


def tabela_oferta():
    return f"""<div class="rolagem"><table>
<caption>Preços e estoque da {NOME}, em {LOCAL}. Atualizado em {DATA_HTML}. Valores para retirada no local, sem frete.</caption>
<thead><tr><th scope="col">Produto</th><th scope="col">Preço</th><th scope="col">Equivale a</th><th scope="col">Disponível</th><th scope="col">Como levar</th></tr></thead>
<tbody>
<tr><th scope="row"><a href="/silagem-de-milho/">Silagem de milho</a></th><td><b>R$ {PT}</b> por tonelada a partir de {MIN} t (R$ {PTM} abaixo disso, sob consulta)</td><td>R$ {PKG} por kg</td><td>{T} toneladas</td><td>Retirada no local ou entrega {ALC}, frete orçado</td></tr>
<tr><th scope="row"><a href="/carga-de-silagem/">Carga fechada de silagem</a></th><td><b>R$ {PC1} a R$ {PC2}</b> por carga</td><td>{CARGA} a R$ {PT} a tonelada</td><td>{N_CARGAS} cargas de {C2} t</td><td>Carregada da face do silo no caminhão, entrega com frete orçado</td></tr>
<tr><th scope="row"><a href="/pre-secado-de-azevem/">Pré-secado de azevém</a></th><td><b>R$ {PB}</b> por bola</td><td>R$ {PKG_MIN} a R$ {PKG_MAX} por kg</td><td>Bolas de cerca de {KG} kg ({KMIN} a {KMAX} kg)</td><td>Retirada no local ou entrega {ALC}, frete orçado</td></tr>
</tbody></table></div>"""


def chamada(titulo, texto, msg, origem):
    return f"""<div class="chamada"><div class="wrap"><div><h2>{titulo}</h2><p>{texto}</p></div>
<div>{wa(msg, origem, "Chamar no WhatsApp", "bt claro")}</div></div></div>"""


BROMA = ("A análise bromatológica está em andamento. Assim que o laudo do laboratório sair, os números de matéria seca, amido e fibra "
         "entram nesta página, com a data da coleta. Até lá, não informamos nenhum valor de composição: preferimos mostrar o laudo a prometer número.")

# ---------------------------------------------------------------- HOME
msg_home = "Olá! Vi no site da Estância Safra a silagem de milho e o pré-secado. Ainda tem disponível?"
FAQ_HOME, LD_HOME = faq([
    (f"Quanto custa a tonelada de silagem de milho?",
     f"Na {NOME}, em {LOCAL}, a silagem de milho custa R$ {PT} a tonelada em {MESANO} para pedidos a partir de {MIN} t, a carga fechada de um caminhão, o que dá R$ {PKG} por quilo. Abaixo de {MIN} t, a tonelada sai a R$ {PTM} e o pedido depende de disponibilidade. O valor é para retirada na estância e não inclui frete."),
    (f"Vocês entregam?",
     f"Sim, {ALC} de {LOCAL}. O frete é orçado pelo WhatsApp conforme a distância até a sua propriedade e o tamanho da carga. {REGRA_ENTREGA} Quem tem caminhão também pode retirar na estância."),
    (f"Qual o pedido mínimo de silagem?",
     f"O pedido ideal é a carga fechada de um caminhão, de {CARGA}, a R$ {PT} a tonelada. Abaixo de {MIN} t, a tonelada sai a R$ {PTM} e o pedido depende de disponibilidade: consulte pelo WhatsApp. O pré-secado é vendido por bola."),
    (f"Tem análise bromatológica?",
     f"{BROMA}"),
    (f"Qual a diferença entre silagem de milho e pré-secado de azevém?",
     f"A silagem de milho é a planta inteira do milho picada e fermentada no silo, vendida aqui por tonelada. O pré-secado de azevém é o capim cortado, murcho no campo e embalado em bolas com filme, vendido aqui por unidade. <a href=\"/pre-secado-de-azevem/\">Veja a comparação de preço por quilo</a>."),
])
home = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="pill"><i></i><span>Disponível hoje · atualizado em {DATA_HTML}</span></p>
<h1>Silagem de milho e pré-secado de azevém à venda em {LOCAL}</h1>
<p class="sub">Silagem de milho a granel, por tonelada ou em carga fechada de {CARGA} num caminhão, carregada da face do silo. Preço aberto, estoque informado e entrega {ALC}, com frete orçado. Ou retire na estância.</p>
<div class="selos">
<div><b>{T} t</b><span>de silagem de milho disponíveis</span></div>
<div><b>R$ {PT}</b><span>a tonelada de silagem, a partir de {MIN} t</span></div>
<div><b>R$ {PB}</b><span>a bola de pré-secado (~{KG} kg)</span></div>
</div>
<div class="acoes">{wa(msg_home, "heroi-home", "Chamar no WhatsApp", "bt claro")}<a class="bt linha" href="#oferta">Ver preços e estoque</a></div>
{PROVA}
</div>
<figure>{img("silo-coberto-eucaliptos", f"Silo trincheira de silagem de milho coberto com lona e sacos de peso na {NOME}, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section id="oferta" class="banda" style="margin-top:0"><div class="wrap">
<p class="rot">Disponível hoje</p>
<h2>Quanto custa e quanto tem</h2>
<p class="lead">Em {MESANO}, a {NOME} tem {T} toneladas de silagem de milho a R$ {PT} a tonelada (a partir de {MIN} t) e bolas de pré-secado de azevém a R$ {PB} cada. Uma carga fechada de {CARGA} sai de R$ {PC1} a R$ {PC2}. Entregamos {ALC}, com frete orçado conforme a distância, ou você retira na estância, em {LOCAL}.</p>
{tabela_oferta()}
</div></section>

<section><div class="wrap">
<p class="rot">Os dois volumosos</p>
<h2>Escolha o que a sua dieta precisa</h2>
<div class="duas">
<article class="cartao"><div class="foto">{img("silagem-face-detalhe", "Face do silo aberta mostrando a silagem de milho picada e compactada", sizes="(min-width:901px) 540px, 100vw")}</div>
<div class="corpo"><h3><a href="/silagem-de-milho/">Silagem de milho</a></h3>
<p class="preco">R$ {PT} <small>por tonelada a partir de {MIN} t · R$ {PKG} o kg</small></p>
<p>{T} toneladas em silos trincheira cobertos com lona e sacos de peso. Vendida por tonelada; o pedido ideal é a carga fechada de {CARGA}. Abaixo de {MIN} t, sob consulta.</p>
<a class="bt" href="/silagem-de-milho/">Ver a silagem de milho</a></div></article>
<article class="cartao"><div class="foto">{img("bolas-pre-secado", "Bolas de pré-secado de azevém embaladas em filme branco, armazenadas entre muros de tijolo", sizes="(min-width:901px) 540px, 100vw")}</div>
<div class="corpo"><h3><a href="/pre-secado-de-azevem/">Pré-secado de azevém</a></h3>
<p class="preco">R$ {PB} <small>por bola de cerca de {KG} kg</small></p>
<p>Bolas embaladas em filme, com peso entre {KMIN} e {KMAX} kg. Vendidas por unidade: leve uma, dez ou a carga fechada.</p>
<a class="bt" href="/pre-secado-de-azevem/">Ver o pré-secado</a></div></article>
</div></div></section>

<section class="escura"><div class="wrap">
<p class="rot">Como comprar</p>
<h2>Três passos, sem intermediário</h2>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>Chame no WhatsApp</h3><p>Diga o produto, a quantidade e de que cidade você vem. Confirmamos o estoque na hora.</p></div>
<div class="passo"><p class="n">02</p><h3>Combine a entrega ou a retirada</h3><p>Até cerca de {EMAX} km de estrada, orçamos o frete até a sua propriedade; em carga fechada de {CARGA}, o frete por tonelada fica menor. Se preferir, marcamos dia e horário para o seu caminhão carregar na estância, em {LOCAL}.</p></div>
<div class="passo"><p class="n">03</p><h3>Carregue e leve</h3><p>Você paga pelo que levar: silagem por tonelada, pré-secado por bola.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Veja antes de vir</p>
<h2>Fotos reais dos silos e das bolas</h2>
<p class="lead">Todas as fotos desta página foram feitas na estância em novembro de 2026. Antes de comprar, veja <a href="/silagem-a-venda-sc/">como avaliar silagem à venda em SC</a> e <a href="/pre-secado-a-venda/">como avaliar uma bola de pré-secado</a>.</p>
<div class="galeria mosaico">
<figure>{img("silo-lona-araucaria", "Silo trincheira coberto com lona branca, com araucária ao fundo")}<figcaption>Silo coberto, com a araucária ao fundo</figcaption></figure>
<figure>{img("silo-trincheira-lateral", "Lateral de um silo trincheira com muro de tijolo e lona presa por sacos", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Silo trincheira com muro de tijolo</figcaption></figure>
<figure>{img("lona-sacos-araucaria", "Lona branca do silo presa por fileiras de sacos, com uma araucária ao fundo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Lona vedada com fileiras de sacos</figcaption></figure>
<figure>{img("silagem-face-parede", "Silagem de milho compactada junto à parede do silo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Silagem compactada junto à parede</figcaption></figure>
<figure>{img("silos-vista-vale", "Dois silos trincheira cobertos, lado a lado, com pasto ao fundo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Dois silos lado a lado</figcaption></figure>
</div></div></section>

<div class="faixa-foto">{img("lona-silos-graneleiros", "Silo trincheira coberto com lona e sacos de peso, com silos graneleiros ao fundo", sizes="100vw")}
<div class="wrap"><p class="rot">Nosso jeito de vender</p>
<h2>O que está no site é o que você encontra na estância</h2>
<div class="tres">
<div><b>Preço aberto</b><p>R$ {PT} a tonelada de silagem a partir de {MIN} t (R$ {PTM} abaixo disso) e R$ {PB} a bola de pré-secado, publicados e com data.</p></div>
<div><b>Estoque informado</b><p>{T} toneladas de silagem de milho em {MESANO}. Quando o número mudar, a página muda.</p></div>
<div><b>Laudo, não promessa</b><p>A análise bromatológica entra no site quando o laboratório entregar. Antes disso, nenhum número de composição.</p></div>
</div></div></div>

<section><div class="wrap">
<p class="rot">Perguntas de quem compra</p>
<h2>O que os produtores perguntam antes de fechar</h2>
{FAQ_HOME}</div></section>
{chamada("Precisa de volumoso perto de " + CID + "?", f'Entregamos em {N_ENT} municípios a até {EMAX} km de estrada, como Concórdia, Seara, Xanxerê e Chapecó. <a href="/regiao/" style="color:inherit">Ver as cidades</a>.', msg_home, "chamada-home")}
"""
NEGOCIO_HOME = {**NEGOCIO, "knowsAbout": ["silagem de milho", "pré-secado de azevém", "volumoso para gado"],
                "makesOffer": [{"@type": "Offer", "itemOffered": {"@id": f"{DOM}/silagem-de-milho/#produto"}, "price": S["preco_tonelada"], "priceCurrency": "BRL", "priceSpecification": SPEC_SIL},
                               {"@type": "Offer", "itemOffered": {"@id": f"{DOM}/pre-secado-de-azevem/#produto"}, "price": P["preco_bola"], "priceCurrency": "BRL"}]}
pagina("/", f"Silagem de milho à venda em {LOCAL} | Estância Safra",
       f"{T} t de silagem de milho a R$ {PT} a tonelada em carga fechada de {C1} a {C2} t e pré-secado a R$ {PB} a bola. Entrega até {EMAX} km de estrada.",
       home, [NEGOCIO_HOME, LD_HOME, {"@type": "WebSite", "@id": f"{DOM}/#site", "url": f"{DOM}/", "name": "Estância Safra",
                        "inLanguage": "pt-BR", "publisher": {"@id": f"{DOM}/#estancia"}}],
       msg_home, f"Silagem R$ {PT}/t · pré-secado R$ {PB}/bola")

# ---------------------------------------------------------------- SILAGEM
msg_sil = "Olá! Vi no site a silagem de milho a R$ %s a tonelada. Ainda tem disponível? Preciso de cerca de ___ toneladas." % PT
FAQ_SIL, LD_SIL = faq([
    (f"Qual o preço da silagem de milho hoje?",
     f"Em {DATA}, a {NOME} vende silagem de milho a R$ {PT} a tonelada para pedidos a partir de {MIN} t (a carga fechada de um caminhão, de {CARGA}) e a R$ {PTM} abaixo disso, sob consulta. Sem frete. O preço desta página muda junto com o da estância."),
    (f"Quanto custa a tonelada de silagem de milho em Santa Catarina?",
     f"Na {NOME}, em {LOCAL}, a tonelada de silagem de milho custa R$ {PT} em {MESANO}, ou R$ {PKG} por quilo, para pedidos a partir de {MIN} t e retirada no local; abaixo de {MIN} t, R$ {PTM}, sob consulta. Este é o preço desta propriedade, não uma média do estado: o valor muda de região para região e de safra para safra."),
    (f"Vale a pena comprar silagem de longe?",
     f"Depende do frete. Silagem é um produto pesado e úmido, então o transporte pesa no custo final por quilo. Na {NOME}, a entrega vai {ALC} de {LOCAL}, e compensa mais em carga fechada de {CARGA}, porque o frete se divide por mais toneladas. Mais longe que {EMAX} km de estrada, peça o frete antes e some ao preço da tonelada."),
    (f"Vocês entregam a silagem?",
     f"Sim, {ALC} de {LOCAL}, com frete orçado pelo WhatsApp conforme a distância e as toneladas. {REGRA_ENTREGA} Quem tem caminhão pode retirar direto no silo."),
    (f"A silagem tem análise bromatológica?",
     f"{BROMA}"),
    ("Quanto de silagem de milho uma vaca come por dia?",
     "Para planejar o silo, a Embrapa usa 30 kg de silagem por vaca por dia (<a href=\"https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1039523/1/25971.pdf\" rel=\"noopener\">Embrapa Acre, 2015</a>). "
     "Outra publicação da Embrapa fala em 25 a 35 kg por animal adulto por dia, conforme a raça e a produção, e de 10 a 30 kg por cabeça conforme a categoria, menos para bezerros e novilhas e mais para vacas em lactação "
     "(<a href=\"https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/900615/1/Instalacoeszootecnicas.pdf\" rel=\"noopener\">Embrapa Amazônia Oriental, 2004</a>). O número da sua dieta é o do seu técnico."),
    (f"Posso comprar menos de {MIN} toneladas?",
     f"Pode, sob consulta. Abaixo de {MIN} t a tonelada sai a R$ {PTM}, e o pedido depende de disponibilidade: pergunte pelo WhatsApp antes. "
     f"A partir de {MIN} t, a carga fechada de um caminhão, vale o preço de R$ {PT} a tonelada."),
    (f"Também vendem pré-secado?",
     f"Sim. A {NOME} vende <a href=\"/pre-secado-de-azevem/\">pré-secado de azevém em bolas de cerca de {KG} kg</a>, a R$ {PB} a bola."),
])
sil = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Silagem de milho</p>
<p class="pill"><i></i><span>{T} t disponíveis · atualizado em {DATA_HTML}</span></p>
<h1>Silagem de milho em {LOCAL}: R$ {PT} a tonelada</h1>
<p class="sub">A {NOME} tem {T} toneladas de silagem de milho disponíveis em {MESANO}. Venda a granel, por tonelada ou em carga fechada de {CARGA} (R$ {PC1} a R$ {PC2}), com retirada na estância ou entrega {ALC}, frete orçado.</p>
<div class="selos">
<div><b>R$ {PT}</b><span>por tonelada, a partir de {MIN} t</span></div>
<div><b>R$ {PKG}</b><span>por quilo</span></div>
<div><b>{T} t</b><span>em estoque</span></div>
</div>
<div class="acoes">{wa(msg_sil, "heroi-silagem", "Pedir pelo WhatsApp", "bt claro")}<a class="bt linha" href="#calculadora">Calcular quantas toneladas</a></div>
{PROVA}
</div>
<figure>{img("silagem-face-detalhe", f"Silagem de milho picada e compactada na face aberta do silo, na {NOME}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Resumo da oferta</p>
<h2>Preço da silagem de milho e estoque, em números</h2>
<div class="rolagem"><table>
<caption>Silagem de milho da {NOME}, {LOCAL}. Atualizado em {DATA_HTML}.</caption>
<tbody>
<tr><th scope="row">Produto</th><td>Silagem de milho (planta inteira picada e ensilada)</td></tr>
<tr><th scope="row">Preço</th><td><b>R$ {PT} por tonelada</b> a partir de {MIN} t (R$ {PKG} por kg). Abaixo de {MIN} t, R$ {PTM} a tonelada, sob consulta de disponibilidade. Sem frete</td></tr>
<tr><th scope="row">Quantidade disponível</th><td>{T} toneladas</td></tr>
<tr><th scope="row">Armazenagem</th><td>Silos trincheira, cobertos com lona e sacos de peso</td></tr>
<tr><th scope="row">Carga fechada</th><td><a href="/carga-de-silagem/">{CARGA} por caminhão: R$ {PC1} a R$ {PC2}</a>, sem frete</td></tr>
<tr><th scope="row">Entrega</th><td>{ALC[0].upper() + ALC[1:]}, com frete orçado pelo WhatsApp. Ou retirada em {LOCAL}</td></tr>
<tr><th scope="row">Análise bromatológica</th><td>Em andamento; o laudo será publicado nesta página</td></tr>
</tbody></table></div>
</div></section>

<section id="calculadora"><div class="wrap">
<p class="rot">Calculadora</p>
<h2>Quantas toneladas de silagem eu preciso?</h2>
<p class="lead">A conta é: número de animais × quilos de silagem por animal por dia × número de dias, dividido por mil. Preencha com os números da sua dieta.</p>
<div class="caixa">
<form id="calc" data-preco="{S['preco_tonelada']}" data-preco-menor="{S['preco_tonelada_menor']}" data-minimo="{MIN}" data-estoque="{S['toneladas']}" data-carga="{C2}">
<div class="campos3">
<div class="campo"><label for="animais">Animais</label><input id="animais" name="animais" type="number" inputmode="numeric" min="1" value="50"></div>
<div class="campo"><label for="kg">Kg por animal/dia</label><input id="kg" name="kg" type="number" inputmode="decimal" min="1" step="0.5" value="30"></div>
<div class="campo"><label for="dias">Dias</label><input id="dias" name="dias" type="number" inputmode="numeric" min="1" value="90"></div>
</div>
<p class="nota">Os valores iniciais são só um exemplo. Para planejar, a Embrapa usa 30 kg de silagem por vaca por dia (<a href="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1039523/1/25971.pdf" rel="noopener">Embrapa Acre, 2015</a>), mas o consumo muda com a categoria, o peso e o resto da dieta: use o número indicado pelo seu técnico ou nutricionista.</p>
</form>
<div class="saida" id="calc-saida" aria-live="polite">
<div class="num">135 <small>toneladas</small></div>
<p>Exemplo: 50 animais × 30 kg por dia × 90 dias = 135 toneladas, ou {cargas(135)}. A R$ {PT} a tonelada, dá R$ {br(135 * S['preco_tonelada'])}, sem frete.</p>
{wa("Olá! Preciso de cerca de 135 t de silagem de milho. Ainda tem disponível?", "calculadora", "Pedir essa quantidade no WhatsApp")}
</div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Armazenagem</p>
<h2>Como a silagem está guardada</h2>
<div class="midia">
<div>{img("silo-lona-araucaria", "Silo trincheira coberto com lona branca e fileiras de sacos, com araucária ao fundo")}</div>
<div><p>A silagem de milho da {NOME} fica em silos trincheira, com paredes de tijolo e de madeira, cobertos com lona e fileiras de sacos de peso por cima e nas bordas. As fotos mostram os silos como estavam em novembro de 2026.</p>
<p>Na retirada, o carregamento é feito direto da face do silo para o seu caminhão. Vale combinar o transporte para que a silagem chegue e seja usada ou reensilada o quanto antes: silagem exposta ao ar perde qualidade. Veja <a href="/silagem-a-venda-sc/#frete">quanto a silagem custa entregue na sua propriedade</a> e por quanto tempo ela aguenta fora do silo.</p></div>
</div>
<div class="galeria" style="margin-top:20px">
<figure>{img("silo-coberto-eucaliptos", "Silo trincheira coberto visto de frente, com eucaliptos ao fundo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Silo coberto, visto de frente</figcaption></figure>
<figure>{img("silagem-face-parede", "Silagem de milho compactada junto à parede do silo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Face do silo junto à parede</figcaption></figure>
<figure>{img("lona-silos-graneleiros", "Lona do silo com sacos de peso e silos metálicos ao fundo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Cobertura com lona e sacos</figcaption></figure>
<figure>{img("silo-trincheira-lateral", "Lateral do silo trincheira com muro de tijolo", sizes="(min-width:901px) 280px, 50vw")}<figcaption>Muro lateral do silo</figcaption></figure>
</div>
</div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem compra silagem de milho</h2>
{FAQ_SIL}</div></section>
{chamada(f"{T} toneladas disponíveis, R$ {PT} a tonelada", f"Retirada em {LOCAL}. Diga a quantidade e a sua cidade.", msg_sil, "chamada-silagem")}
"""
prod_sil = {"@type": "Product", "@id": f"{DOM}/silagem-de-milho/#produto", "name": "Silagem de milho",
            "description": f"Silagem de milho vendida por tonelada pela {NOME}, em {LOCAL}. {T} toneladas disponíveis, com retirada no local ou entrega {ALC}, também em carga fechada de {CARGA}.",
            "category": "Volumoso para alimentação animal", "image": [f"{DOM}/fotos/silagem-face-detalhe.webp", f"{DOM}/fotos/silo-coberto-eucaliptos.webp"],
            "brand": {"@type": "Brand", "name": MARCA},
            "offers": {**oferta(S["preco_tonelada"], "TNE", "tonelada", S["toneladas"]), "priceSpecification": SPEC_SIL}}
pagina("/silagem-de-milho/", f"Silagem de milho a R$ {PT} a tonelada em {LOCAL}",
       f"{T} t de silagem de milho a R$ {PT} a tonelada a partir de {MIN} t (carga fechada) em {LOCAL}. Entrega até {EMAX} km de estrada. Calcule quanto precisa.",
       sil, [NEGOCIO, prod_sil, LD_SIL, migalha("Silagem de milho", "/silagem-de-milho/")],
       msg_sil, f"Silagem de milho · R$ {PT} a tonelada", og="og-silagem.jpg")

# ---------------------------------------------------------------- PRÉ-SECADO
msg_pre = "Olá! Vi no site o pré-secado de azevém a R$ %s a bola. Ainda tem? Preciso de ___ bolas." % PB
FAQ_PRE, LD_PRE = faq([
    (f"Quanto custa uma bola de pré-secado de azevém?",
     f"Na {NOME}, em {LOCAL}, a bola de pré-secado de azevém custa R$ {PB} em {MESANO}. Cada bola pesa cerca de {KG} kg, entre {KMIN} e {KMAX} kg, o que dá de R$ {PKG_MIN} a R$ {PKG_MAX} por quilo."),
    (f"Quanto pesa uma bola de pré-secado?",
     f"As bolas da {NOME} pesam cerca de {KG} kg cada, com variação de {P['variacao_kg']} kg para mais ou para menos. O peso muda de bola para bola porque depende da umidade e da compactação do capim."),
    (f"Pré-secado é a mesma coisa que feno ou que bola de silagem?",
     f"Não é feno. O feno é o capim seco até poder ser guardado sem embalagem; o pré-secado é enfardado mais úmido e embalado em filme, onde fermenta sem ar. \"Bola de silagem\" e \"silagem pré-secada\" são outros nomes que os produtores dão ao mesmo produto que a {NOME} vende: pré-secado de azevém em bolas de cerca de {KG} kg."),
    (f"Posso comprar poucas bolas?",
     f"Sim, a venda é por unidade. Diga pelo WhatsApp quantas bolas você quer e combinamos a retirada."),
    (f"Vocês entregam?",
     f"Sim, {ALC} de {LOCAL}. O frete é orçado pelo WhatsApp conforme a distância e o número de bolas. Também dá para retirar na estância."),
    (f"Tem análise bromatológica do pré-secado?",
     f"{BROMA}"),
])
pre = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Pré-secado de azevém</p>
<p class="pill"><i></i><span>Disponível hoje · atualizado em {DATA_HTML}</span></p>
<h1>Pré-secado de azevém em bolas de {KG} kg: R$ {PB} a bola</h1>
<p class="sub">Também chamado de silagem pré-secada ou bola de silagem. Bolas embaladas em filme, à venda na {NOME}, em {LOCAL}. Cada bola pesa entre {KMIN} e {KMAX} kg. Retirada na estância ou entrega {ALC}, com frete orçado.</p>
<div class="selos">
<div><b>R$ {PB}</b><span>por bola</span></div>
<div><b>~{KG} kg</b><span>cada bola ({KMIN} a {KMAX} kg)</span></div>
<div><b>R$ {PKG_MIN} a {PKG_MAX}</b><span>por quilo, conforme o peso</span></div>
</div>
<div class="acoes">{wa(msg_pre, "heroi-presecado", "Pedir pelo WhatsApp", "bt claro")}<a class="bt linha" href="#comparar">Comparar com a silagem</a></div>
{PROVA}
</div>
<figure>{img("bolas-pre-secado", f"Dezenas de bolas de pré-secado de azevém embaladas em filme branco na {NOME}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Resumo da oferta</p>
<h2>O que está à venda, em números</h2>
<div class="rolagem"><table>
<caption>Pré-secado de azevém da {NOME}, {LOCAL}. Atualizado em {DATA_HTML}.</caption>
<tbody>
<tr><th scope="row">Produto</th><td>Pré-secado de azevém, em bolas embaladas em filme</td></tr>
<tr><th scope="row">Preço</th><td><b>R$ {PB} por bola</b>, sem frete</td></tr>
<tr><th scope="row">Peso de cada bola</th><td>Cerca de {KG} kg, podendo variar {P['variacao_kg']} kg para mais ou para menos ({KMIN} a {KMAX} kg)</td></tr>
<tr><th scope="row">Preço por quilo</th><td>De R$ {PKG_MIN} (bola de {KMAX} kg) a R$ {PKG_MAX} (bola de {KMIN} kg)</td></tr>
<tr><th scope="row">Entrega</th><td>{ALC[0].upper() + ALC[1:]}, com frete orçado pelo WhatsApp. Ou retirada em {LOCAL}</td></tr>
<tr><th scope="row">Análise bromatológica</th><td>Em andamento; o laudo será publicado nesta página</td></tr>
</tbody></table></div>
</div></section>

<section><div class="wrap">
<p class="rot">Veja o estoque</p>
<h2>As bolas, filmadas na estância</h2>
<div class="midia">
<div><video controls muted playsinline preload="none" poster="/fotos/bolas-video-capa.webp" width="576" height="1024">
<source src="/fotos/bolas-pre-secado.mp4" type="video/mp4">Seu navegador não mostra vídeo. Veja as fotos nesta página.</video></div>
<div><p>O vídeo e as fotos mostram as bolas de pré-secado de azevém como estavam armazenadas em novembro de 2026: embaladas em filme branco, lado a lado, entre os muros de tijolo.</p>
<p>O pré-secado é o azevém cortado, deixado murchar no campo e depois enfardado e embalado em filme, que veda a entrada de ar. Por ser vendido em bolas fechadas, é prático de transportar e de usar aos poucos: a bola só começa a perder qualidade depois de aberta ou se o filme for furado.</p>
<p>Recebeu outra oferta de bola? <a href="/pre-secado-a-venda/#comparar-bolas">Compare o pré-secado à venda pelo preço por quilo</a>.</p>
<p>{wa(msg_pre, "video-presecado", "Perguntar pelo estoque")}</p></div>
</div></div></section>

<section id="comparar"><div class="wrap">
<p class="rot">Comparação</p>
<h2>Pré-secado de azevém ou silagem de milho?</h2>
<p class="lead">Os dois são volumosos conservados, mas têm papel diferente na dieta e são vendidos de forma diferente. O preço por quilo abaixo é do produto como ele sai da estância, com a umidade que tem: para comparar com justiça, é preciso o teor de matéria seca, que virá com a análise bromatológica.</p>
{tabela_oferta()}
<p class="nota">Preço por quilo do pré-secado calculado dividindo R$ {PB} pelo peso da bola ({KMIN} a {KMAX} kg).</p>
</div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem compra pré-secado</h2>
{FAQ_PRE}</div></section>
{chamada(f"Pré-secado de azevém, R$ {PB} a bola", f"Retirada em {LOCAL}. Diga quantas bolas e a sua cidade.", msg_pre, "chamada-presecado")}
"""
prod_pre = {"@type": "Product", "@id": f"{DOM}/pre-secado-de-azevem/#produto", "name": "Pré-secado de azevém em bola",
            "description": f"Pré-secado de azevém em bolas de cerca de {KG} kg ({KMIN} a {KMAX} kg), embaladas em filme, vendido por unidade pela {NOME}, em {LOCAL}.",
            "category": "Volumoso para alimentação animal", "image": [f"{DOM}/fotos/bolas-pre-secado.webp"],
            "brand": {"@type": "Brand", "name": MARCA},
            "weight": {"@type": "QuantitativeValue", "minValue": KMIN, "maxValue": KMAX, "unitCode": "KGM"},
            "offers": oferta(P["preco_bola"], "C62", "bola")}
pagina("/pre-secado-de-azevem/", f"Pré-secado de azevém: R$ {PB} a bola de {KG} kg em {CID}",
       f"Pré-secado de azevém (silagem pré-secada) em bolas de ~{KG} kg a R$ {PB} cada em {LOCAL}. Entrega até {EMAX} km de estrada. Fotos, vídeo e preço/kg.",
       pre, [NEGOCIO, prod_pre, LD_PRE, migalha("Pré-secado de azevém", "/pre-secado-de-azevem/")],
       msg_pre, f"Pré-secado de azevém · R$ {PB} a bola", og="og-presecado.jpg")

# ---------------------------------------------------------------- FONTES TÉCNICAS (guias de compra)
# Cada fonte foi aberta e conferida (trecho literal) na data de fatos.json → guias_em.
FONTES = {
    "ct74": ("Embrapa Gado de Leite, Comunicado Técnico 74 (2014)",
             "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/991566/1/COT74PersioProducaodeSilagemdeMilhoparaSuplementacaodoRebanhoLeiteiro.pdf"),
    "folder": ("Embrapa Gado de Leite, folder sobre silagem de capim-elefante",
               "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1081024/1/FolderPersiocapimelefante.pdf"),
    "pab": ("Pesquisa Agropecuária Brasileira (Embrapa), v. 53, n. 9, 2018: reensilagem de silagem de milho",
            "https://apct.sede.embrapa.br/index.php/pab/article/download/25922/14290"),
    "unoesc": ("Unoesc (SC), resumo do SIEPE sobre exposição da silagem de milho ao ar",
               "https://periodicos.unoesc.edu.br/siepe/article/download/15006/7931/49198"),
    "cepa": ("Agrolink, 31 de janeiro de 2025, com dados do Boletim Agropecuário da Epagri/Cepa",
             "https://www.agrolink.com.br/noticias/santa-catarina-avanca-na-colheita-do-milho-para-silagem_498939.html"),
    "ufms": ("UFMS/Famez, revisão sobre feno e pré-secados para ruminantes (2019)",
             "https://famez.ufms.br/files/2019/12/PRODU%C3%87%C3%83O-CARACTERISTICAS-QUALITATIVAS-E-UTILIZA%C3%87%C3%83O-DE-FENO-E-PR%C3%89-SECADOS-PARA-RUMINANTES.pdf"),
    "uepg": ("João Ricardo Alves Pereira (UEPG), Canal do Leite, 19 de junho de 2019",
             "https://canaldoleite.com/colunas/joao-ricardo-alves-pereira/comercializacao-de-silagem-pre-secada-em-fardos/"),
    "semina": ("Semina: Ciências Agrárias (UEL), v. 43, n. 4, 2022: camadas de filme no pré-secado",
               "https://ojs.uel.br/revistas/uel/index.php/semagrarias/article/download/45052/32040/236584"),
    "uky": ("University of Kentucky Cooperative Extension, AGR-283, revisado em maio de 2025",
            "https://publications.mgcafe.uky.edu/sites/publications.ca.uky.edu/files/AGR283.pdf"),
    "uky_q": ("University of Kentucky, Forage Extension: armazenagem de bolas",
              "https://forages.mgcafe.uky.edu/baleageq11"),
    "teagasc": ("Teagasc (Irlanda), Bale Handling: Avoid Damage",
                "https://teagasc.ie/wp-content/uploads/2025/05/BaleHandling.pdf"),
    "aces": ("Alabama Cooperative Extension System, Kim Mullenix, 2018",
             "https://www.aces.edu/blog/topics/beef/strategies-for-using-baleage-in-beef-cattle-operations/"),
    "acre": ("Embrapa Acre, Os Dez Passos da Ensilagem (2015)",
             "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1039523/1/25971.pdf"),
    "instal": ("Embrapa Amazônia Oriental, Instalações zootécnicas visando a produção de silagem (2004)",
               "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/900615/1/Instalacoeszootecnicas.pdf"),
    "ct114": ("Embrapa Gado de Leite, Comunicado Técnico 114: Tecnologia e custo da silagem de milho (2017)",
              "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1078472/1/CT114Tecnologiaecustosilagemdemilho.pdf"),
    "azevem": ("Epagri e Embrapa Pecuária Sul, Baldissera e outros (2018)",
               "https://www.alice.cnptia.embrapa.br/alice/handle/doc/1100511"),
}
GUIAS_EM = F.get("guias_em", F["atualizado_em"])


def fonte(k, rotulo=None):
    nome, url = FONTES[k]
    return f'<a href="{url}" rel="noopener">{rotulo or nome}</a>'


def lista_fontes(chaves):
    itens = "".join(f"<li>{fonte(k)}</li>" for k in chaves)
    return (f'<ol class="fontes">{itens}</ol><p class="nota">Fontes abertas e conferidas em '
            f'<time datetime="{GUIAS_EM}">{data_br(GUIAS_EM)}</time>. Preço e estoque são da própria estância, '
            f'atualizados em {DATA_HTML}.</p>')


def citacoes(chaves):
    return [{"@type": "CreativeWork", "name": FONTES[k][0], "url": FONTES[k][1]} for k in chaves]


# ---------------------------------------------------------------- SILAGEM À VENDA EM SC
FRETE_T, FRETE_RS = C2, 1200                      # exemplo da calculadora de frete (não é preço de frete da estância)
FRETE_POR_T = FRETE_RS / FRETE_T
msg_sc = "Olá! Vi no site a silagem de milho à venda em SC, a R$ %s a tonelada. Sou de ___ e preciso de cerca de ___ toneladas." % PT
FONTES_SC = ["ct74", "folder", "unoesc", "pab", "cepa"]
FAQ_SC, LD_SC = faq([
    ("Onde comprar silagem de milho em Santa Catarina?",
     f"A {NOME} vende silagem de milho em {LOCAL}, no Oeste catarinense: {T} toneladas a R$ {PT} a tonelada em {MESANO}, com retirada no silo. "
     f"A entrega vai {ALC}, em cidades como {CID_TXT}, e compensa mais em carga fechada de {CARGA} (R$ {PC1} a R$ {PC2} por carga, sem frete)."),
    ("Qual o preço da tonelada de silagem em SC?",
     f"Não existe preço oficial da silagem em Santa Catarina: cada vendedor define o seu, e o valor muda com a safra e com a região. "
     f"Na {NOME}, em {LOCAL}, a silagem de milho custa R$ {PT} a tonelada (R$ {PKG} o quilo) em {MESANO} para pedidos a partir de {MIN} t, sem frete. Abaixo de {MIN} t, R$ {PTM}, sob consulta."),
    ("Como comprar silagem de milho de outro produtor?",
     f"Pergunte o preço por tonelada e a partir de quantas toneladas ele vale, quanto cabe no caminhão, se há entrega e até onde, se há laudo e de onde sai a silagem, e veja a face do silo antes de carregar. "
     f"Na {NOME}: {PRECO_REGRA}; um caminhão leva {CARGA}; entrega {ALC}; laudo em andamento; carregamento direto da face do silo trincheira."),
    ("Silagem ensacada ou a granel: qual sai mais barata?",
     f"Compare sempre por tonelada. Para converter o saco, divida o preço pelo peso do saco e multiplique por mil: um saco de 25 kg a R$ 15 (exemplo) sai a R$ 600 a tonelada. "
     f"A {NOME} vende a granel, por tonelada, a R$ {PT}, carregada da face do silo no caminhão do comprador."),
    ("Vocês vendem silagem em bola?",
     f"A silagem de milho da {NOME} é vendida a granel, por tonelada. Em bolas, vendemos o <a href=\"/pre-secado-a-venda/\">pré-secado de azevém, a R$ {PB} a bola de cerca de {KG} kg</a>, "
     f"que muitos produtores chamam de bola de silagem."),
    ("Dá para comprar silagem e guardar de novo no meu silo?",
     f"Dá, e é comum, mas quanto antes melhor. Um estudo publicado em 2018 na Pesquisa Agropecuária Brasileira mostrou que reensilar a silagem de milho depois de 36 horas exposta ao ar "
     f"reduziu o valor nutritivo e aumentou as perdas de matéria seca. Combine a retirada para compactar e cobrir no mesmo dia."),
    ("Vocês entregam a silagem em SC?",
     f"Sim, {ALC} de {LOCAL}. O frete é orçado pelo WhatsApp conforme a distância e a carga. Mais longe que isso, a retirada é no silo com o seu freteiro; use a calculadora desta página para somar o frete ao preço."),
])
sc = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Silagem à venda em SC</p>
<p class="pill"><i></i><span>{T} t disponíveis · atualizado em {DATA_HTML}</span></p>
<h1>Silagem à venda em SC: onde comprar, quanto custa com frete e como avaliar</h1>
<p class="sub">A {NOME} vende silagem de milho a granel, por tonelada, em {LOCAL}. Em {MESANO} são {T} toneladas a R$ {PT} a tonelada a partir de {MIN} t, com retirada no silo ou entrega {ALC}, em cidades como {CIDADES[0]}, {CIDADES[1]} e {CIDADES[2]}.</p>
<div class="selos">
<div><b>R$ {PT}</b><span>a tonelada, sem frete</span></div>
<div><b>{T} t</b><span>em estoque em {MESANO}</span></div>
<div><b>{EMAX} km</b><span>de estrada até onde entregamos</span></div>
</div>
<div class="acoes">{wa(msg_sc, "heroi-silagem-sc", "Pedir pelo WhatsApp", "bt claro")}<a class="bt linha" href="#frete">Somar o frete</a></div>
{PROVA}
</div>
<figure>{img("silo-trincheira-lateral", f"Silo trincheira de silagem de milho com muro de tijolo e lona presa por sacos, na {NOME}, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Resposta rápida</p>
<h2>Onde comprar silagem de milho em SC hoje?</h2>
<p class="lead">Em {MESANO}, a {NOME} ({MARCA}), em {LOCAL}, tem {T} toneladas de silagem de milho à venda a R$ {PT} a tonelada, o que dá R$ {PKG} por quilo. A venda é a granel, por tonelada, com carregamento direto da face do silo trincheira para o caminhão do comprador.</p>
<div class="rolagem"><table>
<caption>Silagem de milho à venda em SC na {NOME}, {LOCAL}. Atualizado em {DATA_HTML}.</caption>
<tbody>
<tr><th scope="row">Onde</th><td>{LOCAL}, Oeste catarinense (microrregião de Concórdia)</td></tr>
<tr><th scope="row">Preço</th><td><b>R$ {PT} por tonelada</b> a partir de {MIN} t (R$ {PKG} por kg). Abaixo de {MIN} t, R$ {PTM} a tonelada, sob consulta de disponibilidade. Sem frete</td></tr>
<tr><th scope="row">Estoque</th><td>{T} toneladas em {MESANO}</td></tr>
<tr><th scope="row">Forma de venda</th><td>A granel, por tonelada, carregada da face do silo</td></tr>
<tr><th scope="row">Carga fechada</th><td><a href="/carga-de-silagem/">{CARGA} por caminhão, R$ {PC1} a R$ {PC2}</a></td></tr>
<tr><th scope="row">Retirada</th><td>No silo, em dia e horário combinados. Entrega {ALC}, com frete orçado</td></tr>
<tr><th scope="row">Cidades atendidas</th><td>{CID_TXT}, entre os {N_ENT} municípios a até {EMAX} km de estrada</td></tr>
<tr><th scope="row">Análise bromatológica</th><td>Em andamento; o laudo será publicado na <a href="/silagem-de-milho/">página da silagem de milho</a></td></tr>
</tbody></table></div>
<p class="nota">Detalhes da oferta, fotos dos silos e a calculadora de toneladas por rebanho estão na página <a href="/silagem-de-milho/">silagem de milho a R$ {PT} a tonelada</a>.</p>
</div></section>

<section id="frete"><div class="wrap">
<p class="rot">Calculadora de frete</p>
<h2>Quanto a silagem custa entregue na sua propriedade?</h2>
<p class="lead">Na {NOME}, em {LOCAL}, a silagem de milho custa R$ {PT} a tonelada em {MESANO}, sem frete. Entregue, ela custa R$ {PT} mais o frete da viagem dividido pelas toneladas da carga. Numa carga fechada de {CARGA}, o frete se divide por mais toneladas. Peça o orçamento do nosso frete pelo WhatsApp (até cerca de {EMAX} km de estrada) ou o valor da viagem ao seu freteiro, e preencha.</p>
<div class="caixa">
<form id="frete-calc" data-preco="{S['preco_tonelada']}" data-preco-menor="{S['preco_tonelada_menor']}" data-minimo="{MIN}">
<div class="campos3">
<div class="campo"><label for="carga">Toneladas na carga</label><input id="carga" name="carga" type="number" inputmode="decimal" min="1" step="0.5" value="{FRETE_T}"></div>
<div class="campo"><label for="viagem">Frete da viagem (R$)</label><input id="viagem" name="viagem" type="number" inputmode="decimal" min="0" step="10" value="{FRETE_RS}"></div>
<div class="campo"><label for="cargas">Número de viagens</label><input id="cargas" name="cargas" type="number" inputmode="numeric" min="1" value="1"></div>
</div>
<p class="nota">Os valores iniciais são só um exemplo, não o frete da {NOME}, que é orçado pelo WhatsApp. Silagem é pesada e úmida, então quanto mais longe, mais o frete pesa em cada tonelada.</p>
</form>
<div class="saida" id="frete-saida" aria-live="polite">
<div class="num">R$ {br(S['preco_tonelada'] + FRETE_POR_T, 2)} <small>por tonelada entregue</small></div>
<p>Exemplo: R$ {PT} da tonelada + R$ {br(FRETE_RS)} de frete ÷ {FRETE_T} t = R$ {br(FRETE_POR_T, 2)} de frete por tonelada. A carga de {FRETE_T} t sai por R$ {br(FRETE_T * S['preco_tonelada'] + FRETE_RS)} no total.</p>
{wa(f"Olá! Quero {FRETE_T} t de silagem de milho a R$ {PT} a tonelada. Ainda tem disponível?", "calculadora-frete", "Pedir essa carga no WhatsApp")}
</div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Antes de fechar</p>
<h2>Como avaliar silagem de milho antes de comprar</h2>
<p class="lead">Silagem de milho boa tem de 30% a 35% de matéria seca no corte, pH entre 3,8 e 4,2, cor verde a verde-amarelada e cheiro suave, segundo a Embrapa Gado de Leite ({fonte("ct74", "Comunicado Técnico 74, 2014")}). Na hora da compra, quem não tem laudo confere com os olhos, o nariz e a mão.</p>
<div class="rolagem"><table>
<caption>Sinais de qualidade da silagem de milho na hora da compra. Referência: {fonte("ct74")}; descarte do mofo: {fonte("folder", "Embrapa Gado de Leite, folder de silagem")}.</caption>
<thead><tr><th scope="col">O que conferir</th><th scope="col">Sinal bom</th><th scope="col">Sinal de alerta</th></tr></thead>
<tbody>
<tr><th scope="row">Cor</th><td>Verde a verde-amarelada</td><td>Marrom-escura ou preta (putrefação)</td></tr>
<tr><th scope="row">Cheiro</th><td>Suave e agradável</td><td>Manteiga rançosa (fermentação butírica), vinagre forte, queimado ou mofo</td></tr>
<tr><th scope="row">Umidade (espremer na mão)</th><td>Não escorre água</td><td>Escorre água: silagem úmida demais</td></tr>
<tr><th scope="row">Mofo</th><td>Ausente na face do silo</td><td>Odor forte de mofo e partes mofadas, que devem ser retiradas e descartadas antes de dar ao gado</td></tr>
<tr><th scope="row">Temperatura da massa</th><td>Fresca ao toque</td><td>Massa quente: sinal de deterioração pelo ar</td></tr>
<tr><th scope="row">Laudo</th><td>Matéria seca de 30% a 35% no corte e pH de 3,8 a 4,2</td><td>Vendedor que promete número sem laudo</td></tr>
</tbody></table></div>
<p class="nota">A {NOME} ainda não tem laudo bromatológico publicado. {BROMA} Na retirada, a silagem sai da face do silo, onde esses sinais podem ser conferidos antes de carregar.</p>
</div></section>

<section id="perguntar"><div class="wrap">
<p class="rot">Antes de pedir</p>
<h2>O que perguntar a quem vende silagem de milho</h2>
<p class="lead">Seis perguntas resolvem a maior parte das dúvidas de uma compra de silagem a granel. A coluna da direita traz as respostas da {NOME}, para você comparar com outras ofertas.</p>
<div class="rolagem"><table>
<caption>Perguntas para fazer ao vendedor de silagem e as respostas da {NOME}, {LOCAL}. Atualizado em {DATA_HTML}.</caption>
<thead><tr><th scope="col">Pergunta</th><th scope="col">Por que importa</th><th scope="col">Na {NOME}</th></tr></thead>
<tbody>
<tr><th scope="row">Qual o preço por tonelada, e a partir de quantas toneladas?</th><td>O preço pode mudar com a quantidade pedida.</td><td>{PRECO_REGRA[0].upper() + PRECO_REGRA[1:]}.</td></tr>
<tr><th scope="row">Quanto cabe num caminhão?</th><td>A silagem enche a carroceria antes do limite de peso: é a cubagem que define a carga.</td><td>Em geral {CARGA} por caminhão: <a href="/carga-de-silagem/">R$ {PC1} a R$ {PC2} por carga</a>.</td></tr>
<tr><th scope="row">Entrega? Até onde?</th><td>O frete pode pesar mais que a diferença de preço entre dois vendedores.</td><td>Entrega {ALC}, com frete orçado. <a href="/regiao/">Ver as cidades</a>.</td></tr>
<tr><th scope="row">Quanto tem em estoque?</th><td>Quem precisa de várias cargas quer saber se o vendedor atende a estação.</td><td>{T} toneladas em {MESANO}, ou {N_CARGAS} cargas de {C2} t.</td></tr>
<tr><th scope="row">Tem laudo bromatológico?</th><td>É o laudo que mostra matéria seca e valor nutritivo; sem ele, confira cor, cheiro e mofo.</td><td>Em andamento; nenhum número é informado antes do laudo.</td></tr>
<tr><th scope="row">De onde sai a silagem?</th><td>Silagem carregada direto da face do silo passa menos tempo exposta ao ar.</td><td>Da face do silo trincheira, direto no caminhão, onde dá para conferir antes de carregar.</td></tr>
</tbody></table></div>
</div></section>

<section class="escura"><div class="wrap">
<p class="rot">Depois de retirar</p>
<h2>Quanto tempo a silagem comprada aguenta fora do silo?</h2>
<p class="lead">Silagem de milho retirada do silo deve ser fornecida em até 48 horas de exposição ao ar, segundo um estudo da Unoesc (SC), ou reensilada no mesmo dia: reensilar depois de 36 horas reduziu o valor nutritivo, segundo a Pesquisa Agropecuária Brasileira (2018).</p>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>O ar começa a estragar</h3><p>A deterioração começa assim que a silagem é exposta ao ar: a temperatura sobe e os microrganismos decompositores agem. A Embrapa estima em até 15% a perda por deterioração depois da descarga e a classifica como evitável ({fonte("ct74", "Embrapa, 2014")}).</p></div>
<div class="passo"><p class="n">02</p><h3>Use em até 48 horas</h3><p>Um estudo da Unoesc, em Santa Catarina, concluiu que não seria aconselhável fornecer silagem de milho depois de 48 horas de exposição ao ar ({fonte("unoesc", "Unoesc")}). Leve só o que o rebanho consome nesse prazo ou reensile.</p></div>
<div class="passo"><p class="n">03</p><h3>Reensile no mesmo dia</h3><p>Reensilar depois de 36 horas no ar reduziu o valor nutritivo e aumentou as perdas, segundo a Pesquisa Agropecuária Brasileira ({fonte("pab", "PAB, 2018")}). Compacte e cubra com lona assim que a carga chegar.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Por que no Oeste</p>
<h2>O Oeste catarinense concentra a silagem de milho de SC</h2>
<div class="midia">
<div>{img("silagem-face-parede", f"Silagem de milho compactada junto à parede de um silo trincheira na {NOME}")}</div>
<div><p>As microrregiões de São Miguel do Oeste, Chapecó e Concórdia, ligadas à pecuária leiteira, respondem por mais de 50% da produção de silagem de Santa Catarina, segundo o Boletim Agropecuário da Epagri/Cepa de janeiro de 2025 ({fonte("cepa", "Agrolink, 2025")}). {CID} fica na microrregião de Concórdia.</p>
<p>Para quem compra, isso significa oferta perto e frete curto. A {NOME} atende {CID_TXT} e outros municípios {ALC}. Veja <a href="/regiao/">como funciona a entrega e quais cidades são atendidas</a>.</p>
<p>Também precisa de volumoso em bola? Veja o <a href="/pre-secado-a-venda/">pré-secado à venda, em bolas de cerca de {KG} kg</a>.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem procura silagem à venda em SC</h2>
{FAQ_SC}</div></section>

<section><div class="wrap texto">
<p class="rot">Como esta página foi feita</p>
<h2>Fontes e método</h2>
<p>Preço, estoque, forma de venda e fotos são da própria {NOME}, em {LOCAL}, e mudam nesta página quando mudam na estância. Os critérios de qualidade e de conservação vêm de publicações técnicas abertas, citadas abaixo. Onde não encontramos fonte (por exemplo, uma temperatura de referência em graus para conferir a massa), não informamos número.</p>
{lista_fontes(FONTES_SC)}
</div></section>
{chamada(f"{T} toneladas em {CID}, R$ {PT} a tonelada", f"Diga a sua cidade em SC e quantas toneladas precisa. Confirmamos o estoque na hora.", msg_sc, "chamada-silagem-sc")}
"""
pagina("/silagem-a-venda-sc/", "Silagem à venda em SC: preço com frete e como avaliar",
       f"Silagem de milho à venda em SC: {T} t a R$ {PT}/t a partir de {MIN} t em {LOCAL}. Some o frete, veja como avaliar a silagem e as cidades atendidas.",
       sc, [NEGOCIO, LD_SC, migalha("Silagem à venda em SC", "/silagem-a-venda-sc/")],
       msg_sc, f"Silagem em SC · R$ {PT} a tonelada", og="og-silagem.jpg",
       extra={"datePublished": GUIAS_EM, "dateModified": max(GUIAS_EM, F["atualizado_em"]), "mainEntity": {"@id": f"{DOM}/silagem-de-milho/#produto"}, "citation": citacoes(FONTES_SC),
              "spatialCoverage": {"@type": "State", "name": "Santa Catarina"}})

# ---------------------------------------------------------------- CARGA FECHADA DE SILAGEM (comprador de caminhão)
CARGA_EM = "2026-11-23"                         # data de publicação da página
FONTES_CG = ["unoesc", "pab", "ct74", "ct114", "acre", "instal"]
msg_cg = f"Olá! Vi no site a carga fechada de silagem de milho ({CARGA}). Sou de ___ e preciso de ___ cargas."
EX_A, EX_K, EX_D = 100, 30, 180                  # exemplo da calculadora (não é recomendação de dieta)
EX_T = EX_A * EX_K * EX_D / 1000
POR_DIA = C2 * 1000 / 2                         # kg/dia para fornecer uma carga de C2 t em 48 h
ANIMAIS_48H = int(POR_DIA // EX_K)
FRETE_EX = [4, C1, C2]                          # toneladas na viagem, para mostrar o frete dividido
CID_CG = sorted([z for z in MUNS_E if z.get("slug")], key=lambda z: z["estrada_km"])


linhas_cg = "".join(
    f'<tr><th scope="row">{q} carga{"s" if q > 1 else ""} de {t} t</th><td>{br(q * t)} t</td><td><b>R$ {br(q * t * S["preco_tonelada"])}</b></td></tr>'
    for q, t in ((1, C1), (1, C2), (2, C2), (5, C2), (10, C2))) + (
    f'<tr><th scope="row">Pedido menor que {MIN} t (exemplo: 4 t)</th><td>4 t</td><td>R$ {br(4 * S["preco_tonelada_menor"])}, a R$ {PTM} a tonelada, sob consulta de disponibilidade</td></tr>')
linhas_fr = "".join(
    f'<tr><th scope="row">{t} t na viagem</th><td>R$ {br(FRETE_RS)}</td><td>R$ {br(FRETE_RS / t, 2)}</td><td>R$ {br(preco_t(t) + FRETE_RS / t, 2)} (silagem a R$ {br(preco_t(t))})</td></tr>'
    for t in FRETE_EX)
linhas_cid_cg = "".join(
    f'<tr><th scope="row"><a href="/entrega/{z["slug"]}/">{z["nome"]} ({z["uf"]})</a></th><td>{z["estrada_km"]} km</td><td>{tempo(z["estrada_min"])}</td></tr>'
    for z in CID_CG)
FAQ_CG, LD_CG = faq([
    ("Quanto custa uma carga de silagem de milho?",
     f"Na {NOME}, em {LOCAL}, uma carga fechada de {CARGA} de silagem de milho custa de R$ {PC1} a R$ {PC2} em {MESANO}, a R$ {PT} a tonelada, sem frete. "
     f"Entregue, soma-se o frete da viagem, orçado pelo WhatsApp."),
    ("Quantas toneladas de silagem cabem num caminhão?",
     f"Em geral, um caminhão leva, pela cubagem da carroceria, o equivalente a {CARGA} de silagem de milho. A silagem enche a carroceria antes de chegar ao limite de peso, então o volume é o que manda. "
     f"Por isso a {NOME} trabalha com a carga fechada de {CARGA}."),
    (f"E se eu precisar de menos de {MIN} toneladas?",
     f"Dá, sob consulta. Abaixo de {MIN} t a tonelada sai a R$ {PTM}, e não R$ {PT}, e o pedido depende de disponibilidade. Pergunte pelo WhatsApp antes de vir."),
    ("Quanto tempo dura uma carga de silagem para gado de leite?",
     f"Pouco tempo. Exemplo: 50 vacas comendo {EX_K} kg de silagem por dia, a referência de planejamento da Embrapa, consomem {br(50 * EX_K / 1000, 1)} t por dia, então uma carga de {C2} t dura cerca de {round(C2 * 1000 / (50 * EX_K))} dias. "
     f"Para saber quantas cargas o rebanho pede na estação, use a calculadora desta página com o consumo indicado pelo seu técnico."),
    ("Vocês entregam a carga de silagem?",
     f"Sim, {ALC} de {LOCAL}, com frete orçado pelo WhatsApp conforme a distância. {REGRA_ENTREGA} "
     f"Nos municípios que passam de {EMAX} km pela estrada, a entrega é sob consulta."),
    ("Dá para comprar várias cargas de silagem?",
     f"Sim. Em {MESANO}, o estoque é de {T} toneladas, o equivalente a {N_CARGAS} cargas de {C2} t. "
     f"Diga quantas cargas e em que datas, e confirmamos o estoque e o frete de cada viagem."),
    ("Posso buscar a carga com o meu caminhão?",
     f"Pode. A silagem é carregada da face do silo trincheira direto no seu caminhão, em {LOCAL}, em dia e horário combinados. Na retirada não há frete: você paga só as toneladas, a R$ {PT} a partir de {MIN} t."),
    ("Quanto tempo uma carga de silagem aguenta depois de descarregada?",
     f"Pouco: um estudo da Unoesc (SC) concluiu que não é aconselhável fornecer silagem de milho depois de 48 horas de exposição ao ar, "
     f"e reensilar depois de 36 horas reduziu o valor nutritivo, segundo a Pesquisa Agropecuária Brasileira (2018). Quem não consome a carga em dois dias deve reensilar no mesmo dia."),
    ("A silagem tem análise bromatológica?", BROMA),
])
cg = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Carga fechada de silagem</p>
<p class="pill"><i></i><span>{N_CARGAS} cargas de {C2} t em estoque · atualizado em {DATA_HTML}</span></p>
<h1>Carga de silagem de milho: quanto custa o caminhão fechado</h1>
<p class="sub">Na {NOME}, a carga fechada de {CARGA} de silagem de milho custa de R$ {PC1} a R$ {PC2} (R$ {PT} a tonelada), sem frete. Ela é carregada da face do silo no caminhão, com entrega {ALC} ou retirada em {LOCAL}.</p>
<div class="selos">
<div><b>R$ {PC1} a {PC2}</b><span>por carga de {CARGA}</span></div>
<div><b>{N_CARGAS} cargas</b><span>de {C2} t no estoque de {T} t</span></div>
<div><b>{EMAX} km</b><span>de estrada até onde entregamos</span></div>
</div>
<div class="acoes">{wa(msg_cg, "heroi-carga", "Pedir cargas pelo WhatsApp", "bt claro")}<a class="bt linha" href="#calculadora">Quantas cargas eu preciso</a></div>
{PROVA}
</div>
<figure>{img("silo-coberto-eucaliptos", f"Silo trincheira de silagem de milho coberto com lona e sacos de peso, de onde sai a carga fechada, na {NOME}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Resposta rápida</p>
<h2>Quanto custa uma carga de silagem de milho?</h2>
<p class="lead">Em {MESANO}, a {NOME} ({MARCA}), em {LOCAL}, vende silagem de milho a granel a R$ {PT} a tonelada. Uma carga fechada de {C1} toneladas custa R$ {PC1} e uma de {C2} toneladas, R$ {PC2}, sem frete. O estoque de {T} toneladas dá {N_CARGAS} cargas de {C2} t.</p>
<div class="rolagem"><table>
<caption>Preço da silagem de milho por carga na {NOME}, {LOCAL}. Atualizado em {DATA_HTML}. Sem frete.</caption>
<thead><tr><th scope="col">Pedido</th><th scope="col">Toneladas</th><th scope="col">Preço na estância</th></tr></thead>
<tbody>{linhas_cg}</tbody></table></div>
<p class="nota">{PRECO_REGRA[0].upper() + PRECO_REGRA[1:]}. Detalhes do produto, fotos e armazenagem na página da <a href="/silagem-de-milho/">silagem de milho</a>.</p>
</div></section>

<section><div class="wrap">
<p class="rot">Por que carga fechada</p>
<h2>A carga fechada sai mais barata por tonelada entregue</h2>
<p class="lead">Dois motivos. O preço: a partir de {MIN} t a tonelada sai a R$ {PT}; abaixo disso, a R$ {PTM}, sob consulta. E o frete: ele é de uma viagem, não de uma tonelada. Um caminhão comum leva, pela cubagem da carroceria, o equivalente a {CARGA} de silagem; quanto mais cheio, menor o frete em cada tonelada.</p>
<div class="rolagem"><table>
<caption>Exemplo com uma viagem de R$ {br(FRETE_RS)}. O valor é só ilustrativo: o frete da {NOME} é orçado caso a caso pelo WhatsApp.</caption>
<thead><tr><th scope="col">Carga</th><th scope="col">Frete da viagem (exemplo)</th><th scope="col">Frete por tonelada</th><th scope="col">Tonelada entregue</th></tr></thead>
<tbody>{linhas_fr}</tbody></table></div>
<p class="nota">Com o valor real do frete, faça a conta na <a href="/silagem-a-venda-sc/#frete">calculadora de frete da silagem</a>.</p>
</div></section>

<section id="calculadora"><div class="wrap">
<p class="rot">Calculadora</p>
<h2>Quantas cargas de silagem o seu rebanho precisa?</h2>
<p class="lead">A conta é: animais × quilos de silagem por animal por dia × dias, dividido por mil, dá as toneladas. Dividido por {C2}, dá as cargas.</p>
<div class="caixa">
<form id="calc" data-preco="{S['preco_tonelada']}" data-preco-menor="{S['preco_tonelada_menor']}" data-minimo="{MIN}" data-estoque="{S['toneladas']}" data-carga="{C2}">
<div class="campos3">
<div class="campo"><label for="animais">Animais</label><input id="animais" name="animais" type="number" inputmode="numeric" min="1" value="{EX_A}"></div>
<div class="campo"><label for="kg">Kg por animal/dia</label><input id="kg" name="kg" type="number" inputmode="decimal" min="1" step="0.5" value="{EX_K}"></div>
<div class="campo"><label for="dias">Dias</label><input id="dias" name="dias" type="number" inputmode="numeric" min="1" value="{EX_D}"></div>
</div>
<p class="nota">Os valores iniciais são só um exemplo. Para planejar, a Embrapa usa 30 kg de silagem por vaca por dia (<a href="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1039523/1/25971.pdf" rel="noopener">Embrapa Acre, 2015</a>), mas o consumo muda com a categoria, o peso e o resto da dieta: use o número indicado pelo seu técnico ou nutricionista.</p>
</form>
<div class="saida" id="calc-saida" aria-live="polite">
<div class="num">{br(EX_T)} <small>toneladas</small></div>
<p>Exemplo: {EX_A} animais × {EX_K} kg por dia × {EX_D} dias = {br(EX_T)} toneladas, ou {cargas(EX_T)}. A R$ {PT} a tonelada, dá R$ {br(EX_T * S['preco_tonelada'])}, sem frete.</p>
{wa(f"Olá! Preciso de cerca de {br(EX_T)} t de silagem de milho ({cargas(EX_T)}). Ainda tem disponível?", "calculadora", "Pedir essas cargas no WhatsApp")}
</div>
</div></div></section>

<section class="escura"><div class="wrap">
<p class="rot">Como comprar</p>
<h2>Como funciona a compra de uma carga</h2>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>Diga cargas e cidade</h3><p>Pelo WhatsApp, diga quantas cargas, em que datas e onde fica a propriedade. Confirmamos o estoque na hora.</p></div>
<div class="passo"><p class="n">02</p><h3>Receba o frete</h3><p>Orçamos o frete de cada viagem até a sua propriedade, {ALC}. O preço da silagem é o publicado: R$ {PT} a tonelada.</p></div>
<div class="passo"><p class="n">03</p><h3>Carregue e descarregue no mesmo dia</h3><p>A silagem sai da face do silo trincheira direto no caminhão. Combine a descarga para usar ou reensilar no mesmo dia.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Entrega da carga</p>
<h2>Até onde a carga fechada é entregue</h2>
<p class="lead">A {NOME} entrega {ALC} de {LOCAL}, em {N_ENT} municípios de Santa Catarina e do Rio Grande do Sul. Em {", ".join(z["nome"] for z in MUNS_C[:-1])} e {MUNS_C[-1]["nome"]}, que passam de {EMAX} km pela estrada, a entrega é sob consulta.</p>
<div class="rolagem"><table>
<caption>Distância pela estrada da estância, em {LOCAL}, até a sede dos municípios com página própria. Aproximada, calculada com o OpenStreetMap.</caption>
<thead><tr><th scope="col">Município</th><th scope="col">Estrada (aprox.)</th><th scope="col">Tempo de carro</th></tr></thead>
<tbody>{linhas_cid_cg}</tbody></table></div>
<p class="nota">Todas as cidades, com linha reta, estrada e rebanho leiteiro: <a href="/regiao/">entrega e região</a>.</p>
</div></section>

<section><div class="wrap">
<p class="rot">Depois que a carga chega</p>
<h2>Uma carga de {C2} t precisa ser usada ou reensilada logo</h2>
<p class="lead">Silagem de milho fora do silo deve ser fornecida em até 48 horas de exposição ao ar, segundo um estudo da Unoesc ({fonte("unoesc", "Unoesc, SC")}). Para gastar {C2} toneladas em 48 horas, são {br(POR_DIA)} kg por dia: a {EX_K} kg por animal, cerca de {ANIMAIS_48H} animais. Rebanho menor deve reensilar a carga no mesmo dia.</p>
<div class="midia">
<div>{img("silo-parede-madeira-1", f"Silo trincheira de parede de madeira escorada, com silos graneleiros ao fundo, na {NOME}", w=1280, h=960, sizes="(min-width:901px) 540px, 100vw")}</div>
<div><p>Reensilar depois de 36 horas no ar reduziu o valor nutritivo e aumentou as perdas de matéria seca, segundo a Pesquisa Agropecuária Brasileira ({fonte("pab", "PAB, 2018")}). Por isso, combine o dia da carga com o dia em que você vai compactar e cobrir com lona.</p>
<p>A Embrapa estima em até 15% a perda por deterioração depois que a silagem sai do silo e a classifica como evitável ({fonte("ct74", "Embrapa, 2014")}). Na carga fechada, a {NOME} carrega a silagem direto da face do silo, para ela sair da estância com o mínimo de tempo no ar.</p>
<p>Para reensilar, a Embrapa recomenda, na ensilagem, camadas de no máximo 20 cm bem compactadas e lona de pelo menos 200 micras, com pesos por cima ({fonte("ct114", "Comunicado Técnico 114, 2017")}). Faça isso no mesmo dia em que a carga chega.</p>
<p>Como avaliar a silagem antes de carregar: veja <a href="/silagem-a-venda-sc/">silagem à venda em SC</a>.</p></div>
</div>
</div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem compra silagem por carga</h2>
{FAQ_CG}</div></section>

<section><div class="wrap texto">
<p class="rot">Como esta página foi feita</p>
<h2>Fontes e método</h2>
<p>Preço, estoque, tamanho da carga fechada e forma de carregamento são da própria {NOME}, em {LOCAL}. O frete da tabela é um exemplo, não um preço. As distâncias vêm de rotas calculadas sobre o OpenStreetMap e são aproximadas. Os prazos de uso e reensilagem vêm das publicações abaixo.</p>
{lista_fontes(FONTES_CG)}
</div></section>
{chamada(f"{N_CARGAS} cargas de {C2} t em {CID}", f"R$ {PC1} a R$ {PC2} por carga, sem frete. Diga quantas cargas e a sua cidade.", msg_cg, "chamada-carga")}
"""
prod_ref = {"@id": f"{DOM}/silagem-de-milho/#produto"}
oferta_cg = {"@type": "Offer", "@id": f"{DOM}/carga-de-silagem/#oferta", "name": f"Carga fechada de silagem de milho ({CARGA})",
             "description": f"Carga fechada de {CARGA} de silagem de milho a granel: R$ {PC1} a R$ {PC2} por carga, a R$ {PT} a tonelada, sem frete.",
             "itemOffered": prod_ref, "price": S["preco_tonelada"], "priceCurrency": "BRL", "availability": "https://schema.org/InStock",
             "priceSpecification": SPEC_SIL,
             "inventoryLevel": {"@type": "QuantitativeValue", "value": S["toneladas"], "unitCode": "TNE"},
             "availableDeliveryMethod": ["https://schema.org/OnSitePickup", "http://purl.org/goodrelations/v1#DeliveryModeFreight"], "seller": {"@id": f"{DOM}/#estancia"}, "areaServed": NEGOCIO["areaServed"]}
pagina("/carga-de-silagem/", "Carga de silagem de milho: preço do caminhão fechado",
       f"Quanto custa uma carga de silagem de milho: {C1} a {C2} t por caminhão, R$ {PC1} a R$ {PC2} em {LOCAL}, sem frete. Entrega até {EMAX} km de estrada.",
       cg, [NEGOCIO, oferta_cg, LD_CG, migalha("Carga fechada de silagem", "/carga-de-silagem/")],
       msg_cg, f"Carga de {CARGA} · R$ {PC1} a {PC2}", og="og-silagem.jpg",
       extra={"datePublished": CARGA_EM, "dateModified": max(CARGA_EM, F["atualizado_em"]), "mainEntity": {"@id": f"{DOM}/carga-de-silagem/#oferta"},
              "citation": citacoes(FONTES_CG)})

# ---------------------------------------------------------------- PRÉ-SECADO À VENDA
msg_pv = "Olá! Vi no site o pré-secado à venda a R$ %s a bola. Sou de ___ e quero ___ bolas." % PB
FONTES_PV = ["uepg", "uky", "aces", "teagasc", "uky_q", "semina", "ufms", "ct74", "azevem"]
FAQ_PV, LD_PV = faq([
    ("Quanto custa uma bola de pré-secado?",
     f"Na {NOME}, em {LOCAL}, a bola de pré-secado de azevém custa R$ {PB} em {MESANO}. Cada bola pesa cerca de {KG} kg (de {KMIN} a {KMAX} kg), "
     f"o que dá de R$ {PKG_MIN} a R$ {PKG_MAX} por quilo, sem frete. Para comparar com outra oferta, divida o preço pelo peso da bola."),
    ("Quanto pesa uma bola de pré-secado?",
     f"Bolas de pré-secado costumam ter de 400 a 600 kg, segundo o professor João Ricardo Alves Pereira, da UEPG. As da {NOME} pesam cerca de {KG} kg, "
     f"com variação de {P['variacao_kg']} kg para mais ou para menos, porque o peso depende da umidade e da compactação de cada bola."),
    ("Bola mais pesada é sempre mais vantajosa?",
     "Não necessariamente. Como o pré-secado costuma ser vendido por bola, e não por peso, há bolas pesadas porque têm mais água, não mais alimento. "
     "O professor João Ricardo Alves Pereira, da UEPG, alerta (Canal do Leite, 2019) que boa parte do pré-secado ainda é vendida com matéria seca baixa. Se o vendedor tiver laudo, compare o preço por quilo de matéria seca."),
    ("Bola de silagem e pré-secado são a mesma coisa?",
     f"Na maioria das conversas, sim: \"bola de silagem\", \"silagem pré-secada\" e \"pré-secado\" são nomes para o capim cortado, murcho no campo e enfardado em bolas embaladas em filme. "
     f"A {NOME} vende pré-secado de azevém em bolas; a silagem de milho é vendida <a href=\"/silagem-a-venda-sc/\">a granel, por tonelada</a>."),
    ("Pré-secado é feno?",
     "Não. O feno é desidratado até cerca de 10% a 15% de umidade e guardado sem embalagem. O pré-secado é enfardado bem mais úmido, entre 40% e 60% de matéria seca, "
     "e fermenta dentro do filme, sem ar."),
    ("Quanto tempo uma bola de pré-secado dura depois de aberta?",
     "A extensão rural do Alabama (EUA) recomenda oferecer a bola aberta de modo que os animais a consumam em 1 a 2 dias, e a da University of Kentucky fala em menos de dois dias quando a fermentação não foi a ideal. "
     "Não encontramos recomendação brasileira com prazo diferente."),
    ("Vocês vendem poucas bolas?",
     f"Sim. A venda é por unidade: leve uma, dez ou a carga fechada. A retirada é em {LOCAL} ou o frete é combinado caso a caso."),
])
pv = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Pré-secado à venda</p>
<p class="pill"><i></i><span>Disponível hoje · atualizado em {DATA_HTML}</span></p>
<h1>Pré-secado à venda: quanto custa, quanto pesa e como comparar bolas</h1>
<p class="sub">Pré-secado de azevém (também chamado de bola de silagem ou silagem pré-secada) em bolas embaladas em filme, de {KMIN} a {KMAX} kg. R$ {PB} a bola, ou de R$ {PKG_MIN} a R$ {PKG_MAX} o quilo, com retirada na {NOME}.</p>
<div class="selos">
<div><b>R$ {PB}</b><span>por bola, sem frete</span></div>
<div><b>{KMIN} a {KMAX} kg</b><span>peso de cada bola</span></div>
<div><b>R$ {PKG_MIN} a {PKG_MAX}</b><span>por quilo</span></div>
</div>
<div class="acoes">{wa(msg_pv, "heroi-pre-secado-venda", "Pedir pelo WhatsApp", "bt claro")}<a class="bt linha" href="#comparar-bolas">Comparar ofertas por quilo</a></div>
{PROVA}
</div>
<figure>{img("bolas-pre-secado", f"Bolas de pré-secado embaladas em filme branco à venda na {NOME}, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Resposta rápida</p>
<h2>Quanto custa e quanto pesa uma bola de pré-secado?</h2>
<p class="lead">Na {NOME}, em {LOCAL}, a bola de pré-secado de azevém custa R$ {PB} em {MESANO} e pesa cerca de {KG} kg, entre {KMIN} e {KMAX} kg. Isso dá de R$ {PKG_MIN} a R$ {PKG_MAX} por quilo, sem frete. No mercado, as bolas costumam ter de 400 a 600 kg ({fonte("uepg", "Canal do Leite, professor da UEPG, 2019")}), por isso o preço da bola sozinho não diz qual oferta é mais barata.</p>
<div class="rolagem"><table>
<caption>Pré-secado à venda na {NOME}, {LOCAL}. Atualizado em {DATA_HTML}.</caption>
<tbody>
<tr><th scope="row">Produto</th><td>Pré-secado de azevém em bolas embaladas em filme</td></tr>
<tr><th scope="row">Preço</th><td><b>R$ {PB} por bola</b>, sem frete</td></tr>
<tr><th scope="row">Peso</th><td>Cerca de {KG} kg ({KMIN} a {KMAX} kg)</td></tr>
<tr><th scope="row">Preço por quilo</th><td>De R$ {PKG_MIN} (bola de {KMAX} kg) a R$ {PKG_MAX} (bola de {KMIN} kg)</td></tr>
<tr><th scope="row">Quantidade mínima</th><td>Uma bola. Venda por unidade</td></tr>
<tr><th scope="row">Retirada</th><td>Em {LOCAL}, Oeste de SC, ou entrega {ALC}, com frete orçado</td></tr>
<tr><th scope="row">Análise bromatológica</th><td>Em andamento; o laudo será publicado na <a href="/pre-secado-de-azevem/">página do pré-secado de azevém</a></td></tr>
</tbody></table></div>
<p class="nota">Vídeo das bolas e comparação com a silagem de milho: <a href="/pre-secado-de-azevem/">pré-secado de azevém a R$ {PB} a bola</a>.</p>
</div></section>

<section id="comparar-bolas"><div class="wrap">
<p class="rot">Comparador</p>
<h2>Qual bola de pré-secado sai mais barata por quilo?</h2>
<p class="lead">A bola de pré-secado da {NOME} sai a R$ {br(P["preco_bola"] / P["peso_bola_kg"], 2)} o quilo (R$ {PB} ÷ {KG} kg), em {MESANO}. Para comparar com outra oferta, divida o preço da bola pelo peso. Se o vendedor tiver laudo, divida também pela matéria seca: é ela que alimenta, não a água. Preencha a outra oferta que você recebeu.</p>
<div class="caixa">
<form id="bolas" data-preco="{P['preco_bola']}" data-peso="{P['peso_bola_kg']}">
<div class="campos3">
<div class="campo"><label for="b1p">Bola A: preço (R$)</label><input id="b1p" name="b1p" type="number" inputmode="decimal" min="1" value="{P['preco_bola']}"></div>
<div class="campo"><label for="b1k">Bola A: peso (kg)</label><input id="b1k" name="b1k" type="number" inputmode="decimal" min="1" value="{P['peso_bola_kg']}"></div>
<div class="campo"><label for="b1m">Bola A: matéria seca (%)</label><input id="b1m" name="b1m" type="number" inputmode="decimal" min="1" max="100" placeholder="se tiver laudo"></div>
<div class="campo"><label for="b2p">Bola B: preço (R$)</label><input id="b2p" name="b2p" type="number" inputmode="decimal" min="1" placeholder="outra oferta"></div>
<div class="campo"><label for="b2k">Bola B: peso (kg)</label><input id="b2k" name="b2k" type="number" inputmode="decimal" min="1" placeholder="peso informado"></div>
<div class="campo"><label for="b2m">Bola B: matéria seca (%)</label><input id="b2m" name="b2m" type="number" inputmode="decimal" min="1" max="100" placeholder="se tiver laudo"></div>
</div>
<p class="nota">A bola A já vem com a oferta da {NOME} (R$ {PB}, cerca de {KG} kg). Peso de bola varia: pergunte se foi pesada na balança ou estimado.</p>
</form>
<div class="saida" id="bolas-saida" aria-live="polite">
<div class="num">R$ {br(P['preco_bola'] / P['peso_bola_kg'], 2)} <small>por quilo (bola A)</small></div>
<p>R$ {PB} ÷ {KG} kg = R$ {br(P['preco_bola'] / P['peso_bola_kg'], 2)} por quilo. Preencha a bola B para comparar.</p>
{wa(msg_pv, "comparador-bolas", "Pedir bolas no WhatsApp")}
</div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Pré-secado, feno ou silagem</p>
<h2>Qual a diferença entre pré-secado, feno e silagem de milho?</h2>
<p class="lead">A diferença principal é a água. O feno é seco até 10% a 15% de umidade ({fonte("ufms", "UFMS, 2019")}); o pré-secado é enfardado com 40% a 60% de matéria seca ({fonte("uky", "University of Kentucky, 2025")}); a silagem de milho é cortada com 30% a 35% de matéria seca ({fonte("ct74", "Embrapa, 2014")}).</p>
<div class="rolagem"><table>
<caption>Feno, pré-secado e silagem de milho comparados. Fontes: UFMS (2019), University of Kentucky (2025) e Embrapa Gado de Leite (2014).</caption>
<thead><tr><th scope="col">Volumoso</th><th scope="col">Água ou matéria seca de referência</th><th scope="col">Como é guardado</th><th scope="col">Na {NOME}</th></tr></thead>
<tbody>
<tr><th scope="row">Feno</th><td>10% a 15% de umidade</td><td>Seco, sem embalagem vedada</td><td>Fora do nosso catálogo</td></tr>
<tr><th scope="row">Pré-secado (bola de silagem)</th><td>40% a 60% de matéria seca</td><td>Bola embalada em filme, fermenta sem ar</td><td><a href="/pre-secado-de-azevem/">Azevém, R$ {PB} a bola</a></td></tr>
<tr><th scope="row">Silagem de milho</th><td>30% a 35% de matéria seca no corte</td><td>Silo trincheira, compactada e coberta com lona</td><td><a href="/silagem-a-venda-sc/">R$ {PT} a tonelada</a></td></tr>
</tbody></table></div>
<p class="nota">O azevém-anual é a principal forrageira de inverno do Sul do Brasil, segundo a Epagri e a Embrapa Pecuária Sul ({fonte("azevem", "Baldissera e outros, 2018")}).</p>
</div></section>

<section><div class="wrap">
<p class="rot">Antes de fechar</p>
<h2>Como avaliar uma bola de pré-secado antes de comprar</h2>
<p class="lead">Numa bola de pré-secado, confira o filme sem furos, a data em que a bola foi feita, o cheiro e o mofo ao abrir e o preço por quilo. Um furo pequeno, de 3 mm, já fez perder 8% da silagem aproveitável numa pesquisa do Teagasc, na Irlanda.</p>
<div class="rolagem"><table>
<caption>O que conferir numa bola de pré-secado. Fontes: Teagasc (Irlanda), University of Kentucky (EUA), Semina/UEL (2022) e UEPG (2019).</caption>
<thead><tr><th scope="col">O que conferir</th><th scope="col">Por que importa</th></tr></thead>
<tbody>
<tr><th scope="row">Furos no filme</th><td>Na pesquisa irlandesa do Teagasc, um único furo pequeno, de 3 mm, fez perder 8% da silagem aproveitável da bola; um furo grande, de 24 mm, fez perder um terço ({fonte("teagasc", "Teagasc")}).</td></tr>
<tr><th scope="row">Camadas de filme</th><td>As extensões de Kentucky ({fonte("uky", "AGR-283")}) e da Irlanda ({fonte("teagasc", "Teagasc")}) recomendam seis camadas. Num estudo brasileiro com Tifton 85, quatro ou seis camadas não mudaram o valor nutricional ({fonte("semina", "Semina, 2022")}).</td></tr>
<tr><th scope="row">Tempo de armazenagem</th><td>No estudo brasileiro com Tifton 85, 90 dias de armazenagem reduziram o valor nutricional do pré-secado ({fonte("semina", "Semina, 2022")}). Pergunte quando a bola foi feita.</td></tr>
<tr><th scope="row">Cheiro e mofo ao abrir</th><td>Cheiro suave; mofo e partes estragadas devem ser descartados antes de dar ao gado.</td></tr>
<tr><th scope="row">Peso e umidade</th><td>Bola pesada pode ser bola úmida: o pré-secado costuma ser vendido por bola, e parte dele ainda sai com matéria seca baixa ({fonte("uepg", "UEPG")}). Sem laudo, compare pelo preço por quilo.</td></tr>
</tbody></table></div>
</div></section>

<section class="escura"><div class="wrap">
<p class="rot">Depois de comprar</p>
<h2>Como transportar e guardar as bolas de pré-secado</h2>
<p class="lead">Bolas de pré-secado devem ser manuseadas o mínimo, guardadas em lugar drenado e longe de mato, com furos tapados na hora, e consumidas em 1 a 2 dias depois de abertas, segundo extensões rurais da Irlanda e dos Estados Unidos.</p>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>Mexa o mínimo</h3><p>Quanto mais a bola é manuseada, maior a chance de furar o filme. No transporte, ande devagar nos trechos ruins: solavancos forçam o filme ({fonte("teagasc", "Teagasc")}).</p></div>
<div class="passo"><p class="n">02</p><h3>Guarde longe do mato</h3><p>Deixe as bolas em lugar bem drenado, longe de árvores e mato que abriguem roedores e atraiam pássaros ({fonte("uky_q", "Kentucky")}). Se for empilhar, o Teagasc indica pilhas de duas ou três bolas deitadas ({fonte("teagasc", "Teagasc")}).</p></div>
<div class="passo"><p class="n">03</p><h3>Conserte e consuma rápido</h3><p>Tape furos na hora com fita própria para filme de silagem; fita comum se desfaz ao sol ({fonte("uky_q", "Kentucky")}). Depois de aberta, ofereça a bola de modo que o gado a consuma em 1 a 2 dias ({fonte("aces", "Alabama Extension")}).</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem procura pré-secado à venda</h2>
{FAQ_PV}</div></section>

<section><div class="wrap texto">
<p class="rot">Como esta página foi feita</p>
<h2>Fontes e método</h2>
<p>Preço, peso das bolas, forma de venda e fotos são da própria {NOME}, em {LOCAL}. O peso é uma faixa ({KMIN} a {KMAX} kg) porque cada bola sai com umidade e compactação diferentes. As orientações de compra e armazenagem vêm das publicações técnicas abaixo; algumas são de extensão rural da Irlanda e dos Estados Unidos, porque não encontramos recomendação brasileira equivalente para furos, empilhamento e prazo depois de aberta.</p>
{lista_fontes(FONTES_PV)}
<p>Procurando silagem de milho por tonelada? Veja a <a href="/silagem-a-venda-sc/">silagem à venda em SC</a>.</p>
</div></section>
{chamada(f"Pré-secado à venda, R$ {PB} a bola", f"Retirada em {LOCAL}. Diga quantas bolas e a sua cidade.", msg_pv, "chamada-pre-secado-venda")}
"""
pagina("/pre-secado-a-venda/", "Pré-secado à venda: preço da bola, peso e como comparar",
       f"Pré-secado à venda no Oeste de SC: bolas de ~{KG} kg a R$ {PB} em {LOCAL}. Peso da bola, preço por quilo e como avaliar antes de comprar.",
       pv, [NEGOCIO, LD_PV, migalha("Pré-secado à venda", "/pre-secado-a-venda/")],
       msg_pv, f"Pré-secado · R$ {PB} a bola", og="og-presecado.jpg",
       extra={"datePublished": GUIAS_EM, "dateModified": max(GUIAS_EM, F["atualizado_em"]), "mainEntity": {"@id": f"{DOM}/pre-secado-de-azevem/#produto"}, "citation": citacoes(FONTES_PV)})

# ---------------------------------------------------------------- ENTREGA E REGIÃO (hub + páginas por município)
# Dados em site-src/cidades.json: distâncias (sedes, OSRM/OpenStreetMap) e rebanho leiteiro (IBGE, PPM).
ORIG = CD["origem"]
FONTES_CID = CD["fontes"]
PPM_ANO = CD["ppm_ano"]
CONF_CID = CD["conferido_em"]
TOTAL_VACAS = ORIG["vacas_ordenhadas"] + sum(z["vacas_ordenhadas"] for z in MUNS)
RANK = {z["nome"]: i + 1 for i, z in enumerate(sorted([ORIG] + MUNS, key=lambda z: -z["vacas_ordenhadas"]))}
N_MUN = len(MUNS) + 1


def nome_uf(z):
    return f'{z["nome"]} ({z["uf"]})'


def milhoes_litros(mil):
    return f"{br(mil / 1000, 1)} milhões de litros" if mil >= 1000 else f"{br(mil * 1000)} litros"


def link_cid(z):
    return f'<a href="/entrega/{z["slug"]}/">{z["nome"]}</a>' if z.get("slug") else z["nome"]


def fonte_cid(k):
    return f'<a href="{FONTES_CID[k][1]}" rel="noopener">{FONTES_CID[k][0]}</a>'


NOTA_CID = (f'<p class="nota">Distâncias entre as sedes dos municípios: linha reta pelas coordenadas do IBGE; estrada e tempo de carro '
            f'calculados com {fonte_cid("rotas")}, aproximados. Rebanho e leite: {fonte_cid("ppm_vacas")} e {fonte_cid("ppm_leite")}. '
            f'Conferido em <time datetime="{CONF_CID}">{data_br(CONF_CID)}</time>.</p>')
CIT_CID = [{"@type": "Dataset", "name": FONTES_CID[k][0], "url": FONTES_CID[k][1]} for k in ("ppm_vacas", "ppm_leite")]


def migalha3(rotulo, caminho):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Início", "item": f"{DOM}/"},
        {"@type": "ListItem", "position": 2, "name": "Entrega e região", "item": f"{DOM}/regiao/"},
        {"@type": "ListItem", "position": 3, "name": rotulo, "item": f"{DOM}{caminho}"}]}


PAGS = [z for z in MUNS if z.get("slug")]
RS = [z for z in MUNS_E if z["uf"] == "RS"]
msg_reg = "Olá! Sou de ___ e quero um orçamento de entrega de silagem ou pré-secado da Estância Safra."

linhas = (f'<tr><th scope="row">{CID} (sede da estância)</th><td>0 km</td><td>-</td><td>-</td><td>Sim</td><td>{br(ORIG["vacas_ordenhadas"])}</td></tr>' +
          "".join(f'<tr><th scope="row">{link_cid(z)} ({z["uf"]})</th><td>{br(z["reta_km"], 1)} km</td><td>{z["estrada_km"]} km</td>'
                  f'<td>{tempo(z["estrada_min"])}</td><td>{"Sim" if z["estrada_km"] <= EMAX else "Sob consulta"}</td><td>{br(z["vacas_ordenhadas"])}</td></tr>' for z in MUNS))
cards = "".join(f'<li><a href="/entrega/{z["slug"]}/"><b>{z["nome"]}</b> · {z["estrada_km"]} km de estrada</a></li>'
                for z in sorted(PAGS, key=lambda z: z["estrada_km"]))
ex_rs = sorted(RS, key=lambda z: z["reta_km"])
FAQ_REG, LD_REG = faq([
    ("Em quais cidades a Estância Safra entrega silagem?",
     f"Em {N_ENT} municípios {ALC} de {LOCAL}: " +
     ", ".join(z["nome"] for z in MUNS_E if z["uf"] == "SC") + f", em Santa Catarina, e " +
     ", ".join(z["nome"] for z in ex_rs) + ", no Rio Grande do Sul, além da própria Lindóia do Sul. " +
     f"Em {', '.join(z['nome'] for z in MUNS_C[:-1])} e {MUNS_C[-1]['nome']}, que passam de {EMAX} km pela estrada, a entrega é sob consulta."),
    ("A entrega é só em carga fechada?",
     f"Não, mas é o pedido ideal. A partir de {MIN} t a tonelada sai a R$ {PT}; abaixo disso, a R$ {PTM}, sob consulta de disponibilidade. Uma carga de {CARGA} de silagem de milho custa de R$ {PC1} a R$ {PC2} na estância, mais o frete. <a href=\"/carga-de-silagem/\">Veja quanto custa a carga fechada</a>."),
    ("Como é calculado o frete da entrega?",
     f"Pela distância até a sua propriedade e pelo tamanho da carga. Mande pelo WhatsApp a cidade, a localidade e a quantidade, e respondemos com o valor. O preço na estância é o mesmo para qualquer cidade: {PRECO_REGRA}; R$ {PB} a bola de pré-secado."),
    ("Vocês entregam no Rio Grande do Sul?",
     f"Sim, nos municípios gaúchos a até {EMAX} km de estrada, como {ex_rs[0]['nome']}, {ex_rs[1]['nome']} e {ex_rs[2]['nome']}. Eles ficam do outro lado do rio Uruguai, então a estrada é bem mais longa que a linha reta: {ex_rs[0]['nome']} está a {br(ex_rs[0]['reta_km'], 1)} km em linha reta e cerca de {ex_rs[0]['estrada_km']} km de estrada."),
    (f"E quem está a mais de {EMAX} km de estrada?",
     f"Pode retirar na estância, em {LOCAL}, com o seu caminhão ou freteiro. Peça pelo WhatsApp e confirmamos estoque e horário. Nos municípios que ficam a menos de {RAIO} km em linha reta mas passam de {EMAX} km pela estrada, a entrega é sob consulta."),
])
reg = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Entrega e região</p>
<h1>Entrega de silagem e pré-secado até {EMAX} km de estrada de {CID}</h1>
<p class="sub">A {NOME} entrega silagem de milho e pré-secado de azevém em {N_ENT} municípios do Oeste e do Meio-Oeste de Santa Catarina e do Norte do Rio Grande do Sul, {ALC} da estância, em {LOCAL}. O pedido ideal é a carga fechada de {CARGA} num caminhão. O frete é orçado pelo WhatsApp. Quem preferir retira na estância.</p>
<div class="acoes">{wa(msg_reg, "heroi-regiao", "Pedir orçamento de entrega", "bt claro")}<a class="bt linha" href="{F['perfil_google']}" rel="noopener">Abrir no Google Maps</a></div>
</div>
<figure>{img("silos-vista-vale", f"Silos trincheira cobertos na {NOME}, com pasto e mata ao fundo, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Páginas por cidade</p>
<h2>Entrega nas cidades com mais procura</h2>
<p class="lead">Cada página mostra a distância pela estrada, o tempo de viagem e o rebanho leiteiro do município segundo o IBGE.</p>
<ul class="cidades">{cards}</ul>
</div></section>

<section><div class="wrap">
<p class="rot">Todos os municípios do raio</p>
<h2>{N_MUN} municípios a até {RAIO} km em linha reta da estância</h2>
<p class="lead">Somados, esses municípios têm {br(TOTAL_VACAS)} vacas ordenhadas, segundo a Pesquisa da Pecuária Municipal {PPM_ANO} do IBGE. A entrega vai até cerca de {EMAX} km de estrada: em {N_ENT} deles ela é normal e nos {len(MUNS_C)} que passam disso pela estrada é sob consulta. A tabela vai do mais perto ao mais longe, em linha reta.</p>
<div class="rolagem"><table>
<caption>Distância da sede de {LOCAL} até a sede de cada município e rebanho leiteiro ({PPM_ANO}).</caption>
<thead><tr><th scope="col">Município</th><th scope="col">Linha reta</th><th scope="col">Estrada (aprox.)</th><th scope="col">Tempo de carro</th><th scope="col">Entrega</th><th scope="col">Vacas ordenhadas</th></tr></thead>
<tbody>{linhas}</tbody></table></div>
{NOTA_CID}
</div></section>

<section class="escura"><div class="wrap">
<p class="rot">Como funciona</p>
<h2>Entrega ou retirada, você escolhe</h2>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>Mande cidade e quantidade</h3><p>Pelo WhatsApp, diga o produto, a quantidade e onde fica a propriedade. Hoje há {T} toneladas de silagem de milho e bolas de pré-secado de azevém.</p></div>
<div class="passo"><p class="n">02</p><h3>Receba o orçamento do frete</h3><p>O frete sai pela distância até a sua propriedade e pelo tamanho da carga. Sem surpresa: o preço do produto é o publicado no site.</p></div>
<div class="passo"><p class="n">03</p><h3>Receba ou retire</h3><p>Entregamos no dia combinado. Se preferir, o seu caminhão carrega na estância, em {CID}: a silagem sai da face do silo e o pré-secado em bolas de cerca de {KG} kg.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Perguntas sobre entrega</p>
<h2>O que perguntam antes de pedir</h2>
{FAQ_REG}</div></section>

<section><div class="wrap">
<p class="rot">Preços de hoje</p>
<h2>Preço na estância, antes do frete</h2>
{tabela_oferta()}
<p class="nota">Quem vem de mais longe encontra preço, frete e critérios de compra em <a href="/silagem-a-venda-sc/">silagem à venda em SC</a>.</p>
</div></section>
{chamada("Sua cidade está no raio?", "Mande a cidade e a quantidade. Respondemos com o frete.", msg_reg, "chamada-regiao")}
"""
pagina("/regiao/", f"Entrega de silagem até {EMAX} km de estrada de {CID} (SC)",
       f"Silagem de milho e pré-secado com entrega em {N_ENT} municípios de SC e RS a até {EMAX} km de estrada de {CID}: Concórdia, Seara, Xanxerê, Chapecó.",
       reg, [NEGOCIO, LD_REG, migalha("Entrega e região", "/regiao/")], msg_reg, f"Entrega até {EMAX} km de {CID}",
       extra={"citation": CIT_CID})

# ---------------------------------------------------------------- PÁGINAS POR MUNICÍPIO
FOTOS_CID = ["silo-coberto-eucaliptos", "silagem-face-detalhe", "bolas-pre-secado", "silo-trincheira-lateral",
             "lona-sacos-araucaria", "silo-lona-araucaria", "silagem-face-parede", "lona-silos-graneleiros"]
ALT_CID = {"silo-coberto-eucaliptos": "Silo trincheira de silagem de milho coberto com lona e sacos de peso",
           "silagem-face-detalhe": "Silagem de milho picada e compactada na face aberta do silo",
           "bolas-pre-secado": "Bolas de pré-secado de azevém embaladas em filme branco",
           "silo-trincheira-lateral": "Silo trincheira com muro de tijolo e lona presa por sacos",
           "lona-sacos-araucaria": "Silo coberto com lona e sacos de peso, com araucária ao fundo",
           "silo-lona-araucaria": "Lona do silo de silagem de milho com araucária ao fundo",
           "silagem-face-parede": "Silagem de milho compactada junto à parede do silo",
           "lona-silos-graneleiros": "Silo trincheira coberto com lona, com silos graneleiros ao fundo"}
ESTADO = {"SC": "Santa Catarina", "RS": "Rio Grande do Sul"}


def dist(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


URLS_CID = []
for i, z in enumerate(sorted(PAGS, key=lambda z: z["estrada_km"])):
    cam = f'/entrega/{z["slug"]}/'
    URLS_CID.append(cam)
    nm, nu = z["nome"], nome_uf(z)
    viz_pag = sorted([w for w in PAGS if w is not z], key=lambda w: dist(z, w))[:3]
    viz_out = sorted([w for w in MUNS_E if w is not z and not w.get("slug")], key=lambda w: dist(z, w))[:4]
    foto = FOTOS_CID[i % len(FOTOS_CID)]
    msg = f"Olá! Sou de {nm} ({z['uf']}) e quero um orçamento de entrega de ___ (silagem de milho ou pré-secado)."
    leite = milhoes_litros(z["leite_mil_litros"])
    rk = RANK[nm]
    FAQ_C, LD_C = faq([
        (f"Vocês entregam silagem em {nm}?",
         f"Sim. {nu} fica a cerca de {z['estrada_km']} km de estrada de {LOCAL}, dentro da área em que a {NOME} entrega, até cerca de {EMAX} km de estrada. O frete é orçado pelo WhatsApp conforme a quantidade e o endereço da propriedade."),
        (f"Qual a distância de {CID} até {nm}?",
         f"{br(z['reta_km'], 1)} km em linha reta entre as sedes e cerca de {z['estrada_km']} km pela estrada, perto de {tempo(z['estrada_min'])} de carro. Até a sua propriedade, a distância pode ser maior ou menor."),
        (f"Quanto custa a silagem de milho entregue em {nm}?",
         f"R$ {PT} a tonelada na estância, a partir de {MIN} t, mais o frete até {nm}. O frete é orçado pela distância e pela carga: quanto mais toneladas na mesma viagem, menor o frete por tonelada. Uma carga fechada de {CARGA} sai de R$ {PC1} a R$ {PC2} na estância, mais o frete até {nm}."),
        (f"Tem pré-secado de azevém para entregar em {nm}?",
         f"Sim. São bolas de cerca de {KG} kg ({KMIN} a {KMAX} kg), embaladas em filme, a R$ {PB} cada na estância. Diga quantas bolas pelo WhatsApp e orçamos a entrega em {nm}."),
    ])
    corpo = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › <a href="/regiao/">Entrega e região</a> › {nm}</p>
<h1>Silagem de milho e pré-secado com entrega em {nu}</h1>
<p class="sub">A {NOME} fica em {LOCAL}, a {br(z['reta_km'], 1)} km em linha reta da sede de {nm}: cerca de {z['estrada_km']} km e {tempo(z['estrada_min'])} pela estrada. Entregamos silagem de milho e pré-secado de azevém em {nm} com frete orçado pelo WhatsApp, ou você retira na estância.</p>
<div class="acoes">{wa(msg, "heroi-" + z["slug"], f"Pedir orçamento para {nm}", "bt claro")}<a class="bt linha" href="/regiao/">Ver todas as cidades</a></div>
</div>
<figure>{img(foto, f"{ALT_CID[foto]}, na {NOME}, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">{nm} em números</p>
<h2>Distância, preço e rebanho de {nm}</h2>
<div class="rolagem"><table>
<caption>Entrega da {NOME} em {nu}. Preços atualizados em {DATA_HTML}.</caption>
<tbody>
<tr><th scope="row">Distância em linha reta</th><td>{br(z['reta_km'], 1)} km entre as sedes</td></tr>
<tr><th scope="row">Pela estrada</th><td>Cerca de {z['estrada_km']} km, {tempo(z['estrada_min'])} de carro</td></tr>
<tr><th scope="row">Silagem de milho</th><td><b>R$ {PT} a tonelada</b> na estância a partir de {MIN} t (R$ {PTM} abaixo, sob consulta), {T} toneladas disponíveis</td></tr>
<tr><th scope="row">Carga fechada de silagem</th><td>{CARGA} por caminhão: <b>R$ {PC1} a R$ {PC2}</b> na estância, mais o frete até {nm}</td></tr>
<tr><th scope="row">Pré-secado de azevém</th><td><b>R$ {PB} a bola</b> de cerca de {KG} kg</td></tr>
<tr><th scope="row">Frete até {nm}</th><td>Orçado pelo WhatsApp, pela distância e pela carga</td></tr>
<tr><th scope="row">Vacas ordenhadas em {nm}</th><td>{br(z['vacas_ordenhadas'])} cabeças, o {'' if rk == 1 else f'{rk}º '}maior rebanho entre os {N_MUN} municípios do raio (IBGE, {PPM_ANO})</td></tr>
<tr><th scope="row">Leite produzido em {nm}</th><td>{leite} em {PPM_ANO} (IBGE)</td></tr>
</tbody></table></div>
{NOTA_CID}
</div></section>

<section><div class="wrap">
<p class="rot">Quanto custa entregue</p>
<h2>Silagem entregue em {nm}: preço mais frete</h2>
<p class="lead">O preço do produto é o mesmo em qualquer cidade: R$ {PT} a tonelada de silagem de milho a partir de {MIN} t e R$ {PB} a bola de pré-secado. Entregue em {nm}, soma-se o frete de uma viagem de cerca de {z['estrada_km']} km, dividido pelas toneladas da carga. Em <a href="/carga-de-silagem/">carga fechada de {CARGA}</a>, a silagem sai de R$ {PC1} a R$ {PC2} por caminhão, antes do frete.</p>
<p>Para comparar com outra oferta, faça a conta por tonelada entregue na <a href="/silagem-a-venda-sc/#frete">calculadora de frete</a>, ou veja o preço por quilo do <a href="/pre-secado-a-venda/">pré-secado à venda</a>. Se tiver caminhão, a retirada em {CID} sai sem frete.</p>
</div></section>

<section><div class="wrap">
<p class="rot">Perguntas de quem é de {nm}</p>
<h2>Entrega em {nm}: dúvidas comuns</h2>
{FAQ_C}</div></section>

<section><div class="wrap">
<p class="rot">Vizinhos de {nm}</p>
<h2>Também entregamos perto de {nm}</h2>
<p>{", ".join(link_cid(w) + f" ({w['uf']})" for w in viz_pag)} têm página própria. Na mesma região também atendemos {", ".join(nome_uf(w) for w in viz_out[:-1])} e {nome_uf(viz_out[-1])}. Veja a <a href="/regiao/">lista completa dos {N_MUN} municípios</a>.</p>
</div></section>
{chamada(f"Entrega em {nm}", f"Diga o produto e a quantidade. Respondemos com o frete até {nm}.", msg, "chamada-" + z["slug"])}
"""
    servico = {"@type": "Service", "@id": f"{DOM}{cam}#entrega", "name": f"Entrega de silagem de milho e pré-secado em {nu}",
               "serviceType": "Entrega de volumoso para alimentação animal", "provider": {"@id": f"{DOM}/#estancia"},
               "areaServed": {"@type": "City", "name": f"{nm}, {z['uf']}",
                              "geo": {"@type": "GeoCoordinates", "latitude": z["lat"], "longitude": z["lon"]},
                              "containedInPlace": {"@type": "State", "name": ESTADO[z["uf"]]}},
               "offers": [{"@type": "Offer", "itemOffered": {"@id": f"{DOM}/silagem-de-milho/#produto"}, "price": S["preco_tonelada"], "priceCurrency": "BRL", "priceSpecification": SPEC_SIL},
                          {"@type": "Offer", "itemOffered": {"@id": f"{DOM}/pre-secado-de-azevem/#produto"}, "price": P["preco_bola"], "priceCurrency": "BRL"}]}
    titulo = f"Silagem de milho com entrega em {nu}"
    pagina(cam, titulo + (" | Estância Safra" if len(titulo) < 44 else ""),
           f"Silagem de milho a R$ {PT}/t (8 t ou mais) e pré-secado a R$ {PB}/bola com entrega em {nu}, a cerca de {z['estrada_km']} km de {CID}. Frete orçado no WhatsApp.",
           corpo, [NEGOCIO, servico, LD_C, migalha3(nm, cam)], msg, f"Entrega em {nm}", extra={"citation": CIT_CID})

# ---------------------------------------------------------------- CONTATO
msg_con = "Olá! Quero comprar volumoso da Estância Safra."
con = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Contato</p>
<h1>Peça silagem de milho ou pré-secado pelo WhatsApp</h1>
<p class="sub">Atendimento direto com a {NOME}, em {LOCAL}. Preencha o pedido abaixo ou chame agora: confirmamos o estoque e orçamos a entrega ou combinamos a retirada.</p>
<div class="acoes">{wa(msg_con, "heroi-contato", "Chamar no WhatsApp", "bt claro")}</div>
{PROVA}
</div>
<figure>{img("lona-sacos-araucaria", f"Silo coberto com lona e sacos de peso na {NOME}, com araucária ao fundo", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section class="fim"><div class="wrap">
<p class="rot">Pedido rápido</p>
<h2>Diga o que precisa e de onde vem</h2>
<div class="caixa">
<form id="pedido">
<div class="campo"><label for="nome">Seu nome</label><input id="nome" name="nome" autocomplete="name" required></div>
<div class="campo"><label for="cidade">Cidade da propriedade</label><input id="cidade" name="cidade" autocomplete="address-level2" required></div>
<div class="campo"><label for="produto">Produto</label><select id="produto" name="produto">
<option>silagem de milho</option><option>pré-secado de azevém</option><option>silagem de milho e pré-secado de azevém</option></select></div>
<div class="campo"><label for="qtd">Quantidade (toneladas ou bolas)</label><input id="qtd" name="qtd" placeholder="Ex.: 30 toneladas"></div>
<div class="campo"><label for="obs">Observação (opcional)</label><textarea id="obs" name="obs" rows="3"></textarea></div>
<button class="bt" type="submit" data-lead="formulario-contato">Enviar pedido pelo WhatsApp</button>
<p class="nota">O botão abre o seu WhatsApp com a mensagem pronta. Nada é guardado no site.</p>
<noscript><p class="nota">Seu navegador está sem JavaScript: use o botão "Chamar no WhatsApp" no topo desta página.</p></noscript>
</form>
<div class="saida">
<h3>Onde estamos</h3>
<p>{NOME} ({MARCA})<br>{CID}, Santa Catarina</p>
<p><a href="{F['perfil_google']}" rel="noopener">Ver localização e rota no Google</a></p>
<h3>Preços em {MESANO}</h3>
<p>Silagem de milho: R$ {PT} a tonelada a partir de {MIN} t; R$ {PTM} abaixo disso, sob consulta ({T} t disponíveis).<br>Pré-secado de azevém: R$ {PB} a bola de cerca de {KG} kg.</p>
<p>Entrega {ALC}, com frete orçado, ou retirada no local. Carga fechada de silagem: {CARGA} por caminhão.</p>
</div>
</div></div></section>
"""
pagina("/contato/", "Contato e pedido pelo WhatsApp | Estância Safra",
       f"Peça silagem de milho ou pré-secado de azevém à {NOME}, em {LOCAL}, pelo WhatsApp. Diga produto, quantidade e cidade.",
       con, [NEGOCIO, migalha("Contato", "/contato/")], msg_con, "Fale direto com a estância")

# ---------------------------------------------------------------- PRIVACIDADE
DOC = F.get("documento", "")   # CNPJ ou CPF do responsável, se o dono quiser mostrar
EMAIL = F.get("email", "")
contato_priv = (f'pelo WhatsApp (botões deste site)' + (f' ou pelo e-mail <a href="mailto:{EMAIL}">{EMAIL}</a>' if EMAIL else ""))
priv = f"""<section class="fim"><div class="wrap texto">
<p class="migalha"><a href="/">Início</a> › Privacidade</p>
<p class="rot">Lei Geral de Proteção de Dados (LGPD)</p>
<h1 class="h1-claro">Política de privacidade</h1>
<p class="lead">Este site serve para mostrar preço, estoque e fotos da silagem e do pré-secado da {NOME}, em {LOCAL}. Ele não tem cadastro, login nem pagamento, e não guarda o que você digita. Aqui está, em linguagem simples, o que acontece com os seus dados.</p>
<p>Versão de <time datetime="{F['privacidade_em']}">{data_br(F['privacidade_em'])}</time>.</p>

<h2>Quem é o responsável</h2>
<p>{NOME} ({MARCA}), {CID}, Santa Catarina, Brasil{f", {DOC}" if DOC else ""}. É quem decide como os dados deste site são usados (controlador, na LGPD). Contato para qualquer assunto de privacidade: {contato_priv}.</p>

<h2>O que coletamos e para quê</h2>
<h3>1. Estatísticas de visita (Google Analytics 4)</h3>
<p>Usamos o Google Analytics 4 para saber quantas pessoas visitam o site, de quais cidades e aparelhos vêm, quais páginas leem e quais botões do WhatsApp clicam. Isso nos diz se o site está ajudando quem procura volumoso. O Google Analytics grava cookies no seu navegador (como <code>_ga</code>) e recebe dados técnicos da visita: páginas vistas, tipo de aparelho e navegador, região aproximada e origem do acesso. Não enviamos ao Google o seu nome, telefone nem o texto das mensagens.</p>
<p>Base legal: legítimo interesse em medir e melhorar o site (art. 7º, IX, da LGPD).</p>

<h3>2. Pedidos pelo WhatsApp</h3>
<p>Os botões "Chamar no WhatsApp", a calculadora e o formulário de pedido só montam uma mensagem e abrem o seu WhatsApp. O site não guarda nada do que você digita. Se você enviar a mensagem, recebemos o que você escreveu e o seu número de telefone, e usamos isso apenas para responder, confirmar estoque e preço e combinar a retirada.</p>
<p>Base legal: procedimentos para a venda que você pediu (art. 7º, V, da LGPD). A conversa passa pelo WhatsApp, que segue a política de privacidade da própria empresa (Meta).</p>

<h3>3. Hospedagem</h3>
<p>Como em qualquer site, o servidor que hospeda estas páginas recebe dados técnicos de cada acesso, como endereço IP, navegador e horário, para entregar as páginas e proteger o site contra abuso.</p>

<h2>O que não fazemos</h2>
<ul>
<li>Não vendemos nem alugamos dados de ninguém.</li>
<li>Não usamos pixel de anúncios nem remarketing.</li>
<li>Não pedimos CPF, endereço nem dados de pagamento pelo site.</li>
<li>As fontes e as fotos são servidas pelo próprio site, sem rastreio de terceiros.</li>
</ul>

<h2>Por quanto tempo guardamos</h2>
<p>Os dados do Google Analytics ficam guardados pelo prazo de retenção configurado na conta (no máximo 14 meses) e depois são apagados pelo Google. As conversas de WhatsApp ficam com a gente enquanto forem úteis para atender você e cumprir obrigações legais da venda.</p>

<h2>Como recusar a medição</h2>
<p>Você pode bloquear ou apagar cookies nas configurações do seu navegador, usar a navegação anônima ou instalar o <a href="https://tools.google.com/dlpage/gaoptout?hl=pt-BR" rel="noopener">complemento de desativação do Google Analytics</a>. O site continua funcionando normalmente.</p>

<h2>Seus direitos</h2>
<p>Pela LGPD (art. 18), você pode pedir a qualquer momento: confirmação de que tratamos seus dados, acesso a eles, correção, anonimização ou eliminação do que for desnecessário, informação sobre com quem compartilhamos e revisão do consentimento quando ele for a base. Peça {contato_priv}. Se não ficar satisfeito, você pode reclamar à Autoridade Nacional de Proteção de Dados (<a href="https://www.gov.br/anpd/" rel="noopener">ANPD</a>).</p>

<h2>Mudanças nesta política</h2>
<p>Se mudarmos o que o site coleta, esta página será atualizada e a data no topo mudará.</p>
<p style="margin-top:28px"><a class="bt" href="/">Voltar ao início</a></p>
</div></section>"""
pagina("/privacidade/", "Política de privacidade | Estância Safra",
       f"Como o site da {NOME} ({MARCA}) usa dados: Google Analytics, pedidos pelo WhatsApp e seus direitos pela LGPD.",
       priv, [NEGOCIO, migalha("Privacidade", "/privacidade/")], msg_home, "Silagem e pré-secado à venda")

# ---------------------------------------------------------------- 404
pagina("/404.html", "Página não encontrada | Estância Safra", "Esta página não existe. Veja a silagem de milho e o pré-secado de azevém à venda.",
       f"""<section class="fim"><div class="wrap"><p class="rot">Erro 404</p><h1 class="h1-claro">Esta página não existe</h1>
<p class="lead">O que está à venda continua aqui:</p>{tabela_oferta()}<p style="margin-top:24px"><a class="bt" href="/">Voltar ao início</a></p></div></section>""",
       [NEGOCIO], msg_home, "Silagem e pré-secado à venda")

# ---------------------------------------------------------------- arquivos técnicos
(OUT / "assets").mkdir(parents=True, exist_ok=True)
for f in ("site.css", "site.js"):
    shutil.copyfile(SRC / f, OUT / "assets" / f)
for f in (SRC / "fontes").glob("*.woff2"):
    shutil.copyfile(f, OUT / "assets" / f.name)
LOGO = SRC.parent / "logo"
for f in ("safra-horizontal.svg", "safra-emblema-negativo.svg", "safra-icone.svg"):
    shutil.copyfile(LOGO / f, OUT / "assets" / f)
shutil.copyfile(LOGO / "png" / "safra-icone.png", OUT / "assets" / "safra-icone.png")
shutil.copyfile(LOGO / "png" / "safra-emblema.png", OUT / "assets" / "safra-emblema.png")
(OUT / "fotos").mkdir(exist_ok=True)
for f in (SRC / "fotos").iterdir():
    alvo = OUT / "fotos" / f.name
    if not alvo.exists() or alvo.stat().st_size != f.stat().st_size:
        shutil.copyfile(f, alvo)

urls = ["/", "/silagem-de-milho/", "/carga-de-silagem/", "/pre-secado-de-azevem/", "/silagem-a-venda-sc/", "/pre-secado-a-venda/", "/regiao/"] + URLS_CID + ["/contato/", "/privacidade/"]


LASTMOD = {u: max(GUIAS_EM, F["atualizado_em"]) for u in ("/silagem-a-venda-sc/", "/pre-secado-a-venda/")}
LASTMOD["/privacidade/"] = max(F["privacidade_em"], F["atualizado_em"])


def imgs_da(u):
    h = (OUT / u.strip("/") / "index.html").read_text(encoding="utf-8")
    vistos = list(dict.fromkeys(re.findall(r'src="(/fotos/[^"]+\.webp)"', h)))
    return "".join(f"<image:image><image:loc>{DOM}{i}</image:loc></image:image>" for i in vistos)


(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
    "".join(f"  <url><loc>{DOM}{u}</loc><lastmod>{LASTMOD.get(u, F['atualizado_em'])}</lastmod>{imgs_da(u)}</url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOM}/sitemap.xml\n", encoding="utf-8")
QA_LLMS = [
    ("Quanto custa a tonelada de silagem de milho na Estância Safra?", f"{PRECO_REGRA[0].upper() + PRECO_REGRA[1:]}. Sem frete. Preço de {DATA}."),
    ("Quanto custa uma carga (um caminhão) de silagem de milho?", f"A carga fechada de {CARGA} custa de R$ {PC1} a R$ {PC2}, sem frete."),
    ("Quantas toneladas de silagem cabem num caminhão?", f"Em geral, pela cubagem da carroceria, o equivalente a {CARGA}. É a carga fechada com que a estância trabalha."),
    ("Qual o pedido mínimo?", f"O ideal é a carga fechada de {CARGA}. Abaixo de {MIN} t, R$ {PTM} a tonelada e sob consulta de disponibilidade. O pré-secado é vendido por bola."),
    ("Até onde vocês entregam?", f"{ALC[0].upper() + ALC[1:]} de {LOCAL}, com frete orçado pelo WhatsApp, em {N_ENT} municípios de SC e RS. Sob consulta: {', '.join(z['nome'] for z in MUNS_C)}."),
    ("Quanto custa o frete?", "Não há tabela publicada: o frete é orçado pelo WhatsApp pela distância e pela carga. Quanto mais toneladas na viagem, menor o frete por tonelada."),
    ("Quanto de silagem há em estoque?", f"{T} toneladas em {MESANO}, o equivalente a {N_CARGAS} cargas de {C2} t."),
    ("A silagem é a granel ou ensacada?", "A granel, carregada da face do silo trincheira direto no caminhão."),
    ("Quanto tempo a silagem aguenta depois de entregue?", "Deve ser fornecida em até 48 horas de exposição ao ar (Unoesc) ou reensilada no mesmo dia; reensilar depois de 36 horas reduziu o valor nutritivo (Pesquisa Agropecuária Brasileira, 2018)."),
    ("Tem análise bromatológica?", "Em andamento. Nenhum valor de composição é informado antes do laudo."),
    ("Quanto de silagem uma vaca come por dia?", "Para planejar, a Embrapa usa 30 kg de silagem por vaca por dia (Embrapa Acre, 2015); outra publicação da Embrapa fala em 25 a 35 kg por animal adulto, conforme raça e produção (Embrapa Amazônia Oriental, 2004). Uma carga de 10 t dura cerca de 7 dias para 50 vacas a 30 kg."),
    ("Como reensilar a silagem comprada?", "No mesmo dia da entrega: camadas de no máximo 20 cm bem compactadas e lona de pelo menos 200 micras com pesos por cima, como a Embrapa recomenda para a ensilagem (Comunicado Técnico 114, 2017)."),
    ("Quanto custa o pré-secado de azevém?", f"R$ {PB} a bola de cerca de {KG} kg ({KMIN} a {KMAX} kg), ou R$ {PKG_MIN} a R$ {PKG_MAX} por kg."),
    ("Dá para retirar na propriedade?", f"Sim, em {LOCAL}, em dia e horário combinados, com o seu caminhão ou freteiro. Na retirada não há frete."),
]
(OUT / "llms.txt").write_text(f"""# Estância Safra ({NOME})

> Propriedade rural em {CID}, Santa Catarina, Brasil, que vende silagem de milho a granel por tonelada, com foco em carga fechada de {CARGA} por caminhão, e pré-secado de azevém em bolas. Entrega {ALC}, com frete orçado, ou retirada no local. Dados atualizados em {DATA}.

## Fatos
- Silagem de milho a granel: {PRECO_REGRA}. R$ {PKG} por kg na carga fechada. {T} toneladas disponíveis.
- Carga fechada: um caminhão leva, pela cubagem, o equivalente a {CARGA} de silagem; custa de R$ {PC1} a R$ {PC2} sem frete. O estoque equivale a {N_CARGAS} cargas de {C2} t.
- Pré-secado de azevém: R$ {PB} por bola de cerca de {KG} kg ({KMIN} a {KMAX} kg), ou R$ {PKG_MIN} a R$ {PKG_MAX} por kg.
- Entrega {ALC} de {LOCAL}, com frete orçado pelo WhatsApp conforme a distância e a carga, em {N_ENT} municípios de SC e RS. Municípios a menos de {RAIO} km em linha reta que passam de {EMAX} km pela estrada: sob consulta. Também há retirada no local.
- Análise bromatológica em andamento; nenhum valor de composição é informado antes do laudo.
- Contato: WhatsApp, pelos botões do site.

## Perguntas e respostas
""" + "".join(f"- {q} {r}\n" for q, r in QA_LLMS) + f"""
## Páginas
- [Silagem de milho]({DOM}/silagem-de-milho/): preço por tonelada e regra de quantidade, estoque, armazenagem, calculadora de toneladas e cargas.
- [Carga fechada de silagem]({DOM}/carga-de-silagem/): quanto custa uma carga ou um caminhão de silagem de milho, quantas toneladas cabem, quantas cargas o rebanho precisa, frete por tonelada e prazo de uso depois da descarga.
- [Pré-secado de azevém]({DOM}/pre-secado-de-azevem/): preço por bola e por quilo, peso, vídeo, comparação com a silagem.
- [Silagem à venda em SC]({DOM}/silagem-a-venda-sc/): onde e como comprar silagem de milho em Santa Catarina, o que perguntar ao vendedor, custo com frete, como avaliar antes de comprar e quanto tempo dura fora do silo, com fontes da Embrapa.
- [Pré-secado à venda]({DOM}/pre-secado-a-venda/): quanto custa e quanto pesa uma bola, comparador de preço por quilo, diferença para feno e silagem, como avaliar e guardar as bolas.
- [Entrega e região]({DOM}/regiao/): os municípios atendidos {ALC}, com distância, tempo de estrada, rebanho leiteiro (IBGE) e quais são sob consulta.
- [Contato]({DOM}/contato/): pedido pelo WhatsApp.
- [Política de privacidade]({DOM}/privacidade/): o que o site coleta (Google Analytics) e direitos pela LGPD.

## Entrega por município
""" + "".join(f"- [Silagem e pré-secado com entrega em {nome_uf(z)}]({DOM}/entrega/{z['slug']}/): cerca de {z['estrada_km']} km de estrada de {CID}.\n" for z in sorted(PAGS, key=lambda z: z["estrada_km"])) + f"""
Também há entrega em: {", ".join(nome_uf(z) for z in MUNS_E if not z.get("slug"))}.
Sob consulta (mais de {EMAX} km de estrada): {", ".join(nome_uf(z) for z in MUNS_C)}.
""", encoding="utf-8")

# verificação de Search Console, Bing e chave do IndexNow (arquivos na raiz)
if V.get("google_arquivo"):
    (OUT / V["google_arquivo"]).write_text(f"google-site-verification: {V['google_arquivo']}", encoding="utf-8")
if V.get("bing"):
    (OUT / "BingSiteAuth.xml").write_text(f'<?xml version="1.0"?>\n<users>\n\t<user>{V["bing"]}</user>\n</users>\n', encoding="utf-8")
if V.get("indexnow_chave"):
    (OUT / f"{V['indexnow_chave']}.txt").write_text(V["indexnow_chave"], encoding="utf-8")

print(f"Site gerado em {OUT}")
if not F.get("whatsapp_definitivo"):
    print("Aviso: WhatsApp provisório. Ele está nos botões, mas fica fora do schema até whatsapp_definitivo virar true.", file=sys.stderr)
