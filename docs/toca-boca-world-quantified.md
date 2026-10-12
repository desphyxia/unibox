# Toca Boca World: Quantified Findings

Status as of 2026-10-12. This extends `docs/toca-boca-world-findings.md` (15 videos, qualitative) with counts, prices, time shares and outside evidence. Raw coding is in `docs/data/`. Text only: no videos, screenshots or review text are stored in the repo.

**How this document is organised.** Evidence comes in three kinds and they are kept apart:

- **A. Video evidence** (40 videos: the original 15 plus 25 new). Sections 3-5.
- **B. Reviews** (14 review pages read, plus a 500-review App Store sample). Section 6.
- **C. Other sources** (the store listing, press, company site, market estimates). Section 7.

Section 8 lists where they agree and conflict. Section 9 turns the numbers into targets for the unicorn game. Section 10 lists what is still unknown.

## 1. Headline numbers

| Question | Answer | Confidence |
|---|---|---|
| How much is there from the start? | About **8-11 locations** and **39-40 characters**, plus Home Designer with a free starter house, weekly gifts and **3 saved-character slots**. | Medium. Four sources agree within a few units; they count differently. |
| How much exists in total? | The "World Bundle" card (Apr 2026) lists **88 scenes, 479 characters, 39 Home Designer houses, 3,700+ furniture and decor items, 138 outfits, 102 packs**. A 2023 bundle card listed 91 scenes, 498 characters, 1,358 furniture items. | Medium. Bundle cards are the best counts found, but they are lower bounds and exclude content that was already free. |
| So what share is free at the start? | Roughly **8-12% of locations** and **about 8% of characters**. Furniture is harder to say. | Low-medium. Different counting units; free drops keep adding to the free side. |
| What does it cost to own everything? | **$199.99 list** for the World Bundle (Apr 2026), shown as **$84.99** to a player who already owned part of it. A creator put her 2023 total at about $200. Single packs run **$0.99-$13.99**. | Medium-high for the card prices (read from frames); the totals are one creator's. |
| What is capped on the free tier? | **3 saved-character slots**; the paid Character Creator upgrade ($4.99 in 2023, $7.99 in 2022) raises it to **30**. | Medium-high. Four independent mentions. |
| How do players spend their time? | Pooled over 11 time-coded sessions (430 min): **44% building/decorating, 34% role-play in locations, 10% character creator, 5% map, 3% Post Office, 2% shop browsing, 2% loading.** The one long child session (V6, 84 min): **58% play, 20% creator, 8% map, 5% build.** Five child-play sessions together (144 min, see 5.1a): **63% play, 16% creator, 7% map, 6% Post Office, 3% build.** | Medium for the shares, low for generalising: the sample leans toward building videos, and only V6 is a child playing alone for a long time. |
| How often is there new content? | Free Post Office gifts **every Friday**; an official news post about **every 2 weeks** (4 dated posts in the 60 days before 2026-10-06); at least one **free location** in the last 3 months (Flipside Park, Aug 2026). | Medium-high. |
| What do players complain about most? | In 500 App Store reviews from 8-10 Oct 2026: **price/"make more free" about 1 in 5**, **bugs/crashes about 1 in 5**, **lost progress or purchases about 1 in 8**. The reviews skew positive (65% five-star). | Medium. Keyword coding is approximate (see 6.3). |
| Is there anything like needs, moods, breeding, a storybook, or goals? | **No** in any of the 40 videos. Exception: some locations hold small scored mini-games (arcade, a pool timer). | High for these videos. |

## 2. Method and limits

**Video selection (25 new).** Fixed in advance from YouTube search results, before any new video was watched. Rules: same game (the older name "Toca Life World" counts); not Avatar World, not another Toca app, not "free hack/code" videos; spread across dates; unedited footage preferred for the time analysis. Groups: 4 fresh-install, 7 shop, 3 long sessions plus 2 child-related, 5 update videos, 4 location tours. I had planned 6 long-session videos with at least 3 children; I found only two child-related videos (see 3.3), so the shop group got the spare slot. Combined length of the 25 new videos is 9.7 hours; the original 15 total 4.0 hours.

**Frame sampling.** Each video was tiled into timestamped contact sheets at a fixed interval (10-60 s depending on length) and every sheet was reviewed. For videos with speech I also ran a local Whisper "base" transcription. Five videos have no usable speech (silent or music only).

**Time coding.** For 11 sessions I labelled every sampled frame with one activity: play in a location, build/decorate (Home Designer), character creator, map, Post Office, shop, loading/title, other. Each frame stands for one sampling interval, so a share is "frames of that type / frames coded". Only unedited footage is coded; edited videos (updates, tours, rankings) are not time-coded.

**Reliability check.** I re-labelled 35 randomly chosen frames blind (shuffled, no timestamps) against my original labels. A first attempt was invalid because my frame extraction was misaligned by a few seconds (80% agreement). The corrected test gave **32/35 = 91% agreement, Cohen's kappa 0.88**. All three disagreements were the Post Office (a decorated party-themed Post Office, and a gift-collection tutorial step) which I had first coded as ordinary play; I recoded those frames. Treat shares as good to roughly plus or minus 3 points per category per video, not more.

**Process note on image reading.** In part of this session, image reads returned a "media removed" placeholder instead of the picture. I wrote some notes in that period. I then re-viewed the video sheets for the original time-coded videos, the third-party price cards, and a sample of others, and the notes matched. A few lower-stakes video notes (the ones not re-viewed) rest on the first read plus the transcript; they are marked "frames + transcript" in the appendix only where I could not double-check them. Nothing in the headline numbers depends on an unchecked frame.

**Known biases.**
- Creators choose what to film. The sample over-represents decorating (several videos exist to show a build) and under-represents shopping, because buying is rarely filmed except by "buy everything" creators.
- Only **one** video is a real child playing alone for a long stretch (V6). A second search round (3.4) added one more child on camera with a parent (C1) and two screen-only videos whose titles give a child's age (C2, C3) that I cannot verify. So "how children spend their time" rests on five sessions, of which one is long and unassisted.
- The game changed a lot from 2018 to 2026. Prices, the shop UI and free content differ by date; every figure below carries its date.
- Frame coding is my judgement. The check above bounds that, it does not remove it.

## 3. The video set

### 3.1 Original 15 (V1-V15)
Listed in `docs/toca-boca-world-findings.md`, section 3. Re-used here for time coding (V1, V4, V5, V6) and for first-run timing (V4).

### 3.2 New 25 (N1-N25)
Metadata is in `docs/data/toca-videos-new25.csv`. Short form:

| ID | Group | What it is | Date | Length |
|---|---|---|---|---|
| N1 | Fresh install | Character-creator tour, no talking | 2019-05 | 5:49 |
| N2 | Fresh install | Silent walkthrough of starter content | 2023-06 | 16:58 |
| N3 | Fresh install + long | Silent first run, creator then two houses | 2026-02 | 61:35 |
| N4 | Fresh install | First-time play, narrated, current build | 2026-09 | 12:39 |
| N5 | Shop | Ranked locations with shop pack cards | 2020-03 | 10:30 |
| N6 | Shop | Mega-pack purchase flow (prices in Thai baht) | 2021-11 | 10:41 |
| N7 | Shop | "Buy every pack" (2023) | 2023-08 | 10:10 |
| N8 | Shop | Ranks Home Designer packs | 2024-11 | 21:01 |
| N9 | Shop | Compilation: pack purchases plus later builds | 2025-12 | 80:03 |
| N10 | Shop | Buys the World Bundle | 2026-04 | 21:55 |
| N11 | Shop | Mall free-rumour check plus mall tour | 2026-06 | 9:05 |
| N12 | Long session | Silent creator + decorating | 2023-04 | 60:14 |
| N13 | Long session | Silent one-hour house build | 2026-06 | 60:01 |
| N14 | Long session | Live stream (Toca ~62 min, then Roblox) | 2026-10 | 77:24 |
| N15 | Children | Family channel, parent-guided, 2020 | 2020-11 | 27:48 |
| N16 | Children | Scripted skit with child actors | 2021-07 | 5:29 |
| N17 | Update | Teaser reaction, "create your own baby" | 2025-11 | 4:11 |
| N18 | Update | Riverside Street Market pack | 2026-04 | 13:33 |
| N19 | Update | Free park and free items preview | 2026-08 | 8:01 |
| N20 | Update | Post Office redesign | 2026-09 | 10:15 |
| N21 | Update | Halloween 2026 event | 2026-10 | 10:12 |
| N22 | Location tour | Old Toca Life apps vs the merged world | 2023-09 | 29:21 |
| N23 | Location tour | Map fly-over, no speech | 2023-05 | 3:50 |
| N24 | Location tour | Ranks 11 districts | 2025-10 | 10:50 |
| N25 | Location tour | Map fly-over with everything built | 2025-01 | 3:04 |

### 3.3 What I could not find
Real children playing and recording themselves are rare in search results. Most "kid" results are role-play story channels made by older children or teens, which are scripted and not what a 4-10-year-old does in a first session. Treat all child-related numbers as thin. A second round is in 3.4.

### 3.4 Second search round: more children playing (2026-10-12)
Request: find more videos with a child playing. I ran 59 YouTube searches (age phrases such as "5 / 6 / 7 / 8 year old", "my son", "my daughter", "kids react", "with my kids", "toddler", under both "Toca Boca World" and the older "Toca Life World"). Most hits are voiced role-play story channels or Roblox creators; the title never says who is playing. I screened 12 candidates by description, contact sheets and a Whisper transcript. Verdicts per video are in `docs/data/toca-child-videos-round2.csv`.

| ID | Date | Min | What the evidence for a child is | Use |
|---|---|---|---|---|
| C1 Caleb Kids Show | 2021-02 | 12.6 | Child and mother visible on a webcam inset; first time playing on a tablet | Time-coded; behaviour notes below |
| C2 "played by a five year old girl" | 2023-02 | 17.9 | Title and description only; no clear speech | Time-coded, age unverified |
| C3 "7 years old plays" | 2022-10 | 5.7 | Title only; no speech | Time-coded, age unverified |
| C4 Kin Tin Plays | 2024-10 | 10.2 | Child on face camera, but an edited, scripted vampire-mansion story | Qualitative only |
| 8 others | 2026 mostly | n/a | No age evidence, under a minute long, or scripted voiced stories | Excluded |

What the added child videos show:
- **C1 (mother-guided, first time, 12.6 min):** 79% play, 10% map, 5% loading. No character creation. The mother and child take turns steering and the mother names roles ("you're the sister"): cooking and serving dinner, shower and tooth brushing, bed, a cinema and a stage band (picking instruments), a hair salon (haircut and colour change). They looked for a dentist, did not find one, and went to the cat place instead. Everything is **family routine and role assignment**, in about 6 locations in 12 minutes.
- **C2 (age unverified, 17.9 min):** a third of the time in the character creator (6 minutes, one character), 39% at the Post Office (a Valentine's-themed one, Feb 2023), little free play. This one looks like a child exploring features rather than telling a story.
- **C3 (age unverified, 5.7 min):** all of it in a single apartment, with no map, creator or shop visit.
- **C4 (scripted):** the player sets a goal for themselves (find paintings to escape) inside a Halloween location. That is a **self-made quest**: the game supplies the place and props; the story is added by the player.

Limits: C2 and C3 ages come from the uploader's title; I could not confirm them. C1 is from 2021 and its parent steers the play. C1-C3 were frame-coded once with a coarse 20-60 s step and were **not** part of the blind re-label test, so treat their shares as rough (one frame is about 5-6% of each video's length). The second round did not find a single new video of a child under about six playing alone.

## 4. Content: what is free, what is paid

### 4.1 Free at the start
| Source | Date | Free locations | Free characters | Notes |
|---|---|---|---|---|
| Common Sense Media (expert review) | Apr 2024 (v1.25.1) | 8 | 39 (+3 custom) | Reviewer's count |
| Children and Media Australia | Jan 2022 | 9 (one town of 8, plus 1) | not listed | Weekly free gift noted |
| Fan wiki figure, via a search snippet | unknown | 11 | 40+ | Unofficial; I could not open the wiki itself |
| Apple store text | Oct 2026 | "apartments, shops and hangouts in Bop City"; Home Designer; Friday gifts | "design your own characters" | No counts given |
| N4 (video, Sept 2026) | 2026-09 | Robo Cafe, Voxella festival, Post Office, own home visited with no purchase | creator plus pre-made townsfolk in view | Observed, not counted |

**Free locations named in videos or sources (changes over time):** Robo Cafe (starter), Morning Meadows bakery, Voxella Festival (free by Oct 2025 per N24), Flipside Park (free drop, Aug 2026, per N19), a Free Fashion Store (promo seen in N3, Feb 2026), the Free Family House (Home Designer, per Apple and V6), and the hospital (N10 says it was made free; see the conflict in 8).

### 4.2 Total content
| Card / source | Date | Scenes (locations) | Characters | Home Designer houses | Furniture & decor | Other |
|---|---|---|---|---|---|---|
| "The Ultimate Bundle" (N7, card icons) | Aug 2023 | 91 | 498 | 8-9 | 1,358 | |
| "World Bundle" (N10, read from frame) | Apr 2026 | 88 | 479 | 39 | 3,700+ | 138 outfits, 504 pieces, 102 packs |
| Video claim (V13, parent review) | Dec 2025 | "100+ places" | "500+" | | | Unsourced |
| Retail listing (Softonic, via snippet) | unknown | ">100" | ">500" | | | Also ">500 pets" |
| Other retail listing (MuMu, via snippet) | unknown | ">50" | ">300" | | | ">125 pets" |

Notes: the two bundle cards are the only first-hand counts. "Scenes" is the game's word for a location (some are multi-room). The World Bundle excludes content a player already owns, so it undercounts the whole. The 2023 to 2026 change in Home Designer houses (8-9 to 39) and furniture (1,358 to 3,700+) shows that the Home Designer catalog grew far faster than the number of locations (91 to 88, which reflects different bundle definitions more than a loss).

### 4.3 Price points (USD unless stated)
| Date | Item | Price | Source |
|---|---|---|---|
| Jan 2022 | Starter pack | $10.99 (40% off) | ACCM |
| Jan 2022 | Mega pack | $74.99 (40% off) | ACCM |
| Jan 2022 | Character creator | $7.99 | ACCM |
| Jan 2022 | Hospital / Mall / University | $5.99 / $4.99 / $4.49 | ACCM |
| Jan 2022 | Super secret pack | $19.99 | ACCM |
| Aug 2023 | Character Creator Upgrade | $4.99 | N7 |
| Aug 2023 | Get Glossy furniture pack | $1.99 (card: 114 furniture and decor items) | N7 |
| Aug 2023 | Big Family Home | $2.99 (card: 2 buildings, 118 furniture, 14 wall designs) | N7 |
| Aug 2023 | Voxella Festival | $2.99 (2 locations, 16 characters, 5 pets) | N7 |
| Aug 2023 | Back to School Bundle | $8.99 (was $9.99; 11 scenes, 81 characters) | N7 |
| Aug 2023 | Foodie Bundle | $5.99 (was $7.99) | N7 |
| Aug 2023 | Home Designer Dream Bundle | $20.99 (was $31.99; 11 houses) | N7 |
| Aug 2023 | The Ultimate Bundle | $49.99 (was $119.99; 91 scenes) | N7 |
| Dec 2025 | Rooftop Garden Apartment | about $2 | N9, spoken |
| Apr 2026 | World Bundle | $84.99 (was $199.99) | N10 |
| Jun 2026 | Mall | about $3, spoken | N11 |
| Oct 2026 | Strange Masquerade Style Pack | $1.99 | Apple listing, N21 |
| Oct 2026 | Activity House; Business Tower | $2.99; $1.99 | Apple listing |
| Oct 2026 | Hospital; Resort Hotel; Stable Grounds | $3.99 each | Apple listing |
| Oct 2026 | Lettuce Lands tiers | $3.99 / $4.99 / $5.99 | Apple listing |
| Oct 2026 | Biscuit Town tiers | $2.99 / $3.99 | Apple listing |
| Oct 2018 | (V9 shop tour, Canadian dollars) | see original doc | V9 |

Reading these together: **single items trended down** (mall $4.99 to about $3; hospital $5.99 to $3.99; character creator $7.99 to $4.99), **bundle cards show a strike-through full price and a lower price**, and the lower price is what that player pays after the value of packs they already own is netted out (the N7 creator says her "$120" bundle fell to $49.99 because she owned some packs; N10's $199.99 fell to $84.99 the same way). That removes the "pay twice" problem for bundles but means a displayed price says little about the full price of the content.

The Apple listing shows only a partial in-app purchase list (11 items), so the 2026 row is a sample, not a catalog.

### 4.4 Character slots
- Free: 3 saved characters. Evidence: V4 first-run roster shows three slots; CSM says 3 custom; one App Store reviewer says only 3 characters without the upgrade.
- Paid ("Character Creator" pack or upgrade): 30 slots. Evidence: N5 (2020) shows 30 slots; N3 shows a wardrobe counter "0/30".
- The earlier doc recorded a 15-slot figure from a different video; I could not reconcile it. Treat 30 as the better supported cap.
- V6 (child) kept three saved characters on the roster tray for the whole 84 minutes and changed their looks several times (including mermaid tails): a 3-slot tier did not stop that play.

## 5. Behaviour: time, variety, onboarding, update cadence

### 5.1 Time breakdown (11 sessions, `docs/data/toca-time-coding.csv`)
Minutes coded per video, and the share of each activity. "Narr." = the player talks, so they may linger or demonstrate.

| Video | Min | Narr. | Play | Build | Creator | Map | Post Office | Shop | Load/title |
|---|---|---|---|---|---|---|---|---|---|
| V1 first-time, Android | 8.5 | yes | 68% | 0 | 9% | 12% | 0 | 0 | 9% |
| V4 first-run, silent | 14.8 | no | 31% | 29% | 5% | 3% | 10% | 0 | 22% |
| V5 role-play 2023, silent | 26.5 | no | 83% | 0 | 0 | 2% | 11% | 0 | 4% |
| V6 child session | 84.0 | yes | 58% | 5% | 20% | 8% | 2% | 0 | 4% |
| N2 starter walkthrough, silent | 17.0 | no | 90% | 0 | 0 | 6% | 0 | 0 | 4% |
| N4 first-time 2026 | 12.8 | yes | 45% | 10% | 27% | 6% | 10% | 0 | 2% |
| N3 first-run 61 min, silent | 61.5 | no | 11% | 55% | 16% | 7% | 7% | 0 | 2% |
| N12 creator+decorate, silent | 60.0 | no | 18% | 63% | 16% | 2% | 0 | 0 | 0 |
| N13 one-hour house build, silent | 60.0 | no | 2% | 98% | 0 | 0 | 0 | 0 | 0 |
| N14 live stream (Toca part) | 62.0 | yes | 0 | 82% | 0 | 5% | 0 | 13% | 0 |
| N15 family channel 2020 (game part) | 23.7 | yes | 99% | 0 | 0 | 1% | 0 | 0 | 0 |

**Pooled (430.7 min):** play 34%, build 44%, creator 10%, map 5%, Post Office 3%, shop 2%, loading 2%, other 1%.
**Average of per-video shares (each video counts equally):** play 46%, build 31%, creator 9%, map 5%, Post Office 4%, loading 4%, shop 1%.
**Silent videos only (6; no commentary effects):** play 25-39%, build 41-56% depending on how you average, creator 6-8%, loading 3-5%.
**Child session V6 only:** play 58%, creator 20%, map 8%, build 5%, loading 4%, Post Office 2%.

What to take from it:
- **Two usage styles, not one.** Players who build (N3, N12, N13, N14) spend more than half of the session in the Home Designer; players who role-play (V5, N2, N15, V6) spend 60-99% in locations. The V6 child fits the role-play style but spends a fifth of the time in the creator, using it mid-story.
- **Shop time is small** (2% pooled), but it is concentrated: it appears only in the one livestream, where the creator used the shop as a **catalog** to find which pack contains an item (about 9 min). That is shop-as-reference, not shop-as-buying.
- **Loading is visible overhead** in the first-run video V4: 22% of its 14.8 minutes are loading vignettes (about one per 80 seconds). Later builds are lighter: 2-4%.
- **Longest unbroken stays:** V6's child stayed 8-12 minutes in one location several times (Krill Grill, waterfront, boat and reef, night waterfront). Role-play videos switch location roughly every 2.5-3 minutes (V5: 9 locations in 26.5 min; N2: 6 in 17 min).

### 5.1a Child-play sessions only (5 sessions, 144 min)
Same coding as 5.1. V6 and N15 are in the table above; C1-C3 come from the second search round (3.4) and are reported here rather than pooled into the 11-session figures.

| Session | Min | Who | Play | Build | Creator | Map | Post Office | Load/other |
|---|---|---|---|---|---|---|---|---|
| V6 | 84.0 | child alone, narrated | 58% | 5% | 20% | 8% | 2% | 6% |
| N15 (2020) | 23.7 | children about 2 and 5 with parents | 99% | 0 | 0 | 1% | 0 | 0 |
| C1 (2021) | 12.7 | child with mother, narrated | 79% | 0 | 0 | 10% | 0 | 11% |
| C2 (2023) | 18.0 | stated age 5, screen only | 11% | 6% | 33% | 6% | 39% | 6% |
| C3 (2022) | 5.7 | stated age 7, screen only | 100% | 0 | 0 | 0 | 0 | 0 |
| **All five** | **144.0** | | **63%** | **3%** | **16%** | **7%** | **6%** | **5%** |

Read this as: children spend most of their time **in locations** (play 63%), very little building (3%, versus 58% in the nine other coded sessions, 323 min), and a notable share in the **character creator** (16%). The spread between sessions is large (play 11% to 100%), so the pooled number mostly reflects the long V6 session. Do not quote 63% as "what a child does"; quote the contrast with building and the creator share.

### 5.2 Variety of things to do
I grouped what players do in locations into **20 activity families**: cooking/serving food, hygiene (toilet, shower, hair wash), rest and TV, shopping/ATM/photo booth, music and stage, sport and rides (skate, ice, pool, water park, amusement), pet care, baby/doctor/hospital care, gardening/farming, fishing/diving/boats, dress-up/salon/spa, school and classroom, crafts (painting, knitting), travel (airport, train), scored mini-games, photography/film recording, hidden secrets and collectibles, home building/decorating, character creation, and gift unboxing. I did not build a per-video presence matrix, so I can say "at least these 20 exist" but not how often each appears.

Counts that are easier to defend:
- **11 named districts** (ranked in N24), plus separate Home Designer districts (for example Pelican Pier), about **88-102 locations** in total per the bundle cards.
- **Individual locations are deep:** the hospital has 5 floors and 30 characters (N5, 2020); the Activity House has 4 floors and 26 characters, with skate, dance, basketball and graffiti areas (N5); the mall has three levels, 16 characters and 18 pets (N11).
- **Mini-games with scores exist** inside some locations: the arcade (whack-a-mole style game with a timer, air hockey with a score, a token machine) in N16; a pool game with a stopwatch in N24. So "no scores anywhere" is too strong; the better statement is "no global score, goal or fail state".
- **Hidden collectibles** exist: a pet card with a found date and a paw counter (N4, 10:45) and a "crumpet collector" feature, said to be released Sept 2026 (N20), with "50-54 secret crumpets" in other search results. Tapping every object to look for secrets is itself a play pattern (N18).
- **Recipes:** food items combine (pizza plus an ingredient gives a labelled pizza) (N18). Placed items have behaviour: the TV changes channels, a robot vacuum moves, bottles drop and scatter (N13).
- **Social in the sense of "other characters", not other players:** 7-20 non-player characters per location is common, with an emoji bar and a mute-mic icon. There is no multiplayer; App Store reviewers ask for it.

### 5.3 Onboarding timings (first-run videos)
| Milestone | V4 (Mar 2026) | N3 (Feb 2026) | N4 (Sept 2026) |
|---|---|---|---|
| Creator starts | 0:20 | 0:00 (modal "make your first character") | 0:15 |
| Creator ends | about 1:00 | about 8:30 (player's choice) | about 3:40 |
| First home build starts | 1:15 (map hint "Swipe to build your first home") | 9:30 (hand-pointer tutorial) | 4:00 |
| First free gift | 3:15 ("Collect your first gift") | 28:30 (visited late, by choice) | 7:00 |
| Tutorial ends | about 8:00, no modal | 21:30 modal "Go explore" | 5:32 (stated aloud) |
| First free location | 5:00 (Robo Cafe) | 21:30 (Robo Cafe) | 5:30 (Robo Cafe) |
| Purchase prompts before 12 minutes | 0 | 0 | 0 |

So a new player reaches a free location and a free gift in **3-7 minutes** when they follow the script. Across the three runs (about 89 minutes) there was **no purchase prompt**, although a cart button is always visible and a "Free Fashion Store / Free furniture" promo card appears on the map (N3, 23:00). In N4 the player also lost their first creator attempt by accidentally closing the app at about 0:48 and had to restart.

### 5.4 Update and free-drop cadence
Dated events seen across the videos and the company site:

| Date | Event | Free or paid |
|---|---|---|
| Every Friday | Post Office gifts | Free |
| 2025-09-23 | Re-release of old favourite gifts (V6) | Free |
| 2025-11-11 | Character Creator update (teased in N17) | Not stated |
| 2025-12 | Five-storey apartment pack (N9) | Paid; creator got a copy free |
| 2026-04-28 | Riverside Street Market (N18): about 1 Home Designer house, 36 furniture, 116 decorations (small card text, approximate) | Paid location; free gifts alongside |
| 2026-08-07, 08-18, 08-26, 10-06 | Four official news posts (company site) | Mixed |
| 2026-08-18 | Flipside Park, a **free** location, plus about 16 free items (N19) | Free |
| 2026-09-01 | Dated teaser for clothes (N19) | Not stated |
| 2026-09-10, 09-17 | Brand gift drops (N20) | Free |
| 2026-10-06 | Halloween event (N21, App Store notes): 10 gifts, 8 free decor items, new free hair, skin tones, eyes and more, plus one paid $1.99 style pack | Mostly free |

That is a new dated drop **about every 1-2 weeks**, with the large majority of Halloween 2026 content free. The Post Office was redesigned in Sept 2026 into a digital "Lost & Found" with filters by type and by year (2018 to 2026), and a recovery feature for trashed gifts (N20). Pre-release teasers use dated silhouettes ("August 18 - ?") and the community speculates for days.

## 6. Evidence B: reviews

### 6.1 Review pages read (14), with quality
"Independent" means no stake in selling the app or a parental-control product.

| # | Source | Date | Type | What it adds | Quality |
|---|---|---|---|---|---|
| R1 | Common Sense Media, expert review | Apr 2024 (v1.25.1) | Independent | 8 free locations, 39 free characters, 3 custom; purchases $0.99-$13.99; shop cart "shown prominently"; settings can switch shopping off; ratings "some" for purchases and educational value, "a lot" for ease of play | High |
| R2 | Common Sense Media, parent reviews | current | Independent (user text hidden by the fetch) | 31 parent reviews: glitches, lost purchases, high spend; praise for open-ended play and no ads | Medium (summary only) |
| R3 | Common Sense Media, kid reviews | current | Independent (summary) | 59 kid reviews: fun and creative; complaints about purchases and glitches | Medium |
| R4 | Children and Media Australia (ACCM) | Jan 2022 | Independent | 9 free buildings, weekly gift, price list (4.3), age 9+ with co-play, sales tactics (strike-through prices, "New items available!"), advertising ID sent to a third party in 2021 test, birth-year gate easy to bypass | High |
| R5 | Bark | 2022, updated 2023 | Parental-control vendor | 5/5, 5+; many things doable without buying; no chat; no built-in parental controls | Medium (vendor) |
| R6 | Screenwise, Toca Boca World | undated, 2026 footer | Parental-app vendor | Free version "a taste"; $20-50 over time; "constant can we buy" requests; ages 6-12 | Medium (vendor, opinion) |
| R7 | Screenwise, Toca Life World page | undated | Same | Parent spend "$0 to $100+", 60M kids claim, no loot boxes or timers | Medium |
| R8 | Screenwise, apps-ranked guide | undated, "updated 3 days ago" | Same | Claims "$8/month to unlock everything" and "$1-4 per location" | **Low** (conflicts with the store listing; see 8) |
| R9 | Bitdefender HOTforSecurity | Jul 2025, updated Apr 2026 | Security vendor | No chat; ages 4+ or 6-12; risks: purchases, YouTube exposure, analytics data, no stopping point | Medium (vendor) |
| R10 | Pixalate | Nov 2022 | Compliance firm | Classed "child directed"; Google "Teacher Approved"; no SDK findings stated | Medium (thin) |
| R11 | Family Gaming Database | about 2020, updated 2024-25 | Community | ESRB Everyone; notes crude humour and medical themes; "5 to 30 minute rounds" | Medium |
| R12 | FlashGet Kids blog | 2025-03 | Vendor marketing | Starter town free; inconsistent location counts (50 vs 90+); ages 4+ | Low |
| R13 | Vocal (account "apkclub") | about 2025 | SEO, links to a third-party download site | Price range "$0.99 to over $50"; 6-12; unsourced claims | Low |
| R14 | JustUseApp, aggregate of 39 App Store reviews | 2021-2025 | Aggregator | Themes below | Medium |

Read and **rejected**: two pages (marcnorgaard.com, reviewergame.com) turned out to describe other Toca apps (Toca Train, Toca Kitchen Sushi), claim no in-app purchases, and show no first-hand play; I did not use their facts. Several search hits were not fetched (for example a mod-download site) and are not counted.

### 6.2 What the reviews say, in numbers
- **Age guidance conflicts.** 4+ (App Store, CSM expert); 5+ (Bark, CSM kids); 6-12 (developer per ACCM, Bitdefender, Screenwise, Vocal); 9+ with co-play up to 15 (ACCM); "2+" skill level (Family Gaming Database). The store page also says "Made for Ages 6-8".
- **Spend.** Common range of $0.99-$13.99 per item; parent-reported total from "$0" to "$100+" (Screenwise, unsourced); one creator spent about $200 for everything (video N7).
- **Chat and ads.** Every source says no chat. Most say no third-party ads. ACCM saw store promotion inside the game and, in 2021, an advertising identifier sent to an ad company.
- **Safety framing.** Reviews treat the game as safe; the recurring concern is money, plus "no natural stopping point" (R6, R9).

### 6.3 App Store sample (500 reviews, 2026-10-08 to 2026-10-10, US)
Collected from Apple's public review feed (the most recent 500; the current version was 1.140). The store shows **4.29 average from 894,683 ratings** overall; this sample's mean is **4.34**.

| Stars | Reviews | Share |
|---|---|---|
| 5 | 323 | 64.6% |
| 4 | 98 | 19.6% |
| 3 | 36 | 7.2% |
| 2 | 14 | 2.8% |
| 1 | 29 | 5.8% |

**Timing bias:** the sample covers only three days right after the Halloween update, so it over-represents update bugs (Post Office crashes, a stuck school area) and the reaction to a map change.

**Coding.** I read the opening text (roughly 350 characters) of all 79 reviews rated 1-3 stars and of a random 70 of the 421 rated 4-5, then ran keyword rules over all 500. The keyword counts are approximate: when I checked 15 random matches per rule, about **60% were real** for the price rule and for the lost-progress rule, and about **85%** for the bug rule. Read them as upper bounds.

| Theme (keyword match over all 500) | Count | Share | Mean stars |
|---|---|---|---|
| Price / "more free" / paywall | 103 | 21% | 4.3 |
| Bugs, crashes, "kicked out", lag | 95 | 19% | 3.9 |
| Lost progress, purchases or gifts; restore failures | 63 | 13% | 3.5 |
| Asks for new content, collaborations, events | 83 | 17% | 4.5 |
| Praises creative play / build / role-play | 93 | 19% | 4.6 |
| Praises free gifts or free updates | 45 | 9% | 4.2 |
| Praises no ads / safe | 29 | 6% | 4.9 |
| Mentions playing for years, nostalgia | 35 | 7% | 4.5 |
| Asks for playing with friends / multiplayer | 25 | 5% | 4.6 |
| Bored or nothing to do | 18 | 4% | 4.2 |
| Mentions weather, day/night or seasons | 9 | 2% | 4.7 |

My manual reading of the 79 low-rated reviews (a review can carry more than one theme; counts are approximate): **about 23 bugs or crashes, about 17 lost progress or purchases, about 16 price or paywall, about 4 multiplayer requests, about 6 dislike of the update, 3 "inappropriate" (mostly Halloween), 1 boredom after years.**

Findings worth acting on:
- **Lost progress is the angriest theme** (mean 3.5 stars, the lowest). Typical: a crash or an "offload and reinstall" erases worlds, gifts or characters; "restore purchases" does not bring back a purchased pack; a new device starts empty. The N14 streamer's world reset after a crash and the N9 creator's new iPad lost all gifts, which matches. The Sept 2026 Post Office "recovery" feature (N20) looks like a response.
- **Visible-but-locked content is now a complaint.** Three low-rated reviews say that since the latest update, everything not purchased shows greyed out on the map, which they find ugly and "money-hungry". One 10-year-old says they cannot buy because they have no card. I could not confirm the greyed-out map in video; this is a review claim.
- **"Paid then free" still stings.** One review says "I paid for the hospital and now it's free", asking for a refund (consistent with V12 and N10).
- **Players want other people:** playing with friends is the most common feature request in the 4-5 star group (the keyword count understates it; I counted about ten such comments in the text I read).
- **Hardly anyone mentions weather or time of day** (2%), which fits Toca's manual weather/time panel and means that feature is not a driver of reviews. One long-time fan asks for control over day/night and weather.
- **Long-term fatigue appears but is rare** (about 4%). One reviewer who played for 3-4 years says it became boring and moved to another game.

## 7. Evidence C: other sources (assessed separately)

| Source | What it gives | Reliability |
|---|---|---|
| **Apple App Store record (official, API)** | Name "Toca Boca World: Game & Play"; first released **2018-11-21**; current version 1.140 (2026-10-05); free with in-app purchases; 4+ (page also shows "Made for Ages 6-8"); 1.02 GB; 21 languages; 894,683 ratings, 4.29 average; categories Education and Entertainment; no subscription shown. Release notes: 10 Halloween gifts, 8 free decor items, free creator items. | High for these fields |
| **Apple privacy label (developer-declared)** | "Data linked to you": coarse location. "Not linked": identifiers (user ID, device ID) used for developer's advertising or marketing, analytics and app functionality; purchase history; product interaction; diagnostics. | Medium (self-reported, not verified by Apple) |
| **Company site (tocaboca.com)** | Four dated news items 2026-08-07 to 10-06; a free location and free Home Designer items called out; adult/kid gate; Privo certification badge | High for what it shows; it states no counts or prices |
| **Spin Master press release (2025-10-06)** | "Close to 60 million monthly users" of Toca Boca World; 1.1 billion downloads across all Toca games | Medium-high (company claim) |
| **Wikipedia** | Toca Life apps merged into one app announced 2018-11-21; standalone apps removed from stores in Jan 2024; awards (Parents' Choice 2018-19, Webby 2020, App Store iPhone App of the Year 2021, Kidscreen 2022 and 2025); owned by Spin Master | Medium |
| **Rename date** | A community wiki post dates the switch from "Toca Life World" to "Toca Boca World" to May 2024; no official announcement found | Low |
| **Market estimates** | Sensor Tower page snapshots: iOS US about $5M and 1M downloads in a recent month; Google Play US about $2M and 4M. Another estimate site: $8.0M a month in Jul 2026. Company: 1.7B SEK revenue in 2023 for the whole studio. | Low (the sources disagree and the snapshot months are unclear) |
| **Fan wiki (Fandom)** | Could not open (payment-required error). Search snippets only. | Unusable here |
| **Official in-game "Grown-ups" and shop settings** | Not accessible; known only through reviews (shopping can be switched off in device settings; a birth-year gate precedes purchases) | n/a |

Compliance relevance for your game (not legal advice): this game's own listing declares **coarse location** and **device identifiers used for advertising or marketing** in an app rated 4+ and "Made for Ages 6-8". If you target ages 4+ in the Kids category, the earlier research (`docs/concept-state.md`, Apple 1.3/5.1.4 and COPPA notes) says to avoid exactly these. The ACCM test in 2021 found an advertising identifier sent to an ad company, so this is not new.

## 8. Where the evidence agrees and where it conflicts

| Topic | Agreement | Conflict or gap |
|---|---|---|
| Free start content | 8-11 locations, 39-40 characters (4 sources) | Counts changed over time; Flipside Park, Voxella, Robo Cafe, hospital and others were added free later |
| Price per item | $0.99-$13.99 (CSM, store list partial) | Bundle prices depend on what you already own |
| Total content | 88-91 scenes, 480-500 characters (two cards; two spoken claims) | Retail listings say ">50" or ">100" locations |
| Hospital | N10 (Apr 2026) and V12 say it became free; V10/V14 corroborate it was once paid | The Oct 2026 App Store list still shows "Hospital $3.99"; not resolved (could be a stale store entry or a legacy product) |
| Subscription | App Store shows none; one vendor guide (R8) says "$8/month unlock everything" | Likely confused with the separate Toca Boca Jr subscription; treat as wrong until seen in-app |
| Mall free? | N11 checked in June 2026: official channels did not confirm; commenters disagreed | Unresolved; the N10 spoken line "Wasn't the mall free?" is also inconclusive |
| Ads | Reviews: none in game; promotion of the store and of other Toca apps inside the game (R1, R4) | Declared "advertising or marketing" identifier use on the store label |
| Age | 4+ rating | 4+ to 6-12 recommendations; ACCM says not under 4 |
| Restore/lost purchases | V12, R2, many App Store reviews say purchases can fail to restore | Other reviews say restore works across devices; N9 shows purchases returned but world and gifts did not |
| Weather/time | Manual control in V3; a sun icon in every map frame | N23 appears to show the same location in day and in dark rain tint; consistent with a manual change but not proven |

## 9. What this means for the unicorn game (inferences, not findings)

These are **targets to test**, derived from the numbers above.

1. **Free island size.** Toca's free start is about 8-11 locations out of about 90-100 (roughly 10%), and that is enough for a new player to reach a free gift and a free location within 3-7 minutes. Your first island can be much smaller if each location is deep (Toca's hospital has 5 floors and 30 characters). Set a floor of "enough for the first week", not a percentage.
2. **Cap the right thing.** Toca caps **saved characters at 3** on the free tier, not play. V6 shows a child doing a lot with three characters. For your game the equivalent is how many creatures a child can keep; a small cap that is easy to understand fits a 4-year-old and is a clear, non-manipulative upgrade. Check this against your "first island free and complete" promise, since a cap on creatures may feel like a missing feature.
3. **Plan for two play styles.** In 11 sessions, building took 31-44% of time and role-play 34-46%, with very different individual mixes. Your Builder mode and your pet-care loop should each be able to carry a session on their own. A session of 5-20 minutes (the reviews' "5 to 30 minute rounds") is a better design target than the 60-minute creator videos.
4. **Make the creator the keystone.** It is 9-10% of pooled time but 20% of V6's session (16% across the five child sessions), it is revisited in the middle of stories, and it is the first thing a new player does. In your game that is the creature creator and, later, breeding preview.
5. **Do not hide loading in the first minutes.** V4 spent 22% of its first 15 minutes in loading vignettes. Toca fills those with mascot animations; if you load between islands, budget for that.
6. **Treat lost progress as the top risk.** It is the lowest-rated recurring theme in the review sample and the most emotional ("everything reset"). Design saves, recovery and restore first; consider a "found things" shelf like Toca's new Lost & Found. This also supports your plan for purchases restored across devices.
7. **No visible locks in the main world.** The new greyed-out map draws anger; and mixing free and paid items in one location confuses (earlier doc). Show only what the child owns, and put anything for sale in a separate parent-gated place, outside the creative flow.
8. **A Friday-style free ritual is worth more than a free percentage.** Weekly free gifts are the most-praised monetization feature in reviews and appear in 9% of reviews as praise, while the "make more free" complaint appears in about 21%. Keep a recurring free drop, and keep old drops retrievable (Toca now filters 2018-2026 gifts by year).
9. **Differentiators are still untested here.** Toca shows no needs, moods, breeding, storybook or goals, so nothing in this data supports or refutes them. The 2% weather/time mention rate suggests weather alone will not drive reviews; a reactive world should pay off through what creatures do, not the sky.
10. **Do not copy the data practice.** The store label lists identifiers for advertising or marketing and coarse location. For ages 4+ in the Kids category, plan for none of that.

## 10. What is still unknown

- True **time on each activity for young children**: five child-play sessions exist, only one of them long and unassisted (V6), and none is verified as a child aged 4-6 playing alone. Finding that needs a recorded playtest of your own, not more YouTube.
- **Retention, session counts per day, conversion and spend per payer** are not observable from videos or reviews. The market estimates are inconsistent.
- The **exact free-content counts today**: no official figure; the closest are 2024 and 2022 reviews.
- Whether the **hospital and the mall are free now** (conflicting evidence).
- What the **sparkle** HUD button does (a red-dot button next to the cart). N3 shows a news panel opening after it, so a news/events button is likely but not proven.
- The Fandom wiki and any official catalog: not reachable here.
- Avatar World: done separately, see `docs/avatar-world-findings.md`; the cross-game summary is `docs/reference-games-comparison.md`.

## Appendix A: per-video notes (new videos)

Time-coded videos are in section 5.1. Short notes on the rest:

| ID | Note |
|---|---|
| N1 | Creator only (35 of 35 frames). Around 13 tabs: body, skin, hair style and colour, face, eyes, nose, brows, mouth, clothes, hats, glasses. A roster strip with dashed empty slots. 2019 UI. |
| N5 | 2020 shop-card counts: Resort Hotel 4 areas/11 characters; Interior Design Store 1/6; Haunted House 2 floors/9; Ice Skating Village 2/9; Activity House 4 floors/26; Apartment Building 4 flats/12; Waterfront 3/24; Amusement Park 3/18; Hospital 5 areas/30; Character Creator 30 slots. |
| N6 | Purchase flow: shop drawer under the map, pack page with trailer, year-of-birth gate on a number pad, "Please wait", "You're all set", Build; buildings appear on the map with a scaffold-and-dust animation. Prices in Thai baht (Mystery Pack 479, Ultimate Makeover 399, location packs 99). Frames + transcript (transcript unusable). |
| N7 | Shop UI (Aug 2023): tabs Map, Design & Build, Furniture Packs, Character Creator, Fan Faves; shelves "This just in!", "Bundles", themed shelves; "Owned" ticks. Price list in 4.3. |
| N8 | Spoken ranking of about 35 Home Designer and furniture packs by tier; helpful for pack content descriptions, not for prices. |
| N9 | 80-minute compilation. The first 10 minutes repeat N7. Later segments: a Midtown five-storey apartment pack, a supermarket stocked with about 100 grocery items. |
| N10 | World Bundle card: $84.99 (was $199.99); buying places 88 scenes on the map by itself. |
| N11 | Mall: three levels, 16 characters, 18 pets. The mall-free rumour check ends unresolved. |
| N15 | Family channel, children about 2 and 5 with parents co-playing (webcam inset); about 8 distinct locations in 23.7 minutes of game footage. |
| N16 | Scripted skit; game footage shows the arcade (scores, timer, tokens). Excluded from time shares. |
| N17-N21 | Update coverage; see 5.4. |
| N22 | Compares more than a dozen old Toca Life apps (house, school, pet shop, vacation, hospital, farm, stable, camp, skate park, robot diner) with their redesigned versions; evidence for where the content came from. |
| N23, N25 | Map fly-overs with about 12 biomes (city, harbour, resort, canyon, farmland, autumn forest, snow village, suburbs). Buildings appear in three stages: empty slab, scaffold with dust, finished. |
| N24 | District ranking: 11 districts (Creators Campus, Morning Meadows, Biscuit Town, Tip Top Tops, Bop City, Lettuce Lands, OK Street, Omelet Islands, Pom-Pom Peaks, Vox Valley, Busy Plaza). |

## Appendix B: files
- `docs/data/toca-videos-new25.csv`: IDs, channels, dates, lengths, groups.
- `docs/data/toca-time-coding.csv`: frame counts and minutes per activity for the 11 time-coded sessions plus the three added child sessions (C1-C3).
- `docs/data/toca-child-videos-round2.csv`: the 12 candidate child-play videos from the second search, with the evidence and the verdict for each.
