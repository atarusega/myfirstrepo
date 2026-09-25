(function () {
  var tiles = document.querySelectorAll(".tile");

  // Сетка подстраивается под число проектов и пропорции окна: плитки ~3:2
  var grid = document.querySelector(".grid");
  function fit() {
    var n = tiles.length, w = grid.clientWidth || window.innerWidth;
    var h = window.innerHeight - 60, best = 1, bestScore = Infinity;
    if (w < 100 || h < 100) return;
    for (var cols = 1; cols <= n; cols++) {
      var rows = Math.ceil(n / cols);
      var score = Math.abs(Math.log((w / cols) / (h / rows) / 1.5)) + (cols * rows - n) * 0.08;
      if (score < bestScore) { bestScore = score; best = cols; }
    }
    grid.style.setProperty("--cols", best);
    grid.style.setProperty("--rows", Math.ceil(n / best));
  }
  fit();
  window.addEventListener("resize", fit);
  var lb = document.getElementById("lightbox");
  var strip = lb.querySelector(".lb-strip");
  var title = lb.querySelector(".lb-title");

  // При наведении плитка листает фотографии проекта
  tiles.forEach(function (t) {
    var imgs = t.dataset.images.split("|"), img = t.querySelector("img"), i = 0, timer;
    t.addEventListener("mouseenter", function () {
      timer = setInterval(function () { i = (i + 1) % imgs.length; img.src = imgs[i]; }, 700);
    });
    t.addEventListener("mouseleave", function () {
      clearInterval(timer); i = 0; img.src = imgs[0];
    });
    t.addEventListener("click", function (e) {
      e.preventDefault();
      title.textContent = t.dataset.title;
      strip.innerHTML = "";
      imgs.forEach(function (src) {
        var im = document.createElement("img"); im.src = src; im.alt = t.dataset.title;
        strip.appendChild(im);
      });
      lb.hidden = false; lb.scrollTop = 0; document.body.style.overflow = "hidden";
    });
  });

  function close() { lb.hidden = true; document.body.style.overflow = ""; }
  lb.querySelector(".lb-close").addEventListener("click", close);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
})();
