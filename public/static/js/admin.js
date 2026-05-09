let allIssues = [];
let selectedId = "";
let storageState = { read_only: false, reason: "" };

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

function setMessage(elementId, message, kind = "") {
  const node = document.getElementById(elementId);
  node.textContent = message;
  node.className = `form-message${kind ? ` is-${kind}` : ""}`;
}

function setAdminDisabled(disabled) {
  [
    "kml-file",
    "issue-status",
    "issue-reported-by",
    "issue-notes",
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (node) node.disabled = disabled;
  });
  document.querySelectorAll("#kml-upload-form button, #status-form button").forEach((button) => {
    button.disabled = disabled;
  });
}

async function fetchIssues() {
  const response = await fetch(`${API_BASE}/issues`);
  if (!response.ok) throw new Error("Could not load issue points.");
  return response.json();
}

function renderTable() {
  const searchValue = document.getElementById("search-input").value.trim().toLowerCase();
  const statusFilter = document.getElementById("status-filter").value;
  const body = document.getElementById("issues-table-body");

  const rows = allIssues.filter((issue) => {
    const matchesSearch = !searchValue || issue.name.toLowerCase().includes(searchValue);
    const matchesStatus = statusFilter === "all" || issue.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  body.innerHTML = rows.map((issue) => `
    <tr data-id="${escapeHtml(issue.id)}" class="${issue.id === selectedId ? "is-selected" : ""}">
      <td>
        <strong>${escapeHtml(issue.name)}</strong>
        <div class="small-note">${issue.latitude.toFixed(5)}, ${issue.longitude.toFixed(5)}</div>
      </td>
      <td><span class="status-badge status-badge--${escapeHtml(issue.status)}">${escapeHtml(issue.status)}</span></td>
      <td>${escapeHtml(issue.last_updated || "Not updated yet")}</td>
      <td>${escapeHtml(issue.notes || "")}</td>
    </tr>
  `).join("");

  body.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => selectIssue(row.dataset.id || ""));
  });
}

function selectIssue(issueId) {
  const issue = allIssues.find((entry) => entry.id === issueId);
  if (!issue) return;
  selectedId = issue.id;
  document.getElementById("issue-id").value = issue.id;
  document.getElementById("issue-name").value = issue.name;
  document.getElementById("issue-status").value = issue.status;
  document.getElementById("issue-reported-by").value = issue.reported_by || "";
  document.getElementById("issue-notes").value = issue.notes || "";
  renderTable();
}

async function reloadIssues(selectFirst = false) {
  const payload = await fetchIssues();
  allIssues = payload.features || [];
  storageState = payload.storage || { read_only: false, reason: "" };
  setAdminDisabled(Boolean(storageState.read_only));
  if (storageState.read_only) {
    setMessage("status-message", storageState.reason, "error");
    setMessage("kml-message", storageState.reason, "error");
  }
  if ((!selectedId || !allIssues.find((issue) => issue.id === selectedId)) && selectFirst && allIssues.length) {
    selectedId = allIssues[0].id;
  }
  renderTable();
  if (selectedId) {
    selectIssue(selectedId);
  }
}

async function saveStatus(event) {
  event.preventDefault();
  if (storageState.read_only) {
    setMessage("status-message", storageState.reason, "error");
    return;
  }
  const issueId = document.getElementById("issue-id").value;
  if (!issueId) {
    setMessage("status-message", "Select a point first.", "error");
    return;
  }
  const payload = {
    id: issueId,
    status: document.getElementById("issue-status").value,
    reported_by: document.getElementById("issue-reported-by").value,
    notes: document.getElementById("issue-notes").value,
  };
  const response = await fetch(`${API_BASE}/statuses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    setMessage("status-message", "Could not save the status update.", "error");
    return;
  }
  await reloadIssues();
  setMessage("status-message", "Status saved.", "success");
}

async function uploadKml(event) {
  event.preventDefault();
  if (storageState.read_only) {
    setMessage("kml-message", storageState.reason, "error");
    return;
  }
  const input = document.getElementById("kml-file");
  const file = input.files?.[0];
  if (!file) {
    setMessage("kml-message", "Choose a KML file first.", "error");
    return;
  }
  const kmlText = await file.text();
  const response = await fetch(`${API_BASE}/kml`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: file.name, kml_text: kmlText }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setMessage("kml-message", payload.error || "Could not replace the KML file.", "error");
    return;
  }
  await reloadIssues(true);
  setMessage("kml-message", `Loaded ${payload.features.length} points from ${payload.kml_file}.`, "success");
  input.value = "";
}

function bindEvents() {
  document.getElementById("status-form").addEventListener("submit", saveStatus);
  document.getElementById("kml-upload-form").addEventListener("submit", uploadKml);
  document.getElementById("search-input").addEventListener("input", renderTable);
  document.getElementById("status-filter").addEventListener("change", renderTable);
}

async function boot() {
  bindEvents();
  try {
    await reloadIssues(true);
  } catch (error) {
    document.getElementById("issues-table-body").innerHTML = `
      <tr>
        <td colspan="4">${escapeHtml(error.message)} Start python server.py for local admin access.</td>
      </tr>
    `;
    setMessage("status-message", "Backend unavailable. Start python server.py before using the admin tools.", "error");
  }
}

boot();
