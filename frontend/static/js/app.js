// ── État global ───────────────────────────────────────────────────────────────
let state = {
  jobId:    null,
  clients:  [],
  rateSL:   280,
  rateGN:   340,
  pollTimer: null,
};

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadTariffs();
  loadHistory();
  setupUploadZone();
});

// ── Tarifs ────────────────────────────────────────────────────────────────────
async function loadTariffs() {
  const res = await fetch("/api/tariffs/");
  if (!res.ok) return;
  const data = await res.json();
  data.forEach(t => {
    if (t.destination === "SL") { state.rateSL = t.rate; document.getElementById("rate-sl").value = t.rate; }
    if (t.destination === "GN") { state.rateGN = t.rate; document.getElementById("rate-gn").value = t.rate; }
  });
  document.getElementById("rates-display").textContent = `SL $${state.rateSL}/CBM · GN $${state.rateGN}/CBM`;
}

function openSettings()  { document.getElementById("modal-settings").style.display = "flex"; }
function closeSettings() { document.getElementById("modal-settings").style.display = "none"; }

async function saveTariffs() {
  const sl = parseFloat(document.getElementById("rate-sl").value);
  const gn = parseFloat(document.getElementById("rate-gn").value);
  await fetch("/api/tariffs/", { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({destination:"SL", rate:sl}) });
  await fetch("/api/tariffs/", { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify({destination:"GN", rate:gn}) });
  state.rateSL = sl; state.rateGN = gn;
  document.getElementById("rates-display").textContent = `SL $${sl}/CBM · GN $${gn}/CBM`;
  closeSettings();
  recalcAll();
}

// ── Upload zone drag & drop ───────────────────────────────────────────────────
function setupUploadZone() {
  const zone  = document.getElementById("upload-zone");
  const input = document.getElementById("file-input");

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("dragover");
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => { if (input.files[0]) setFile(input.files[0]); });
}

function setFile(file) {
  const zone = document.getElementById("upload-zone");
  zone.classList.add("has-file");
  document.getElementById("upload-filename").textContent = `✓ ${file.name}`;
  zone.dataset.file = "ok";
  window._selectedFile = file;
}

// ── Upload & Parse ────────────────────────────────────────────────────────────
async function uploadFile() {
  const file  = window._selectedFile;
  const cnum  = document.getElementById("container-num").value.trim();
  const ldate = document.getElementById("load-date").value.trim();
  const eta   = document.getElementById("eta").value.trim();

  if (!file)  return alert("Veuillez sélectionner un fichier Excel.");
  if (!cnum)  return alert("Veuillez saisir le numéro de conteneur.");
  if (!ldate) return alert("Veuillez saisir la date de chargement.");
  if (!eta)   return alert("Veuillez saisir la date d'arrivée estimée.");

  const btn = document.getElementById("btn-upload");
  btn.disabled = true; btn.textContent = "Analyse en cours…";

  const fd = new FormData();
  fd.append("file", file);
  fd.append("container_num", cnum);
  fd.append("load_date", ldate);
  fd.append("eta", eta);

  const res  = await fetch("/api/jobs/upload", { method:"POST", body: fd });
  const data = await res.json();

  btn.disabled = false; btn.textContent = "Analyser le fichier →";

  if (!res.ok) return alert(data.detail || "Erreur lors de l'analyse.");

  state.jobId   = data.job_id;
  state.clients = data.clients;
  state.rateSL  = data.rate_sl;
  state.rateGN  = data.rate_gn;

  showStep("edit");
  renderClients();
}

// ── Affichage clients ─────────────────────────────────────────────────────────
function fmt(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

function calcClient(c) {
  const rate      = c.destination === "GN" ? state.rateGN : state.rateSL;
  const total_cbm = c.items.reduce((s, i) => s + parseFloat(i.cbm || 0), 0);
  const freight   = (total_cbm * rate) / 2;
  const custom    = (total_cbm * rate) / 2;
  const total_due = total_cbm * rate;
  return { total_cbm, freight, custom, total_due, rate };
}

function recalcAll() {
  state.clients.forEach((c, idx) => {
    const r = calcClient(c);
    const card = document.querySelector(`[data-client-idx="${idx}"]`);
    if (!card) return;
    card.querySelector(".amount-total").textContent = `$${fmt(r.total_due)}`;
    card.querySelector(".amount-detail").textContent = `Freight $${fmt(r.freight)} · Custom $${fmt(r.custom)}`;
  });
  updateStats();
}

function renderClients() {
  const container = document.getElementById("client-list");
  document.getElementById("edit-title").textContent =
    `${state.clients.length} clients — Conteneur ${document.getElementById("container-num").value}`;

  container.innerHTML = state.clients.map((c, idx) => {
    const r    = calcClient(c);
    const dest = c.destination === "GN"
      ? '<span class="badge badge-gn">🇬🇳 Guinée</span>'
      : '<span class="badge badge-sl">🌍 Sierra Leone</span>';
    const merged = c.is_merged ? '<span class="badge badge-merged">fusionné</span>' : '';

    const itemsHtml = c.items.map((it, jdx) => `
      <div class="item-row">
        <input type="text" value="${it.description}" placeholder="Description"
          onchange="state.clients[${idx}].items[${jdx}].description=this.value" />
        <input type="text" value="${it.quantity}" placeholder="Qté"
          onchange="state.clients[${idx}].items[${jdx}].quantity=this.value" />
        <input type="number" value="${it.cbm}" step="0.01" placeholder="CBM"
          onchange="state.clients[${idx}].items[${jdx}].cbm=parseFloat(this.value)||0; recalcAll();" />
      </div>
    `).join("");

    return `
    <div class="client-card" data-client-idx="${idx}">
      <div class="client-header" onclick="toggleEdit(${idx})">
        <div>
          <div class="client-name">${c.name}</div>
          <div class="client-phone">${c.phone || '—'}</div>
        </div>
        ${dest}
        ${merged}
        <div class="client-amounts">
          <div class="amount-total">$${fmt(r.total_due)}</div>
          <div class="amount-detail">Freight $${fmt(r.freight)} · Custom $${fmt(r.custom)}</div>
        </div>
        <button class="btn-edit">✏ Éditer</button>
      </div>
      <div class="edit-panel" id="edit-panel-${idx}">
        <div class="edit-grid">
          <div class="field">
            <label>Nom</label>
            <input type="text" value="${c.name}"
              onchange="state.clients[${idx}].name=this.value" />
          </div>
          <div class="field">
            <label>Téléphone</label>
            <input type="text" value="${c.phone}"
              onchange="state.clients[${idx}].phone=this.value" />
          </div>
          <div class="field">
            <label>Destination</label>
            <select onchange="state.clients[${idx}].destination=this.value; recalcAll(); renderDestBadge(${idx});">
              <option value="SL" ${c.destination==="SL"?"selected":""}>Sierra Leone ($${state.rateSL}/CBM)</option>
              <option value="GN" ${c.destination==="GN"?"selected":""}>Guinée ($${state.rateGN}/CBM)</option>
            </select>
          </div>
        </div>
        <div class="items-label">Colis (${c.items.length})</div>
        ${itemsHtml}
      </div>
    </div>`;
  }).join("");

  updateStats();
}

function toggleEdit(idx) {
  const panel = document.getElementById(`edit-panel-${idx}`);
  panel.classList.toggle("open");
}

function updateStats() {
  let totalCbm = 0, totalDue = 0, nbGN = 0;
  state.clients.forEach(c => {
    const r = calcClient(c);
    totalCbm += r.total_cbm;
    totalDue += r.total_due;
    if (c.destination === "GN") nbGN++;
  });
  document.getElementById("stats-row").innerHTML = `
    <span class="stat-item">Total CBM : <strong>${fmt(totalCbm)}</strong></span>
    <span class="stat-item">Total à facturer : <strong>$${fmt(totalDue)}</strong></span>
    <span class="stat-item">Guinée : <strong>${nbGN}</strong></span>
    <span class="stat-item">Sierra Leone : <strong>${state.clients.length - nbGN}</strong></span>
  `;
}

// ── Génération ────────────────────────────────────────────────────────────────
async function generateAll() {
  showStep("generating");
  animateProgress();

  const payload = {
    container_num: document.getElementById("container-num").value,
    load_date:     document.getElementById("load-date").value,
    eta:           document.getElementById("eta").value,
    clients:       state.clients.map(c => ({
      id:          c.id || "",
      name:        c.name,
      phone:       c.phone,
      destination: c.destination,
      items:       c.items.map(i => ({
        receipt:     i.receipt || "",
        description: i.description,
        quantity:    i.quantity,
        cbm:         parseFloat(i.cbm) || 0,
      })),
    })),
  };

  const res  = await fetch(`/api/jobs/${state.jobId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    showStep("edit");
    return alert("Erreur lors du lancement de la génération.");
  }

  pollStatus();
}

function pollStatus() {
  state.pollTimer = setInterval(async () => {
    const res  = await fetch(`/api/jobs/${state.jobId}/status`);
    const data = await res.json();

    if (data.status === "done") {
      clearInterval(state.pollTimer);
      document.getElementById("btn-download").href = data.zip_url;
      document.getElementById("done-summary").textContent =
        `${state.clients.length} factures générées pour le conteneur ${document.getElementById("container-num").value}`;
      showStep("done");
      loadHistory();
    } else if (data.status === "failed") {
      clearInterval(state.pollTimer);
      showStep("edit");
      alert("Erreur : " + (data.error || "Génération échouée"));
    }
  }, 2000);
}

function animateProgress() {
  let p = 0;
  const bar = document.getElementById("progress-fill");
  const iv  = setInterval(() => {
    p = Math.min(p + Math.random() * 8, 85);
    bar.style.width = p + "%";
    if (p >= 85) clearInterval(iv);
  }, 400);
}

// ── Navigation ────────────────────────────────────────────────────────────────
function showStep(name) {
  document.querySelectorAll(".step").forEach(s => s.classList.remove("active"));
  document.getElementById(`step-${name}`).classList.add("active");
  document.getElementById("history-section").style.display = name === "upload" ? "block" : "none";
}

function goBack() { showStep("upload"); }
function goHome() {
  state = { jobId: null, clients: [], rateSL: state.rateSL, rateGN: state.rateGN, pollTimer: null };
  window._selectedFile = null;
  document.getElementById("upload-zone").classList.remove("has-file");
  document.getElementById("upload-filename").textContent = "";
  showStep("upload");
  loadHistory();
}

// ── Historique ────────────────────────────────────────────────────────────────
async function loadHistory() {
  const res  = await fetch("/api/jobs/");
  if (!res.ok) return;
  const jobs = await res.json();
  const el   = document.getElementById("history-list");
  if (!jobs.length) { el.innerHTML = '<p style="color:var(--text-secondary);font-size:14px;">Aucun conteneur traité.</p>'; return; }
  el.innerHTML = jobs.map(j => `
    <div class="history-row">
      <div class="history-info">
        <strong>${j.container_num}</strong> — ${j.nb_clients} clients
        <div class="history-meta">Chargé le ${j.load_date} · ETA ${j.eta} · ${new Date(j.created_at).toLocaleDateString('fr')}</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="status-badge status-${j.status}">${j.status}</span>
        ${j.zip_url ? `<a href="${j.zip_url}" class="btn-primary" style="padding:6px 14px;font-size:12px;">ZIP</a>` : ""}
      </div>
    </div>
  `).join("");
}

// Init
showStep("upload");
