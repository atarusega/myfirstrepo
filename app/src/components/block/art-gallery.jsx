"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { WebGLSurface, useEffectReducedMotion } from "@/lib/effects/shared/webgl-surface";
import { cn } from "@/lib/utils";
import { LoaderGooeyBlobs } from "@/components/ui/loaders-gooey-blobs";

const defaultConfig = {
  cellSize: 0.75,
  zoomLevel: 1.25,
  lerpFactor: 0.075,
  // Фирменный стиль STRUKTORUM: графит, линии сетки, синяя подсветка ячеек у курсора
  borderColor: "rgba(255, 255, 255, 0.09)",
  backgroundColor: "rgba(28, 28, 28, 1)",
  textColor: "rgba(236, 236, 230, 1)",
  hoverColor: "rgba(58, 62, 216, 0.55)",
};

const defaultItems = [
  { title: "Motion Study", year: 2024 },
  { title: "Idle Form", year: 2023 },
  { title: "Blur Signal", year: 2024 },
  { title: "Still Drift", year: 2023 },
  { title: "Tidewalk", year: 2024 },
  { title: "Core Motion", year: 2022 },
  { title: "White Bloom", year: 2024 },
  { title: "Backrun", year: 2023 },
  { title: "Rushline", year: 2024 },
  { title: "Afterimage", year: 2023 },
  { title: "Shadowhead", year: 2022 },
  { title: "Opal Lace", year: 2024 },
  { title: "Glassprint", year: 2024 },
  { title: "Redshift", year: 2023 },
  { title: "White Noise", year: 2023 },
  { title: "Twin Field", year: 2024 },
  { title: "Petalloop", year: 2023 },
  { title: "Ghostwalk", year: 2024 },
  { title: "Heatwave", year: 2023 },
  { title: "Sky Drift", year: 2024 },
  { title: "Spindle", year: 2022 },
  { title: "Pacer", year: 2023 },
  { title: "Stride", year: 2024 },
  { title: "Cryo Pulse", year: 2022 },
  { title: "Velvet Blur", year: 2024 },
];

const defaultImages = [
  "https://cdn-new.obsidianui.dev/imagess/1.png",
  "https://cdn-new.obsidianui.dev/imagess/2.png",
  "https://cdn-new.obsidianui.dev/imagess/3.png",
  "https://cdn-new.obsidianui.dev/imagess/4.png",
  "https://cdn-new.obsidianui.dev/imagess/5.png",
  "https://cdn-new.obsidianui.dev/imagess/6.png",
  "https://cdn-new.obsidianui.dev/imagess/7.png",
  "https://cdn-new.obsidianui.dev/imagess/8.png",
  "https://cdn-new.obsidianui.dev/imagess/9.png",
  "https://cdn-new.obsidianui.dev/imagess/10.png",
  "https://cdn-new.obsidianui.dev/imagess/11.png",
  "https://cdn-new.obsidianui.dev/imagess/12.png",
  "https://cdn-new.obsidianui.dev/imagess/13.png",
  "https://cdn-new.obsidianui.dev/imagess/14.png",
  "https://cdn-new.obsidianui.dev/imagess/15.png",
  "https://cdn-new.obsidianui.dev/imagess/16.png",
  "https://cdn-new.obsidianui.dev/imagess/17.png",
  "https://cdn-new.obsidianui.dev/imagess/18.png",
  "https://cdn-new.obsidianui.dev/imagess/19.png",
  "https://cdn-new.obsidianui.dev/imagess/20.jpg",
  "https://cdn-new.obsidianui.dev/imagess/21.jpg",
  "https://cdn-new.obsidianui.dev/imagess/22.jpg",
  "https://cdn-new.obsidianui.dev/imagess/23.jpg",
  "https://cdn-new.obsidianui.dev/imagess/24.jpg",
  "https://cdn-new.obsidianui.dev/imagess/25.jpg",
];

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  uniform vec2 uOffset;
  uniform vec2 uResolution;
  uniform vec4 uBorderColor;
  uniform vec4 uHoverColor;
  uniform vec4 uBackgroundColor;
  uniform vec2 uMousePos;
  uniform float uZoom;
  uniform float uCellSize;
  uniform float uImageSize;
  uniform float uRadius;
  uniform float uTextTop;
  uniform float uTextH;
  uniform float uTextureCount;
  uniform sampler2D uImageAtlas;
  uniform sampler2D uTextAtlas;
  varying vec2 vUv;

  void main() {
    vec2 screenUV = (vUv - 0.5) * 2.0;
    float radius = length(screenUV);
    float distortion = 1.0 - 0.08 * radius * radius;
    vec2 distortedUV = screenUV * distortion;
    vec2 aspectRatio = vec2(uResolution.x / uResolution.y, 1.0);
    vec2 worldCoord = distortedUV * aspectRatio;
    worldCoord *= uZoom;
    worldCoord += uOffset;
    vec2 cellPos = worldCoord / uCellSize;
    vec2 cellId = floor(cellPos);
    vec2 cellUV = fract(cellPos);
    vec2 mouseScreenUV = (uMousePos / uResolution) * 2.0 - 1.0;
    mouseScreenUV.y = -mouseScreenUV.y;
    float mouseRadius = length(mouseScreenUV);
    float mouseDistortion = 1.0 - 0.08 * mouseRadius * mouseRadius;
    vec2 mouseDistortedUV = mouseScreenUV * mouseDistortion;
    vec2 mouseWorldCoord = mouseDistortedUV * aspectRatio;
    mouseWorldCoord *= uZoom;
    mouseWorldCoord += uOffset;
    vec2 mouseCellPos = mouseWorldCoord / uCellSize;
    vec2 mouseCellId = floor(mouseCellPos);
    vec2 cellCenter = cellId + 0.5;
    vec2 mouseCellCenter = mouseCellId + 0.5;
    float cellDistance = length(cellCenter - mouseCellCenter);
    float hoverIntensity = 1.0 - smoothstep(0.4, 0.7, cellDistance);
    bool isHovered = hoverIntensity > 0.0 && uMousePos.x >= 0.0;
    vec3 backgroundColor = uBackgroundColor.rgb;
    if (isHovered) {
      backgroundColor = mix(uBackgroundColor.rgb, uHoverColor.rgb, hoverIntensity * uHoverColor.a);
    }
    float lineWidth = 0.005;
    float gridX = smoothstep(0.0, lineWidth, cellUV.x) * smoothstep(0.0, lineWidth, 1.0 - cellUV.x);
    float gridY = smoothstep(0.0, lineWidth, cellUV.y) * smoothstep(0.0, lineWidth, 1.0 - cellUV.y);
    float gridMask = gridX * gridY;
    // Сверху название (до двух строк), под ним картинка; оба выровнены по одному левому краю
    float imageSize = uImageSize;
    float imageLeft = (1.0 - imageSize) * 0.5;
    float textBottom = uTextTop - uTextH;
    float imageBottom = textBottom - 0.025 - imageSize;
    vec2 imageUV = vec2((cellUV.x - imageLeft) / imageSize, (cellUV.y - imageBottom) / imageSize);
    // Скруглённый прямоугольник (SDF), радиус в долях стороны картинки
    vec2 q = abs(imageUV - 0.5) - (0.5 - uRadius);
    float roundDist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - uRadius;
    float edgeSmooth = 0.006;
    float imageAlpha = 1.0 - smoothstep(-edgeSmooth, edgeSmooth, roundDist);
    bool inImageArea = imageUV.x >= 0.0 && imageUV.x <= 1.0 && imageUV.y >= 0.0 && imageUV.y <= 1.0;
    bool inTextArea = cellUV.x >= imageLeft && cellUV.x <= imageLeft + imageSize && cellUV.y >= textBottom && cellUV.y <= uTextTop;
    float texIndex = mod(cellId.x + cellId.y * 3.0, uTextureCount);
    vec3 color = backgroundColor;
    if (inImageArea && imageAlpha > 0.0) {
      float atlasSize = ceil(sqrt(uTextureCount));
      vec2 atlasPos = vec2(mod(texIndex, atlasSize), floor(texIndex / atlasSize));
      // Строки атласа идут сверху вниз, как и у подписей; переворачиваем только кадр внутри ячейки
      vec2 atlasUV = vec2(atlasPos.x + imageUV.x, atlasPos.y + 1.0 - imageUV.y) / atlasSize;
      vec3 imageColor = texture2D(uImageAtlas, atlasUV).rgb;
      color = mix(color, imageColor, imageAlpha);
    }
    if (inTextArea) {
      vec2 textCoord = vec2((cellUV.x - imageLeft) / imageSize, 1.0 - (cellUV.y - textBottom) / uTextH);
      float atlasSize = ceil(sqrt(uTextureCount));
      vec2 atlasPos = vec2(mod(texIndex, atlasSize), floor(texIndex / atlasSize));
      vec2 atlasUV = (atlasPos + textCoord) / atlasSize;
      vec4 textColor = texture2D(uTextAtlas, atlasUV);
      color = mix(backgroundColor, textColor.rgb, textColor.a);
    }
    vec3 borderRGB = uBorderColor.rgb;
    float borderAlpha = uBorderColor.a;
    color = mix(color, borderRGB, (1.0 - gridMask) * borderAlpha);
    float fade = 1.0 - smoothstep(1.2, 1.8, radius);
    gl_FragColor = vec4(color * fade, 1.0);
  }
`;

function rgbaToArray(rgba) {
  const match = rgba.match(/rgba?\(([^)]+)\)/);
  if (!match) return [1, 1, 1, 1];
  const parts = match[1].split(",");
  return [
    parseFloat(parts[0]) / 255,
    parseFloat(parts[1]) / 255,
    parseFloat(parts[2]) / 255,
    parseFloat(parts[3] ?? "1"),
  ];
}

// Ширина текстуры названия в пикселях; высота — по пропорциям полосы названия в ячейке
const TEXT_TEX_W = 768;

function createTextTexture(title, textColor, band) {
  const canvas = document.createElement("canvas");
  canvas.width = TEXT_TEX_W;
  canvas.height = Math.round((TEXT_TEX_W * band.h) / band.w);
  const ctx = canvas.getContext("2d");
  if (ctx) {
    const W = canvas.width, H = canvas.height;
    let size = (TEXT_TEX_W * band.text) / band.w;
    const minSize = size * 0.6;
    const words = String(title).toUpperCase().split(/\s+/);
    // Раскладываем слова максимум на две строки; не влезает — уменьшаем кегль, в крайнем случае многоточие
    const layout = () => {
      ctx.font = `700 ${size}px "Unbounded", sans-serif`;
      if ("letterSpacing" in ctx) ctx.letterSpacing = `${size * 0.04}px`;
      const lines = [""];
      for (const word of words) {
        const next = lines[lines.length - 1] ? `${lines[lines.length - 1]} ${word}` : word;
        if (ctx.measureText(next).width <= W) lines[lines.length - 1] = next;
        else lines.push(word);
      }
      return lines;
    };
    let lines = layout();
    while ((lines.length > 2 || lines.some((l) => ctx.measureText(l).width > W)) && size > minSize) {
      size *= 0.92;
      lines = layout();
    }
    if (lines.length > 2) lines = [lines[0], lines.slice(1).join(" ")];
    lines = lines.map((l) => {
      let t = l;
      while (t.length > 1 && ctx.measureText(t).width > W) t = t.slice(0, -2) + "…";
      return t;
    });
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = textColor;
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    // Строки прижаты к низу полосы, то есть к картинке
    const lineH = size * 1.2;
    lines.forEach((line, i) => ctx.fillText(line, 0, H - (lines.length - 1 - i) * lineH));
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.flipY = false;
  texture.generateMipmaps = false;
  return texture;
}

function blankTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 512;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#111";
    ctx.fillRect(0, 0, 512, 512);
  }
  return new THREE.CanvasTexture(canvas);
}

function loadImageTexture(src) {
  return new Promise((resolve) => {
    const image = new Image();
    let retries = 0;
    if (/^https?:\/\//.test(src)) image.crossOrigin = "anonymous";
    image.decoding = "async";
    image.onload = async () => {
      try { await image.decode(); } catch {}
      const texture = new THREE.Texture(image);
      texture.wrapS = THREE.ClampToEdgeWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.flipY = false;
      texture.needsUpdate = true;
      resolve(texture);
    };
    image.onerror = () => {
      if (retries === 0) {
        retries = 1;
        image.src = `${src}${src.includes("?") ? "&" : "?"}retry=1`;
        return;
      }
      resolve(null);
    };
    image.src = src;
  });
}

function createTextureAtlas(textures, isText = false) {
  const atlasSize = Math.ceil(Math.sqrt(textures.length));
  const textureSize = 512;
  const first = textures[0]?.image;
  const cellW = isText && first ? first.width : textureSize;
  const cellH = isText && first ? first.height : textureSize;
  const canvas = document.createElement("canvas");
  canvas.width = atlasSize * cellW;
  canvas.height = atlasSize * cellH;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    if (isText) ctx.clearRect(0, 0, canvas.width, canvas.height);
    else {
      ctx.fillStyle = "black";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    const fallback = textures.find((texture) => texture.source?.data ?? texture.image);
    const fallbackSource = fallback?.source?.data ?? fallback?.image;
    textures.forEach((texture, index) => {
      const x = (index % atlasSize) * cellW;
      const y = Math.floor(index / atlasSize) * cellH;
      const src = texture.source?.data ?? texture.image;
      if (!src) return;
      const sw = src.naturalWidth || src.width, sh = src.naturalHeight || src.height;
      const side = isText ? 0 : Math.min(sw, sh);
      try {
        if (isText) ctx.drawImage(src, x, y, cellW, cellH);
        else if (!side) ctx.drawImage(src, x, y, textureSize, textureSize);
        else ctx.drawImage(src, (sw - side) / 2, (sh - side) / 2, side, side, x, y, textureSize, textureSize);
      }
      catch {
        if (fallbackSource) ctx.drawImage(fallbackSource, x, y, textureSize, textureSize);
      }
    });
  }
  const atlasTexture = new THREE.CanvasTexture(canvas);
  atlasTexture.wrapS = THREE.ClampToEdgeWrapping;
  atlasTexture.wrapT = THREE.ClampToEdgeWrapping;
  atlasTexture.minFilter = isText ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
  atlasTexture.generateMipmaps = isText;
  atlasTexture.magFilter = THREE.LinearFilter;
  atlasTexture.flipY = false;
  return atlasTexture;
}

function ArtGalleryScene({ images, items, cellSize, zoomLevel, showHint, reducedMotion, onSelect, imageSize, imageRadius, textSize, drift, paused }) {
  const containerRef = useRef(null);
  // Пока поверх открыт проект, сетку не видно — не рисуем её, чтобы не отнимать видеокарту у ленты
  const pausedRef = useRef(paused);
  pausedRef.current = paused;
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [ready, setReady] = useState(false);
  // Подсказка видна только в начале: гаснет после первого касания или через 6 секунд
  const [hint, setHint] = useState(true);
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => setHint(false), 6000);
    return () => clearTimeout(t);
  }, [ready]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    setReady(false);

    let cancelled = false;
    let animFrameId = 0;
    let renderer;
    let plane;
    let geometry;
    let material;
    let imageAtlas;
    let textAtlas;
    const loadedTextures = [];
    let resizeObserver;

    const state = {
      isDragging: false,
      previousPointer: { x: 0, y: 0 },
      downPointer: { x: 0, y: 0 },
      travel: 0,
      offset: { x: 0, y: 0 },
      targetOffset: { x: 0, y: 0 },
      mousePosition: { x: -1, y: -1 },
      zoom: 1,
      targetZoom: 1,
      // Инерция после броска: скорость в мировых единицах за кадр (60 fps)
      velocity: { x: 0, y: 0 },
      lastMoveTime: 0,
    };

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
    camera.position.z = 1;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    const bgColor = rgbaToArray(defaultConfig.backgroundColor);
    renderer.setClearColor(new THREE.Color(bgColor[0], bgColor[1], bgColor[2]), bgColor[3]);
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.touchAction = "none";
    container.appendChild(renderer.domElement);

    // Полоса названия: две строки кеглем textSize (в долях ячейки), ширина = ширине картинки.
    // Блок «название + зазор + картинка» центрируем по вертикали
    const textH = textSize * 1.2 * 2;
    const blockH = textH + 0.025 + imageSize;
    const textBand = { w: imageSize, h: textH, text: textSize, top: 1 - (1 - blockH) / 2 };

    const lerpFactor = reducedMotion ? 1 : defaultConfig.lerpFactor;
    const dragZoom = reducedMotion ? 1 : zoomLevel;

    let lastFrame = performance.now();
    const animate = () => {
      animFrameId = requestAnimationFrame(animate);
      const now = performance.now();
      const k = Math.min((now - lastFrame) / 16.667, 4); // доля кадра 60 fps
      lastFrame = now;
      if (pausedRef.current) return;
      if (!state.isDragging && !reducedMotion) {
        // Сетка катится по инерции и плавно гаснет
        state.targetOffset.x += state.velocity.x * k;
        state.targetOffset.y += state.velocity.y * k;
        const friction = Math.pow(0.95, k);
        state.velocity.x *= friction;
        state.velocity.y *= friction;
        // Медленный собственный дрейф (включается на телефоне)
        if (drift) {
          state.targetOffset.x += drift[0] * k;
          state.targetOffset.y += drift[1] * k;
        }
      }
      state.offset.x += (state.targetOffset.x - state.offset.x) * lerpFactor;
      state.offset.y += (state.targetOffset.y - state.offset.y) * lerpFactor;
      state.zoom += (state.targetZoom - state.zoom) * lerpFactor;
      if (plane?.material.uniforms) {
        plane.material.uniforms.uOffset.value.set(state.offset.x, state.offset.y);
        plane.material.uniforms.uZoom.value = state.zoom;
      }
      renderer.render(scene, camera);
    };

    const updateMousePosition = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      state.mousePosition.x = event.clientX - rect.left;
      state.mousePosition.y = event.clientY - rect.top;
      plane?.material.uniforms.uMousePos.value.set(state.mousePosition.x, state.mousePosition.y);
    };

    // Та же математика, что в шейдере: пиксель -> ячейка -> индекс картинки
    const tileIndexAt = (clientX, clientY) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const sx = ((clientX - rect.left) / rect.width) * 2 - 1;
      const sy = -(((clientY - rect.top) / rect.height) * 2 - 1);
      const radius = Math.hypot(sx, sy);
      const distortion = 1 - 0.08 * radius * radius;
      const wx = sx * distortion * (rect.width / rect.height) * state.zoom + state.offset.x;
      const wy = sy * distortion * state.zoom + state.offset.y;
      const cx = Math.floor(wx / cellSize), cy = Math.floor(wy / cellSize);
      const n = images.length;
      return (((cx + cy * 3) % n) + n) % n;
    };

    const startDrag = (x, y) => {
      state.isDragging = true;
      state.downPointer.x = x;
      state.downPointer.y = y;
      state.travel = 0;
      state.velocity.x = state.velocity.y = 0; // касание останавливает инерцию
      state.lastMoveTime = performance.now();
      state.previousPointer.x = x;
      state.previousPointer.y = y;
    };

    const handleMove = (x, y) => {
      if (!state.isDragging) return;
      const deltaX = x - state.previousPointer.x;
      const deltaY = y - state.previousPointer.y;
      state.travel += Math.abs(deltaX) + Math.abs(deltaY);
      if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
        if (state.targetZoom === 1) state.targetZoom = dragZoom;
      }
      state.targetOffset.x -= deltaX * 0.003;
      state.targetOffset.y += deltaY * 0.003;
      const now = performance.now();
      const dt = Math.max(now - state.lastMoveTime, 1);
      state.lastMoveTime = now;
      // Сглаженная скорость, пересчитанная на кадр 60 fps
      const blend = 0.35;
      state.velocity.x = state.velocity.x * (1 - blend) + ((-deltaX * 0.003) / dt) * 16.667 * blend;
      state.velocity.y = state.velocity.y * (1 - blend) + ((deltaY * 0.003) / dt) * 16.667 * blend;
      state.previousPointer.x = x;
      state.previousPointer.y = y;
    };

    const endDrag = () => {
      // Палец задержали на месте перед отпусканием — броска нет
      if (performance.now() - state.lastMoveTime > 80) state.velocity.x = state.velocity.y = 0;
      const max = 0.08;
      state.velocity.x = Math.max(-max, Math.min(max, state.velocity.x));
      state.velocity.y = Math.max(-max, Math.min(max, state.velocity.y));
      state.isDragging = false;
      state.targetZoom = 1;
    };

    // Колёсико мыши и тачпад двигают сетку (у тачпада своя инерция)
    const onWheel = (event) => {
      event.preventDefault();
      const scale = event.deltaMode === 1 ? 0.05 : 0.0015;
      state.velocity.x = state.velocity.y = 0;
      state.targetOffset.x += event.deltaX * scale;
      state.targetOffset.y -= event.deltaY * scale;
    };

    const onPointerDown = (event) => {
      event.preventDefault();
      container.setPointerCapture?.(event.pointerId);
      startDrag(event.clientX, event.clientY);
    };
    const onPointerMove = (event) => {
      updateMousePosition(event);
      handleMove(event.clientX, event.clientY);
    };
    const onPointerUp = (event) => {
      if (container.hasPointerCapture?.(event.pointerId)) container.releasePointerCapture(event.pointerId);
      const wasClick = state.isDragging && state.travel < 6;
      endDrag();
      if (wasClick && event.type === "pointerup") onSelectRef.current?.(tileIndexAt(event.clientX, event.clientY));
    };
    const onPointerLeave = () => {
      state.mousePosition.x = state.mousePosition.y = -1;
      plane?.material.uniforms.uMousePos.value.set(-1, -1);
      endDrag();
    };
    const onResize = () => {
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (!width || !height) return;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      plane?.material.uniforms.uResolution.value.set(width, height);
    };

    const init = async () => {
      const loadedImages = await Promise.all(images.map((src) => loadImageTexture(src)));
      if (cancelled) {
        loadedImages.forEach((texture) => texture?.dispose());
        return;
      }
      const replacement = loadedImages.find(Boolean) ?? blankTexture();
      const imageTiles = loadedImages.map((texture) => texture ?? replacement);
      loadedTextures.push(...new Set(imageTiles));
      try { await document.fonts.load('700 56px "Unbounded"', "АБВ"); } catch {}
      if (cancelled) return;
      const textTextures = items.map((item) => createTextTexture(item.title, defaultConfig.textColor, textBand));
      loadedTextures.push(...textTextures);
      imageAtlas = createTextureAtlas(imageTiles, false);
      textAtlas = createTextureAtlas(textTextures, true);
      if (cancelled) return;

      const uniforms = {
        uOffset: { value: new THREE.Vector2(0, 0) },
        uResolution: { value: new THREE.Vector2(container.clientWidth, container.clientHeight) },
        uBorderColor: { value: new THREE.Vector4(...rgbaToArray(defaultConfig.borderColor)) },
        uHoverColor: { value: new THREE.Vector4(...rgbaToArray(defaultConfig.hoverColor)) },
        uBackgroundColor: { value: new THREE.Vector4(...rgbaToArray(defaultConfig.backgroundColor)) },
        uMousePos: { value: new THREE.Vector2(-1, -1) },
        uZoom: { value: 1 },
        uCellSize: { value: cellSize },
        uImageSize: { value: imageSize },
        uTextTop: { value: textBand.top },
        uTextH: { value: textBand.h },
        uRadius: { value: imageRadius },
        uTextureCount: { value: images.length },
        uImageAtlas: { value: imageAtlas },
        uTextAtlas: { value: textAtlas },
      };

      geometry = new THREE.PlaneGeometry(2, 2);
      material = new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms });
      plane = new THREE.Mesh(geometry, material);
      scene.add(plane);

      container.addEventListener("pointerdown", onPointerDown);
      container.addEventListener("pointermove", onPointerMove);
      container.addEventListener("pointerup", onPointerUp);
      container.addEventListener("pointercancel", onPointerUp);
      container.addEventListener("pointerleave", onPointerLeave);
      container.addEventListener("wheel", onWheel, { passive: false });
      window.addEventListener("resize", onResize);
      // Контейнер может получить размер позже монтирования — следим за ним напрямую
      resizeObserver = new ResizeObserver(onResize);
      resizeObserver.observe(container);
      onResize();
      animate();
      setReady(true);
    };

    init();

    return () => {
      cancelled = true;
      cancelAnimationFrame(animFrameId);
      container.removeEventListener("pointerdown", onPointerDown);
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("pointerup", onPointerUp);
      container.removeEventListener("pointercancel", onPointerUp);
      container.removeEventListener("pointerleave", onPointerLeave);
      container.removeEventListener("wheel", onWheel);
      window.removeEventListener("resize", onResize);
      resizeObserver?.disconnect();
      loadedTextures.forEach((texture) => texture.dispose());
      imageAtlas?.dispose();
      textAtlas?.dispose();
      geometry?.dispose();
      material?.dispose();
      renderer?.dispose();
      if (renderer?.domElement?.parentNode === container) container.removeChild(renderer.domElement);
    };
  }, [images, items, cellSize, zoomLevel, reducedMotion, imageSize, imageRadius, textSize, drift]);

  return (
    <div className="absolute inset-0 cursor-grab active:cursor-grabbing" style={{ touchAction: "none" }} onPointerDown={() => setHint(false)}>
      <div ref={containerRef} className="absolute inset-0" style={{ opacity: ready ? 1 : 0 }} />
      {!ready ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-graphite text-brand" role="status" aria-live="polite">
          <LoaderGooeyBlobs color="#3A3ED8" />
        </div>
      ) : null}
      {ready && showHint ? (
        <div
          className="pointer-events-none absolute bottom-6 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full bg-graphite/80 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/60 transition-opacity duration-700"
          style={{ opacity: hint ? 1 : 0 }}
        >
          тяни сетку · нажми на проект
        </div>
      ) : null}
    </div>
  );
}

/** @param {{ images?: string[], items?: { title: string, year: string | number }[], cellSize?: number, zoomLevel?: number, showHint?: boolean, onSelect?: (index: number) => void, imageSize?: number, imageRadius?: number, textSize?: number, paused?: boolean, drift?: [number, number], className?: string, style?: import("react").CSSProperties }} props */
export function ArtGallery({
  images = defaultImages,
  items = defaultItems,
  cellSize = defaultConfig.cellSize,
  zoomLevel = defaultConfig.zoomLevel,
  showHint = true,
  imageSize = 0.6,
  imageRadius = 0.035,
  textSize = 0.05,
  drift,
  paused = false,
  onSelect,
  className,
  style,
} = {}) {
  const reducedMotion = useEffectReducedMotion();
  const tiles = images.length ? images : defaultImages;
  const captions = useMemo(
    () => tiles.map((_, index) => items[index % items.length] ?? { title: `Study ${index + 1}`, year: "2024" }),
    [tiles, items],
  );

  return (
    <WebGLSurface className={cn("bg-graphite", className)} style={style} label="ObsidianUI Art Gallery">
      <ArtGalleryScene
        images={tiles}
        items={captions}
        cellSize={cellSize}
        zoomLevel={zoomLevel}
        showHint={showHint}
        reducedMotion={reducedMotion}
        onSelect={onSelect}
        imageSize={imageSize}
        imageRadius={imageRadius}
        textSize={textSize}
        drift={drift}
        paused={paused}
      />
    </WebGLSurface>
  );
}
