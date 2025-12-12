import random

# --- Core Constraint ---
MAX_CLIENTS = 4

#############################################
############ Server Constants ###############
#############################################


def calculate_grid_size(max_clients):
    """
    Sets the logical grid dimensions based on the number of players.
    - Up to 4 players: 20x20
    - 5 to 6 players: 25x25 (New requirement)
    - 7 to 9 players: 30x30
    - 10 to 12 players: 35x35
    - More than 12 players: Scales up by 5 for every 3 extra players
    """
    if max_clients <= 4:
        return 20
    elif max_clients <= 6:
        return 25 # 5 or 6 players get 25x25
    elif max_clients <= 9:
        return 30 # 7, 8, or 9 players get 30x30
    else:

        return 30 + 5 * ((max_clients - 7) // 3)

GRID_SIZE = calculate_grid_size(MAX_CLIENTS)

# Network configurations
DEFAULT_PORT = 12000
MAX_PACKET_SIZE = 1200  # May need to increase


def generate_player_positions(max_clients, grid_size):
    """
    Generates starting positions for players by dividing the grid into
    regions based on the number of clients. (Logic remains sound)
    """
    positions = {}


    dim = max(2, int(max_clients ** 0.5 + 0.999))  # Ensure minimum 2x2 grid

    cell_width = grid_size // dim
    cell_height = grid_size // dim

    for i in range(max_clients):
        row_idx = i // dim
        col_idx = i % dim

        # Define the safe region within the cell for random placement
        min_x = int(col_idx * cell_width + 2)
        max_x = int((col_idx + 1) * cell_width - 2)
        min_y = int(row_idx * cell_height + 2)
        max_y = int((row_idx + 1) * cell_height - 2)

        if min_x < max_x and min_y < max_y:
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
        else:
            x = random.randint(1, grid_size - 1)
            y = random.randint(1, grid_size - 1)

        positions[i] = (x, y)

    positions['default'] = (grid_size // 2, grid_size // 2)
    return positions


PLAYER_POSITIONS = generate_player_positions(MAX_CLIENTS, GRID_SIZE)

WINNING_THRESHOLD = MAX_CLIENTS * 50
#############################################
############ Client Constants ###############
#############################################


GRID_WIDTH = int(GRID_SIZE)
GRID_HEIGHT = int(GRID_SIZE)


MAX_SCREEN_DIMENSION = 800

# Calculate the optimal CELL_SIZE to ensure SCREEN_WIDTH does not exceed the maximum.
# We aim for a target of 30, but must reduce it if the grid is too big.
TARGET_CELL_SIZE = 30
CELL_SIZE = min(TARGET_CELL_SIZE, MAX_SCREEN_DIMENSION // GRID_SIZE)
if CELL_SIZE < 1:
    CELL_SIZE = 1 # Minimum cell size must be 1

SCREEN_WIDTH = int(GRID_SIZE * CELL_SIZE)


PLAYER_STRIP_HEIGHT = 100
SCREEN_HEIGHT = SCREEN_WIDTH + PLAYER_STRIP_HEIGHT



# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GRID_COLOR = (200, 200, 200)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 149, 237)
STRIP_BG_COLOR = (240, 240, 240)


def generate_player_colors(max_clients):
    # ... (Color generation function remains the same) ...
    colors = {}
    base_colors = {
        0: (255, 0, 0),  # Red
        1: (0, 0, 255),  # Blue
        2: (0, 255, 0),  # Green
        3: (255, 255, 0)  # Yellow
    }

    if max_clients <= 4:
        colors = base_colors
    else:
        for i in range(max_clients):
            hue = int((i * 360 / max_clients) % 360)
            h = hue / 60.0
            c = 255
            x = int(c * (1 - abs(h % 2 - 1)))

            r, g, b = 0, 0, 0
            # RGB calculation block...
            if 0 <= h < 1: r, g, b = c, x, 0
            elif 1 <= h < 2: r, g, b = x, c, 0
            elif 2 <= h < 3: r, g, b = 0, c, x
            elif 3 <= h < 4: r, g, b = 0, x, c
            elif 4 <= h < 5: r, g, b = x, 0, c
            elif 5 <= h < 6: r, g, b = c, 0, x

            colors[i] = (r, g, b)

    colors['default'] = (100, 100, 100)
    return colors


PLAYER_COLORS = generate_player_colors(MAX_CLIENTS)

# Connection timeout
CONNECTION_TIMEOUT = 10.0  # seconds

# Verify the dynamic values for the user
print(f"--- Configuration Summary (MAX_CLIENTS={MAX_CLIENTS}) ---")
print(f"GRID_SIZE: {GRID_SIZE}x{GRID_SIZE}")
print(f"CELL_SIZE: {CELL_SIZE}")
print(f"SCREEN_WIDTH: {SCREEN_WIDTH}")
print(f"SCREEN_HEIGHT: {SCREEN_HEIGHT}")
print(f"Generated Positions: {PLAYER_POSITIONS}")
print(f"Generated Colors: {PLAYER_COLORS}")