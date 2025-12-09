import pygame
from src.constants import BUTTON_COLOR, BUTTON_HOVER_COLOR, WHITE

class Button:
    """Simple button class for UI."""

    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.hovered = False

    def is_hovered(self, mouse_pos):
        """Check if mouse is over button."""
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered

    def is_clicked(self, mouse_pos):
        """Check if button was clicked."""
        return self.rect.collidepoint(mouse_pos)

    def draw(self, surface, mouse_pos):
        """Draw the button."""
        self.is_hovered(mouse_pos)
        color = BUTTON_HOVER_COLOR if self.hovered else BUTTON_COLOR

        # Draw button background
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)  # Border

        # Draw text
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

