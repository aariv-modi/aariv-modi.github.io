# Essays

A plain essay site, live at https://aariv-modi.github.io.

## Write and publish

Double-click **Write essay** on the Desktop, or search for it in the Start menu. The editor opens in your browser (http://localhost:8000/edit). It runs without a window and stops by itself about 30 minutes after you close the editor tab.

If the shortcut is ever lost, `python editor.py` does the same thing.

- **Save** keeps the essay on this computer only. New essays start as drafts.
- **Preview** shows the page as it will look on the site.
- **Publish** sends the essay to GitHub, and it goes live in a minute or two.
- For an essay that's already live, **Publish changes** updates it and **Unpublish** takes it down.

The editor only works from this computer. To post from elsewhere, add a file to the `essays` folder on github.com.

## Essay files

Each essay is a text file in `essays/`, named after its title (`why-i-write.md` becomes `why-i-write.html`). You can also edit these files directly:

```
title: Why I Write
date: 2026-11-24
draft: yes

First paragraph...
```

`essays/how-this-site-works.md` shows all the formatting. Images go in `files/` and are referenced as `![description](files/photo.jpg)`.
To delete an essay, delete its file, then commit and push.

## Settings

The site name and an optional intro line are at the top of `build.py`.
Fonts, colors and widths are in `style.css`. The page frame is `layout.html`.
GitHub runs `build.py` on every push to rebuild the site (drafts left out).
