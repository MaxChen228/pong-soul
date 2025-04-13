import math
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.patches import Circle

def simulate_collision_standard(vx, vy, omega, e, mu, m, R):
    """
    標準定義：正角速度表示逆時針旋轉。
    
    接觸點由平移與旋轉共同決定，其中自轉對接觸點的貢獻為 -R*omega，
    因此接觸點的切向（y方向）速度為: v_y - R*omega.
    
    要求碰撞後無滑，則必須滿足:
      v_y' - R*omega' = 0.
    
    更新過程：
      (1) 平面法向： v_x' = -e * vx.
      (2) 黏著（無滑）情形下所需摩擦脈衝:
             J_t* = (2m/7)*(R*omega - v_y).
          黏著條件要求:
             (2/7)|R*omega - v_y| <= mu*(1+e)*|vx|.
          此時更新：
             v_y' = v_y + J_t*/m = (5/7)*v_y + (2/7)*R*omega,
             omega' = omega - (R*J_t*)/I = (2/7)*omega + (5/(7*R))*v_y.
      (3) 如果不滿足上述黏著條件，則處於滑動情形，
          此時選取摩擦脈衝達到極限:
             J_t = -mu * m*(1+e)*|vx| * sign(v_y - R*omega),
          更新:
             v_y' = v_y + J_t/m,
             omega' = omega - (R*J_t)/I.
             
    輸入參數:
       vx, vy, omega : 碰撞前平移速度（m/s）及角速度（rad/s）
       e: 彈性係數 (0<=e<=1)
       mu: 摩擦係數
       m: 質量 (kg)
       R: 球半徑 (m)
    
    輸出:
       vx_prime, vy_prime, omega_prime : 碰撞後參數.
    """
    # 法向更新（碰撞後球心 x 速度）
    vx_prime = -e * vx

    # 黏著條件檢查：要求 (2/7)|R*omega - v_y| <= mu*(1+e)*|vx|
    required = (2/7)*abs(R*omega - vy)
    available = mu*(1+e)*abs(vx)
    
    I = (2/5)*m*R**2  # 轉動慣量

    if required <= available:
        # 黏著（無滑）情形：直接使用解析解
        J_t = (2 * m / 7) * (R * omega - vy)
        vy_prime = vy + J_t/m  # = (5/7)*v_y + (2/7)*R*omega
        omega_prime = omega - (R * J_t)/I  # = (2/7)*omega + (5/(7*R))*v_y
    else:
        # 滑動情形：摩擦力達到極限值
        sign = math.copysign(1, (vy - R*omega))
        J_t = - mu * m * (1+e) * abs(vx) * sign
        vy_prime = vy + J_t/m
        omega_prime = omega - (R * J_t)/I

    return vx_prime, vy_prime, omega_prime

# ------------------- 模擬與動畫參數 -------------------
# 碰撞參數
e = 0.8       # 彈性係數
mu = 0.8      # 摩擦係數
m = 1.0       # 質量 (kg)
R = 0.1       # 球半徑 (m)

# 模擬時間參數（每一周期從 t_start 到 t_end）
t_start = -1.0   # 碰撞前 1 秒
t_end = 2.0      # 碰撞後 2 秒
T = t_end - t_start  # 模擬周期（共 3 秒）
dt = 0.02

# 以下為全局變數，儲存當前模擬的初始參數與碰撞後狀態
vx_pre = vy_pre = omega_pre = phi0 = None
vx_post = vy_post = omega_post = None
collision_x = None
collision_y = None

def reset_simulation():
    """
    隨機生成一次完整模擬週期的初始條件與碰撞後狀態，
    假設碰撞發生時球心位於 (x, y) = (R, 0)
    為確保球從牆右側運動到牆（牆位於 x = 0），要求 vx 為負值。
    """
    global vx_pre, vy_pre, omega_pre, phi0, vx_post, vy_post, omega_post, collision_x, collision_y
    vx_pre = -random.uniform(1.5, 3.0)    # m/s（負值：從右向左撞牆）
    vy_pre = random.uniform(-1.0, 1.0)      # m/s（可正可負）
    omega_pre = 30   # rad/s（正值代表逆時針旋轉）
    phi0 = random.uniform(0, 2*math.pi)       # 初始自轉角 (rad)
    collision_x = R   # 撞牆時球心位於 x = R
    collision_y = 0.0
    vx_post, vy_post, omega_post = simulate_collision_standard(vx_pre, vy_pre, omega_pre, e, mu, m, R)
    print("隨機初始條件更新：")
    print("vx_pre = {:.3f} m/s, vy_pre = {:.3f} m/s, omega_pre = {:.3f} rad/s, phi0 = {:.3f} rad".format(
        vx_pre, vy_pre, omega_pre, phi0))
    print("碰撞更新結果：vx' = {:.3f} m/s, vy' = {:.3f} m/s, omega' = {:.3f} rad/s\n".format(
        vx_post, vy_post, omega_post))

# 第一次初始化隨機參數
reset_simulation()

def get_state_at_time(t):
    """
    根據當前時間 t 返回球的狀態 (x, y, phi)。
    當 t < 0 時，使用碰撞前參數 (vx_pre, vy_pre, omega_pre)，
    反推至碰撞點 (collision_x, collision_y)。
    當 t >= 0 時，從 t=0 起以碰撞後參數 (vx_post, vy_post, omega_post) 運動。
    """
    if t < 0:
        t_shift = t  # t 為負，從碰撞點反推
        x = collision_x + vx_pre * t_shift
        y = collision_y + vy_pre * t_shift
        phi = phi0 + omega_pre * t_shift
    else:
        t_shift = t
        x = collision_x + vx_post * t_shift
        y = collision_y + vy_post * t_shift
        phi = phi0 + omega_post * t_shift
    return x, y, phi

# ------------------- 建立動畫 -------------------
fig, ax = plt.subplots(figsize=(8, 4))
ax.set_xlim(-0.5, 2.5)
ax.set_ylim(-1.0, 1.0)
ax.set_aspect('equal')
ax.set_title("標準定義下隨機初始條件的旋轉球碰撞動畫")
ax.set_xlabel("x (m)")
ax.set_ylabel("y (m)")

# 畫牆（牆位於 x = 0）
ax.plot([0, 0], [-2, 2], 'k-', linewidth=2)

# 初始化球（以圓形表示）和指示球內自轉方向的線
ball_patch = Circle((collision_x, collision_y), R, fc='skyblue', ec='b', zorder=2)
ax.add_patch(ball_patch)
orientation_line, = ax.plot([], [], 'r-', lw=2, zorder=3)

# 用以檢查是否進入新一輪模擬
prev_sim_time = t_start
frame_counter = 0  # 全局幀計數

def init():
    ball_patch.center = (collision_x, collision_y)
    orientation_line.set_data([], [])
    return ball_patch, orientation_line

def animate(i):
    global frame_counter, prev_sim_time
    frame_counter += 1
    # 模擬時間以周期 T 進行：t = (frame_counter*dt) mod T + t_start
    sim_time = (frame_counter * dt) % T + t_start

    # 當 sim_time 從周期末回到起點時，重設隨機模擬參數
    if sim_time < prev_sim_time:
        reset_simulation()
    prev_sim_time = sim_time

    # 取得當前球的位置與自轉角
    x, y, phi = get_state_at_time(sim_time)
    ball_patch.center = (x, y)
    # 計算球內指示自轉方向的線 (長度取 R)
    x_line = [x, x + R * math.cos(phi)]
    y_line = [y, y + R * math.sin(phi)]
    orientation_line.set_data(x_line, y_line)
    
    return ball_patch, orientation_line

ani = animation.FuncAnimation(fig, animate, frames=1000,
                              init_func=init, interval=dt*1000, blit=True)

plt.show()
