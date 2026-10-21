// Copy text to the clipboard. navigator.clipboard only exists on https (and localhost), but schools
// often open TatvaX at a plain http address on their network, so fall back to a hidden text box.
export async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch { /* permission refused: try the fallback */ }
  }
  const box = document.createElement("textarea");
  box.value = text;
  box.setAttribute("readonly", "");
  box.style.position = "fixed";
  box.style.opacity = "0";
  document.body.appendChild(box);
  box.select();
  try {
    if (!document.execCommand("copy")) throw new Error("Copying isn't allowed in this browser.");
  } finally {
    box.remove();
  }
}
