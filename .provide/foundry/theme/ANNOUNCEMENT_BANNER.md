# Announcement Banner System

The shared theme includes an announcement banner system for marking AI-generated content and displaying version status (pre-release/stable). Some APIs may change during the pre-release series.

## Features

- **Automatic version detection**: Reads `VERSION` file and displays pre-release status
- **AI-generated content notice**: Shows warning banner on all pages by default
- **Per-page control**: Use frontmatter to mark pages as audited and hide the banner
- **Responsive design**: Works on mobile and desktop with light/dark mode support

## How It Works

### 1. Version Status Detection

The `hooks/version_hook.py` reads your project's `VERSION` file and automatically determines status:

- **Pre-release**: Versions like `0.x.y` or `1.0.0-beta.1`
- **Stable**: Versions like `1.0.0` and above

### 2. Default Banner

By default, all pages show a warning banner:

```
⚠️ Pre-release — 📝 This documentation contains AI-generated content that may not have been reviewed by a human. Please report issues if you find inaccuracies.
```

### 3. Marking Pages as Audited

Add frontmatter to hide the banner on audited pages:

```markdown
---
audited: true
reviewer: "John Doe"
audit_notes: "Reviewed and approved 2025-11-06"
---

# My Audited Page

This page has been reviewed by a human...
```

**Frontmatter Fields:**

- `audited` (boolean): Set to `true` to hide the banner
- `reviewer` (string, optional): Name of reviewer
- `audit_notes` (string, optional): Notes about the review/audit
- `show_ai_notice` (boolean, optional): Explicitly show/hide banner (overrides `audited`)

## Setup Instructions

### Step 1: Enable in mkdocs.yml

```yaml
theme:
  name: material
  custom_dir: !relative $THEME_DIR/overrides  # Enable custom templates

plugins:
  - macros:
      module_name: provide.foundry.theme.hooks.version_hook  # Enable VERSION parsing

hooks:
  - provide.foundry.theme.hooks.version_hook  # Parse VERSION file on build
```

### Step 2: Ensure VERSION File Exists

Create a `VERSION` file in your project root:

```bash
echo "0.3.0" > VERSION
```

### Step 3: Build and Test

```bash
mkdocs serve
```

Visit any page - you should see the announcement banner at the top.

## Examples

### Example 1: Unaudited Page (Shows Banner)

```markdown
# My New Feature Documentation

This is AI-generated content that needs review...
```

**Result:** Shows banner with AI warning

### Example 2: Audited Page (No Banner)

```markdown
---
audited: true
reviewer: "Tim"
audit_notes: "Reviewed and corrected on 2025-11-06"
---

# Core Infrastructure

This documentation has been reviewed...
```

**Result:** No banner shown

### Example 3: Custom Audit Notes

```markdown
---
audited: false
audit_notes: "Partial review - sections 1-3 verified, rest needs work"
---

# Partially Audited Page

...
```

**Result:** Shows banner with custom audit notes

### Example 4: Force Hide Banner

```markdown
---
show_ai_notice: false
---

# Special Page

This page doesn't need the AI notice...
```

**Result:** Banner hidden regardless of audit status

## Customization

### Change Banner Message

Edit `src/provide/foundry/theme/overrides/announce.html`:

```html
<span class="md-banner__message">
  Your custom message here...
</span>
```

### Change Banner Colors

Edit `src/provide/foundry/theme/css/provide-theme.css`:

```css
.md-banner--warning {
    background-color: #your-color;
    color: #your-text-color;
}
```

### Add Different Banner Types

You can create different banner styles (info, success, danger) by adding CSS classes:

```css
.md-banner--info {
    background-color: #d1ecf1;
    border-bottom-color: #0c5460;
    color: #0c5460;
}
```

## Integration with Existing Projects

If your project already uses `base-mkdocs.yml` from provide-foundry, the banner system is automatically available. Just add frontmatter to control it on a per-page basis.

### Migration Guide

For existing documentation:

1. **Leave as-is** - All existing pages will show the banner by default
2. **Audit gradually** - Add `audited: true` frontmatter as you review pages
3. **Track progress** - Use `grep -r "audited: true" docs/` to see how many pages are audited

## Workflow Recommendations

### For New Documentation

```markdown
---
# Default for AI-generated content - remove audited field
# Add once human review is complete
---

# New Page Title
```

### For Human-Written Documentation

```markdown
---
audited: true
reviewer: "Author Name"
---

# Hand-Crafted Documentation
```

### For Collaborative Review

```markdown
---
audited: false
audit_notes: "Needs technical review from backend team"
reviewer_requested: "Alice"
---

# Pending Review
```

## Troubleshooting

### Banner Not Showing

1. Verify `custom_dir` points to theme overrides
2. Check that VERSION file exists in project root
3. Ensure hooks are registered in mkdocs.yml

### Banner Shows on Audited Pages

1. Check frontmatter syntax (must be valid YAML)
2. Ensure `audited: true` (not `audited: "true"` as string)
3. Clear MkDocs cache: `rm -rf site/`

### VERSION Not Detected

1. Confirm VERSION file is in same directory as mkdocs.yml parent
2. Check hook is registered in mkdocs.yml under `hooks:`
3. Look for errors in build output

## Related Files

- `src/provide/foundry/theme/overrides/announce.html` - Banner template
- `src/provide/foundry/theme/hooks/version_hook.py` - VERSION parser and config hook
- `src/provide/foundry/theme/css/provide-theme.css` - Banner styles
