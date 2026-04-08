# Using Shared Data Files in Documentation

The shared theme includes YAML data files that can be used across all provide.io documentation using the `mkdocs-macros-plugin`.

## ⚠️ Important: Custom Delimiter Syntax

**To avoid conflicts with GitHub Actions syntax (`${{ }}`), this documentation uses custom Jinja2 delimiters:**

- **Variables**: Use `{$ variable $}` instead of `{{ variable }}`
- **Blocks**: Use `{% block %}` (standard syntax unchanged)
- **Comments**: Use `{# comment #}` (standard syntax unchanged)

This means GitHub Actions examples like `${{ secrets.TOKEN }}` will render correctly without escaping.

## Available Data Files

### contributors.yml
Information about contributors to the ecosystem.

**Usage Example:**
```markdown
## Contributors

We're grateful to our contributors:

{% for contributor in contributors %}
### {$ contributor.name $}

- **Role:** {$ contributor.role $}
- **GitHub:** [@{$ contributor.github $}](https://github.com/{$ contributor.github $})
{% if contributor.contributions %}
- **Projects:** {$ contributor.contributions | join(", ") $}
{% endif %}

{$ contributor.bio $}

---
{% endfor %}
```

**Note:** This documentation uses custom Jinja2 delimiters (`{$ $}` for variables) to avoid conflicts with GitHub Actions syntax (`${{ }}`). Block tags still use standard `{% %}` syntax.

### external_links.yml
Organized external resources and links.

**Usage Example:**
```markdown
## Useful Resources

### Official Resources
{% for link in official %}
- [{{ link.name }}]({{ link.url }}) {{ link.icon }} - {{ link.description }}
{% endfor %}

### Package Registries
{% for pkg in packages %}
- [{{ pkg.name }}]({{ pkg.url }}) {{ pkg.icon }} - {{ pkg.description }}
{% endfor %}

### Related Technologies
{% for tech in related %}
- [{{ tech.name }}]({{ tech.url }}) {{ tech.icon }} - {{ tech.description }}
{% endfor %}
```

### people.yml
Team structure and project maintainers.

**Usage Example:**
```markdown
## Core Team

{% for person in core_team %}
### {{ person.name }}

<img src="{{ person.avatar }}" width="100" alt="{{ person.name }}">

**{{ person.role }}**

{{ person.bio }}

**Focus Areas:**
{% for area in person.focus_areas %}
- {{ area }}
{% endfor %}

[GitHub: @{{ person.github }}](https://github.com/{{ person.github }})

---
{% endfor %}

## Project Maintainers

### Foundation Layer
{% for project in maintainers.foundation_layer %}
- **{{ project.project }}**: {{ project.maintainer }} - {{ project.description }}
{% endfor %}

### Framework Layer
{% for project in maintainers.framework_layer %}
- **{{ project.project }}**: {{ project.maintainer }} - {{ project.description }}
{% endfor %}

### Tools Layer
{% for project in maintainers.tools_layer %}
- **{{ project.project }}**: {{ project.maintainer }} - {{ project.description }}
{% endfor %}
```

### sponsors.yml
Sponsor information and support tiers.

**Usage Example:**
```markdown
## Sponsors

{% if platinum_sponsors %}
### Platinum Sponsors
{% for sponsor in platinum_sponsors %}
[![{{ sponsor.name }}]({{ sponsor.logo }})]({{ sponsor.url }})
{% endfor %}
{% endif %}

{% if gold_sponsors %}
### Gold Sponsors
{% for sponsor in gold_sponsors %}
[![{{ sponsor.name }}]({{ sponsor.logo }})]({{ sponsor.url }})
{% endfor %}
{% endif %}

### Support Us

{{ info.description }}

**Sponsorship Benefits:**

#### Platinum ($5000+/month)
{% for benefit in info.benefits.platinum %}
- {{ benefit }}
{% endfor %}

#### Gold ($1000+/month)
{% for benefit in info.benefits.gold %}
- {{ benefit }}
{% endfor %}

[Become a Sponsor]({{ info.github_sponsors_url }})
```

## Advanced Usage

### Conditional Display

```markdown
{% if bronze_sponsors %}
## Bronze Sponsors
Thanks to our bronze sponsors:
{% for sponsor in bronze_sponsors %}
- [{{ sponsor.name }}]({{ sponsor.url }})
{% endfor %}
{% else %}
[Become our first sponsor!]({{ info.github_sponsors_url }})
{% endif %}
```

### Combining Data Sources

```markdown
## Acknowledgments

{% for ack in acknowledgments %}
### {{ ack.category }}
{% for credit in ack.credits %}
- **[{{ credit.name }}]({{ credit.url }})** - {{ credit.reason }}
{% endfor %}
{% endfor %}
```

### Creating Cards with HTML

```markdown
<div class="contributor-grid">
{% for contributor in contributors %}
<div class="contributor-card">
  <img src="{{ contributor.avatar }}" alt="{{ contributor.name }}">
  <h3>{{ contributor.name }}</h3>
  <p>{{ contributor.role }}</p>
  <a href="https://github.com/{{ contributor.github }}">@{{ contributor.github }}</a>
</div>
{% endfor %}
</div>
```

## Testing Macros

To test if macros are working in your documentation:

```markdown
## Debug Information

- Total contributors: {{ contributors | length }}
- Total external links: {{ official | length + packages | length + related | length }}
- Core team size: {{ core_team | length }}
```

## Configuration

Ensure your `mkdocs.yml` has the macros plugin configured:

```yaml
plugins:
  - macros:
      include_dir: ../provide-foundry/shared-theme/data
```

For the documentation hub (provide-foundry):

```yaml
plugins:
  - macros:
      include_dir: shared-theme/data
```

## Available Variables

When using the data files, the following variables are available:

**From contributors.yml:**
- `contributors` - List of contributor objects

**From external_links.yml:**
- `official` - Official provide.io links
- `packages` - PyPI package links
- `related` - Related technology links
- `community` - Community resource links
- `standards` - Standards and specifications

**From people.yml:**
- `core_team` - Core team members
- `maintainers` - Project maintainers by layer
- `community_contributors` - Community contributors
- `acknowledgments` - Acknowledgment sections

**From sponsors.yml:**
- `platinum_sponsors`, `gold_sponsors`, `silver_sponsors`, `bronze_sponsors`
- `individual_supporters`
- `info` - Sponsorship information and benefits

## Examples in Use

See these pages for live examples:
- Foundation documentation: Contributors page
- Provide Foundry hub: Resources section
- Project READMEs: Acknowledgments sections
