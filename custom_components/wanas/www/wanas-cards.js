/*
 * Wanas dashboard cards, served by the integration itself (see frontend.py).
 *
 *   type: custom:wanas-card            unit overview: airflow diagram, readouts, modules
 *   type: custom:wanas-schedule-card   weekly schedule: five periods per day, as on the panel
 *
 * Both find their entities through the entity registry (platform "wanas" plus the
 * entity's translation key), so renamed entity ids keep working. Optional config:
 *   device_id: <id>     pick one unit when more than one is set up
 *   compact: true       (wanas-card) a single-row tile instead of the full card
 *
 * The DOM is built once and only values are patched afterwards: Home Assistant hands
 * the card a new `hass` on every state change in the house, and rebuilding would
 * restart the airflow animation each time.
 */

const VERSION = "3.4.0";
const ROMAN = ["0", "I", "II", "III"];
const DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

const TEXT = {
  pl: {
    unit: "Rekuperator", schedule: "Harmonogram", outside: "na zewnątrz", house: "dom",
    intake: "czerpnia", exhaust: "wyrzutnia", supply: "nawiew", extract: "wywiew", core: "wymiennik",
    gear: "Bieg", flow: "Przepływ", filter: "Filtr", days: "dni", toReplace: "do wymiany",
    replaceNow: "wymień filtr", program: "program", input3: "wejście III", input1: "wejście I",
    forced: (g, p) => `Bieg ${g} wymusza wejście cyfrowe rekuperatora. Program na teraz: bieg ${p}.`,
    modules: "Moduły", timed: "Funkcje czasowe", now: "Teraz w harmonogramie", period: "przedział",
    clockOk: "zegar sterownika zgodny", clockOff: (m) => `zegar sterownika ${m > 0 ? "+" : ""}${m} min`,
    setClock: "ustaw zegar", recovery: "odzysk", bypass: "bypass", cooling: "chłód",
    today: (v) => `dziś ${v}kWh`, notRecovering: "nie liczy się", recoveryTile: "Odzysk",
    names: { bypass: "Bypass", gwc: "GWC", heater: "Nagrzewnica", cooler: "Chłodnica", humidifier: "Nawilżacz",
      fireplace_switch: "Kominek", party_switch: "Impreza", vacation_switch: "Urlop" },
    dayShort: ["pon", "wt", "śr", "czw", "pt", "sob", "nie"],
    dayLong: ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"],
    from: "od", to: "do", speed: "bieg", temp: "temp.", applyAlso: "Zastosuj też do:",
    undo: "Cofnij zmiany", save: (n, d) => (n > 1 ? `Zapisz ${n} dni` : `Zapisz ${d}`),
    saved: (d) => `Zapisano: ${d}`, week: "Tydzień", reading: "Odczyt harmonogramu…",
    readFromUnit: "odczytaj z urządzenia", readFailed: "Nie udało się odczytać harmonogramu",
    errGrid: (p, t) => `Przedział ${p}: ${t} jest poza 00:15–23:45.`,
    errBefore: (p, t, q, u) => `Przedział ${p} nie może kończyć się o ${t}: przedział ${q} kończy się o ${u}.`,
    errAfter: (p, t, q, u) => `Przedział ${p} nie może kończyć się o ${t}: przedział ${q} kończy się o ${u}.`,
    noDevice: "Nie znaleziono urządzenia Wanas.",
    edDevice: "Urządzenie (puste = pierwsze znalezione)", edCompact: "Kompaktowy kafelek (jeden wiersz)",
  },
  en: {
    unit: "Ventilation", schedule: "Schedule", outside: "outside", house: "house",
    intake: "intake", exhaust: "exhaust", supply: "supply", extract: "extract", core: "core",
    gear: "Speed", flow: "Airflow", filter: "Filter", days: "days", toReplace: "left",
    replaceNow: "replace filter", program: "schedule", input3: "input III", input1: "input I",
    forced: (g, p) => `Speed ${g} is forced by the unit's digital input. The schedule says speed ${p}.`,
    modules: "Modules", timed: "Timed functions", now: "Now in the schedule", period: "period",
    clockOk: "controller clock in sync", clockOff: (m) => `controller clock ${m > 0 ? "+" : ""}${m} min`,
    setClock: "set clock", recovery: "recovery", bypass: "bypass", cooling: "cooling",
    today: (v) => `today ${v}kWh`, notRecovering: "not counted", recoveryTile: "Recovery",
    names: { bypass: "Bypass", gwc: "Ground loop", heater: "Heater", cooler: "Cooler", humidifier: "Humidifier",
      fireplace_switch: "Fireplace", party_switch: "Party", vacation_switch: "Vacation" },
    dayShort: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    dayLong: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    from: "from", to: "until", speed: "speed", temp: "temp.", applyAlso: "Also apply to:",
    undo: "Undo", save: (n, d) => (n > 1 ? `Save ${n} days` : `Save ${d}`),
    saved: (d) => `Saved: ${d}`, week: "Week", reading: "Reading the schedule…",
    readFromUnit: "read from unit", readFailed: "Could not read the schedule",
    errGrid: (p, t) => `Period ${p}: ${t} is outside 00:15–23:45.`,
    errBefore: (p, t, q, u) => `Period ${p} cannot end at ${t}: period ${q} ends at ${u}.`,
    errAfter: (p, t, q, u) => `Period ${p} cannot end at ${t}: period ${q} ends at ${u}.`,
    noDevice: "No Wanas device found.",
    edDevice: "Device (empty = the first one found)", edCompact: "Compact tile (one row)",
  },
};

const TIMED = [
  ["fireplace_switch", "fireplace", "s", 180],
  ["party_switch", "party", "min", 720],
  ["vacation_switch", "vacation", "d", 30],
];
const MODULES = ["bypass", "gwc", "heater", "cooler", "humidifier"];

const SHARED_CSS = `
  :host { --wc-mono: var(--code-font-family, ui-monospace, "Roboto Mono", monospace);
    --wc-accent: var(--primary-color, #5ca5ff); --wc-warn: var(--warning-color, #f0b429);
    --wc-ok: var(--success-color, #7fe1a8); --wc-soft: var(--secondary-text-color, #9aa);
    --wc-line: var(--divider-color, rgba(255,255,255,0.12)); --wc-track: rgba(127,127,127,0.12); }
  ha-card { padding: 16px 18px 18px; }
  .head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .head h2 { margin: 0; font-size: 16px; font-weight: 600; font-variant: small-caps; letter-spacing: 0.06em; text-transform: lowercase; }
  .sub { font-family: var(--wc-mono); font-size: 11px; color: var(--wc-soft); }
  .sub button { font: inherit; color: var(--wc-accent); background: none; border: 0; padding: 0 0 0 6px; cursor: pointer; }
  .mono { font-family: var(--wc-mono); font-variant-numeric: tabular-nums; }
  .label { font-size: 12px; color: var(--wc-soft); margin: 14px 0 8px; }
  button:focus-visible { outline: 2px solid var(--wc-accent); outline-offset: 2px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { font: inherit; font-size: 13px; color: var(--wc-soft); background: transparent; border: 1px solid var(--wc-line);
    border-radius: 999px; padding: 5px 11px; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; }
  .chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--wc-line); }
  .chip.on { color: var(--primary-text-color); border-color: color-mix(in srgb, var(--wc-accent) 60%, transparent);
    background: color-mix(in srgb, var(--wc-accent) 14%, transparent); }
  .chip.on .dot { background: var(--wc-accent); }
  .chip .cd { font-family: var(--wc-mono); font-size: 11px; color: var(--wc-soft); }
  .chip.on .cd { color: var(--wc-accent); }
  .empty { color: var(--wc-soft); font-size: 13px; padding: 8px 0; }
  @media (prefers-reduced-motion: reduce) { .dash, .fan { animation: none !important; } }
`;

function lang(hass) {
  const l = (hass && (hass.locale?.language || hass.language)) || "en";
  return l.startsWith("pl") ? TEXT.pl : TEXT.en;
}

/** Map "domain:translation_key" -> entity_id for one Wanas device. */
function wanasEntities(hass, deviceId) {
  const all = Object.values(hass.entities || {}).filter((e) => e.platform === "wanas");
  const device = deviceId || all.find((e) => e.device_id)?.device_id;
  const map = {};
  for (const e of all) {
    if (e.device_id !== device || !e.translation_key) continue;
    map[`${e.entity_id.split(".")[0]}:${e.translation_key}`] = e.entity_id;
  }
  return { device, map };
}

function num(hass, entityId) {
  const s = entityId && hass.states[entityId];
  if (!s) return null;
  const v = parseFloat(s.state);
  return Number.isFinite(v) ? v : null;
}

function fmtTemp(v) {
  return v == null ? "—" : `${(Math.round(v * 10) / 10).toFixed(1).replace(".", ",")}°`;
}

const hm = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
const fmtKw = (w) => (w / 1000).toFixed(2).replace(".", ",");
const toMin = (t) => { const [h, m] = String(t).split(":"); return +h * 60 + +m; };

/* ======================================================================== card 1 */

class WanasCard extends HTMLElement {
  static getStubConfig() { return {}; }

  static getConfigElement() {
    const el = document.createElement("wanas-card-editor");
    el.compactOption = true;
    return el;
  }

  setConfig(config) {
    this._config = config || {};
    this._built = false;
    if (this.shadowRoot) this.shadowRoot.innerHTML = "";
  }

  getCardSize() { return this._config?.compact ? 1 : 6; }

  // Height follows the content: modules and timed functions vary per unit.
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const { map } = wanasEntities(hass, this._config?.device_id);
    this._e = map;
    if (!this._built) this._build();
    this._update();
  }

  _id(domain, key) { return this._e[`${domain}:${key}`]; }

  _build() {
    const t = lang(this._hass);
    this._t = t;
    const root = this.shadowRoot;
    if (!this._id("sensor", "supply_airflow")) {
      root.innerHTML = `<style>${SHARED_CSS}</style><ha-card><div class="empty">${t.noDevice}</div></ha-card>`;
      this._built = false;
      return;
    }
    if (this._config.compact) {
      root.innerHTML = `<style>${SHARED_CSS}
        .tile { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 14px; align-items: center; cursor: pointer; }
        .g { font-family: var(--wc-mono); font-size: 26px; width: 52px; height: 52px; display: grid; place-items: center;
          border-radius: 50%; border: 1px solid color-mix(in srgb, var(--wc-accent) 55%, transparent); }
        .l1 { font-size: 15px; } .l2 { font-family: var(--wc-mono); font-size: 12px; color: var(--wc-soft);
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .r { text-align: right; font-family: var(--wc-mono); font-size: 12px; color: var(--wc-soft); }
        .r b { display: block; font-size: 17px; font-weight: 500; color: var(--primary-text-color); }
        .r.warn b { color: var(--wc-warn); }
      </style>
      <ha-card><div class="tile" id="tile"><div class="g" id="g">–</div>
        <div style="min-width:0; display:grid; gap:2px"><span class="l1">${t.unit}</span><span class="l2" id="l2"></span></div>
        <div class="r" id="r"><b id="rf">–</b>${t.filter.toLowerCase()}</div></div></ha-card>`;
      root.getElementById("tile").onclick = () => this._moreInfo(this._id("sensor", "supply_airflow"));
      this._built = true;
      return;
    }
    root.innerHTML = `<style>${SHARED_CSS}
      svg { width: 100%; height: auto; display: block; margin: 6px 0 2px; }
      svg text { font-family: var(--wc-mono); fill: var(--primary-text-color); }
      svg .lbl { font-family: inherit; font-variant: small-caps; letter-spacing: 0.06em; fill: var(--wc-soft); font-size: 12px; }
      svg .t { font-size: 17px; font-weight: 500; cursor: pointer; }
      .duct { fill: none; stroke-width: 7; stroke-linecap: round; }
      .dash { fill: none; stroke-width: 2; stroke-linecap: round; stroke-dasharray: 2 12; stroke: rgba(255,255,255,0.85);
        animation: run linear infinite; }
      @keyframes run { to { stroke-dashoffset: -28; } }
      .core { fill: var(--wc-track); stroke: var(--wc-soft); stroke-width: 1.2; }
      .fan { transform-box: fill-box; transform-origin: center; animation: spin linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
      .ro { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
      .r { display: grid; gap: 2px; padding: 9px 11px; border-radius: 12px; background: var(--wc-track); cursor: pointer; min-width: 0; }
      .r .k { font-size: 12px; color: var(--wc-soft); }
      .r .v { font-family: var(--wc-mono); font-size: 21px; font-weight: 500; font-variant-numeric: tabular-nums; }
      .r .v small { font-size: 12px; color: var(--wc-soft); margin-left: 3px; }
      .r .n { font-family: var(--wc-mono); font-size: 11px; color: var(--wc-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .r.warn { background: color-mix(in srgb, var(--wc-warn) 16%, transparent); }
      .r.warn .v { color: var(--wc-warn); }
      .ov { display: flex; gap: 10px; align-items: center; margin-top: 10px; padding: 8px 11px; border-radius: 12px;
        background: color-mix(in srgb, var(--wc-accent) 10%, transparent); font-size: 13px; }
      .ov .tag { font-family: var(--wc-mono); font-size: 11px; color: var(--wc-accent); white-space: nowrap;
        border: 1px solid color-mix(in srgb, var(--wc-accent) 45%, transparent); border-radius: 6px; padding: 1px 6px; }
      .now { margin-top: 14px; padding-top: 11px; border-top: 1px solid var(--wc-line); font-size: 13px; }
      .now b { font-family: var(--wc-mono); font-weight: 500; }
      @media (max-width: 420px) { .ro { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    </style>
    <ha-card>
      <div class="head"><h2>${t.unit}</h2><span class="sub" id="clock"></span></div>
      <svg viewBox="0 0 640 250" role="img" aria-label="${t.unit}">
        <defs>
          <linearGradient id="gS" x1="0" x2="1"><stop id="gS0" offset="0"/><stop id="gS1" offset="1"/></linearGradient>
          <linearGradient id="gE" x1="1" x2="0"><stop id="gE0" offset="0"/><stop id="gE1" offset="1"/></linearGradient>
        </defs>
        <path d="M420 230 V96 L520 40 L620 96 V230" fill="none" stroke="var(--wc-line)" stroke-width="1.2"/>
        <text class="lbl" x="520" y="122" text-anchor="middle">${t.house}</text>
        <text class="lbl" x="150" y="128" text-anchor="middle">${t.outside}</text>
        <path id="pS" class="duct" stroke="url(#gS)" d="M30 80 H230 L300 125 L370 170 H600"/>
        <path id="dS" class="dash" d="M30 80 H230 L300 125 L370 170 H600"/>
        <path id="pE" class="duct" stroke="url(#gE)" d="M600 80 H370 L300 125 L230 170 H30"/>
        <path id="dE" class="dash" d="M600 80 H370 L300 125 L230 170 H30"/>
        <path id="pB" class="duct" d="M230 80 C 300 40, 330 40, 370 60 L 380 170" stroke="var(--wc-accent)" stroke-dasharray="1 9" stroke-width="3" opacity="0"/>
        <rect class="core" x="268" y="93" width="64" height="64" rx="6" transform="rotate(45 300 125)"/>
        <text class="lbl" x="300" y="210" text-anchor="middle">${t.core}</text>
        <text id="eff" x="300" y="122" text-anchor="middle" style="font-size:12px"></text>
        <text id="effP" x="300" y="138" text-anchor="middle" style="font-size:11px; fill: var(--wc-soft)"></text>
        <g transform="translate(150 80)"><g class="fan" id="f1"><circle r="13" fill="var(--ha-card-background, var(--card-background-color, #111))" stroke="var(--wc-soft)"/><path d="M0 -9 C4 -6 4 -2 0 0 C-4 2 -4 6 0 9 M-9 0 C-6 -4 -2 -4 0 0 C2 4 6 4 9 0" stroke="var(--primary-text-color)" stroke-width="1.6" fill="none"/></g></g>
        <g transform="translate(470 80)"><g class="fan" id="f2"><circle r="13" fill="var(--ha-card-background, var(--card-background-color, #111))" stroke="var(--wc-soft)"/><path d="M0 -9 C4 -6 4 -2 0 0 C-4 2 -4 6 0 9 M-9 0 C-6 -4 -2 -4 0 0 C2 4 6 4 9 0" stroke="var(--primary-text-color)" stroke-width="1.6" fill="none"/></g></g>
        <text class="lbl" x="30" y="62">${t.intake}</text><text class="t" id="tO" x="30" y="44" data-k="outdoor_temperature"></text>
        <text class="lbl" x="30" y="196">${t.exhaust}</text><text class="t" id="tX" x="30" y="214" data-k="exhaust_temperature"></text>
        <text class="lbl" x="600" y="196" text-anchor="end">${t.supply}</text><text class="t" id="tS" x="600" y="152" text-anchor="end" data-k="supply_temperature"></text>
        <text class="lbl" x="600" y="62" text-anchor="end">${t.extract}</text><text class="t" id="tI" x="600" y="44" text-anchor="end" data-k="indoor_temperature"></text>
      </svg>
      <div class="ro">
        <div class="r" data-k="supply_fan_speed"><span class="k">${t.gear}</span><span class="v" id="gear"></span><span class="n" id="gearN"></span></div>
        <div class="r" data-k="supply_airflow"><span class="k">${t.flow}</span><span class="v" id="flow"></span><span class="n" id="flowN"></span></div>
        <div class="r" data-k="heat_recovery_power" id="rbox"><span class="k">${t.recoveryTile}</span><span class="v" id="rec"></span><span class="n" id="recN"></span></div>
        <div class="r" data-k="filter_replacement" id="fbox"><span class="k">${t.filter}</span><span class="v" id="filt"></span><span class="n" id="filtN"></span></div>
      </div>
      <div class="ov" id="ov" hidden><span class="tag" id="ovTag"></span><span id="ovText"></span></div>
      <div class="label">${t.modules}</div><div class="chips" id="mods"></div>
      <div class="label">${t.timed}</div><div class="chips" id="timed"></div>
      <div class="now" id="now" hidden></div>
    </ha-card>`;
    for (const el of root.querySelectorAll("[data-k]")) {
      el.addEventListener("click", () => this._moreInfo(this._id("sensor", el.dataset.k)));
    }
    this._built = true;
    this._sig = "";
  }

  // Today's recovered energy from recorder statistics, at most every five minutes.
  async _fetchToday() {
    const id = this._id("sensor", "heat_recovery_energy");
    if (!id || this._todayBusy || Date.now() - (this._todayAt || 0) < 300000) return;
    this._todayBusy = true;
    try {
      const r = await this._hass.callWS({
        type: "recorder/statistic_during_period", statistic_id: id,
        calendar: { period: "day" }, types: ["change"],
      });
      this._today = typeof r?.change === "number" ? r.change : null;
      this._todayAt = Date.now();
      this._sig = "";
      this._update();
    } catch (e) {
      this._todayAt = Date.now();
    } finally {
      this._todayBusy = false;
    }
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  _signature() {
    // Only the card's own entities decide whether anything needs patching.
    return Object.values(this._e).map((id) => this._hass.states[id]?.state).join("|") + "|" + Math.floor(Date.now() / 60000);
  }

  _update() {
    if (!this._built) return;
    const sig = this._signature();
    if (sig === this._sig) return;
    this._sig = sig;
    const h = this._hass, t = this._t, root = this.shadowRoot, $ = (id) => root.getElementById(id);
    const s = (k) => num(h, this._id("sensor", k));
    const on = (domain, k) => h.states[this._id(domain, k)]?.state === "on";
    const out = s("outdoor_temperature"), exh = s("exhaust_temperature"), sup = s("supply_temperature"), ind = s("indoor_temperature");
    const gear = s("supply_fan_speed") ?? 0, flowS = s("supply_airflow"), flowE = s("exhaust_airflow"), filter = s("filter_replacement");
    const bypass = on("binary_sensor", "bypass_state") || on("switch", "bypass");
    // Recovery sensors when enabled; with the efficiency sensor disabled the ratio is computed here.
    const recId = this._id("sensor", "heat_recovery_power");
    const recState = recId ? h.states[recId] : null;
    const recW = recId ? num(h, recId) : null;
    const cooling = recState?.attributes?.mode === "cooling";
    const effS = this._id("sensor", "heat_recovery_efficiency");
    const eff = effS ? (num(h, effS) == null ? null : num(h, effS) / 100)
      : out != null && ind != null && sup != null && ind !== out ? (sup - out) / (ind - out) : null;
    const effTxt = bypass ? t.bypass : eff == null ? "—" : `${Math.round(Math.max(0, Math.min(1, eff)) * 100)}%`;
    const powTxt = recW == null ? "" : `${cooling ? t.cooling + " " : ""}${fmtKw(recW)} kW`;
    const cur = h.states[this._id("sensor", "current_period")];
    const progSpeed = cur?.attributes?.speed;
    const input3 = on("binary_sensor", "input_speed_3"), input1 = on("binary_sensor", "input_speed_1");
    const filterWarn = filter != null && filter <= 7;

    if (this._config.compact) {
      $("g").textContent = ROMAN[gear] ?? gear;
      $("l2").textContent = `${flowS ?? "—"} m³/h · ${t.supply} ${fmtTemp(sup)} · ${bypass ? t.bypass : `${t.recovery} ${effTxt}${powTxt ? ` · ${powTxt}` : ""}`}`;
      $("rf").textContent = filter == null ? "—" : `${filter} ${t.days}`;
      $("r").classList.toggle("warn", filterWarn);
      return;
    }

    $("tO").textContent = fmtTemp(out); $("tX").textContent = fmtTemp(exh);
    $("tS").textContent = fmtTemp(sup); $("tI").textContent = fmtTemp(ind);
    const col = (v) => {
      if (v == null) return "var(--wc-soft)";
      const k = Math.max(0, Math.min(1, (v + 5) / 30));
      const c = [[124, 179, 249], [231, 165, 154]];
      return `rgb(${c[0].map((x, i) => Math.round(x + (c[1][i] - x) * k)).join(",")})`;
    };
    $("gS0").setAttribute("stop-color", col(out)); $("gS1").setAttribute("stop-color", col(sup));
    $("gE0").setAttribute("stop-color", col(ind)); $("gE1").setAttribute("stop-color", col(exh));
    $("eff").textContent = effTxt;
    $("effP").textContent = bypass ? "" : powTxt;
    const gain = recState?.attributes?.temperature_gain;
    $("rec").innerHTML = recW == null ? "—" : `${fmtKw(recW)}<small>kW</small>`;
    $("recN").textContent = recW == null ? (recId ? t.notRecovering : "")
      : (this._today != null ? t.today(this._today.toFixed(1).replace(".", ",")) : gain != null ? `${cooling ? "−" : "+"}${String(gain).replace(".", ",")} K` : "");
    $("rbox").hidden = !recId;
    this._fetchToday();
    const dur = [0, 3.2, 1.8, 0.9][gear] || 0;
    for (const id of ["dS", "dE"]) { $(id).style.animationDuration = dur ? `${dur}s` : "0s"; $(id).style.opacity = gear ? 1 : 0; }
    for (const id of ["f1", "f2"]) $(id).style.animationDuration = gear ? `${dur * 0.6}s` : "0s";
    $("pB").setAttribute("opacity", bypass ? 0.9 : 0);
    $("pS").style.opacity = bypass ? 0.45 : 1;

    $("gear").textContent = ROMAN[gear] ?? gear;
    const forced = (input3 && gear === 3) || (input1 && gear === 1);
    $("gearN").textContent = (forced ? `${input3 ? t.input3 : t.input1} · ` : "") + (progSpeed != null ? `${t.program}: ${ROMAN[progSpeed]}` : "");
    $("flow").innerHTML = `${flowS ?? "—"}<small>m³/h</small>`;
    $("flowN").textContent = flowE != null ? `${t.extract} ${flowE}` : "";
    $("filt").innerHTML = `${filter ?? "—"}<small>${t.days}</small>`;
    $("filtN").textContent = filterWarn ? t.replaceNow : t.toReplace;
    $("fbox").classList.toggle("warn", filterWarn);
    $("ov").hidden = !(forced && progSpeed != null && progSpeed !== gear);
    $("ovTag").textContent = input3 ? t.input3 : t.input1;
    $("ovText").textContent = t.forced(ROMAN[gear], ROMAN[progSpeed] ?? "–");

    // modules: only the ones this unit has (absent modules have no entity)
    const mods = $("mods"); mods.textContent = "";
    for (const k of MODULES) {
      const id = this._id("switch", k); if (!id) continue;
      const b = document.createElement("button");
      b.className = "chip" + (h.states[id]?.state === "on" ? " on" : "");
      b.innerHTML = `<span class="dot"></span>${t.names[k]}`;
      b.onclick = () => h.callService("switch", "toggle", { entity_id: id });
      mods.append(b);
    }
    const timed = $("timed"); timed.textContent = "";
    for (const [k, counter, unit, max] of TIMED) {
      const id = this._id("switch", k); if (!id) continue;
      const active = h.states[id]?.state === "on";
      const left = num(h, this._id("number", counter));
      const shown = active && left != null ? (unit === "s" ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}` : `${left} ${unit === "d" ? t.days : unit}`)
        : `${max} ${unit === "d" ? t.days : unit}`;
      const b = document.createElement("button");
      b.className = "chip" + (active ? " on" : "");
      b.innerHTML = `<span class="dot"></span>${t.names[k]} <span class="cd">${shown}</span>`;
      b.onclick = () => h.callService("switch", active ? "turn_off" : "turn_on", { entity_id: id });
      timed.append(b);
    }

    const nowEl = $("now");
    if (cur && cur.state && !["unknown", "unavailable"].includes(cur.state)) {
      const a = cur.attributes;
      nowEl.hidden = false;
      nowEl.innerHTML = `${t.now}: <b>${t.period} ${cur.state} · ${a.from}–${a.until} · ${ROMAN[a.speed] ?? a.speed} · ${a.temperature}°</b>`;
    } else nowEl.hidden = true;

    // controller clock: only worth a line when it drifts
    const clk = h.states[this._id("sensor", "controller_clock")];
    const clockEl = $("clock"); clockEl.textContent = "";
    if (clk && !["unknown", "unavailable"].includes(clk.state)) {
      const drift = Math.round((new Date(clk.state).getTime() - Date.now()) / 60000);
      if (Math.abs(drift) > 2) {
        clockEl.append(t.clockOff(drift));
        const btn = this._id("button", "sync_clock");
        if (btn) {
          const b = document.createElement("button"); b.textContent = t.setClock;
          b.onclick = () => h.callService("button", "press", { entity_id: btn });
          clockEl.append(b);
        }
      } else clockEl.textContent = t.clockOk;
    }
  }
}

/* ======================================================================== card 2 */

class WanasScheduleCard extends HTMLElement {
  static getStubConfig() { return {}; }

  static getConfigElement() { return document.createElement("wanas-card-editor"); }

  setConfig(config) {
    this._config = config || {};
    this._week = null; this._saved = null; this._day = (new Date().getDay() + 6) % 7;
    this._sel = 0; this._also = new Set(); this._msg = ""; this._toast = ""; this._loading = false;
    if (this.shadowRoot) this.shadowRoot.innerHTML = "";
  }

  getCardSize() { return 8; }

  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this._t = lang(hass);
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const { device, map } = wanasEntities(hass, this._config?.device_id);
    this._device = device; this._e = map;
    if (first) this._load(false);
    // Only the "now" marker depends on time and the current-period sensor.
    const cur = hass.states[map["sensor:current_period"]]?.state;
    const minute = Math.floor(Date.now() / 60000);
    if (cur !== this._lastCur || minute !== this._lastMin) { this._lastCur = cur; this._lastMin = minute; this._render(); }
  }

  async _load(refresh) {
    if (!this._hass || this._loading) return;
    this._loading = true; this._render();
    try {
      const data = {};
      if (refresh) data.refresh = true;
      const entryId = this._entryId();
      if (entryId) data.config_entry_id = entryId;
      const res = await this._hass.callService("wanas", "get_schedule", data, undefined, false, true);
      const week = res?.response || {};
      this._saved = DAY_KEYS.map((k) => this._fromPeriods(week[k]?.periods));
      this._week = this._saved.map((d) => JSON.parse(JSON.stringify(d)));
      this._msg = "";
    } catch (err) {
      this._msg = `${this._t.readFailed}: ${err?.message || err}`;
    }
    this._loading = false; this._render();
  }

  _entryId() {
    const dev = this._device && this._hass.devices?.[this._device];
    return dev?.config_entries?.[0];
  }

  _fromPeriods(periods) {
    if (!periods || periods.length !== 5) return null;
    return {
      until: periods.slice(0, 4).map((p) => toMin(p.until)),
      speed: periods.map((p) => p.speed),
      temp: periods.map((p) => p.temperature),
    };
  }

  _bounds(d, i) { return [i === 0 ? 0 : d.until[i - 1], i === 4 ? 1440 : d.until[i]]; }
  _dirty(i) { return JSON.stringify(this._week?.[i]) !== JSON.stringify(this._saved?.[i]); }

  _render() {
    const t = this._t, root = this.shadowRoot;
    if (!root) return;
    if (!this._e["sensor:supply_airflow"] && !this._device) {
      root.innerHTML = `<style>${SHARED_CSS}</style><ha-card><div class="empty">${t.noDevice}</div></ha-card>`;
      return;
    }
    const speedColor = (s) => [
      "var(--wc-track)",
      "color-mix(in srgb, var(--wc-accent) 45%, transparent)",
      "color-mix(in srgb, var(--wc-accent) 72%, transparent)",
      "var(--wc-accent)",
    ][s] || "var(--wc-track)";
    const today = (new Date().getDay() + 6) % 7;
    const d = this._week?.[this._day];
    const nowMin = new Date().getHours() * 60 + new Date().getMinutes();

    let body;
    if (!this._week) {
      body = `<div class="empty">${this._loading ? t.reading : this._msg || t.reading}</div>`;
    } else if (!d) {
      body = `<div class="empty">${t.readFailed}</div>`;
    } else {
      const segs = [0, 1, 2, 3, 4].map((i) => {
        const [a, b] = this._bounds(d, i);
        const hgt = [8, 34, 64, 100][d.speed[i]] ?? 8;
        return `<div class="seg ${i === this._sel ? "sel" : ""}" data-sel="${i}" style="width:${(b - a) / 14.4}%"
          title="${t.period} ${i + 1}: ${hm(a)}–${hm(b)}, ${ROMAN[d.speed[i]]}, ${d.temp[i]}°">
          <span class="tp" style="bottom:calc(${hgt}% + 3px)">${d.temp[i]}°</span>
          <div class="bar" style="height:${hgt}%; background:${speedColor(d.speed[i])}"></div></div>`;
      }).join("");
      const rows = [0, 1, 2, 3, 4].map((i) => {
        const [a, b] = this._bounds(d, i);
        const until = i < 4
          ? `<span class="step"><button data-a="u-" data-i="${i}">−</button><span class="tm">${hm(b)}</span><button data-a="u+" data-i="${i}">+</button></span>`
          : `<span class="tm fx">00:00</span>`;
        const speed = `<span class="sg">${[0, 1, 2, 3].map((s) => `<button data-a="s" data-i="${i}" data-v="${s}" class="${d.speed[i] === s ? "on" : ""}">${ROMAN[s]}</button>`).join("")}</span>`;
        const temp = `<span class="step"><button data-a="t-" data-i="${i}" ${d.temp[i] <= 10 ? "disabled" : ""}>−</button><span class="tm">${d.temp[i]}°</span><button data-a="t+" data-i="${i}" ${d.temp[i] >= 30 ? "disabled" : ""}>+</button></span>`;
        return `<tr class="${i === this._sel ? "sel" : ""}"><td class="n">${i + 1}</td><td><span class="tm ${i === 0 ? "fx" : ""}">${hm(a)}</span></td><td>${until}</td><td>${speed}</td><td>${temp}</td></tr>`;
      }).join("");
      const also = [0, 1, 2, 3, 4, 5, 6].filter((i) => i !== this._day)
        .map((i) => `<button class="mini ${this._also.has(i) ? "on" : ""}" data-also="${i}" title="${t.dayLong[i]}">${t.dayShort[i]}</button>`).join("");
      const week = this._week.map((wd, i) => {
        const parts = wd ? [0, 1, 2, 3, 4].map((p) => { const [a, b] = this._bounds(wd, p); return `<i style="width:${(b - a) / 14.4}%; background:${speedColor(wd.speed[p])}"></i>`; }).join("") : "";
        return `<div class="wk ${i === this._day ? "on" : ""}" data-day="${i}"><span>${t.dayShort[i]}</span><span class="ws">${parts}</span></div>`;
      }).join("");
      const changed = this._dirty(this._day) || this._also.size > 0;
      body = `
        <div class="tl">
          <div class="bars">${segs}</div>
          ${this._day === today ? `<div class="nowm" style="left:${nowMin / 14.4}%"></div>` : ""}
          <div class="ax"><span style="left:0">00</span><span style="left:25%">06</span><span style="left:50%">12</span><span style="left:75%">18</span><span style="left:100%">24</span></div>
        </div>
        <table><thead><tr><th></th><th>${t.from}</th><th>${t.to}</th><th>${t.speed}</th><th>${t.temp}</th></tr></thead><tbody>${rows}</tbody></table>
        <div class="msg" role="status">${this._msg}</div>
        <div class="apply"><span>${t.applyAlso}</span>${also}</div>
        <div class="act"><button class="btn" id="undo" ${this._dirty(this._day) ? "" : "disabled"}>${t.undo}</button>
          <button class="btn pri" id="save" ${changed ? "" : "disabled"}>${t.save(this._also.size + 1, t.dayLong[this._day])}</button></div>
        <div class="toast">${this._toast}</div>
        <div class="label">${t.week}</div><div class="week">${week}</div>`;
    }

    const days = [0, 1, 2, 3, 4, 5, 6].map((i) =>
      `<button class="day ${i === this._day ? "on" : ""} ${this._week && this._dirty(i) ? "dirty" : ""}" data-day="${i}" title="${t.dayLong[i]}">${t.dayShort[i]}${i === today ? '<span class="td"></span>' : ""}</button>`).join("");

    root.innerHTML = `<style>${SHARED_CSS}
      .days { display: flex; gap: 4px; flex-wrap: wrap; margin: 10px 0 12px; }
      .day { font: inherit; font-size: 13px; color: var(--wc-soft); background: transparent; border: 1px solid transparent; border-radius: 10px;
        padding: 4px 9px; cursor: pointer; font-variant: small-caps; letter-spacing: 0.05em; }
      .day.on { color: var(--primary-text-color); border-color: var(--wc-line); background: var(--wc-track); }
      .day .td { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--wc-ok); margin-left: 5px; vertical-align: middle; }
      .day.dirty::after { content: "•"; color: var(--wc-accent); margin-left: 3px; }
      .tl { position: relative; height: 108px; }
      .bars { position: absolute; inset: 20px 0 20px 0; display: flex; align-items: flex-end; border-bottom: 1px solid var(--wc-line); }
      .seg { position: relative; height: 100%; display: flex; align-items: flex-end; cursor: pointer; }
      .seg .bar { width: 100%; margin-inline: 1px; border-radius: 6px 6px 0 0; transition: height .25s; }
      .seg.sel .bar { box-shadow: 0 0 0 1px var(--primary-text-color) inset; }
      .seg .tp { position: absolute; left: 0; right: 0; text-align: center; font-family: var(--wc-mono); font-size: 11px; color: var(--wc-soft); }
      .nowm { position: absolute; top: 12px; bottom: 18px; border-left: 1px dashed var(--wc-ok); pointer-events: none; }
      .ax { position: absolute; left: 0; right: 0; bottom: 0; height: 16px; font-family: var(--wc-mono); font-size: 10px; color: var(--wc-soft); }
      .ax span { position: absolute; transform: translateX(-50%); } .ax span:first-child { transform: none; } .ax span:last-child { transform: translateX(-100%); }
      table { width: 100%; border-collapse: collapse; margin-top: 8px; }
      th { text-align: left; font-weight: 400; font-size: 12px; color: var(--wc-soft); padding: 5px 3px; border-bottom: 1px solid var(--wc-line);
        font-variant: small-caps; letter-spacing: 0.05em; }
      td { padding: 6px 3px; border-bottom: 1px solid var(--wc-line); }
      tr.sel td { background: color-mix(in srgb, var(--wc-accent) 6%, transparent); }
      td.n { font-family: var(--wc-mono); font-size: 12px; color: var(--wc-soft); width: 18px; }
      .tm { font-family: var(--wc-mono); font-size: 14px; font-variant-numeric: tabular-nums; min-width: 46px; display: inline-block; text-align: center; }
      .tm.fx { color: var(--wc-soft); text-align: left; }
      .step { display: inline-flex; align-items: center; gap: 2px; white-space: nowrap; }
      .step button { font: inherit; font-family: var(--wc-mono); width: 26px; height: 26px; border-radius: 8px; border: 1px solid var(--wc-line);
        background: transparent; color: var(--wc-soft); cursor: pointer; }
      .step button:disabled { opacity: .3; cursor: default; }
      .sg { display: inline-flex; border: 1px solid var(--wc-line); border-radius: 9px; overflow: hidden; }
      .sg button { font: inherit; font-family: var(--wc-mono); font-size: 12px; color: var(--wc-soft); background: transparent; border: 0;
        padding: 4px 8px; min-width: 30px; cursor: pointer; }
      .sg button + button { border-left: 1px solid var(--wc-line); }
      .sg button.on { background: color-mix(in srgb, var(--wc-accent) 20%, transparent); color: var(--primary-text-color); }
      .msg { min-height: 18px; font-size: 12.5px; margin-top: 6px; color: var(--wc-warn); }
      .apply { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 8px; font-size: 12px; color: var(--wc-soft); }
      .mini { font: inherit; font-size: 12px; font-variant: small-caps; color: var(--wc-soft); background: transparent; border: 1px solid var(--wc-line);
        border-radius: 8px; padding: 2px 7px; cursor: pointer; }
      .mini.on { color: var(--primary-text-color); border-color: var(--wc-accent); background: color-mix(in srgb, var(--wc-accent) 14%, transparent); }
      .act { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; flex-wrap: wrap; }
      .btn { font: inherit; font-size: 13px; border-radius: 10px; padding: 6px 13px; cursor: pointer; border: 1px solid var(--wc-line);
        background: transparent; color: var(--wc-soft); }
      .btn.pri { background: var(--wc-accent); border-color: var(--wc-accent); color: var(--text-primary-color, #fff); font-weight: 600; }
      .btn:disabled { opacity: .4; cursor: default; }
      .toast { font-family: var(--wc-mono); font-size: 12px; color: var(--wc-ok); min-height: 16px; text-align: right; margin-top: 4px; }
      .week { display: grid; gap: 4px; }
      .wk { display: grid; grid-template-columns: 30px minmax(0,1fr); gap: 8px; align-items: center; cursor: pointer; font-size: 11px;
        color: var(--wc-soft); font-variant: small-caps; }
      .wk.on { color: var(--primary-text-color); }
      .ws { display: flex; height: 10px; border-radius: 3px; overflow: hidden; background: var(--wc-track); }
      .ws i { display: block; height: 100%; border-right: 1px solid var(--ha-card-background, var(--card-background-color, #000)); }
      .scroll { overflow-x: auto; }
    </style>
    <ha-card>
      <div class="head"><h2>${t.schedule}</h2><span class="sub"><button id="reload">${t.readFromUnit}</button></span></div>
      <div class="days">${days}</div>
      <div class="scroll">${body}</div>
    </ha-card>`;
    this._wire();
  }

  _wire() {
    const root = this.shadowRoot;
    root.getElementById("reload")?.addEventListener("click", () => this._load(true));
    for (const el of root.querySelectorAll("[data-day]")) {
      el.addEventListener("click", () => { this._day = +el.dataset.day; this._sel = 0; this._also.clear(); this._msg = ""; this._render(); });
    }
    for (const el of root.querySelectorAll("[data-sel]")) el.addEventListener("click", () => { this._sel = +el.dataset.sel; this._render(); });
    for (const el of root.querySelectorAll("[data-also]")) {
      el.addEventListener("click", () => { const i = +el.dataset.also; this._also.has(i) ? this._also.delete(i) : this._also.add(i); this._render(); });
    }
    for (const el of root.querySelectorAll("button[data-a]")) el.addEventListener("click", () => this._edit(el.dataset.a, +el.dataset.i, +el.dataset.v));
    root.getElementById("undo")?.addEventListener("click", () => {
      this._week[this._day] = JSON.parse(JSON.stringify(this._saved[this._day])); this._msg = ""; this._render();
    });
    root.getElementById("save")?.addEventListener("click", () => this._save());
  }

  _edit(action, i, v) {
    const d = this._week[this._day], t = this._t;
    this._sel = i; this._msg = "";
    if (action === "u-" || action === "u+") {
      const next = d.until[i] + (action === "u+" ? 15 : -15);
      const lo = i === 0 ? 0 : d.until[i - 1], hi = i === 3 ? 1440 : d.until[i + 1];
      if (next < 15 || next > 1425) this._msg = t.errGrid(i + 1, hm(next));
      else if (next <= lo) this._msg = t.errBefore(i + 1, hm(next), i, hm(lo));
      else if (next >= hi) this._msg = t.errAfter(i + 1, hm(next), i + 2, hm(hi));
      else d.until[i] = next;
    } else if (action === "s") d.speed[i] = v;
    else if (action === "t-") d.temp[i] = Math.max(10, d.temp[i] - 1);
    else if (action === "t+") d.temp[i] = Math.min(30, d.temp[i] + 1);
    this._render();
  }

  async _save() {
    const t = this._t, d = this._week[this._day];
    const targets = [this._day, ...[...this._also].sort((a, b) => a - b)];
    const data = {
      days: targets.map((i) => DAY_KEYS[i]),
      periods: [0, 1, 2, 3, 4].map((i) => (i < 4
        ? { until: hm(d.until[i]), speed: d.speed[i], temperature: d.temp[i] }
        : { speed: d.speed[i], temperature: d.temp[i] })),
    };
    const entryId = this._entryId();
    if (entryId) data.config_entry_id = entryId;
    try {
      await this._hass.callService("wanas", "set_schedule", data);
      for (const i of targets) { this._week[i] = JSON.parse(JSON.stringify(d)); this._saved[i] = JSON.parse(JSON.stringify(d)); }
      this._also.clear();
      this._toast = t.saved(targets.map((i) => t.dayLong[i]).join(", "));
      setTimeout(() => { this._toast = ""; this._render(); }, 4000);
    } catch (err) {
      this._msg = err?.message || String(err);
    }
    this._render();
  }
}

/* ======================================================================== editor */

/** Visual editor shared by both cards: the unit, and for wanas-card the compact tile. */
class WanasCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...(config || {}) };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = lang(this._hass);
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => (s.name === "device_id" ? t.edDevice : t.edCompact);
      this._form.addEventListener("value-changed", (ev) => {
        const config = { ...this._config, ...ev.detail.value };
        for (const key of ["device_id", "compact"]) {
          if (config[key] === undefined || config[key] === "" || config[key] === false) delete config[key];
        }
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      { name: "device_id", selector: { device: { integration: "wanas" } } },
      ...(this.compactOption ? [{ name: "compact", selector: { boolean: {} } }] : []),
    ];
  }
}

// Home Assistant's app bundle replaces window.customElements with a scoped-registry
// polyfill, and this module (add_extra_js_url) loads in parallel with it. Defined before
// the swap, the cards land in the native registry the polyfill does not consult, and
// Lovelace shows "Configuration error" on some page loads. <home-assistant> is defined
// after the polyfill is in place, so wait for it and define on whatever registry is
// current then.
function defineCards() {
  const registry = window.customElements;
  if (!registry.get("wanas-card")) registry.define("wanas-card", WanasCard);
  if (!registry.get("wanas-schedule-card")) registry.define("wanas-schedule-card", WanasScheduleCard);
  if (!registry.get("wanas-card-editor")) registry.define("wanas-card-editor", WanasCardEditor);
}
window.customElements.whenDefined("home-assistant").then(defineCards);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "wanas-card")) {
  window.customCards.push(
    { type: "wanas-card", name: "Wanas", description: "Heat recovery unit: airflow, temperatures, modules.", preview: true },
    { type: "wanas-schedule-card", name: "Wanas schedule", description: "Weekly schedule as five periods per day.", preview: true },
  );
}
console.info(`%c WANAS-CARDS %c ${VERSION} `, "background:#5ca5ff;color:#061224;font-weight:600", "background:#222;color:#ddd");
