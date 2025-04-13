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
