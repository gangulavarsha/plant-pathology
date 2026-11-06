// Image preview on the Predict page
const file = document.getElementById("imageInput"), prev = document.getElementById("preview");
if (file) file.addEventListener("change", () => {
  const f = file.files[0]; if (!f) return;
  prev.src = URL.createObjectURL(f); prev.style.display = "inline-block";
});
// Loading state on forms
document.querySelectorAll("form[data-loading]").forEach(f => f.addEventListener("submit", () => {
  const b = f.querySelector("button"); b.disabled = true; b.textContent = "Analysing...";
}));
// Confirm dangerous actions
document.querySelectorAll("[data-confirm]").forEach(a => a.addEventListener("click", e => {
  if (!confirm(a.dataset.confirm)) e.preventDefault();
}));
// Auto-hide flash messages
setTimeout(() => document.querySelectorAll(".flash").forEach(f => f.style.display = "none"), 5000);
