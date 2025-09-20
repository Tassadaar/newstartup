import sys

import numpy as np
import pygame
from brainflow import DataFilter, BoardIds, BoardShim, LogLevels

from bci_control.brainflow_stream import compute_band_powers, BrainFlowBoard
from game.ball import START_SPEED, Ball
from game.brick import Brick
from game.constants import *
from game.paddle import Paddle


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(None, 36)
        self.large_font = pygame.font.Font(None, 74)

        self.state = 'playing'

        self.start_time = pygame.time.get_ticks()
        self.final_time = 0
        self.best_time = self._load_best_time()
        self.setup_objects()

        self.increasing = False
        self.ratio = 0.0
        self.max_ratio = 0.0

    def setup_objects(self):
        self.paddle = Paddle(SCREEN_HEIGHT - 40, SCREEN_WIDTH, PADDLE_HEIGHT, WHITE)
        self.ball = Ball(SCREEN_WIDTH // 2, self.paddle.rect.top - 10, 10, WHITE, speed=START_SPEED)
        self.bricks = self._create_bricks()

    def _create_bricks(self):
        bricks = []
        rows = len(VIBGYOR)
        cols = 10
        brick_width, brick_height = 75, 20
        gap = 5
        for row in range(rows):
            for col in range(cols):
                intensity = (rows - 1) - row
                color = VIBGYOR[row]
                brick_x = col * (brick_width + gap) + (gap * 4)
                brick_y = row * (brick_height + gap) + 50
                bricks.append(Brick(brick_x, brick_y, brick_width, brick_height, color, intensity))
        return bricks

    def remove_dc_offset(self, data):
        return data[1:4, :] - np.mean(data[1:4, :], axis=1, keepdims=True)

    def run(self):
        self.running = True
        self.max_ratio = 0.0
        board_id = BoardIds.CYTON_BOARD.value
        board = BrainFlowBoard(board_id=board_id, serial_port="/dev/cu.usbserial-DM01IK21")
        board.setup()
        board_descr = BoardShim.get_board_descr(board_id)
        sampling_rate = int(board_descr['sampling_rate'])
        BoardShim.log_message(LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')

        while self.running:
            self._handle_events()
            nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
            data = board.get_current_board_data(num_samples=500)

            if data is not None and len(data) > 0:
                try:
                    eeg_data = data

                    eeg_data = self.remove_dc_offset(eeg_data)
                    band_powers = compute_band_powers(eeg_data, sampling_rate, relative=True)
                    powers, _ = band_powers

                    self.ratio = powers[2] / powers[3]
                except Exception as e:
                    pass
            if self.ratio > self.max_ratio:
                self.max_ratio = self.ratio
                self.ball.increase_speed()
            elif self.ratio < self.max_ratio:
                self.ball.decrease_speed()
            if self.state == 'playing':
                self._update()
                self._draw()
            elif self.state in ('game_over', 'win'):
                self._draw_end_screen()

        self._cleanup()

    def _handle_events(self):

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            # TODO: map this to p300 instead
            if self.state == 'playing':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                    self.ball.increase_speed()
                  # elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:  #     self.ball.decrease_speed()  # elif event.type == pygame.MOUSEBUTTONDOWN:  #     self.ball.light_force()

    def _update(self):

        self.ball.update()
        self._handle_collisions()

    def _handle_collisions(self):
        if self.ball.rect.colliderect(self.paddle.rect):
            self.ball.bounce()
            self.ball.rect.bottom = self.paddle.rect.top

        hit_brick = None
        for brick in self.bricks:
            if self.ball.rect.colliderect(brick.rect):
                hit_brick = brick
                break

        if hit_brick:
            self.ball.bounce()
            if hit_brick.hit(factor=self.ball.speed % len(VIBGYOR)):
                self.bricks.remove(hit_brick)

        if self.ball.rect.bottom >= SCREEN_HEIGHT:
            self.state = 'game_over'
            self._handle_game_end()
        if not self.bricks:
            self.state = 'win'
            self._handle_game_end()

    def _draw(self):
        self.screen.fill(BLACK)
        self.paddle.draw(self.screen)
        self.ball.draw(self.screen)
        for brick in self.bricks:
            brick.draw(self.screen)
        self._draw_timer()
        pygame.display.flip()
        self.clock.tick(FPS)

    def _draw_timer(self):
        elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000
        minute, sec = divmod(elapsed_time, 60)
        timer_text = self.font.render(f"Time: {minute:02d}:{sec:02d}", True, WHITE)
        self.screen.blit(timer_text, timer_text.get_rect(topright=(SCREEN_WIDTH - 10, 10)))

    def _handle_game_end(self):

        self.final_time = (pygame.time.get_ticks() - self.start_time) // 1000

        if self.state == 'win':
            self.best_time = self.final_time
            self._save_best_time(self.best_time)

    def _draw_end_screen(self):

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        message = "Game Over" if self.state == 'game_over' else "You Win!"
        text_surf = self.large_font.render(message, True, WHITE)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        self.screen.blit(text_surf, text_rect)

        time_surf = self.font.render(f"Your Time: {self.final_time // 60:02d}:{self.final_time % 60:02d}", True, WHITE)
        time_rect = time_surf.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20))
        self.screen.blit(time_surf, time_rect)

        if self.best_time > 0:
            if self.final_time > self.best_time:
                self.best_time = self.final_time
            best_time_surf = self.font.render(f"Best Time: {self.best_time // 60:02d}:{self.best_time % 60:02d}", True,
                                              WHITE)
            best_time_rect = best_time_surf.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 60))
            self.screen.blit(best_time_surf, best_time_rect)

        pygame.display.flip()

    def _load_best_time(self):

        try:
            with open("best_time.txt", "r") as f:
                return int(f.read())
        except (FileNotFoundError, ValueError):
            return 0

    def _save_best_time(self, time):

        with open("best_time.txt", "w") as f:
            f.write(str(time))

    def _cleanup(self):

        pygame.quit()
        sys.exit()
