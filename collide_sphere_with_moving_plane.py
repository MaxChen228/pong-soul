import math
def collide_sphere_with_moving_plane(vn, vt, u, omega, e, mu, m, R):
    """
    模擬剛體球(均質實心) 與可在切向方向以速度 u 移動的平面碰撞。
    
    輸入參數：
      vn    : 碰撞前球在法向 n 上的速度 (標量)，朝向平面可為負。
      vt    : 碰撞前球在切向 t 上的速度 (標量)。
      u     : 平面在切向 t 方向的速度 (標量)；假設不因碰撞改變。
      omega : 碰撞前球的角速度 (正值表示逆時針轉動)。
      e     : 法向恢復係數，0~1。
      mu    : 摩擦係數。
      m     : 球的質量 (kg)。
      R     : 球的半徑 (m)。
    
    輸出 (vn_post, vt_post, omega_post)：
      vn_post    : 碰撞後球在法向 n 的速度。
      vt_post    : 碰撞後球在切向 t 的速度。
      omega_post : 碰撞後球的角速度。
    
    假設：
      1) 平面在法向方向固定，故法向速度更新為 vn' = - e vn。
      2) 球為均質實心球，轉動慣量 I = (2/5)*m*R^2。
      3) 摩擦力瞬時作用，並可取到最大靜摩擦，若不足則發生滑動。
      4) 若發生滑動，摩擦達飽和值 mu*m(1+e)*|vn|。
      5) 正角速度 omega 表示逆時針方向，則接觸點對切向的貢獻 = -R*omega。
    """
    
    # 法向速度直接更新
    vn_post = - e * vn
    
    # 法向衝量（用於計算最大摩擦量）
    Jn = m * (1 + e) * abs(vn)   # 大小
    
    # 轉動慣量（均質實心球）
    I = (2/5) * m * R**2
    
    # 嘗試"無滑動"所需的摩擦脈衝
    # 無滑動條件: (v_t' - u) - R*omega' = 0
    # => J_t^* = 2m/7 * [u + R*omega - v_t]
    Jt_star = (2*m/7.0) * (u + R*omega - vt)
    
    # 摩擦最大可提供衝量
    max_friction_impulse = mu * Jn
    
    # 判斷是否能黏著（無滑）
    if abs(Jt_star) <= max_friction_impulse:
        # -- 無滑動情形 --
        Jt = Jt_star
    else:
        # -- 滑動情形 -- (摩擦衝量取達飽和值, 方向與接觸點相對運動相反)
        # 相對切向速度(碰撞前) = (vt - u) - R*omega
        vrel = (vt - u) - R*omega
        sign_vrel = math.copysign(1, vrel)
        Jt = - max_friction_impulse * sign_vrel
    
    # 根據 Jt 更新切向速度與角速度
    vt_post = vt + (Jt / m)
    omega_post = omega - (R * Jt) / I
    
    return vn_post, vt_post, omega_post



if __name__ == "__main__":
    # 一些參數
    v_n = -2.0      # 法向速度 (例如: 往下/往負 n 方向)
    v_t = 1.0       # 切向速度
    u   = 0.5       # 平面在切向方向速度 (例如地板在 t 方向以 0.5 m/s 移動)
    omega = -20     # 球的逆時針角速度
    e = 1         # 恢復係數
    mu = 0.4        # 摩擦係數
    m = 1.0         # 質量 (kg)
    R = 0.1         # 半徑 (m)
    
    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
        v_n, v_t, u, omega, e, mu, m, R
    )
    
    print("碰撞後:")
    print(f"  vn'    = {vn_post:.3f} m/s")
    print(f"  vt'    = {vt_post:.3f} m/s")
    print(f"  omega' = {omega_post:.3f} rad/s")
