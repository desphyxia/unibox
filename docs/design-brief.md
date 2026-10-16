# Design Brief (Working Title Not Chosen)

Status as of 2026-10-16. One page for people and coding agents who need the whole picture. Decisions come from `docs/concept-state.md` section 12; evidence from the reference-game research (`docs/reference-games-comparison.md`). Nothing here is built.

## What it is
A cosy creature-care game for children aged 4-10 on iPhone and iPad first, Android after. The child raises gentle mythic creatures (unicorns plus other kinds) on a small island whose weather and seasons change on the game's own clock. No failure, no death, no timers, no chat, no ads. Parents get a templated storybook of each creature's life.

## Who and why
- **Child:** plays alone, cannot necessarily read; wants a creature that is theirs.
- **Parent:** buys, reads the storybook, wants a safe, calm game with no tricks.
- **Gap:** the big sandbox games (Toca Boca World, Avatar World) are dress-up and decorating with no creature care; unicorn pet games have huge installs but are shallow, ad-supported and rated about 3.7-3.9; Livly Island proves cosy creature care sells to a small, loyal audience. No unicorn game found combines care, breeding, a living world and a parent storybook.

## Pillars
1. **A creature that is yours:** hatch it, care for it, dress it, breed it, watch it grow into a guardian.
2. **Gentle care:** moods and simple needs (hunger and thirst, sleep and energy, affection and play), never punishment.
3. **A world that moves on its own:** island-time day and night, one weather and season pair.
4. **Fair and calm:** no ads, no marketing identifiers, no loot boxes, no pressure to return.
5. **A story for the parent:** each creature's life, written from templates.

## Core loop
Hatch an egg, meet the creature, care for and dress it, explore two places (meadow, pond), pair two adults, pick one trait from each parent, hatch a new baby that carries those traits. Deterministic, no randomness in outcomes.

## Prototype scope (about 3 months, solo with AI agents, Godot)
- 3 creature kinds (unicorn, water creature, fox spirit), layered recolourable 2D parts; 4 trait types (colour and pattern, horn/wings/tail, mane, temperament), 3 temperaments (calm, playful, curious); same-kind breeding only.
- 2 places, about 12 decor items, a handful of outfits, 3 life stages, creatures never die; elders become guardians.
- Island-time clock: sun-and-moon arc plus an optional analog clock.
- Parent area behind the gate: storybook, purchases and restore (stubbed), play controls, privacy and delete-all.
- Two variants to test: visible needs and no visible needs. Sound is creature noises and music only.
- Out of scope for the prototype: Builder mode, multiplayer, Android build, real purchases.

## Monetisation (decided, not built)
Free first island. Later islands as one-time purchases restored across devices. A free weekly item. Small optional outfit and decor packs, parent-gated and outside the play flow. No subscription.

## Compliance rules the design must keep
Apple Kids Category (parental gate for purchases and links, no third-party analytics or ads), COPPA (no persistent identifiers or location, no accounts for a child, delete on request). Android rules (Google Play Families) are not yet researched and wait until after the iOS prototype. Names are not trademark-cleared.

## How we will know it works
A playtest with 5-10 children (focus ages 4-6, a few 7-10), one session each. **Pass:** children keep playing 10+ minutes unprompted and make a creature their own. **Stop:** most are bored within minutes, or 4-year-olds cannot reach the core loop alone. The session script is `docs/first-ten-minutes.md`. Measurement is observation plus a local on-device log; no network.

## Biggest risks
- **Scope:** four trait types across three kinds, plus decor, dressing and a storybook, is heavy for one person; the thin-slice rule applies.
- **Needs are unproven:** neither reference game has visible needs; the A/B test checks this by observation only.
- **Thin evidence on young children:** no verified 4-6-year-old playing alone was found in research; the playtest is the first real data.
- **AI-assisted assets:** ownership and App Review implications to check before anything ships.
- **Creators and discovery:** with no goals or secrets, there is less for creators to film; design reveals (hatching, trait choice), makeovers and weekly drops.
- **Name:** undecided and not cleared.

## Open decisions
Theme (unicorn or a mix), working title, art mood (three style samples to be made), the first creature kind order in tests, and what to do about the name step for a child who cannot type.
