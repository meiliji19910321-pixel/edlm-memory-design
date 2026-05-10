---
description: Convert markdown to PDF with excellent Obsidian compatibility
---

# md2pdf Skill

## Overview

A markdown to PDF converter optimized for Obsidian users. Provides seamless conversion with beautiful output quality.

## Installation

```bash
pip install md2pdf
```

Or via npm:
```bash
npm install -g md2pdf
```

## Core Features

- **Obsidian Friendly**: Optimized output for Obsidian-generated markdown
- **Out of the Box**: Works with default settings, no complex configuration
- **Beautiful Typography**: Clean, readable PDF output
- **Code Highlighting**: Syntax highlighting for code blocks
- **Front Matter Support**: Handles YAML front matter correctly

## Usage

### Command Line

```bash
# Basic conversion
md2pdf input.md output.pdf

# With options
md2pdf input.md output.pdf --style fancy --toc
```

### Python API

```python
from md2pdf import md2pdf

md2pdf('output.pdf', 'input.md')

# With custom styles
md2pdf('output.pdf', 'input.md', css_file='custom.css')
```

## CSS Customization

Create a custom `style.css` for styling:

```css
body {
    font-family: 'Segoe UI', sans-serif;
    line-height: 1.6;
}

code {
    background-color: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
}

pre {
    background-color: #272822;
    color: #f8f8f2;
    padding: 15px;
    overflow-x: auto;
}
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--style` | CSS style preset | default |
| `--toc` | Generate table of contents | false |
| `--toc-depth` | TOC heading depth (1-6) | 3 |
| `--page-size` | Page size (A4, Letter, etc.) | A4 |
| `--margin` | Page margins | 20mm |

## Obsidian Integration

Works seamlessly with Obsidian markdown:
- Supports Obsidian callouts
- Handles internal links
- Preserves formatting
- Supports footnotes

## Example Workflow

```bash
# Convert a note from Obsidian vault
md2pdf "path/to/note.md" "output.pdf"

# Batch convert all md files
for f in *.md; do md2pdf "$f" "${f%.md}.pdf"; done
```