<img src="assets/logo.svg" alt="" width="96" height="96">

# pipeline-board

**See, understand and speed up your pipeline.** A plugin for **Claude Code** that turns your real runs into an interactive board and publishes it to **your own artifact**.

![Works with Claude Code](https://img.shields.io/badge/works%20with-Claude%20Code-d97757)

![Demo: dragging cards, opening a step, searching, replaying a run until it fails, checking limits and the report](docs/demo.gif)

[MP4 video](docs/demo.mp4) · The pipeline in the demo is **made up**. The board labels and video captions are in Portuguese.

## Works with Claude Code

Installing from this repository was checked with **Claude Code 2.1.332** on macOS: the marketplace was added, the plugin installed and all 4 skills were listed. The guided flows inside each skill have not been run end to end in a fresh session yet.

## Install

Inside Claude Code:

```
/plugin marketplace add molholabs/pipeline-board
/plugin install pipeline-board@pipeline-board
```

This repository is private, so you need access to it on GitHub. To try a local copy for one session: `claude --plugin-dir <folder>`.

Requirements: Python 3.9+ and, to read your runs, an authenticated [`gh`](https://cli.github.com/) CLI. Publishing to an artifact needs a Claude account where artifacts are available. The scripts also work without it and produce a local HTML file.

## Use

Open Claude Code in your repository and ask:

> draw my pipeline

The skill instructions are written in Portuguese. They tell Claude to answer in your language.

| Skill | Ask when | What it does |
|---|---|---|
| `/pipeline-board:map` | "draw my pipeline" | Reads GitHub Actions runs, groups them into cards, scans for secrets and publishes to your artifact |
| `/pipeline-board:explain` | "what does this step do?" | Reads your code and fills in the flow, measurements, **real examples**, latest records and models used |
| `/pipeline-board:speedup` | "this is slow" or "this broke" | Finds the actual bottleneck, parallelizes in code and **measures before and after** |
| `/pipeline-board:limits` | "how close are we to a limit?" | CI minutes, job timeout, cache and files per deploy |

## What the board does

![Board overview](docs/quadro.png)

- **Infinite canvas.** Drag to pan, pinch or ⌘/Ctrl + scroll to zoom, move cards and resize them: steps reflow and arrows redraw. One button restores the auto layout.
- **Inside each step.** Flow with loops, parallelism and decisions; measurements; a real example; latest records; where it writes.
- **Replay.** A run plays back in seconds, with a clock, and stops where it broke.
- **Search** (`/` or ⌘K) across names, files, flows and examples.
- **Copy context.** One click copies a step as text, ready to paste into Claude and ask for a fix.
- **Ask.** Inside an artifact, a question builds an answer out of blocks. The model picks the blocks and may write short sentences, labeled as model-written. Charts and lists come from the board data.
- **Limits** with a warning from 80%. Missing data shows as not measured, never as zero.

![An open step](docs/etapa.png)

![Limits panel](docs/limites.png)

## Without Claude

```bash
python3 scripts/collect.py owner/repo -o spec.json     # first draft from your runs
python3 scripts/limits.py owner/repo --spec spec.json  # limits
python3 scripts/check.py spec.json                     # look for secrets before publishing
python3 scripts/build.py spec.json -o board.html       # a single HTML file, opens in a browser
```

The spec format is described in [references/spec.md](references/spec.md) (in Portuguese), with an example in [examples/demo.spec.json](examples/demo.spec.json).

## Before you share

- The board shows workflow names, file names, failures and records. **Artifacts start private; read the board before sharing it.** `check.py` looks for keys, tokens, vault references, e-mail addresses and home folder paths. It is not an audit: names of people and customers get through.
- Text coming from logs is inserted as text, never as HTML.
- Natural language questions use the Claude account of whoever asks, and model-written text can be wrong.

## Limitations in this version

- Automatic collection covers **GitHub Actions only**, using the latest run of each workflow. For other orchestrators the spec has to be written by hand.
- The automatic draft has steps, durations and results. **Flows and real examples come from the `explain` skill**, which reads your code.
- The board is a snapshot. It does not update live.
- Tested in desktop Chrome. Phones and other browsers have not been tested.

## Development

```bash
python3 -m unittest discover -s tests
claude plugin validate .
python3 scripts/build.py examples/demo.spec.json -o docs/demo.html
node scripts/record.mjs docs/demo.html docs   # re-records the video; needs Chrome and ffmpeg
```

`record.mjs` drives the board with real mouse and keyboard events and **fails if an interaction stops working**.

## Credits

Design ideas learned from [diagram-design](https://github.com/cathrynlavery/diagram-design) (density limits, look before delivering), [stack-diagram](https://github.com/caru-ini/stack-diagram) (grid, light tiles, right-angle arrows) and [lanshu-animated-architecture-diagram](https://github.com/cclank/lanshu-animated-architecture-diagram) (animated flow). The code in this plugin is original. Icons: [Lucide](https://lucide.dev), ISC license.
