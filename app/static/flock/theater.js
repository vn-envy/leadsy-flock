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
    { id: "scout", label: "Scout", say: "Scout reads the listing, Maps, and the shop's own site." },
    { id: "inka", label: "Inka", say: "Inka starts Veo from this shop's own photos — not fake UGC." },
    { id: "inka_harvest", label: "Harvest", say: "Harvest polls Veo, muxes English and Hindi, crops the slots." },
    { id: "creative_gate", label: "Gate", say: "Ledge fail-closes the copy. A reject does not ship." },
    { id: "stella", label: "Stella", say: "Stella hosts a consent-first landing. Discovery is not consent." },
    { id: "ad_kit", label: "Kit", say: "Ad Kit fans one master into Meta, WhatsApp, and Google. No autopost." },
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
  const cueEl = $("cue");
  const capsule = $("capsule");
  let campaign = boot.campaign || null;
  let timer = null;
  let auditioning = false;

  function reduceMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function beat(ms) {
    return new Promise((r) => setTimeout(r, reduceMotion() ? Math.min(ms, 280) : ms));
  }

  function cue(text) {
    if (cueEl) cueEl.textContent = text;
  }

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
    capsule?.classList.remove("typing", "ready");
    hireBtn.classList.remove("press");
    setStage("quote");
    quote.classList.add("show");
    yesBtn.hidden = false;
    hireBtn.hidden = true;
    headline.textContent = campaign?.brief?.businessName || seed.name;
    lede.textContent = "Scout, Inka, and Stella for a launch kit. Flo never autoposts. YES is the only expensive door.";
    cue("3 · YES — nothing expensive runs until this");
  }

  function showWork() {
    yesBtn.classList.remove("press");
    setStage("work");
    path.classList.add("show");
    path.setAttribute("aria-hidden", "false");
    yesBtn.disabled = true;
    yesBtn.textContent = "Hired";
    lede.textContent = "The flock is on the listing. Stay on this roost.";
    cue("4 · The flock works");
  }

  function showKit(src) {
    setStage("kit");
    delivery.classList.add("show");
    const next = new URL(src, window.location.origin).href;
    if (frame.src !== next) frame.src = src;
    headline.textContent = "The kit is the roost.";
    lede.textContent = "Paste into Ads Manager. We do not autopost. Do not contact the bakery.";
    cue("5 · Paste kit");
  }

  async function typeUrl(text) {
    hireBtn.hidden = false;
    yesBtn.hidden = true;
    urlInput.value = "";
    setStage("paste");
    cue("1 · Paste the Google listing");
    headline.textContent = "Paste a listing you own.";
    lede.textContent =
      "Watch the URL land in the box. This roost uses Glen's Bakehouse as a seeded kit. We never autopost. Hire is closed.";
    capsule?.classList.add("typing");
    capsule?.classList.remove("ready");
    try {
      urlInput.focus({ preventScroll: true });
    } catch (e) {
      /* ignore */
    }
    if (reduceMotion()) {
      urlInput.value = text;
    } else {
      for (let i = 1; i <= text.length; i += 1) {
        urlInput.value = text.slice(0, i);
        await beat(i < 20 ? 42 : 78);
      }
    }
    capsule?.classList.remove("typing");
  }

  async function playAudition() {
    if (auditioning) return;
    auditioning = true;
    $("name").value = seed.name;
    $("geo").value = seed.geo;
    $("goal").value = seed.goal;
    await beat(900);
    await typeUrl(seed.url);
    await beat(1800);
    cue("2 · Hire the flock");
    lede.textContent = "Hire the flock. Flo still waits for YES before Veo. This seeded roost does not start a real campaign.";
    capsule?.classList.add("ready");
    hireBtn.classList.add("press");
    await beat(1600);
    hireBtn.classList.remove("press");
    capsule?.classList.remove("ready");
    showQuote();
    yesBtn.classList.add("press");
    await beat(3200);
    yesBtn.classList.remove("press");
    await playWork();
    auditioning = false;
  }

  async function playWork() {
    showWork();
    for (let i = 0; i < STEPS.length; i += 1) {
      cue("4 · " + STEPS[i].label);
      headline.textContent = STEPS[i].label;
      lede.textContent = STEPS[i].say;
      paintPath(
        STEPS.slice(0, i).map((s) => ({ step: s.id, status: "ok" })),
        "running",
      );
      await beat(1500);
    }
    paintPath(
      STEPS.map((s) => ({ step: s.id, status: "ok" })),
      "completed",
    );
    await beat(900);
    showKit(seed.kitPath);
  }

  async function createRun() {
    err.textContent = "";
    if (auditioning) return;
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
    if (auditioning) return;
    if (boot.locked || !campaign?.id) return playWork();
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
    if (fromYes) return playWork();
    $("name").value = seed.name;
    $("geo").value = seed.geo;
    $("goal").value = seed.goal;
    await typeUrl(seed.url);
    await beat(1400);
    showQuote();
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
    if (auditioning) return;
    playAudition();
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
    playWork();
  } else if (boot.play === "seed") {
    playAudition();
  }
})();
