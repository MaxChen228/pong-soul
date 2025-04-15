# render.py

import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS

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

        self.skill_glow_position = 0
        self.skill_glow_trail = []
        self.max_skill_glow_trail_length = 15

    def render(self):
        freeze_active = (
            self.env.freeze_timer > 0 and
            (pygame.time.get_ticks() - self.env.freeze_timer < self.env.freeze_duration)
        )
        if freeze_active:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                self.window.fill((220,220,220))
            else:
                self.window.fill((10,10,10))
        else:
            self.window.fill(Style.BACKGROUND_COLOR)

        offset_y = self.offset_y

        # 取得當前技
        skill = self.env.skills.get(self.env.active_skill_name, None)

        # === shockwave繪製（以 slowmo_skill 為例） ===
        # 若當前技能是 slowmo
        shockwaves = []
        fog_active = False
        fog_end_time = 0
        slowmo_cfg = None

        if skill and self.env.active_skill_name == "slowmo":
            # 轉型為 slowmo_skill
            slowmo_skill = skill
            # shockwaves = slowmo_skill.shockwaves
            # fog_active = slowmo_skill.fog_active
            # fog_end_time = slowmo_skill.fog_end_time
            # or 也可直接一次拿
            shockwaves = slowmo_skill.shockwaves
            fog_active = slowmo_skill.fog_active
            fog_end_time = slowmo_skill.fog_end_time
            slowmo_cfg = SKILL_CONFIGS["slowmo"]

        if shockwaves:
            # 計算目前 fog 剩餘比例
            remaining_ratio = 1.0
            if not (skill and skill.is_active()) and fog_active:
                # 技能已結束但 fog_active 還在
                cur = pygame.time.get_ticks()
                ratio = max(0.0, (fog_end_time - cur) / slowmo_cfg["fog_duration_ms"])
                remaining_ratio = ratio

            # 繪製shockwave
            if remaining_ratio>0:
                base_fill_alpha= 80
                base_border_alpha= 200
                final_fill_alpha= int(base_fill_alpha* remaining_ratio)
                final_border_alpha= int(base_border_alpha* remaining_ratio)

                if final_fill_alpha>0 or final_border_alpha>0:
                    # 只做繪製，不做 wave["radius"]+=30（因 skill裏已做過）
                    new_list=[]
                    for wave in shockwaves:
                        # wave["radius"] ...
                        overlay= pygame.Surface((self.render_size, self.render_size+200), pygame.SRCALPHA)
                        fill_color= (50,150,255, final_fill_alpha)
                        border_color= (255,255,255, final_border_alpha)
                        pygame.draw.circle(overlay, fill_color, (wave["cx"], wave["cy"]), wave["radius"])
                        pygame.draw.circle(overlay, border_color, (wave["cx"], wave["cy"]), wave["radius"], width=6)
                        self.window.blit(overlay, (0,0))
                        # 保留
                        if final_fill_alpha>0 or final_border_alpha>0:
                            new_list.append(wave)
                    # skill.shockwaves = new_list # 你若想清到skill裏
                else:
                    shockwaves.clear()
            else:
                shockwaves.clear()

        # === UI 區域背景 ===
        ui_overlay_color = tuple(max(0,c-20) for c in Style.BACKGROUND_COLOR)
        if skill and skill.is_active() and self.env.active_skill_name=="slowmo":
            ui_overlay_color = (20,20,100)
        pygame.draw.rect(self.window, ui_overlay_color, (0,0,self.render_size,offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y+self.render_size, self.render_size, offset_y))

        # 球與板子
        cx= int(self.env.ball_x*self.render_size)
        cy= int(self.env.ball_y*self.render_size)+ offset_y
        px= int(self.env.player_x*self.render_size)
        ax= int(self.env.ai_x*self.render_size)

        # 全局球拖尾
        for i,(tx,ty) in enumerate(self.env.trail):
            fade= int(255*(i+1)/len(self.env.trail))
            color= (*Style.BALL_COLOR, fade)
            t_s= pygame.Surface((self.render_size, self.render_size+200), pygame.SRCALPHA)
            pygame.draw.circle(t_s, color, (int(tx*self.render_size),int(ty*self.render_size)+ offset_y),4)
            self.window.blit(t_s,(0,0))

        # 球旋轉
        self.ball_angle += self.env.spin*12
        rotated= pygame.transform.rotate(self.ball_image, self.ball_angle)
        rect= rotated.get_rect(center=(cx,cy))
        self.window.blit(rotated, rect)

        # slowmo 技能殘影：從 skill.player_trail
        if skill and self.env.active_skill_name=="slowmo" and skill.is_active():
            slowmo_cfg= SKILL_CONFIGS["slowmo"]
            sm_color= slowmo_cfg["trail_color"]
            slowmo_skill= skill
            for i,trx in enumerate(slowmo_skill.player_trail):
                fade_ratio= (i+1)/ len(slowmo_skill.player_trail)
                alpha= int(200* fade_ratio)
                sur= pygame.Surface((self.env.player_paddle_width, self.env.paddle_height), pygame.SRCALPHA)
                sur.fill((*sm_color, alpha))
                r= sur.get_rect(center=(
                    int(trx*self.render_size),
                    offset_y+ self.render_size- self.env.paddle_height//2
                ))
                self.window.blit(sur, r)

        # 板子
        paddle_color= self.env.paddle_color or Style.PLAYER_COLOR
        pygame.draw.rect(self.window, paddle_color,
            (px- self.env.player_paddle_width//2,
             offset_y+ self.render_size- self.env.paddle_height,
             self.env.player_paddle_width, self.env.paddle_height),
             border_radius=8
        )
        pygame.draw.rect(self.window, Style.AI_COLOR,
            (ax- self.env.ai_paddle_width//2,
             offset_y,
             self.env.ai_paddle_width, self.env.paddle_height)
        )

        # 血條
        bar_w, bar_h, space= 150,20,20
        now=pygame.time.get_ticks()
        # AI
        pygame.draw.rect(self.window, Style.AI_BAR_BG, (
            self.render_size- bar_w- space,
            space,
            bar_w, bar_h
        ))
        ai_flash= (now- self.env.last_ai_hit_time< self.env.freeze_duration)
        ai_bar_fill= (255,255,255) if (ai_flash and (now//100%2==0)) else Style.AI_BAR_FILL
        pygame.draw.rect(self.window, ai_bar_fill, (
            self.render_size- bar_w- space,
            space,
            bar_w*(self.env.ai_life/self.env.ai_max_life),
            bar_h
        ))

        # Player
        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG,
            (space, self.render_size+offset_y+space, bar_w, bar_h))
        player_flash= (now- self.env.last_player_hit_time < self.env.freeze_duration)
        player_fill= (255,255,255) if (player_flash and (now//100%2==0)) else Style.PLAYER_BAR_FILL
        pygame.draw.rect(self.window, player_fill, (
            space,
            self.render_size+ offset_y+ space,
            bar_w*(self.env.player_life/self.env.player_max_life),
            bar_h
        ))

        # 技能條
        if skill:
            slow_bar_w, slow_bar_h, sp= 100,10,20
            slow_bar_x= self.render_size - slow_bar_w- sp
            slow_bar_y= self.render_size + offset_y+ self.env.paddle_height+ sp
            pygame.draw.rect(self.window,(50,50,50),(slow_bar_x, slow_bar_y, slow_bar_w, slow_bar_h))

            skill_cfg= SKILL_CONFIGS[self.env.active_skill_name]
            bar_color= skill_cfg.get("bar_color",(255,255,255))
            ratio= skill.get_energy_ratio()
            pygame.draw.rect(self.window, bar_color,
                (slow_bar_x, slow_bar_y, slow_bar_w* ratio, slow_bar_h)
            )

            cd= skill.get_cooldown_seconds()
            if (not skill.is_active()) and cd>0:
                cd_txt= f"{cd:.1f}"
                fnt= Style.get_font(14)
                cd_surf= fnt.render(cd_txt, True, Style.TEXT_COLOR)
                cd_rect= cd_surf.get_rect(center=(slow_bar_x+ slow_bar_w/2, slow_bar_y+ slow_bar_h+15))
                self.window.blit(cd_surf, cd_rect)

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()
