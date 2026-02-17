// Navigation scroll effect
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 20);
});

// Mobile nav toggle
const navToggle = document.getElementById('nav-toggle');
const navLinks = document.getElementById('nav-links');
navToggle.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// Close mobile nav on link click
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
  });
});

// Scroll reveal animation
const revealElements = document.querySelectorAll(
  '.feature-card, .arch-layer, .arch-side-card, .tool-group, .guarantee, .stack-card, .step, .ci-gate'
);

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
);

revealElements.forEach(el => observer.observe(el));

// Copy buttons
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const code = btn.getAttribute('data-code');
    navigator.clipboard.writeText(code).then(() => {
      const original = btn.textContent;
      btn.textContent = 'Copied!';
      btn.style.color = '#22c55e';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.color = '';
      }, 2000);
    });
  });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    const target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      e.preventDefault();
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  });
});
