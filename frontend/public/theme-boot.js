// Apply the saved theme before React mounts so there is no flash of the wrong theme.
// Kept as a separate file because the Content-Security-Policy forbids inline scripts.
try {
  var theme = localStorage.getItem("tatvax.theme");
  if (theme && theme !== "system") document.documentElement.setAttribute("data-theme", theme);
} catch (e) {}
