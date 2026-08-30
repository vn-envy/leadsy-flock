# Copyright 2026 Neekhil Vatsa — unique stamp-flock SVGs for mockups (not a vendor pack)

(() => {
  const birds = {
    flo: `<svg class="bird flo" viewBox="0 0 80 100" aria-label="Flo, director">
      <g class="body">
        <ellipse cx="40" cy="64" rx="20" ry="24" class="fill-ink stroke"/>
        <path d="M22 58 Q18 48 28 46" class="stroke" fill="none"/>
        <circle cx="40" cy="32" r="15" class="fill-bone stroke"/>
        <circle cx="46" cy="31" r="2.4" fill="#14181f"/>
        <circle cx="46.8" cy="30.2" r="0.7" class="fill-bone"/>
        <polygon class="beak fill-gold" points="52,34 64,36 52,40"/>
        <circle class="ring" cx="54" cy="36" r="9" fill="none" stroke="#c4a574" stroke-width="1.3" stroke-dasharray="3 5"/>
        <path d="M34 18 L40 8 L46 18" class="fill-gold stroke"/>
        <path d="M32 88 L32 94 M48 88 L48 94" class="stroke"/>
      </g>
    </svg>`,
    bri: `<svg class="bird bri" viewBox="0 0 80 100" aria-label="Bri, strategist">
      <g class="body">
        <rect x="26" y="48" width="28" height="32" rx="10" class="fill-ink stroke"/>
        <circle cx="40" cy="34" r="14" class="fill-bone stroke"/>
        <circle cx="45" cy="33" r="2.2" fill="#14181f"/>
        <polygon class="fill-gold" points="52,34 62,32 52,39"/>
        <text x="40" y="68" text-anchor="middle" font-size="11" fill="#c4a574" font-family="Georgia,serif">₹</text>
        <g class="beads">
          <circle cx="22" cy="72" r="3" fill="#e08a4a"/>
          <circle cx="18" cy="80" r="3" fill="#c4a574"/>
          <circle cx="22" cy="88" r="3" fill="#e08a4a"/>
        </g>
      </g>
    </svg>`,
    scout: `<svg class="bird scout" viewBox="0 0 80 100" aria-label="Scout, tracker">
      <g class="body">
        <ellipse cx="40" cy="66" rx="16" ry="22" class="fill-ink stroke"/>
        <circle cx="40" cy="30" r="13" class="fill-bone stroke"/>
        <circle cx="45" cy="29" r="2" fill="#14181f"/>
        <polygon class="fill-gold" points="51,31 63,28 51,35"/>
        <g class="scope">
          <circle cx="50" cy="28" r="7" fill="none" stroke="#7eaebe" stroke-width="1.6"/>
          <line x1="50" y1="21" x2="50" y2="19" stroke="#7eaebe"/>
        </g>
        <path d="M40 8 L40 16 M37 12 L43 12" stroke="#7eaebe" stroke-width="1.6"/>
        <circle cx="40" cy="7" r="2.2" fill="#7eaebe"/>
      </g>
    </svg>`,
    inka: `<svg class="bird inka" viewBox="0 0 80 100" aria-label="Inka, artist">
      <g class="body">
        <ellipse cx="40" cy="64" rx="19" ry="23" class="fill-ink stroke"/>
        <circle cx="40" cy="33" r="14" class="fill-bone stroke"/>
        <circle cx="35" cy="32" r="2.2" fill="#14181f"/>
        <path class="beak" d="M26 34 Q14 38 26 42 Z" fill="#14181f"/>
        <path d="M58 50 Q70 40 68 58 Q60 62 58 50" fill="#14181f"/>
        <circle class="drop" cx="18" cy="44" r="2.4" fill="#14181f"/>
        <path d="M48 18 Q52 10 44 12" class="stroke" fill="none"/>
      </g>
    </svg>`,
    stella: `<svg class="bird stella" viewBox="0 0 80 100" aria-label="Stella, host">
      <g class="body">
        <ellipse cx="40" cy="66" rx="18" ry="22" class="fill-ink stroke"/>
        <circle cx="40" cy="34" r="14" class="fill-bone stroke"/>
        <circle cx="45" cy="33" r="2.2" fill="#14181f"/>
        <polygon class="fill-gold" points="52,34 62,36 52,40"/>
        <g class="lantern">
          <rect x="34" y="6" width="12" height="10" rx="1" fill="#c4a574"/>
          <path d="M36 6 L44 6 L42 2 L38 2 Z" fill="#c4a574"/>
          <circle cx="40" cy="11" r="2" fill="#f3eee6" opacity="0.8"/>
        </g>
        <path d="M24 58 L16 50 L24 52" class="stroke" fill="none"/>
      </g>
    </svg>`,
    ray: `<svg class="bird ray" viewBox="0 0 80 100" aria-label="Ray, postbird">
      <g class="body">
        <ellipse cx="42" cy="64" rx="17" ry="22" class="fill-ink stroke"/>
        <circle cx="42" cy="32" r="13" class="fill-bone stroke"/>
        <circle cx="47" cy="31" r="2" fill="#14181f"/>
        <polygon class="fill-gold" points="53,33 64,31 53,38"/>
        <g class="wing">
          <rect x="10" y="46" width="22" height="16" rx="1.5" fill="#f3eee6" stroke="#c4a574"/>
          <path d="M10 50 L32 50 M21 46 L21 62" stroke="#c4a574" stroke-width="1"/>
          <circle cx="27" cy="58" r="3" fill="#b54a4a"/>
        </g>
      </g>
    </svg>`,
    callie: `<svg class="bird callie" viewBox="0 0 80 100" aria-label="Callie, voice, not hired this run">
      <g class="body">
        <ellipse cx="40" cy="64" rx="18" ry="22" fill="none" class="outline" stroke="#b7aea2" stroke-width="1.6"/>
        <circle cx="40" cy="32" r="13" fill="none" class="outline" stroke="#b7aea2" stroke-width="1.6"/>
        <circle cx="45" cy="31" r="2" fill="#b7aea2"/>
        <path d="M52 28 Q64 22 58 40" fill="none" stroke="#b7aea2" stroke-width="1.6"/>
        <circle cx="58" cy="22" r="5" fill="none" stroke="#b7aea2" stroke-width="1.6"/>
      </g>
    </svg>`,
    ledge: `<svg class="bird ledge" viewBox="0 0 80 100" aria-label="Ledge, auditor">
      <g class="body">
        <rect x="24" y="40" width="32" height="40" rx="2" class="fill-bone stroke"/>
        <line x1="30" y1="50" x2="50" y2="50" stroke="#2c3340"/>
        <line x1="30" y1="56" x2="48" y2="56" stroke="#2c3340"/>
        <line x1="30" y1="62" x2="46" y2="62" stroke="#2c3340"/>
        <circle cx="40" cy="26" r="12" class="fill-ink stroke"/>
        <circle cx="44" cy="25" r="1.8" fill="#c4a574"/>
        <g class="mark">
          <circle cx="40" cy="58" r="9" fill="none" stroke="#b54a4a" stroke-width="1.5"/>
          <text x="40" y="62" text-anchor="middle" font-size="8" fill="#b54a4a" font-family="Georgia,serif">NO</text>
        </g>
      </g>
    </svg>`,
  };

  const meta = {
    flo: ["Flo", "Director"],
    bri: ["Bri", "Strategist"],
    scout: ["Scout", "Tracker"],
    inka: ["Inka", "Artist"],
    stella: ["Stella", "Host"],
    ray: ["Ray", "Postbird"],
    callie: ["Callie", "Voice · later"],
    ledge: ["Ledge", "Auditor"],
  };

  document.querySelectorAll("[data-bird]").forEach((el) => {
    const id = el.getAttribute("data-bird");
    if (!birds[id]) return;
    const named = el.hasAttribute("data-card");
    const ghost = id === "callie" ? " ghost" : "";
    if (named) {
      const [name, role] = meta[id];
      el.className = `flock-card${ghost}`;
      el.innerHTML = `${birds[id]}<h3>${name}</h3><p>${role}</p>`;
    } else {
      el.innerHTML = birds[id];
    }
  });
})();
