# Essays

A plain essay site. Each essay is a text file; one script turns them into web pages.

## Write an essay

Make a new file in `essays/`, like `essays/why-i-write.md`. The file name becomes the address (`why-i-write.html`).

```
title: Why I Write
date: 2026-11

First paragraph...
```

Add `draft: yes` under the date to keep it off the site while you work on it.
`essays/how-this-site-works.md` shows all the formatting; delete it when you're done with it.
Images go in `files/` and are referenced as `![description](files/photo.jpg)`.

## Preview

```
python build.py serve
```

Then open http://localhost:8000. Edit an essay and refresh to see the change.

## Publish

The site lives at https://aariv-modi.github.io. Commit and push, and GitHub rebuilds and publishes it within a minute or two:

```
git add -A
git commit -m "New essay"
git push
```

`python build.py` builds the same site locally into `site/`, if you ever want to host it elsewhere.

## Settings

Your name, site address and an optional intro line are at the top of `build.py`.
Fonts, colors and widths are in `style.css`. The page frame is `layout.html`.
