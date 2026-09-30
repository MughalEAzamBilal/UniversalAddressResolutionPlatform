// Global App JavaScript

// Dark Mode Handling
function initTheme() {
  const saved = localStorage.getItem("ua_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("ua_theme", next);
}

// Toast Notifications
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Copy to Clipboard
function copyToClipboard(text, successMsg = "Copied to clipboard!") {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg, "success");
    }).catch(() => {
      legacyCopy(text, successMsg);
    });
  } else {
    legacyCopy(text, successMsg);
  }
}

function legacyCopy(text, successMsg) {
  const el = document.createElement("textarea");
  el.value = text;
  document.body.appendChild(el);
  el.select();
  document.execCommand("copy");
  document.body.removeChild(el);
  showToast(successMsg, "success");
}

// Modal System
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("open");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("open");
}

// Mobile Sidebar
function toggleSidebar() {
  const sidebar = document.querySelector(".sidebar");
  if (sidebar) sidebar.classList.toggle("open");
}

// QR Code generation using public QR API / SVG renderer
function showQrModal(publicId, url) {
  const qrImage = document.getElementById("qr-modal-image");
  const qrTitle = document.getElementById("qr-modal-id");
  const qrUrl = document.getElementById("qr-modal-url");

  if (qrImage) {
    // Generate clean QR image using standard encoded SVG / quickchart API or data url
    qrImage.src = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(url)}`;
  }
  if (qrTitle) qrTitle.textContent = publicId;
  if (qrUrl) qrUrl.textContent = url;

  openModal("qr-modal");
}

// Share Modal
function showShareModal(publicId, url) {
  const input = document.getElementById("share-modal-url");
  if (input) input.value = url;
  openModal("share-modal");
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
});
