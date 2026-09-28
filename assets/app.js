(function () {
  var tiles = document.querySelectorAll(".tile");
  var grid = document.querySelector(".grid");

  // Сетка подстраивается под число проектов и пропорции окна: плитки ~3:2
  function fit() {
    var n = tiles.length, w = grid.clientWidth || window.innerWidth;
    var h = window.innerHeight - 60, best = 1, bestScore = Infinity;
    if (w < 100 || h < 100) return;
    for (var cols = 1; cols <= n; cols++) {
      var rows = Math.ceil(n / cols);
      var score = Math.abs(Math.log((w / cols) / (h / rows) / 1.5));
      if (score < bestScore) { bestScore = score; best = cols; }
    }
    grid.style.setProperty("--cols", best);
    grid.style.setProperty("--rows", Math.ceil(n / best));
    // Неполная последняя строка растягивается на всю ширину
    var rem = n % best, first = n - rem;
    tiles.forEach(function (t, i) {
      if (!rem || i < first) { t.style.gridColumn = ""; return; }
      var k = i - first;
      t.style.gridColumn = (Math.round(k * best / rem) + 1) + " / " + (Math.round((k + 1) * best / rem) + 1);
    });
  }
  fit();
  window.addEventListener("resize", fit);

  // При наведении плитка листает фотографии проекта
  tiles.forEach(function (t) {
    var imgs = t.dataset.images.split("|"), img = t.querySelector("img"), i = 0, timer;
    t.addEventListener("mouseenter", function () {
      timer = setInterval(function () { i = (i + 1) % imgs.length; img.src = imgs[i]; }, 700);
    });
    t.addEventListener("mouseleave", function () {
      clearInterval(timer); i = 0; img.src = imgs[0];
    });
    t.addEventListener("click", function (e) { e.preventDefault(); open(t, imgs); });
  });

  // Просмотр проекта
  var lb = document.getElementById("lightbox");
  var frame = lb.querySelector(".lb-frame");
  var layers = [lb.querySelector(".lb-img-a"), lb.querySelector(".lb-img-b")];
  var active = 0; // индекс текущего слоя в layers
  var thumbs = lb.querySelector(".lb-thumbs");
  var indexNav = lb.querySelector(".lb-index");
  var list = [], cur = 0;

  function show(n, dir) {
    var next = (n + list.length) % list.length;
    if (!dir) dir = next >= cur ? 1 : -1;
    cur = next;

    var from = layers[active], to = layers[1 - active];
    active = 1 - active;
    to.src = list[cur];
    to.classList.remove("out-left", "out-right");
    to.classList.add(dir > 0 ? "out-right" : "out-left");
    // eslint-disable-next-line no-unused-expressions
    to.offsetWidth; // форсируем применение стартового положения перед анимацией
    from.classList.remove("on");
    from.classList.add(dir > 0 ? "out-left" : "out-right");
    to.classList.add("on");
    to.classList.remove("out-left", "out-right");

    [].forEach.call(indexNav.children, function (b, k) { b.classList.toggle("on", k === cur); });
    var onBtn = indexNav.children[cur];
    if (onBtn) onBtn.scrollIntoView({ inline: "center", block: "nearest" });
    [].forEach.call(thumbs.children, function (im, k) { im.classList.toggle("on", k === cur); });
    thumbs.children[cur].scrollIntoView({ inline: "center", block: "nearest" });
    new Image().src = list[(cur + 1) % list.length];
  }

  function open(tile, imgs) {
    list = imgs;
    lb.style.setProperty("--c", getComputedStyle(tile).getPropertyValue("--c") || "");
    lb.style.setProperty("--t", getComputedStyle(tile).getPropertyValue("--t") || "");
    lb.querySelector(".lb-title").textContent = tile.dataset.title;
    lb.querySelector(".lb-post").href = tile.href;
    thumbs.innerHTML = "";
    indexNav.innerHTML = "";
    imgs.forEach(function (src, k) {
      var im = document.createElement("img"); im.src = src; im.alt = "";
      im.addEventListener("click", function () { show(k); });
      thumbs.appendChild(im);

      var b = document.createElement("button");
      b.type = "button";
      b.textContent = String(k + 1).padStart(2, "0");
      b.addEventListener("click", function () { show(k); });
      indexNav.appendChild(b);
    });
    layers.forEach(function (l) { l.classList.remove("on", "out-left", "out-right"); l.src = ""; });
    active = 0; cur = 0;
    layers[0].src = imgs[0];
    layers[0].classList.add("on");
    [].forEach.call(indexNav.children, function (b, k) { b.classList.toggle("on", k === 0); });
    [].forEach.call(thumbs.children, function (im, k) { im.classList.toggle("on", k === 0); });
    lb.hidden = false; document.body.style.overflow = "hidden";
  }

  function close() { lb.hidden = true; document.body.style.overflow = ""; }
  lb.querySelector(".lb-close").addEventListener("click", close);
  lb.querySelector(".lb-prev").addEventListener("click", function () { show(cur - 1, -1); });
  lb.querySelector(".lb-next").addEventListener("click", function () { show(cur + 1, 1); });
  frame.addEventListener("click", function (e) {
    var left = e.clientX - frame.getBoundingClientRect().left < frame.clientWidth / 2;
    show(cur + (left ? -1 : 1), left ? -1 : 1);
  });
  document.addEventListener("keydown", function (e) {
    if (lb.hidden) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(cur - 1, -1);
    if (e.key === "ArrowRight") show(cur + 1, 1);
  });

  // Свайп на телефоне
  var x0 = null;
  lb.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; });
  lb.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) show(dx < 0 ? cur + 1 : cur - 1, dx < 0 ? 1 : -1);
  });
})();
