"use strict";

const tabs = [...document.querySelectorAll('[role="tab"]')];
const panels = [...document.querySelectorAll(".code-panel")];
const copyButton = document.querySelector(".copy-button");
const copyStatus = document.querySelector("#copy-status");
let activePanel = panels[0];
let feedbackTimer;

function selectTab(tab, focus = false) {
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
  }
  for (const panel of panels) {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls");
    if (!panel.hidden) activePanel = panel;
  }
  clearTimeout(feedbackTimer);
  copyButton.textContent = "Copy code";
  copyStatus.textContent = "";
  if (focus) tab.focus();
}

for (const tab of tabs) {
  const panel = document.getElementById(tab.getAttribute("aria-controls"));
  panel.setAttribute("role", "tabpanel");
  panel.setAttribute("aria-labelledby", tab.id);
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (event) => {
    const current = tabs.indexOf(tab);
    let next;
    if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    selectTab(tabs[next], true);
  });
}

selectTab(tabs[0]);
document.querySelector(".code-tabs").hidden = false;

// Browsers may deny clipboard access; keep the source selectable either way.
if (navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    const code = activePanel.querySelector("code").textContent;
    copyButton.disabled = true;
    try {
      await navigator.clipboard.writeText(code);
      copyButton.textContent = "Copied";
      copyStatus.textContent = "Source excerpt copied to clipboard.";
    } catch {
      copyButton.textContent = "Select to copy";
      copyStatus.textContent = "Clipboard unavailable. Select the code and copy it manually.";
    } finally {
      copyButton.disabled = false;
      feedbackTimer = setTimeout(() => { copyButton.textContent = "Copy code"; }, 2500);
    }
  });
}
