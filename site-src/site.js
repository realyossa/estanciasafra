// Safra · sem dependências. O conteúdo todo já está no HTML; isto só soma conveniência.
(function () {
  var cfg = document.documentElement.dataset;
  var zap = cfg.zap;

  // 1) Mede o lead: todo clique em WhatsApp vira evento (GA4 / dataLayer, se existirem)
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-lead]');
    if (!a) return;
    var dados = { event: 'lead_whatsapp', origem: a.dataset.lead, pagina: location.pathname };
    (window.dataLayer = window.dataLayer || []).push(dados);
    if (window.gtag) window.gtag('event', 'generate_lead', { method: 'whatsapp', origem: a.dataset.lead });
  });

  function brl(n) { return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }); }
  function num(n, d) { return n.toLocaleString('pt-BR', { maximumFractionDigits: d }); }
  function abrir(msg) { location.href = 'https://wa.me/' + zap + '?text=' + encodeURIComponent(msg); }

  // 2) Calculadora de toneladas
  var calc = document.getElementById('calc');
  if (calc) {
    var estoque = Number(calc.dataset.estoque), carga = Number(calc.dataset.carga) || 0;
    var minimo = Number(calc.dataset.minimo) || 0, cheio = Number(calc.dataset.preco), menor = Number(calc.dataset.precoMenor) || cheio;
    var out = document.getElementById('calc-saida');
    var render = function () {
      var a = Number(calc.animais.value) || 0, k = Number(calc.kg.value) || 0, d = Number(calc.dias.value) || 0;
      var t = a * k * d / 1000;
      var preco = t >= minimo ? cheio : menor;
      var nc = carga && t >= minimo ? Math.ceil(t / carga) : 0;
      var cargas = nc > 1 ? ', ou ' + nc + ' cargas de ' + num(carga, 0) + ' t' : (nc ? ', ou 1 carga' : '');
      var abaixo = t > 0 && t < minimo ? ' Abaixo de ' + num(minimo, 0) + ' t a tonelada sai a R$ ' + num(menor, 0) + ' e o pedido depende de disponibilidade.' : '';
      var aviso = t > estoque ? '<p><b>Passa do estoque de hoje (' + num(estoque, 0) + ' t).</b> Fale com a gente para ver o que dá para atender.</p>' : '';
      out.innerHTML = '<div class="num">' + num(t, 1) + ' <small>toneladas</small></div>' +
        '<p>' + num(a, 0) + ' animais × ' + num(k, 1) + ' kg por dia × ' + num(d, 0) + ' dias' + cargas + '. A R$ ' + num(preco, 0) +
        ' a tonelada, dá <b>' + brl(t * preco) + '</b>, sem frete.' + abaixo + '</p>' + aviso +
        '<a class="bt" data-lead="calculadora" href="https://wa.me/' + zap + '?text=' +
        encodeURIComponent('Olá! Fiz a conta no site: preciso de cerca de ' + num(t, 1) + ' t de silagem de milho (' + num(a, 0) + ' animais, ' + num(d, 0) + ' dias). Ainda tem disponível?') +
        '">Pedir essa quantidade no WhatsApp</a>';
    };
    calc.addEventListener('input', render);
    calc.addEventListener('submit', function (e) { e.preventDefault(); render(); });
    render();
  }

  // 3) Formulário de contato: monta a mensagem e abre o WhatsApp
  var form = document.getElementById('pedido');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = form.elements;
      var msg = 'Olá! Sou ' + f.nome.value + ', de ' + f.cidade.value + '. Tenho interesse em ' + f.produto.value +
        (f.qtd.value ? ', quantidade: ' + f.qtd.value : '') + '.' + (f.obs.value ? ' ' + f.obs.value : '');
      (window.dataLayer = window.dataLayer || []).push({ event: 'lead_formulario', produto: f.produto.value, cidade: f.cidade.value });
      if (window.gtag) window.gtag('event', 'generate_lead', { method: 'formulario', produto: f.produto.value });
      abrir(msg);
    });
  }
})();

// v2: barra do celular só depois do herói (o conteúdo nunca fica escondido esperando animação)
(function () {
  var barra = document.querySelector('.barra'), heroi = document.querySelector('.heroi');
  if (barra) {
    if (!heroi || !('IntersectionObserver' in window)) barra.classList.add('on');
    else new IntersectionObserver(function (e) { barra.classList.toggle('on', !e[0].isIntersecting); }).observe(heroi);
  }
})();

// v3: calculadora de frete (silagem à venda em SC) e comparador de bolas (pré-secado à venda)
(function () {
  var zap = document.documentElement.dataset.zap;
  function n(v) { return Number(String(v).replace(',', '.')) || 0; }
  function brl(v, d) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); }
  function num(v, d) { return v.toLocaleString('pt-BR', { maximumFractionDigits: d }); }
  function link(origem, rotulo, msg) {
    return '<a class="bt" data-lead="' + origem + '" rel="nofollow" href="https://wa.me/' + zap + '?text=' + encodeURIComponent(msg) + '">' + rotulo + '</a>';
  }

  var fr = document.getElementById('frete-calc');
  if (fr) {
    var cheio = n(fr.dataset.preco), menor = n(fr.dataset.precoMenor) || cheio, minimo = n(fr.dataset.minimo), out = document.getElementById('frete-saida');
    var r = function () {
      var t = n(fr.carga.value), v = Math.max(0, n(fr.viagem.value)), c = Math.max(1, Math.round(n(fr.cargas.value)) || 1);
      if (t <= 0) { out.innerHTML = '<div class="num">—</div><p>Informe as toneladas da carga.</p>'; return; }
      var preco = t * c >= minimo ? cheio : menor;
      var porT = v / t, total = (t * preco + v) * c;
      out.innerHTML = '<div class="num">' + brl(preco + porT, 2) + ' <small>por tonelada entregue</small></div>' +
        '<p>' + brl(preco) + ' da tonelada + ' + brl(v) + ' de frete ÷ ' + num(t, 1) + ' t = ' + brl(porT, 2) + ' de frete por tonelada. ' +
        (c > 1 ? c + ' viagens, ' + num(t * c, 1) + ' t' : 'A carga de ' + num(t, 1) + ' t') + ' sai por <b>' + brl(total) + '</b> no total.' + (preco !== cheio ? ' Abaixo de ' + num(minimo, 0) + ' t a tonelada sai a ' + brl(menor) + ', sob consulta de disponibilidade.' : '') + '</p>' +
        link('calculadora-frete', 'Pedir essa carga no WhatsApp', 'Olá! Fiz a conta no site: quero cerca de ' + num(t * c, 1) + ' t de silagem de milho a ' + brl(preco) + ' a tonelada. Ainda tem disponível?');
    };
    fr.addEventListener('input', r);
    fr.addEventListener('submit', function (e) { e.preventDefault(); r(); });
    r();
  }

  var bo = document.getElementById('bolas');
  if (bo) {
    var sb = document.getElementById('bolas-saida');
    var calc = function (p, k, m) {
      var o = { kg: p > 0 && k > 0 ? p / k : 0 };
      o.ms = o.kg && m > 0 && m <= 100 ? p / (k * m / 100) : 0;
      return o;
    };
    var rb = function () {
      var a = calc(n(bo.b1p.value), n(bo.b1k.value), n(bo.b1m.value));
      var b = calc(n(bo.b2p.value), n(bo.b2k.value), n(bo.b2m.value));
      var h = '<div class="num">' + (a.kg ? brl(a.kg, 2) : '—') + ' <small>por quilo (bola A)</small></div><p>';
      var qual = function (x, y, o) {
        if (Math.abs(x - y) < 0.005) return 'As duas saem pelo mesmo preço por quilo' + o + '.';
        return 'A bola <b>' + (x < y ? 'A' : 'B') + '</b> sai mais barata por quilo' + o + '.';
      };
      if (!a.kg) {
        h += 'Preencha o preço e o peso da bola A.';
      } else if (!b.kg) {
        h += 'Preencha o preço e o peso da bola B para comparar.';
      } else {
        h += 'Bola B: <b>' + brl(b.kg, 2) + '</b> por quilo. ';
        if (a.ms && b.ms) {
          h += 'Por quilo de matéria seca: A ' + brl(a.ms, 2) + ', B ' + brl(b.ms, 2) + '. ' + qual(a.ms, b.ms, ' de matéria seca');
        } else {
          h += qual(a.kg, b.kg, ' de peso') + ' Para comparar o alimento de verdade, preencha a matéria seca das duas bolas: parte do peso pode ser água.';
        }
      }
      sb.innerHTML = h + '</p>' + link('comparador-bolas', 'Pedir bolas no WhatsApp', 'Olá! Vi no site o pré-secado à venda. Quero ___ bolas. Ainda tem?');
    };
    bo.addEventListener('input', rb);
    bo.addEventListener('submit', function (e) { e.preventDefault(); rb(); });
    rb();
  }
})();
