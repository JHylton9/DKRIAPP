const STATUS_LABELS = {
  all: "All Issues",
  pending: "Pending",
  down: "Down",
  fixed: "Fixed",
};

const STATUS_CLASS = {
  pending: "issue-marker--pending",
  down: "issue-marker--down",
  fixed: "issue-marker--fixed",
};

let activeStatus = "all";
let map;
let layerGroup;
let allFeatures = [];

function getApiBase() {
  const isLocalPreview = ["127.0.0.1", "localhost"].includes(window.location.hostname)
    && window.location.port
    && window.location.port !== "8080";
  return isLocalPreview ? "http://127.0.0.1:8080/api" : "/api";
}

const API_BASE = getApiBase();

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusBadge(status) {
  return `<span class="status-badge status-badge--${status}">${escapeHtml(status)}</span>`;
}

function buildPopup(feature) {
  return `
    <article class="popup-card">
      <h3>${escapeHtml(feature.name)}</h3>
      <p>${statusBadge(feature.status)}</p>
      <p><strong>Coordinates:</strong> ${feature.latitude.toFixed(6)}, ${feature.longitude.toFixed(6)}</p>
      ${feature.notes ? `<p><strong>Notes:</strong> ${escapeHtml(feature.notes)}</p>` : ""}
      ${feature.reported_by ? `<p><strong>Updated by:</strong> ${escapeHtml(feature.reported_by)}</p>` : ""}
      ${feature.last_updated ? `<p class="small-note"><strong>Last updated:</strong> ${escapeHtml(feature.last_updated)}</p>` : ""}
      ${feature.description ? `<p>${escapeHtml(feature.description)}</p>` : ""}
    </article>
  `;
}

function buildMarker(feature) {
  const icon = L.divIcon({
    className: "",
    html: `<div class="issue-marker ${STATUS_CLASS[feature.status] || STATUS_CLASS.pending}"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -12],
  });
  return L.marker([feature.latitude, feature.longitude], { icon }).bindPopup(buildPopup(feature));
}

function renderMetrics(counts) {
  const metricRow = document.getElementById("metric-row");
  metricRow.innerHTML = ["all", "pending", "down", "fixed"]
    .map((status) => `
      <div class="metric-card">
        <span class="metric-card__label">${STATUS_LABELS[status]}</span>
        <span class="metric-card__value">${counts[status] ?? 0}</span>
      </div>
    `)
    .join("");
}

function renderMarkers() {
  if (!layerGroup) return;
  layerGroup.clearLayers();
  const visible = activeStatus === "all"
    ? allFeatures
    : allFeatures.filter((feature) => feature.status === activeStatus);
  visible.forEach((feature) => layerGroup.addLayer(buildMarker(feature)));
}

async function loadIssues() {
  const response = await fetch(`${API_BASE}/issues`);
  if (!response.ok) throw new Error("Could not load issue data.");
  return response.json();
}

function initMap(bounds) {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true });
  const streets = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  });
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri" },
  );
  streets.addTo(map);
  L.control.layers({ Map: streets, Satellite: satellite }, {}, { position: "topleft" }).addTo(map);
  layerGroup = L.layerGroup().addTo(map);

  if (bounds.min_lat !== null) {
    const leafletBounds = [
      [bounds.min_lat, bounds.min_lng],
      [bounds.max_lat, bounds.max_lng],
    ];
    map.fitBounds(leafletBounds, { padding: [30, 30] });
  } else {
    map.setView([17.9714, -76.792], 15);
  }
}

function bindFilters() {
  document.querySelectorAll(".filter-chip").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach((chip) => chip.classList.remove("is-active"));
      button.classList.add("is-active");
      activeStatus = button.dataset.status || "all";
      renderMarkers();
    });
  });
}

async function boot() {
  bindFilters();
  try {
    const payload = await loadIssues();
    allFeatures = payload.features || [];
    renderMetrics(payload.counts || {});
    initMap(payload.bounds || {});
    renderMarkers();
  } catch (error) {
    console.error(error);
  }
}

boot();
