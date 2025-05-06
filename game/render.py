# render.py

import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path # <--- 加入這行

class Renderer:
    def __init__(self, env):
        pygame.init()
        self.env = env
        self.render_size = env.render_size
        self.offset_y = 100
        self.window = pygame.display.set_mode((self.render_size, self.render_size + 2*self.offset_y))
        self.clock = pygame.time.Clock()
        self.ball_image = pygame.transform.smoothscale(
            pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha(), # <--- 修改這裡
            (env.ball_radius*2, env.ball_radius*2)
        )
        self.ball_angle = 0

        # 共用的 技能條特效
        self.skill_glow_position = 0
        self.skill_glow_trail = []
        self.max_skill_glow_trail_length = 15

    def render(self):
        freeze_active = (
            self.env.freeze_timer>0
            and (pygame.time.get_ticks() - self.env.freeze_timer< self.env.freeze_duration)
        )
        if freeze_active:
            if (pygame.time.get_ticks()//100)%2==0:
                self.window.fill((220,220,220))
            else:
                self.window.fill((10,10,10))
        else:
            self.window.fill(Style.BACKGROUND_COLOR)

        offset_y = self.offset_y

        # 先繪製最基礎 UI(上下區塊)
        active_skill= self.env.skills.get(self.env.active_skill_name, None)
        ui_overlay_color= tuple(max(0,c-20) for c in Style.BACKGROUND_COLOR)
        pygame.draw.rect(self.window, ui_overlay_color, (0,0,self.render_size,offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y+self.render_size, self.render_size, offset_y))

        # === 球與板子位置 ===
        cx= int(self.env.ball_x* self.render_size)
        cy= int(self.env.ball_y* self.render_size)+ offset_y
        px= int(self.env.player_x* self.render_size)
        ax= int(self.env.ai_x* self.render_size)

        # 全局拖尾
        for i, (tx,ty) in enumerate(self.env.trail):
            fade= int(255*(i+1)/ len(self.env.trail))
            color= (*Style.BALL_COLOR, fade)
            t_surf= pygame.Surface((self.render_size, self.render_size+200), pygame.SRCALPHA)
            pygame.draw.circle(t_surf, color, (int(tx*self.render_size), int(ty*self.render_size)+ offset_y),4)
            self.window.blit(t_surf,(0,0))

        # 球旋轉
        self.ball_angle+= self.env.spin*12
        rotated_ball= pygame.transform.rotate(self.ball_image, self.ball_angle)
        rect= rotated_ball.get_rect(center=(cx,cy))
        self.window.blit(rotated_ball, rect)

        # === (A) 在畫板子 **之前**，先呼叫 skill.render() ===
        # 讓slowmo的殘影 / shockwave 畫在底層
        for skill in self.env.skills.values():
            skill.render(self.window)

        # === 再來畫玩家 & AI擋板 (在特效之上) ===
        paddle_color= self.env.paddle_color or Style.PLAYER_COLOR
        pygame.draw.rect(self.window, paddle_color,
            (px- self.env.player_paddle_width//2,
             offset_y+ self.render_size- self.env.paddle_height,
             self.env.player_paddle_width,self.env.paddle_height),
            border_radius=8
        )
        pygame.draw.rect(self.window, Style.AI_COLOR,
            (ax- self.env.ai_paddle_width//2,
             offset_y, self.env.ai_paddle_width,self.env.paddle_height)
        )

        # 血條
        bar_w, bar_h, sp= 150,20,20
        cur= pygame.time.get_ticks()

        # AI
        pygame.draw.rect(self.window, Style.AI_BAR_BG,
            (self.render_size- bar_w- sp, sp, bar_w, bar_h)
        )
        ai_flash= (cur- self.env.last_ai_hit_time< self.env.freeze_duration)
        ai_fill= (255,255,255) if (ai_flash and (cur//100%2==0)) else Style.AI_BAR_FILL
        pygame.draw.rect(self.window, ai_fill, (
            self.render_size- bar_w- sp,
            sp,
            bar_w*(self.env.ai_life/ self.env.ai_max_life), bar_h
        ))

        # Player
        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG,
            (sp, self.render_size+ offset_y+ sp, bar_w, bar_h)
        )
        player_flash= (cur- self.env.last_player_hit_time< self.env.freeze_duration)
        player_fill= (255,255,255) if (player_flash and (cur//100%2==0)) else Style.PLAYER_BAR_FILL
        pygame.draw.rect(self.window, player_fill, (
            sp, self.render_size+ offset_y+ sp,
            bar_w*(self.env.player_life/ self.env.player_max_life), bar_h
        ))

        # 技能能量條(通用)
        if active_skill:
            slow_bar_w, slow_bar_h, spc= 100,10,20
            slow_bar_x= self.render_size- slow_bar_w- spc
            slow_bar_y= self.render_size+ offset_y+ self.env.paddle_height+ spc
            pygame.draw.rect(self.window,(50,50,50),(slow_bar_x, slow_bar_y, slow_bar_w, slow_bar_h))

            from game.skills.skill_config import SKILL_CONFIGS
            skill_cfg= SKILL_CONFIGS[self.env.active_skill_name]
            bar_color= skill_cfg.get("bar_color",(255,255,255))
            ratio= active_skill.get_energy_ratio()
            pygame.draw.rect(self.window, bar_color,
                (slow_bar_x, slow_bar_y, slow_bar_w*ratio, slow_bar_h)
            )

            cd_sec= active_skill.get_cooldown_seconds()
            if (not active_skill.is_active()) and cd_sec>0:
                txt= f"{cd_sec:.1f}"
                fnt= Style.get_font(14)
                surf= fnt.render(txt, True, Style.TEXT_COLOR)
                r= surf.get_rect(center=(slow_bar_x+ slow_bar_w/2, slow_bar_y+ slow_bar_h+15))
                self.window.blit(surf, r)

            # 若能量滿, 顯示追跡特效
            if active_skill.has_full_energy_effect():
                glow_rect= pygame.Rect(slow_bar_x-2, slow_bar_y-2, slow_bar_w+4, slow_bar_h+4)
                self.skill_glow_position= (self.skill_glow_position+8)%((glow_rect.width+ glow_rect.height)*2)
                pos= self.skill_glow_position

                if pos<= glow_rect.width:
                    glow_pos= (glow_rect.x+ pos, glow_rect.y)
                elif pos<= glow_rect.width+ glow_rect.height:
                    glow_pos= (glow_rect.x+ glow_rect.width, glow_rect.y+ (pos- glow_rect.width))
                elif pos<= glow_rect.width*2+ glow_rect.height:
                    glow_pos= (
                        glow_rect.x+ glow_rect.width- (pos- glow_rect.width- glow_rect.height),
                        glow_rect.y+ glow_rect.height
                    )
                else:
                    glow_pos= (
                        glow_rect.x,
                        glow_rect.y+ glow_rect.height- (pos- 2* glow_rect.width- glow_rect.height)
                    )

                self.skill_glow_trail.append(glow_pos)
                if len(self.skill_glow_trail)> self.max_skill_glow_trail_length:
                    self.skill_glow_trail.pop(0)

                pygame.draw.rect(self.window, bar_color,
                    (slow_bar_x, slow_bar_y, slow_bar_w*ratio, slow_bar_h)
                )
                if (not active_skill.is_active()) and cd_sec>0:
                    txt= f"{cd_sec:.1f}"
                    fnt= Style.get_font(14)
                    surf= fnt.render(txt, True, Style.TEXT_COLOR)
                    r= surf.get_rect(center=(slow_bar_x+ slow_bar_w/2, slow_bar_y+ slow_bar_h+15))
                    self.window.blit(surf, r)

                for i,pos2 in enumerate(self.skill_glow_trail):
                    alpha= int(255*(i+1)/ len(self.skill_glow_trail))
                    t_color= (255,255,255, alpha)
                    t_s= pygame.Surface((self.render_size, self.render_size+200), pygame.SRCALPHA)
                    pygame.draw.circle(t_s, t_color, pos2,4)
                    self.window.blit(t_s,(0,0))
            else:
                self.skill_glow_position=0
                self.skill_glow_trail.clear()

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()
