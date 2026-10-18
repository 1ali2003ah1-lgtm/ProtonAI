"""ProtonAI Design System - Medical-grade UI components.
Designed & developed by: Ali Hussein Thajil

Color palette inspired by medical imaging standards (DICOM GSDF).
Typography: system fonts for performance.
Spacing: 4px grid system.
"""

# Medical color palette (DICOM-compliant)
COLORS = {
    "primary": "#0D47A1",      # Deep medical blue
    "primary_light": "#1976D2",
    "primary_dark": "#002171",
    "secondary": "#00ACC1",    # Teal accent
    "success": "#2E7D32",      # Green (healthy tissue)
    "warning": "#F9A825",      # Amber (caution)
    "error": "#C62828",        # Red (critical)
    "info": "#1565C0",         # Blue (information)
    "neutral": {
        "50": "#FAFAFA",
        "100": "#F5F5F5",
        "200": "#EEEEEE",
        "300": "#E0E0E0",
        "400": "#BDBDBD",
        "500": "#9E9E9E",
        "600": "#757575",
        "700": "#616161",
        "800": "#424242",
        "900": "#212121",
    },
}

# Semantic colors
SEMANTIC = {
    "target": "#FF1744",       # Red (tumor)
    "oar": "#2196F3",          # Blue (organs at risk)
    "dose_high": "#F44336",    # Red (high dose)
    "dose_medium": "#FF9800",  # Orange (medium dose)
    "dose_low": "#4CAF50",     # Green (low dose)
    "uncertainty": "#FF5722",  # Deep orange (uncertainty)
    "contour": "#00E676",      # Bright green (contours)
}

# Spacing system (4px grid)
SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "xxl": "48px",
}

# Border radius
RADIUS = {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px",
}

# Shadows
SHADOWS = {
    "sm": "0 1px 3px rgba(0,0,0,0.12)",
    "md": "0 4px 6px rgba(0,0,0,0.1)",
    "lg": "0 10px 15px rgba(0,0,0,0.1)",
    "xl": "0 20px 25px rgba(0,0,0,0.15)",
}

# Typography
TYPOGRAPHY = {
    "h1": "2.5rem",
    "h2": "2rem",
    "h3": "1.5rem",
    "h4": "1.25rem",
    "body": "1rem",
    "small": "0.875rem",
    "tiny": "0.75rem",
}

# Animation
ANIMATION = {
    "fast": "150ms",
    "normal": "300ms",
    "slow": "500ms",
    "ease": "cubic-bezier(0.4, 0, 0.2, 1)",
}


def get_css_variables():
    """Generate CSS custom properties for theming."""
    css = ":root {\n"
    for key, value in COLORS.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                css += f"  --color-{key}-{subkey}: {subvalue};\n"
        else:
            css += f"  --color-{key}: {value};\n"
    for key, value in SPACING.items():
        css += f"  --spacing-{key}: {value};\n"
    for key, value in RADIUS.items():
        css += f"  --radius-{key}: {value};\n"
    css += "}\n"
    return css


def get_base_styles():
    """Base CSS for ProtonAI console."""
    return """
/* Base styles */
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
               'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
  color: var(--color-neutral-900);
  background: var(--color-neutral-50);
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
  margin: 0 0 var(--spacing-md);
  font-weight: 600;
  line-height: 1.2;
}

h1 { font-size: var(--spacing-xxl); }
h2 { font-size: var(--spacing-xl); }
h3 { font-size: var(--spacing-lg); }

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--animation-fast) var(--animation-ease);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-secondary {
  background: var(--color-neutral-200);
  color: var(--color-neutral-900);
}

.btn-secondary:hover {
  background: var(--color-neutral-300);
}

/* Cards */
.card {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--animation-normal) var(--animation-ease);
}

.card:hover {
  box-shadow: var(--shadow-md);
}

/* Glassmorphism */
.glass {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

/* Traffic lights */
.tl {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: var(--spacing-sm);
}

.tl-g { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.tl-y { background: var(--color-warning); box-shadow: 0 0 8px var(--color-warning); }
.tl-r { background: var(--color-error); box-shadow: 0 0 8px var(--color-error); }

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--spacing-small);
  font-weight: 600;
}

.badge-primary { background: var(--color-primary); color: white; }
.badge-success { background: var(--color-success); color: white; }
.badge-warning { background: var(--color-warning); color: white; }
.badge-error { background: var(--color-error); color: white; }

/* Alerts */
.alert {
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border-left: 4px solid;
  margin: var(--spacing-md) 0;
}

.alert-success {
  background: #E8F5E9;
  border-color: var(--color-success);
  color: #1B5E20;
}

.alert-warning {
  background: #FFF3E0;
  border-color: var(--color-warning);
  color: #E65100;
}

.alert-error {
  background: #FFEBEE;
  border-color: var(--color-error);
  color: #B71C1C;
}

.alert-info {
  background: #E3F2FD;
  border-color: var(--color-info);
  color: #0D47A1;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { transform: translateX(-20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-fadeIn { animation: fadeIn var(--animation-normal) var(--animation-ease); }
.animate-slideIn { animation: slideIn var(--animation-normal) var(--animation-ease); }
.animate-pulse { animation: pulse 2s infinite; }

/* Skeleton loading */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Dark mode */
[data-theme="dark"] {
  --color-neutral-50: #121212;
  --color-neutral-100: #1E1E1E;
  --color-neutral-200: #2D2D2D;
  --color-neutral-900: #E0E0E0;
}

[data-theme="dark"] body {
  background: var(--color-neutral-50);
  color: var(--color-neutral-900);
}

[data-theme="dark"] .card,
[data-theme="dark"] .glass {
  background: rgba(30, 30, 30, 0.92);
  border-color: rgba(255, 255, 255, 0.1);
}

/* Responsive */
@media (max-width: 768px) {
  :root {
    --spacing-lg: 16px;
    --spacing-xl: 24px;
  }
}
"""


def get_hero_styles():
    """Hero section styles with gradient animation."""
    return """
.hero {
  background: linear-gradient(135deg,
    var(--color-primary-dark) 0%,
    var(--color-primary) 30%,
    var(--color-secondary) 60%,
    #7C4DFF 100%);
  background-size: 300% 300%;
  animation: gradient-shift 12s ease infinite;
  color: white;
  padding: 32px;
  border-radius: var(--radius-xl);
  margin-bottom: var(--spacing-lg);
  box-shadow: 0 10px 40px rgba(13, 71, 161, 0.5);
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);
  pointer-events: none;
}

.hero h1 {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0;
  letter-spacing: 0.5px;
  position: relative;
  z-index: 1;
}

.hero p {
  margin: 8px 0 0;
  opacity: 0.95;
  font-size: 1.1rem;
  position: relative;
  z-index: 1;
}

.hero .signature {
  font-size: 0.9rem;
  opacity: 0.9;
  margin-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  padding-top: 10px;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.pro-badge {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #000;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 800;
  margin-left: 8px;
  letter-spacing: 1px;
  display: inline-block;
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);
}
"""


def get_command_palette_styles():
    """Command palette (Ctrl+K) styles."""
    return """
.command-palette {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  max-width: 90vw;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  z-index: 10000;
  display: none;
}

.command-palette.active {
  display: block;
  animation: fadeIn var(--animation-fast) var(--animation-ease);
}

.command-palette input {
  width: 100%;
  padding: var(--spacing-md);
  border: none;
  border-bottom: 1px solid var(--color-neutral-200);
  font-size: 1.1rem;
  outline: none;
}

.command-palette .results {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.command-palette .result-item {
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: background var(--animation-fast);
}

.command-palette .result-item:hover,
.command-palette .result-item.selected {
  background: var(--color-neutral-100);
}

.command-palette-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: none;
}

.command-palette-overlay.active {
  display: block;
}
"""


def get_all_styles():
    """Combine all styles."""
    return (get_css_variables() + "\n" +
            get_base_styles() + "\n" +
            get_hero_styles() + "\n" +
            get_command_palette_styles())
