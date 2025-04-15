import math

def collide_sphere_with_moving_plane(vn, vt, u, omega, e, mu, m, R):
    """
    模擬球與移動平面碰撞，產生反彈、切向摩擦與角速度變化。
    """
    vn_post = - e * vn
    Jn = m * (1 + e) * abs(vn)
    I = (2/5) * m * R**2
    Jt_star = (2*m/7.0) * (u + R*omega - vt)
    max_friction_impulse = mu * Jn

    if abs(Jt_star) <= max_friction_impulse:
        Jt = Jt_star
    else:
        vrel = (vt - u) - R*omega
        sign_vrel = math.copysign(1, vrel)
        Jt = - max_friction_impulse * sign_vrel

    vt_post = vt + (Jt / m)
    omega_post = omega - (R * Jt) / I

    return vn_post, vt_post, omega_post


def simulate_collision_standard(vx, vy, omega, e, mu, m, R):
    """
    真實球撞牆模型：含滑動/黏著判斷 + 摩擦影響。
    vx: 法向速度（撞進去是負）
    vy: 切向速度（平行板面）
    omega: 球角速度（正 = 逆時針）
    """
    vx_prime = -e * vx
    required = (2/7)*abs(R*omega - vy)
    available = mu*(1+e)*abs(vx)
    I = (2/5)*m*R**2

    if required <= available:
        J_t = (2 * m / 7) * (R * omega - vy)
        vy_prime = vy + J_t/m
        omega_prime = omega - (R * J_t)/I
    else:
        sign = math.copysign(1, (vy - R*omega))
        J_t = - mu * m * (1+e) * abs(vx) * sign
        vy_prime = vy + J_t/m
        omega_prime = omega - (R * J_t)/I

    return vx_prime, vy_prime, omega_prime

def handle_paddle_collision(
    ball_x, ball_y,
    old_ball_y,
    ball_vx, ball_vy,
    spin,
    paddle_x, paddle_y, prev_paddle_x,
    paddle_width,
    radius,
    time_scale,
    mass, R, e, mu,
    is_ai=False
):
    """
    統一處理「球 與 AI擋板 or 玩家擋板」的碰撞。
    回傳:
      (ball_x, ball_y, ball_vx, ball_vy, spin, collided_bool)
      collided_bool 表示本幀是否真的撞到擋板
    is_ai=True => 表示AI擋板(上方), False => 玩家擋板(下方)
    """

    # 1) 判斷是否穿越到擋板那邊
    collided = False
    if is_ai:
        # AI擋板在 paddle_y 上方
        # 若舊 y > paddle_y, 新 y <= paddle_y => 可能撞到
        if old_ball_y > paddle_y and ball_y <= paddle_y:
            # 是否 x範圍內
            half_w = paddle_width / 2
            if abs(ball_x - paddle_x) < half_w + radius:
                # 撞到
                collided = True
                # 校正 y，避免穿透
                ball_y = paddle_y

                # 計算 vn, vt, u
                vn = ball_vy   # 上方擋板 => normal朝下 => ball_vy 即 vn
                vt = ball_vx
                u = (paddle_x - prev_paddle_x) / time_scale
                # 呼叫原 collide_sphere_with_moving_plane
                from game.physics import collide_sphere_with_moving_plane
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, spin, e, mu, mass, R
                )
                ball_vy = vn_post
                ball_vx = vt_post
                spin = omega_post

    else:
        # 玩家擋板(下方)
        # 若舊 y < paddle_y, 新 y >= paddle_y => 可能撞到
        if old_ball_y < paddle_y and ball_y >= paddle_y:
            half_w = paddle_width / 2
            if abs(ball_x - paddle_x) < half_w + radius:
                collided = True
                ball_y = paddle_y

                vn = -ball_vy   # 下方擋板 => normal朝上 => ball_vy>0 => vn = -ball_vy
                vt = ball_vx
                u = (paddle_x - prev_paddle_x) / time_scale
                from game.physics import collide_sphere_with_moving_plane
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, spin, e, mu, mass, R
                )
                ball_vy = -vn_post
                ball_vx = vt_post
                spin = omega_post

    return (ball_x, ball_y, ball_vx, ball_vy, spin, collided)
