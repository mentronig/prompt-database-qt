PALETTES = {
    "light": {"bg": "#FFFFFF", "fg": "#111827", "accent": "#3B82F6", "muted": "#6B7280"},
    "dark": {"bg": "#0B1220", "fg": "#E5E7EB", "accent": "#60A5FA", "muted": "#9CA3AF"},
}

def palette(mode: str = "light") -> dict:
    return PALETTES.get(mode, PALETTES["light"])
