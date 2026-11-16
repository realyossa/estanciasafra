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
    var preco = Number(calc.dataset.preco), estoque = Number(calc.dataset.estoque);
    var out = document.getElementById('calc-saida');
    var render = function () {
      var a = Number(calc.animais.value) || 0, k = Number(calc.kg.value) || 0, d = Number(calc.dias.value) || 0;
      var t = a * k * d / 1000;
      var aviso = t > estoque ? '<p><b>Passa do estoque de hoje (' + num(estoque, 0) + ' t).</b> Fale com a gente para ver o que dá para atender.</p>' : '';
      out.innerHTML = '<div class="num">' + num(t, 1) + ' <small>toneladas</small></div>' +
        '<p>' + num(a, 0) + ' animais × ' + num(k, 1) + ' kg por dia × ' + num(d, 0) + ' dias. A R$ ' + num(preco, 0) +
        ' a tonelada, dá <b>' + brl(t * preco) + '</b>, sem frete.</p>' + aviso +
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
