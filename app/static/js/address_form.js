let currentStep = 1;
const totalSteps = 5;
let map = null;
let marker = null;

function showStep(step) {
  step = parseInt(step, 10);
  if (isNaN(step) || step < 1 || step > totalSteps) {
    step = 1;
  }
  currentStep = step;
  for (let i = 1; i <= totalSteps; i++) {
    const el = document.getElementById(`step-${i}`);
    const indicator = document.getElementById(`indicator-step-${i}`);
    if (el) {
      el.style.display = (i === step) ? "block" : "none";
    }
    if (indicator) {
      indicator.classList.remove("active", "completed");
      if (i === step) indicator.classList.add("active");
      else if (i < step) indicator.classList.add("completed");
    }
  }
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (step === 3) {
    setTimeout(initAddressMap, 150);
  }

  if (step === 5) {
    populateReview();
  }
}

function initAddressMap() {
  const container = document.getElementById("address-map-picker");
  if (!container) return;

  const latInput = document.getElementById("latitude");
  const lngInput = document.getElementById("longitude");
  let currentLat = latInput && latInput.value ? parseFloat(latInput.value) : null;
  let currentLng = lngInput && lngInput.value ? parseFloat(lngInput.value) : null;

  const defaultLat = 30.3753; // Regional default
  const defaultLng = 69.3451;
  const initialLat = (currentLat && !isNaN(currentLat)) ? currentLat : defaultLat;
  const initialLng = (currentLng && !isNaN(currentLng)) ? currentLng : defaultLng;
  const initialZoom = (currentLat && !isNaN(currentLat)) ? 15 : 6;

  if (typeof window.L === "undefined") {
    // If Leaflet is still loading from CDN, retry shortly
    setTimeout(initAddressMap, 300);
    return;
  }

  if (!map) {
    const placeholder = document.getElementById("map-loading-placeholder");
    if (placeholder) placeholder.style.display = "none";

    map = L.map("address-map-picker", { zoomControl: true }).setView([initialLat, initialLng], initialZoom);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
    }).addTo(map);

    if (currentLat && currentLng && !isNaN(currentLat) && !isNaN(currentLng)) {
      placeMarker(currentLat, currentLng, false);
    }

    map.on("click", (e) => {
      placeMarker(e.latlng.lat, e.latlng.lng, true);
    });
  } else {
    setTimeout(() => { map.invalidateSize(); }, 150);
  }
}

function placeMarker(lat, lng, centerMap = true) {
  const fixedLat = parseFloat(lat).toFixed(6);
  const fixedLng = parseFloat(lng).toFixed(6);

  const latInput = document.getElementById("latitude");
  const lngInput = document.getElementById("longitude");
  if (latInput) latInput.value = fixedLat;
  if (lngInput) lngInput.value = fixedLng;

  updatePinnedPreview(fixedLat, fixedLng);

  if (!map) return;

  if (!marker) {
    marker = L.marker([fixedLat, fixedLng], { draggable: true }).addTo(map);
    marker.on("dragend", (e) => {
      const pos = e.target.getLatLng();
      placeMarker(pos.lat, pos.lng, false);
    });
  } else {
    marker.setLatLng([fixedLat, fixedLng]);
  }

  if (centerMap) {
    map.setView([fixedLat, fixedLng], Math.max(map.getZoom(), 15));
  }
}

function updatePinnedPreview(lat, lng) {
  const display = document.getElementById("pinned-coords-display");
  const linksBox = document.getElementById("google-maps-preview-links");
  const viewLink = document.getElementById("link-gmaps-view");
  const dirLink = document.getElementById("link-gmaps-directions");

  if (display) {
    display.textContent = `${lat}, ${lng}`;
  }
  if (linksBox) {
    linksBox.style.display = "inline-flex";
  }
  if (viewLink) {
    viewLink.href = `https://www.google.com/maps?q=${lat},${lng}`;
  }
  if (dirLink) {
    dirLink.href = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
  }
}

function onCoordInputChange() {
  const latVal = parseFloat(document.getElementById("latitude").value);
  const lngVal = parseFloat(document.getElementById("longitude").value);
  if (!isNaN(latVal) && !isNaN(lngVal) && latVal >= -90 && latVal <= 90 && lngVal >= -180 && lngVal <= 180) {
    placeMarker(latVal, lngVal, true);
  }
}

function nextStep() {
  if (typeof currentStep === "undefined" || !currentStep) {
    currentStep = 1;
  }
  if (validateCurrentStep()) {
    if (currentStep < totalSteps) {
      showStep(currentStep + 1);
    }
  }
}

function prevStep() {
  if (typeof currentStep === "undefined" || !currentStep) {
    currentStep = 1;
  }
  if (currentStep > 1) {
    showStep(currentStep - 1);
  }
}

function goToStep(step) {
  step = parseInt(step, 10);
  if (!isNaN(step) && step >= 1 && step <= totalSteps) {
    showStep(step);
  }
}

function validateCurrentStep() {
  if (currentStep === 1) {
    const addressType = document.getElementById("address_type") ? document.getElementById("address_type").value : "PERSONAL";
    if (addressType === "BUSINESS") {
      const bizName = document.getElementById("business_name");
      if (!bizName || !bizName.value.trim()) {
        if (typeof showToast === "function") {
          showToast("Please enter Business / Company Name.", "error");
        } else {
          alert("Please enter Business / Company Name.");
        }
        if (bizName) bizName.focus();
        return false;
      }
    }
    const recipient = document.getElementById("recipient_name");
    if (!recipient || !recipient.value.trim()) {
      if (typeof showToast === "function") {
        showToast("Please enter Contact Person Name (Compulsory).", "error");
      } else {
        alert("Please enter Contact Person Name (Compulsory).");
      }
      if (recipient) recipient.focus();
      return false;
    }
    return true;
  }
  if (currentStep === 2) {
    const city = document.getElementById("city");
    if (!city || !city.value.trim()) {
      if (typeof showToast === "function") {
        showToast("Please enter a city.", "error");
      } else {
        alert("Please enter a city.");
      }
      if (city) city.focus();
      return false;
    }
  }
  return true;
}

function toggleLocationScope(scope) {
  const localFields = document.getElementById("local-specific-fields");
  const localCard = document.getElementById("scope-local-card");
  const intlCard = document.getElementById("scope-intl-card");
  const badgeLocal = document.getElementById("badge-local");
  const badgeIntl = document.getElementById("badge-intl");
  const scopeInput = document.getElementById("location_scope");

  if (scopeInput) scopeInput.value = scope;

  const checkSvg = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="margin-right: 4px;"><polyline points="20 6 9 17 4 12"></polyline></svg>';

  if (scope === "LOCAL") {
    if (localFields) localFields.style.display = "grid";
    if (localCard) {
      localCard.classList.add("reach-card-active");
      localCard.classList.remove("reach-card-inactive");
    }
    if (intlCard) {
      intlCard.classList.remove("reach-card-active");
      intlCard.classList.add("reach-card-inactive");
    }
    if (badgeLocal) {
      badgeLocal.className = "reach-badge badge-active";
      badgeLocal.innerHTML = checkSvg + 'ACTIVE';
    }
    if (badgeIntl) {
      badgeIntl.className = "reach-badge badge-inactive";
      badgeIntl.textContent = 'INACTIVE';
    }
  } else {
    if (localFields) localFields.style.display = "none";
    if (intlCard) {
      intlCard.classList.add("reach-card-active");
      intlCard.classList.remove("reach-card-inactive");
    }
    if (localCard) {
      localCard.classList.remove("reach-card-active");
      localCard.classList.add("reach-card-inactive");
    }
    if (badgeIntl) {
      badgeIntl.className = "reach-badge badge-active";
      badgeIntl.innerHTML = checkSvg + 'ACTIVE';
    }
    if (badgeLocal) {
      badgeLocal.className = "reach-badge badge-inactive";
      badgeLocal.textContent = 'INACTIVE';
    }
  }
}

function selectAddressType(type) {
  const typeInput = document.getElementById("address_type");
  if (typeInput) typeInput.value = type;
}

function setRedirectDelay(seconds) {
  const input = document.getElementById("redirect_seconds");
  if (input) input.value = seconds;

  document.querySelectorAll(".delay-chip").forEach(chip => {
    chip.classList.remove("selected");
    if (chip.getAttribute("data-seconds") == seconds) {
      chip.classList.add("selected");
    }
  });
}

function fetchCurrentGps() {
  if (!navigator.geolocation) {
    showToast("Geolocation is not supported by your browser.", "error");
    return;
  }

  showToast("Fetching GPS coordinates...", "info");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude.toFixed(6);
      const lng = pos.coords.longitude.toFixed(6);
      placeMarker(lat, lng, true);
      showToast(`Location acquired: ${lat}, ${lng}`, "success");
    },
    (err) => {
      showToast("Unable to retrieve location: " + err.message, "error");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

function populateReview() {
  const getVal = (id) => (document.getElementById(id) ? document.getElementById(id).value : "") || "—";
  
  const revType = document.getElementById("rev-type");
  const revBizRow = document.getElementById("rev-biz-row");
  const revBizName = document.getElementById("rev-bizname");
  const revScope = document.getElementById("rev-scope");
  const revRecipient = document.getElementById("rev-recipient");
  const revCity = document.getElementById("rev-city");
  const revCountry = document.getElementById("rev-country");
  const revHouseStreet = document.getElementById("rev-housestreet");
  const revDestination = document.getElementById("rev-destination");
  const revDelay = document.getElementById("rev-delay");

  const typeVal = getVal("address_type");
  if (revType) {
    revType.textContent = typeVal === "BUSINESS" ? "🏢 Business Address" : "👤 Personal Address";
  }
  if (revBizRow && revBizName) {
    if (typeVal === "BUSINESS") {
      revBizRow.style.display = "block";
      revBizName.textContent = getVal("business_name");
    } else {
      revBizRow.style.display = "none";
    }
  }

  if (revScope) {
    const scopeVal = getVal("location_scope");
    revScope.textContent = scopeVal === "LOCAL" ? "🛵 Local City Delivery" : "🌍 Out of City / Worldwide";
  }
  if (revRecipient) revRecipient.textContent = getVal("recipient_name");
  if (revCity) revCity.textContent = getVal("city");
  if (revCountry) revCountry.textContent = getVal("country");

  const house = getVal("house_number");
  const street = getVal("street");
  const landmark = getVal("landmark");
  if (revHouseStreet) {
    revHouseStreet.textContent = [house !== "—" ? `House ${house}` : "", street !== "—" ? street : "", landmark !== "—" ? `Near ${landmark}` : ""].filter(Boolean).join(", ") || "—";
  }
  if (revDestination) revDestination.textContent = getVal("destination_url");
  if (revDelay) revDelay.textContent = `${getVal("redirect_seconds")} seconds`;
}

// Global window exposure to guarantee accessibility across all inline events
window.currentStep = currentStep;
window.totalSteps = totalSteps;
window.showStep = showStep;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.goToStep = goToStep;
window.toggleLocationScope = toggleLocationScope;
window.setRedirectDelay = setRedirectDelay;
window.fetchCurrentGps = fetchCurrentGps;
window.populateReview = populateReview;

// Initialize on page load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => showStep(1));
} else {
  showStep(1);
}
