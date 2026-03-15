/* =====================================================
   MRABILITY Finance – app.js
   Navbar, Hero animations, Calculators, Carousel, FAQ
   ===================================================== */

document.addEventListener('DOMContentLoaded', () => {

  /* ---- Navbar scroll effect ---- */
  const navbar = document.getElementById('navbar');
  const backToTop = document.getElementById('backToTop');

  window.addEventListener('scroll', () => {
    if (window.scrollY > 60) {
      navbar && navbar.classList.add('scrolled');
      backToTop && backToTop.classList.add('visible');
    } else {
      navbar && navbar.classList.remove('scrolled');
      backToTop && backToTop.classList.remove('visible');
    }
  }, { passive: true });

  backToTop && backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  /* ---- Mobile hamburger ---- */
  const hamburger = document.getElementById('hamburger');
  const navLinks  = document.getElementById('navLinks');

  let navOverlay = null;
  function closeNav() {
    navLinks.classList.remove('open');
    hamburger.querySelectorAll('span').forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    if (navOverlay) { navOverlay.remove(); navOverlay = null; }
  }
  function openNav() {
    navLinks.classList.add('open');
    const spans = hamburger.querySelectorAll('span');
    spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
    spans[1].style.opacity   = '0';
    spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
    if (!navOverlay) {
      navOverlay = document.createElement('div');
      navOverlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.3);z-index:1098;';
      navOverlay.addEventListener('click', closeNav);
      document.body.appendChild(navOverlay);
    }
  }
  hamburger && hamburger.addEventListener('click', () => {
    navLinks.classList.contains('open') ? closeNav() : openNav();
  });

  // Close nav when clicking a link on mobile
  navLinks && navLinks.querySelectorAll('a.nav-link, .dropdown-menu a').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) closeNav();
    });
  });

  // Mobile: toggle dropdown on tap instead of hover
  document.querySelectorAll('.nav-dropdown .nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (window.innerWidth <= 768) {
        e.stopPropagation();
        const menu = btn.nextElementSibling;
        const isOpen = menu.style.display === 'block';
        document.querySelectorAll('.nav-dropdown .dropdown-menu').forEach(m => { m.style.display = ''; });
        menu.style.display = isOpen ? '' : 'block';
      }
    });
  });

  /* ---- Hero rotating text ---- */
  const heroRotate = document.getElementById('heroRotate');
  const rotateWords = ['Home Loans', 'Personal Loans', 'Business Loans', 'Credit Cards', 'Car Loans'];
  let wordIdx = 0;

  if (heroRotate) {
    setInterval(() => {
      heroRotate.style.opacity = '0';
      heroRotate.style.transform = 'translateY(-10px)';
      setTimeout(() => {
        wordIdx = (wordIdx + 1) % rotateWords.length;
        heroRotate.textContent = rotateWords[wordIdx];
        heroRotate.style.opacity = '1';
        heroRotate.style.transform = 'translateY(0)';
      }, 300);
    }, 2500);

    heroRotate.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  }

  /* ---- Counter animation ---- */
  const counters = document.querySelectorAll('.counter');

  const animateCounter = (el) => {
    const target = parseInt(el.dataset.target, 10);
    if (isNaN(target)) return;
    const suffix = el.dataset.suffix || '';
    const duration = 2000;
    const start = performance.now();
    const update = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString('en-IN') + suffix;
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  };

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          animateCounter(e.target);
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(c => observer.observe(c));
  } else {
    counters.forEach(animateCounter);
  }

  /* ---- Fetch live rates from admin panel ---- */
  const heroStats = document.querySelector('.page-hero-stats[data-loan-type]');
  if (heroStats) {
    const loanType = heroStats.dataset.loanType;
    fetch('/api/rates/summary')
      .then(r => r.json())
      .then(data => {
        const info = data[loanType];
        if (!info) return;
        heroStats.querySelectorAll('[data-rate-field]').forEach(el => {
          const field = el.dataset.rateField;
          if (field === 'starting_rate' && info.starting_rate != null) {
            el.textContent = info.starting_rate + '% p.a.';
          } else if (field === 'max_amount' && info.max_amount) {
            el.textContent = info.max_amount;
          } else if (field === 'max_tenure' && info.max_tenure != null) {
            el.textContent = info.max_tenure + ' yrs';
          }
        });
      })
      .catch(() => {});
  }

  /* ---- Range slider dynamic fill ---- */
  const updateSliderFill = (slider) => {
    const min = +slider.min, max = +slider.max, val = +slider.value;
    const pct = ((val - min) / (max - min)) * 100;
    slider.style.setProperty('--val', `${pct}%`);
    slider.style.background = `linear-gradient(90deg, #4f46e5 ${pct}%, #e2e8f0 ${pct}%)`;
  };

  document.querySelectorAll('input[type="range"]').forEach(slider => {
    updateSliderFill(slider);
    slider.addEventListener('input', () => updateSliderFill(slider));
  });

  /* ---- Calculator tabs ---- */
  const calcTabs  = document.querySelectorAll('.calc-tab');
  const calcPanels = document.querySelectorAll('.calc-panel');

  calcTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      calcTabs.forEach(t => t.classList.remove('active'));
      calcPanels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const target = document.getElementById(`calc-${tab.dataset.calc}`);
      target && target.classList.add('active');
    });
  });

  /* ---- Canvas Donut helper ---- */
  const drawDonut = (canvasId, principal, interest, colors = ['#4f46e5', '#06b6d4']) => {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2, cy = canvas.height / 2, r = 80;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const total = principal + interest;
    if (total === 0) {
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 18; ctx.stroke();
      return;
    }

    const startAngle = -Math.PI / 2;
    const slices = [
      { value: principal, color: colors[0] },
      { value: interest,  color: colors[1] },
    ];
    let currentAngle = startAngle;

    slices.forEach(slice => {
      if (slice.value <= 0) return;
      const sliceAngle = (slice.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, currentAngle, currentAngle + sliceAngle);
      ctx.strokeStyle = slice.color;
      ctx.lineWidth = 18;
      ctx.lineCap = 'butt';
      ctx.stroke();
      currentAngle += sliceAngle;
    });
  };

  const fmt = (n) => '₹' + Math.round(n).toLocaleString('en-IN');

  /* ---- Load calculator defaults from API, then wire all calculators ---- */
  const API_BASE = '/api';

  async function loadCalcDefaults() {
    try {
      const res  = await fetch(`${API_BASE}/rates/calculators`);
      const data = await res.json();
      // Apply defaults to sliders if present on this page
      const apply = (id, key) => {
        const el = document.getElementById(id);
        if (el && data[key]) el.value = data[key].value;
      };
      apply('emiRate',  'emi_rate');
      apply('fdRate',   'fd_rate');
      apply('sipRate',  'sip_rate');
      apply('ppfRate',  'ppf_rate');
      // Store eligibility rate for formula use
      if (data['eligibility_rate']) window._eligibilityRate = data['eligibility_rate'].value;
    } catch { /* server not running — use hardcoded defaults */ }
    // Run all calculators after defaults are applied
    calcEMI(); calcEligibility();
    if (document.getElementById('sipAmount')) calcSIP();
    if (document.getElementById('fdAmount'))  calcFD();
    if (document.getElementById('ppfAmount')) calcPPF();
  }

  /* ---- EMI Calculator ---- */
  const calcEMI = () => {
    const P = +document.getElementById('emiAmount').value;
    const rAnnual = +document.getElementById('emiRate').value;
    const years = +document.getElementById('emiTenure').value;
    const r = rAnnual / 12 / 100;
    const n = years * 12;

    document.getElementById('emiAmountVal').textContent  = fmt(P);
    document.getElementById('emiRateVal').textContent    = `${rAnnual}%`;
    document.getElementById('emiTenureVal').textContent  = `${years} yr${years > 1 ? 's' : ''}`;

    const emi   = P * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
    const total = emi * n;
    const interest = total - P;

    document.getElementById('emiResult').textContent    = fmt(emi);
    document.getElementById('emiPrincipal').textContent = fmt(P);
    document.getElementById('emiInterest').textContent  = fmt(interest);
    document.getElementById('emiTotal').textContent     = fmt(total);

    drawDonut('emiDonut', P, interest);
  };

  ['emiAmount', 'emiRate', 'emiTenure'].forEach(id => {
    const el = document.getElementById(id);
    el && el.addEventListener('input', calcEMI);
  });

  /* ---- Eligibility Calculator ---- */
  const calcEligibility = () => {
    const income     = +document.getElementById('elIncome').value;
    const obligation = +document.getElementById('elObligation').value;
    const years      = +document.getElementById('elTenure').value;

    document.getElementById('elIncomeVal').textContent     = fmt(income);
    document.getElementById('elObligationVal').textContent = fmt(obligation);
    document.getElementById('elTenureVal').textContent     = `${years} yr${years > 1 ? 's' : ''}`;

    const r = (window._eligibilityRate || 10.99) / 12 / 100;
    const n = years * 12;
    const foir = 0.5;
    const availableEmi  = income * foir - obligation;
    const eligible = availableEmi > 0
      ? availableEmi * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n))
      : 0;

    document.getElementById('elResult').textContent = fmt(Math.max(eligible, 0));
  };

  ['elIncome', 'elObligation', 'elTenure'].forEach(id => {
    const el = document.getElementById(id);
    el && el.addEventListener('input', calcEligibility);
  });

  /* ---- SIP Calculator ---- */
  const calcSIP = () => {
    const monthly = +document.getElementById('sipAmount').value;
    const rate    = +document.getElementById('sipRate').value;
    const years   = +document.getElementById('sipTenure').value;

    document.getElementById('sipAmountVal').textContent  = fmt(monthly);
    document.getElementById('sipRateVal').textContent    = `${rate}%`;
    document.getElementById('sipTenureVal').textContent  = `${years} yr${years > 1 ? 's' : ''}`;

    const r = rate / 12 / 100;
    const n = years * 12;
    const fv = monthly * ((Math.pow(1 + r, n) - 1) / r) * (1 + r);
    const invested = monthly * n;
    const returns  = fv - invested;

    document.getElementById('sipResult').textContent   = fmt(fv);
    document.getElementById('sipInvested').textContent = fmt(invested);
    document.getElementById('sipReturns').textContent  = fmt(returns);

    drawDonut('sipDonut', invested, Math.max(returns, 0), ['#4f46e5', '#10b981']);
  };

  ['sipAmount', 'sipRate', 'sipTenure'].forEach(id => {
    const el = document.getElementById(id);
    el && el.addEventListener('input', calcSIP);
  });

  /* ---- FD Calculator ---- */
  const calcFD = () => {
    const P     = +document.getElementById('fdAmount').value;
    const rate  = +document.getElementById('fdRate').value;
    const years = +document.getElementById('fdTenure').value;

    document.getElementById('fdAmountVal').textContent = fmt(P);
    document.getElementById('fdRateVal').textContent   = `${rate}%`;
    document.getElementById('fdTenureVal').textContent = `${years} yr${years > 1 ? 's' : ''}`;

    const fv = P * Math.pow(1 + rate / 400, 4 * years); // quarterly compounding
    const interest = fv - P;

    document.getElementById('fdResult').textContent   = fmt(fv);
    document.getElementById('fdPrincipal').textContent = fmt(P);
    document.getElementById('fdInterest').textContent  = fmt(interest);

    drawDonut('fdDonut', P, interest, ['#4f46e5', '#f59e0b']);
  };

  ['fdAmount', 'fdRate', 'fdTenure'].forEach(id => {
    const el = document.getElementById(id);
    el && el.addEventListener('input', calcFD);
  });

  // Load defaults from DB then run all calcs
  loadCalcDefaults();

  /* ---- Credit Cards Carousel ---- */
  const carousel     = document.getElementById('cardsCarousel');
  const dotsContainer = document.getElementById('carouselDots');
  const prevBtn       = document.getElementById('prevCard');
  const nextBtn       = document.getElementById('nextCard');

  if (carousel) {
    const items = carousel.querySelectorAll('.credit-card-item');
    let current = 0;

    const dots = Array.from({ length: items.length }, (_, i) => {
      const dot = document.createElement('div');
      dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
      dot.addEventListener('click', () => goTo(i));
      dotsContainer && dotsContainer.appendChild(dot);
      return dot;
    });

    const goTo = (idx) => {
      current = (idx + items.length) % items.length;
      track.style.transform = `translateX(-${current * 100}%)`;
      track.style.transition = 'transform 0.4s cubic-bezier(0.4,0,0.2,1)';
      dots.forEach((d, i) => d.classList.toggle('active', i === current));
    };

    // Wrap all carousel items in a sliding track inside an overflow-hidden viewport
    const viewport = document.createElement('div');
    viewport.style.cssText = 'overflow:hidden;width:100%;';
    const track = document.createElement('div');
    track.style.cssText = 'display:flex;width:100%;';
    // Move all items into the track
    while (carousel.firstChild) track.appendChild(carousel.firstChild);
    viewport.appendChild(track);
    carousel.appendChild(viewport);
    // Make items non-shrinkable and full-width
    items.forEach(item => {
      item.style.minWidth = '100%';
      item.style.flexShrink = '0';
    });

    prevBtn && prevBtn.addEventListener('click', () => goTo(current - 1));
    nextBtn && nextBtn.addEventListener('click', () => goTo(current + 1));

    // Auto-advance
    let autoInterval = setInterval(() => goTo(current + 1), 5000);
    carousel.addEventListener('mouseenter', () => clearInterval(autoInterval));
    carousel.addEventListener('mouseleave', () => {
      autoInterval = setInterval(() => goTo(current + 1), 5000);
    });

    // Touch support
    let touchStartX = 0;
    carousel.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
    carousel.addEventListener('touchend', e => {
      const diff = touchStartX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 50) goTo(diff > 0 ? current + 1 : current - 1);
    }, { passive: true });
  }

  /* ---- FAQ accordion ---- */
  window.toggleFaq = (btn) => {
    const item = btn.closest('.faq-item');
    const answer = item.querySelector('.faq-a');
    const isOpen = item.classList.contains('open');

    // close all
    document.querySelectorAll('.faq-item.open').forEach(openItem => {
      openItem.classList.remove('open');
      openItem.querySelector('.faq-a').style.display = 'none';
    });

    if (!isOpen) {
      item.classList.add('open');
      answer.style.display = 'block';
    }
  };

  /* ---- Smooth scroll for anchor links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ---- Scroll reveal animation ---- */
  if ('IntersectionObserver' in window) {
    const revealStyle = document.createElement('style');
    revealStyle.textContent = `
      .reveal { opacity: 0; transform: translateY(30px); transition: opacity 0.6s ease, transform 0.6s ease; }
      .reveal.visible { opacity: 1; transform: translateY(0); }
      .reveal-delay-1 { transition-delay: 0.1s; }
      .reveal-delay-2 { transition-delay: 0.2s; }
      .reveal-delay-3 { transition-delay: 0.3s; }
    `;
    document.head.appendChild(revealStyle);

    const revealTargets = [
      ...document.querySelectorAll('.product-card'),
      ...document.querySelectorAll('.step-card'),
      ...document.querySelectorAll('.testimonial-card'),
      ...document.querySelectorAll('.stat-item'),
    ];

    revealTargets.forEach((el, i) => {
      el.classList.add('reveal');
      if (i % 4 === 1) el.classList.add('reveal-delay-1');
      if (i % 4 === 2) el.classList.add('reveal-delay-2');
      if (i % 4 === 3) el.classList.add('reveal-delay-3');
    });

    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          revealObserver.unobserve(e.target);
        }
      });
    }, { threshold: 0.15 });

    revealTargets.forEach(el => revealObserver.observe(el));
  }

  /* ---- Active nav link highlighting ---- */
  const sections = document.querySelectorAll('section[id]');
  const navLinksAll = document.querySelectorAll('.nav-link, .nav-btn');

  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(s => {
      if (window.scrollY >= s.offsetTop - 120) current = s.id;
    });
    navLinksAll.forEach(l => {
      l.classList.remove('active-nav');
      if (l.getAttribute('href') === `#${current}`) l.classList.add('active-nav');
    });
  }, { passive: true });

});

/* =====================================================
   LOGIN / REGISTER MODAL — Global Functions
   ===================================================== */

/* ---- API + Session Store ---- */
const API = '/api';

const FinNova = {
  // ── Session (JWT stored in localStorage) ──────────
  setSession: (token, name, role, id) => {
    localStorage.setItem('fn_token',   token);
    localStorage.setItem('fn_session', JSON.stringify({ name, role, id, loggedIn: true, at: new Date().toISOString() }));
  },
  getSession: () => {
    try { return JSON.parse(localStorage.getItem('fn_session') || 'null'); } catch { return null; }
  },
  getToken: () => localStorage.getItem('fn_token') || null,
  clearSession: () => {
    localStorage.removeItem('fn_token');
    localStorage.removeItem('fn_session');
  },
  isAdmin: () => {
    const s = FinNova.getSession();
    return s && s.role === 'admin';
  },

  // ── Auth headers ──────────────────────────────────
  authHeaders: () => {
    const token = FinNova.getToken();
    return token
      ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
      : { 'Content-Type': 'application/json' };
  },

  // ── Register ──────────────────────────────────────
  register: async (name, mobile, email, password) => {
    const res  = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, mobile, email, password })
    });
    return res.json().then(data => ({ ok: res.ok, ...data }));
  },

  // ── Login ─────────────────────────────────────────
  login: async (identifier, password) => {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password })
    });
    return res.json().then(data => ({ ok: res.ok, ...data }));
  },

  // ── Submit loan application ───────────────────────
  saveApplication: async (loanType, formData) => {
    try {
      const res = await fetch(`${API}/applications`, {
        method: 'POST',
        headers: FinNova.authHeaders(),
        body: JSON.stringify({ loan_type: loanType, ...formData })
      });
      const data = await res.json();
      return data.ref_id || ('APP' + Date.now());
    } catch {
      // Fallback to localStorage if server down
      const apps = JSON.parse(localStorage.getItem('fn_applications') || '[]');
      const id   = 'FN-LOCAL-' + Date.now();
      apps.push({ loan_type: loanType, ...formData, status: 'Submitted', created_at: new Date().toISOString(), ref_id: id });
      localStorage.setItem('fn_applications', JSON.stringify(apps));
      return id;
    }
  },

  // ── Save credit score ─────────────────────────────
  saveCreditScore: async (data) => {
    try {
      await fetch(`${API}/credit-score`, {
        method: 'POST',
        headers: FinNova.authHeaders(),
        body: JSON.stringify(data)
      });
    } catch { /* silent */ }
    showToast(`Credit score saved: ${data.score} (${data.tier})`, 'success');
  },
};

// Restore session on page load
let _lastSyncedUser = null;

function syncSessionUI(fromCache) {
  const session = FinNova.getSession();
  const navActions = document.querySelector('.nav-actions');
  const currentUser = session && session.loggedIn ? session.name + '|' + (session.id || '') : null;

  if (navActions) {
    navActions.querySelectorAll('.user-pill').forEach(el => el.remove());
  }

  if (session && session.loggedIn) {
    updateNavForLoggedIn(session.name, session.role);
    if (document.querySelector('.apply-form-card')) {
      if (fromCache && _lastSyncedUser !== currentUser) {
        _resetLoanForms();
      }
      autoFillLoanForm();
    }
    _lastSyncedUser = currentUser;
  } else {
    if (document.querySelector('.apply-form-card') && fromCache) {
      _resetLoanForms();
    }
    _lastSyncedUser = null;
    if (navActions) {
      const hasLoginBtn = navActions.querySelector('.btn-ghost, button[onclick*="openLoginModal"]');
      if (!hasLoginBtn) {
        window.location.reload();
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => syncSessionUI(false));

// Re-sync when page is restored from back-forward cache
window.addEventListener('pageshow', (e) => {
  if (e.persisted) {
    syncSessionUI(true);
  }
});

// ---- Open / Close ----
window.openLoginModal = (tab = 'login') => {
  const modal = document.getElementById('loginModal');
  if (!modal) {
    // On sub-pages the modal doesn't exist — redirect to index with hash
    window.location.href = `index.html#openLogin=${tab}`;
    return;
  }
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  switchModalTab(tab);
};

window.closeModal = () => {
  const modal = document.getElementById('loginModal');
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
};

// Close on overlay click
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('loginModal');
  const closeBtn = document.getElementById('modalClose');

  closeBtn && closeBtn.addEventListener('click', closeModal);

  modal && modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // Handle redirect from sub-pages with hash
  const hash = window.location.hash;
  if (hash.startsWith('#openLogin=')) {
    const tab = hash.replace('#openLogin=', '') || 'login';
    setTimeout(() => openLoginModal(tab), 300);
    history.replaceState(null, '', window.location.pathname);
  }
});

// ---- Tab Switching ----
window.switchModalTab = (tab) => {
  // Update tab buttons
  document.querySelectorAll('.modal-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.modalTab === tab);
  });
  // Show correct panel
  document.querySelectorAll('.modal-panel').forEach(p => {
    p.classList.toggle('active', p.id === `modal-${tab}`);
  });
  // Show/hide the top tab bar (hide for forgot/otp/newpass/success)
  const tabBar = document.querySelector('.modal-tabs');
  if (tabBar) {
    tabBar.style.display = ['forgot', 'otp', 'newpass', 'success'].includes(tab) ? 'none' : '';
  }
};

// Tab button click handlers
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.addEventListener('click', () => switchModalTab(tab.dataset.modalTab));
  });
});

// ---- Show Forgot Password ----
window.showForgot = () => switchModalTab('forgot');

// ---- Password Visibility Toggle ----
window.togglePassword = (inputId, btn) => {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  btn.textContent = isText ? '👁' : '🙈';
};

// ---- Password Strength ----
document.addEventListener('DOMContentLoaded', () => {
  const passInput = document.getElementById('regPass');
  const passFill  = document.getElementById('passFill');
  const passLabel = document.getElementById('passLabel');
  if (!passInput) return;

  passInput.addEventListener('input', () => {
    const val = passInput.value;
    let score = 0;
    if (val.length >= 8)  score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    const levels = [
      { pct: '0%',   color: '',           label: 'Strength' },
      { pct: '25%',  color: '#ef4444',    label: 'Weak' },
      { pct: '50%',  color: '#f59e0b',    label: 'Fair' },
      { pct: '75%',  color: '#84cc16',    label: 'Good' },
      { pct: '100%', color: '#10b981',    label: 'Strong' },
    ];
    const lv = levels[score] || levels[0];
    if (passFill)  { passFill.style.width = lv.pct; passFill.style.background = lv.color; }
    if (passLabel) { passLabel.textContent = lv.label; passLabel.style.color = lv.color || 'var(--text-light)'; }
  });
});

// ---- Form Validation Helpers ----
const setErr = (id, msg) => {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
};
const clearErrs = (...ids) => ids.forEach(id => setErr(id, ''));

const markInput = (id, valid) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle('error', !valid);
  el.classList.toggle('success', valid);
};

// ---- Mobile Number Validation ----
function sanitizeMobile(raw) {
  return raw.replace(/\D/g, '').replace(/^91/, '').slice(0, 10);
}

function isValidIndianMobile(num) {
  return /^[6-9]\d{9}$/.test(num);
}

function setupMobileInputs() {
  document.querySelectorAll('input[type="tel"]').forEach(inp => {
    inp.setAttribute('inputmode', 'numeric');
    inp.setAttribute('pattern', '[0-9]*');
    inp.setAttribute('maxlength', '10');
    inp.placeholder = 'Enter 10-digit mobile number';

    inp.addEventListener('input', function() {
      this.value = this.value.replace(/\D/g, '').slice(0, 10);
    });

    inp.addEventListener('blur', function() {
      const v = this.value.trim();
      if (v && !isValidIndianMobile(v)) {
        this.classList.add('error');
        this.classList.remove('success');
        const errSpan = this.parentElement.querySelector('.field-err');
        if (errSpan) errSpan.textContent = 'Enter a valid 10-digit mobile number starting with 6-9';
      } else if (v) {
        this.classList.remove('error');
        this.classList.add('success');
        const errSpan = this.parentElement.querySelector('.field-err');
        if (errSpan) errSpan.textContent = '';
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', setupMobileInputs);

// ---- Login Handler ----
window.handleLogin = (e) => {
  e.preventDefault();
  clearErrs('loginIdErr', 'loginPassErr');

  const userId = document.getElementById('loginId')?.value.trim() || '';
  const pass   = document.getElementById('loginPass')?.value || '';
  let valid = true;

  if (!userId) {
    setErr('loginIdErr', 'Please enter your mobile number or email.');
    markInput('loginId', false); valid = false;
  } else {
    markInput('loginId', true);
  }

  if (pass.length < 6) {
    setErr('loginPassErr', 'Password must be at least 6 characters.');
    markInput('loginPass', false); valid = false;
  } else {
    markInput('loginPass', true);
  }

  if (!valid) return;

  // Call real API
  const btn = document.getElementById('loginBtn');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; btn.textContent = 'Logging in...'; }

  FinNova.login(userId, pass).then(data => {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; btn.textContent = 'Login'; }
    if (!data.ok) {
      setErr('loginPassErr', data.error || 'Invalid credentials');
      markInput('loginPass', false);
      return;
    }
    FinNova.setSession(data.token, data.name, data.role, data.id);
    document.getElementById('successTitle').textContent = `Welcome back, ${data.name}! 👋`;
    document.getElementById('successMsg').textContent = 'You are now logged in to your MRABILITY Finance dashboard.';
    switchModalTab('success');
    updateNavForLoggedIn(data.name, data.role);
    _submitPendingApp();
    _resetLoanForms();
    setTimeout(autoFillLoanForm, 300);
  }).catch(() => {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; btn.textContent = 'Login'; }
    setErr('loginPassErr', 'Server error. Please try again.');
  });
};

// ---- Register Handler ----
window.handleRegister = (e) => {
  e.preventDefault();
  clearErrs('regNameErr', 'regMobileErr', 'regEmailErr', 'regPassErr');

  const name    = document.getElementById('regName')?.value.trim() || '';
  const mobile  = sanitizeMobile(document.getElementById('regMobile')?.value || '');
  const email   = document.getElementById('regEmail')?.value.trim() || '';
  const pass    = document.getElementById('regPass')?.value || '';
  const consent = document.getElementById('regConsent')?.checked;
  let valid = true;

  if (!name || name.length < 3) {
    setErr('regNameErr', 'Please enter your full name (min 3 chars).');
    markInput('regName', false); valid = false;
  } else { markInput('regName', true); }

  if (!isValidIndianMobile(mobile)) {
    setErr('regMobileErr', 'Enter a valid 10-digit Indian mobile number starting with 6-9.');
    markInput('regMobile', false); valid = false;
  } else { markInput('regMobile', true); }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    setErr('regEmailErr', 'Enter a valid email address.');
    markInput('regEmail', false); valid = false;
  } else { markInput('regEmail', true); }

  if (pass.length < 8) {
    setErr('regPassErr', 'Password must be at least 8 characters.');
    markInput('regPass', false); valid = false;
  } else { markInput('regPass', true); }

  if (!valid) return;

  const btn = document.getElementById('registerBtn');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; btn.textContent = 'Creating account...'; }

  FinNova.register(name, mobile, email, pass).then(data => {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; btn.textContent = 'Create My Account'; }
    if (!data.ok) {
      const msg = data.error || 'Registration failed';
      if (msg.toLowerCase().includes('email')) { setErr('regEmailErr', msg); markInput('regEmail', false); }
      else { setErr('regPassErr', msg); }
      return;
    }
    FinNova.setSession(data.token, data.name, data.role, data.id);
    document.getElementById('successTitle').textContent = `Welcome, ${data.name.split(' ')[0]}! 🎉`;
    document.getElementById('successMsg').textContent = 'Your account has been created. Start exploring the best loan offers!';
    switchModalTab('success');
    updateNavForLoggedIn(data.name.split(' ')[0], data.role);
    _submitPendingApp();
    _resetLoanForms();
    setTimeout(autoFillLoanForm, 300);
  }).catch(() => {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; btn.textContent = 'Create My Account'; }
    setErr('regPassErr', 'Server error. Please try again.');
  });
};

// ---- Forgot Password — 3-Step Real Flow ----
// Step 1: Send OTP
window.handleForgot = async (e) => {
  e.preventDefault();
  const id = (document.getElementById('forgotId')?.value || '').trim();
  if (!id) return;
  const btn = e.target.querySelector('button[type="submit"]');
  const errEl = document.getElementById('forgotErr');
  if (errEl) errEl.textContent = '';
  if (btn) { btn.textContent = 'Sending OTP…'; btn.disabled = true; }
  try {
    const res  = await fetch(`${API}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: id })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to send OTP');
    // Store identifier for next steps
    window._resetIdentifier = id;
    // Show OTP entry panel
    const sentMsg = document.getElementById('otpSentMsg');
    if (sentMsg) sentMsg.textContent = data.sent_to
      ? `OTP sent to ${data.sent_to}`
      : data.dev_mode
        ? 'DEV MODE: Check server console for OTP'
        : 'OTP sent successfully';
    switchModalTab('otp');
  } catch (err) {
    if (errEl) errEl.textContent = err.message;
    else alert(err.message);
  } finally {
    if (btn) { btn.textContent = 'Send OTP'; btn.disabled = false; }
  }
};

// Step 2: Verify OTP
window.handleVerifyOtp = async (e) => {
  e.preventDefault();
  const otp   = (document.getElementById('otpInput')?.value || '').trim();
  const errEl = document.getElementById('otpErr');
  if (errEl) errEl.textContent = '';
  if (!otp || !window._resetIdentifier) return;
  const btn = e.target.querySelector('button[type="submit"]');
  if (btn) { btn.textContent = 'Verifying…'; btn.disabled = true; }
  try {
    const res  = await fetch(`${API}/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: window._resetIdentifier, otp })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Invalid OTP');
    window._resetToken = data.reset_token;
    switchModalTab('newpass');
  } catch (err) {
    if (errEl) errEl.textContent = err.message;
  } finally {
    if (btn) { btn.textContent = 'Verify OTP'; btn.disabled = false; }
  }
};

// Step 3: Set new password
window.handleResetPassword = async (e) => {
  e.preventDefault();
  const pass  = (document.getElementById('newPassInput')?.value || '').trim();
  const pass2 = (document.getElementById('newPassConfirm')?.value || '').trim();
  const errEl = document.getElementById('newPassErr');
  if (errEl) errEl.textContent = '';
  if (pass !== pass2) {
    if (errEl) errEl.textContent = 'Passwords do not match';
    return;
  }
  if (pass.length < 8) {
    if (errEl) errEl.textContent = 'Password must be at least 8 characters';
    return;
  }
  const btn = e.target.querySelector('button[type="submit"]');
  if (btn) { btn.textContent = 'Resetting…'; btn.disabled = true; }
  try {
    const res  = await fetch(`${API}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        identifier:  window._resetIdentifier,
        reset_token: window._resetToken,
        password:    pass
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Reset failed');
    // Clean up temp vars
    delete window._resetIdentifier;
    delete window._resetToken;
    // Show success — go to login tab
    document.getElementById('successTitle').textContent = 'Password Reset!';
    document.getElementById('successMsg').textContent   = 'Your password has been reset successfully. Please log in with your new password.';
    document.getElementById('successAction').textContent = 'Go to Login';
    document.getElementById('successAction').onclick    = () => switchModalTab('login');
    switchModalTab('success');
  } catch (err) {
    if (errEl) errEl.textContent = err.message;
  } finally {
    if (btn) { btn.textContent = 'Reset Password'; btn.disabled = false; }
  }
};

// ---- Social Login ----
// Google is handled by the GIS SDK rendered button (in index.html inline script).
// This handles Facebook + fallback for any old onclick="socialLogin('Google')" calls.
window.socialLogin = async (provider) => {
  if (provider === 'Google') {
    // If GIS SDK loaded and client ID configured, trigger popup
    if (typeof google !== 'undefined' && google.accounts && window._gClientId) {
      google.accounts.id.prompt();
    } else if (typeof showGoogleConfigModal === 'function') {
      showGoogleConfigModal();
    } else {
      showOAuthSetupModal('Google');
    }
    return;
  }

  if (provider === 'Facebook') {
    const btn = document.querySelector('.fb-btn') || document.querySelector(`.social-btn[onclick*="Facebook"]`);
    if (btn) { btn.disabled = true; btn.style.opacity = '.6'; }
    const restore = () => { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } };
    try {
      const res  = await fetch(`${API}/auth/facebook/check`);
      const data = await res.json();
      if (data.configured) { window.location.href = `${API}/auth/facebook`; return; }
      restore(); showOAuthSetupModal('Facebook');
    } catch { restore(); showOAuthSetupModal('Facebook', true); }
  }
};

// Fallback panel shown inside modal when OAuth is not set up
function showOAuthSetupModal(provider, serverDown = false) {
  const modal = document.getElementById('loginModal') || document.getElementById('modalOverlay');
  if (!modal) return;
  document.getElementById('oauthSetupPanel')?.remove();

  const panel = document.createElement('div');
  panel.id = 'oauthSetupPanel';
  panel.style.cssText = 'position:absolute;inset:0;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem;text-align:center;z-index:10;border-radius:20px;overflow-y:auto';

  const gIcon = `<svg width="40" height="40" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.1 0 5.8 1.1 8 2.8l6-6C34.4 3.2 29.5 1 24 1 14.8 1 7 6.7 3.8 14.7l7 5.5C12.5 13.6 17.8 9.5 24 9.5z"/><path fill="#34A853" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.4c-.5 2.8-2.2 5.2-4.6 6.8l7 5.5c4.1-3.8 6.3-9.4 6.3-16.3z"/><path fill="#4A90D9" d="M10.8 28.3A14.8 14.8 0 0 1 9.5 24c0-1.5.3-2.9.7-4.3l-7-5.5A23.9 23.9 0 0 0 0 24c0 3.9.9 7.5 2.6 10.7l8.2-6.4z"/><path fill="#FBBC05" d="M24 47c5.5 0 10.1-1.8 13.5-4.9l-7-5.5c-1.9 1.3-4.3 2-6.5 2-6.2 0-11.5-4.1-13.2-9.8l-8.2 6.4C7 41.3 14.8 47 24 47z"/></svg>`;
  const fbIcon = `<svg width="40" height="40" viewBox="0 0 24 24" fill="#1877F2"><path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97h-1.514c-1.491 0-1.956.93-1.956 1.886v2.268h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>`;

  panel.innerHTML = `
    <div style="margin-bottom:1.25rem">${provider === 'Google' ? gIcon : fbIcon}</div>
    <h3 style="font-size:1.05rem;font-weight:800;margin-bottom:.5rem;color:#0f172a">
      ${serverDown ? 'Server not reachable' : `${provider} Login — Setup Required`}
    </h3>
    <p style="font-size:.82rem;color:#64748b;margin-bottom:1.25rem;line-height:1.65;max-width:300px">
      ${serverDown ? 'Cannot reach backend. Make sure the server is running with <code style="background:#f1f5f9;padding:.1rem .35rem;border-radius:4px">./start.sh</code>' : `${provider} login requires OAuth credentials in the server.`}
    </p>
    ${!serverDown && provider === 'Facebook' ? `
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:.875rem 1rem;font-size:.77rem;text-align:left;margin-bottom:1.25rem;width:100%;line-height:1.8">
      1. Visit <strong>developers.facebook.com</strong> → Create App<br/>
      2. Add Facebook Login, set redirect URI:<br/>
      <code style="background:#e2e8f0;padding:.1rem .35rem;border-radius:4px;font-size:.72rem">${window.location.origin}/api/auth/facebook/callback</code><br/>
      3. Restart: <code style="background:#e2e8f0;padding:.1rem .35rem;border-radius:4px;font-size:.72rem">FACEBOOK_APP_ID=x FACEBOOK_APP_SECRET=y ./start.sh</code>
    </div>` : ''}
    <div style="display:flex;flex-direction:column;gap:.5rem;width:100%">
      <button onclick="document.getElementById('oauthSetupPanel').remove();switchModalTab('login');"
        style="background:linear-gradient(135deg,#4f46e5,#3730a3);color:#fff;padding:.8rem;border-radius:50px;font-weight:700;cursor:pointer;border:none;font-size:.875rem;width:100%">
        ✉️ Use Email Login Instead
      </button>
      <button onclick="document.getElementById('oauthSetupPanel').remove();switchModalTab('register');"
        style="background:#f8fafc;color:#475569;padding:.7rem;border-radius:50px;font-weight:600;cursor:pointer;border:1.5px solid #e2e8f0;font-size:.85rem;width:100%">
        Register a New Account
      </button>
    </div>`;

  const box = modal.querySelector('.modal-box');
  if (box) { box.style.position = 'relative'; box.style.overflow = 'hidden'; box.appendChild(panel); }
}

// ── Handle OAuth callback (Google/Facebook redirect back with token) ──
(function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token  = params.get('oauth_token');
  const name   = params.get('oauth_name');
  const role   = params.get('oauth_role') || 'user';
  if (token && name) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      FinNova.setSession(token, decodeURIComponent(name), role, payload.sub);
      updateNavForLoggedIn(decodeURIComponent(name), role);
    } catch { /* ignore */ }
    window.history.replaceState({}, '', window.location.pathname);
    showToast(`Welcome, ${decodeURIComponent(name)}! Logged in successfully 🎉`, 'success');
  }
  const oauthError = params.get('oauth_error');
  if (oauthError) {
    showToast('Social login was cancelled or failed. Please try again.', 'error');
    window.history.replaceState({}, '', window.location.pathname);
  }
})();

// ---- Update Navbar after login ----
function updateNavForLoggedIn(name, role = 'user') {
  const navActions = document.querySelector('.nav-actions');
  if (!navActions) return;
  navActions.querySelectorAll('.btn-ghost, .btn-primary:not(.hamburger), button[onclick*="openLoginModal"], .user-pill')
    .forEach(el => el.remove());

  const pill = document.createElement('div');
  pill.className = 'user-pill';
  pill.style.cursor = 'pointer';

  let menuHtml = `<div class="user-avatar">${name.charAt(0).toUpperCase()}</div><span class="user-name">${name.split(' ')[0]}</span>`;
  pill.innerHTML = menuHtml;
  pill.title = `Logged in as ${name} (${role})`;

  // Dropdown menu on click
  pill.addEventListener('click', (e) => {
    e.stopPropagation();
    let menu = document.getElementById('userDropdown');
    if (menu) { menu.remove(); return; }
    menu = document.createElement('div');
    menu.id = 'userDropdown';
    menu.style.cssText = `
      position:absolute; top:calc(100% + 8px); right:0;
      background:#fff; border:1px solid var(--border);
      border-radius:var(--radius-md); box-shadow:var(--shadow-lg);
      min-width:180px; z-index:2000; padding:.5rem; font-size:.875rem;
    `;
    const items = [
      { label: '👤 My Profile', action: () => { window.location.href = 'profile.html'; } },
      { label: '📋 My Applications', action: () => { window.location.href = 'my-applications.html'; } },
    ];
    if (role === 'admin') {
      items.push({ label: '🛡️ Admin Dashboard', action: () => { window.location.href = 'admin.html'; } });
    }
    items.push({ label: '🚪 Logout', action: () => {
      FinNova.clearSession();
      window.location.href = 'index.html';
    }});
    items.forEach(item => {
      const el = document.createElement('div');
      el.textContent = item.label;
      el.style.cssText = 'padding:.6rem .875rem;border-radius:6px;cursor:pointer;transition:.2s';
      el.addEventListener('mouseenter', () => el.style.background = '#f5f3ff');
      el.addEventListener('mouseleave', () => el.style.background = '');
      el.addEventListener('click', () => { menu.remove(); item.action(); });
      menu.appendChild(el);
    });
    pill.style.position = 'relative';
    pill.appendChild(menu);
    document.addEventListener('click', () => menu.remove(), { once: true });
  });

  const hamburger = navActions.querySelector('.hamburger');
  navActions.insertBefore(pill, hamburger || null);
}

/* =====================================================
   Shared Form Submit Handler — saves to localStorage
   ===================================================== */
// Auto-submit a pending loan application that was saved before login
function _submitPendingApp() {
  const pending = localStorage.getItem('fn_pending_app');
  if (!pending) return;
  try {
    const { loanType, formData } = JSON.parse(pending);
    FinNova.saveApplication(loanType, formData).then(refId => {
      localStorage.removeItem('fn_pending_app');
      showToast(`Application submitted! Ref: ${refId}`, 'success');
    }).catch(() => {});
  } catch { localStorage.removeItem('fn_pending_app'); }
}

function _resetLoanForms() {
  document.querySelectorAll('.apply-form-card form, form[onsubmit*="submitLoanForm"]').forEach(form => {
    form.reset();
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.origText || 'Check Eligibility & Apply';
      btn.style.background = '';
    }
    form.querySelectorAll('input').forEach(inp => {
      inp.readOnly = false;
      inp.style.background = '';
      inp.style.color = '';
      inp.style.borderColor = '';
      inp.title = '';
    });
  });
}

// Called by "Apply" button in the bank rates table
window.applyNow = (loanType) => {
  const session = FinNova.getSession();
  const formCard = document.querySelector('.apply-form-card');
  if (!session || !session.loggedIn) {
    // Not logged in — save intended loan type and open login
    localStorage.setItem('fn_pending_apply', loanType);
    openLoginModal('login');
    return;
  }
  // Already logged in — scroll to the apply form
  if (formCard) {
    formCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    formCard.style.outline = '3px solid #4f46e5';
    formCard.style.borderRadius = '16px';
    setTimeout(() => { formCard.style.outline = ''; }, 2000);
    autoFillLoanForm();
  }
};

// Auto-fill name/email/mobile from session or URL params (admin apply-on-behalf)
window.autoFillLoanForm = async () => {
  const params = new URLSearchParams(window.location.search);
  const applyFor = params.get('apply_for');

  let user;
  if (applyFor) {
    user = {
      name: applyFor,
      mobile: params.get('apply_mobile') || '',
      email: params.get('apply_email') || ''
    };
  } else {
    const session = FinNova.getSession();
    const token   = FinNova.getToken();
    if (!session || !session.loggedIn) return;

    user = { name: session.name, mobile: '', email: '' };
    try {
      const res = await fetch(`${API}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }, cache: 'no-store'
      });
      if (res.ok) user = await res.json();
    } catch { /* use session fallback */ }
  }

  // Fill each form in the page
  document.querySelectorAll('.apply-form-card form, form[onsubmit*="submitLoanForm"]').forEach(form => {
    const setVal = (selectors, value) => {
      if (!value) return;
      for (const sel of selectors) {
        const el = form.querySelector(sel);
        if (el && !el.value) { el.value = value; el.dispatchEvent(new Event('input')); return; }
      }
    };
    setVal(['#loanName', '[name="full_name"]', 'input[type="text"][placeholder*="name" i]'], user.name);
    setVal(['#loanMobile', '[name="mobile"]', 'input[type="tel"]'], user.mobile);
    setVal(['#loanEmail', '[name="email"]', 'input[type="email"]'], user.email);

    form.querySelectorAll('#loanName, #loanMobile, #loanEmail, [name="full_name"], [name="mobile"], [name="email"]').forEach(inp => {
      if (inp && inp.value) {
        inp.readOnly = true;
        inp.style.background = '#f0fdf4';
        inp.style.color = '#166534';
        inp.style.borderColor = '#86efac';
        inp.title = '✓ Auto-filled from your profile';
      }
    });
  });
};


window.submitLoanForm = (e, loanType) => {
  e.preventDefault();
  const form = e.target;
  const btn  = form.querySelector('button[type="submit"]');

  const formData = {};
  form.querySelectorAll('input:not([type="checkbox"]):not([type="submit"]), select, textarea').forEach(el => {
    const key = el.name || el.id;
    if (key) formData[key] = el.value;
  });

  const nameVal   = (formData.full_name || formData.loanName || formData.name || '').trim();
  const mobileVal = sanitizeMobile(formData.mobile || formData.loanMobile || '');
  const dobVal    = (formData.dob || '').trim();
  const pinVal    = (formData.pincode || '').trim();
  if (!nameVal)   { showToast('Full Name is required', 'error'); return; }
  if (!isValidIndianMobile(mobileVal)) { showToast('Enter valid 10-digit mobile number starting with 6-9', 'error'); return; }
  if (!dobVal)    { showToast('Date of Birth is required', 'error'); return; }
  if (!pinVal || !/^[0-9]{6}$/.test(pinVal)) { showToast('Valid 6-digit Pincode is required', 'error'); return; }

  if (btn) {
    if (!btn.dataset.origText) btn.dataset.origText = btn.textContent;
    btn.textContent = 'Submitting...'; btn.disabled = true;
  }

  const applyParams = new URLSearchParams(window.location.search);
  if (applyParams.get('apply_for')) {
    formData._apply_for_email = applyParams.get('apply_email') || '';
  }

  FinNova.saveApplication(loanType, formData).then(refId => {
    if (btn) {
      btn.textContent = `✓ Submitted! Ref: ${refId}`;
      btn.style.background = 'linear-gradient(135deg,#059669,#047857)';
    }
    showToast(`Application submitted! Ref: ${refId}`, 'success');
    setTimeout(() => {
      form.reset();
      if (btn) {
        btn.textContent = btn.dataset.origText || 'Check Eligibility & Apply';
        btn.style.background = '';
        btn.disabled = false;
      }
      form.querySelectorAll('input').forEach(inp => {
        inp.readOnly = false;
        inp.style.background = '';
        inp.style.color = '';
        inp.style.borderColor = '';
        inp.title = '';
      });
      autoFillLoanForm();
    }, 2000);
  }).catch(() => {
    if (btn) { btn.textContent = 'Submit Failed — Retry'; btn.disabled = false; }
    showToast('Could not save. Please retry.', 'error');
  });
};

/* ---- Toast Notification ---- */
window.showToast = (msg, type = 'success') => {
  let toast = document.getElementById('fn-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'fn-toast';
    toast.style.cssText = `
      position:fixed; bottom:2rem; left:50%; transform:translateX(-50%) translateY(80px);
      background:${type === 'success' ? '#059669' : '#dc2626'}; color:#fff;
      padding:.875rem 2rem; border-radius:50px; font-size:.875rem; font-weight:600;
      box-shadow:0 8px 30px rgba(0,0,0,.2); z-index:9999;
      transition:transform .35s cubic-bezier(.34,1.56,.64,1), opacity .35s ease;
      opacity:0; white-space:nowrap; max-width:90vw; overflow:hidden; text-overflow:ellipsis;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.background = type === 'success' ? '#059669' : '#dc2626';
  // Animate in
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
  });
  // Animate out
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(-50%) translateY(80px)';
  }, 4000);
};

// ---- Warn before leaving if form has unsaved data ----
(function() {
  function hasUnsavedFormData() {
    const forms = document.querySelectorAll('.apply-form-card form, #loginForm, #registerForm');
    for (const form of forms) {
      if (form.closest('.modal-overlay') && !form.closest('.modal-overlay.active')) continue;
      const inputs = form.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([readonly]), select, textarea');
      for (const inp of inputs) {
        if (inp.value && inp.value.trim()) return true;
      }
    }
    return false;
  }

  window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedFormData()) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
})();
