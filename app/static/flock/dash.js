(() => {
  const boot = window.__DASH__ || {};
  const MIX = {
    completed: "#8d9972",
    running: "#d49a9a",
    planned: "#5b6440",
    failed: "#b56e7c",
    unknown: "#c5c0b8",
  };

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function metric(label, value) {
    const v = value === 0 || value ? String(value) : "—";
    return `<article class="stat"><p class="quiet">${esc(label)}</p><p class="metric">${esc(v)}</p></article>`;
  }

  function hbar(label, n, max, href, pink) {
    const pct = Math.round((n / Math.max(1, max)) * 100);
    const name = href
      ? `<a href="${esc(href)}">${esc(label)}</a>`
      : esc(label);
    const cls = pink ? ' class="pink"' : "";
    return `<div class="hbar"><b>${name}</b><div class="track"><i${cls} style="width:${pct}%"></i></div><em>${esc(n)}</em></div>`;
  }

  function paintDonut(status) {
    const el = document.getElementById("donut");
    if (!el) return;
    const total = (status || []).reduce((sum, row) => sum + (row.n || 0), 0);
    if (!total) {
      el.style.background = "var(--chunnam)";
      return;
    }
    let acc = 0;
    const stops = [];
    for (const row of status) {
      const start = (acc / total) * 360;
      acc += row.n || 0;
      const end = (acc / total) * 360;
      stops.push(`${MIX[row.id] || MIX.unknown} ${start}deg ${end}deg`);
    }
    el.style.background = `conic-gradient(${stops.join(",")})`;
  }

  function paint(data) {
    const totals = data.totals || {};
    const run = data.run || {};
    document.getElementById("stats").innerHTML = [
      metric("Campaigns", totals.campaigns),
      metric("Completed", totals.completed),
      metric("Landing hits", totals.hits),
      metric("Requests · 1h", totals.requests1h),
    ].join("");

    const maxN = Math.max(1, ...((data.engines || []).map((e) => e.n || 0)));
    document.getElementById("engines").innerHTML = (data.engines || [])
      .map((e) => {
        const ok = Math.round(((e.ok || 0) / maxN) * 100);
        const runH = Math.round(((e.running || 0) / maxN) * 100);
        const other = Math.round(((e.other || 0) / maxN) * 100);
        return `<div class="col">
          <div class="fill">
            <div class="other" style="height:${other}%"></div>
            <div class="run" style="height:${runH}%"></div>
            <div class="ok" style="height:${ok}%"></div>
          </div>
          <span>${esc(String(e.id || "").replaceAll("_", " "))}</span>
        </div>`;
      })
      .join("");

    const image = (run.image || "").split("/").pop() || "—";
    const ready = run.ready ? "ready" : "local";
    document.getElementById("proof").innerHTML = `
      <div class="proof">
        <div><p class="quiet">Service</p><p>${esc(run.service || "flock-api")} <span class="chip">${esc(ready)}</span></p></div>
        <div><p class="quiet">Revision</p><p><code>${esc(run.revision || "local")}</code></p></div>
        <div><p class="quiet">Region</p><p>${esc(run.region || "—")} · ${esc(run.project || "")}</p></div>
        <div><p class="quiet">Traffic</p><p>${esc(run.trafficPercent || 0)}% · ${esc(run.source || "env")}</p></div>
        <div><p class="quiet">Image</p><p>${esc(image)}</p></div>
      </div>`;
    const rev = document.getElementById("revision");
    if (rev) rev.textContent = run.revision || "local";

    const stMax = Math.max(1, ...((data.status || []).map((s) => s.n || 0)));
    document.getElementById("status").innerHTML = (data.status || [])
      .map((s) => hbar(s.id, s.n, stMax))
      .join("") || `<p class="quiet">No campaigns yet.</p>`;
    paintDonut(data.status || []);

    const p50 = totals.latencyMsP50;
    const p95 = totals.latencyMsP95;
    const latMax = Math.max(1, p50 || 0, p95 || 0);
    const latency = document.getElementById("latency");
    if (latency) {
      if (p50 == null && p95 == null) {
        latency.innerHTML = `<p class="quiet">Waiting on Cloud Monitoring.</p>`;
      } else {
        latency.innerHTML = [
          hbar("p50", p50 ?? 0, latMax),
          hbar("p95", p95 ?? 0, latMax, null, true),
        ].join("");
      }
    }

    const hitMax = Math.max(1, ...((data.hits || []).map((h) => h.hits || 0)));
    document.getElementById("hits").innerHTML = (data.hits || [])
      .map((h) => hbar(h.name || h.id, h.hits, hitMax, h.kitPath, true))
      .join("") || `<p class="quiet">No landing hits yet.</p>`;
  }

  paint(boot);
  if (boot.static) return;
  async function refresh() {
    try {
      const res = await fetch("/v1/dash");
      if (!res.ok) return;
      paint(await res.json());
    } catch (e) {}
  }
  refresh();
  setInterval(refresh, 12000);
})();
