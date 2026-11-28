"use strict";

const byId = id => document.getElementById(id);
const fonts = byId("fonts");
const selectAll = byId("select-all");
const install = byId("install");
const replace = byId("replace");
const statusLine = byId("status");
let scanId;

async function invoke(command, payload = {}) {
  const reply = await window.jade.invoke(command, payload);
  if (reply.error) throw new Error(reply.error);
  return reply.data;
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function selectedIndexes() {
  return Array.from(fonts.querySelectorAll("input:checked"), input => Number(input.value));
}

function updateSelection() {
  const available = fonts.querySelectorAll("input:not([disabled])").length;
  const count = selectedIndexes().length;
  selectAll.disabled = available === 0;
  selectAll.checked = count > 0 && count === available;
  selectAll.indeterminate = count > 0 && count < available;
  install.disabled = count === 0;
  install.textContent = count ? "Install selected (" + count + ")" : "Install selected";
}

function fontRow(font, index) {
  const row = document.createElement("tr");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.id = "font-" + index;
  input.value = index;
  input.disabled = Boolean(font.error);
  const check = row.insertCell();
  check.className = "check";
  check.append(input);

  const split = Math.max(font.path.lastIndexOf("/"), font.path.lastIndexOf("\\"));
  const filename = font.path.slice(split + 1);
  const label = element("label", filename);
  label.htmlFor = input.id;
  if (split >= 0) label.append(element("span", font.path.slice(0, split), "parent"));
  row.insertCell().append(label);

  const type = row.insertCell();
  type.textContent = filename.split(".").at(-1).toUpperCase();
  if (font.kind) type.title = font.kind;
  row.insertCell().textContent = font.name ?? "—";
  const result = row.insertCell();
  if (font.error) {
    result.append(element("span", "Unreadable", "result failed"), element("span", font.error, "detail"));
  } else {
    result.textContent = "—";
  }
  return row;
}

async function chooseFolder() {
  const scan = await invoke("pick_folder");
  if (scan === null) return;
  const rows = document.createDocumentFragment();
  scan.fonts.forEach((font, index) => rows.append(fontRow(font, index)));
  fonts.replaceChildren(rows);
  scanId = scan.scanId;
  byId("folder").textContent = scan.folder;
  byId("folder").hidden = false;
  const empty = scan.fonts.length === 0;
  const unreadable = scan.fonts.filter(font => font.error).length;
  const available = scan.fonts.length - unreadable;
  byId("scan-table").hidden = empty;
  byId("controls").hidden = available === 0;
  byId("scan-empty").hidden = !empty;
  byId("scan-empty").textContent = "No TTF, OTF, TTC or OTC files found in this folder.";
  replace.checked = false;
  updateSelection();
  statusLine.textContent = available + (available === 1 ? " selectable font." : " selectable fonts.")
    + (unreadable ? " " + unreadable + " unreadable." : "");
}

async function refreshInstalled() {
  const empty = byId("installed-empty");
  const table = byId("installed-table");
  const count = byId("installed-count");
  try {
    const {installed} = await invoke("list");
    const rows = document.createDocumentFragment();
    for (const font of installed) {
      const row = document.createElement("tr");
      row.insertCell().textContent = font.name;
      row.insertCell().textContent = font.filename;
      rows.append(row);
    }
    byId("installed").replaceChildren(rows);
    count.textContent = "(" + installed.length + ")";
    table.hidden = installed.length === 0;
    empty.hidden = !table.hidden;
    empty.textContent = "No fonts installed for this user.";
  } catch (error) {
    count.textContent = "";
    table.hidden = true;
    empty.hidden = false;
    empty.textContent = "Could not read installed fonts. " + (error.message ?? error);
  }
}

function showBatch(selected, batch) {
  const results = new Map(batch.results.map(result => [result.index, result]));
  const labels = {installed: "Installed", skipped: "Skipped", failed: "Failed", unattempted: "Not attempted"};
  const counts = new Map();
  for (const index of selected) {
    const {status, message} = results.get(index) ?? {status: "unattempted"};
    const cell = fonts.rows[index].lastElementChild;
    cell.replaceChildren(element("span", labels[status], "result " + status));
    if (message) cell.append(element("span", message, "detail"));
    counts.set(status, (counts.get(status) ?? 0) + 1);
  }
  const summary = Array.from(counts)
    .map(([status, count]) => count + " " + labels[status].toLowerCase()).join(", ");
  statusLine.textContent = summary + "." + (batch.error ? " " + batch.error : "");
}

async function installSelected() {
  const selected = selectedIndexes();
  statusLine.textContent = "Installing selected fonts…";
  for (const row of fonts.rows) {
    if (!row.querySelector("input").disabled) row.lastElementChild.textContent = "—";
  }
  try {
    const batch = await invoke("install", {scanId, selected, replace: replace.checked});
    showBatch(selected, batch);
  } finally {
    replace.checked = false;
    await refreshInstalled();
  }
}

async function run(task) {
  const choose = byId("choose"), refresh = byId("refresh"), selection = byId("selection");
  choose.disabled = refresh.disabled = selection.disabled = true;
  try {
    await task();
  } catch (error) {
    statusLine.textContent = String(error.message ?? error);
  } finally {
    choose.disabled = refresh.disabled = selection.disabled = false;
  }
}

selectAll.addEventListener("change", () => {
  for (const input of fonts.querySelectorAll("input:not([disabled])")) input.checked = selectAll.checked;
  updateSelection();
});
fonts.addEventListener("change", updateSelection);
byId("choose").addEventListener("click", () => run(chooseFolder));
install.addEventListener("click", () => run(installSelected));
byId("refresh").addEventListener("click", () => run(refreshInstalled));
window.addEventListener("load", () => run(refreshInstalled));
