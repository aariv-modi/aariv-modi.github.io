title: How This Site Works
date: 2026-11
draft: yes

This is a sample essay. It shows everything the build script understands, so you can delete it once you've written your own.

Each essay is a plain text file in the `essays` folder. The first lines give the title and date. After a blank line comes the essay itself, written in Markdown: blank lines separate paragraphs, and a few symbols add formatting.

## Formatting

You can write *italics*, **bold**, `code`, and [links](https://example.com). Lists work too:

- one item
- another item

So do numbered lists:

1. first
2. second

> A line starting with ">" becomes a quotation.

A number in square brackets, like this one [1], links to the matching note at the end of the essay.

## Publishing

Run `python build.py` and the finished pages appear in the `site` folder. Upload that folder anywhere that hosts static files and you're done.

To keep an essay out of the site while you work on it, add `draft: yes` under its date.

## Notes

[1] Notes go under a heading called "Notes". Each one starts with its number in square brackets.

**Thanks** to you for reading this one.
