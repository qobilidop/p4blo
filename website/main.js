"use strict";

const walkthrough = document.querySelector("#gateway-walkthrough");
const regions = [...walkthrough.querySelectorAll(".code-step")];
const notes = [...walkthrough.querySelectorAll(".step-note")];
const navigation = walkthrough.querySelector(".step-navigation");
const buttons = [...navigation.querySelectorAll("button")];
const status = document.querySelector("#copy-status");
const mobile = window.matchMedia("(max-width: 1023px)");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let current = -1;
let framePending = false;
let manualUntil = 0;

function activate(index) {
  if (current === index) return;
  current = index;
  regions.forEach((region, i) => region.classList.toggle("active", i === index));
  notes.forEach((note, i) => { note.hidden = i !== index; });
  buttons.forEach((button, i) => {
    if (i === index) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
}

function focalPoint() {
  // Reserve the card's maximum height. Basing this on the active note's height
  // would move the selection boundary whenever a note changes, causing flicker.
  const available = mobile.matches ? window.innerHeight * 0.58 - 32 : window.innerHeight;
  return Math.max(60, available * 0.45);
}

function update() {
  framePending = false;
  const bounds = walkthrough.getBoundingClientRect();
  const focus = focalPoint();
  const visible = bounds.top < focus && bounds.bottom > window.innerHeight * 0.5;
  walkthrough.classList.toggle("in-view", visible);
  if (!visible || performance.now() < manualUntil) return;
  let closest = 0;
  let distance = Infinity;
  regions.forEach((region, i) => {
    const rect = region.getBoundingClientRect();
    // Distance to the region keeps a long block active while it is being read.
    const next = Math.max(rect.top - focus, focus - rect.bottom, 0);
    if (next < distance) { closest = i; distance = next; }
  });
  activate(closest);
}

function scheduleUpdate() {
  if (framePending) return;
  framePending = true;
  window.requestAnimationFrame(update);
}

buttons.forEach((button, index) => {
  button.addEventListener("click", () => {
    activate(index);
    manualUntil = performance.now() + 1200;
    const rect = regions[index].getBoundingClientRect();
    window.scrollTo({
      top: window.scrollY + rect.top - focalPoint() + Math.min(rect.height / 2, 80),
      behavior: reducedMotion.matches ? "instant" : "smooth",
    });
    status.textContent = `Step ${index + 1}: ${notes[index].querySelector("h3").textContent}`;
  });
  button.addEventListener("keydown", (event) => {
    let target;
    if (event.key === "ArrowRight") target = (index + 1) % buttons.length;
    if (event.key === "ArrowLeft") target = (index - 1 + buttons.length) % buttons.length;
    if (event.key === "Home") target = 0;
    if (event.key === "End") target = buttons.length - 1;
    if (target === undefined) return;
    event.preventDefault();
    buttons[target].focus({ preventScroll: true });
    buttons[target].click();
  });
});

for (const event of ["wheel", "touchstart"]) {
  window.addEventListener(event, () => { manualUntil = 0; }, { passive: true });
}
window.addEventListener("scroll", scheduleUpdate, { passive: true });
window.addEventListener("resize", scheduleUpdate);
window.addEventListener("pageshow", scheduleUpdate);
activate(0);
navigation.hidden = false;
walkthrough.classList.add("enhanced");
scheduleUpdate();

const copyButton = walkthrough.querySelector(".copy-button");
let feedbackTimer;
if (navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    clearTimeout(feedbackTimer);
    copyButton.disabled = true;
    try {
      await navigator.clipboard.writeText(document.querySelector("#gateway-source").textContent);
      copyButton.textContent = "Copied";
      status.textContent = "Complete Python source copied to clipboard.";
    } catch {
      copyButton.textContent = "Select to copy";
      status.textContent = "Clipboard unavailable. Select the code or use Download Python source.";
    } finally {
      copyButton.disabled = false;
      feedbackTimer = setTimeout(() => { copyButton.textContent = "Copy source"; }, 2500);
    }
  });
}
