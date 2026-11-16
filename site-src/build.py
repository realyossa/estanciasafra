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


def img(nome, alt, w=720, h=1280, lazy=True, extra=""):
    l = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    return f'<img src="/fotos/{nome}.webp" alt="{escape(alt)}" width="{w}" height="{h}"{l}{extra}>'


NAV = [("/silagem-de-milho/", "Silagem de milho"), ("/pre-secado-de-azevem/", "Pré-secado de azevém"),
       ("/regiao/", "Região e retirada"), ("/contato/", "Contato")]

NEGOCIO = {
    "@type": "LocalBusiness", "@id": f"{DOM}/#estancia", "name": NOME, "alternateName": [MARCA, "Estância Safra"],
    "url": f"{DOM}/", "logo": f"{DOM}/assets/safra-emblema.png", "image": f"{DOM}/fotos/og.jpg",
    "description": f"Propriedade rural em {LOCAL} que vende silagem de milho por tonelada e pré-secado de azevém em bolas, com retirada no local.",
    "address": {"@type": "PostalAddress", "addressLocality": CID, "addressRegion": UF, "addressCountry": "BR"},
    "areaServed": [{"@type": "City", "name": f"{c}, {UF}"} for c in [CID] + CIDADES],
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


def pagina(caminho, title, desc, corpo, grafo, barra_msg, barra_txt, og="og.jpg"):
    url = f"{DOM}{caminho}"
    atual = ' aria-current="page"'
    nav = "".join(f'<a href="{h}"{atual if h == caminho else ""}>{t}</a>' for h, t in NAV)
    mh = re.search(r'<img src="([^"]+)"[^>]*fetchpriority="high"', corpo)
    pre = f'<link rel="preload" as="image" href="{mh.group(1)}" fetchpriority="high">\n' if mh else ""
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
                                       "contentLocation": LOCAL}} if mi else {})}]
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&display=swap">
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
<div><img src="/assets/safra-emblema-negativo.svg" alt="" width="130" height="96" loading="lazy">
<p><strong>{NOME}</strong> ({MARCA})<br>{CID}, Santa Catarina, Brasil</p>
<p>Preços e estoque atualizados em {DATA_HTML}.</p>{PROVA}</div>
<div><b>À venda</b><ul>
<li><a href="/silagem-de-milho/">Silagem de milho, R$ {PT} a tonelada</a></li>
<li><a href="/pre-secado-de-azevem/">Pré-secado de azevém, R$ {PB} a bola</a></li></ul></div>
<div><b>Atendimento</b><ul>
<li><a href="/regiao/">Região e retirada</a></li>
<li><a href="/contato/">Contato e pedido</a></li>
<li><a href="{F['perfil_google']}" rel="noopener">Ver a estância no Google</a></li></ul></div>
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
<tr><th scope="row"><a href="/silagem-de-milho/">Silagem de milho</a></th><td><b>R$ {PT}</b> por tonelada</td><td>R$ {PKG} por kg</td><td>{T} toneladas</td><td>Retirada no local ou frete a combinar</td></tr>
<tr><th scope="row"><a href="/pre-secado-de-azevem/">Pré-secado de azevém</a></th><td><b>R$ {PB}</b> por bola</td><td>R$ {PKG_MIN} a R$ {PKG_MAX} por kg</td><td>Bolas de cerca de {KG} kg ({KMIN} a {KMAX} kg)</td><td>Retirada no local ou frete a combinar</td></tr>
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
     f"Na {NOME}, em {LOCAL}, a silagem de milho custa R$ {PT} a tonelada em {MESANO}, o que dá R$ {PKG} por quilo. O valor é para retirada na estância e não inclui frete."),
    (f"Vocês entregam?",
     f"Não. A {NOME} não tem entrega própria: o comprador retira em {LOCAL} ou o frete é combinado caso a caso. Por isso a compra costuma compensar para quem está a até cerca de {RAIO} km."),
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
<p class="sub">Volumoso pronto para retirar na estância, com preço aberto e estoque informado. Atendemos produtores num raio de cerca de {RAIO} km, onde o frete ainda compensa.</p>
<div class="selos">
<div><b>{T} t</b><span>de silagem de milho disponíveis</span></div>
<div><b>R$ {PT}</b><span>a tonelada de silagem</span></div>
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
<p class="lead">Em {MESANO}, a {NOME} tem {T} toneladas de silagem de milho a R$ {PT} a tonelada e bolas de pré-secado de azevém a R$ {PB} cada. Não fazemos entrega: a retirada é na estância, em {LOCAL}, ou com frete a combinar.</p>
{tabela_oferta()}
</div></section>

<section><div class="wrap">
<p class="rot">Os dois volumosos</p>
<h2>Escolha o que a sua dieta precisa</h2>
<div class="duas">
<article class="cartao"><div class="foto">{img("silagem-face-detalhe", "Face do silo aberta mostrando a silagem de milho picada e compactada")}</div>
<div class="corpo"><h3><a href="/silagem-de-milho/">Silagem de milho</a></h3>
<p class="preco">R$ {PT} <small>por tonelada · R$ {PKG} o kg</small></p>
<p>{T} toneladas em silos trincheira cobertos com lona e sacos de peso. Vendida por tonelada, na quantidade que você precisar.</p>
<a class="bt" href="/silagem-de-milho/">Ver a silagem de milho</a></div></article>
<article class="cartao"><div class="foto">{img("bolas-pre-secado", "Bolas de pré-secado de azevém embaladas em filme branco, armazenadas entre muros de tijolo")}</div>
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
<div class="passo"><p class="n">02</p><h3>Combine a retirada</h3><p>Marcamos dia e horário para o seu caminhão carregar na estância, em {LOCAL}. Se precisar de frete, combinamos.</p></div>
<div class="passo"><p class="n">03</p><h3>Carregue e leve</h3><p>Você paga pelo que levar: silagem por tonelada, pré-secado por bola.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Veja antes de vir</p>
<h2>Fotos reais dos silos e das bolas</h2>
<p class="lead">Todas as fotos desta página foram feitas na estância em novembro de 2026.</p>
<div class="galeria mosaico">
<figure>{img("silo-lona-araucaria", "Silo trincheira coberto com lona branca, com araucária ao fundo")}<figcaption>Silo coberto, com a araucária ao fundo</figcaption></figure>
<figure>{img("silo-trincheira-lateral", "Lateral de um silo trincheira com muro de tijolo e lona presa por sacos")}<figcaption>Silo trincheira com muro de tijolo</figcaption></figure>
<figure>{img("lona-sacos-araucaria", "Lona branca do silo presa por fileiras de sacos, com uma araucária ao fundo")}<figcaption>Lona vedada com fileiras de sacos</figcaption></figure>
<figure>{img("silagem-face-parede", "Silagem de milho compactada junto à parede do silo")}<figcaption>Silagem compactada junto à parede</figcaption></figure>
<figure>{img("silos-vista-vale", "Dois silos trincheira cobertos, lado a lado, com pasto ao fundo")}<figcaption>Dois silos lado a lado</figcaption></figure>
</div></div></section>

<div class="faixa-foto">{img("lona-silos-graneleiros", "")}
<div class="wrap"><p class="rot">Nosso jeito de vender</p>
<h2>O que está no site é o que você encontra na estância</h2>
<div class="tres">
<div><b>Preço aberto</b><p>R$ {PT} a tonelada de silagem e R$ {PB} a bola de pré-secado, publicados e com data.</p></div>
<div><b>Estoque informado</b><p>{T} toneladas de silagem de milho em {MESANO}. Quando o número mudar, a página muda.</p></div>
<div><b>Laudo, não promessa</b><p>A análise bromatológica entra no site quando o laboratório entregar. Antes disso, nenhum número de composição.</p></div>
</div></div></div>

<section><div class="wrap">
<p class="rot">Perguntas de quem compra</p>
<h2>O que os produtores perguntam antes de fechar</h2>
{FAQ_HOME}</div></section>
{chamada("Precisa de volumoso perto de " + CID + "?", f"Atendemos {CID_TXT} e outros municípios num raio de cerca de {RAIO} km.", msg_home, "chamada-home")}
"""
NEGOCIO_HOME = {**NEGOCIO, "knowsAbout": ["silagem de milho", "pré-secado de azevém", "volumoso para gado"],
                "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Product", "@id": f"{DOM}/silagem-de-milho/#produto", "name": "Silagem de milho"}, "price": S["preco_tonelada"], "priceCurrency": "BRL"},
                               {"@type": "Offer", "itemOffered": {"@type": "Product", "@id": f"{DOM}/pre-secado-de-azevem/#produto", "name": "Pré-secado de azevém em bola"}, "price": P["preco_bola"], "priceCurrency": "BRL"}]}
pagina("/", f"Silagem de milho à venda em {LOCAL} | Estância Safra",
       f"{T} toneladas de silagem de milho a R$ {PT} a tonelada e pré-secado de azevém a R$ {PB} a bola. Retirada em {LOCAL}. Chame no WhatsApp.",
       home, [NEGOCIO_HOME, LD_HOME, {"@type": "WebSite", "@id": f"{DOM}/#site", "url": f"{DOM}/", "name": "Estância Safra",
                        "inLanguage": "pt-BR", "publisher": {"@id": f"{DOM}/#estancia"}}],
       msg_home, f"Silagem R$ {PT}/t · pré-secado R$ {PB}/bola")

# ---------------------------------------------------------------- SILAGEM
msg_sil = "Olá! Vi no site a silagem de milho a R$ %s a tonelada. Ainda tem disponível? Preciso de cerca de ___ toneladas." % PT
FAQ_SIL, LD_SIL = faq([
    (f"Quanto custa a tonelada de silagem de milho em Santa Catarina?",
     f"Na {NOME}, em {LOCAL}, a tonelada de silagem de milho custa R$ {PT} em {MESANO}, ou R$ {PKG} por quilo, para retirada no local. Este é o preço desta propriedade, não uma média do estado: o valor muda de região para região e de safra para safra."),
    (f"Vale a pena comprar silagem de longe?",
     f"Depende do frete. Silagem é um produto pesado e úmido, então o transporte pesa no custo final por quilo. Na {NOME}, a compra costuma compensar para propriedades a até cerca de {RAIO} km de {LOCAL}. Acima disso, peça o frete antes e some ao preço da tonelada."),
    (f"Vocês entregam a silagem?",
     f"Não. A venda é com retirada na estância, em {LOCAL}. Se você não tem caminhão, o frete pode ser combinado pelo WhatsApp."),
    (f"A silagem tem análise bromatológica?",
     f"{BROMA}"),
    (f"Posso comprar pouca quantidade?",
     f"A venda é por tonelada. Diga pelo WhatsApp quanto você precisa e de onde vem, e confirmamos se a carga compensa para os dois lados."),
    (f"Também vendem pré-secado?",
     f"Sim. A {NOME} vende <a href=\"/pre-secado-de-azevem/\">pré-secado de azevém em bolas de cerca de {KG} kg</a>, a R$ {PB} a bola."),
])
sil = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Silagem de milho</p>
<p class="pill"><i></i><span>{T} t disponíveis · atualizado em {DATA_HTML}</span></p>
<h1>Silagem de milho à venda: R$ {PT} a tonelada, em {LOCAL}</h1>
<p class="sub">A {NOME} tem {T} toneladas de silagem de milho disponíveis em {MESANO}. Venda por tonelada, com retirada na estância ou frete a combinar.</p>
<div class="selos">
<div><b>R$ {PT}</b><span>por tonelada</span></div>
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
<tr><th scope="row">Preço</th><td><b>R$ {PT} por tonelada</b> (R$ {PKG} por kg), sem frete</td></tr>
<tr><th scope="row">Quantidade disponível</th><td>{T} toneladas</td></tr>
<tr><th scope="row">Armazenagem</th><td>Silos trincheira, cobertos com lona e sacos de peso</td></tr>
<tr><th scope="row">Entrega</th><td>Não fazemos. Retirada em {LOCAL} ou frete a combinar</td></tr>
<tr><th scope="row">Região que compensa</th><td>Até cerca de {RAIO} km da estância</td></tr>
<tr><th scope="row">Análise bromatológica</th><td>Em andamento; o laudo será publicado nesta página</td></tr>
</tbody></table></div>
</div></section>

<section id="calculadora"><div class="wrap">
<p class="rot">Calculadora</p>
<h2>Quantas toneladas de silagem eu preciso?</h2>
<p class="lead">A conta é: número de animais × quilos de silagem por animal por dia × número de dias, dividido por mil. Preencha com os números da sua dieta.</p>
<div class="caixa">
<form id="calc" data-preco="{S['preco_tonelada']}" data-estoque="{S['toneladas']}">
<div class="campos3">
<div class="campo"><label for="animais">Animais</label><input id="animais" name="animais" type="number" inputmode="numeric" min="1" value="50"></div>
<div class="campo"><label for="kg">Kg por animal/dia</label><input id="kg" name="kg" type="number" inputmode="decimal" min="1" step="0.5" value="30"></div>
<div class="campo"><label for="dias">Dias</label><input id="dias" name="dias" type="number" inputmode="numeric" min="1" value="90"></div>
</div>
<p class="nota">Os valores iniciais são só um exemplo. O consumo por animal muda com a categoria, o peso e o resto da dieta: use o número indicado pelo seu técnico ou nutricionista.</p>
</form>
<div class="saida" id="calc-saida" aria-live="polite">
<div class="num">135 <small>toneladas</small></div>
<p>Exemplo: 50 animais × 30 kg por dia × 90 dias = 135 toneladas. A R$ {PT} a tonelada, dá R$ {br(135 * S['preco_tonelada'])}, sem frete.</p>
{wa("Olá! Preciso de cerca de 135 t de silagem de milho. Ainda tem disponível?", "calculadora", "Pedir essa quantidade no WhatsApp")}
</div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Armazenagem</p>
<h2>Como a silagem está guardada</h2>
<div class="midia">
<div>{img("silo-lona-araucaria", "Silo trincheira coberto com lona branca e fileiras de sacos, com araucária ao fundo")}</div>
<div><p>A silagem de milho da {NOME} fica em silos trincheira, com paredes de tijolo e de madeira, cobertos com lona e fileiras de sacos de peso por cima e nas bordas. As fotos mostram os silos como estavam em novembro de 2026.</p>
<p>Na retirada, o carregamento é feito direto da face do silo para o seu caminhão. Vale combinar o transporte para que a silagem chegue e seja usada ou reensilada o quanto antes: silagem exposta ao ar perde qualidade.</p></div>
</div>
<div class="galeria" style="margin-top:20px">
<figure>{img("silo-coberto-eucaliptos", "Silo trincheira coberto visto de frente, com eucaliptos ao fundo")}<figcaption>Silo coberto, visto de frente</figcaption></figure>
<figure>{img("silagem-face-parede", "Silagem de milho compactada junto à parede do silo")}<figcaption>Face do silo junto à parede</figcaption></figure>
<figure>{img("lona-silos-graneleiros", "Lona do silo com sacos de peso e silos metálicos ao fundo")}<figcaption>Cobertura com lona e sacos</figcaption></figure>
<figure>{img("silo-trincheira-lateral", "Lateral do silo trincheira com muro de tijolo")}<figcaption>Muro lateral do silo</figcaption></figure>
</div>
</div></section>

<section><div class="wrap">
<p class="rot">Perguntas frequentes</p>
<h2>Dúvidas de quem compra silagem de milho</h2>
{FAQ_SIL}</div></section>
{chamada(f"{T} toneladas disponíveis, R$ {PT} a tonelada", f"Retirada em {LOCAL}. Diga a quantidade e a sua cidade.", msg_sil, "chamada-silagem")}
"""
prod_sil = {"@type": "Product", "@id": f"{DOM}/silagem-de-milho/#produto", "name": "Silagem de milho",
            "description": f"Silagem de milho vendida por tonelada pela {NOME}, em {LOCAL}. {T} toneladas disponíveis, retirada no local.",
            "category": "Volumoso para alimentação animal", "image": [f"{DOM}/fotos/silagem-face-detalhe.webp", f"{DOM}/fotos/silo-coberto-eucaliptos.webp"],
            "brand": {"@type": "Brand", "name": MARCA},
            "offers": oferta(S["preco_tonelada"], "TNE", "tonelada", S["toneladas"])}
pagina("/silagem-de-milho/", f"Silagem de milho a R$ {PT} a tonelada em {LOCAL}",
       f"{T} toneladas de silagem de milho a R$ {PT} a tonelada (R$ {PKG}/kg) em {LOCAL}. Retirada no local, até cerca de {RAIO} km. Calcule quanto você precisa.",
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
     f"Não. A retirada é na estância, em {LOCAL}, ou com frete a combinar. Costuma compensar para quem está a até cerca de {RAIO} km."),
    (f"Tem análise bromatológica do pré-secado?",
     f"{BROMA}"),
])
pre = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Pré-secado de azevém</p>
<p class="pill"><i></i><span>Disponível hoje · atualizado em {DATA_HTML}</span></p>
<h1>Pré-secado de azevém em bolas de {KG} kg: R$ {PB} a bola</h1>
<p class="sub">Também chamado de silagem pré-secada ou bola de silagem. Bolas embaladas em filme, à venda na {NOME}, em {LOCAL}. Cada bola pesa entre {KMIN} e {KMAX} kg. Retirada na estância ou frete a combinar.</p>
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
<tr><th scope="row">Entrega</th><td>Não fazemos. Retirada em {LOCAL} ou frete a combinar</td></tr>
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
       f"Pré-secado de azevém (silagem pré-secada) em bolas de cerca de {KG} kg a R$ {PB} cada, em {LOCAL}. Retirada no local. Veja fotos, vídeo e preço por quilo.",
       pre, [NEGOCIO, prod_pre, LD_PRE, migalha("Pré-secado de azevém", "/pre-secado-de-azevem/")],
       msg_pre, f"Pré-secado de azevém · R$ {PB} a bola", og="og-presecado.jpg")

# ---------------------------------------------------------------- REGIÃO
msg_reg = "Olá! Sou de ___ e quero saber se compensa buscar silagem ou pré-secado na Estância Safra."
lis = "".join(f"<li>{c} ({UF})</li>" for c in CIDADES)
reg = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Região e retirada</p>
<h1>Silagem de milho perto de {CIDADES[0]}, {CIDADES[1]} e {CIDADES[2]} ({UF})</h1>
<p class="sub">A {NOME} fica em {LOCAL}, no Oeste catarinense. Vendemos silagem de milho e pré-secado de azevém com retirada na estância, para propriedades num raio de cerca de {RAIO} km.</p>
<div class="acoes">{wa(msg_reg, "heroi-regiao", "Perguntar se compensa para a minha cidade", "bt claro")}<a class="bt linha" href="{F['perfil_google']}" rel="noopener">Abrir no Google Maps</a></div>
</div>
<figure>{img("silos-vista-vale", f"Silos trincheira cobertos na {NOME}, com pasto e mata ao fundo, em {LOCAL}", lazy=False)}<figcaption>Foto real · {LOCAL}, novembro de 2026</figcaption></figure>
</div></div>

<section><div class="wrap">
<p class="rot">Por que {RAIO} km</p>
<h2>O frete decide se a compra vale a pena</h2>
<p class="lead">Silagem e pré-secado são pesados e têm muita água. Quanto mais longe, mais o frete pesa em cada quilo que chega ao cocho. Pela nossa conta, a compra na {NOME} compensa para quem está a até cerca de {RAIO} km de {LOCAL}.</p>
<p>Esse raio é uma referência, não uma regra. Quem tem caminhão próprio ou leva carga fechada pode vir de mais longe. Diga a sua cidade e a quantidade pelo WhatsApp e fazemos a conta juntos, somando o frete ao preço de R$ {PT} a tonelada da silagem ou de R$ {PB} a bola do pré-secado.</p>
</div></section>

<section><div class="wrap">
<p class="rot">Municípios próximos</p>
<h2>Cidades que costumam ficar dentro do raio</h2>
<div class="duas">
<div><p>Além de {CID}, estes municípios do Oeste e do Meio-Oeste de Santa Catarina ficam na vizinhança da estância:</p>
<ul style="margin:16px 0 0 20px;columns:2">{lis}</ul>
<p class="nota">A lista é um ponto de partida. A distância que importa é a da estrada até a sua propriedade: confira a rota no <a href="{F['perfil_google']}" rel="noopener">perfil da estância no Google</a>.</p></div>
<div>{img("silo-parede-madeira-1", "Silo trincheira com parede de madeira escorada e silos metálicos ao fundo", w=1280, h=960)}</div>
</div></div></section>

<section class="escura"><div class="wrap">
<p class="rot">Retirada</p>
<h2>Como funciona a retirada na estância</h2>
<div class="tres">
<div class="passo"><p class="n">01</p><h3>Confirme o estoque</h3><p>Pelo WhatsApp, diga o produto e a quantidade. Hoje há {T} toneladas de silagem de milho e bolas de pré-secado de azevém.</p></div>
<div class="passo"><p class="n">02</p><h3>Marque o dia</h3><p>Combinamos dia e horário para o seu caminhão chegar. Sem caminhão, o frete é combinado à parte.</p></div>
<div class="passo"><p class="n">03</p><h3>Carregue em {CID}</h3><p>A silagem sai da face do silo; o pré-secado sai em bolas fechadas, de cerca de {KG} kg cada.</p></div>
</div></div></section>

<section><div class="wrap">
<p class="rot">Preços de hoje</p>
<h2>O que você encontra ao chegar</h2>
{tabela_oferta()}
</div></section>
{chamada("Sua cidade está no raio?", "Mande a cidade e a quantidade. Respondemos se compensa.", msg_reg, "chamada-regiao")}
"""
pagina("/regiao/", f"Silagem de milho perto de {CIDADES[0]} e região | Estância Safra",
       f"Silagem de milho e pré-secado de azevém com retirada em {LOCAL}, para produtores de {CIDADES[0]}, {CIDADES[1]}, {CIDADES[2]} e região, num raio de cerca de {RAIO} km.",
       reg, [NEGOCIO, migalha("Região e retirada", "/regiao/")], msg_reg, f"Retirada em {LOCAL}")

# ---------------------------------------------------------------- CONTATO
msg_con = "Olá! Quero comprar volumoso da Estância Safra."
con = f"""
<div class="heroi"><div class="wrap">
<div class="txt">
<p class="migalha"><a href="/">Início</a> › Contato</p>
<h1>Peça silagem de milho ou pré-secado pelo WhatsApp</h1>
<p class="sub">Atendimento direto com a {NOME}, em {LOCAL}. Preencha o pedido abaixo ou chame agora: confirmamos o estoque e combinamos a retirada.</p>
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
<p>Silagem de milho: R$ {PT} a tonelada ({T} t disponíveis).<br>Pré-secado de azevém: R$ {PB} a bola de cerca de {KG} kg.</p>
<p>Sem entrega: retirada no local ou frete a combinar.</p>
</div>
</div></div></section>
"""
pagina("/contato/", "Contato e pedido pelo WhatsApp | Estância Safra",
       f"Peça silagem de milho ou pré-secado de azevém direto à {NOME}, em {LOCAL}, pelo WhatsApp. Diga produto, quantidade e cidade.",
       con, [NEGOCIO, migalha("Contato", "/contato/")], msg_con, "Fale direto com a estância")

# ---------------------------------------------------------------- 404
pagina("/404.html", "Página não encontrada | Estância Safra", "Esta página não existe. Veja a silagem de milho e o pré-secado de azevém à venda.",
       f"""<section class="fim"><div class="wrap"><p class="rot">Erro 404</p><h1 class="h1-claro">Esta página não existe</h1>
<p class="lead">O que está à venda continua aqui:</p>{tabela_oferta()}<p style="margin-top:24px"><a class="bt" href="/">Voltar ao início</a></p></div></section>""",
       [NEGOCIO], msg_home, "Silagem e pré-secado à venda")

# ---------------------------------------------------------------- arquivos técnicos
(OUT / "assets").mkdir(parents=True, exist_ok=True)
for f in ("site.css", "site.js"):
    shutil.copyfile(SRC / f, OUT / "assets" / f)
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

urls = ["/", "/silagem-de-milho/", "/pre-secado-de-azevem/", "/regiao/", "/contato/"]


def imgs_da(u):
    h = (OUT / u.strip("/") / "index.html").read_text(encoding="utf-8")
    vistos = list(dict.fromkeys(re.findall(r'src="(/fotos/[^"]+\.webp)"', h)))
    return "".join(f"<image:image><image:loc>{DOM}{i}</image:loc></image:image>" for i in vistos)


(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
    "".join(f"  <url><loc>{DOM}{u}</loc><lastmod>{F['atualizado_em']}</lastmod>{imgs_da(u)}</url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOM}/sitemap.xml\n", encoding="utf-8")
(OUT / "llms.txt").write_text(f"""# Estância Safra ({NOME})

> Propriedade rural em {CID}, Santa Catarina, Brasil, que vende silagem de milho por tonelada e pré-secado de azevém em bolas, com retirada no local. Dados atualizados em {DATA}.

## Fatos
- Silagem de milho: R$ {PT} por tonelada (R$ {PKG} por kg), {T} toneladas disponíveis.
- Pré-secado de azevém: R$ {PB} por bola de cerca de {KG} kg ({KMIN} a {KMAX} kg), ou R$ {PKG_MIN} a R$ {PKG_MAX} por kg.
- Não há entrega: retirada em {LOCAL} ou frete a combinar. A compra costuma compensar até cerca de {RAIO} km.
- Análise bromatológica em andamento; nenhum valor de composição é informado antes do laudo.
- Contato: WhatsApp, pelos botões do site.

## Páginas
- [Silagem de milho]({DOM}/silagem-de-milho/): preço, estoque, armazenagem, calculadora de toneladas.
- [Pré-secado de azevém]({DOM}/pre-secado-de-azevem/): preço por bola e por quilo, peso, vídeo, comparação com a silagem.
- [Região e retirada]({DOM}/regiao/): municípios próximos e como funciona a retirada.
- [Contato]({DOM}/contato/): pedido pelo WhatsApp.
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
