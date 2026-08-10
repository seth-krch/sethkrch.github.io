/* ============================================================
   Portfolio behavior + single source of truth for identity.
   Edit CONFIG below to change name / links everywhere at once.
   ============================================================ */

const CONFIG = {
  name:        "Seth Krch",                     // shown big in the hero
  handle:      "krch",                          // small mono logo in the nav
  role:        "Freelance Developer",           // one-line title under the name
  location:    "",                              // e.g. "Austin, TX" — leave "" to hide
  status:      "available for freelance work",  // short status in the eyebrow
  statusLong:  "Available for freelance projects.",
  email:       "sethkrch@gmail.com",
  github:      "https://github.com/sethkrch",
  linkedin:    "",                              // full URL, or leave "" to hide the row

  // Per-project source links. Leave "" to keep the "Source" link disabled.
  repos: {
    "job-collector": "",
    "northstar":     "",
    "search-tool":   "",
  },
};

/* ---------- apply CONFIG to the DOM ---------- */
(function applyConfig() {
  const set = (field, fn) =>
    document.querySelectorAll(`[data-field="${field}"]`).forEach(fn);

  set("name",   el => (el.textContent = CONFIG.name));
  set("handle", el => (el.textContent = CONFIG.handle));
  set("role",   el => (el.textContent = CONFIG.role));
  set("status", el => (el.textContent = CONFIG.status));
  set("status-long", el => (el.textContent = CONFIG.statusLong));
  set("year",   el => (el.textContent = new Date().getFullYear()));

  // Location: hide the eyebrow segment gracefully if empty.
  set("location", el => (el.textContent = CONFIG.location || "remote"));

  // Email
  set("email", el => {
    el.href = `mailto:${CONFIG.email}`;
    const v = el.querySelector(".contact__v");
    if (v) v.textContent = CONFIG.email;
  });

  // GitHub
  set("github", el => {
    el.href = CONFIG.github;
    const v = el.querySelector(".contact__v");
    if (v) v.textContent = CONFIG.github.replace(/^https?:\/\//, "");
  });

  // LinkedIn — enable the row only if a URL is provided.
  set("linkedin", el => {
    if (CONFIG.linkedin) {
      el.href = CONFIG.linkedin;
      el.removeAttribute("data-disabled");
      el.target = "_blank";
      el.rel = "noopener";
      const v = el.querySelector(".contact__v");
      if (v) v.textContent = CONFIG.linkedin.replace(/^https?:\/\//, "");
    }
  });

  // Project source links.
  document.querySelectorAll("[data-repo]").forEach(el => {
    const url = CONFIG.repos[el.getAttribute("data-repo")];
    if (url) {
      el.href = url;
      el.removeAttribute("data-disabled");
      el.target = "_blank";
      el.rel = "noopener";
    }
  });

  // Keep <title> in sync.
  document.title = `${CONFIG.name} — ${CONFIG.role}`;
})();

/* ---------- sticky nav border on scroll ---------- */
const nav = document.getElementById("nav");
const onScroll = () => nav.classList.toggle("is-stuck", window.scrollY > 8);
onScroll();
window.addEventListener("scroll", onScroll, { passive: true });

/* ---------- reveal on scroll ---------- */
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const targets = document.querySelectorAll(".hero, .project, .about, .contact__line, .contact__links, .section__head");

if (reduce || !("IntersectionObserver" in window)) {
  targets.forEach(t => t.classList.add("is-in"));
} else {
  targets.forEach(t => t.classList.add("reveal"));
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
  targets.forEach(t => io.observe(t));
}
