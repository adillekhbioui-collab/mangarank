import re

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/MangaDetailPage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

import_str = "import { useTheme } from './hooks/useTheme.js'\n"
if "useTheme" not in content[:500]:
    content = content.replace("import { useState, useEffect } from 'react'", "import { useState, useEffect } from 'react'\n" + import_str)

hook_str = "const { theme, toggleTheme, isDark } = useTheme()"

# For MangaDetailPage, there are three return blocks depending on loading or error:
# We should probably put the hook near the top and add the button to the headers.
if "useTheme()" not in content:
    content = content.replace("export default function MangaDetailPage() {", "export default function MangaDetailPage() {\n    " + hook_str)

header_old = """            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo">
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
            </header>"""

header_new = """            <header className="site-header">
                <div className="header-left">
                    <Link to="/" className="logo">
                        <span className="logo-manhwa">MANHWA</span>
                        <span className="logo-rank">RANK</span>
                    </Link>
                </div>
                <div className="header-right">
                    <button className="theme-toggle" onClick={toggleTheme}>
                        {isDark ? '○ LIGHT' : '● DARK'}
                    </button>
                </div>
            </header>"""

content = content.replace(header_old, header_new)

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/MangaDetailPage.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("MangaDetailPage.jsx updated")
