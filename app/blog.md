# Google pointed the models at the courtyard. We built the agency that lives there.

*This article was created for the purposes of entering Google's All Things Agentic hackathon.*

For a decade, “AI for business” meant a chatbot on a homepage, or a slide in a Fortune-500 transformation deck. The interesting models sat behind specialist teams. The neighbourhood shop — the bakery with a courtyard, the salon with a shelf of bottles, the gym above a chemist — still bought ads the old way: a cousin with a phone, or an agency retainer that assumed a brand manager.

Google’s 2026 stack changed the unit economics. Gemini 3.5 Flash on Vertex is cheap enough to read a listing. Veo 3.1 is cheap enough, at list price, to shoot an eight-second film. Cloud Run and Pub/Sub are cheap enough to run that work in the background without a GPU laptop. The All Things Agentic hackathon asked builders to prove agents that *do the work*, not chat about it. We pointed that brief at India’s SMBs.

Leadsy Flock is a five-bird studio on that stack. Paste a Google listing you own. Scout grounds it. Inka films from **this shop’s own photos**. Stella hands you a paste kit for Meta, WhatsApp, and Google. Flo never autoposts. The owner says YES. That is the product.

Live roost: [Glen's Bakehouse seeded kit](https://flock-api-533880600838.asia-south1.run.app/demo) · Architecture: [/architecture](https://flock-api-533880600838.asia-south1.run.app/architecture) · Observatory: [/dash](https://flock-api-533880600838.asia-south1.run.app/dash) · Backend path: [/trace](https://flock-api-533880600838.asia-south1.run.app/trace)

## Grass roots, not a demo tenant

Google Search and Maps already *are* the grass roots. A kirana, a courtyard bakery, a neighbourhood salon — they live on a listing long before they live on a brand site. The gap was never discovery. It was the jump from “we exist on Maps” to “we have a film, bilingual voice, and a landing that does not leak the owner’s phone to a scraped lead list.”

That jump used to mean a crew, an editor, a Hindi VO artist, and a week. It was priced for a brand, not a shop. Vertex list prices invert that. Two eight-second Veo clips with audio are about **$6.40** at $0.40/s. Gemini Flash for copy is cents. Gemini TTS for English plus one Indic language is a rounding error next to the film. Our seeded Glen’s Bakehouse kit — a public listing we do **not** contact — reconstructed at **$6.41 · ₹545** of Vertex list-price burn. That is not a Google invoice and not a sell price. It is the honest COGS of the engine.

When film costs six dollars instead of sixty thousand rupees, the playing field is no longer “who can hire the agency.” It is “who owns the courtyard photos.”

## Deterministic on purpose

Generative stacks fail SMBs when they improvise. A model that invents a second branch, a fake UGC creator, or a dish the bakery does not sell is not creative. It is liability.

We made the pipeline boring in the ways that matter:

1. **Evidence first.** Scout may only ground what the listing, Maps, and the shop’s own site already say. Google Search, Maps, and URL context are tools, not vibes.
2. **Own pixels first.** Inka conditions Veo on this shop’s photos, menu, and listing frames. Gemini Image fills a still only when there is no usable visual evidence. We do not scrape swipe files. We do not fake UGC.
3. **Fail closed.** Ledge runs regex, a Gemma classifier, and a Gemini judge on the copy. A reject revises once. It does not ship.
4. **One master, many crops.** Veo is expensive. ffmpeg derives the 4:5 / 1:1 / 9:16 / 1.91:1 slots from the master. We do not re-roll an 8s film for every network.
5. **Do not wait on Veo inside the request.** Inka starts the job. A harvest sidecar polls. The worker ACKs Pub/Sub and keeps the rest of the flock moving.
6. **A human YES.** Nothing expensive runs because a form was curious. The owner pastes the kit. The flock does not autopost.

Deterministic outcome, for us, means: the same listing, the same own photos, the same gate, the same kit shape. Not a slot machine.

## How each piece of the Google stack earns its keep

The architecture is one line. A shop pastes a listing. Cloud Run `flock-api` is the door. Pub/Sub fans the birds. Cloud Run `flock-worker` does the work. Vertex paints. Firestore, Cloud Storage, Memory Bank, and Cloud Trace keep the record. The owner leaves with a kit.

![Leadsy Flock end-to-end architecture](/assets/flock/architecture.png)

**Gemini 3.5 Flash via Vertex** is Flo’s brain and the cheap text path — brief, copy, gate. We do not spend Veo on a headline.

**Google ADK** is how Flo is an agent, not a prompt file. A2A AgentCard is how the fleet can be catalogued. The hackathon asked for a framework. We used the one Google ships.

**Cloud Run** (`flock-api` + `flock-worker`, `asia-south1`) is the runtime. Request-shaped work stays on the API. Long work is a worker. No laptop left running overnight.

**Pub/Sub** (`campaign-steps`) is the async spine. One message, one step, one receipt. At-least-once delivery; idempotency lives on the receipt. If harvest needs another poll, we republish. We do not hold a request open for eight seconds of Veo.

**Model Armor** screens inbound text. A neighbourhood shop pasting a listing should not become a prompt-injection toy.

**Scout + Google Search + Maps + URL context** read the grass-roots record that already exists. The model is not allowed to invent a second address.

**Veo 3.1** is the costly brush — 8s, 9:16, audio on. We call it twice when we must (place film + proof film), then we stop. That is why COGS is a Veo story, not a Flash story.

**Gemini Image** is the fallback still, not the default. Own photos win.

**Gemini TTS** muxes English and one Indic language onto the same picture. The courtyard can speak Hindi without a second shoot.

**Lyria** is a jingle when quota allows. We skip, we do not fake a track.

**Gemma** sits on the Creative Gate as the classifier next to the Gemini judge. Bonus model, real job.

**ffmpeg** is not a Google model and that is the point. The lowest-cost engine is the one that refuses to regenerate pixels it already paid for.

**Firestore** stores receipts. **Cloud Storage** stores films. **Memory Bank** keeps long context. **Cloud Trace / OpenTelemetry** is the audit the Fortified Enterprise Fleet track asked for. The [observatory](https://flock-api-533880600838.asia-south1.run.app/dash) shows tokens, tools, models, and list-price USD for the seed. The [backend path](https://flock-api-533880600838.asia-south1.run.app/trace) lists the exact hops that ran (`engine.scout` on Cloud Run `flock-worker`, and so on) plus console links for anyone with the GCP project. Transparency is the product, not a PDF we would rather not show.

**ffmpeg + Stella’s landing** finish the job the shop can actually run: paste into Ads Manager, a consent checkbox on `/l`, UTM hits on the record. No autopost. Discovery is not consent.

## Lowest cost is a series of refusals

The cheap engine is not “we picked Flash.” It is the refusals:

- Refuse to generate video until YES.
- Refuse to wait on Veo in the interactive path.
- Refuse a second Veo call for a square crop.
- Refuse fake UGC, which would also be a second ethical bill.
- Refuse to autopost, which would turn a $6 film into a $6 mistake on a real Page.
- Refuse to hide the burn. If Veo is 99% of COGS, say so.

That is how a deterministic kit stays in the range of a neighbourhood P&L.

## What we are asking Google’s stack to be

Enterprise agent platforms are usually demoed on enterprise data. The grass roots already gave Google the other dataset: millions of listings, photos, hours, and reviews. The missing piece was an agent that treats that listing as a brief, spends a few dollars of Vertex like a producer, and hands the owner a kit they still control.

We built that for the All Things Agentic hackathon. The roost is public. The architecture diagram is public. The observatory is public. The backend path is public. The Glen’s Bakehouse kit is a seeded demo — do not email, call, or review the bakery.

Paste a listing you own.

— Leadsy Flock, August 2026
