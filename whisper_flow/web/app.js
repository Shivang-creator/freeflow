// whisper_flow/web/app.js — Reactive Client for FreeFlow Dictation

const API_BASE = window.location.origin;

// State
let appState = {
  status: {},
  models: [],
  dictionary: { vocabulary: [], corrections: {} },
  history: [],
  config: {},
};

// Elements
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const engineStatusPill = document.getElementById("engineStatusPill");
const modelsGrid = document.getElementById("modelsGrid");
const activeModelRamText = document.getElementById("activeModelRamText");
const vocabCount = document.getElementById("vocabCount");
const correctionsCount = document.getElementById("correctionsCount");
const vocabTagsContainer = document.getElementById("vocabTagsContainer");
const correctionsTableBody = document.getElementById("correctionsTableBody");
const historyListContainer = document.getElementById("historyListContainer");
const historySearchInput = document.getElementById("historySearchInput");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const toast = document.getElementById("toast");

// Toast Notification
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2400);
}

// Tab Switching
document.querySelectorAll(".nav-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    
    tab.classList.add("active");
    const targetId = tab.getAttribute("data-tab");
    const targetPane = document.getElementById(targetId);
    if (targetPane) targetPane.classList.add("active");

    if (targetId === "tab-history") loadHistory();
    if (targetId === "tab-dictionary") loadDictionary();
    if (targetId === "tab-models") loadModels();
  });
});

// API Helpers
async function fetchJSON(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    return await res.json();
  } catch (err) {
    console.error("API error:", path, err);
    return null;
  }
}

// Load Status
async function loadStatus() {
  const data = await fetchJSON("/api/status");
  if (!data) return;
  appState.status = data;

  // Update status pill
  statusText.textContent = data.state.charAt(0).toUpperCase() + data.state.slice(1);
  engineStatusPill.className = "status-pill " + data.state.toLowerCase();

  // Active RAM
  if (data.active_model) {
    activeModelRamText.textContent = `Active: ~${data.active_model.ram_mb} MB RAM (${data.active_model.name})`;
  }
}

// Load Models & RAM Budgets
async function loadModels() {
  const data = await fetchJSON("/api/models");
  if (!data || !data.models) return;
  appState.models = data.models;

  modelsGrid.innerHTML = "";
  data.models.forEach(m => {
    const card = document.createElement("div");
    card.className = `model-card ${m.is_active ? "active-model" : ""}`;

    let actionBtnHtml = "";
    if (m.is_active) {
      actionBtnHtml = `<button class="model-action-btn btn-active-label" disabled>✓ Active Engine</button>`;
    } else if (m.is_cached) {
      actionBtnHtml = `<button class="model-action-btn btn-activate" onclick="activateModel('${m.id}')">Switch to ${m.id === 'turbo' ? 'Turbo' : m.name}</button>`;
    } else {
      actionBtnHtml = `<button class="model-action-btn btn-download" onclick="downloadModel('${m.repo}', this)">⚡ 1-Click Download (~${m.size_mb} MB)</button>`;
    }

    card.innerHTML = `
      <div>
        <div class="model-header">
          <span class="model-badge">${m.badge}</span>
          ${m.is_cached ? '<span style="font-size:11px;color:#00e676;">✓ On Disk</span>' : '<span style="font-size:11px;color:#8e9bb2;">Cloud</span>'}
        </div>
        <div class="model-name">${m.name}</div>
        <div class="model-desc">${m.description}</div>
      </div>

      <div>
        <div class="model-specs">
          <div class="spec-row">
            <span class="spec-label">Weight Size:</span>
            <span class="spec-val">~${m.size_mb} MB</span>
          </div>
          <div class="spec-row">
            <span class="spec-label">RAM Footprint:</span>
            <span class="spec-val">~${m.ram_mb} MB</span>
          </div>
          <div class="spec-row">
            <span class="spec-label">Latency:</span>
            <span class="spec-val">${m.latency}</span>
          </div>
        </div>
        ${actionBtnHtml}
      </div>
    `;
    modelsGrid.appendChild(card);
  });
}

// Activate Model
window.activateModel = async function(modelId) {
  showToast("Switching MLX Whisper engine & pre-warming...");
  await fetchJSON("/api/models/activate", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId }),
  });
  await loadModels();
  await loadStatus();
  showToast("✅ Whisper model active & pre-warmed!");
};

// Download Model
window.downloadModel = async function(repo, btnElem) {
  btnElem.disabled = true;
  btnElem.textContent = "⏳ Downloading weights...";
  showToast("Starting background download from HuggingFace...");

  await fetchJSON("/api/models/download", {
    method: "POST",
    body: JSON.stringify({ repo }),
  });

  // Poll until cached
  const checkInterval = setInterval(async () => {
    const data = await fetchJSON("/api/models");
    if (!data) return;
    const target = data.models.find(m => m.repo === repo);
    if (target && target.is_cached) {
      clearInterval(checkInterval);
      showToast("✅ Weights downloaded! Activating engine...");
      await activateModel(target.id);
    }
  }, 2000);
};

// Load Custom Dictionary
async function loadDictionary() {
  const data = await fetchJSON("/api/dictionary");
  if (!data) return;
  appState.dictionary = data;

  // Vocabulary
  vocabCount.textContent = `${data.vocabulary.length} words`;
  vocabTagsContainer.innerHTML = "";
  data.vocabulary.forEach(word => {
    const chip = document.createElement("div");
    chip.className = "tag-chip";
    chip.innerHTML = `
      <span>${escapeHTML(word)}</span>
      <button class="tag-delete-btn" onclick="deleteWord('${escapeHTML(word)}')">×</button>
    `;
    vocabTagsContainer.appendChild(chip);
  });

  // Corrections
  const pairs = Object.entries(data.corrections);
  correctionsCount.textContent = `${pairs.length} rules`;
  correctionsTableBody.innerHTML = "";

  pairs.forEach(([heard, write]) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHTML(heard)}</strong></td>
      <td class="arrow-col">➔</td>
      <td><span style="color:#00e5ff;font-weight:600;">${escapeHTML(write)}</span></td>
      <td>
        <button class="btn btn-danger-outline" style="padding:3px 8px;font-size:11px;" onclick="deleteCorrection('${escapeHTML(heard)}')">Delete</button>
      </td>
    `;
    correctionsTableBody.appendChild(tr);
  });
}

// Add Vocabulary Word
document.getElementById("addWordForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("newWordInput");
  const word = input.value.trim();
  if (!word) return;

  await fetchJSON("/api/dictionary/word", {
    method: "POST",
    body: JSON.stringify({ word }),
  });
  input.value = "";
  await loadDictionary();
  showToast(`Added '${word}' to vocabulary`);
});

// Delete Word
window.deleteWord = async function(word) {
  await fetchJSON("/api/dictionary/word", {
    method: "DELETE",
    body: JSON.stringify({ word }),
  });
  await loadDictionary();
  showToast(`Removed '${word}'`);
};

// Add Correction
document.getElementById("addCorrectionForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const heardInput = document.getElementById("heardInput");
  const writeInput = document.getElementById("writeInput");
  const heard = heardInput.value.trim();
  const write = writeInput.value.trim();
  if (!heard || !write) return;

  await fetchJSON("/api/dictionary/correction", {
    method: "POST",
    body: JSON.stringify({ heard, write }),
  });
  heardInput.value = "";
  writeInput.value = "";
  await loadDictionary();
  showToast(`Added phonetic rule: '${heard}' ➔ '${write}'`);
});

// Delete Correction
window.deleteCorrection = async function(heard) {
  await fetchJSON("/api/dictionary/correction", {
    method: "DELETE",
    body: JSON.stringify({ heard }),
  });
  await loadDictionary();
  showToast(`Removed rule for '${heard}'`);
};

// Load Clipboard History
async function loadHistory(query = "") {
  const url = query ? `/api/history?q=${encodeURIComponent(query)}` : "/api/history";
  const data = await fetchJSON(url);
  if (!data || !data.entries) return;
  appState.history = data.entries;

  historyListContainer.innerHTML = "";
  if (data.entries.length === 0) {
    historyListContainer.innerHTML = `
      <div style="text-align:center;padding:40px;color:#5c687e;font-size:14px;">
        No dictated clips yet. Hold Right Option and speak!
      </div>
    `;
    return;
  }

  data.entries.forEach(item => {
    const card = document.createElement("div");
    card.className = "history-card";
    card.innerHTML = `
      <div>
        <div class="history-meta">
          <span class="app-badge">${escapeHTML(item.app_name)}</span>
          <span class="timestamp">${escapeHTML(item.iso_time)}</span>
          <span class="history-stats">${item.word_count} words • ${item.duration_s}s</span>
        </div>
        <div class="history-text">${escapeHTML(item.text)}</div>
      </div>
      <div class="history-btn-group">
        <button class="btn btn-copy" onclick="copySnippet('${escapeHTML(item.text).replace(/'/g, "\\'")}', this)">Copy</button>
      </div>
    `;
    historyListContainer.appendChild(card);
  });
}

// Copy Snippet
window.copySnippet = async function(text, btnElem) {
  await fetchJSON("/api/history/copy", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  if (btnElem) {
    const orig = btnElem.textContent;
    btnElem.textContent = "Copied! ✓";
    btnElem.style.background = "#00e676";
    btnElem.style.color = "#000";
    setTimeout(() => {
      btnElem.textContent = orig;
      btnElem.style.background = "";
      btnElem.style.color = "";
    }, 1200);
  }
  showToast("Snippet copied to clipboard!");
};

// Search History
historySearchInput.addEventListener("input", (e) => {
  loadHistory(e.target.value.trim());
});

// Clear History
clearHistoryBtn.addEventListener("click", async () => {
  if (confirm("Are you sure you want to clear all dictation history?")) {
    await fetchJSON("/api/history", { method: "DELETE" });
    await loadHistory();
    showToast("Clipboard history cleared.");
  }
});

// Load Settings / Config
async function loadConfig() {
  const data = await fetchJSON("/api/config");
  if (!data || !data.config) return;
  const cfg = data.config;
  appState.config = cfg;

  document.getElementById("hotkeySelect").value = cfg.hotkey || "alt_r";
  document.getElementById("vadSlider").value = cfg.vad_pause_seconds || 2.5;
  document.getElementById("vadValueText").textContent = `${cfg.vad_pause_seconds || 2.5}s`;
  document.getElementById("enableSlmToggle").checked = !!cfg.enable_slm;
  document.getElementById("slmModelInput").value = cfg.slm_model || "qwen2.5:1.5b";
  document.getElementById("restoreClipboardToggle").checked = !!cfg.restore_clipboard;
  document.getElementById("enableHudToggle").checked = !!cfg.enable_hud;
  document.getElementById("enableSoundToggle").checked = !!cfg.enable_sound;
}

// Wire Settings Auto-Save Listeners
function setupSettingsListeners() {
  const save = async (payload) => {
    await fetchJSON("/api/config", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast("Settings updated!");
  };

  document.getElementById("hotkeySelect").addEventListener("change", (e) => {
    save({ hotkey: e.target.value });
  });

  const vadSlider = document.getElementById("vadSlider");
  vadSlider.addEventListener("input", (e) => {
    document.getElementById("vadValueText").textContent = `${e.target.value}s`;
  });
  vadSlider.addEventListener("change", (e) => {
    save({ vad_pause_seconds: parseFloat(e.target.value) });
  });

  document.getElementById("enableSlmToggle").addEventListener("change", (e) => {
    save({ enable_slm: e.target.checked });
  });

  document.getElementById("slmModelInput").addEventListener("change", (e) => {
    save({ slm_model: e.target.value.trim() });
  });

  document.getElementById("restoreClipboardToggle").addEventListener("change", (e) => {
    save({ restore_clipboard: e.target.checked });
  });

  document.getElementById("enableHudToggle").addEventListener("change", (e) => {
    save({ enable_hud: e.target.checked });
  });

  document.getElementById("enableSoundToggle").addEventListener("change", (e) => {
    save({ enable_sound: e.target.checked });
  });
}

function escapeHTML(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// Initial Boot
(async function init() {
  await loadStatus();
  await loadModels();
  await loadDictionary();
  await loadConfig();
  setupSettingsListeners();

  // Status polling loop
  setInterval(loadStatus, 1500);
})();
