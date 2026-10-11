# Unicorn Sanctuary: Concept State

Status as of 2026-10-11. Research and concept only; no design, code or art has started.

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
- **Real-time weather and seasons:** device clock vs. the child's location. Location data is a COPPA and Apple privacy problem.

## 11. Open items
- **"Little mode":** undecided whether to have one. Neither reference game does. Options: drop it and use a single mode that deepens with use, with Builder mode as an unlockable layer.
- Final theme, working title, engine and art style.
- Timelines and budget.
- Re-pull 2026 market figures; confirm the Apple age-rating tiers.
