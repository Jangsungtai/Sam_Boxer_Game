from __future__ import annotations

import math
import random
from typing import List, Tuple

import arcade


class HitParticle:
    """히트 효과를 위한 개별 파티클."""

    def __init__(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        particle_type: str,
        spawn_time: float,
        lifetime: float = 0.8,
    ) -> None:
        self.x = x
        self.y = y
        self.color = color
        self.particle_type = particle_type
        self.spawn_time = spawn_time
        self.lifetime = lifetime

        # Movement parameters based on particle type
        if particle_type == "ring":
            # Slight variation in initial radius and velocity for wave effect
            self.radius = 25.0 + random.uniform(-5.0, 5.0)
            self.radius_velocity = 180.0 + random.uniform(-20.0, 20.0)
            self.angle = 0.0
            self.angle_velocity = 0.0
        elif particle_type == "burst":
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80.0, 200.0)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.radius = random.uniform(4.0, 10.0)
        elif particle_type == "spark":
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(150.0, 350.0)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.radius = random.uniform(2.0, 4.0)
            self.length = random.uniform(15.0, 30.0)
        else:
            self.vx = 0.0
            self.vy = 0.0
            self.radius = 5.0

        self.alpha = 255
        self.size = 1.0

    def update(self, now: float, delta_time: float) -> bool:
        """파티클을 업데이트하고 살아있는지 반환합니다."""
        age = now - self.spawn_time
        if age >= self.lifetime:
            return False

        # Fade out over lifetime
        self.alpha = int(255 * (1.0 - age / self.lifetime))
        self.size = 1.0 - (age / self.lifetime) * 0.5

        if self.particle_type == "ring":
            self.radius += self.radius_velocity * delta_time
            # Slow down expansion over time
            self.radius_velocity *= 0.98
        elif self.particle_type in ("burst", "spark"):
            self.x += self.vx * delta_time
            self.y += self.vy * delta_time
            # Apply friction
            friction = 0.92 if self.particle_type == "spark" else 0.96
            self.vx *= friction
            self.vy *= friction

        return True

    def draw(self) -> None:
        """파티클을 그립니다."""
        # Fade color based on alpha (0-255)
        alpha_factor = self.alpha / 255.0
        faded_color = tuple(int(c * alpha_factor) for c in self.color)
        
        if self.particle_type == "ring":
            # Draw expanding ring with fade
            thickness = max(2, int(5 * self.size))
            if self.radius > 0 and thickness > 0 and alpha_factor > 0:
                arcade.draw_circle_outline(
                    self.x, self.y, 
                    self.radius, 
                    faded_color, 
                    thickness
                )
                # Draw inner ring for depth
                if self.radius > 20:
                    inner_radius = self.radius * 0.7
                    inner_alpha = alpha_factor * 0.6
                    inner_color = tuple(int(c * inner_alpha) for c in self.color)
                    arcade.draw_circle_outline(
                        self.x, self.y,
                        inner_radius,
                        inner_color,
                        max(1, int(thickness * 0.6))
                    )
        elif self.particle_type == "burst":
            arcade.draw_circle_filled(self.x, self.y, self.radius * self.size, faded_color)
        elif self.particle_type == "spark":
            angle = math.atan2(self.vy, self.vx) if (self.vx != 0 or self.vy != 0) else 0
            end_x = self.x + math.cos(angle) * self.length * self.size
            end_y = self.y + math.sin(angle) * self.length * self.size
            arcade.draw_line(
                self.x, self.y, end_x, end_y, faded_color, max(1, int(2 * self.size))
            )


class HitEffectSystem:
    """히트 효과 파티클 시스템."""

    def __init__(self) -> None:
        self.particles: List[HitParticle] = []

    def spawn_effect(
        self,
        x: float,
        y: float,
        judgement: str,
        color: Tuple[int, int, int],
        now: float,
    ) -> None:
        """지정된 위치에 히트 효과를 생성합니다."""
        # Convert BGR to RGB if needed (assuming color is already RGB)
        effect_color = color

        # Different effects based on judgement
        if judgement == "PERFECT":
            # Spectacular effect: multiple expanding rings + many sparks
            for _ in range(4):
                # Spawn multiple rings at once for layered wave effect
                self.particles.append(HitParticle(x, y, effect_color, "ring", now, lifetime=0.8))
            for _ in range(25):
                self.particles.append(HitParticle(x, y, effect_color, "spark", now, lifetime=0.6))
            # Add some burst particles for density
            for _ in range(10):
                self.particles.append(HitParticle(x, y, effect_color, "burst", now, lifetime=0.4))
        elif judgement == "GREAT":
            # Good effect: two rings + burst
            for _ in range(2):
                self.particles.append(HitParticle(x, y, effect_color, "ring", now, lifetime=0.6))
            for _ in range(15):
                self.particles.append(HitParticle(x, y, effect_color, "burst", now, lifetime=0.5))
        elif judgement == "GOOD":
            # Moderate effect: one ring + smaller burst
            self.particles.append(HitParticle(x, y, effect_color, "ring", now, lifetime=0.5))
            for _ in range(10):
                self.particles.append(HitParticle(x, y, effect_color, "burst", now, lifetime=0.4))
        elif judgement == "MISS":
            # Subtle effect - minimal burst with muted colors
            # Darken color for miss effect
            muted_color = tuple(int(c * 0.4) for c in effect_color)
            for _ in range(6):
                self.particles.append(HitParticle(x, y, muted_color, "burst", now, lifetime=0.25))

    def update(self, now: float, delta_time: float) -> None:
        """모든 파티클을 업데이트하고 죽은 파티클을 제거합니다."""
        self.particles = [p for p in self.particles if p.update(now, delta_time)]

    def draw(self) -> None:
        """모든 파티클을 그립니다."""
        for particle in self.particles:
            particle.draw()

    def clear(self) -> None:
        """모든 파티클을 제거합니다."""
        self.particles.clear()

