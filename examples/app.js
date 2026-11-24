"use strict";

const TABS = ["waivers", "standings", "playoffs"];
const WAIVER_PAGE = 25;
const state = { data: null, scope: { standings: "all", playoffs: "all" }, waiversExpanded: false };

const fixed = (digits) => (v) => (v === null || v === undefined ? "–" : Number(v).toFixed(digits));
const text = (v) => (v === null || v === undefined ? "–" : String(v));

const COLUMNS = {
  standings: [
    { label: "#", rank: true },
    { key: "name", label: "Manager" },
    { key: "wins", label: "Wins", num: true },
    { key: "losses", label: "Losses", num: true },
    { key: "win_pct", label: "Win pct", num: true, format: fixed(2) },
  ],
  playoffs: [
    { label: "#", rank: true },
    { key: "name", label: "Manager" },
    { key: "playoff_apps", label: "Appearances", num: true },
    { key: "seasons", label: "Decided seasons", num: true },
    { key: "playoff_pct", label: "Playoff pct", num: true, format: fixed(2) },
    { key: "championships", label: "Championships", num: true },
  ],
  waivers: [
    { label: "#", rank: true },
    { key: "player_name", label: "Player" },
    { key: "position", label: "Pos" },
    { key: "year", label: "Year", num: true },
    { key: "total_points", label: "Points", num: true, format: fixed(2) },
    { key: "weeks", label: "Starts", num: true },
    { key: "vor", label: "VOR", num: true, format: fixed(2) },
  ],
};

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const child of children) node.append(child);
  return node;
}

function renderTable(table, columns, rows) {
  const head = el("thead", {}, [el("tr", {}, columns.map((c) =>
    el("th", { textContent: c.label, scope: "col", className: c.num || c.rank ? "num" : "" })))]);
  const body = el("tbody");
  rows.forEach((row, i) => {
    body.append(el("tr", {}, columns.map((c) => el("td", {
      className: c.num || c.rank ? "num" : "",
      textContent: c.rank ? String(i + 1) : (c.format || text)(row[c.key]),
    }))));
  });
  if (!rows.length) {
    body.append(el("tr", {}, [el("td", { colSpan: columns.length, className: "muted", textContent: "No rows" })]));
  }
  table.replaceChildren(head, body);
}

function renderManagers(name) {
  const rows = state.data[name].filter((r) => state.scope[name] === "all" || r.current);
  renderTable(document.getElementById(`${name}-table`), COLUMNS[name], rows);
}

function renderWaivers() {
  const { waivers } = state.data;
  const season = document.getElementById("waiver-season").value;
  const position = document.getElementById("waiver-position").value;
  let rows = season ? waivers.by_season[season] || [] : waivers.all_seasons;
  if (position) rows = rows.filter((r) => r.position === position);
  const shown = state.waiversExpanded ? rows : rows.slice(0, WAIVER_PAGE);
  renderTable(document.getElementById("waiver-table"), COLUMNS.waivers, shown);
  const more = document.getElementById("waiver-more");
  more.hidden = rows.length <= WAIVER_PAGE;
  more.textContent = state.waiversExpanded ? `Show top ${WAIVER_PAGE}` : `Show all (${rows.length})`;
}

function showTab(name) {
  if (!TABS.includes(name)) name = TABS[0];
  for (const tab of TABS) {
    const active = tab === name;
    document.getElementById(tab).hidden = !active;
    const button = document.getElementById(`tab-${tab}`);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
  }
}

function setupControls() {
  document.querySelectorAll('[role="tab"]').forEach((button) => {
    button.addEventListener("click", () => { location.hash = button.dataset.tab; });
  });
  window.addEventListener("hashchange", () => showTab(location.hash.slice(1)));

  document.querySelectorAll(".segmented").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-scope]");
      if (!button) return;
      for (const b of group.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === button));
      state.scope[group.dataset.target] = button.dataset.scope;
      renderManagers(group.dataset.target);
    });
  });

  const season = document.getElementById("waiver-season");
  season.append(el("option", { value: "", textContent: "All seasons" }));
  for (const year of Object.keys(state.data.waivers.by_season).sort().reverse()) {
    season.append(el("option", { value: year, textContent: year }));
  }
  for (const id of ["waiver-season", "waiver-position"]) {
    document.getElementById(id).addEventListener("change", () => { state.waiversExpanded = false; renderWaivers(); });
  }
  document.getElementById("waiver-more").addEventListener("click", () => {
    state.waiversExpanded = !state.waiversExpanded;
    renderWaivers();
  });
}

function describeSeasons(metadata) {
  const years = metadata.seasons;
  if (!years.length) return "No seasons";
  const range = years.length === 1 ? String(years[0]) : `${years[0]}–${years[years.length - 1]}`;
  const latest = years[years.length - 1];
  const week = metadata.source_current_weeks[String(latest)];
  return `Seasons ${range} · ${latest} data through week ${week}`;
}

async function load() {
  const files = ["metadata", "standings", "playoff_appearances", "waivers"];
  const responses = await Promise.all(files.map(async (name) => {
    const response = await fetch(`${name}.json`);
    if (!response.ok) throw new Error(`${name}.json: HTTP ${response.status}`);
    return response.json();
  }));
  const [metadata, standings, playoffs, waivers] = responses;
  return { metadata, standings, playoffs, waivers };
}

async function main() {
  showTab(location.hash.slice(1));
  try {
    state.data = await load();
  } catch (error) {
    const box = document.getElementById("error");
    box.textContent = `Could not load league data (${error.message}). Run "ff-dashboard generate" and serve the output directory.`;
    box.hidden = false;
    document.getElementById("seasons").textContent = "";
    return;
  }
  document.getElementById("seasons").textContent = describeSeasons(state.data.metadata);
  setupControls();
  renderManagers("standings");
  renderManagers("playoffs");
  renderWaivers();
}

main();
