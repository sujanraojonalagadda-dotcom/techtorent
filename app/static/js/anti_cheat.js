(function () {
  const sendViolation = (type) => {
    const body = new URLSearchParams();
    body.set('violation_type', type);
    fetch('/log_violation', { method: 'POST', body, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
  };

  document.addEventListener('copy', (e) => { e.preventDefault(); sendViolation('copy_attempt'); });
  document.addEventListener('paste', (e) => { e.preventDefault(); sendViolation('paste_attempt'); });
  document.addEventListener('contextmenu', (e) => e.preventDefault());
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) sendViolation('tab_switch');
  });

  let devtoolsOpen = false;
  setInterval(() => {
    const threshold = 160;
    const opened = (window.outerWidth - window.innerWidth > threshold) || (window.outerHeight - window.innerHeight > threshold);
    if (opened && !devtoolsOpen) {
      devtoolsOpen = true;
      sendViolation('devtools_open');
    }
    if (!opened) devtoolsOpen = false;
  }, 1000);
})();
