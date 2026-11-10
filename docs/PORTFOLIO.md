# Pokémon portfolio: handoff notes

Three connected Pokémon projects that together show data, web and mobile work. Start here when
picking up the work in a new session or on another computer.

> "I built a data pipeline that analyses the competitive Pokémon meta, a web app that uses that data
> to coach team building, and an iOS app that optimises collection spending."

## Status (10 November 2026)

| # | Project | Status | Live | Code |
| --- | --- | --- | --- | --- |
| 1 | Python: Competitive Meta Tracker | Done, updates itself monthly | [Dashboard](https://pokemon-meta-tracker-lvxim6hx4xmcluqcqqmvst.streamlit.app) | [repo](https://github.com/Eb-8734843/pokemon-meta-tracker) |
| 2 | JavaScript: Team Builder | Done | [Website](https://pokemon-team-builder-lemon.vercel.app) | [repo](https://github.com/Eb-8734843/pokemon-team-builder) |
| 3 | SwiftUI: TCG Collection Tracker | Done (all 5 weeks); screen recordings still to add | Runs in the simulator | [repo](https://github.com/Eb-8734843/pokemon-tcg-tracker) |

Open work for projects 1 and 2 is in each repo's GitHub Issues. Each repo also has a `CLAUDE.md` with
its commands and conventions. Project 3's next steps are listed in its section below.

### How 1 and 2 connect

```
Smogon stats ─▶ Meta Tracker ─▶ GitHub Action (3rd of each month) ─▶ exports/meta-*.json
                     │                                                      │
              Streamlit dashboard                                  Team Builder loads it live
```

The Action fetches the new month, regenerates reports, charts and exports, and commits them. Streamlit
redeploys from the commit, and the Team Builder reads the JSON from the repo, so nothing needs doing by
hand. Confirmed working on 3 November 2026, when it loaded October 2026 by itself.

## Project 3: SwiftUI TCG Collection Tracker

An iPhone app for logging Pokémon cards that helps you complete sets as cheaply as possible.

**What makes it different.** Existing collection apps mostly log cards and show value. This one focuses
on completing goals smartly:

- **Cheapest path to completion** (built): the missing cards cheapest first, with a running total and what
  the cheapest 10, 25, 50 and 100 cost.
- **Home screen widget** (built): collection value and the sets closest to complete.
- **Offline-first** (built): set lists, card lists and prices are saved on the phone.
- **Budget mode** (not built yet): set a monthly spend and it suggests what to buy next.
- **Price history and alerts** (not built yet) when a wanted card drops in price.

**Stack.** Xcode on a Mac, SwiftUI and SwiftData, WidgetKit, and [TCGdex](https://tcgdex.dev) for card data,
images and daily Cardmarket prices (free, no API key). Prices are converted to pounds with the ECB rate
from [Frankfurter](https://frankfurter.dev). TestFlight is optional and needs a paid Apple Developer
account.

**Why TCGdex and not pokemontcg.io.** The app started on pokemontcg.io, as first planned. In November 2026
that API failed 6 to 8 requests in 10 and no longer included prices, so the app moved to TCGdex, which
answered every test request. A one-time migration moved owned cards to TCGdex's card numbers.

**Plan** (about 4 to 5 weeks, 1 to 2 hours on weekdays plus a longer weekend session):

| Week | Tasks | Status |
| --- | --- | --- |
| 1 | Set up the project. Fetch sets from the API and list them with logos. | Done |
| 2 | Set detail screen with a card grid. Tap a card to mark it owned, saved with SwiftData. | Done, plus Undo for accidental taps |
| 3 | Progress bars per set. Search and filters (rarity, type). | Done, plus an owned/missing filter |
| 4 | Prices and total collection value. "Cheapest cards remaining" for set completion. | Done, after the move to TCGdex |
| 5 | Widget and app icon. Polish, and screen recordings for the README. | Done except the screen recordings |

Stretch: camera card recognition with Vision, and price alerts.

Skills shown: SwiftUI, networking, local persistence, widgets, iOS app architecture.

### Next steps

1. Record the app in the Simulator (**File → Record Screen**) and add the videos to the README by dragging
   them into GitHub's editor, so they play on the page.
2. Stretch features: budget mode, price history and alerts, then camera card recognition with Vision.
3. To run on a real iPhone, set your Apple developer team for both the app and the CollectionWidget
   target, and use an App Group ID your account owns.

### Picking it up on the MacBook

1. Clone the [repo](https://github.com/Eb-8734843/pokemon-tcg-tracker) and open
   `PokemonTCGTracker.xcodeproj` in Xcode 26 or later. No API key is needed.
2. Choose an iPhone simulator and press **Run**. The README covers the widget, the tests and the layout.
3. Point Claude at this file and the app's README so it has the context.

## Ways of working that have suited these projects

- One project at a time: finish the MVP, then add stretch features.
- GitHub Issues as the task list, closed by commits (`Closes #n`).
- Explain each setup step in plain language and one command at a time.
- Findings only claim what the data shows. Causes come from confirmed sources (for tiering events,
  Smogon's tiering history) and correlation is labelled as timing, not proof.
- Check changes on the live site after deploying, not just locally.
- Commits are made as Ebube-Chukwu Ekwe with the GitHub noreply address.
