# docs/

## Running the presentations

Both decks in `docs/presentation/` are self-contained HTML files — no build step, no
dependencies, no server required.

### Open directly

```bash
open docs/presentation/partner-pitch.html      # partner / co-founder deck
open docs/presentation/index.html              # customer deck
```

(`open` is macOS; on Linux use `xdg-open`, on Windows just double-click the file.)

### Or serve it (needed if a browser blocks local file access for any reason)

```bash
cd docs/presentation
python3 -m http.server 8080
# then visit http://localhost:8080/partner-pitch.html
```

### Navigation

| Deck | Controls |
|---|---|
| `partner-pitch.html` | `→` / click / dots at the bottom to advance, `←` to go back |
| `index.html` | `→` `↓` or space to advance, `←` `↑` to go back, swipe on touch devices |

## What's in this folder

| File | What it is |
|---|---|
| `presentation/partner-pitch.html` | Deck for a technical co-founder conversation — the idea, the market, and an honest read of where the build actually stands. |
| `presentation/index.html` | Customer-facing sales deck — problem, product, pricing, roadmap. |
| `a2a-notes.md` | Notes on the A2A protocol spec (Agent Card, JSON-RPC methods, task lifecycle). |
| `system-overview.excalidraw` | System architecture sketch — open at [excalidraw.com](https://excalidraw.com) (File → Open). |
