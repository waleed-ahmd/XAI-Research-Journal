# Short paper (XAI Assignment 03)

```
main.tex        preamble from IEEE's conference template, title/authors, \input of each section
IEEEtran.cls    IEEE's class file (v1.8b) from the official template zip; don't edit
IEEEtran.bst    IEEE's reference style (v1.12) from the official "LaTeX Bibliography Files" zip; don't edit
sections/       one file per section; the comment at the top says what it's for
figures/        charts exported from harness/results (PDF preferred)
refs.bib        shared bibliography; cite with \cite{key}
```

## Note for LaTeX?

- `.tex` = the content.
- `.cls` = the styling for  whole paper: layout, fonts, headings.
- `.bst` = the styling for the reference list.
- `.bib` = our list of sources, stored as data. Add a source here once, cite it
  with `\cite{key}`, and the `.bst` turns it into a numbered IEEE reference.

**only ever edit `.tex` and `.bib` files.**

## Getting the PDF

You don't need LaTeX installed. Every push/PR that touches `shortpaper/`
runs the **Build short paper** workflow: open the run in  Actions tab and
download the `short-paper` artifact. Each push to `main` also updates the
[`latest-draft` release](https://github.com/waleed-ahmd/XAI-Research-Journal/releases/tag/latest-draft).

You can build it locally but The LaTeX Workshop extension for VS Code gives
a live preview aswell.

## Note
- Don't change margins, font sizes or spacing to fit the page limit. Cut
  words instead.

## Proposed section owners (not yet agreed)

| Section | File | Owner | Words |
|---|---|---|---|
| Abstract | `abstract.tex` | everyone, written last | ~180 |
| Introduction | `introduction.tex` | TJ | ~400 |
| Background / Related Work | `background.tex` | Peter | ~550 |
| Methodology | `methodology.tex` | Luca | ~600 |
| Results / Analysis | `results.tex` | Waleed | ~700 + 1–2 figures |
| Discussion and Limitations | `discussion.tex` | everyone, one editor | shared ~400 total with Conclusion |
| Conclusion | `conclusion.tex` | everyone, one editor | shared budget |

