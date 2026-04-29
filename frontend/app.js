var ALLOYS = [];
var COMPARE_LIST = [];
var COMPARE_COLORS = ["#7ec4cf", "#e87272", "#5dd9a8", "#e8c55a", "#b8c6d0", "#8fa2b0", "#a0c4e8", "#607D8B"];
var ELEMENTS = [
  "Fe","Cr","Ni","Mo","Mn","C","Si","Ti","Al","V",
  "W","Co","Cu","Nb","Zr","N","Ta","Hf","B","Re",
  "Sn","Zn","Mg","O","Y","Nd","P","S","Sc","La",
  "Ce","Ga","Ge","Ag","Pt","Au","Pb","Bi","Ru","Pd",
  "In","Cd","Sb","As","Rh","Ir","Os","Gd","Sm","Ca",
  "Na","K","Li","Be","H","F","Cl","Ba","Cs","Hg",
  "Tl","Se","Te","Pr","Dy"
];
var radarChartInstance = null;
var barChartInstance = null;
var compareRadarInstance = null;
var lastPayload = null;
var API_TIMEOUT_MS = 300000;
var HEALTH_TIMEOUT_MS = 10000;

var DOMAIN_HINTS = {
  "Thermodynamics": "High = stable phase formation",
  "Hume-Rothery": "High = favorable solid-solution mixing",
  "Mechanical": "High = strong yield/UTS properties",
  "Corrosion": "High = resistant to corrosive attack",
  "Oxidation": "High = strong oxide-layer protection",
  "Radiation Physics": "High = radiation damage tolerant",
  "Weldability": "High = easy to weld without cracking",
  "Creep": "High = resists deformation under sustained load",
  "Fatigue & Fracture": "High = long fatigue life, crack resistant",
  "Grain Boundary": "High = stable, clean grain boundaries",
  "Hydrogen Embrittlement": "High = resistant to H-induced cracking",
  "Magnetism": "High = favorable magnetic behavior",
  "Thermal Properties": "High = good conductivity/expansion control",
  "Regulatory & Safety": "High = compliant, non-toxic composition",
  "Electronic Structure": "High = favorable electronic configuration",
  "Superconductivity": "High = favorable for superconducting state",
  "Phase Stability": "High = resists unwanted phase precipitation",
  "Plasticity": "High = good ductility and formability",
  "Diffusion": "High = controlled diffusion kinetics",
  "Surface Energy": "High = favorable surface interactions",
  "Tribology & Wear": "High = wear and friction resistant",
  "Acoustic Properties": "High = good acoustic damping/velocity",
  "Shape Memory": "High = strong shape-memory response",
  "Catalysis": "High = catalytically active surface",
  "Biocompatibility": "High = safe for biological contact",
  "Relativistic Effects": "High = accounts for heavy-element corrections",
  "Nuclear Fuel Compatibility": "High = compatible with nuclear fuels",
  "Optical Properties": "High = favorable reflectance/absorption",
  "Hydrogen Storage": "High = stores/releases H2 effectively",
  "Structural Efficiency": "High = strong per unit weight",
  "CALPHAD Stability": "High = thermodynamically validated phases",
  "India Corrosion Index": "High = resistant to tropical/coastal corrosion",
  "Transformation Kinetics": "High = predictable phase transformations",
  "Castability": "High = easy to cast without defects",
  "Machinability": "High = easy to machine and cut",
  "Formability": "High = easy to press/bend/stamp",
  "Additive Manufacturing": "High = printable with low defect risk",
  "Heat Treatment Response": "High = responds well to heat treatment",
  "Fracture Mechanics": "High = high fracture toughness (K_IC)",
  "Impact Toughness": "High = absorbs impact energy well",
  "Galvanic Compatibility": "High = low galvanic corrosion risk",
  "Solidification": "High = clean, defect-free solidification",
};

function $(id) { return document.getElementById(id); }

function defaultApiBase() { return window.location.origin; }

function initApiBase() {
  var params = new URLSearchParams(window.location.search);
  var fromUrl = (params.get("api") || "").trim();
  if (fromUrl) { $("apiBase").value = fromUrl; localStorage.setItem("aide_api_base", fromUrl); return; }
  var fromStorage = (localStorage.getItem("aide_api_base") || "").trim();
  if (fromStorage) { $("apiBase").value = fromStorage; return; }
  $("apiBase").value = defaultApiBase();
}

function apiBase() {
  var value = $("apiBase").value.trim().replace(/\/$/, "");
  if (value) localStorage.setItem("aide_api_base", value);
  return value;
}

function escapeHtml(text) {
  if (text == null) return "";
  var div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

function setLoading(btnId, spinnerId, loading) {
  var btn = $(btnId);
  var spinner = $(spinnerId);
  if (loading) { btn.disabled = true; spinner.classList.remove("hidden"); }
  else { btn.disabled = false; spinner.classList.add("hidden"); }
}

function setStatus(state, label) {
  $("statusPill").className = "status-pill " + state;
  $("statusText").textContent = label;
}

async function fetchWithTimeout(url, options, timeoutMs) {
  var controller = new AbortController();
  var timer = setTimeout(function() { controller.abort(); }, timeoutMs);
  try {
    var requestOptions = Object.assign({}, options || {});
    requestOptions.signal = controller.signal;
    return await fetch(url, requestOptions);
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new Error("Request timed out after " + Math.round(timeoutMs / 1000) + " seconds.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function checkHealth() {
  var base = apiBase();
  if (!base) { setStatus("disconnected", "No URL"); return; }
  setStatus("", "Checking");
  fetchWithTimeout(base + "/health", { method: "GET" }, HEALTH_TIMEOUT_MS)
    .then(function(r) { return r.json(); })
    .then(function(b) {
      if (b && b.ok) setStatus("connected", "Connected");
      else setStatus("disconnected", "Unhealthy");
    })
    .catch(function() { setStatus("disconnected", "Unreachable"); });
}

async function callApi(path, method, body) {
  var base = apiBase();
  if (!base) throw new Error("API base URL is required");
  var response = await fetchWithTimeout(base + path, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  }, API_TIMEOUT_MS);
  var rawText = await response.text();
  var payload = null;
  try {
    payload = rawText ? JSON.parse(rawText) : null;
  } catch (error) {
    payload = { detail: rawText || null };
  }
  if (!response.ok) throw new Error((payload && (payload.detail || payload.error)) || "Request failed (" + response.status + ")");
  return payload;
}

function initTabs() {
  document.querySelectorAll(".tabs .tab").forEach(function(tab) {
    tab.addEventListener("click", function() {
      document.querySelectorAll(".tabs .tab").forEach(function(t) { t.classList.remove("active"); });
      tab.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach(function(p) { p.classList.remove("active"); });
      $("tab-" + tab.dataset.tab).classList.add("active");
    });
  });
}

function initViewToggle() {
  $("viewVisualBtn").addEventListener("click", function() {
    $("viewVisualBtn").classList.add("active");
    $("viewJsonBtn").classList.remove("active");
    $("resultVisual").classList.remove("hidden");
    $("resultView").classList.add("hidden");
  });
  $("viewJsonBtn").addEventListener("click", function() {
    $("viewJsonBtn").classList.add("active");
    $("viewVisualBtn").classList.remove("active");
    $("resultView").classList.remove("hidden");
    $("resultVisual").classList.add("hidden");
  });
}

async function loadAlloys() {
  try {
    var payload = await callApi("/api/v1/alloys", "GET");
    ALLOYS = payload.data.alloys || [];
    populateAlloyDropdowns();
  } catch (e) {
    console.error("Failed to load alloys:", e);
    ALLOYS = [];
  }
}

function populateAlloyDropdowns() {
  [$("alloySelect"), $("edPreset"), $("compareAddSelect")].forEach(function(sel) {
    while (sel.options.length > 1) sel.remove(1);
    ALLOYS.forEach(function(a) {
      var opt = document.createElement("option");
      opt.value = a.key;
      opt.textContent = a.key + " (" + a.category + ")";
      sel.appendChild(opt);
    });
  });
}

function findAlloy(key) {
  for (var i = 0; i < ALLOYS.length; i++) {
    if (ALLOYS[i].key === key) return ALLOYS[i];
  }
  return null;
}

function fmtComp(comp, top) {
  top = top || 6;
  return Object.entries(comp).sort(function(a, b) { return b[1] - a[1]; }).slice(0, top)
    .map(function(e) { return e[0] + ":" + (e[1] * 100).toFixed(1) + "%"; }).join("  ");
}

function statusIcon(status) {
  if (!status) return "[ ]";
  var s = status.toUpperCase();
  if (s === "PASS") return "[OK]";
  if (s === "WARN") return "[!]";
  if (s === "FAIL") return "[X]";
  return "[ ]";
}

function statusClass(status) {
  if (!status) return "";
  var s = status.toUpperCase();
  if (s === "PASS") return "score-pass";
  if (s === "WARN") return "score-warn";
  if (s === "FAIL") return "score-fail";
  return "";
}

/* ---------- Alloy Selector ---------- */

$("alloySelect").addEventListener("change", function() {
  var key = this.value;
  var info = $("alloyInfo");
  var btn = $("analyzeAlloyBtn");
  if (!key) { info.classList.add("hidden"); btn.disabled = true; return; }
  var alloy = findAlloy(key);
  if (!alloy) { info.classList.add("hidden"); btn.disabled = true; return; }
  var props = alloy.properties || {};
  var propsText = [];
  if (props.yield_MPa) propsText.push("Yield: " + props.yield_MPa + " MPa");
  if (props.UTS_MPa) propsText.push("UTS: " + props.UTS_MPa + " MPa");
  if (props.density_gcc) propsText.push("Density: " + props.density_gcc + " g/cc");
  info.innerHTML = '<div><strong>' + escapeHtml(alloy.key) + '</strong> - ' + escapeHtml(alloy.category) + ' / ' + escapeHtml(alloy.subcategory) + '</div>'
    + '<div class="alloy-comp">' + escapeHtml(fmtComp(alloy.composition_wt)) + '</div>'
    + (propsText.length ? '<div class="alloy-props">' + escapeHtml(propsText.join(" | ")) + '</div>' : '')
    + (alloy.applications.length ? '<div class="alloy-props">Uses: ' + escapeHtml(alloy.applications.join(", ")) + '</div>' : '');
  info.classList.remove("hidden");
  btn.disabled = false;
});

$("analyzeAlloyBtn").addEventListener("click", async function() {
  var key = $("alloySelect").value;
  var alloy = findAlloy(key);
  if (!alloy) return;
  setLoading("analyzeAlloyBtn", "alloySpinner", true);
  try {
    var payload = await callApi("/api/v1/run", "POST", {
      composition: alloy.composition_wt, basis: "wt", temperature_K: 298, weight_profile: "auto",
    });
    lastPayload = payload;
    displayResults(payload);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading("analyzeAlloyBtn", "alloySpinner", false);
  }
});

/* ---------- Engine Run ---------- */

async function runEngine() {
  var query = $("queryInput").value.trim();
  if (!query) {
    $("engineSummary").innerHTML = '<div class="error-line">Please enter a query.</div>';
    return;
  }
  setLoading("engineBtn", "engineSpinner", true);
  $("engineSummary").innerHTML = '<div>[RUN] Running full pipeline and multi-iteration optimization... this may take 3 to 5 minutes.</div>';
  try {
    var payload = await callApi("/api/v1/run", "POST", {
      query: query,
      overrides: { use_ml: false, n_results: 10, max_iterations: 1, min_iterations: 1, target_score: 85, feedback_limit: 3 },
    });
    lastPayload = payload;
    var type = (payload.data || {}).request_type || "";
    var matched = (payload.data || {}).matched_alloy || "";
    $("engineSummary").innerHTML = '<div>[OK] Done - ' + escapeHtml(type) + (matched ? " (" + escapeHtml(matched) + ")" : "") + '</div>';
    displayResults(payload);
  } catch (e) {
    $("engineSummary").innerHTML = '<div class="error-line">[X] ' + escapeHtml(e.message) + '</div>';
    showError(e.message);
  } finally {
    setLoading("engineBtn", "engineSpinner", false);
  }
}

$("engineForm").addEventListener("submit", function(event) {
  event.preventDefault();
  runEngine();
});

$("queryInput").addEventListener("keydown", function(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    runEngine();
  }
});

/* ---------- Composition Editor ---------- */

function buildElementGrid() {
  var grid = $("elementGrid");
  grid.innerHTML = "";
  ELEMENTS.forEach(function(el) {
    var item = document.createElement("div");
    item.className = "el-item";
    item.innerHTML = '<span class="el-symbol">' + el + '</span>'
      + '<button type="button" class="el-btn" data-el="' + el + '" data-dir="-1">-</button>'
      + '<input type="number" class="el-input" id="el_' + el + '" value="0.00" min="0" max="100" step="0.5" />'
      + '<button type="button" class="el-btn" data-el="' + el + '" data-dir="1">+</button>'
      + '<span class="el-unit">%</span>';
    grid.appendChild(item);
  });
  grid.querySelectorAll(".el-btn").forEach(function(btn) {
    btn.addEventListener("click", function() {
      var inp = $("el_" + btn.dataset.el);
      var val = parseFloat(inp.value) || 0;
      val += parseFloat(btn.dataset.dir) * 0.5;
      if (val < 0) val = 0; if (val > 100) val = 100;
      inp.value = val.toFixed(2);
      updateCompTotal();
    });
  });
  grid.querySelectorAll(".el-input").forEach(function(inp) {
    inp.addEventListener("input", updateCompTotal);
  });
}

function updateCompTotal() {
  var total = 0;
  ELEMENTS.forEach(function(el) { total += parseFloat($("el_" + el).value) || 0; });
  $("compTotal").textContent = "Total: " + total.toFixed(2) + "%";
  $("compTotal").style.color = (total > 99.5 && total < 100.5) ? "var(--success)" : (total > 100.5 ? "var(--danger)" : "var(--warn)");
}

$("edPreset").addEventListener("change", function() {
  var key = this.value; if (!key) return;
  var alloy = findAlloy(key); if (!alloy) return;
  ELEMENTS.forEach(function(el) { $("el_" + el).value = "0.00"; });
  Object.entries(alloy.composition_wt).forEach(function(e) {
    var inp = $("el_" + e[0]);
    if (inp) inp.value = (e[1] * 100).toFixed(2);
  });
  updateCompTotal();
});

$("normalizeBtn").addEventListener("click", function() {
  var total = 0;
  ELEMENTS.forEach(function(el) { total += parseFloat($("el_" + el).value) || 0; });
  if (total <= 0) return;
  ELEMENTS.forEach(function(el) {
    var inp = $("el_" + el);
    inp.value = (((parseFloat(inp.value) || 0) / total) * 100).toFixed(2);
  });
  updateCompTotal();
});

$("analyzeCompBtn").addEventListener("click", async function() {
  var comp = {};
  ELEMENTS.forEach(function(el) {
    var val = parseFloat($("el_" + el).value) || 0;
    if (val > 0) comp[el] = val / 100;
  });
  if (Object.keys(comp).length < 2) { showError("Enter at least 2 elements"); return; }
  setLoading("analyzeCompBtn", "compEdSpinner", true);
  try {
    var payload = await callApi("/api/v1/run", "POST", {
      composition: comp, basis: $("edBasis").value,
      temperature_K: parseFloat($("edTemp").value) || 298, weight_profile: "auto",
    });
    lastPayload = payload;
    displayResults(payload);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading("analyzeCompBtn", "compEdSpinner", false);
  }
});

/* ---------- Multi-Compare ---------- */

// COMPARE_LIST stores objects: { name: string, composition_wt: {}, type: "db"|"custom" }

function buildCompareElementGrid() {
  var grid = $("compareElementGrid");
  grid.innerHTML = "";
  ELEMENTS.forEach(function(el) {
    var item = document.createElement("div");
    item.className = "el-item";
    item.innerHTML = '<span class="el-symbol">' + el + '</span>'
      + '<button type="button" class="el-btn" data-cel="' + el + '" data-dir="-1">-</button>'
      + '<input type="number" class="el-input" id="cel_' + el + '" value="0.00" min="0" max="100" step="0.5" />'
      + '<button type="button" class="el-btn" data-cel="' + el + '" data-dir="1">+</button>'
      + '<span class="el-unit">%</span>';
    grid.appendChild(item);
  });
  grid.querySelectorAll(".el-btn[data-cel]").forEach(function(btn) {
    btn.addEventListener("click", function() {
      var inp = $("cel_" + btn.dataset.cel);
      var val = parseFloat(inp.value) || 0;
      val += parseFloat(btn.dataset.dir) * 0.5;
      if (val < 0) val = 0; if (val > 100) val = 100;
      inp.value = val.toFixed(2);
      updateCompareTotal();
    });
  });
  grid.querySelectorAll(".el-input").forEach(function(inp) {
    if (inp.id && inp.id.startsWith("cel_")) {
      inp.addEventListener("input", updateCompareTotal);
    }
  });
}

function updateCompareTotal() {
  var total = 0;
  ELEMENTS.forEach(function(el) {
    var inp = $("cel_" + el);
    if (inp) total += parseFloat(inp.value) || 0;
  });
  $("compareCompTotal").textContent = "Total: " + total.toFixed(2) + "%";
  $("compareCompTotal").style.color = (total > 99.5 && total < 100.5) ? "var(--success)" : (total > 100.5 ? "var(--danger)" : "var(--warn)");
}

function getCompareGridComposition() {
  var comp = {};
  ELEMENTS.forEach(function(el) {
    var inp = $("cel_" + el);
    var val = inp ? (parseFloat(inp.value) || 0) : 0;
    if (val > 0) comp[el] = val / 100;
  });
  return comp;
}

function clearCompareGrid() {
  ELEMENTS.forEach(function(el) {
    var inp = $("cel_" + el);
    if (inp) inp.value = "0.00";
  });
  updateCompareTotal();
}

$("compareNormalizeBtn").addEventListener("click", function() {
  var total = 0;
  ELEMENTS.forEach(function(el) {
    var inp = $("cel_" + el);
    if (inp) total += parseFloat(inp.value) || 0;
  });
  if (total <= 0) return;
  ELEMENTS.forEach(function(el) {
    var inp = $("cel_" + el);
    if (inp) inp.value = (((parseFloat(inp.value) || 0) / total) * 100).toFixed(2);
  });
  updateCompareTotal();
});

$("compareAddBtn").addEventListener("click", function() {
  var key = $("compareAddSelect").value;
  if (!key || COMPARE_LIST.length >= 8) return;
  for (var i = 0; i < COMPARE_LIST.length; i++) {
    if (COMPARE_LIST[i].name === key) return;
  }
  var alloy = findAlloy(key);
  if (!alloy) return;
  COMPARE_LIST.push({ name: key, composition_wt: alloy.composition_wt, type: "db" });
  renderCompareList();
});

$("compareAddCustomBtn").addEventListener("click", function() {
  var comp = getCompareGridComposition();
  if (Object.keys(comp).length < 1) {
    showError("Set at least 1 element in the grid above.");
    return;
  }
  if (COMPARE_LIST.length >= 8) return;
  // Normalize
  var total = 0;
  for (var k in comp) total += comp[k];
  if (total > 0 && Math.abs(total - 1.0) > 0.01) {
    for (var k in comp) comp[k] = comp[k] / total;
  }
  var label = ($("customCompName").value || "").trim();
  if (!label) {
    label = "Custom-" + (COMPARE_LIST.length + 1);
  }
  COMPARE_LIST.push({ name: label, composition_wt: comp, type: "custom" });
  $("customCompName").value = "";
  clearCompareGrid();
  renderCompareList();
});

function renderCompareList() {
  var container = $("compareList");
  container.innerHTML = "";
  COMPARE_LIST.forEach(function(entry, i) {
    var tag = document.createElement("span");
    tag.className = "compare-tag";
    var c = COMPARE_COLORS[i % COMPARE_COLORS.length];
    tag.style.cssText = "background:" + c + "22;color:" + c + ";border:1px solid " + c + "44";
    var typeLabel = entry.type === "custom" ? " ★" : "";
    var compHint = fmtComp(entry.composition_wt, 3);
    tag.innerHTML = escapeHtml(entry.name + typeLabel) + ' <span style="font-size:0.7em;opacity:0.7">' + escapeHtml(compHint) + '</span> <button>&times;</button>';
    tag.querySelector("button").addEventListener("click", function() {
      COMPARE_LIST.splice(i, 1); renderCompareList();
    });
    container.appendChild(tag);
  });
  $("compareRunBtn").disabled = COMPARE_LIST.length < 2;
}

$("compareRunBtn").addEventListener("click", async function() {
  if (COMPARE_LIST.length < 2) return;
  setLoading("compareRunBtn", "compareSpinner", true);
  try {
    var results = [];
    for (var i = 0; i < COMPARE_LIST.length; i++) {
      var entry = COMPARE_LIST[i];
      var payload = await callApi("/api/v1/run", "POST", {
        composition: entry.composition_wt, basis: "wt", temperature_K: 298, weight_profile: "auto",
      });
      results.push({ name: entry.name, data: payload.data });
    }
    renderCompareCharts(results);
    renderCompareTable(results);
  } catch (e) { showError(e.message); }
  finally { setLoading("compareRunBtn", "compareSpinner", false); }
});

function renderCompareCharts(results) {
  $("compareCharts").classList.remove("hidden");
  var domains = extractDomainList(results[0].data.result);
  var datasets = results.map(function(r, i) {
    var c = COMPARE_COLORS[i % COMPARE_COLORS.length];
    return {
      label: r.name, data: extractDomainScores(r.data.result, domains),
      borderColor: c, backgroundColor: c + "18",
      borderWidth: 2, pointBackgroundColor: c, pointRadius: 3,
    };
  });
  if (compareRadarInstance) compareRadarInstance.destroy();
  compareRadarInstance = new Chart($("compareRadar"), {
    type: "radar",
    data: { labels: domains.map(function(d) { return d.length > 18 ? d.substring(0, 18) : d; }), datasets: datasets },
    options: {
      responsive: true,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: "#8c95a4", backdropColor: "transparent" }, grid: { color: "rgba(126,196,207,0.1)" }, pointLabels: { color: "#8c95a4", font: { size: 9 } } } },
      plugins: { legend: { labels: { color: "#e8ecf2", font: { size: 12 } } } },
    },
  });
}

function renderCompareTable(results) {
  var container = $("compareTable");
  container.classList.remove("hidden");
  var domains = extractDomainList(results[0].data.result);
  var html = '<table><thead><tr><th>Domain</th>';
  results.forEach(function(r) { html += '<th>' + escapeHtml(r.name) + '</th>'; });
  html += '</tr></thead><tbody>';
  domains.forEach(function(d, di) {
    html += '<tr><td title="' + escapeHtml(DOMAIN_HINTS[d] || '') + '">' + escapeHtml(d) + '</td>';
    results.forEach(function(r) {
      var s = extractDomainScores(r.data.result, domains)[di];
      html += '<td class="' + (s >= 70 ? "score-pass" : s >= 40 ? "score-warn" : "score-fail") + '">' + s.toFixed(1) + '</td>';
    });
    html += '</tr>';
  });
  // Composite score summary row (same penalised formula used everywhere)
  html += '<tr style="border-top:2px solid var(--border);font-weight:600"><td>Composite Score</td>';
  results.forEach(function(r) {
    var cs = r.data.result && r.data.result.composite_score != null ? Number(r.data.result.composite_score) : null;
    var cls = cs != null ? (cs >= 70 ? "score-pass" : cs >= 40 ? "score-warn" : "score-fail") : "";
    html += '<td class="' + cls + '">' + (cs != null ? cs.toFixed(1) : "?") + '</td>';
  });
  html += '</tr>';
  html += '</tbody></table>';
  container.innerHTML = html;
}

/* ---------- Domain helpers ---------- */

function extractDomainList(result) {
  if (!result) return [];
  var domains = result.domain_results || result.domains || [];
  if (Array.isArray(domains)) return domains.map(function(d) { return d.domain_name || d.name || ""; }).filter(Boolean);
  return [];
}

function normalizeScore(s) {
  if (typeof s !== "number") return 0;
  if (s > 0 && s <= 1) return s * 100;
  return s;
}

function extractDomainScores(result, domainNames) {
  if (!result) return domainNames.map(function() { return 0; });
  var domains = result.domain_results || result.domains || [];
  if (Array.isArray(domains)) {
    var map = {};
    domains.forEach(function(d) { map[d.domain_name || d.name || ""] = normalizeScore(d.score); });
    return domainNames.map(function(n) { return map[n] || 0; });
  }
  return domainNames.map(function() { return 0; });
}

/* ---------- Display Results ---------- */

function displayResults(payload) {
  $("resultView").textContent = JSON.stringify(payload, null, 2);
  $("viewVisualBtn").click();
  var data = payload.data || {};
  var result = data.result || {};
  showMetrics(data, result);
  renderCharts(result);
  renderDomainTable(result);
  renderCandidatesTable(data);
  $("resultPanel").scrollIntoView({ behavior: "smooth", block: "start" });
}

function showMetrics(data, result) {
  var metrics = $("metricsRow");
  metrics.classList.remove("hidden");
  var cards = [];
  cards.push({ label: "Type", value: data.request_type || "--" });
  if (result.composite_score != null) cards.push({ label: "Score", value: Number(result.composite_score).toFixed(1) + "/100" });
  if (result.n_domains != null) cards.push({ label: "Domains", value: result.n_domains });
  if (result.n_pass != null) cards.push({ label: "Pass", value: result.n_pass });
  if (result.n_warn != null) cards.push({ label: "Warn", value: result.n_warn });
  if (result.n_fail != null) cards.push({ label: "Fail", value: result.n_fail });
  if (result.best_physics_score != null) cards.push({ label: "Best Physics", value: Number(result.best_physics_score).toFixed(1) });
  if (result.best_rank_score != null) cards.push({ label: "Best Rank", value: Number(result.best_rank_score).toFixed(1) });
  else if (result.best_score != null) cards.push({ label: "Best Score", value: Number(result.best_score).toFixed(1) });
  if (result.n_candidates != null) cards.push({ label: "Candidates", value: result.n_candidates });
  if (result.n_physics_evaluated != null) cards.push({ label: "Physics Eval", value: result.n_physics_evaluated });
  if (result.iterations != null) cards.push({ label: "Iterations", value: result.iterations });
  metrics.innerHTML = cards.map(function(c) {
    return '<div class="metric-card"><div class="metric-label">' + c.label + '</div><div class="metric-value">' + c.value + '</div></div>';
  }).join("");
}

function renderCharts(result) {
  var domains = extractDomainList(result);
  if (!domains.length) { $("chartsRow").classList.add("hidden"); return; }
  $("chartsRow").classList.remove("hidden");
  var scores = extractDomainScores(result, domains);
  var labels = domains.map(function(d) { return d.length > 18 ? d.substring(0, 18) : d; });

  if (radarChartInstance) radarChartInstance.destroy();
  radarChartInstance = new Chart($("radarChart"), {
    type: "radar",
    data: { labels: labels, datasets: [{ label: "Score", data: scores, borderColor: "#7ec4cf", backgroundColor: "rgba(126,196,207,0.15)", borderWidth: 2, pointBackgroundColor: "#7ec4cf", pointRadius: 3 }] },
    options: {
      responsive: true,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: "#8c95a4", backdropColor: "transparent" }, grid: { color: "rgba(126,196,207,0.1)" }, pointLabels: { color: "#8c95a4", font: { size: 8 } } } },
      plugins: { legend: { display: false } },
    },
  });

  if (barChartInstance) barChartInstance.destroy();
  var barColors = scores.map(function(s) { return s >= 70 ? "#5dd9a8" : s >= 40 ? "#e8c55a" : "#e87272"; });
  barChartInstance = new Chart($("barChart"), {
    type: "bar",
    data: { labels: labels, datasets: [{ label: "Score", data: scores, backgroundColor: barColors, borderColor: barColors, borderWidth: 1 }] },
    options: {
      indexAxis: "y", responsive: true,
      scales: { x: { min: 0, max: 100, ticks: { color: "#8c95a4" }, grid: { color: "rgba(126,196,207,0.06)" } }, y: { ticks: { color: "#8c95a4", font: { size: 9 } }, grid: { display: false } } },
      plugins: { legend: { display: false } },
    },
  });
}

/* ---------- Domain Table with Expandable Checks ---------- */

function renderDomainTable(result) {
  var container = $("domainTable");
  var domains = result.domain_results || result.domains || [];
  if (!Array.isArray(domains) || !domains.length) { container.classList.add("hidden"); return; }
  container.classList.remove("hidden");

  var html = '<table class="domain-detail-table"><thead><tr>'
    + '<th style="width:30px"></th><th>ID</th><th>Domain</th><th>Score</th><th>Pass</th><th>Warn</th><th>Fail</th>'
    + '</tr></thead><tbody>';

  domains.forEach(function(d, idx) {
    var s = normalizeScore(d.score);
    var cls = s >= 70 ? "score-pass" : s >= 40 ? "score-warn" : "score-fail";
    var checks = d.checks || [];
    var hasChecks = checks.length > 0;
    var rowId = "domain-row-" + idx;
    var detailId = "domain-detail-" + idx;

    // Main domain row  (clickable)
    html += '<tr class="domain-row' + (hasChecks ? ' clickable' : '') + '" data-target="' + detailId + '" id="' + rowId + '">';
    html += '<td class="expand-icon">' + (hasChecks ? '>' : '') + '</td>';
    html += '<td>' + (d.domain_id || "") + '</td>';
    var domainName = d.domain_name || d.name || "";
    var hint = DOMAIN_HINTS[domainName] || "";
    html += '<td><strong>' + escapeHtml(domainName) + '</strong>' + (hint ? '<br><span class="domain-hint">' + escapeHtml(hint) + '</span>' : '') + '</td>';
    html += '<td class="' + cls + '">' + s.toFixed(1) + '</td>';
    html += '<td>' + (d.n_pass || 0) + '</td>';
    html += '<td>' + (d.n_warn || 0) + '</td>';
    html += '<td>' + (d.n_fail || 0) + '</td>';
    html += '</tr>';

    // Expandable detail row with checks
    if (hasChecks) {
      html += '<tr class="domain-detail-row hidden" id="' + detailId + '"><td colspan="7">';
      html += '<div class="checks-container">';
      checks.forEach(function(c) {
        var cscore = normalizeScore(c.score);
        var cCls = statusClass(c.status);
        html += '<div class="check-card">';
        html += '<div class="check-header">';
        html += '<span class="check-status">' + statusIcon(c.status) + '</span>';
        html += '<span class="check-name">' + escapeHtml(c.name) + '</span>';
        html += '<span class="check-score ' + cCls + '">' + cscore.toFixed(1) + '</span>';
        html += '</div>';
        html += '<div class="check-body">';
        if (c.value != null) {
          html += '<div class="check-row"><span class="check-label">Value:</span> <span class="check-val">' + escapeHtml(String(typeof c.value === "number" ? c.value.toPrecision(4) : c.value)) + (c.unit ? ' ' + escapeHtml(c.unit) : '') + '</span></div>';
        }
        if (c.formula) {
          html += '<div class="check-row"><span class="check-label">Formula:</span> <span class="check-formula">' + escapeHtml(c.formula) + '</span></div>';
        }
        if (c.message) {
          html += '<div class="check-row"><span class="check-label">Explanation:</span> <span class="check-msg">' + escapeHtml(c.message) + '</span></div>';
        }
        if (c.citation) {
          html += '<div class="check-row"><span class="check-label">Citation:</span> <span class="check-cite">' + escapeHtml(c.citation) + '</span></div>';
        }
        html += '</div></div>';
      });
      html += '</div></td></tr>';
    }
  });

  html += '</tbody></table>';
  container.innerHTML = html;

  // Attach click handlers to expand/collapse
  container.querySelectorAll(".domain-row.clickable").forEach(function(row) {
    row.addEventListener("click", function() {
      var target = row.dataset.target;
      var detail = $(target);
      var icon = row.querySelector(".expand-icon");
      if (detail.classList.contains("hidden")) {
        detail.classList.remove("hidden");
        icon.textContent = "v";
      } else {
        detail.classList.add("hidden");
        icon.textContent = ">";
      }
    });
  });
}

function renderCandidatesTable(data) {
  var container = $("candidatesTable");
  var result = data.result || {};
  var top = result.top;
  var detail = result.candidates_detail || [];
  if ((!top || !Array.isArray(top) || !top.length) && !detail.length) { container.classList.add("hidden"); return; }
  container.classList.remove("hidden");
  var title = detail.length ? "Candidate Pool (" + detail.length + " returned)" : "Top Candidates";
  var html = '<h3 style="margin: 16px 0 8px; font-size: 1rem;">' + escapeHtml(title) + '</h3>';
  html += '<table><thead><tr><th>#</th><th>Type</th><th>Iter</th><th>Score</th><th>Source</th><th>Composition</th></tr></thead><tbody>';

  if (detail.length) {
    detail.forEach(function(cd, i) {
      var badgeCls = cd.result_type === "catalog" ? "badge-catalog" : "badge-generated";
      var badgeText = cd.result_type === "catalog" ? "CATALOG" : "GENERATED";
      var scoreSource = String(cd.score_source || "").toLowerCase();
      var source = "SCREEN";
      if (cd.physics_evaluated && scoreSource === "physics_ml") source = "PHYSICS+ML";
      else if (cd.physics_evaluated) source = "PHYSICS";
      var score = cd.physics_score != null ? Number(cd.physics_score) : (cd.score != null ? Number(cd.score) : null);
      html += '<tr><td>' + (i + 1) + '</td>';
      html += '<td><span class="badge ' + badgeCls + '">' + badgeText + '</span></td>';
      html += '<td>' + ((cd.iteration != null ? Number(cd.iteration) + 1 : "-")) + '</td>';
      html += '<td>' + (score != null ? score.toFixed(1) : "-") + '</td>';
      html += '<td>' + escapeHtml(source) + '</td>';
      html += '<td style="font-family: var(--mono); font-size: 0.78rem;">' + escapeHtml(fmtComp(cd.composition_wt || cd.composition || {}, 5)) + '</td></tr>';
    });
  } else if (top) {
    top.forEach(function(entry, i) {
      var comp = entry[0] || entry.composition || {};
      var r = entry[1] || entry.result || {};
      html += '<tr><td>' + (i + 1) + '</td>';
      html += '<td><span class="badge badge-generated">GENERATED</span></td>';
      html += '<td>-</td>';
      html += '<td>' + (r.composite_score != null ? Number(r.composite_score).toFixed(1) : "?") + '</td>';
      html += '<td>PHYSICS</td>';
      html += '<td style="font-family: var(--mono); font-size: 0.78rem;">' + escapeHtml(fmtComp(comp, 5)) + '</td></tr>';
    });
  }

  html += '</tbody></table>';

  // Show provenance if present at root level (alloy_lookup)
  if (data.result_type === "catalog" && data.provenance) {
    html += '<div style="margin-top:8px;font-size:0.78rem;color:var(--text-muted)">';
    html += 'Source: ' + escapeHtml(data.provenance.source || "");
    if (data.provenance.year) html += ' (' + data.provenance.year + ')';
    if (data.provenance.confidence) html += ' [' + escapeHtml(data.provenance.confidence) + ']';
    html += '</div>';
  }

  container.innerHTML = html;
}

function showError(msg) {
  $("metricsRow").classList.add("hidden");
  $("chartsRow").classList.add("hidden");
  $("domainTable").classList.add("hidden");
  $("candidatesTable").classList.add("hidden");
  $("resultView").textContent = JSON.stringify({ error: msg }, null, 2);
  $("resultVisual").innerHTML = '<div class="summary"><div class="error-line">Error: ' + escapeHtml(msg) + '</div></div>';
}

$("copyBtn").addEventListener("click", function() {
  var text = $("resultView").textContent;
  if (!text) return;
  navigator.clipboard.writeText(text).then(function() {
    $("copyBtn").textContent = "Copied!";
    setTimeout(function() { $("copyBtn").textContent = "Copy"; }, 1500);
  });
});

$("apiBase").addEventListener("change", function() { checkHealth(); loadAlloys(); });

initApiBase();
initTabs();
initViewToggle();
buildElementGrid();
buildCompareElementGrid();
checkHealth();
loadAlloys();

