import sys
with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/index.css', 'r', encoding='utf-8') as f:
    content = f.read()

css_addition = """

:root {
  color-scheme: dark;
}

[data-theme="light"] {
  color-scheme: light;
  --bg-primary:     #F5F0EB;
  --bg-secondary:   #EDE8E1;
  --bg-elevated:    #E4DED5;
  --accent-red:     #C1121F;
  --accent-gold:    #A07C20;
  --accent-muted:   #6B4E71;
  --text-primary:   #1A1410;
  --text-secondary: #5C5248;
  --text-ghost:     #B8AFA6;
  --border:         #D4CEC7;
}

/* Light mode specific element treatments */
[data-theme="light"] .manga-cover {
  box-shadow: 0 1px 4px rgba(26,20,16,0.15);
}

[data-theme="light"] .skeleton-strip {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-elevated) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
}

/* Specific transitions for theme change */
body, header, aside, .manga-strip, .manga-grid, .manga-card, .filter-panel, .category-strip, .category-card, .view-toggle-btn {
  transition: background-color 200ms ease, color 200ms ease, border-color 200ms ease;
}

/* Theme Toggle Button */
.theme-toggle {
  font-family: var(--font-data);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 120ms ease;
  padding: 0;
  margin-left: 16px;
}

.theme-toggle:hover {
  color: var(--text-primary);
}
"""

if '[data-theme="light"]' not in content:
    with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/index.css', 'w', encoding='utf-8') as f:
        f.write(content + css_addition)
    print("CSS updated")
else:
    print("Already updated")