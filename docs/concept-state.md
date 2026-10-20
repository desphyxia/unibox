# Unicorn Sanctuary: Concept State

Status as of 2026-10-12. Research and concept only; no design, code or art has started. Reference-game research is in `docs/toca-boca-world-findings.md`, `docs/toca-boca-world-quantified.md`, `docs/avatar-world-findings.md` and the cross-game summary `docs/reference-games-comparison.md`. Section 12 holds the decisions from the 2026-10-12 interview.

## 1. What this is
A mobile game (iOS first) for children aged 4-10, in the sandbox space of Toca Boca World and Avatar World. Working title: none yet (not chosen or cleared).

The full research write-up is a Claude doc (artifact `6e4d8bb4-72e2-4e24-b310-234246d8f809`). This file was written from the hand-off brief; the doc's text has not been read in full.

## 2. Decisions made
- **Segment:** goal-free sandbox, not subscription learning apps.
- **Age floor:** 4. The reference games both sit at 4+ on the App Store, and neither targets 3-year-olds.
- **Learning:** woven into game systems, with no separate mode, tasks or quizzes. New islands unlock as in-app purchases, so the free first island must carry the core learning loop.
- **Purchasing:** the first island is free and complete. Later islands are one-time purchases that restore across devices. No loot boxes.
- **Storybook:** a parent-facing record of play, written without AI (templated).
- **Life cycles vs. "no death or failure":** to be adapted to fit the audience during design.

## 3. Concept
Theme: a unicorn sanctuary archipelago, with unicorns as the anchor and other gentle mythic creatures arriving as content.

Differentiators:
1. Creatures with simple needs and moods; gentle care, no death or failure.
2. A reactive world: real-time day/night, weather and seasons that change the islands.
3. Deterministic breeding: choose and preview traits, no random loot boxes.
4. An auto-written parent-facing storybook of play; no kid-facing chat.
5. Depth for the full age range: a "Builder mode" for ages 8-10 with terraforming and if-then rules.
6. Fair purchasing (see above).

Learning is embedded: creature care teaches life cycles and cause and effect; weather teaches the water cycle; breeding teaches early genetics and patterns; building teaches shapes, symmetry and counting; Builder mode teaches if-then logic. Difficulty adapts silently, and the parent storybook surfaces what the child did.

## 4. Market and reference games
2025 revenue, iOS + Google Play (Business of Apps / AppMagic), $M: Toca Boca World 88, Lingokids 38, Bluey: Let's Play 19, Avatar World 17, Keiki Learning 13.5, ABCmouse 13.5, Kiddopia 13.5, Reading Eggs 9, Barbie Dreamhouse 8, Sago Mini World 7. Subscription learning apps dominate the 3-6 end. These figures are a year old and no kids-specific 2026 numbers were found; re-pull before using them in a business case.

**Toca Boca World** (Toca Boca AB, Spin Master): goal-free sandbox with character customization, home decoration and story play in themed locations. Single-player, no chat, no third-party ads, COPPA-compliant. Free download with content packs; monthly content; Friday gifts at an in-game Post Office. App Store rating 4+ (an earlier listing also carried a "Made for Ages 6-8" label; third-party sources say 4+ to 6-12). Praised for safe creativity; criticized for purchase costs and purchases lost on device changes.

**Avatar World** (Pazu Games): a town with many locations, avatar and home design. Free with in-app purchases (an Avatar Pass). About 1M App Store ratings at 4.7. App Store rating 4+; the developer says "up to 5 and over". An Australian review (Nov 2023) recommended parental guidance under 4 because of purchases and ads. Building a licensing and merchandise program.

Neither is educational by design, and neither has unicorns as a key element as far as searches found (not exhaustive).

**Observed in a Toca Boca World walkthrough** (frames only; no audio or transcript): a side-scrolling loft with an open layout; a dressing-room customizer with undo/redo and a saved-outfit wardrobe; interactive objects (fridge, TV content, food on the table, watering can); two controllable characters posed in activities; a day/night indicator; a promotional stage scene.

## 5. Alternative themes considered
Dinosaurs and prehistoric life (strongest evidence of sustained kid interest), ocean or coral reef, space outposts, animal rescue sanctuary, fantasy forest, bakery or cafe. Plan: test unicorn, dinosaur and ocean concepts side by side during validation. Toca and Avatar World won with neutral everyday-life settings, so the loop matters more than the theme.

## 6. Compliance facts (checked 2026-10-11)
- **Apple Kids Category (guidelines 1.3, 5.1.4):** no links out or purchases outside a parental gate; no sending personal or device information to third parties; third-party analytics and ads "should not" be included, with narrow exceptions (analytics that never touch the IDFA, identifiers, location or device data; contextual ads with human review). A parental gate is not the same as COPPA parental consent.
- **COPPA (FTC):** persistent identifiers and precise geolocation are personal information; verifiable parental consent is required; third-party SDKs need vendor diligence; data retention is limited. The amended rule's compliance date was 2026-04-22 (from law-firm and trade sources; not confirmed on ftc.gov).
- **Unverified:** Apple's reported five-tier age ratings (4+, 9+, 13+, 16+, 18+) with a questionnaire. Seen only on aggregator sites; confirm on Apple's App Store Connect help.

## 7. Draft build phases (each ends with a gate)
1. **Validate:** clickable prototype of one island with children and parents; the gate includes an early-childhood educator confirming the learning intent.
2. **Foundations:** engine (Unity or Godot), 2D or 2.5D art, data-driven content. Choose analytics tooling here, given the Apple limits above.
3. **Vertical slice:** one island, creature creator, about 20 items, care loop, day/night.
4. **Systems:** needs and moods, breeding, weather, saves, parent gate.
5. **Content and art pipeline:** three islands, a few hundred items, audio, monthly cadence.
6. **Compliance:** Apple Kids Category, COPPA, GDPR-K, parental gates, no third-party ads or tracking, restore purchases.
7. **Soft launch:** release in a few small markets and measure D1/D7/D30 retention (share of installs returning on day 1, 7 and 30), session length, and parent conversion (share of players whose parent buys an island).
8. **Live operations.**

## 8. Awareness and launch (ideas, not a plan)
App Store optimization and editorial features, parenting and child-safety reviews, kid-safe YouTube creators, the storybook as parent-driven sharing, later licensing, and recurring content rituals. Paid ads are constrained by Apple's kids-app rules and COPPA; verify current rules and test in a soft-launch market first.

## 9. Risks
- **Look-alike:** the genre is open, but both leaders' characters, art and names are protected. Use original designs and clear any name.
- **Kids-safety rules** can block approval; re-verify against current Apple guidelines.
- **Discoverability** against incumbents is hard.
- **Learning claims** need testing with children and an educator before any marketing.
- **Evidence quality:** some third-party pages, including a gameplay comparison for Avatar World, were weak or conflicting. Treat the assessment as directional.

## 10. Revisit later
- **Breeding vs. genetics:** deterministic trait choice may not teach real inheritance patterns.
- **Real-time weather and seasons:** resolved 2026-10-12: island-time, independent of real time and location (see section 12).

## 11. Open items
- **"Little mode":** resolved 2026-10-12: no separate Little mode; one mode that deepens with use, Builder mode as a later unlockable layer.
- Final theme and working title. (Engine, art style and the 3-month milestone are set in section 12.)
- Budget beyond solo time with AI agents; timeline after the first prototype.
- Re-pull 2026 market figures; confirm the Apple age-rating tiers.

## 12. Interview decisions (2026-10-12, user answers after the reference-game research)
These supersede earlier open items where they conflict.

**Product shape**
- **No separate Little mode.** One mode that deepens with use: everyone starts with exploring, caring for and dressing creatures. Builder mode (ages 8-10) is an unlockable layer, **built after the core creature loop is proven**, not in the prototype.
- **No creature cap on the free first island.** Revenue comes from new islands, creature families, outfits and decor, not from limiting what a child keeps.
- **Stay goal-free like Toca.** No collection book or quests; creature care, moods and breeding provide the structure. (Avatar World's hidden-object hunts were offered and declined.)
- **Needs and moods:** unproven in either reference game, so **prototype both a version with visible needs and one without, and test**.
- **Must stay true whatever the theme:** creature care with moods, deterministic breeding, a reactive world, and the parent storybook.
- **Open-ended sessions, no daily pull.** Nothing is lost or missed if a child stays away.
- **First minutes:** the child meets and chooses a first creature (a short hatch or rescue moment), then the creature creator, then the island. The child is not an avatar-maker first.
- **Life cycle without death:** creatures grow baby, young, adult; **they never die; elders become guardians** (bonuses or stories). Offspring carry on the family.
- **Breeding (prototype):** an egg appears from two creatures and the child **picks one trait from each parent** with a live preview. Deterministic. Real inheritance rules and a family-tree layer are a later, older-child layer.
- **World clock:** **island-time, independent of real time and of location.** Day/night, weather and seasons run on the game's own clock, so nothing depends on location or the device date and the earlier location revisit item is resolved. (Check this against the wish below to teach telling the time.)
- **Multiplayer:** none at launch; revisit after a compliance review.
- **Text:** no reading needed for the child (icons, colour, animation, short voiced cues); all text in the parent area; English first.
- **Storybook:** lives inside the parent-gated area, readable and savable as a PDF or image; no accounts or uploads.

**Learning (embedded; no claims until tested):** empathy and caring, cause and effect, patterns and inheritance, creativity and design, and **everyday concepts: the clock, shapes, colours and numbers**.

**Money:** free first island; later islands as one-time purchases restored across devices; **a free weekly item**; and **small optional packs (outfits, decor), all behind a parent gate and outside the play flow.** No subscription, no loot boxes.

**Theme:** **open to a different theme.** The 3-month prototype uses the unicorn sanctuary and a **mix of creatures in which unicorns are one example**; the theme is chosen from playtests.

**Build and business**
- **Solo with AI agents.** Goal: **prove it first**: a small prototype tested with children and parents, then decide how big to go.
- **Engine: Godot**, targeting **iOS first and Android after.** Art: **layered, recolourable 2D parts** (suits combinable traits and breeding).
- **First milestone: about 3 months**: one island with creature creator, care, mood, island-time day/night and a first breeding step, tested with 5-10 children and parents.
- **Discovery:** App Store plus parent reviews, **and kid-safe creator videos**, so design for shareable looks and free drops without breaking the Kids Category rules.

### 12b. Second interview round (2026-10-12)
- **Creator content to design for:** creature reveals (hatching, trait-picking with the live preview, family tree), island makeovers across seasons and weather, weekly free drops, and storybook pages shared as images (no uploads from the game).
- **In-game clock:** a sun-and-moon arc as the main time cue, plus an optional simple analog clock tied to creature routines (breakfast, play, bedtime), clearly "island time", so it is not mistaken for real time.
- **Learning to test in the first playtest:** empathy and caring, cause and effect, patterns and inheritance. Clock, shapes, colours and numbers come through in design but are not the first test.
- **AI use:** AI-assisted art, sound and text **with human cleanup**. Open: ownership of AI-assisted assets, consistency across a layered-parts library, and App Review and parent-trust implications; check before any asset ships. The storybook text stays templated, not generated.
- **Playtesters:** a mix, starting with family and friends' children, then an educator and a few outside families. Keep written parent consent.
- **Measuring:** observation plus simple anonymous on-device logs read by hand; no network and no analytics SDK in the prototype.
- **Android:** research Google Play Families and Android compliance **after the iOS prototype**, when a store build is planned.
- **Art mood:** not chosen; **make a few quick style samples first** (soft pastel, bold graphic, painterly storybook) and pick from them.

### 12c. Third interview round (2026-10-12): prototype content
- **Creature kinds:** 3-4 (a mix in which unicorns are one example).
- **Breeding traits:** colour and pattern, horn/wings/tail shape, mane and hair style, and temperament (a mood tendency that changes how the creature acts, linking breeding to care).
- **Island play:** a few simple decor items, a few distinct places to visit, and dressing and styling creatures. (Watching the world change is not a separate activity, but the reactive island-time world stays a must-keep.)
- **Storybook:** a running **life story per creature, egg to guardian**, templated, in the parent-gated area.
- **Scope rule: a thin slice of each.** Keep the breadth, go shallow: about 3 creature kinds, 2 places, about 12 decor items, a handful of outfits, 3 life stages, and one weather and season pair. Prove the loop before adding depth. Four trait types across 3 kinds is the multiplier to watch.
- **Needs and moods to build in the visible-needs variant:** hunger and thirst, sleep and energy, affection and play. Comfort in weather is not in the first build.
- **Parent area (behind the gate):** storybook, purchases and restore, play controls (sound, rest reminders, optional session limit), privacy and data with a delete-all-progress button. The prototype is not shipped, so purchases and restore can be stubbed until a store build.
- **Audio:** creature sounds and music, **no narrator**; nothing to translate and no voice talent needed.

### 12d. Fourth interview round (2026-10-12): playtest gate and prototype content
**Playtest pass gate (all of the following, not a score):**
- Children **choose to keep playing**: most play 10+ minutes unprompted and ask to play again.
- Children **make a creature their own**: they name, style or choose traits and show attachment.
**Stop or change direction if:**
- Children are **bored within minutes** (most stop or need prompting to find something to do), or
- **the youngest cannot use it**: 4-year-olds cannot reach the core loop alone.
**Sample:** 5-10 children, one session each, **focused on ages 4-6 with a few 7-10**. One session cannot show retention; the gate measures first-session engagement and attachment only.
Not in the gate (noted, not decided): response to creature needs, distress at needs, parent willingness to pay. The needs-versus-no-needs comparison therefore needs its own observation notes, since the gate does not judge it.

**Prototype content**
- **Creature kinds (3):** unicorn, a sea-horse or water creature, and a fox spirit or forest creature.
- **Places (2):** meadow and pond or lake.
- **Temperaments (3):** calm, playful, curious.
- **What changes with the island-time weather and season pair:** how the island looks, what creatures do, what grows, and how places feel (for example the pond freezing). All four were chosen. This is more than a thin slice if each is built deeply; build the **look** and **creature behaviour** first, then **growth** (tied to hunger) and **place effects** as time allows.

### 12e. Fifth interview round (2026-10-13): interaction, breeding flow, name
- **Touch:** tap to pet or call a creature (it answers with a sound and small animation); drag food, water or toys onto it; drag a creature to walk it to places. Press-and-hold to cuddle was not chosen.
- **Breeding flow:** the child picks two adult creatures to spend time together; after a short moment an egg appears, the child picks traits (one from each parent, live preview), and the egg hatches on the island.
- **Cross-kind breeding:** same kind only in the prototype (mixed-kind offspring is a later, larger feature).
- **Name feel:** cosy and descriptive. **Not chosen yet.** Candidates checked on 2026-10-13 against US App Store search and a web search (this is **not trademark clearance**; it only found no exact-name app or game): *Moonmeadow Isles*, *Glimmer Meadow Isles*, *Dewdrop Isles*, *Willow Isle Sanctuary*. Near-misses to avoid confusion with: Moonstone Island (a creature-collecting life sim), Moondrop Isle, Creature Isle, Livly Island, Hello Kitty Island Adventure. *Starlit Sanctuary* is close to a registered "Starlit Adventures" mark for game software. A real clearance needs a search of the USPTO, EUIPO and WIPO databases (ideally by a trademark attorney) before any name is used publicly.

**Name update (2026-10-13), second batch.** Checked the same way (US App Store, Google Play and a web search; not trademark clearance) and found no exact-name app or game: *Thistledown Isles*, *Fernlight Isles*, *Cloverlight Isle*, *Pebblebrook Haven*, *Hollowhill Haven*, *Honeydew Haven*, *Whistlewood Haven*, *Brightwater Haven*, *Starmeadow Haven*, *Mossglow Isles*. Avoid *Little Haven Isles* (close to the Switch game "My Little Haven" and "Littlehaven").

**Games found with similar names that are close to this concept**
- **Livly Island** (ENSAPIA, 2021, 4+, free with in-app purchases, about 2,900 ratings, 4.6): the closest. Raise small creatures (70+ species) on your own island: feed, keep clean, colour change from food, transformation potions, decorate the island, dress an avatar, a part-time job. From the store description only; breeding and moods unconfirmed.
- **Creature Isle** (single indie developer, released 2026-03, 4+, free, no ratings yet): gentle island, find and adopt creatures, nurture a family, co-op with friends, build a haven. Closest in wording to a "sanctuary"; tiny so far.
- **Hello Kitty Island Adventure** (Apple Arcade, 4+, about 160,000 ratings): cosy island life sim with licensed characters; not creature raising, but shows the cosy-island style working with a young audience.
- **Moonstone Island** (PC and Switch, 12+ on mobile via Crunchyroll): creature-taming and card battles; not similar for this audience. **Moondrop Isle** is an interactive fiction game; unrelated.

**How successful is Livly Island? (2026-10-13)** A profitable niche, not a mass hit. Apple: about 98,000 ratings in Japan at 4.60 against 2,921 in the US; Google Play: about 3.0M installs, 32,000 ratings at 3.90, listed as "Social". The publisher's 2025 press kit claims **over $50M revenue since 2021** (company claim, unaudited; roughly $12M a year by simple division) after buying the rights for about $110K and rebuilding it over nine months; the 2.6M monthly users in that kit combine Livly Island and Pokecolo. The only independent figure found is a Sensor Tower snapshot of about $50K in one US week (Q3 2024). Monetisation is in-app purchases of $0.99-$99.99 per item, no ads. Audience age unverified, probably older than 4-10. Reach is about 1-2% of Avatar World's by installs.

**Unicorn-focused games (2026-10-13, US App Store and Google Play searches; not exhaustive)**
- **Demand is real.** The biggest unicorn pet-care games are TutoTOONS' *Kpopsies - Hatch Baby Unicorns* (about 61M Play installs, 3.91), *My Baby Unicorn - Pony Care* (about 47M, 3.88; ads plus in-app purchases $3.99-$159.99) and *My Baby Unicorn 2* (about 24M, 3.73). Pazu, BabyBus and others add dress-up and salon games at 5-8M installs.
- **Quality is low where the volume is.** Those leaders are ad-supported tap games rated 3.7-3.9 on Play, against 4.36 for Toca and 4.73 for Avatar World. The best-rated unicorn pet game found is *My little unicorn: Pets academy* (about 4.5M installs, 4.51).
- **No iOS leader.** The only unicorn kids game over about 200,000 iOS ratings is a pet-salon game; Toca has about 0.9M.
- **No unicorn game found that combines** real creature care and breeding, a living world and a parent storybook. Nearest: Livly Island (not unicorn-focused) and Pazu's *Magical Unicorn World*.
- **Risks:** a crowded "unicorn" search; installs are not revenue (none found for unicorn titles); the audience looks girl-skewed (inference from titles); a licensed unicorn game (My Little Pony, Unicorn Academy) was not ruled out.
- **Implication:** keep the prototype's unicorn plus a mix of creatures, test whether children respond to unicorns specifically, and if they do, use "unicorn" in the store subtitle with a distinctive main title.

### 12f. Sixth interview round (2026-10-16): the first ten minutes
- **Opening:** a glowing egg in the meadow hatches at a touch (three or four taps or a rub). The first creature's kind is set by the facilitator so kinds can be compared across children.
- **Naming:** **a parent types the name** in the parent area. Design consequence: the name step must be non-blocking, with a placeholder icon until named (see `docs/first-ten-minutes.md`, open points).
- **First need (visible-needs variant):** at about 2-3 minutes, gently: the creature sighs at an apple tree with a soft glow; ignoring it has no consequence.
- **Breeding in session one:** a second adult is already on the island; from about minute 6 a nest glows, the child pairs the two, and an egg and trait choice follow (two trait types offered in session one).
- **New documents:** `docs/first-ten-minutes.md` (shot-by-shot session script, what the playtest watches, the local event log, open points) and `docs/design-brief.md` (one-page brief for people and coding agents).

**New open items from these answers**
- **Android compliance** (Google Play Families policy, data safety, an Android age-gate pattern) has not been researched; only Apple's Kids Category and COPPA were checked. Scheduled after the iOS prototype (12b).
- **Teaching the clock with island-time:** resolved in 12b (sun-and-moon arc plus an optional analog clock, labelled island time); watch in playtests for confusion with real time.
- **Learning outcomes list is long:** resolved in 12b (test empathy, cause and effect, patterns and inheritance first).
- **Goal-free plus no quests** leaves creature care, mood and breeding to carry engagement; the needs test above is where that is checked.
- **Creator-video discovery** conflicts mildly with no secrets or goals (Avatar World's creators mostly film secrets and free coins); decide what creators will film.
- **AI-assisted assets:** decided in 12b to allow with human cleanup; ownership and App Review implications still to check.

### 12g. Art direction (2026-10-16)
- **No person involved in the art** (user): all art is generated by AI or code; there is no human artist and no human cleanup. This supersedes "AI-assisted art with human cleanup" in 12b.
- **Style chosen: soft pastel** (over bold graphic and painterly), after three style samples, a detailed foal and a full unicorn study (`art/`). The painterly look is dropped for the game; it may return for storybook pages.
- **Route in use:** Claude writes the art as code (layered SVG: one body outline, limbs and hair as tapered ribbons, gradient shading). Colour variants are palette swaps of the same shapes, which suits deterministic breeding.
- **AI image generators for concept art (researched 2026-10-16, not tried):** Midjourney (paid plans only; companies over $1M revenue need Pro or Mega; you own your assets; Midjourney gets a broad licence), Leonardo (paid subscribers own output; free-plan output belongs to Leonardo), Ideogram (hosted terms claim no ownership but disclaim liability), Recraft (SVG output; free-plan images owned by Recraft; no evidence of separate layers), Adobe Firefly (trained on licensed content; indemnity mainly an enterprise entitlement). Character consistency across many poses is the weak point of all of them, per secondary sources.
- **Ownership:** the US Copyright Office (January 2025 report; Supreme Court declined review in 2026) says prompts alone do not make a person the author; only human selection, arrangement or modification can be protected. Purely AI- or code-generated creature images are therefore probably unprotectable, and could be copied. The name and logo are a separate trademark question. App Review and parent attitudes to AI-generated art are unchecked.
- **Round 4 (2026-10-16, `art/generators/artgen4.py`):** the unicorn is now a rig with poses (stand, walk, sleep), a mirrored front view and trait layers (wings, bobbed mane, coat patterns, colour sets). Loaded through Godot 4.7.2's own SVG loader: renders like the browser once clip paths holding several shapes were merged into one path (Godot clipped them wrongly). No filters are used. Weak spots: pale cluttered wings, the sleeping pose reads as a loaf, each pose needs hand tuning, only the unicorn exists.
- **Round 5 (2026-10-17, `art/generators/artgen5.py`):** wings rebuilt as an arm carrying three rows of rounded feathers (raised, higher when walking, folded over the back when asleep; far wing behind the body); sleeping pose redrawn as a lying pose with forelegs stretched under the resting head and a folded hind leg with crease strokes. Found and fixed a round-4 bug: the coat gradient was applied inside the head's moved frame, so a moved head was the wrong colour. Godot 4.7.2 loader matches the browser. Weak spots: wing still pale and partly scale-like, hind leg in the sleeping pose is mostly crease lines, winged SVGs 150-220 KB, no animation, only the unicorn exists.
- **Art quality bar (2026-10-17):** the user set the round 5 unicorn as the minimum detail and ambition for all creatures and rounds. Definition and the open weak-parts register are in `art/quality-bar.md`.
- **Round 6 (2026-10-17, `art/generators/seahorse.py`):** sea-horse built on a spine-ribbon skeleton (idle, swim, sleep, mirrored front view; fin, ridge, crest and pattern layers). Shared ribbon, hair, face and shading code carried over unchanged; the skeleton itself is new, so each creature kind needs its own. Loaded in Godot 4.7.2 and checked at 320 px. Round 7 (same day): front view rebuilt from the side view's depths (it was too wide), back view, snout and tail traits, flowing crest, smooth belly shading, fuller scene. Open items are in the register in `art/quality-bar.md` (items 11-14).
- **Round 8 (2026-10-17, `art/generators/seahorse.py`):** user said the round 7 front was now too thin and asked for something between thin and wide, one style only in all views, and the crest, fins and stripes reworked. Front and back widths set about halfway (neck 100, chest 166, skull 176; old wide 168/204/240, thin 72/128/132). Crest redone as hair that rises from the crown and falls (side, front, back views share it). Dorsal fin moved to the lower back so the pectoral fin at the neck stays separate. Stripes follow the local body width. Artifact UZu5dsc9ExbKxt34p4DQR6 v3; samples in art/samples/round6-seahorse (five SVGs); open items in art/quality-bar.md 12-13.
- **Round 9 (2026-10-17, `art/generators/seahorse3d.py`, `backdrop.py`):** user said the views are not consistent (same feature looks different, such as the hair), asked whether a full 3D version rendered from would be easier, and to keep going until no style or consistency weak spots are left (file size and animation parked). Built the sea-horse as one 3D model in Blender 4.5 LTS (official download, checksum verified, headless): body tube, lofted head, hair locks, fins, stripes and star, eyes. Seven renders (idle side, three-quarter, front, back; swim; sleep side and three-quarter), transparent PNG over a shared flat backdrop. Open decision: the rendered look differs from the flat SVG unicorn; recommended to rebuild all creatures in 3D. Artifact UZu5dsc9ExbKxt34p4DQR6 v4.
- **Round 10 (2026-10-17, `art/generators/unicorn3d.py`, `backdrop_unicorn.py`):** unicorn rebuilt as one 3D model (user request after approving the 3D sea-horse): same pose numbers as the 2D unicorn, seven renders (stand side/three-quarter/front/back, walk, sleep side/three-quarter), wings opened outward so they show from front and back, spiral horn, shared face style with the sea-horse. Artifact NA62DuLywRRC4mPiZL7zJz. **Revision b (same day, after user feedback: eyes too far apart, rendering cut off, leg sharp against the body, eyebrow misplaced, 2D head looked better):** eyes moved forward on a narrower face, lid and lashes rebuilt on the eye's rim, forelock as two bangs, torso/neck/legs fused by voxel union with smoothed joins, wings rebuilt as smooth feather sheets, mane as thin spaced ribbons on an analytic body surface, bounce light; study page now serves WebP (cut-off not reproducible, likely a partial load of the big PNGs). Open: boxy folded wing and rib-like mane in the sleeping pose, wings thin from the front, plain hooves, no Godot/device test.

- **Round 11 (2026-10-17, `art/generators/unicorn3d.py`, `backdrop_bloom.py`):** user rejected round 10b as 'not good enough' and pointed to a reference unicorn (a stock watercolour picture; used as direction only, nothing copied or traced, not to be used in the game). Rebuilt look on the same 3D rig: rounder chibi proportions (`chibify`), Bloom palette (aqua-white coat to lavender legs, pink-peach-lilac mane, pearl spiral horn, dark-blue eyes), long wavy curled mane and tail, two bangs, crest rope, flowers trait (crown, back garland, fetlock cuffs), glitter freckles, prance pose with a raised foreleg, watercolour-wash backdrop; wings are now an optional trait (`--wings`). **Revision b:** user said the face/head looked off and the mane was wrong anatomically (two mirrored sides, nothing in the middle). Head profile rebuilt from a close study of the reference (steeper forehead and bridge, small narrower muzzle with lip and chin, narrower skull), eye rebuilt as a flat almond with raised outer corner placed high on the face; mane is now one continuous crest mass with the side locks growing out of it and the bangs starting at the crown centre. **Revision c:** user said everything was built symmetrically (two mouths, two mirrored mane halves, mirrored flowers), the eye shape looked nothing like the reference, and the head should be pointier and more horse-like; asked for a rebuild if needed. Rebuilt: head as a long wedge (wide at cheeks, narrow pointed muzzle), eye as a flat almond decal projected onto the face (navy, paler lower edge, big highlight, lid flick, lashes), one continuous mouth line, head turned and tilted as one rotated group; mane as three overlapping hair sheets growing from the crest and falling over the near side (plus short spill on the far side), bangs, tail, flowers, freckles, ears, wings all deliberately unequal. Artifact NA62DuLywRRC4mPiZL7zJz v5. **Revision d:** user flagged floating flowers, still two mouths, dot nostrils, mane not running down the whole neck, and asked for the best unicorn imaginable with the reference as the minimum bar. Fixed: mane rooted on the real neck top line (the loft bulged past the 2D outline), parting and arching over the crest, never inside body or head; head rear pulled forward; flowers rest on hair or skin; one mouth traced round the muzzle; comma nostrils; aqua-lavender coat and lower exposure; shaped silver hooves. Artifact v6. Open: no painted brushwork on the animal, tail reads as one rope from the side, simple flowers, plain hooves, raised leg tucked, no Godot/device test.
- **Round 12 (2026-10-18):** tried a code-only watercolour painting pass over the renders (glazes, wet edges, paper grain, line work, stroke-painted hair). User: "Revert the painted look. It was better before." Reverted; the soft rendered 3D look of round 11d stays. Do not reopen the painted finish unless the user asks.
- **Round 13 (2026-10-18, `art/generators/fox3d.py`):** user asked for \"the most awesome fox spirit with great ambition\". Built a chibi kitsune as one 3D model with real strand fur (combed and tufted by region: plush body, cream bib, cheek ruffs, ear tufts, fluffy tails with glowing flame tips), teal almond eyes (the unicorn's decal eyes), smooth cream-and-apricot face with rose eyeshadow and a forehead flame, plum nose, one smile, plum stockings and ear tips, three tails, floating foxfire, ribbon with bell, ear blossom; poses sit, stand, play bow, sleep; tail count is a trait (1-9, idea: tails grow with life stage). Shares the unicorn's palette family and watercolour backdrop. Open: own design without a reference; slow fur renders; sleep pose; no Godot/device test.
- **Round 14 (2026-10-18): how creatures get into the game.** User decided all creatures share one finish, and that creatures go into the game as **pre-rendered sprites** (renderings), not real-time 3D; the 3D models stay as the source. Proof done: the fox is rigged in code (`FoxRig` in `fox3d.py`: head, ears, breathing, tails, foxfire, blink; fur strands follow the skin), a 24-frame 2-second idle loop was rendered at game size with full fur (18 min CPU, frames 311x487 after crop), and it plays in Godot 4.7.2 at 60 fps on desktop (`prototype/fox-sprite-test`): about 3.5 MB per loop as ASTC textures, 9.8 MB scene texture memory. Shadows are drawn by the game, not baked (Blender's shadow catcher leaves a haze). **No Mac (2026-10-18):** the user has none and won't buy one. Quick iPad checks use a web build served over home Wi-Fi (`serve_web.py`, sound off on plain http); real device tests and the store build will use a cloud macOS build to TestFlight (needs the $99/year Apple Developer account). Open: walk cycles need real leg bones, layered parts for traits, same rig and finish for the unicorn and sea-horse.
- **Open:** a second creature kind (sea-horse, fox spirit) to test whether the rig carries over; a running Godot scene and a device check; animation; the generator comparison before the art route is final.
- **Round 15 (2026-10-20): first playable slice.** `game/` (Godot 4.7.2) plays the first part of `docs/first-ten-minutes.md` with the fox in the meadow: hatch the egg by tapping or rubbing; pet, drag or call the fox; feed it apples by hand or from the grass. Calm, playful and curious temperaments react differently. The paw name tag opens a parental gate and then a name field. Variant A shows a hunger cue (the fox sighs toward the tree and the apples bounce and glow); B shows none. Island time runs dawn to dusk in about ten minutes. The parent area (press and hold the corner, then the gate) sets name, variant, temperament, time speed and new session. The local TSV event log follows section 3. Walking, reactions and eating are stand-in motions on the idle loop; the meadow art and sounds are made from code (`meadow.py`, `sfx.py`). Next: pond, dressing, the second adult and egg, rendered fox animations.
- **Round 16 (2026-10-20): the fox walks.** `WalkRig` in `fox3d.py` (a four-beat walk; leg skin and fur follow the legs; paws can't slide or go through the ground) rendered a 12-frame walk cycle with full fur in about 11 minutes. In the game the fox sits when still and walks when it moves, both anchored to the same ground point. The walk speed (120 px/s) and the playback rate are matched so paws don't slide. The meadow prototype is published at https://desphyxia.github.io/unibox/ (GitHub Pages; rebuilt by `.github/workflows/pages.yml` on every push to `game/`; sound on, since the page is https). The parent area can show and copy the event log.
