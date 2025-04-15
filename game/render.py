# game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS  # <<< 新增，引入我們的技能參數

class Renderer:
    def __init__(self, env):
        pygame.init()
        self.env = env
        self.render_size = env.render_size
        self.offset_y = 100
        self.window = pygame.display.set_mode((self.render_size, self.render_size + 2 * self.offset_y))
        self.clock = pygame.time.Clock()
        self.ball_image = pygame.transform.smoothscale(
            pygame.image.load("assets/sunglasses.png").convert_alpha(),
            (env.ball_radius * 2, env.ball_radius * 2)
        )
        self.ball_angle = 0

        # 技能條追跡 & 殘影相關
        self.skill_glow_position = 0
        self.skill_glow_trail = []
        self.max_skill_glow_trail_length = 15

    def render(self):
        freeze_active = (
            self.env.freeze_timer > 0 
            and pygame.time.get_ticks() - self.env.freeze_timer < self.env.freeze_duration
        )
        if freeze_active:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                flash_color = (220, 220, 220) 
                self.window.fill(flash_color)
            else:
                self.window.fill((10, 10, 10))
        else:
            self.window.fill(Style.BACKGROUND_COLOR)

        offset_y = self.offset_y

        # === 衝擊波觸發 ===
        active_skill = self.env.skills.get(self.env.active_skill_name)
        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":
            if not hasattr(self.env, 'shockwaves'):
                self.env.shockwaves = []
            if not hasattr(self.env, 'last_slowmo_frame'):
                self.env.last_slowmo_frame = 0

            if self.env.last_slowmo_frame <= 0:
                cx = int(self.env.player_x * self.render_size)
                cy = int((1 - self.env.paddle_height / self.render_size) * self.render_size + offset_y)
                self.env.shockwaves.append({"cx": cx, "cy": cy, "radius": 0})
                self.env.last_slowmo_frame = 1
            else:
                self.env.last_slowmo_frame += 1
        else:
            self.env.last_slowmo_frame = 0

        # --- 修正後的衝擊波繪製與淡出 ---
        if hasattr(self.env, 'shockwaves') and self.env.shockwaves:
            current_time = pygame.time.get_ticks()
            active_skill = self.env.skills.get(self.env.active_skill_name)

            # 若 slowmo 結束 => 霧氣淡出
            remaining_ratio = 1.0
            if self.env.slowmo_fog_active and active_skill and not active_skill.is_active():
                # 過去用 GameSettings.SLOWMO_FOG_DURATION_MS，改用 skill_config
                slowmo_cfg = SKILL_CONFIGS["slowmo"]
                fog_ms = slowmo_cfg["fog_duration_ms"]
                remaining_ratio = max(0.0, (self.env.slowmo_fog_end_time - current_time) / fog_ms)

            if remaining_ratio > 0:
                base_fill_alpha = 80
                base_border_alpha = 200
                final_fill_alpha = int(base_fill_alpha * remaining_ratio)
                final_border_alpha = int(base_border_alpha * remaining_ratio)

                if final_fill_alpha > 0 or final_border_alpha > 0:
                    next_shockwaves = []
                    for shockwave in self.env.shockwaves:
                        shockwave["radius"] += 30

                        overlay = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
                        fill_color = (50, 150, 255, final_fill_alpha)
                        border_color = (255, 255, 255, final_border_alpha)
                        pygame.draw.circle(overlay, fill_color, (shockwave["cx"], shockwave["cy"]), shockwave["radius"])
                        pygame.draw.circle(overlay, border_color, (shockwave["cx"], shockwave["cy"]), shockwave["radius"], width=6)
                        self.window.blit(overlay, (0, 0))

                        if final_fill_alpha > 0 or final_border_alpha > 0:
                            next_shockwaves.append(shockwave)

                    self.env.shockwaves = next_shockwaves
                else:
                    if hasattr(self.env, 'shockwaves'):
                        self.env.shockwaves.clear()
            else:
                if hasattr(self.env, 'shockwaves'):
                    self.env.shockwaves.clear()

        # === UI 區域背景 ===
        active_skill = self.env.skills.get(self.env.active_skill_name)
        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":
            ui_overlay_color = (20, 20, 100)
        else:
            ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)

        pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.render_size, offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y + self.render_size, self.render_size, offset_y))

        # === 球與板子位置 ===
        cx = int(self.env.ball_x * self.render_size)
        cy = int(self.env.ball_y * self.render_size) + offset_y
        px = int(self.env.player_x * self.render_size)
        ax = int(self.env.ai_x * self.render_size)

        # --- 拖尾渲染 ---
        for i, (tx, ty) in enumerate(self.env.trail):
            fade = int(255 * (i + 1) / len(self.env.trail))
            trail_color = (*Style.BALL_COLOR, fade)
            trail_surface = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, trail_color, (int(tx * self.render_size), int(ty * self.render_size) + offset_y), 4)
            self.window.blit(trail_surface, (0, 0))

        # 球旋轉
        self.ball_angle += self.env.spin * 12
        rotated_ball = pygame.transform.rotate(self.ball_image, self.ball_angle)
        rotated_rect = rotated_ball.get_rect(center=(cx, cy))
        self.window.blit(rotated_ball, rotated_rect)

        # === slowmo 技能板子殘影 ===
        active_skill = self.env.skills.get(self.env.active_skill_name, None)
        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":
            # 取 slowmo 的 trail_color
            slowmo_cfg = SKILL_CONFIGS["slowmo"]
            sm_trail_color = slowmo_cfg["trail_color"]

            for i, trail_x in enumerate(self.env.player_trail):
                fade_ratio = (i + 1) / len(self.env.player_trail)
                trail_alpha = int(200 * fade_ratio)

                trail_surface = pygame.Surface(
                    (self.env.player_paddle_width, self.env.paddle_height),
                    pygame.SRCALPHA
                )
                # 改用 slowmo_cfg["trail_color"]
                trail_color = (*sm_trail_color, trail_alpha)
                trail_surface.fill(trail_color)

                trail_rect = trail_surface.get_rect(center=(
                    int(trail_x * self.render_size),
                    offset_y + self.render_size - self.env.paddle_height // 2
                ))
                self.window.blit(trail_surface, trail_rect)

        # === 繪製玩家 & AI 擋板 ===
        paddle_color = self.env.paddle_color or Style.PLAYER_COLOR
        pygame.draw.rect(self.window, paddle_color, (
            px - self.env.player_paddle_width // 2,
            offset_y + self.render_size - self.env.paddle_height,
            self.env.player_paddle_width,
            self.env.paddle_height
        ), border_radius=8)

        pygame.draw.rect(self.window, Style.AI_COLOR, (
            ax - self.env.ai_paddle_width // 2,
            offset_y,
            self.env.ai_paddle_width,
            self.env.paddle_height
        ))

        # === 血條顯示 ===
        bar_width, bar_height, spacing = 150, 20, 20
        current_time = pygame.time.get_ticks()

        # AI 血條
        pygame.draw.rect(self.window, Style.AI_BAR_BG, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width,
            bar_height
        ))
        ai_flash = current_time - self.env.last_ai_hit_time < self.env.freeze_duration
        ai_bar_color = (255, 255, 255) if ai_flash and (current_time // 100 % 2 == 0) else Style.AI_BAR_FILL
        pygame.draw.rect(self.window, ai_bar_color, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width * (self.env.ai_life / self.env.ai_max_life),
            bar_height
        ))

        # 玩家血條
        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width,
            bar_height
        ))
        player_flash = current_time - self.env.last_player_hit_time < self.env.freeze_duration
        player_bar_color = (255, 255, 255) if player_flash and (current_time // 100 % 2 == 0) else Style.PLAYER_BAR_FILL
        pygame.draw.rect(self.window, player_bar_color, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width * (self.env.player_life / self.env.player_max_life),
            bar_height
        ))

        # === 技能條繪製 ===
        slow_bar_width, slow_bar_height, slow_bar_spacing = 100, 10, 20
        slow_bar_x = self.render_size - slow_bar_width - slow_bar_spacing
        slow_bar_y = self.render_size + offset_y + self.env.paddle_height + slow_bar_spacing
        pygame.draw.rect(self.window, (50, 50, 50), (slow_bar_x, slow_bar_y, slow_bar_width, slow_bar_height))
        
        active_skill = self.env.skills[self.env.active_skill_name]
        skill_name = self.env.active_skill_name
        skill_cfg = SKILL_CONFIGS[skill_name]

        # 原本 referencing GameSettings.SLOWMO_BAR_COLOR / LONG_PADDLE_BAR_COLOR
        # 改成 skill_cfg["bar_color"]
        bar_color = skill_cfg.get("bar_color", (255, 255, 255))

        # 技能能量比例
        energy_ratio = active_skill.get_energy_ratio()
        pygame.draw.rect(
            self.window,
            bar_color,
            (slow_bar_x, slow_bar_y, slow_bar_width * energy_ratio, slow_bar_height)
        )

        # 顯示冷卻時間
        cooldown_seconds = active_skill.get_cooldown_seconds()
        if not active_skill.is_active() and cooldown_seconds > 0:
            cooldown_text = f"{cooldown_seconds:.1f}"
            cooldown_font = Style.get_font(14)
            cooldown_surface = cooldown_font.render(cooldown_text, True, Style.TEXT_COLOR)
            cooldown_rect = cooldown_surface.get_rect(center=(
                slow_bar_x + slow_bar_width / 2,
                slow_bar_y + slow_bar_height + 15
            ))
            self.window.blit(cooldown_surface, cooldown_rect)

        # === 技能條滿能量時的追跡線效果 ===
        if active_skill.has_full_energy_effect():
            glow_rect = pygame.Rect(slow_bar_x - 2, slow_bar_y - 2, slow_bar_width + 4, slow_bar_height + 4)
            self.skill_glow_position = (self.skill_glow_position + 8) % ((glow_rect.width + glow_rect.height) * 2)
            pos = self.skill_glow_position

            if pos <= glow_rect.width:
                glow_pos = (glow_rect.x + pos, glow_rect.y)
            elif pos <= glow_rect.width + glow_rect.height:
                glow_pos = (glow_rect.x + glow_rect.width, glow_rect.y + (pos - glow_rect.width))
            elif pos <= glow_rect.width * 2 + glow_rect.height:
                glow_pos = (
                    glow_rect.x + glow_rect.width - (pos - glow_rect.width - glow_rect.height),
                    glow_rect.y + glow_rect.height
                )
            else:
                glow_pos = (
                    glow_rect.x,
                    glow_rect.y + glow_rect.height - (pos - 2 * glow_rect.width - glow_rect.height)
                )

            self.skill_glow_trail.append(glow_pos)
            if len(self.skill_glow_trail) > self.max_skill_glow_trail_length:
                self.skill_glow_trail.pop(0)

            # 再畫一次能量條(疊加特效)
            pygame.draw.rect(
                self.window,
                bar_color,
                (slow_bar_x, slow_bar_y, slow_bar_width * energy_ratio, slow_bar_height)
            )

            # 顯示冷卻
            if not active_skill.is_active() and cooldown_seconds > 0:
                cooldown_text = f"{cooldown_seconds:.1f}"
                cooldown_font = Style.get_font(14)
                cooldown_surface = cooldown_font.render(cooldown_text, True, Style.TEXT_COLOR)
                cooldown_rect = cooldown_surface.get_rect(center=(
                    slow_bar_x + slow_bar_width / 2,
                    slow_bar_y + slow_bar_height + 15
                ))
                self.window.blit(cooldown_surface, cooldown_rect)

            # 拖曳殘影效果
            for i, pos in enumerate(self.skill_glow_trail):
                alpha = int(255 * (i + 1) / len(self.skill_glow_trail))
                trail_color = (255, 255, 255, alpha)
                trail_surface = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
                pygame.draw.circle(trail_surface, trail_color, pos, 4)
                self.window.blit(trail_surface, (0, 0))
        else:
            self.skill_glow_position = 0
            self.skill_glow_trail.clear()

        # === Slowmo技能時鐘特效 ===
        active_skill = self.env.skills.get(self.env.active_skill_name)
        current_time = pygame.time.get_ticks()

        should_draw_clock = False
        if active_skill and self.env.active_skill_name == "slowmo":
            if active_skill.is_active():
                should_draw_clock = True
            elif self.env.slowmo_fog_active:
                should_draw_clock = True

        if should_draw_clock:
            clock_alpha_ratio = 1.0
            if not active_skill.is_active() and self.env.slowmo_fog_active:
                # 讀取 slowmo 的 fog_ms
                slowmo_cfg = SKILL_CONFIGS["slowmo"]
                fog_ms = slowmo_cfg["fog_duration_ms"]
                clock_alpha_ratio = max(0.0, (self.env.slowmo_fog_end_time - current_time) / fog_ms)

            # ❶ 改：不再用 GameSettings，直接取 slowmo_cfg
            slowmo_cfg = SKILL_CONFIGS["slowmo"]
            base_clock_color_rgb = slowmo_cfg["clock_color"][:3]
            base_clock_alpha = slowmo_cfg["clock_color"][3]

            final_clock_alpha = int(base_clock_alpha * clock_alpha_ratio)
            if final_clock_alpha > 0:
                energy_ratio = active_skill.get_energy_ratio() if active_skill.is_active() else 0
                angle_deg = (1 - energy_ratio) * 360
                angle_rad = math.radians(angle_deg)

                # ❷ 改：用 slowmo_cfg["clock_radius"]
                clock_radius = slowmo_cfg["clock_radius"]

                clock_surface = pygame.Surface((clock_radius * 2 + 10, clock_radius * 2 + 10), pygame.SRCALPHA)
                final_clock_color = (*base_clock_color_rgb, final_clock_alpha)

                pygame.draw.circle(
                    clock_surface,
                    final_clock_color,
                    (clock_radius + 5, clock_radius + 5),
                    clock_radius
                )

                final_needle_alpha = int(255 * clock_alpha_ratio)
                final_needle_color = (255, 255, 255, final_needle_alpha)

                # ❸ 改：用 clock_radius
                needle_length = clock_radius - 5
                needle_end_pos = (
                    (clock_radius + 5) + needle_length * math.cos(angle_rad - math.pi/2),
                    (clock_radius + 5) + needle_length * math.sin(angle_rad - math.pi/2)
                )

                # ❹ 改：用 slowmo_cfg["clock_line_width"]
                pygame.draw.line(
                    clock_surface,
                    final_needle_color,
                    (clock_radius + 5, clock_radius + 5),
                    needle_end_pos,
                    slowmo_cfg["clock_line_width"]
                )

                clock_rect = clock_surface.get_rect(center=(self.render_size // 2, self.render_size // 2))
                self.window.blit(clock_surface, clock_rect)

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()
