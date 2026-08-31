(() => {
  const boot = window.__FLOCK__ || {};
  const seed = boot.seed || {
    name: "Glen's Bakehouse",
    geo: "Indiranagar, Bangalore",
    goal: "Walk-ins to the courtyard for mini red velvet cupcakes.",
    url: "https://share.google/rLF34cfolz9TJA92F",
    kitPath: "/k/google-listing-eaf57cae",
    campaignId: "google-listing-eaf57cae",
    markers: ["rLF34cfolz9TJA92F", "glensbakehouse.com", "google-listing-eaf57cae"],
  };
  const STEPS = [
    { id: "scout", label: "Scout" },
    { id: "inka", label: "Inka" },
    { id: "inka_harvest", label: "Harvest" },
    { id: "creative_gate", label: "Gate" },
    { id: "stella", label: "Stella" },
    { id: "ad_kit", label: "Kit" },
  ];

  const $ = (id) => document.getElementById(id);
  const urlInput = $("url");
  const hireBtn = $("hire");
  const yesBtn = $("yes");
  const headline = $("headline");
  const lede = $("lede");
  const quote = $("quote");
  const path = $("path");
  const delivery = $("delivery");
  const frame = $("kit-frame");
  const err = $("err");
  const status = $("status");
  let campaign = boot.campaign || null;
  let timer = null;

  function setStage(name) {
    document.body.dataset.stage = name;
    status.textContent = name;
  }

  function isSeedListing(url) {
    const u = (url || "").trim().toLowerCase();
    if (!u) return false;
    const markers = seed.markers || [seed.url, seed.campaignId];
    return markers.some((m) => m && u.includes(String(m).toLowerCase()));
  }

  function paintPath(receipts, st) {
    const done = new Set((receipts || []).filter((r) => r.status === "ok").map((r) => r.step));
    const current =
      (receipts || []).find((r) => r.status === "running")?.step ||
      (st === "running" ? STEPS.find((s) => !done.has(s.id))?.id : "");
    path.querySelectorAll(".step").forEach((el) => {
      el.classList.remove("on", "ok");
      if (done.has(el.dataset.id)) el.classList.add("ok");
      else if (el.dataset.id === current) el.classList.add("on");
    });
    document.querySelectorAll(".bird").forEach((el) => {
      el.classList.toggle("ok", done.has(el.dataset.step));
      el.classList.toggle("on", el.dataset.step === current);
    });
  }

  function showQuote() {
    setStage("quote");
    quote.classList.add("show");
    yesBtn.hidden = false;
    hireBtn.hidden = true;
    headline.textContent = campaign?.brief?.businessName || seed.name;
    lede.textContent = "Scout, Inka, and Stella for a launch kit. Flo never autoposts.";
  }

  function showWork() {
    setStage("work");
    path.classList.add("show");
    path.setAttribute("aria-hidden", "false");
    yesBtn.disabled = true;
    yesBtn.textContent = "Hired";
    lede.textContent = "The flock is on the listing. Stay on this roost.";
  }

  function showKit(src) {
    setStage("kit");
    delivery.classList.add("show");
    const next = new URL(src, window.location.origin).href;
    if (frame.src !== next) frame.src = src;
    headline.textContent = "The kit is the roost.";
    lede.textContent = "Paste into Ads Manager. We do not autopost. Do not contact the bakery.";
  }

  async function createRun() {
    err.textContent = "";
    const url = (urlInput.value || "").trim();
    if (boot.locked) {
      await playSeed(false);
      return;
    }
    if (!url) {
      err.textContent = "Drop a website or Google listing.";
      return;
    }
    if (isSeedListing(url) && !campaign?.id) {
      await playSeed(false);
      return;
    }
    hireBtn.disabled = true;
    hireBtn.textContent = "Gathering…";
    try {
      const res = await fetch("/", {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({
          url,
          businessName: $("name").value,
          geo: $("geo").value,
          goal: $("goal").value,
          assetUris: $("assets").value,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        err.textContent = "Could not quote that listing.";
        hireBtn.disabled = false;
        hireBtn.textContent = "Hire the flock";
        return;
      }
      campaign = body;
      history.pushState({}, "", body.runPath || "/");
      showQuote();
    } catch (e) {
      err.textContent = "Could not quote that listing.";
      hireBtn.disabled = false;
      hireBtn.textContent = "Hire the flock";
    }
  }

  async function approve() {
    if (boot.locked || !campaign?.id) return playSeed(true);
    yesBtn.disabled = true;
    yesBtn.textContent = "Hiring…";
    const res = await fetch("/v1/campaigns/" + campaign.id + "/approve", { method: "POST" });
    if (!res.ok) {
      yesBtn.disabled = false;
      yesBtn.textContent = "YES";
      return;
    }
    showWork();
    startPoll();
  }

  async function tick() {
    if (!campaign?.id) return;
    const [cRes] = await Promise.all([
      fetch("/v1/campaigns/" + campaign.id),
      fetch("/media/" + campaign.id + "/ready"),
    ]);
    if (!cRes.ok) return;
    const c = await cRes.json();
    paintPath(c.receipts || [], c.status);
    if (c.status === "completed" || c.kitPath) {
      showKit(c.kitPath || "/k/" + campaign.id);
    }
  }

  function startPoll() {
    if (timer) return;
    tick();
    timer = setInterval(tick, 2200);
  }

  async function playSeed(fromYes) {
    if (!fromYes) {
      urlInput.value = seed.url;
      $("name").value = seed.name;
      $("geo").value = seed.geo;
      $("goal").value = seed.goal;
      headline.textContent = seed.name;
      await new Promise((r) => setTimeout(r, 900));
      showQuote();
      return;
    }
    showWork();
    for (let i = 0; i < STEPS.length; i += 1) {
      paintPath(
        STEPS.slice(0, i).map((s) => ({ step: s.id, status: "ok" })),
        "running",
      );
      await new Promise((r) => setTimeout(r, 620));
    }
    paintPath(
      STEPS.map((s) => ({ step: s.id, status: "ok" })),
      "completed",
    );
    showKit(seed.kitPath);
  }

  hireBtn.addEventListener("click", (e) => {
    e.preventDefault();
    createRun();
  });
  urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      createRun();
    }
  });
  yesBtn.addEventListener("click", () => approve());
  $("seed-chip")?.addEventListener("click", (e) => {
    e.preventDefault();
    playSeed(false);
  });
  $("more-toggle")?.addEventListener("click", () => {
    $("more").classList.toggle("open");
  });

  if (!path.children.length) {
    path.innerHTML = STEPS.map(
      (s) => `<div class="step" data-id="${s.id}" data-label="${s.label}"></div>`,
    ).join("");
  }

  if (campaign?.status === "completed" || campaign?.kitPath) {
    showQuote();
    showWork();
    showKit(campaign.kitPath || campaign.studioPath);
    startPoll();
  } else if (campaign?.status === "running") {
    showQuote();
    showWork();
    startPoll();
  } else if (campaign?.id) {
    showQuote();
  } else if (boot.play === "kit") {
    urlInput.value = seed.url;
    headline.textContent = seed.name;
    playSeed(true);
  } else if (boot.play === "seed") {
    playSeed(false).then(() => setTimeout(() => playSeed(true), 1800));
  }
})();
