/* AEROSTRIDE storefront script. Vanilla ES6+, no dependencies.
   The server re-validates and re-prices everything at checkout; client state is a convenience only. */
(() => {
  "use strict";

  document.documentElement.classList.add("js");

  const CART_KEY = "aerostride.cart.v1";
  const WISH_KEY = "aerostride.wish.v1";
  const body = document.body;
  const FREE_SHIP = Number(body.dataset.freeShipping) || 7999;
  const FLAT_SHIP = Number(body.dataset.flatShipping) || 249;
  const MAX_QTY = Number(body.dataset.maxQty) || 10;
  const MAX_LINES = 25;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Formatting ---------- */
  const inr = (n) => "₹" + Math.round(n).toLocaleString("en-IN");

  /* ---------- Safe storage (can throw in private mode or when blocked) ---------- */
  const memory = {};
  const store = {
    read(key, fallback) {
      try {
        const raw = window.localStorage.getItem(key);
        return raw === null ? (key in memory ? memory[key] : fallback) : JSON.parse(raw);
      } catch (_) {
        return key in memory ? memory[key] : fallback;
      }
    },
    write(key, value) {
      memory[key] = value;
      try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* keep in-memory copy */ }
    },
    remove(key) {
      delete memory[key];
      try { window.localStorage.removeItem(key); } catch (_) { /* ignore */ }
    },
  };

  /* ---------- Catalogue (cart + checkout pages only) ---------- */
  let catalog = null;
  const catalogEl = $("#catalog-data");
  if (catalogEl) {
    try { catalog = JSON.parse(catalogEl.textContent); } catch (_) { catalog = null; }
  }

  /* ---------- Cart model ---------- */
  const sanitizeCart = (raw) => {
    if (!Array.isArray(raw)) return [];
    const merged = new Map();
    for (const it of raw) {
      if (!it || typeof it.id !== "string") continue;
      const size = Number(it.size);
      const qty = Number(it.qty);
      if (!Number.isInteger(size) || !Number.isInteger(qty) || qty < 1) continue;
      if (catalog && (!catalog[it.id] || !catalog[it.id].sizes.includes(size))) continue;
      const key = it.id + "|" + size;
      const prev = merged.get(key);
      merged.set(key, { id: it.id, size, qty: Math.min(MAX_QTY, (prev ? prev.qty : 0) + qty) });
    }
    return Array.from(merged.values()).slice(0, MAX_LINES);
  };

  const getCart = () => sanitizeCart(store.read(CART_KEY, []));
  const saveCart = (cart) => { store.write(CART_KEY, cart); renderCounts(); };
  const cartCount = (cart = getCart()) => cart.reduce((n, it) => n + it.qty, 0);

  const addToCart = (id, size, qty) => {
    const cart = getCart();
    const line = cart.find((it) => it.id === id && it.size === size);
    const existing = line ? line.qty : 0;
    if (!line && cart.length >= MAX_LINES) return { ok: false, reason: "Your bag is full. Remove an item to add another." };
    if (existing >= MAX_QTY) return { ok: false, reason: `You can add up to ${MAX_QTY} of the same item.` };
    const next = Math.min(MAX_QTY, existing + qty);
    if (line) line.qty = next; else cart.push({ id, size, qty: next });
    saveCart(cart);
    return { ok: true, capped: existing + qty > MAX_QTY };
  };

  const shippingFor = (subtotal) => (subtotal <= 0 || subtotal >= FREE_SHIP ? 0 : FLAT_SHIP);

  /* ---------- Wishlist model ---------- */
  const getWish = () => {
    const raw = store.read(WISH_KEY, []);
    return Array.isArray(raw) ? raw.filter((s) => typeof s === "string") : [];
  };
  const toggleWish = (slug) => {
    const list = getWish();
    const i = list.indexOf(slug);
    if (i >= 0) list.splice(i, 1); else list.push(slug);
    store.write(WISH_KEY, list);
    renderCounts();
    syncWishButtons();
    return i < 0;
  };

  /* ---------- Toasts ---------- */
  const toastRegion = $("#toasts");
  const toast = (message, { href, linkText, kind = "ok", ms = 3600 } = {}) => {
    if (!toastRegion) return;
    const el = document.createElement("div");
    el.className = "toast toast-" + kind + " is-entering";
    el.setAttribute("role", "status");
    el.append(document.createTextNode(message));
    if (href) {
      const a = document.createElement("a");
      a.href = href;
      a.textContent = linkText || "View";
      el.append(a);
    }
    toastRegion.append(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove("is-entering")));
    setTimeout(() => dismissToast(el), ms);
  };
  const dismissToast = (el) => {
    el.classList.add("is-leaving");
    setTimeout(() => el.remove(), 350);
  };
  $$(".toast", toastRegion || document).forEach((el) => setTimeout(() => dismissToast(el), 6000));

  /* ---------- Header counts ---------- */
  function renderCounts() {
    const n = cartCount();
    const w = getWish().length;
    const cartBadge = $("[data-cart-count]");
    const cartLink = $("[data-cart-link]");
    if (cartBadge) { cartBadge.textContent = n > 99 ? "99+" : String(n); cartBadge.hidden = n === 0; }
    if (cartLink) cartLink.setAttribute("aria-label", `Shopping bag, ${n} ${n === 1 ? "item" : "items"}`);
    const wishBadge = $("[data-wish-count]");
    const wishLink = $("[data-wish-link]");
    if (wishBadge) { wishBadge.textContent = String(w); wishBadge.hidden = w === 0; }
    if (wishLink) wishLink.setAttribute("aria-label", `Wishlist, ${w} ${w === 1 ? "item" : "items"}`);
  }

  /* ---------- Navigation + search toggles ---------- */
  const nav = $("#site-nav");
  const navToggle = $(".nav-toggle");
  const searchForm = $("#site-search-form");
  const searchToggle = $(".search-toggle");
  const desktop = window.matchMedia("(min-width: 900px)");

  const setNav = (open) => {
    if (!nav || !navToggle) return;
    nav.classList.toggle("is-open", open);
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  };
  const setSearch = (open, focus = false) => {
    if (!searchForm || !searchToggle) return;
    searchForm.classList.toggle("is-open", open);
    searchToggle.setAttribute("aria-expanded", String(open));
    searchToggle.setAttribute("aria-label", open ? "Close search" : "Open search");
    if (open && focus) $("input", searchForm).focus();
  };
  if (navToggle) navToggle.addEventListener("click", () => { const open = navToggle.getAttribute("aria-expanded") !== "true"; setNav(open); if (open) setSearch(false); });
  if (searchToggle) searchToggle.addEventListener("click", () => { const open = searchToggle.getAttribute("aria-expanded") !== "true"; setSearch(open, true); if (open) setNav(false); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (nav && nav.classList.contains("is-open")) { setNav(false); navToggle.focus(); }
    else if (searchForm && searchForm.classList.contains("is-open")) { setSearch(false); searchToggle.focus(); }
  });
  const onBreakpoint = () => { if (desktop.matches) { setNav(false); setSearch(false); } };
  if (desktop.addEventListener) desktop.addEventListener("change", onBreakpoint); else desktop.addListener(onBreakpoint);

  /* ---------- Product cards: sizes, quick add, wishlist ---------- */
  function syncWishButtons() {
    const list = getWish();
    $$("[data-wish]").forEach((btn) => {
      const slug = btn.dataset.wish;
      const on = list.includes(slug);
      btn.setAttribute("aria-pressed", String(on));
      const card = btn.closest("[data-product]");
      const name = card && $(".card-title a", card) ? $(".card-title a", card).textContent.trim() : "this shoe";
      if (btn.classList.contains("wish")) {
        btn.setAttribute("aria-label", `${on ? "Remove" : "Add"} ${name} ${on ? "from" : "to"} wishlist`);
      }
      const label = $("[data-wish-label]", btn);
      if (label) label.textContent = on ? "Saved" : "Wishlist";
    });
  }

  document.addEventListener("click", (e) => {
    const target = e.target instanceof Element ? e.target : null;
    if (!target) return;

    const wishBtn = target.closest("[data-wish]");
    if (wishBtn) {
      const added = toggleWish(wishBtn.dataset.wish);
      if (body.classList.contains("page-wishlist")) renderWishlistPage();
      toast(added ? "Saved to your wishlist." : "Removed from your wishlist.");
      return;
    }

    const sizeBtn = target.closest(".card .size");
    if (sizeBtn) {
      const card = sizeBtn.closest(".card");
      const pressed = sizeBtn.getAttribute("aria-pressed") === "true";
      $$(".size", card).forEach((b) => b.setAttribute("aria-pressed", "false"));
      sizeBtn.setAttribute("aria-pressed", String(!pressed));
      const msg = $(".card-msg", card);
      msg.textContent = ""; msg.className = "card-msg";
      return;
    }

    const quick = target.closest("[data-quick-add]");
    if (quick) {
      const card = quick.closest(".card");
      const msg = $(".card-msg", card);
      const chosen = $(".size[aria-pressed='true']", card);
      if (!chosen) {
        msg.textContent = "Please select a size first.";
        msg.className = "card-msg is-error";
        const first = $(".size", card);
        if (first) first.focus();
        return;
      }
      const result = addToCart(card.dataset.product, Number(chosen.dataset.size), 1);
      if (!result.ok) { msg.textContent = result.reason; msg.className = "card-msg is-error"; return; }
      msg.textContent = "Added to your bag.";
      msg.className = "card-msg is-ok";
      toast(`Added size UK ${chosen.dataset.size} to your bag.`, { href: "/cart", linkText: "View bag" });
      setTimeout(() => { if (msg.textContent === "Added to your bag.") { msg.textContent = ""; msg.className = "card-msg"; } }, 2500);
    }
  });

  /* ---------- Product detail page ---------- */
  const detail = $("[data-detail]");
  if (detail) {
    const mainImg = $("#gallery-main");
    $$("[data-thumb]", detail).forEach((btn) => {
      btn.addEventListener("click", () => {
        mainImg.src = btn.dataset.src;
        mainImg.alt = btn.dataset.alt;
        $$("[data-thumb]", detail).forEach((b) => b.setAttribute("aria-current", "false"));
        btn.setAttribute("aria-current", "true");
      });
    });

    const qtyInput = $("[data-qty-input]", detail);
    const clampQty = () => {
      let v = parseInt(qtyInput.value, 10);
      if (!Number.isFinite(v) || v < 1) v = 1;
      qtyInput.value = String(Math.min(MAX_QTY, v));
      return Number(qtyInput.value);
    };
    $("[data-qty-dec]", detail).addEventListener("click", () => { qtyInput.value = String(clampQty() - 1); clampQty(); });
    $("[data-qty-inc]", detail).addEventListener("click", () => { qtyInput.value = String(clampQty() + 1); clampQty(); });
    qtyInput.addEventListener("change", clampQty);

    const msg = $("[data-detail-msg]", detail);
    const picker = $(".size-picker", detail);
    $$("[data-size-input]", detail).forEach((r) => r.addEventListener("change", () => {
      picker.classList.remove("has-error");
      msg.textContent = ""; msg.className = "form-msg";
    }));

    $("[data-add-detail]", detail).addEventListener("click", () => {
      const checked = $("[data-size-input]:checked", detail);
      if (!checked) {
        picker.classList.add("has-error");
        msg.textContent = "Please select a size to continue.";
        msg.className = "form-msg is-error";
        $("[data-size-input]", detail).focus();
        return;
      }
      const qty = clampQty();
      const result = addToCart(detail.dataset.product, Number(checked.value), qty);
      if (!result.ok) { msg.textContent = result.reason; msg.className = "form-msg is-error"; return; }
      msg.textContent = result.capped
        ? `Added. Your bag is capped at ${MAX_QTY} per item.`
        : `Added ${qty} × size UK ${checked.value} to your bag.`;
      msg.className = "form-msg is-ok";
      toast("Added to your bag.", { href: "/cart", linkText: "View bag" });
    });
  }

  /* ---------- Cart page ---------- */
  const cartPage = $("[data-cart-page]");
  function renderTotals(root, cart) {
    const subtotal = cart.reduce((s, it) => s + catalog[it.id].price * it.qty, 0);
    const shipping = shippingFor(subtotal);
    $("[data-subtotal]", root).textContent = inr(subtotal);
    $("[data-shipping]", root).textContent = shipping === 0 ? "Free" : inr(shipping);
    $("[data-total]", root).textContent = inr(subtotal + shipping);
    return { subtotal, shipping };
  }

  function renderCartPage() {
    if (!cartPage || !catalog) return;
    const cart = getCart();
    const empty = $("[data-cart-empty]", cartPage);
    const content = $("[data-cart-content]", cartPage);
    if (cart.length !== (store.read(CART_KEY, []) || []).length) store.write(CART_KEY, cart);
    empty.hidden = cart.length > 0;
    content.hidden = cart.length === 0;
    renderCounts();
    if (!cart.length) return;

    const list = $("[data-cart-list]", cartPage);
    const tpl = $("#cart-item-tpl");
    list.textContent = "";
    for (const it of cart) {
      const p = catalog[it.id];
      const li = tpl.content.firstElementChild.cloneNode(true);
      li.dataset.id = it.id; li.dataset.size = String(it.size);
      $$("[data-link]", li).forEach((a) => { a.href = p.url; });
      $("[data-name]", li).textContent = p.name;
      const img = $("img", li); img.src = p.image;
      $("[data-meta]", li).textContent = `${p.category} · Size UK ${it.size}`;
      $("[data-unit]", li).textContent = inr(p.price) + " each";
      $("[data-qty]", li).textContent = String(it.qty);
      $("[data-dec]", li).setAttribute("aria-label", it.qty === 1 ? `Remove ${p.name}` : `Decrease quantity of ${p.name}`);
      $("[data-inc]", li).setAttribute("aria-label", `Increase quantity of ${p.name}`);
      $("[data-inc]", li).disabled = it.qty >= MAX_QTY;
      $("[data-line]", li).textContent = inr(p.price * it.qty);
      $("[data-remove]", li).setAttribute("aria-label", `Remove ${p.name}, size ${it.size}, from bag`);
      list.append(li);
    }
    const { subtotal, shipping } = renderTotals(cartPage, cart);
    const note = $("[data-ship-note]", cartPage);
    const bar = $("[data-ship-progress]", cartPage);
    bar.value = Math.min(subtotal, FREE_SHIP);
    note.textContent = shipping === 0
      ? "You've unlocked free shipping."
      : `Add ${inr(FREE_SHIP - subtotal)} more for free shipping.`;
  }

  if (cartPage) {
    cartPage.addEventListener("click", (e) => {
      const target = e.target instanceof Element ? e.target : null;
      const li = target && target.closest(".cart-item");
      if (!li) return;
      const cart = getCart();
      const idx = cart.findIndex((it) => it.id === li.dataset.id && it.size === Number(li.dataset.size));
      if (idx < 0) return;
      const name = catalog[cart[idx].id].name;
      const focusKey = li.dataset.id + "|" + li.dataset.size;
      let focusAction = null;
      if (target.closest("[data-inc]")) { cart[idx].qty = Math.min(MAX_QTY, cart[idx].qty + 1); focusAction = "[data-inc]"; }
      else if (target.closest("[data-dec]")) {
        if (cart[idx].qty <= 1) { cart.splice(idx, 1); toast(`Removed ${name}.`); }
        else { cart[idx].qty -= 1; focusAction = "[data-dec]"; }
      } else if (target.closest("[data-remove]")) { cart.splice(idx, 1); toast(`Removed ${name}.`); }
      else return;
      saveCart(cart);
      renderCartPage();
      const again = focusAction && $$(".cart-item", cartPage).find((n) => n.dataset.id + "|" + n.dataset.size === focusKey);
      const control = again && $(focusAction, again);
      if (control && !control.disabled) control.focus();
      else if (!cart.length) $("[data-cart-empty] a", cartPage).focus();
    });
    renderCartPage();
  }

  /* ---------- Checkout page ---------- */
  const checkoutPage = $("[data-checkout-page]");
  const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$/;
  const rules = {
    name: (v) => (/^[\p{L}][\p{L} .'\-]{1,79}$/u.test(v) ? "" : "Enter your full name (letters only)."),
    email: (v) => (EMAIL_RE.test(v) ? "" : "Enter a valid email address."),
    phone: (v) => {
      let d = v.replace(/[\s\-().]/g, "").replace(/^\+/, "");
      if (d.length === 12 && d.startsWith("91")) d = d.slice(2);
      else if (d.length === 11 && d.startsWith("0")) d = d.slice(1);
      return /^[6-9]\d{9}$/.test(d) ? "" : "Enter a valid 10-digit Indian mobile number.";
    },
    address: (v) => (v.length >= 5 && v.length <= 200 ? "" : "Enter your shipping address (5-200 characters)."),
    city: (v) => (/^[\p{L}][\p{L} .'\-]{1,59}$/u.test(v) ? "" : "Enter a valid city name."),
    pin: (v) => (/^[1-9]\d{5}$/.test(v) ? "" : "Enter a valid 6-digit PIN code."),
    message: (v) => (v.length >= 10 && v.length <= 2000 ? "" : "Your message should be 10-2000 characters."),
  };
  const setFieldError = (input, message) => {
    const wrap = input.closest(".field");
    const err = $("#err-" + input.dataset.field, wrap) || $(".field-error", wrap);
    if (err) err.textContent = message;
    wrap.classList.toggle("has-error", Boolean(message));
    if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
  };
  const validateForm = (form) => {
    let firstBad = null;
    $$("[data-field]", form).forEach((input) => {
      const rule = rules[input.dataset.field];
      if (!rule) return;
      const message = rule(input.value.trim());
      setFieldError(input, message);
      if (message && !firstBad) firstBad = input;
    });
    return firstBad;
  };
  const liveValidate = (form) => {
    $$("[data-field]", form).forEach((input) => {
      input.addEventListener("blur", () => {
        if (input.value.trim() === "" && !input.closest(".has-error")) return;
        const rule = rules[input.dataset.field];
        if (rule) setFieldError(input, rule(input.value.trim()));
      });
      input.addEventListener("input", () => {
        if (input.closest(".has-error")) {
          const rule = rules[input.dataset.field];
          if (rule) setFieldError(input, rule(input.value.trim()));
        }
      });
    });
  };

  if (checkoutPage && catalog) {
    const cart = getCart();
    const form = $("[data-checkout-form]", checkoutPage);
    const list = $("[data-sum-list]", checkoutPage);
    const tpl = $("#sum-item-tpl");
    const emptyNote = $("[data-summary-empty]", checkoutPage);
    const placeBtn = $("[data-place-order]", form);
    const formMsg = $("[data-form-msg]", form);

    if (!cart.length) {
      emptyNote.hidden = false;
      placeBtn.disabled = true;
      formMsg.textContent = "Your bag is empty. Add a pair before checking out.";
      formMsg.className = "form-msg is-error";
    }
    for (const it of cart) {
      const p = catalog[it.id];
      const li = tpl.content.firstElementChild.cloneNode(true);
      $("img", li).src = p.image;
      $("[data-name]", li).textContent = p.name;
      $("[data-meta]", li).textContent = `Size UK ${it.size} · Qty ${it.qty}`;
      $("[data-line]", li).textContent = inr(p.price * it.qty);
      list.append(li);
    }
    if (cart.length) renderTotals(checkoutPage, cart);
    else { $("[data-subtotal]", checkoutPage).textContent = inr(0); $("[data-shipping]", checkoutPage).textContent = inr(0); $("[data-total]", checkoutPage).textContent = inr(0); }

    liveValidate(form);
    form.addEventListener("submit", (e) => {
      const current = getCart();
      if (!current.length) { e.preventDefault(); formMsg.textContent = "Your bag is empty."; formMsg.className = "form-msg is-error"; return; }
      const bad = validateForm(form);
      if (bad) {
        e.preventDefault();
        formMsg.textContent = "Please fix the highlighted fields.";
        formMsg.className = "form-msg is-error";
        bad.focus();
        return;
      }
      $("[data-cart-field]", form).value = JSON.stringify(current.map(({ id, size, qty }) => ({ id, size, qty })));
      placeBtn.disabled = true;
      placeBtn.textContent = "PLACING ORDER…";
    });
    // Back/forward cache can restore a disabled button.
    window.addEventListener("pageshow", () => { if (cart.length) { placeBtn.disabled = false; placeBtn.textContent = "PLACE DEMO ORDER"; } });

    const firstServerError = $(".field.has-error input", form);
    if (firstServerError) firstServerError.focus();
  }

  /* ---------- Contact form ---------- */
  const contactForm = $("[data-contact-form]");
  if (contactForm) {
    liveValidate(contactForm);
    contactForm.addEventListener("submit", (e) => {
      const bad = validateForm(contactForm);
      if (bad) { e.preventDefault(); bad.focus(); }
    });
    const firstServerError = $(".field.has-error input, .field.has-error textarea", contactForm);
    if (firstServerError) firstServerError.focus();
  }

  /* ---------- Order success: clear the bag once ---------- */
  if ($("[data-clear-cart]")) { store.remove(CART_KEY); renderCounts(); }

  /* ---------- Wishlist page ---------- */
  function renderWishlistPage() {
    const page = $("[data-wishlist-page]");
    if (!page) return;
    const list = getWish();
    let shown = 0;
    $$("[data-product]", $("[data-wish-grid]", page)).forEach((card) => {
      const on = list.includes(card.dataset.product);
      card.hidden = !on;
      if (on) shown += 1;
    });
    $("[data-wish-empty]", page).hidden = shown > 0;
    $("[data-wish-grid]", page).hidden = shown === 0;
    const summary = $("[data-wish-summary]");
    if (summary) summary.textContent = shown ? `${shown} saved ${shown === 1 ? "style" : "styles"} on this device.` : "Saved on this device.";
  }

  /* ---------- Newsletter ---------- */
  const news = $("[data-newsletter]");
  if (news) {
    const input = $("input[type=email]", news);
    const msg = $(".form-msg", news);
    const button = $("button[type=submit]", news);
    const show = (text, ok) => { msg.textContent = text; msg.className = "form-msg " + (ok ? "is-ok" : "is-error"); input.setAttribute("aria-invalid", ok ? "false" : "true"); };
    news.addEventListener("submit", async (e) => {
      const value = input.value.trim();
      if (!EMAIL_RE.test(value)) { e.preventDefault(); show("Please enter a valid email address.", false); input.focus(); return; }
      if (!window.fetch) return; // fall back to a normal POST
      e.preventDefault();
      button.disabled = true;
      try {
        const res = await fetch(news.action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch", "X-CSRF-Token": $("meta[name=csrf-token]").content },
          body: new FormData(news),
          credentials: "same-origin",
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) { show(data.message, true); input.value = ""; }
        else show(data.message || "Something went wrong. Please try again.", false);
      } catch (_) {
        show("Network error. Please try again.", false);
      } finally {
        button.disabled = false;
      }
    });
    input.addEventListener("input", () => { if (msg.classList.contains("is-error")) { msg.textContent = ""; msg.className = "form-msg"; input.removeAttribute("aria-invalid"); } });
  }

  /* ---------- Scroll reveal (below-the-fold only; content is visible without JS) ---------- */
  if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const targets = $$(".section .tech-card, .section .review, .section .value, .campaign-grid figure, .story-grid > *");
    const fold = window.innerHeight;
    const io = new IntersectionObserver((entries) => {
      for (const en of entries) if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    targets.forEach((el) => {
      if (el.getBoundingClientRect().top > fold) { el.classList.add("reveal"); io.observe(el); }
    });
  }

  /* ---------- Cross-tab sync + bfcache ---------- */
  window.addEventListener("storage", (e) => {
    if (e.key !== CART_KEY && e.key !== WISH_KEY) return;
    renderCounts(); syncWishButtons();
    if (cartPage) renderCartPage();
    renderWishlistPage();
  });
  window.addEventListener("pageshow", (e) => { if (e.persisted) { renderCounts(); syncWishButtons(); if (cartPage) renderCartPage(); } });

  /* ---------- Init ---------- */
  renderCounts();
  syncWishButtons();
  renderWishlistPage();
})();
