'use strict';

const elementToggleFunc = function (elem) {
  elem.classList.toggle('active');
};

/* Theme */
(function initThemeToggle() {
  var btn = document.querySelector('[data-theme-toggle]');
  if (!btn) return;

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  function setLabel() {
    var dark = currentTheme() === 'dark';
    btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    btn.setAttribute('title', dark ? 'Light theme' : 'Dark theme');
  }

  btn.addEventListener('click', function () {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('nb-theme', next);
    } catch (e) {}
    setLabel();
  });

  setLabel();
})();

/* Section filters: portfolio, talks, publications */
const sectionsWithFilters = document.querySelectorAll(
  'section.projects, section.talks, section.publications-section'
);

const applyFilter = function (selectedValue, items) {
  items.forEach(function (it) {
    const itemCategories = it.dataset.category;
    if (selectedValue === 'all') {
      it.classList.add('active');
    } else if (itemCategories && itemCategories.includes(selectedValue)) {
      it.classList.add('active');
    } else {
      it.classList.remove('active');
    }
  });
};

sectionsWithFilters.forEach(function (section) {
  const select = section.querySelector('[data-select]');
  const selectItems = section.querySelectorAll('[data-select-item]');
  const selectValue = section.querySelector('[data-selecct-value]');
  const filterBtn = section.querySelectorAll('[data-filter-btn]');
  const filterItems = section.querySelectorAll('[data-filter-item]');

  if (select) {
    select.addEventListener('click', function () {
      elementToggleFunc(this);
    });

    selectItems.forEach(function (si) {
      si.addEventListener('click', function () {
        const selectedValue = this.innerText.toLowerCase();
        if (selectValue) selectValue.innerText = this.innerText;
        elementToggleFunc(select);
        applyFilter(selectedValue, filterItems);
      });
    });
  }

  if (filterBtn.length) {
    let lastClickedBtn = filterBtn[0];
    filterBtn.forEach(function (fb) {
      fb.addEventListener('click', function () {
        const selectedValue = this.innerText.toLowerCase();
        if (selectValue) selectValue.innerText = this.innerText;
        applyFilter(selectedValue, filterItems);

        if (lastClickedBtn) lastClickedBtn.classList.remove('active');
        this.classList.add('active');
        lastClickedBtn = this;
      });
    });
  }
});

/* Scroll reveals */
var scrollRevealObserver = null;

function revealAllReveals() {
  document.querySelectorAll('.reveal').forEach(function (el) {
    el.classList.add('reveal--visible');
  });
}

function flushRevealsInViewport() {
  var vh = window.innerHeight || document.documentElement.clientHeight;
  document.querySelectorAll('.reveal:not(.reveal--visible)').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.top < vh * 0.94 && r.bottom > vh * 0.06) {
      el.classList.add('reveal--visible');
    }
  });
}

function initScrollReveals() {
  if (!('IntersectionObserver' in window)) {
    revealAllReveals();
    return;
  }

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {
    reduceMotion = false;
  }

  if (reduceMotion) {
    revealAllReveals();
    return;
  }

  scrollRevealObserver = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('reveal--visible');
        scrollRevealObserver.unobserve(entry.target);
      });
    },
    { root: null, rootMargin: '0px 0px -5% 0px', threshold: 0.06 }
  );

  document.querySelectorAll('.reveal').forEach(function (el) {
    scrollRevealObserver.observe(el);
  });
}

initScrollReveals();
flushRevealsInViewport();

/* Sticky header shadow after scroll */
(function headerScrollState() {
  var header = document.querySelector('[data-site-header]');
  if (!header) return;
  var threshold = 12;
  function tick() {
    var y = window.scrollY || document.documentElement.scrollTop;
    header.classList.toggle('is-scrolled', y > threshold);
  }
  tick();
  window.addEventListener('scroll', tick, { passive: true });
})();

/* Nav highlight on scroll */
(function initSectionNav() {
  var navLinks = document.querySelectorAll('.site-nav a[href^="#"]');
  if (!navLinks.length) return;

  var ids = ['about', 'lab', 'publications', 'talks', 'training', 'focus', 'portfolio', 'tools', 'cv'];

  function update() {
    var probe = window.innerHeight * 0.28;
    var best = null;
    var bestScore = -1;
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var r = el.getBoundingClientRect();
      if (r.bottom <= 80 || r.top >= window.innerHeight) return;
      var visible = Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0);
      if (visible > bestScore) {
        bestScore = visible;
        best = id;
      }
    });
    if (!best) best = 'about';
    navLinks.forEach(function (a) {
      var href = a.getAttribute('href') || '';
      a.classList.toggle('is-active', href === '#' + best);
    });
  }

  var ticking = false;
  window.addEventListener(
    'scroll',
    function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        update();
        ticking = false;
      });
    },
    { passive: true }
  );
  window.addEventListener('resize', update, { passive: true });
  update();
})();

/* Deep link: scroll to section on load / hash change */
function scrollToSectionFromHash() {
  var raw = (location.hash || '').replace(/^#/, '');
  if (!raw) return;
  var el = document.getElementById(raw);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

window.addEventListener('hashchange', scrollToSectionFromHash);
window.addEventListener('load', function () {
  setTimeout(scrollToSectionFromHash, 80);
  flushRevealsInViewport();
});

/* PDF modal: Escape to close */
(function pdfModalEscape() {
  var modal = document.getElementById('pdf-modal');
  if (!modal) return;
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (modal.getAttribute('aria-hidden') !== 'false') return;
    modal.setAttribute('aria-hidden', 'true');
    modal.style.display = 'none';
    document.body.style.overflow = '';
    var frame = modal.querySelector('#pdf-modal-object');
    if (frame) try {
      frame.src = '';
    } catch (err) {}
  });
})();
