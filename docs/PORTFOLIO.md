# Pokémon portfolio: handoff notes

Three connected Pokémon projects that together show data, web and mobile work. Start here when
picking up the work in a new session or on another computer.

> "I built a data pipeline that analyses the competitive Pokémon meta, a web app that uses that data
> to coach team building, and an iOS app that optimises collection spending."

## Status (7 November 2026)

| # | Project | Status | Live | Code |
| --- | --- | --- | --- | --- |
| 1 | Python: Competitive Meta Tracker | Done, updates itself monthly | [Dashboard](https://pokemon-meta-tracker-lvxim6hx4xmcluqcqqmvst.streamlit.app) | [repo](https://github.com/Eb-8734843/pokemon-meta-tracker) |
| 2 | JavaScript: Team Builder | Done | [Website](https://pokemon-team-builder-lemon.vercel.app) | [repo](https://github.com/Eb-8734843/pokemon-team-builder) |
| 3 | SwiftUI: TCG Collection Tracker | **In progress** on the MacBook (week 1 done) | | [repo](https://github.com/Eb-8734843/pokemon-tcg-tracker) |

Open work for projects 1 and 2 is in each repo's GitHub Issues. Each repo also has a `CLAUDE.md` with
its commands and conventions.

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

- **Cheapest path to completion**: "12 more cards for this set, about £34 total; here are the cheapest."
- **Budget mode**: set a monthly spend and it suggests what to buy next.
- **Price history and alerts** when a wanted card drops in price.
- **Home screen widget** showing set progress or collection value.
- **Offline-first**, so it works without signal at card shops.

**Stack.** Xcode on a Mac, SwiftUI and SwiftData, the Pokémon TCG API (pokemontcg.io; register for a key
and check its current status and rate limits before building on it), WidgetKit, an iPhone or the simulator.
TestFlight is optional and needs a paid Apple Developer account.

**Plan** (about 4 to 5 weeks, 1 to 2 hours on weekdays plus a longer weekend session):

| Week | Tasks |
| --- | --- |
| 1 | Set up the project. Fetch sets from the API and list them with logos. |
| 2 | Set detail screen with a card grid. Tap a card to mark it owned, saved with SwiftData. |
| 3 | Progress bars per set. Search and filters (rarity, type). |
| 4 | Prices and total collection value. "Cheapest cards remaining" for set completion. |
| 5 | Widget and app icon. Polish, and screen recordings for the README. |

Stretch: camera card recognition with Vision, and price alerts.

Skills shown: SwiftUI, networking, local persistence, widgets, iOS app architecture.

### Getting started on the MacBook

1. Install **Xcode** from the Mac App Store (SwiftUI comes with it), open it once and let it install
   its components.
2. Register for an API key at pokemontcg.io.
3. Install Claude Code, make a new folder (for example `~/Pokemon Projects/pokemon-tcg-tracker`) and open
   it there. Point Claude at this file so it has the context:
   `https://github.com/Eb-8734843/pokemon-meta-tracker/blob/main/docs/PORTFOLIO.md`
4. Keep the API key out of git (for example in an `.xcconfig` file listed in `.gitignore`).
5. Create the GitHub repo once the project is set up, and add the live links and screen recordings to
   the README when it's done, as with the other two.

## Ways of working that have suited these projects

- One project at a time: finish the MVP, then add stretch features.
- GitHub Issues as the task list, closed by commits (`Closes #n`).
- Explain each setup step in plain language and one command at a time.
- Findings only claim what the data shows. Causes come from confirmed sources (for tiering events,
  Smogon's tiering history) and correlation is labelled as timing, not proof.
- Check changes on the live site after deploying, not just locally.
- Commits are made as Ebube-Chukwu Ekwe with the GitHub noreply address.
