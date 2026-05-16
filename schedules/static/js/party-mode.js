(function () {
  'use strict';

  var raf = null;
  var currentHue = Math.random() * 360;
  var targetHue = pickTarget();

  function pickTarget() {
    // Jump 60–270 degrees away so consecutive targets always look distinct
    var jump = 60 + Math.random() * 210;
    return (currentHue + jump) % 360;
  }

  // Shortest-path lerp on the 0–360 hue circle
  function lerpHue(a, b, t) {
    var d = b - a;
    if (d > 180)  d -= 360;
    if (d < -180) d += 360;
    return (a + d * t + 360) % 360;
  }

  var dark = function () {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  };

  function applyHue(h) {
    var r = document.documentElement;
    var d = dark();
    var pL  = d ? 60  : 52;   // primary lightness
    var pS  = d ? 90  : 88;   // primary saturation
    var bgS = d ? 12  : 20;   // background saturation
    var bgL = d ? 5   : 97;   // background lightness
    var sfS = d ? 6   : 10;   // surface saturation
    var sfL = d ? 12  : 100;  // surface lightness
    var s2L = d ? 18  : 96;   // surface-2 lightness
    var comp  = (h + 150) % 360;  // near-complement for bg
    var tri1  = (h + 120) % 360;  // triadic 1 → green
    var tri2  = (h + 240) % 360;  // triadic 2 → red

    r.style.setProperty('--blue',        'hsl(' + h     + ',' + pS  + '%,' + pL      + '%)');
    r.style.setProperty('--blue-hover',  'hsl(' + h     + ',' + pS  + '%,' + (pL-9)  + '%)');
    r.style.setProperty('--blue-tint',   'hsla(' + h    + ',' + pS  + '%,' + pL + '%,0.15)');
    r.style.setProperty('--nav-bg',      'hsla(' + comp + ',' + bgS + '%,' + bgL + '%,0.82)');
    r.style.setProperty('--bg',          'hsl('  + comp + ',' + bgS + '%,' + bgL      + '%)');
    r.style.setProperty('--surface',     'hsl('  + comp + ',' + sfS + '%,' + sfL      + '%)');
    r.style.setProperty('--surface-2',   'hsl('  + comp + ',' + (sfS+4) + '%,' + s2L  + '%)');
    r.style.setProperty('--green',       'hsl(' + tri1  + ',' + pS  + '%,' + pL      + '%)');
    r.style.setProperty('--green-tint',  'hsla(' + tri1 + ',' + pS  + '%,' + pL + '%,0.15)');
    r.style.setProperty('--red',         'hsl(' + tri2  + ',' + pS  + '%,' + pL      + '%)');
    r.style.setProperty('--red-hover',   'hsl(' + tri2  + ',' + pS  + '%,' + (pL-9)  + '%)');
    r.style.setProperty('--red-tint',    'hsla(' + tri2 + ',' + pS  + '%,' + pL + '%,0.15)');
  }

  function loop() {
    currentHue = lerpHue(currentHue, targetHue, 0.016);
    // When close enough, pick a new target
    if (Math.abs(currentHue - targetHue) < 1.2) {
      targetHue = pickTarget();
    }
    applyHue(currentHue);
    raf = requestAnimationFrame(loop);
  }

  var PROPS = [
    '--blue','--blue-hover','--blue-tint',
    '--nav-bg','--bg','--surface','--surface-2',
    '--green','--green-tint','--red','--red-hover','--red-tint'
  ];

  function start() {
    if (raf) return;
    raf = requestAnimationFrame(loop);
    document.body.classList.add('party-mode');
    try { localStorage.setItem('partyMode', '1'); } catch (e) {}
    updateBtn(true);
  }

  function stop() {
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    var r = document.documentElement;
    PROPS.forEach(function (p) { r.style.removeProperty(p); });
    document.body.classList.remove('party-mode');
    try { localStorage.removeItem('partyMode'); } catch (e) {}
    updateBtn(false);
  }

  function toggle() { raf ? stop() : start(); }

  function updateBtn(on) {
    var btn = document.getElementById('party-btn');
    if (btn) btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  // Keyboard shortcut: Shift+P
  document.addEventListener('keydown', function (e) {
    if (e.shiftKey && (e.key === 'P' || e.key === 'p')) toggle();
  });

  // Wire button + restore saved state
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('party-btn');
    if (btn) btn.addEventListener('click', toggle);
    try { if (localStorage.getItem('partyMode')) start(); } catch (e) {}
  });

  window._partyMode = { start: start, stop: stop, toggle: toggle };
}());
