import math
import sys
from random import randint, choice

import pygame

FPS = 60
WINDOW_WIDTH = 860
WINDOW_HEIGHT = 480
BRICK_COOLDOWN = 10000
BRICK_LIFETIME = 10000
pygame.init()
start_time = pygame.time.get_ticks()
font = pygame.font.Font(None, 36)
clock = pygame.time.Clock()
DISPLAY_SURF = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.mixer.init()

pygame.mixer.music.load("game-background.mp3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)

background_img = pygame.image.load("background-image.jpg").convert()
background_img = pygame.transform.scale(background_img, (WINDOW_WIDTH, WINDOW_HEIGHT))
move_sound = pygame.mixer.Sound("player-walk.mp3")
zombie_move_sound = pygame.mixer.Sound("zombie-walk.mp3")
shoot_sound = pygame.mixer.Sound("shot-sound.mp3")
game_over_sound = pygame.mixer.Sound("game-over.mp3")

game_over_sound.set_volume(0.7)
move_sound.set_volume(0.6)
zombie_move_sound.set_volume(0.2)
shoot_sound.set_volume(0.4)


def load_and_scale(path, scale_factor=5):
    img = pygame.image.load(path).convert_alpha()
    width, height = img.get_size()
    scaled_img = pygame.transform.scale(img, (width // scale_factor, height // scale_factor))
    return scaled_img


player_standing = load_and_scale("player-standing.png", 5)
player_walk1 = load_and_scale("player-walk-1.png", 5)
player_walk2 = load_and_scale("player-walk-2.png", 5)
zombie_walk1 = load_and_scale("zombie-walk-1.png", 5)
zombie_walk2 = load_and_scale("zombie-walk-2.png", 5)
zombie_dead = load_and_scale("zombie-dead.png", 5)
bullet_img = load_and_scale("bullet.png", 25)
brick_img = load_and_scale("brick.png", 10)
zombie_walk_frames = [zombie_walk1, zombie_walk2]
walk_frames = [player_walk1, player_walk2]


class Player:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed
        self.image = player_standing
        self.frame_index = 0
        self.animation_speed = 0.15
        self.moving = False
        self.gun_offset_x = 15
        self.gun_offset_y = 0
        self.hits = 0
        self.score = 0

    def handle_input(self, bricks):
        keys = pygame.key.get_pressed()
        self.moving = False

        dx = dy = 0
        if keys[pygame.K_w]:
            dy -= self.speed
            self.moving = True
        if keys[pygame.K_s]:
            dy += self.speed
            self.moving = True
        if keys[pygame.K_a]:
            dx -= self.speed
            self.moving = True
        if keys[pygame.K_d]:
            dx += self.speed
            self.moving = True

        new_x = self.x + dx
        new_x = max(0, min(WINDOW_WIDTH - self.image.get_width(), new_x))
        if not self.check_brick_collision(new_x, self.y, bricks):
            self.x = new_x

        new_y = self.y + dy
        new_y = max(0, min(WINDOW_HEIGHT - self.image.get_height(), new_y))

        if not self.check_brick_collision(self.x, new_y, bricks):
            self.y = new_y

    def check_brick_collision(self, new_x, new_y, bricks):
        test_rect = pygame.Rect(new_x, new_y, self.image.get_width(), self.image.get_height())
        for brick in bricks:
            if test_rect.colliderect(brick.rect):
                return True
        return False

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())

    def update_animation(self):
        if self.moving:
            self.frame_index += self.animation_speed
            if self.frame_index >= len(walk_frames):
                self.frame_index = 0
            self.image = walk_frames[int(self.frame_index)]
        else:
            self.image = player_standing

    def draw(self, surface):
        mx, my = pygame.mouse.get_pos()
        cx, cy = self.get_center()

        if mx < cx:
            flipped_image = pygame.transform.flip(self.image, True, False)
            surface.blit(flipped_image, (self.x, self.y))
        else:
            surface.blit(self.image, (self.x, self.y))

    def get_center(self):
        return self.x + self.image.get_width() // 2, self.y + self.image.get_height() // 2

    def get_gun_position(self):
        center_x = self.x + self.image.get_width() // 2
        center_y = self.y + self.image.get_height() // 2
        return center_x + self.gun_offset_x, center_y + self.gun_offset_y

    def add_score(self, points=10):
        self.score += points


class Zombie:

    def __init__(self, x, y, speed=0.5):
        self.x = x
        self.y = y
        self.speed = speed
        self.frame_index = 0
        self.animation_speed = 0.1
        self.dead = False
        self.dead_time = 0
        self.image = zombie_walk_frames[0]
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    def move_towards_player(self, player):
        if self.dead:
            return
        px, py = player.get_center()
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        self.x += dx / dist * self.speed
        self.y += dy / dist * self.speed
        self.rect.topleft = (self.x, self.y)
        if not pygame.mixer.Channel(2).get_busy():
            pygame.mixer.Channel(2).play(zombie_move_sound)

    def update_animation(self):
        if self.dead:
            return
        self.frame_index += self.animation_speed
        if self.frame_index >= len(zombie_walk_frames):
            self.frame_index = 0
        self.image = zombie_walk_frames[int(self.frame_index)]

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))

    def hit_by_bullet(self):
        self.dead = True
        self.dead_time = pygame.time.get_ticks()
        self.image = zombie_dead


def spawn_zombie_offscreen(speed=1.0):
    side = choice(['top', 'bottom', 'left', 'right'])
    if side == 'top':
        x = randint(0, WINDOW_WIDTH)
        y = -zombie_walk1.get_height()
    elif side == 'bottom':
        x = randint(0, WINDOW_WIDTH)
        y = WINDOW_HEIGHT + zombie_walk1.get_height()
    elif side == 'left':
        x = -zombie_walk1.get_width()
        y = randint(0, WINDOW_HEIGHT)
    else:
        x = WINDOW_WIDTH + zombie_walk1.get_width()
        y = randint(0, WINDOW_HEIGHT)
    return Zombie(x, y, speed=speed)


class Bullet:
    def __init__(self, x, y, target_x, target_y, speed=5):
        self.image = bullet_img
        self.rect = self.image.get_rect(center=(x, y))

        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.vel_x = dx / dist * speed
        self.vel_y = dy / dist * speed

    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Brick:
    def __init__(self, x, y):
        self.image = brick_img
        self.rect = self.image.get_rect(topleft=(x, y))
        self.spawn_time = pygame.time.get_ticks()
        self.zombie_hits = 0

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def is_expired(self):
        return pygame.time.get_ticks() - self.spawn_time > BRICK_LIFETIME

    def handle_zombie_collision(self, zombie):
        if self.is_expired():
            return False
        if self.rect.colliderect(zombie.rect):
            self.zombie_hits += 1
            if self.zombie_hits >= 3:
                return True
        return False


def draw_hud(surface, player):
    score_text = font.render(f"Score: {player.score}", True, (255, 255, 255))
    hits_text = font.render(f"Hits: {player.hits}/3", True, (255, 255, 255))

    surface.blit(score_text, (10, 10))
    surface.blit(hits_text, (10, 50))


def game_over_screen(player):
    pygame.mixer.music.stop()
    game_over_sound.play()

    DISPLAY_SURF.fill((0, 0, 0))
    game_over_text = font.render("GAME OVER", True, (255, 0, 0))
    score_text = font.render(f"Final Score: {player.score}", True, (255, 255, 255))
    restart_text = font.render("Press R to Restart or Q to Quit", True, (200, 200, 200))

    DISPLAY_SURF.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, 150))
    DISPLAY_SURF.blit(score_text, (WINDOW_WIDTH // 2 - score_text.get_width() // 2, 220))
    DISPLAY_SURF.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, 300))
    pygame.display.update()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    main()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()


def main():
    player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, speed=1.5)
    bullets = []
    zombies = []
    bricks = []

    spawn_timer = 0
    zombie_spawn_count = 1
    zombie_speed = 1.0
    difficulty_timer = 0
    DIFFICULTY_INTERVAL = FPS * 30
    SPAWN_INTERVAL = 120
    last_brick_time = -BRICK_COOLDOWN

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    gx, gy = player.get_gun_position()
                    mx, my = pygame.mouse.get_pos()
                    bullets.append(Bullet(gx, gy, mx, my))
                    shoot_sound.play()
                if event.button == 3:
                    now = pygame.time.get_ticks()
                    if now - last_brick_time >= BRICK_COOLDOWN:
                        px, py = player.get_center()
                        mx, my = pygame.mouse.get_pos()

                        dx = mx - px
                        dy = my - py
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dist = 1
                        bx = px + dx / dist * 100 - brick_img.get_width() // 2
                        by = py + dy / dist * 100 - brick_img.get_height() // 2
                        bricks.append(Brick(bx, by))
                        last_brick_time = now

        player.handle_input(bricks)
        player.update_animation()

        for bullet in bullets[:]:
            bullet.update()
            for brick in bricks:
                if bullet.rect.colliderect(brick.rect):
                    if bullet in bullets:
                        bullets.remove(bullet)
            if (bullet.rect.x < 0 or bullet.rect.x > WINDOW_WIDTH or
                    bullet.rect.y < 0 or bullet.rect.y > WINDOW_HEIGHT):
                bullets.remove(bullet)

        for zombie in zombies[:]:
            if not zombie.dead:
                hit_brick = False
                for brick in bricks:
                    if zombie.rect.colliderect(brick.rect):
                        zombie.hit_by_bullet()
                        player.add_score(1)
                        hit_brick = True
                        break
                if not hit_brick:
                    zombie.speed = 0.5
                    zombie.move_towards_player(player)

                zombie.update_animation()

                if zombie.rect.colliderect(player.get_rect()):
                    player.hits += 1
                    zombies.remove(zombie)
                    if player.hits >= 3:
                        game_over_screen(player)
            else:
                if pygame.time.get_ticks() - zombie.dead_time > 5000:
                    zombies.remove(zombie)

        for bullet in bullets[:]:
            for zombie in zombies:
                if not zombie.dead and bullet.rect.colliderect(zombie.rect):
                    zombie.hit_by_bullet()
                    player.add_score(1)
                    if bullet in bullets:
                        bullets.remove(bullet)

        bricks = [b for b in bricks if not b.is_expired()]
        spawn_timer += 1
        difficulty_timer += 1

        if spawn_timer >= SPAWN_INTERVAL:
            elapsed_seconds = (pygame.time.get_ticks() - start_time) / 1000.0
            current_speed = 1.0 + 0.01 + (elapsed_seconds * 0.02)

            for _ in range(zombie_spawn_count):
                zombies.append(spawn_zombie_offscreen(speed=current_speed))

            spawn_timer = 0

        if difficulty_timer >= DIFFICULTY_INTERVAL:
            zombie_spawn_count += 1
            zombie_speed += 0.1
            difficulty_timer = 0

        DISPLAY_SURF.blit(background_img, (0, 0))
        player.draw(DISPLAY_SURF)
        for bullet in bullets:
            bullet.draw(DISPLAY_SURF)

        for zombie in zombies:
            zombie.draw(DISPLAY_SURF)

        for brick in bricks:
            brick.draw(DISPLAY_SURF)

        draw_hud(DISPLAY_SURF, player)
        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
