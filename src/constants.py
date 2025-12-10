
# --- Visualization Constants (Phase 1) ---
SCREEN_WIDTH = 600
PLAYER_STRIP_HEIGHT = 100
SCREEN_HEIGHT = 600 + PLAYER_STRIP_HEIGHT  # Grid + player strip
GRID_SIZE = 20  # 20x20 Grid
CELL_SIZE = 600 // GRID_SIZE  # Grid cell size

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GRID_COLOR = (200, 200, 200)
BUTTON_COLOR = (70, 130, 180)  # Steel blue
BUTTON_HOVER_COLOR = (100, 149, 237)  # Cornflower blue
STRIP_BG_COLOR = (240, 240, 240)

PLAYER_COLORS = {
    0: (255, 0, 0),      # Red
    1: (0, 0, 255),      # Blue
    2: (0, 255, 0),      # Green
    3: (255, 255, 0),    # Yellow
    'default': (100, 100, 100)  # Gray for unknown IDs
}

# Connection timeout
CONNECTION_TIMEOUT = 10.0  # seconds


