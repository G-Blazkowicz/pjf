from typing import Callable, Any

import pygame
from pygame import Surface
from pygame.math import Vector2
from pygame.transform import rotozoom
import random

from utils import get_random_velocity, load_sprite, load_sound, wrap_position, image_at

UP = Vector2(0, -1)  # wektor wskazujacy do gory



class GameObject:
    def __init__(self, position: [int, int], sprite: Surface, velocity: Vector2):
        self.position = Vector2(position)
        self.sprite = sprite
        self.radius = sprite.get_width() / 2
        self.velocity = Vector2(velocity)

    def draw(self, surface: Surface):
        blit_position = self.position - Vector2(self.radius)
        surface.blit(self.sprite, blit_position)

    def move(self, surface: Surface):
        self.position = wrap_position(self.position + self.velocity, surface)

    def collides_with(self, other_obj: Any) -> bool:
        distance = self.position.distance_to(other_obj.position)
        return distance < self.radius + other_obj.radius


class Spaceship(GameObject):
    MANEUVERABILITY = 3  # turning speed
    ACCELERATION = 0.1  # acceleration speed
    MAX_SPEED = 8  # maximum speed
    BULLET_SPEED = 5  # bullet speed
    STARTING_LIVES = 3  # starting ammount of lives

    def __init__(self, position: [int, int], create_bullet_callback: Callable):
        self.create_bullet_callback = create_bullet_callback
        self.laser_sound = load_sound("laser")
        self.spaceship_hit_asteroid = load_sound("asteroid_hit")
        self.spaceship_destroy_sound = load_sound("spaceship_destroy")
        self.spaceship_hit_shielded = load_sound("shielded_hit")
      # self.default_sprite = load_sprite("spaceship")
        self.default_sprite = image_at(0,0,50,50)
        self.default_accelerating = load_sprite("spaceship_accelerating")
        self.shielded_sprite = load_sprite("spaceship_shielded")
        self.shielded_accelerating = load_sprite("spaceship_shielded_accelerating")
        self.direction = Vector2(UP)
        self.lives = self.STARTING_LIVES
        self.shotgun = False
        self.shotgunRemaining = 0
        self.isShielded = False
        self.accelerating = False

        super().__init__(position, self.default_sprite, Vector2(0))

    def rotate(self, clockwise=True):
        sign = 1 if clockwise else -1
        angle = self.MANEUVERABILITY * sign
        self.direction.rotate_ip(angle)

    def accelerate(self):
        self.velocity += self.direction * self.ACCELERATION
        if self.velocity.length() > self.MAX_SPEED:
            self.velocity.scale_to_length(self.MAX_SPEED)
        if self.isShielded:
            self.sprite = self.shielded_accelerating
        else:
            self.sprite = self.default_accelerating

    def shoot(self):
        bullet_position = self.position
        bullet_velocity = self.direction * self.BULLET_SPEED + self.velocity
        bullet = Bullet(bullet_position, bullet_velocity, 0, self.direction.angle_to(UP))
        if self.shotgun is False:
            self.create_bullet_callback(bullet)
        else:
            for i in range(-30, 31, 30):
                bullet = Bullet(bullet_position, bullet_velocity, i, self.direction.angle_to(UP) - i)
                self.create_bullet_callback(bullet)
            self.shotgunRemaining -= 1
            if self.shotgunRemaining <= 0:
                self.shotgun = False
        self.laser_sound.play()

    def draw(self, surface: Surface):
        angle = self.direction.angle_to(UP)
        rotated_surface = rotozoom(self.sprite, angle, 1.0)
        rotated_surface_size = Vector2(rotated_surface.get_size())
        blit_position = self.position - rotated_surface_size * 0.5
        surface.blit(rotated_surface, blit_position)

    def destroy(self, game) -> bool:
        if not self.isShielded:
            if self.lives > 1:
                self.lives -= 1
                self.spaceship_hit_asteroid.play()
                return False
            elif self.lives == 1:
                self.lives -= -1
                game.spaceship = None
                self.spaceship_destroy_sound.play()
                return True
        else:
            self.isShielded = False
            self.sprite = self.default_sprite
            self.spaceship_hit_shielded.play()
            return False


class Asteroid(GameObject):
    def __init__(self, position: Vector2, create_asteroid_callback: callable, size: int = 3):
        self.create_asteroid_callback = create_asteroid_callback
        self.size = size
        self.asteroid_destroy_sound = load_sound("asteroid_destroy")
        size_to_scale = {
            3: 1,
            2: 0.6,
            1: 0.3,
        }
        rotation = random.randrange(0, 360, 10)
        scale = size_to_scale[size]
        sprite = rotozoom(load_sprite("asteroid"), rotation, scale)
        super().__init__(position, sprite, get_random_velocity(1, 3))

    def split(self):
        self.asteroid_destroy_sound.play()
        if self.size > 1:
            for _ in range(2):
                asteroid = Asteroid(self.position, self.create_asteroid_callback, self.size - 1)
                self.create_asteroid_callback(asteroid)


class Bullet(GameObject):
    def __init__(self, position: Vector2, velocity: Vector2, rotation: int, sprite_rotation: float):
        sprite = rotozoom(load_sprite("bullet"), sprite_rotation, 1)
        super().__init__(position, sprite, velocity)
        # rotation of bullet when fired
        self.velocity.rotate_ip(rotation)

    def move(self, surface: Surface):
        self.position = self.position + self.velocity


class Shotgun(GameObject):
    def __init__(self, position: Vector2, ship):
        super().__init__(position, load_sprite("shotgun"), get_random_velocity(1, 3))
        self.ship = ship
        self.sound = load_sound("upgrade")

    def destroy(self):
        self.ship.shotgun = True
        self.ship.shotgunRemaining += 10
        self.sound.play()


class Shield(GameObject):
    def __init__(self, position: Vector2, ship):
        super().__init__(position, load_sprite("shield"), get_random_velocity(1, 3))
        self.ship = ship
        self.sound = load_sound("upgrade")

    def destroy(self):
        self.ship.isShielded = True
        self.ship.sprite = self.ship.shielded_sprite
        self.sound.play()
