import re

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

import_str = "import { useTheme } from './hooks/useTheme.js'\n"
if "useTheme" not in content[:500]:
    content = content.replace("import { useState, useEffect, useCallback, useMemo, useRef } from 'react'", "import { useState, useEffect, useCallback, useMemo, useRef } from 'react'\n" + import_str)

hook_str = "const { theme, toggleTheme, isDark } = useTheme()"
if hook_str not in content:
    content = content.replace("const [searchParams, setSearchParams] = useSearchParams()", "const [searchParams, setSearchParams] = useSearchParams()\n    " + hook_str)

btn_old = """                    />
                </div>"""

btn_new = """                    />
                    <button className="theme-toggle" onClick={toggleTheme}>
                        {isDark ? '○ LIGHT' : '● DARK'}
                    </button>
                </div>"""

if 'class="theme-toggle"' not in content and 'className="theme-toggle"' not in content:
    content = content.replace(btn_old, btn_new)

with open('c:/Users/Adill/Documents/project_manhwa_v2/manhwa-aggregator/frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
