/**
 * CodeGraph Landing Page - Main JavaScript
 * Enterprise TOP-200 RF
 */

(function() {
  'use strict';

  // ============================================
  // Configuration
  // ============================================
  const CONFIG = {
    animationDuration: 300,
    typingSpeed: 50,
    counterDuration: 2000,
    scrollOffset: 80,
    observerThreshold: 0.1,
    // API configuration for demo
    apiBaseUrl: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8000'
      : '',  // Same origin in production
    apiTimeout: 30000  // 30 seconds timeout
  };

  // Demo scenarios with questions and responses
  const DEMO_SCENARIOS = {
    security: {
      question: 'Найди SQL injection уязвимости',
      response: `<span class="highlight">Анализ кодовой базы...</span>

<span class="success">Найдено 3 потенциальные уязвимости SQL injection:</span>

1. <span class="danger">src/backend/parser/parser.c:1247</span>
   Небезопасное формирование SQL-запроса через sprintf()

2. <span class="danger">src/backend/commands/copy.c:892</span>
   Отсутствует валидация параметра filename

3. <span class="warning">src/backend/utils/adt/ruleutils.c:3456</span>
   Потенциальный SQL injection через конкатенацию

<span class="highlight">Рекомендация:</span> Использовать параметризованные запросы`
    },
    architecture: {
      question: 'Как работает MVCC в PostgreSQL?',
      response: `<span class="highlight">Анализ архитектуры MVCC...</span>

<span class="success">Multi-Version Concurrency Control (MVCC):</span>

<span class="highlight">Основные компоненты:</span>
- <span class="success">HeapTupleHeaderData</span> — метаданные версий строк
- <span class="success">TransactionId (xmin/xmax)</span> — границы видимости
- <span class="success">Snapshot</span> — согласованное представление данных

<span class="highlight">Ключевые файлы:</span>
- src/backend/access/heap/heapam.c
- src/backend/storage/lmgr/lmgr.c
- src/backend/utils/time/snapmgr.c

<span class="highlight">Data Flow:</span>
INSERT → xmin = current_xid, xmax = 0
UPDATE → old: xmax = current_xid, new: xmin = current_xid`
    },
    callgraph: {
      question: 'Покажи callers функции palloc',
      response: `<span class="highlight">Построение графа вызовов для palloc()...</span>

<span class="success">Найдено 847 прямых вызовов в 234 файлах</span>

<span class="highlight">Топ-10 вызывающих модулей:</span>
1. src/backend/utils/mmgr/mcxt.c (42 вызова)
2. src/backend/executor/execMain.c (38 вызовов)
3. src/backend/parser/parser.c (35 вызовов)
4. src/backend/catalog/pg_proc.c (28 вызовов)
5. src/backend/commands/tablecmds.c (25 вызовов)

<span class="highlight">Граф зависимостей:</span>
palloc() ← MemoryContextAlloc() ← ExecInitExpr()
         ← makeNode()
         ← pstrdup()

<span class="success">CPGQL запрос:</span> cpg.method.name("palloc").caller`
    },
    deadcode: {
      question: 'Найди неиспользуемый код',
      response: `<span class="highlight">Поиск мёртвого кода...</span>

<span class="success">Найдено 12 потенциально неиспользуемых функций:</span>

1. <span class="warning">src/backend/utils/misc/guc.c:old_check_function</span>
   Последний вызов: git log -1 → 2019-03-15

2. <span class="warning">src/backend/access/heap/heapam.c:heap_getnext_old</span>
   Закомментированный код, 0 вызовов

3. <span class="warning">src/backend/parser/parse_expr.c:transformIndirection_v1</span>
   Устаревшая версия, заменена на transformIndirection_v2

<span class="highlight">Экономия:</span>
- ~450 строк кода можно удалить
- Потенциальное ускорение компиляции на 2%`
    }
  };

  // ============================================
  // DOM Elements Cache
  // ============================================
  const DOM = {};

  function cacheDOM() {
    DOM.html = document.documentElement;
    DOM.body = document.body;
    DOM.header = document.querySelector('.header');
    DOM.themeToggle = document.querySelector('.theme-toggle');
    DOM.mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    DOM.mobileNav = document.querySelector('.mobile-nav');
    DOM.navLinks = document.querySelectorAll('.nav-link, .mobile-nav-link');
    DOM.demoInput = document.getElementById('demo-input');
    DOM.demoOutput = document.getElementById('demo-output');
    DOM.demoCursor = document.querySelector('.demo-cursor');
    DOM.demoExampleBtns = document.querySelectorAll('.demo-example-btn');
    DOM.featureTabs = document.querySelectorAll('.feature-tab');
    DOM.featurePanels = document.querySelectorAll('.features-panel');
    DOM.faqItems = document.querySelectorAll('.faq-item');
    DOM.faqSearch = document.querySelector('.faq-search-input');
    DOM.faqCategoryBtns = document.querySelectorAll('.faq-category-btn');
    DOM.integrationFilterBtns = document.querySelectorAll('.integration-filter-btn');
    DOM.integrationCards = document.querySelectorAll('.integration-card');
    DOM.pipelineSteps = document.querySelectorAll('.pipeline-step');
    DOM.scenarioTabs = document.querySelectorAll('.scenario-tab');
    DOM.counters = document.querySelectorAll('[data-count]');
    DOM.progressBars = document.querySelectorAll('.quality-metric-bar-fill');
    DOM.animatedElements = document.querySelectorAll('[data-animate]');
    DOM.demoForm = document.getElementById('demo-form');
    // Solution section demo
    DOM.questionInput = document.getElementById('question-input');
    DOM.askBtn = document.getElementById('ask-btn');
    DOM.demoResult = document.getElementById('demo-result');
    DOM.solutionExampleBtns = document.querySelectorAll('.solution .demo-example-btn, #solution .demo-example-btn');
  }

  // ============================================
  // Theme Management
  // ============================================
  function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(theme);

    if (DOM.themeToggle) {
      DOM.themeToggle.addEventListener('click', toggleTheme);
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  function setTheme(theme) {
    DOM.html.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  function toggleTheme() {
    const currentTheme = DOM.html.getAttribute('data-theme');
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
  }

  // ============================================
  // Mobile Navigation
  // ============================================
  function initMobileNav() {
    if (!DOM.mobileMenuToggle || !DOM.mobileNav) return;

    DOM.mobileMenuToggle.addEventListener('click', () => {
      DOM.mobileMenuToggle.classList.toggle('active');
      DOM.mobileNav.classList.toggle('open');
      DOM.body.style.overflow = DOM.mobileNav.classList.contains('open') ? 'hidden' : '';
    });

    // Close on link click
    DOM.navLinks.forEach(link => {
      link.addEventListener('click', () => {
        DOM.mobileMenuToggle.classList.remove('active');
        DOM.mobileNav.classList.remove('open');
        DOM.body.style.overflow = '';
      });
    });

    // Close on escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && DOM.mobileNav.classList.contains('open')) {
        DOM.mobileMenuToggle.classList.remove('active');
        DOM.mobileNav.classList.remove('open');
        DOM.body.style.overflow = '';
      }
    });
  }

  // ============================================
  // Header Scroll Behavior
  // ============================================
  function initHeaderScroll() {
    if (!DOM.header) return;

    let lastScroll = 0;
    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const currentScroll = window.pageYOffset;

          if (currentScroll > 50) {
            DOM.header.classList.add('scrolled');
          } else {
            DOM.header.classList.remove('scrolled');
          }

          lastScroll = currentScroll;
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  // ============================================
  // Smooth Scroll
  // ============================================
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          const offsetTop = target.offsetTop - CONFIG.scrollOffset;
          window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
          });
        }
      });
    });
  }

  // ============================================
  // Demo Terminal
  // ============================================
  function initDemoTerminal() {
    if (!DOM.demoInput || !DOM.demoOutput) return;

    // Handle input
    DOM.demoInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const query = DOM.demoInput.value.trim();
        if (query) {
          runDemo(query);
        }
      }
    });

    // Handle example buttons
    DOM.demoExampleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        DOM.demoInput.value = query;
        runDemo(query);
      });
    });

    // Auto-run first demo on load
    setTimeout(() => {
      if (DOM.demoExampleBtns.length > 0) {
        const firstQuery = DOM.demoExampleBtns[0].getAttribute('data-query');
        typeText(DOM.demoInput, firstQuery, () => {
          setTimeout(() => runDemo(firstQuery), 500);
        });
      }
    }, 1500);
  }

  function runDemo(query) {
    // Find matching scenario
    let scenario = null;
    const queryLower = query.toLowerCase();

    if (queryLower.includes('sql') || queryLower.includes('уязвим') || queryLower.includes('injection')) {
      scenario = DEMO_SCENARIOS.security;
    } else if (queryLower.includes('mvcc') || queryLower.includes('архитектур') || queryLower.includes('работает')) {
      scenario = DEMO_SCENARIOS.architecture;
    } else if (queryLower.includes('caller') || queryLower.includes('вызов') || queryLower.includes('palloc')) {
      scenario = DEMO_SCENARIOS.callgraph;
    } else if (queryLower.includes('dead') || queryLower.includes('неиспользуем') || queryLower.includes('мёртв')) {
      scenario = DEMO_SCENARIOS.deadcode;
    } else {
      // Default to security
      scenario = DEMO_SCENARIOS.security;
    }

    // Animate pipeline
    animatePipeline();

    // Show response with typing effect
    DOM.demoOutput.innerHTML = '';
    if (DOM.demoCursor) DOM.demoCursor.style.display = 'inline-block';

    typeHTML(DOM.demoOutput, scenario.response, () => {
      if (DOM.demoCursor) DOM.demoCursor.style.display = 'none';
    });
  }

  function typeText(element, text, callback) {
    let i = 0;
    element.value = '';

    function type() {
      if (i < text.length) {
        element.value += text.charAt(i);
        i++;
        setTimeout(type, CONFIG.typingSpeed);
      } else if (callback) {
        callback();
      }
    }

    type();
  }

  function typeHTML(element, html, callback) {
    // Parse HTML and type it out
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const text = tempDiv.textContent;

    let i = 0;
    let currentHTML = '';

    function type() {
      if (i < html.length) {
        // Handle HTML tags
        if (html[i] === '<') {
          const closeTag = html.indexOf('>', i);
          if (closeTag !== -1) {
            currentHTML += html.substring(i, closeTag + 1);
            i = closeTag + 1;
          }
        } else {
          currentHTML += html[i];
          i++;
        }

        element.innerHTML = currentHTML;

        // Variable speed for more natural feel
        const delay = html[i - 1] === '\n' ? 100 : (Math.random() * 20 + 10);
        setTimeout(type, delay);
      } else if (callback) {
        callback();
      }
    }

    type();
  }

  // ============================================
  // Solution Section Demo
  // ============================================
  function initSolutionDemo() {
    if (!DOM.questionInput || !DOM.demoResult) return;

    // Handle ask button
    if (DOM.askBtn) {
      DOM.askBtn.addEventListener('click', () => {
        const query = DOM.questionInput.value.trim();
        if (query) {
          runSolutionDemo(query);
        }
      });
    }

    // Handle input enter key
    DOM.questionInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const query = DOM.questionInput.value.trim();
        if (query) {
          runSolutionDemo(query);
        }
      }
    });

    // Handle example buttons in solution section
    const exampleBtns = document.querySelectorAll('#solution .demo-example-btn');
    exampleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        DOM.questionInput.value = query;
        runSolutionDemo(query);
      });
    });
  }

  async function runSolutionDemo(query) {
    // Animate pipeline
    animatePipeline();

    // Show loading state
    DOM.demoResult.innerHTML = '<div class="result-loading"><span class="spinner"></span> Анализирую...</div>';

    try {
      // Try to call the API
      const response = await fetchWithTimeout(
        `${CONFIG.apiBaseUrl}/api/v1/demo/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query,
            language: 'ru'
          })
        },
        CONFIG.apiTimeout
      );

      if (response.status === 429) {
        // Rate limit exceeded
        showRateLimitError();
        return;
      }

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      showApiResult(data.answer, data.processing_time_ms);

    } catch (err) {
      console.warn('API call failed, using fallback:', err.message);
      // Fallback to mock response
      showMockResponse(query);
    }
  }

  // Helper function for fetch with timeout
  async function fetchWithTimeout(url, options, timeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  // Show API result
  function showApiResult(answer, processingTimeMs) {
    const timeStr = processingTimeMs ? ` <span class="processing-time">(${processingTimeMs.toFixed(0)}ms)</span>` : '';
    DOM.demoResult.innerHTML = `<div class="result-content"><pre>${escapeHtml(answer)}</pre>${timeStr}</div>`;
  }

  // Show rate limit error
  function showRateLimitError() {
    DOM.demoResult.innerHTML = `<div class="result-error">
      <span class="warning">Превышен лимит запросов (30/мин)</span>
      <p>Пожалуйста, подождите минуту и попробуйте снова.</p>
    </div>`;
  }

  // Fallback to mock response
  function showMockResponse(query) {
    const scenario = findMatchingScenario(query);
    setTimeout(() => {
      DOM.demoResult.innerHTML = '<div class="result-content"><pre>' + scenario.response + '</pre></div>';
    }, 1000);
  }

  // Find matching mock scenario
  function findMatchingScenario(query) {
    const queryLower = query.toLowerCase();

    if (queryLower.includes('sql') || queryLower.includes('уязвим') || queryLower.includes('injection')) {
      return DEMO_SCENARIOS.security;
    } else if (queryLower.includes('mvcc') || queryLower.includes('архитектур') || queryLower.includes('работает')) {
      return DEMO_SCENARIOS.architecture;
    } else if (queryLower.includes('caller') || queryLower.includes('вызов') || queryLower.includes('palloc')) {
      return DEMO_SCENARIOS.callgraph;
    } else if (queryLower.includes('dead') || queryLower.includes('неиспользуем') || queryLower.includes('мёртв')) {
      return DEMO_SCENARIOS.deadcode;
    } else {
      return DEMO_SCENARIOS.security;
    }
  }

  // Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ============================================
  // Pipeline Animation
  // ============================================
  function animatePipeline() {
    if (!DOM.pipelineSteps || DOM.pipelineSteps.length === 0) return;

    // Reset all steps
    DOM.pipelineSteps.forEach(step => step.classList.remove('active'));

    // Animate each step sequentially
    DOM.pipelineSteps.forEach((step, index) => {
      setTimeout(() => {
        // Deactivate previous
        if (index > 0) {
          DOM.pipelineSteps[index - 1].classList.remove('active');
        }
        // Activate current
        step.classList.add('active');
      }, index * 800);
    });

    // Keep last step active
    setTimeout(() => {
      DOM.pipelineSteps[DOM.pipelineSteps.length - 1].classList.add('active');
    }, DOM.pipelineSteps.length * 800);
  }

  // ============================================
  // Feature Tabs
  // ============================================
  function initFeatureTabs() {
    if (!DOM.featureTabs || DOM.featureTabs.length === 0) return;

    DOM.featureTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-tab');

        // Update tabs
        DOM.featureTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Update panels
        DOM.featurePanels.forEach(panel => {
          panel.classList.remove('active');
          if (panel.getAttribute('data-panel') === target) {
            panel.classList.add('active');
          }
        });
      });
    });
  }

  // ============================================
  // Scenario Tabs
  // ============================================
  function initScenarioTabs() {
    if (!DOM.scenarioTabs || DOM.scenarioTabs.length === 0) return;

    DOM.scenarioTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const scenario = tab.getAttribute('data-scenario');

        // Update tabs
        DOM.scenarioTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Run demo for scenario
        if (DEMO_SCENARIOS[scenario]) {
          DOM.demoInput.value = DEMO_SCENARIOS[scenario].question;
          runDemo(DEMO_SCENARIOS[scenario].question);
        }
      });
    });
  }

  // ============================================
  // FAQ Accordion
  // ============================================
  function initFAQ() {
    if (!DOM.faqItems || DOM.faqItems.length === 0) return;

    DOM.faqItems.forEach(item => {
      const question = item.querySelector('.faq-question');
      if (question) {
        question.addEventListener('click', () => {
          const isOpen = item.classList.contains('open');

          // Close all items (optional: for single open)
          // DOM.faqItems.forEach(i => i.classList.remove('open'));

          // Toggle current
          item.classList.toggle('open');
        });
      }
    });

    // FAQ Search
    if (DOM.faqSearch) {
      DOM.faqSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();

        DOM.faqItems.forEach(item => {
          const text = item.textContent.toLowerCase();
          item.style.display = text.includes(query) ? '' : 'none';
        });
      });
    }

    // FAQ Category Filter
    if (DOM.faqCategoryBtns) {
      DOM.faqCategoryBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const category = btn.getAttribute('data-category');

          // Update buttons
          DOM.faqCategoryBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          // Filter items
          DOM.faqItems.forEach(item => {
            if (category === 'all') {
              item.style.display = '';
            } else {
              const itemCategory = item.getAttribute('data-category');
              item.style.display = itemCategory === category ? '' : 'none';
            }
          });
        });
      });
    }
  }

  // ============================================
  // Integration Filters
  // ============================================
  function initIntegrationFilters() {
    if (!DOM.integrationFilterBtns || DOM.integrationFilterBtns.length === 0) return;

    DOM.integrationFilterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-filter');

        // Update buttons
        DOM.integrationFilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Filter cards
        DOM.integrationCards.forEach(card => {
          if (filter === 'all') {
            card.style.display = '';
          } else {
            const status = card.getAttribute('data-status');
            card.style.display = status === filter ? '' : 'none';
          }
        });
      });
    });
  }

  // ============================================
  // Counter Animation
  // ============================================
  function initCounters() {
    if (!DOM.counters || DOM.counters.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: CONFIG.observerThreshold });

    DOM.counters.forEach(counter => observer.observe(counter));
  }

  function animateCounter(element) {
    const target = parseInt(element.getAttribute('data-count'), 10);
    const suffix = element.getAttribute('data-suffix') || '';
    const prefix = element.getAttribute('data-prefix') || '';
    const duration = CONFIG.counterDuration;
    const start = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - start;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function (ease-out)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(easeOut * target);

      element.textContent = prefix + current + suffix;

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        element.textContent = prefix + target + suffix;
      }
    }

    requestAnimationFrame(update);
  }

  // ============================================
  // Progress Bar Animation
  // ============================================
  function initProgressBars() {
    if (!DOM.progressBars || DOM.progressBars.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = entry.target.getAttribute('data-progress') || '0';
          entry.target.style.width = target + '%';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: CONFIG.observerThreshold });

    DOM.progressBars.forEach(bar => observer.observe(bar));
  }

  // ============================================
  // Scroll Animations
  // ============================================
  function initScrollAnimations() {
    if (!DOM.animatedElements || DOM.animatedElements.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const animation = entry.target.getAttribute('data-animate');
          entry.target.classList.add('animated', `animate-${animation}`);
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: CONFIG.observerThreshold,
      rootMargin: '0px 0px -50px 0px'
    });

    DOM.animatedElements.forEach(el => observer.observe(el));
  }

  // ============================================
  // Form Validation
  // ============================================
  function initFormValidation() {
    if (!DOM.demoForm) return;

    // Russian validation messages
    const validationMessages = {
      valueMissing: 'Пожалуйста, заполните это поле',
      typeMismatch: {
        email: 'Пожалуйста, введите корректный email адрес',
        url: 'Пожалуйста, введите корректный URL'
      },
      patternMismatch: 'Пожалуйста, введите данные в правильном формате',
      tooShort: 'Минимальная длина: {minLength} символов',
      tooLong: 'Максимальная длина: {maxLength} символов'
    };

    // Apply Russian validation to all form inputs
    const formInputs = DOM.demoForm.querySelectorAll('input, select, textarea');
    formInputs.forEach(input => {
      // Set custom message before validation
      input.addEventListener('invalid', (e) => {
        const validity = input.validity;

        if (validity.valueMissing) {
          input.setCustomValidity(validationMessages.valueMissing);
        } else if (validity.typeMismatch) {
          const type = input.type;
          input.setCustomValidity(validationMessages.typeMismatch[type] || 'Неверный формат');
        } else if (validity.patternMismatch) {
          input.setCustomValidity(validationMessages.patternMismatch);
        } else if (validity.tooShort) {
          input.setCustomValidity(validationMessages.tooShort.replace('{minLength}', input.minLength));
        } else if (validity.tooLong) {
          input.setCustomValidity(validationMessages.tooLong.replace('{maxLength}', input.maxLength));
        }
      });

      // Clear custom validity on input to allow re-validation
      input.addEventListener('input', () => {
        input.setCustomValidity('');
      });

      // Also clear on change for select elements
      input.addEventListener('change', () => {
        input.setCustomValidity('');
      });
    });

    DOM.demoForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Simple validation
      const inputs = DOM.demoForm.querySelectorAll('input[required], select[required]');
      let isValid = true;

      inputs.forEach(input => {
        if (!input.value.trim()) {
          isValid = false;
          input.classList.add('error');
        } else {
          input.classList.remove('error');
        }
      });

      // Email validation
      const emailInput = DOM.demoForm.querySelector('input[type="email"]');
      if (emailInput && emailInput.value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(emailInput.value)) {
          isValid = false;
          emailInput.classList.add('error');
        }
      }

      if (isValid) {
        // Submit form to leads API
        const submitBtn = DOM.demoForm.querySelector('button[type="submit"]');
        if (!submitBtn) return;

        const originalText = submitBtn.textContent;

        submitBtn.textContent = 'Отправка...';
        submitBtn.disabled = true;

        // Collect form data
        const formData = {
          name: DOM.demoForm.querySelector('#name').value.trim(),
          email: DOM.demoForm.querySelector('#email').value.trim(),
          company: DOM.demoForm.querySelector('#company').value.trim(),
          position: DOM.demoForm.querySelector('#position')?.value.trim() || null,
          team_size: DOM.demoForm.querySelector('#team-size')?.value || null,
          language: DOM.demoForm.querySelector('#language')?.value || null,
        };

        // Determine API URL based on environment
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const leadsApiUrl = isLocalhost
          ? 'http://localhost:8001/api/v1/leads'
          : '/api/leads';

        try {
          const response = await fetch(leadsApiUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
          });

          if (response.ok) {
            submitBtn.textContent = 'Заявка отправлена!';
            submitBtn.style.background = '#10B981';
            DOM.demoForm.reset();

            setTimeout(() => {
              submitBtn.textContent = originalText;
              submitBtn.style.background = '';
              submitBtn.disabled = false;
            }, 3000);
          } else if (response.status === 429) {
            submitBtn.textContent = 'Слишком много запросов';
            submitBtn.style.background = '#EF4444';

            setTimeout(() => {
              submitBtn.textContent = originalText;
              submitBtn.style.background = '';
              submitBtn.disabled = false;
            }, 3000);
          } else {
            throw new Error(`Server error: ${response.status}`);
          }
        } catch (error) {
          console.error('Form submission error:', error);
          submitBtn.textContent = 'Ошибка отправки';
          submitBtn.style.background = '#EF4444';

          setTimeout(() => {
            submitBtn.textContent = originalText;
            submitBtn.style.background = '';
            submitBtn.disabled = false;
          }, 3000);
        }
      }
    });
  }

  // ============================================
  // Active Navigation Highlight
  // ============================================
  function initActiveNavigation() {
    const sections = document.querySelectorAll('section[id]');

    if (sections.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          DOM.navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${id}`) {
              link.classList.add('active');
            }
          });
        }
      });
    }, {
      threshold: 0.3,
      rootMargin: '-80px 0px -50% 0px'
    });

    sections.forEach(section => observer.observe(section));
  }

  // ============================================
  // Keyboard Navigation
  // ============================================
  function initKeyboardNavigation() {
    // Tab focus indicators are handled by CSS :focus-visible

    // Arrow key navigation for tabs
    document.addEventListener('keydown', (e) => {
      if (e.target.classList.contains('feature-tab') ||
          e.target.classList.contains('scenario-tab') ||
          e.target.classList.contains('faq-question')) {

        const parent = e.target.parentElement;
        const items = Array.from(parent.querySelectorAll('[role="tab"], .faq-question'));
        const currentIndex = items.indexOf(e.target);

        let newIndex;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          newIndex = (currentIndex + 1) % items.length;
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          newIndex = (currentIndex - 1 + items.length) % items.length;
        }

        if (newIndex !== undefined) {
          e.preventDefault();
          items[newIndex].focus();
          items[newIndex].click();
        }
      }
    });
  }

  // ============================================
  // Performance Optimization
  // ============================================
  function initPerformanceOptimizations() {
    // Lazy load images (if any)
    if ('loading' in HTMLImageElement.prototype) {
      const images = document.querySelectorAll('img[loading="lazy"]');
      images.forEach(img => {
        img.src = img.dataset.src;
      });
    }

    // Prefetch linked pages on hover
    let prefetchedLinks = new Set();
    document.querySelectorAll('a[href^="http"]').forEach(link => {
      link.addEventListener('mouseenter', () => {
        const href = link.getAttribute('href');
        if (!prefetchedLinks.has(href)) {
          const prefetch = document.createElement('link');
          prefetch.rel = 'prefetch';
          prefetch.href = href;
          document.head.appendChild(prefetch);
          prefetchedLinks.add(href);
        }
      }, { once: true });
    });
  }

  // ============================================
  // Accessibility Helpers
  // ============================================
  function initAccessibility() {
    // Add ARIA attributes dynamically
    DOM.faqItems.forEach((item, index) => {
      const question = item.querySelector('.faq-question');
      const answer = item.querySelector('.faq-answer');

      if (question && answer) {
        question.setAttribute('aria-expanded', 'false');
        question.setAttribute('aria-controls', `faq-answer-${index}`);
        answer.setAttribute('id', `faq-answer-${index}`);

        question.addEventListener('click', () => {
          const isOpen = item.classList.contains('open');
          question.setAttribute('aria-expanded', isOpen);
        });
      }
    });

    // Add role="tab" to tabs
    DOM.featureTabs.forEach(tab => {
      tab.setAttribute('role', 'tab');
    });

    DOM.scenarioTabs.forEach(tab => {
      tab.setAttribute('role', 'tab');
    });
  }

  // ============================================
  // Error Handling
  // ============================================
  window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ', msg, '\nURL: ', url, '\nLine: ', lineNo);
    return false;
  };

  // ============================================
  // Initialize
  // ============================================
  function init() {
    cacheDOM();
    initTheme();
    initMobileNav();
    initHeaderScroll();
    initSmoothScroll();
    initDemoTerminal();
    initSolutionDemo();
    initFeatureTabs();
    initScenarioTabs();
    initFAQ();
    initIntegrationFilters();
    initCounters();
    initProgressBars();
    initScrollAnimations();
    initFormValidation();
    initActiveNavigation();
    initKeyboardNavigation();
    initPerformanceOptimizations();
    initAccessibility();

    console.log('CodeGraph Landing Page initialized');
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
