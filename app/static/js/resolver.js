document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("resolver-data");
  if (!container) return;

  const addressText = container.getAttribute("data-address") || "";
  const destinationUrl = container.getAttribute("data-destination") || "";
  let remainingSeconds = parseInt(container.getAttribute("data-delay") || "3", 10);

  const copyStatusCard = document.getElementById("copy-status-card");
  const manualCopyBtn = document.getElementById("btn-manual-copy");
  const countdownNumber = document.getElementById("countdown-number");
  const countdownBox = document.getElementById("countdown-box");
  const iconCircle = document.getElementById("resolver-icon-circle");
  const drivingNavCard = document.getElementById("driving-nav-card");

  let countdownInterval = null;

  function startCountdown() {
    if (!destinationUrl) {
      if (countdownBox) countdownBox.style.display = "none";
      return;
    }

    if (countdownNumber) countdownNumber.textContent = remainingSeconds;

    countdownInterval = setInterval(() => {
      remainingSeconds -= 1;
      if (countdownNumber) countdownNumber.textContent = remainingSeconds;

      if (remainingSeconds <= 0) {
        clearInterval(countdownInterval);
        // Safe redirect
        window.location.href = destinationUrl;
      }
    }, 1000);
  }

  function handleCopySuccess() {
    if (manualCopyBtn) manualCopyBtn.classList.remove("visible");
    if (copyStatusCard) copyStatusCard.classList.add("visible");
    if (iconCircle) iconCircle.classList.add("success");
    if (drivingNavCard) drivingNavCard.classList.add("copied-active");
    startCountdown();
  }

  function handleCopyFailure() {
    // Show fallback button; do not claim success falsely!
    if (copyStatusCard) copyStatusCard.classList.remove("visible");
    if (manualCopyBtn) {
      manualCopyBtn.classList.add("visible");
      manualCopyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(addressText).then(() => {
          handleCopySuccess();
        }).catch(() => {
          // Fallback textarea execCommand
          const ta = document.createElement("textarea");
          ta.value = addressText;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          handleCopySuccess();
        });
      });
    }
    // Also start countdown anyway so visitor is not stuck forever if they don't want to copy
    startCountdown();
  }

  // Attempt automatic clipboard copy
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(addressText)
      .then(handleCopySuccess)
      .catch(handleCopyFailure);
  } else {
    // Insecure context or unsupported
    handleCopyFailure();
  }
});
