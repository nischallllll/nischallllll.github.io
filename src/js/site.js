(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');

  const updateThemeLabel = () => {
    if (!toggle) return;
    const isDark = root.dataset.theme === 'dark';
    toggle.setAttribute('aria-label', isDark ? 'Use light theme' : 'Use dark theme');
  };

  toggle?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('theme', root.dataset.theme); } catch (error) {}
    updateThemeLabel();
  });
  updateThemeLabel();

  const year = document.querySelector('[data-year]');
  if (year) year.textContent = new Date().getFullYear();

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.reveal').forEach((element) => element.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));
})();
