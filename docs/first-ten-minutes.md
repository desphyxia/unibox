# First Ten Minutes: Prototype Playtest Script

Status as of 2026-10-16. This turns the decisions in `docs/concept-state.md` (section 12) into a shot-by-shot first session. It is a design proposal to react to, not a built feature. Times are targets for a child aged 4-6; faster or slower is normal.

**Constraints it respects:** no reading for the child; no narrator (creature sounds and music only); no personal data; no failure states; one session per child; island-time (the game's own clock, not the real one); two prototype variants, **A: visible needs** and **B: no visible needs**, switched in the parent area.

## 1. Timeline

| Time | What the child sees and does | Variant notes |
|---|---|---|
| 0:00-0:20 | Soft music, a still meadow at dawn. One big glowing egg in a nest. No text, no menu. A pulsing glow invites a touch. | Same in both. |
| 0:20-1:00 | **Hatching.** The first tap wobbles the egg with a sound. Three more taps (or a rub) crack it, then the baby creature hatches with a small burst of light. | The kind of creature (unicorn, water creature, fox spirit) is set by the facilitator in the parent area so kinds can be compared across children. |
| 1:00-2:00 | **Meet.** The baby blinks, answers taps with a sound and a heart, follows a dragging finger, and can be walked around the meadow. Happy, sleepy and curious animations show its temperament (calm, playful or curious). | Same in both. |
| Any time | **Name tag.** A small blank tag floats above the creature. Tapping it opens the parental gate; a parent types a name and the tag shows an icon plus the name in the parent area. Skipping is fine: until named, the creature wears a placeholder icon. Naming never blocks play. | Same in both. |
| 2:00-3:30 | **First need, gently.** The creature looks at an apple tree and sighs; a soft glow points to the food. The child drags an apple to it; it eats and glows. Nothing bad happens if the child ignores it. | **A:** the cue plays. **B:** no cue; the apple is simply there to offer. |
| 3:30-5:00 | **Pond.** A path leads to the pond. The creature drinks, splashes and reacts to ripples; clouds drift as island-time moves toward midday. A basket offers three decor items (plant, lantern, toy) to place anywhere. | **A:** a thirst cue near the pond. **B:** none. |
| 5:00-6:00 | **Dress.** A basket of ribbons and accessories; the child drags them onto the creature. The game notes the first dressing for the storybook. | Same in both. |
| 6:00-8:00 | **Nest and second adult.** A nest glows; an adult of the same kind waits at the pond edge. The child pairs the two to spend a moment together; hearts rise; an egg appears. **Trait choice:** two side-by-side previews, one trait from each parent, with the creature changing live; confirm with a tap. | In session one only two trait types are offered (colour or pattern, and mane); the rest are set by default and unlock later. Both variants. |
| 8:00-10:00 | **New egg hatches.** The baby carries the traits the child chose. Island-time moves to dusk: the sun sets, the moon rises, lanterns glow, creatures yawn. | **A:** the baby curls up and the child can tuck it in (energy cue). **B:** the baby simply naps. |
| 10:00+ | Free play. The facilitator says nothing and does not suggest anything. The child stops when they want. | Same in both. |

The weather and season pair is one gentle weather event (a soft rain at some point after minute 8) and one season; the island changes look first, then creature behaviour. Growth and place effects are later builds.

## 2. What the playtest watches

These map to the pass and stop gates in `docs/concept-state.md` 12d. The facilitator counts; they do not rate.

**Pass signals**
1. **Keeps playing:** is the child still playing at 10 minutes without being prompted; do they ask to play again.
2. **Makes it their own:** says or shows "mine", names or asks to name it, picks traits deliberately, returns to the creature, shows it to a parent, repeats a favourite action.

**Stop signals**
1. **Bored:** stops or needs prompting before about minute 5; wanders without touching things.
2. **The youngest cannot use it:** a 4-year-old who cannot hatch the egg, find the apple or drag an item alone. Count adult interventions per step.

**Also record (not part of the gate):** time to first hatch; whether a child notices the need cue in variant A and what they do; distress when a creature sighs or looks sad; which kind of creature the child gravitates to; whether they reach the second egg and what they pick.

## 3. Local event log (on-device, read by hand)

No network, no identifiers. One line per event with a timestamp since session start and the variant and creature kind:
`session_start`, `egg_tap`, `hatch`, `creature_tap`, `creature_walk`, `food_given`, `water_given`, `decor_placed`, `accessory_added`, `name_tag_opened`, `name_set`, `nest_pair`, `trait_chosen(type, parent)`, `egg_hatch_second`, `dusk_reached`, `session_end`.

## 4. Open points to resolve before building

- **Name step friction.** You chose "parent types it". In a one-session test a parent step can interrupt the flow, so the design makes it non-blocking and gives the creature a placeholder icon. Confirm this, or the facilitator could name the creature before the child starts.
- **Which kind first.** The facilitator sets the first creature kind per child; decide the order (for example rotate unicorn, water creature, fox spirit).
- **Trait choice for the youngest.** Two trait types may still be a lot for a 4-year-old; the first playtest should note where they hesitate.
- **Needs comparison.** A and B need about half the group each, so with 5-10 children each variant sees only 2-5 children. The comparison will be observational, not statistical.
- **Distress check.** The sigh in variant A is the riskiest moment; plan to stop the test and remove it if a child is upset.
