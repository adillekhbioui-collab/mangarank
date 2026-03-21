import re

file_path = "src/App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# Add state below viewMode
state_old = "const [viewMode, setViewMode] = useState('list')"
state_new = """const [viewMode, setViewMode] = useState('list')
    const [touchStart, setTouchStart] = useState(null)
    const [touchEnd, setTouchEnd] = useState(null)

    const onTouchStart = (e) => {
        setTouchEnd(null)
        setTouchStart(e.targetTouches[0].clientX)
    }

    const onTouchMove = (e) => setTouchEnd(e.targetTouches[0].clientX)

    const onTouchEnd = () => {
        if (!touchStart || !touchEnd) return
        const distance = touchStart - touchEnd
        const isLeftSwipe = distance > 50
        const isRightSwipe = distance < -50
        if (isLeftSwipe && viewMode === 'list') setViewMode('grid')
        if (isRightSwipe && viewMode === 'grid') setViewMode('list')
    }"""

code = code.replace(state_old, state_new, 1)

main_old = '<main className="content-area">'
main_new = '<main className="content-area" onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}>'

code = code.replace(main_old, main_new, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("App.jsx updated with swipe gestures.")
