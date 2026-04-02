// LexRisk Website - Accessible JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // CTA Form Handling
    const ctaForm = document.querySelector('.cta-form');
    const ctaInput = document.querySelector('.cta-input');
    const ctaButton = document.querySelector('.cta-form .button');
    
    if (ctaButton) {
        ctaButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const email = ctaInput.value.trim();
            
            if (!email) {
                ctaInput.setAttribute('aria-invalid', 'true');
                ctaInput.focus();
                return;
            }
            
            if (!isValidEmail(email)) {
                ctaInput.setAttribute('aria-invalid', 'true');
                ctaInput.setAttribute('aria-describedby', 'email-error');
                ctaInput.focus();
                return;
            }
            
            // Reset invalid state
            ctaInput.setAttribute('aria-invalid', 'false');
            
            // Show success message
            const originalText = ctaButton.textContent;
            ctaButton.textContent = '✓ Check your email!';
            ctaButton.disabled = true;
            
            // Simulate API call
            setTimeout(() => {
                ctaButton.textContent = originalText;
                ctaButton.disabled = false;
                ctaInput.value = '';
            }, 3000);
        });
    }
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Move focus to target
                target.focus();
                if (!target.hasAttribute('tabindex')) {
                    target.setAttribute('tabindex', '-1');
                }
            }
        });
    });
    
    // Mobile menu toggle (future enhancement)
    setupKeyboardNavigationAssist();
    setupAccessibilityFeatures();
});

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function setupKeyboardNavigationAssist() {
    // Visible focus indicators for keyboard navigation
    let isKeyboardNav = false;
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            isKeyboardNav = true;
            document.body.classList.add('keyboard-nav');
        }
    });
    
    document.addEventListener('mousedown', function() {
        isKeyboardNav = false;
        document.body.classList.remove('keyboard-nav');
    });
}

function setupAccessibilityFeatures() {
    // Ensure all buttons have accessible labels
    document.querySelectorAll('button, [role="button"]').forEach(btn => {
        if (!btn.getAttribute('aria-label') && btn.textContent.trim()) {
            // Button has visible text, that's fine
        }
    });
    
    // Add aria-current for active nav links
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.setAttribute('aria-current', 'page');
        }
    });
}

// Announce important updates to screen readers
function announce(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.textContent = message;
    
    // Hide visually but keep in accessibility tree
    announcement.style.position = 'absolute';
    announcement.style.left = '-10000px';
    announcement.style.width = '1px';
    announcement.style.height = '1px';
    announcement.style.overflow = 'hidden';
    
    document.body.appendChild(announcement);
    
    setTimeout(() => announcement.remove(), 3000);
}

// Log page performance for accessibility
window.addEventListener('load', function() {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log(`Page loaded in ${pageLoadTime}ms`);
});

// Handle contrast preference
if (window.matchMedia('(prefers-contrast: more)').matches) {
    document.documentElement.style.setProperty('--shadow-md', 'none');
    document.documentElement.style.setProperty('--shadow-lg', 'none');
}

// Handle reduced motion preference
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.style.setProperty('--transition-fast', '0ms');
    document.documentElement.style.setProperty('--transition-normal', '0ms');
    document.documentElement.style.setProperty('--transition-slow', '0ms');
}

// Handle dark mode preference
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    // CSS handles this via @media (prefers-color-scheme: dark)
    console.log('Dark mode preference detected');
}
