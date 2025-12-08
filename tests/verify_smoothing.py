
import sys
import os
import time
from unittest.mock import MagicMock

# Mock pygame before importing client
sys.modules["pygame"] = MagicMock()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from client import GridClient

def verify_smoothing():
    print("Initializing Client...")
    client = GridClient(client_id=1)
    
    # Mock initial state
    print("Setting initial target to (100, 100)")
    client.target_players[1] = (100, 100)
    client.visual_players[1] = (100.0, 100.0) # Start exactly at target
    
    # Verify initial state
    assert client.visual_players[1] == (100.0, 100.0)
    print("Initial state verified.")
    
    # Move target
    print("Updating target to (200, 200)")
    client.target_players[1] = (200, 200)
    
    # Simulate a few frames
    dt = 0.016 # 60 FPS
    
    print("\nSimulating frames...")
    for i in range(60):
        client.update_visuals(dt)
        pos = client.visual_players[1]
        print(f"Frame {i+1}: Visual Pos: ({pos[0]:.2f}, {pos[1]:.2f}) Target: (200, 200)")
        
        # Check if it moved towards target
        if i == 0:
            assert pos[0] > 100.0 and pos[0] < 200.0
            assert pos[1] > 100.0 and pos[1] < 200.0
            
    # Verify it doesn't overshoot or NaN
    assert client.visual_players[1][0] <= 200.0
    
    print("\nVerification Passed: Smoothing logic is working!")

if __name__ == "__main__":
    verify_smoothing()
