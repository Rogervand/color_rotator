/* Color Rotator card — served by the color_rotator integration. No build step. */
const CR_VERSION = "1.0.1";
const MIN_INTERVAL = 5;
const MAX_INTERVAL = 8 * 3600;
const RGB_MODES = ["hs", "xy", "rgb", "rgbw", "rgbww"];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/* The standard CSS / HTML named colors, grouped by family. */
const NAMED_COLORS = {
  Reds: { indianred: "cd5c5c", lightcoral: "f08080", salmon: "fa8072", darksalmon: "e9967a", lightsalmon: "ffa07a", crimson: "dc143c", red: "ff0000", firebrick: "b22222", darkred: "8b0000" },
  Pinks: { pink: "ffc0cb", lightpink: "ffb6c1", hotpink: "ff69b4", deeppink: "ff1493", mediumvioletred: "c71585", palevioletred: "db7093" },
  Oranges: { coral: "ff7f50", tomato: "ff6347", orangered: "ff4500", darkorange: "ff8c00", orange: "ffa500" },
  Yellows: { gold: "ffd700", yellow: "ffff00", lightyellow: "ffffe0", lemonchiffon: "fffacd", lightgoldenrodyellow: "fafad2", papayawhip: "ffefd5", moccasin: "ffe4b5", peachpuff: "ffdab9", palegoldenrod: "eee8aa", khaki: "f0e68c", darkkhaki: "bdb76b" },
  Purples: { lavender: "e6e6fa", thistle: "d8bfd8", plum: "dda0dd", violet: "ee82ee", orchid: "da70d6", fuchsia: "ff00ff", magenta: "ff00ff", mediumorchid: "ba55d3", mediumpurple: "9370db", rebeccapurple: "663399", blueviolet: "8a2be2", darkviolet: "9400d3", darkorchid: "9932cc", darkmagenta: "8b008b", purple: "800080", indigo: "4b0082", slateblue: "6a5acd", darkslateblue: "483d8b", mediumslateblue: "7b68ee" },
  Greens: { greenyellow: "adff2f", chartreuse: "7fff00", lawngreen: "7cfc00", lime: "00ff00", limegreen: "32cd32", palegreen: "98fb98", lightgreen: "90ee90", mediumspringgreen: "00fa9a", springgreen: "00ff7f", mediumseagreen: "3cb371", seagreen: "2e8b57", forestgreen: "228b22", green: "008000", darkgreen: "006400", yellowgreen: "9acd32", olivedrab: "6b8e23", olive: "808000", darkolivegreen: "556b2f", mediumaquamarine: "66cdaa", darkseagreen: "8fbc8f", lightseagreen: "20b2aa", darkcyan: "008b8b", teal: "008080" },
  Blues: { aqua: "00ffff", cyan: "00ffff", lightcyan: "e0ffff", paleturquoise: "afeeee", aquamarine: "7fffd4", turquoise: "40e0d0", mediumturquoise: "48d1cc", darkturquoise: "00ced1", cadetblue: "5f9ea0", steelblue: "4682b4", lightsteelblue: "b0c4de", powderblue: "b0e0e6", lightblue: "add8e6", skyblue: "87ceeb", lightskyblue: "87cefa", deepskyblue: "00bfff", dodgerblue: "1e90ff", cornflowerblue: "6495ed", royalblue: "4169e1", blue: "0000ff", mediumblue: "0000cd", darkblue: "00008b", navy: "000080", midnightblue: "191970" },
  Browns: { cornsilk: "fff8dc", blanchedalmond: "ffebcd", bisque: "ffe4c4", navajowhite: "ffdead", wheat: "f5deb3", burlywood: "deb887", tan: "d2b48c", rosybrown: "bc8f8f", sandybrown: "f4a460", goldenrod: "daa520", darkgoldenrod: "b8860b", peru: "cd853f", chocolate: "d2691e", saddlebrown: "8b4513", sienna: "a0522d", brown: "a52a2a", maroon: "800000" },
  Whites: { white: "ffffff", snow: "fffafa", honeydew: "f0fff0", mintcream: "f5fffa", azure: "f0ffff", aliceblue: "f0f8ff", ghostwhite: "f8f8ff", whitesmoke: "f5f5f5", seashell: "fff5ee", beige: "f5f5dc", oldlace: "fdf5e6", floralwhite: "fffaf0", ivory: "fffff0", antiquewhite: "faebd7", linen: "faf0e6", lavenderblush: "fff0f5", mistyrose: "ffe4e1" },
  Grays: { gainsboro: "dcdcdc", lightgray: "d3d3d3", silver: "c0c0c0", darkgray: "a9a9a9", gray: "808080", dimgray: "696969", lightslategray: "778899", slategray: "708090", darkslategray: "2f4f4f", black: "000000" },
};

const hexToRgb = (hex) => {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.substr(i, 2), 16));
};
const rgbToHex = (rgb) => "#" + rgb.map((v) => v.toString(16).padStart(2, "0")).join("");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clone = (o) => JSON.parse(JSON.stringify(o));
const nameForHex = (hex) => {
  const h = hex.replace("#", "").toLowerCase();
  for (const fam of Object.values(NAMED_COLORS)) for (const [n, v] of Object.entries(fam)) if (v === h) return n;
  return "";
};

const fmtDuration = (secs) => {
  secs = Math.max(0, Math.round(secs));
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60;
  if (h) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
};

const fmtWhen = (iso, hass) => {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const locale = hass?.locale?.language || navigator.language;
  const time = d.toLocaleTimeString(locale, { hour: "numeric", minute: "2-digit" });
  const dayDiff = Math.round((new Date(d.toDateString()) - new Date(now.toDateString())) / 86400000);
  if (dayDiff === 0) return `today ${time}`;
  if (dayDiff === 1) return `tomorrow ${time}`;
  return `${d.toLocaleDateString(locale, { weekday: "short" })} ${time}`;
};

const INTERVAL_UNITS = { s: 1, min: 60, h: 3600 };
const bestUnit = (secs) => (secs % 3600 === 0 ? "h" : secs % 60 === 0 ? "min" : "s");

const STYLE = `
  :host { --cr-gap: 12px; }
  ha-card { padding: 16px; }
  .header { display: flex; align-items: center; gap: 12px; }
  .title { font-size: 1.15em; font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pill { font-size: 0.75em; padding: 3px 10px; border-radius: 999px; background: var(--secondary-background-color); color: var(--secondary-text-color); white-space: nowrap; }
  .pill.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .status { display: flex; align-items: center; gap: 10px; margin-top: 10px; color: var(--secondary-text-color); font-size: 0.9em; flex-wrap: wrap; }
  .dot { width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--divider-color); flex: none; }
  .strip { display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-top: 12px; border: 1px solid var(--divider-color); }
  .strip span { flex: 1; }
  .strip span.cur { flex: 2.5; }
  .controls { display: flex; gap: 8px; margin-top: 12px; }
  button { font: inherit; cursor: pointer; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); padding: 7px 14px; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  button.ghost { border: none; background: none; padding: 4px 6px; color: var(--secondary-text-color); }
  button:disabled { opacity: 0.45; cursor: default; }
  details { border-top: 1px solid var(--divider-color); margin-top: 14px; padding-top: 10px; }
  summary { cursor: pointer; font-weight: 500; list-style: none; display: flex; align-items: center; gap: 8px; }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▸"; color: var(--secondary-text-color); transition: transform .15s; }
  details[open] summary::before { transform: rotate(90deg); }
  summary .sub { font-weight: 400; color: var(--secondary-text-color); font-size: 0.85em; margin-left: auto; }
  .body { padding-top: 10px; display: grid; gap: var(--cr-gap); }
  .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .row > label { min-width: 110px; color: var(--secondary-text-color); font-size: 0.9em; }
  select, input[type=text], input[type=number], input[type=time] { font: inherit; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
  input[type=number] { width: 80px; }
  input[type=range] { flex: 1; min-width: 100px; accent-color: var(--primary-color); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 4px 3px 10px; border-radius: 999px; background: var(--secondary-background-color); font-size: 0.9em; }
  .chip.off { opacity: .55; }
  .colors { display: grid; gap: 6px; }
  .crow { display: flex; align-items: center; gap: 8px; }
  .crow .sw { width: 28px; height: 28px; border-radius: 6px; border: 1px solid var(--divider-color); flex: none; }
  .crow .nm { width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.9em; }
  .crow .pct { width: 40px; text-align: right; font-variant-numeric: tabular-nums; font-size: 0.85em; color: var(--secondary-text-color); }
  .dim { opacity: 0.4; pointer-events: none; }
  .palette { border: 1px solid var(--divider-color); border-radius: 8px; padding: 10px; display: grid; gap: 8px; max-height: 320px; overflow: auto; }
  .fam { font-size: 0.75em; text-transform: uppercase; letter-spacing: .05em; color: var(--secondary-text-color); }
  .swatches { display: flex; flex-wrap: wrap; gap: 4px; }
  .swatches button { width: 24px; height: 24px; padding: 0; border-radius: 5px; border: 1px solid var(--divider-color); }
  .seg { display: inline-flex; border: 1px solid var(--divider-color); border-radius: 8px; overflow: hidden; }
  .seg button { border: none; border-radius: 0; padding: 6px 12px; }
  .seg button.sel { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .days button { padding: 5px 9px; }
  .hint { font-size: 0.8em; color: var(--secondary-text-color); }
  .err { color: var(--error-color, #db4437); font-size: 0.9em; }
  .savebar { position: sticky; bottom: 0; display: flex; align-items: center; gap: 8px; justify-content: flex-end; margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--divider-color); background: var(--card-background-color); }
  .savebar .msg { margin-right: auto; color: var(--secondary-text-color); font-size: 0.9em; }
  .empty { color: var(--secondary-text-color); padding: 8px 0; }
`;

class ColorRotatorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._open = { lights: false, colors: false, timing: false, schedule: false };
    this._showPalette = false;
    this._dirty = false;
    this._error = "";
    this._intervalUnit = null;
    this._lastSwitch = null;
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
    this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
    this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
    this.shadowRoot.addEventListener("toggle", (e) => {
      const d = e.target;
      if (d.tagName === "DETAILS" && d.dataset.sec) this._open[d.dataset.sec] = d.open;
    }, true);
  }

  static getConfigElement() { return document.createElement("color-rotator-card-editor"); }
  static getStubConfig() { return { entry_id: "" }; }

  setConfig(config) {
    const changed = !this._config || this._config.entry_id !== config.entry_id;
    this._config = { ...config };
    if (changed) { this._group = null; this._draft = null; this._loadError = ""; this._loading = false; }
    this._render();
    if (changed && this._hass) this._load();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (!this._config) return;
    if (first || (!this._group && !this._loading && !this._loadError)) { this._load(); return; }
    this._syncFromSwitch();
  }

  getCardSize() { return 3; }

  connectedCallback() { this._timer = setInterval(() => this._tickCountdown(), 1000); }
  disconnectedCallback() { clearInterval(this._timer); }

  /* ---------------- data ---------------- */
  async _load() {
    if (!this._config?.entry_id || !this._hass) { this._render(); return; }
    this._loading = true;
    try {
      const g = await this._hass.callWS({ type: "color_rotator/get", entry_id: this._config.entry_id });
      this._setGroup(g, true);
      this._loadError = "";
    } catch (err) {
      this._loadError = err.message || String(err);
    }
    this._loading = false;
    this._render();
  }

  _setGroup(g, resetDraft) {
    this._group = g;
    if (resetDraft || !this._dirty) {
      this._draft = clone(g.settings);
      this._dirty = false;
      this._intervalUnit = bestUnit(this._draft.interval);
    }
  }

  async _syncFromSwitch() {
    const id = this._group?.switch_entity_id;
    const st = id && this._hass.states[id];
    if (!st || st === this._lastSwitch) return;
    const prev = this._lastSwitch;
    this._lastSwitch = st;
    // If another card or the UI changed this group's settings, pick them up (only when not editing)
    const structural = !prev || prev.attributes.color_count !== st.attributes.color_count ||
      prev.attributes.interval !== st.attributes.interval ||
      JSON.stringify(prev.attributes.entities) !== JSON.stringify(st.attributes.entities);
    if (structural && !this._dirty && prev) {
      try {
        const g = await this._hass.callWS({ type: "color_rotator/get", entry_id: this._config.entry_id });
        if (JSON.stringify(g.settings) !== JSON.stringify(this._group.settings)) { this._setGroup(g, false); this._render(); return; }
      } catch (_) { /* ignore */ }
    }
    this._renderStatus();
  }

  _status() {
    const id = this._group?.switch_entity_id;
    const st = id && this._hass?.states[id];
    if (st) return { running: st.state === "on", ...st.attributes };
    return this._group?.status || {};
  }

  async _control(action) {
    try {
      const g = await this._hass.callWS({ type: "color_rotator/control", entry_id: this._config.entry_id, action });
      this._group.status = g.status;
      this._renderStatus();
    } catch (err) { this._error = err.message; this._render(); }
  }

  async _save() {
    const d = this._draft;
    if (d.interval < MIN_INTERVAL || d.interval > MAX_INTERVAL) {
      this._error = "Interval must be between 5 seconds and 8 hours.";
      this._render();
      return;
    }
    this._saving = true; this._error = ""; this._render();
    try {
      const g = await this._hass.callWS({ type: "color_rotator/update", entry_id: this._config.entry_id, settings: d });
      this._setGroup(g, true);
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._saving = false;
    this._render();
  }

  _touch() { this._dirty = true; this._error = ""; }

  /* ---------------- events ---------------- */
  _onClick(e) {
    const el = e.target.closest("[data-a]");
    if (!el) return;
    const a = el.dataset.a, i = el.dataset.i !== undefined ? Number(el.dataset.i) : null;
    const d = this._draft;
    switch (a) {
      case "start": return this._control("start");
      case "stop": return this._control("stop");
      case "skip": return this._control("skip");
      case "save": return this._save();
      case "discard": this._draft = clone(this._group.settings); this._dirty = false; this._error = ""; this._intervalUnit = bestUnit(this._draft.interval); break;
      case "rm-entity": d.entities.splice(i, 1); this._touch(); break;
      case "add-entity": {
        const sel = this.shadowRoot.getElementById("entity-select");
        if (sel?.value && !d.entities.includes(sel.value)) { d.entities.push(sel.value); this._touch(); }
        break;
      }
      case "palette": this._showPalette = !this._showPalette; break;
      case "pick": d.colors.push({ name: el.dataset.name, rgb: hexToRgb(el.dataset.hex), brightness: 100 }); this._touch(); break;
      case "add-hex": {
        const v = this.shadowRoot.getElementById("hex-input").value;
        d.colors.push({ name: nameForHex(v) || v.toUpperCase(), rgb: hexToRgb(v), brightness: 100 });
        this._touch();
        break;
      }
      case "c-up": if (i > 0) { [d.colors[i - 1], d.colors[i]] = [d.colors[i], d.colors[i - 1]]; this._touch(); } break;
      case "c-down": if (i < d.colors.length - 1) { [d.colors[i + 1], d.colors[i]] = [d.colors[i], d.colors[i + 1]]; this._touch(); } break;
      case "c-rm": d.colors.splice(i, 1); this._touch(); break;
      case "set": {
        const path = el.dataset.path; let val = el.dataset.v;
        if (val === "true" || val === "false") val = val === "true";
        this._setPath(path, val); this._touch(); break;
      }
      case "day": {
        const days = d.schedule.days;
        const k = days.indexOf(i);
        if (k >= 0) days.splice(k, 1); else days.push(i);
        days.sort(); this._touch(); break;
      }
      default: return;
    }
    this._render();
  }

  _onInput(e) {
    const el = e.target;
    if (el.dataset.cb !== undefined) {
      const i = Number(el.dataset.cb);
      this._draft.colors[i].brightness = Number(el.value);
      const lbl = this.shadowRoot.getElementById(`cbp-${i}`);
      if (lbl) lbl.textContent = `${el.value}%`;
      this._touch(); this._renderSaveBar();
    } else if (el.dataset.path === "global_brightness") {
      this._draft.global_brightness = Number(el.value);
      const lbl = this.shadowRoot.getElementById("gbp");
      if (lbl) lbl.textContent = `${el.value}%`;
      this._touch(); this._renderSaveBar();
    }
  }

  _onChange(e) {
    const el = e.target;
    if (el.dataset.cb !== undefined || el.id === "entity-select" || el.id === "hex-input") return;
    const path = el.dataset.path;
    if (!path) return;
    const d = this._draft;
    if (path === "interval_value" || path === "interval_unit") {
      if (path === "interval_unit") this._intervalUnit = el.value;
      const v = Number(this.shadowRoot.getElementById("iv").value) || 0;
      d.interval = Math.round(v * INTERVAL_UNITS[this._intervalUnit]);
    } else if (el.type === "checkbox") {
      this._setPath(path, el.checked);
    } else if (el.type === "number" || el.type === "range") {
      this._setPath(path, Number(el.value));
    } else {
      this._setPath(path, el.value);
    }
    this._touch();
    this._render();
  }

  _setPath(path, val) {
    const parts = path.split(".");
    let o = this._draft;
    for (const p of parts.slice(0, -1)) o = o[p];
    o[parts.at(-1)] = val;
  }

  /* ---------------- rendering ---------------- */
  _lights() {
    if (!this._hass) return [];
    return Object.values(this._hass.states)
      .filter((s) => s.entity_id.startsWith("light.") && (s.attributes.supported_color_modes || []).some((m) => RGB_MODES.includes(m)))
      .map((s) => ({ id: s.entity_id, name: s.attributes.friendly_name || s.entity_id }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  _render() {
    const root = this.shadowRoot;
    const scrollTop = root.querySelector(".palette")?.scrollTop;
    root.innerHTML = `<style>${STYLE}</style><ha-card>${this._content()}</ha-card>`;
    if (scrollTop) { const p = root.querySelector(".palette"); if (p) p.scrollTop = scrollTop; }
  }

  _content() {
    if (!this._config?.entry_id) return `<div class="empty">Pick a rotation group in the card editor.</div>`;
    if (this._loadError) return `<div class="err">Color Rotator: ${esc(this._loadError)}</div>`;
    if (!this._group || !this._draft) return `<div class="empty">Loading…</div>`;
    return `
      <div id="status">${this._statusHtml()}</div>
      ${this._lightsHtml()}
      ${this._colorsHtml()}
      ${this._timingHtml()}
      ${this._scheduleHtml()}
      <div id="savebar">${this._saveBarHtml()}</div>`;
  }

  _statusHtml() {
    const s = this._status();
    const running = !!s.running;
    const colors = this._group.settings.colors;
    const cur = s.current_color;
    let pill = running ? (s.manual ? "Running · manual" : "Running") : "Idle";
    let sched = "";
    if (s.schedule_enabled && s.next_schedule_event) {
      sched = `${s.next_schedule_is_start ? "Starts" : "Ends"} ${fmtWhen(s.next_schedule_event, this._hass)}`;
    } else if (s.schedule_enabled) sched = "No upcoming schedule window";
    const curIdx = cur ? cur.index : -1;
    const strip = colors.length
      ? `<div class="strip">${colors.map((c, i) => `<span class="${i === curIdx ? "cur" : ""}" style="background:${rgbToHex(c.rgb)}"></span>`).join("")}</div>`
      : "";
    return `
      <div class="header">
        <div class="title">${esc(this._config.title || this._group.title)}</div>
        <span class="pill ${running ? "on" : ""}">${pill}</span>
      </div>
      <div class="status">
        ${cur ? `<span class="dot" style="background:${cur.hex}"></span><span>${esc(cur.name || cur.hex)}</span>` : ""}
        ${running && s.next_change ? `<span>· next in <span id="cd" data-t="${s.next_change}">${fmtDuration((new Date(s.next_change) - Date.now()) / 1000)}</span></span>` : ""}
        ${sched ? `<span>${running || cur ? "· " : ""}${sched}</span>` : ""}
      </div>
      ${strip}
      <div class="controls">
        ${running
          ? `<button data-a="stop">Stop</button><button data-a="skip">Next color</button>`
          : `<button class="primary" data-a="start" ${colors.length && this._group.settings.entities.length ? "" : "disabled"}>Start</button>`}
      </div>`;
  }

  _renderStatus() {
    const el = this.shadowRoot.getElementById("status");
    if (el) el.innerHTML = this._statusHtml();
  }

  _tickCountdown() {
    const el = this.shadowRoot.getElementById("cd");
    if (el) el.textContent = fmtDuration((new Date(el.dataset.t) - Date.now()) / 1000);
  }

  _section(key, title, sub, body) {
    return `<details data-sec="${key}" ${this._open[key] ? "open" : ""}>
      <summary>${title}<span class="sub">${sub}</span></summary>
      <div class="body">${body}</div></details>`;
  }

  _lightsHtml() {
    const d = this._draft;
    const lights = this._lights();
    const names = Object.fromEntries(lights.map((l) => [l.id, l.name]));
    const avail = lights.filter((l) => !d.entities.includes(l.id));
    const chips = d.entities.length
      ? `<div class="chips">${d.entities.map((id, i) => {
          const st = this._hass.states[id];
          const off = !st || st.state === "unavailable";
          return `<span class="chip ${off ? "off" : ""}" title="${esc(id)}">${esc(names[id] || st?.attributes.friendly_name || id)}${off ? " (unavailable)" : ""}<button class="ghost" data-a="rm-entity" data-i="${i}" aria-label="Remove">✕</button></span>`;
        }).join("")}</div>`
      : `<div class="hint">No lights yet.</div>`;
    const body = `${chips}
      <div class="row">
        <select id="entity-select">${avail.length ? avail.map((l) => `<option value="${esc(l.id)}">${esc(l.name)}</option>`).join("") : `<option value="">No more color lights</option>`}</select>
        <button data-a="add-entity" ${avail.length ? "" : "disabled"}>Add</button>
      </div>
      <div class="hint">Only lights that support RGB color are listed.</div>`;
    return this._section("lights", "Lights", `${d.entities.length} selected`, body);
  }

  _colorsHtml() {
    const d = this._draft;
    const g = d.global_brightness_enabled;
    const rows = d.colors.length
      ? `<div class="colors ${""}">${d.colors.map((c, i) => `
          <div class="crow">
            <span class="sw" style="background:${rgbToHex(c.rgb)}"></span>
            <span class="nm" title="${esc(c.name)}">${esc(c.name || rgbToHex(c.rgb))}</span>
            <input type="range" min="1" max="100" value="${c.brightness}" data-cb="${i}" class="${g ? "dim" : ""}" aria-label="Brightness">
            <span class="pct ${g ? "dim" : ""}" id="cbp-${i}">${c.brightness}%</span>
            <button class="ghost" data-a="c-up" data-i="${i}" ${i === 0 ? "disabled" : ""} aria-label="Move up">▲</button>
            <button class="ghost" data-a="c-down" data-i="${i}" ${i === d.colors.length - 1 ? "disabled" : ""} aria-label="Move down">▼</button>
            <button class="ghost" data-a="c-rm" data-i="${i}" aria-label="Remove">✕</button>
          </div>`).join("")}</div>`
      : `<div class="hint">No colors yet. Add some from the palette.</div>`;
    const palette = this._showPalette
      ? `<div class="palette">${Object.entries(NAMED_COLORS).map(([fam, cols]) => `
          <div><div class="fam">${fam}</div><div class="swatches">${Object.entries(cols).map(([n, h]) =>
            `<button data-a="pick" data-name="${n}" data-hex="${h}" title="${n}" style="background:#${h}"></button>`).join("")}</div></div>`).join("")}
          <div class="row"><input type="color" id="hex-input" value="#ff8800"><button data-a="add-hex">Add custom color</button></div>
        </div>`
      : "";
    const body = `${rows}
      <div class="row"><button data-a="palette">${this._showPalette ? "Close palette" : "Add colors"}</button></div>
      ${palette}
      <div class="row">
        <label><input type="checkbox" data-path="global_brightness_enabled" ${g ? "checked" : ""}> Global brightness</label>
        <input type="range" min="1" max="100" value="${d.global_brightness}" data-path="global_brightness" class="${g ? "" : "dim"}">
        <span class="pct ${g ? "" : "dim"}" id="gbp" style="width:40px;text-align:right">${d.global_brightness}%</span>
      </div>
      ${g ? `<div class="hint">Global brightness overrides each color's brightness.</div>` : ""}`;
    return this._section("colors", "Colors", `${d.colors.length} color${d.colors.length === 1 ? "" : "s"}`, body);
  }

  _seg(path, current, opts) {
    return `<span class="seg">${opts.map(([v, l]) =>
      `<button class="${String(current) === String(v) ? "sel" : ""}" data-a="set" data-path="${path}" data-v="${v}">${l}</button>`).join("")}</span>`;
  }

  _timingHtml() {
    const d = this._draft;
    const unit = this._intervalUnit || bestUnit(d.interval);
    const val = +(d.interval / INTERVAL_UNITS[unit]).toFixed(2);
    const bad = d.interval < MIN_INTERVAL || d.interval > MAX_INTERVAL;
    const body = `
      <div class="row"><label>Interval</label>
        <input type="number" id="iv" min="0" step="any" value="${val}" data-path="interval_value">
        <select data-path="interval_unit">${Object.keys(INTERVAL_UNITS).map((u) => `<option value="${u}" ${u === unit ? "selected" : ""}>${u === "s" ? "seconds" : u === "min" ? "minutes" : "hours"}</option>`).join("")}</select>
      </div>
      ${bad ? `<div class="err">Interval must be between 5 seconds and 8 hours.</div>` : ""}
      <div class="row"><label>Fade</label>
        <input type="number" min="0" max="300" step="0.5" value="${d.transition}" data-path="transition"><span class="hint">seconds (0 = snap)</span>
      </div>
      <div class="row"><label>Order</label>${this._seg("order", d.order, [["sequential", "In order"], ["random", "Random"]])}</div>
      ${d.order === "random" ? `<div class="row"><label></label><label style="min-width:0"><input type="checkbox" data-path="avoid_repeat" ${d.avoid_repeat ? "checked" : ""}> Never repeat a color twice in a row</label></div>` : ""}
      <div class="row"><label>Lights</label>${this._seg("mode", d.mode, [["sync", "Same color"], ["offset", "Offset (chase)"]])}</div>
      <div class="hint">${d.mode === "offset" ? "Each light shows the next color along the list, so the colors chase across the lights." : "All lights show the same color together."}</div>`;
    const sub = `every ${fmtDuration(d.interval).replace(/^0:/, "")} · ${d.order === "random" ? "random" : "in order"}`;
    return this._section("timing", "Timing", sub, body);
  }

  _triggerHtml(key) {
    const t = this._draft.schedule[key];
    const p = `schedule.${key}`;
    return `<div class="row"><label>${key === "start" ? "Start" : "End"}</label>
      <select data-path="${p}.type">
        <option value="time" ${t.type === "time" ? "selected" : ""}>At time</option>
        <option value="sunrise" ${t.type === "sunrise" ? "selected" : ""}>Sunrise</option>
        <option value="sunset" ${t.type === "sunset" ? "selected" : ""}>Sunset</option>
      </select>
      ${t.type === "time"
        ? `<input type="time" value="${t.time}" data-path="${p}.time">`
        : `<input type="number" min="-720" max="720" value="${t.offset}" data-path="${p}.offset"><span class="hint">min offset</span>`}
    </div>`;
  }

  _scheduleHtml() {
    const s = this._draft.schedule;
    const body = `
      <div class="row"><label><input type="checkbox" data-path="schedule.enabled" ${s.enabled ? "checked" : ""}> Run on a schedule</label></div>
      <div class="${s.enabled ? "" : "dim"}" style="display:grid;gap:var(--cr-gap)">
        <div class="row days"><label>Days</label><span class="seg">${DAYS.map((n, i) =>
          `<button class="${s.days.includes(i) ? "sel" : ""}" data-a="day" data-i="${i}">${n}</button>`).join("")}</span></div>
        ${this._triggerHtml("start")}
        ${this._triggerHtml("end")}
        <div class="hint">If the end is earlier than the start, the window runs past midnight. Days refer to the start day.</div>
      </div>
      <div class="row"><label>When stopped</label>
        <select data-path="end_action">
          <option value="restore" ${this._draft.end_action === "restore" ? "selected" : ""}>Restore previous state</option>
          <option value="off" ${this._draft.end_action === "off" ? "selected" : ""}>Turn lights off</option>
          <option value="leave" ${this._draft.end_action === "leave" ? "selected" : ""}>Leave on last color</option>
        </select>
      </div>`;
    const sub = s.enabled ? `${s.days.length === 7 ? "daily" : s.days.map((i) => DAYS[i]).join(" ")}` : "off";
    return this._section("schedule", "Schedule", sub, body);
  }

  _saveBarHtml() {
    if (!this._dirty && !this._error) return "";
    return `<div class="savebar">
      <span class="msg">${this._error ? `<span class="err">${esc(this._error)}</span>` : "Unsaved changes"}</span>
      ${this._dirty ? `<button data-a="discard" ${this._saving ? "disabled" : ""}>Discard</button>
      <button class="primary" data-a="save" ${this._saving ? "disabled" : ""}>${this._saving ? "Saving…" : "Save"}</button>` : ""}
    </div>`;
  }

  _renderSaveBar() {
    const el = this.shadowRoot.getElementById("savebar");
    if (el) el.innerHTML = this._saveBarHtml();
  }
}

/* ---------------- card editor ---------------- */
class ColorRotatorCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._groups = null;
    this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
    this.shadowRoot.addEventListener("click", (e) => { if (e.target.dataset.a === "create") this._create(); });
  }

  setConfig(config) { this._config = { ...config }; this._render(); }

  set hass(hass) {
    this._hass = hass;
    if (this._groups === null) { this._groups = []; this._load(); }
  }

  async _load() {
    try { this._groups = await this._hass.callWS({ type: "color_rotator/list" }); this._err = ""; }
    catch (err) { this._err = err.message; }
    this._render();
  }

  async _create() {
    const name = this.shadowRoot.getElementById("new-name").value.trim();
    if (!name) return;
    try {
      const g = await this._hass.callWS({ type: "color_rotator/create", name });
      await this._load();
      this._update({ entry_id: g.entry_id });
    } catch (err) { this._err = err.message; this._render(); }
  }

  _onChange(e) {
    const el = e.target;
    if (el.id === "group") this._update({ entry_id: el.value });
    else if (el.id === "title") this._update({ title: el.value || undefined });
  }

  _update(patch) {
    this._config = { ...this._config, ...patch };
    if (this._config.title === undefined) delete this._config.title;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    this._render();
  }

  _render() {
    if (!this._config) return;
    const groups = this._groups || [];
    const sel = this._config.entry_id || "";
    this.shadowRoot.innerHTML = `
      <style>
        .f { display: grid; gap: 14px; padding: 4px 0; }
        label { display: grid; gap: 4px; font-size: .9em; color: var(--secondary-text-color); }
        select, input { font: inherit; padding: 8px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
        .row { display: flex; gap: 8px; } .row input { flex: 1; }
        button { font: inherit; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--primary-color); background: var(--primary-color); color: var(--text-primary-color,#fff); cursor: pointer; }
        .err { color: var(--error-color,#db4437); } .hint { font-size: .85em; color: var(--secondary-text-color); }
      </style>
      <div class="f">
        <label>Rotation group
          <select id="group">
            <option value="" ${sel ? "" : "selected"} disabled>Choose a group…</option>
            ${groups.map((g) => `<option value="${esc(g.entry_id)}" ${g.entry_id === sel ? "selected" : ""}>${esc(g.title)}</option>`).join("")}
          </select>
        </label>
        <label>Or create a new group
          <div class="row"><input id="new-name" placeholder="e.g. Porch holiday lights"><button data-a="create">Create</button></div>
        </label>
        <label>Card title (optional)
          <input id="title" value="${esc(this._config.title || "")}" placeholder="Defaults to the group name">
        </label>
        <div class="hint">Each group has its own lights, colors and schedule. Two cards pointing at the same group show the same settings.</div>
        ${this._err ? `<div class="err">${esc(this._err)}</div>` : ""}
      </div>`;
  }
}

if (!customElements.get("color-rotator-card")) {
  customElements.define("color-rotator-card", ColorRotatorCard);
  customElements.define("color-rotator-card-editor", ColorRotatorCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "color-rotator-card",
    name: "Color Rotator",
    description: "Rotate lights through a list of colors on an interval and schedule.",
    preview: false,
  });
  console.info(`%c COLOR-ROTATOR-CARD %c ${CR_VERSION} `, "background:#7b68ee;color:#fff", "background:#ddd;color:#000");
}
