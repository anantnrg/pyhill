import pygame, pymunk, math, random

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Pyhill")

# ===== PHYSICS =====
space = pymunk.Space()
space.gravity = (0, 900)

# ===== TEXTURES =====
dirt_tex = pygame.image.load("dirt_tile.png").convert()
grass_tex = pygame.image.load("grass_top.png").convert_alpha()

# ===== CAR =====
car_img = pygame.image.load("car.png").convert_alpha()
car_img = pygame.transform.rotozoom(car_img, 0, 0.4)
car_w, car_h = car_img.get_size()
mass = 8
collision_h = car_h * 0.55
moment = pymunk.moment_for_box(mass, (car_w, collision_h)) * 1.3
car_body = pymunk.Body(mass, moment)
car_body.position = (200, 150)
car_shape = pymunk.Poly.create_box(car_body, (car_w, collision_h), radius=14)
car_shape.friction = 0.15
space.add(car_body, car_shape)

# ===== TRACK =====
track_pts = []
track_step = 30
track_x = 0
buffer_ahead = 6000
buffer_behind = 2000
y_base = 450
amp1, amp2 = 160, 70
freq1, freq2 = 0.0016, 0.004


def track_y(x):
    return y_base + amp1 * math.sin(x * freq1) + amp2 * math.sin(x * freq2)


def add_track_point(x):
    y = track_y(x)
    track_pts.append((x, y))
    if len(track_pts) > 1:
        seg = pymunk.Segment(space.static_body, track_pts[-2], track_pts[-1], 4)
        seg.friction = 1.0
        seg.elasticity = 0.1
        space.add(seg)


for _ in range(buffer_ahead // track_step):
    add_track_point(track_x)
    track_x += track_step

# ===== COINS =====
coins = []
coin_spacing_min = 1000
coin_spacing_max = 1600
next_coin_x = 800
coin_radius = 18


def spawn_coin_group(x_start):
    group_size = random.randint(2, 6)
    gap = 45
    for i in range(group_size):
        x = x_start + i * gap
        y = track_y(x) - 90
        coins.append({"x": x, "y": y, "collected": False})


spawn_coin_group(next_coin_x)

# ===== GAS CANS =====
gas_cans = []
gas_radius = 20
gas_refill_amount = 100
game_time = 0
last_spawn_x = 0


def spawn_gas_can(x_start):
    y = track_y(x_start) - 100
    gas_cans.append({"x": x_start, "y": y, "collected": False})


# spawn first can
spawn_gas_can(2500)

# ===== HUD =====
font = pygame.font.SysFont(None, 28)
flip_timer = 0
speed_limit = 3000
accel_force = 5000
distance_traveled = 0
PPM = 30
cam_x, cam_y = 0, 0
cam_smooth = 0.1
coin_score = 0

# ===== GAS =====
fuel = 100
fuel_deplete_rate = 0.05
fuel_accel_drain = 0.2
fuel_bar_width = 200
out_of_gas_time = None
low_fuel_threshold = 30  # %
smart_spawn_distance = 1000  # how far ahead to drop a can
min_gas_distance = 1500  # don’t spawn too close to another

# ===== MAIN LOOP =====
running = True
while running:
    dt = 1 / 60
    game_time += dt

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    keys = pygame.key.get_pressed()
    on_ground = bool(space.shape_query(car_shape))
    vx, vy = car_body.velocity

    out_of_fuel = fuel <= 0
    if out_of_fuel and out_of_gas_time is None:
        out_of_gas_time = game_time

    # ===== DRIVE =====
    if not out_of_fuel:
        if on_ground:
            if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) and vx < speed_limit:
                car_body.apply_force_at_local_point((accel_force, 0))
                fuel -= fuel_accel_drain
            if (keys[pygame.K_a] or keys[pygame.K_LEFT]) and vx > -speed_limit:
                car_body.apply_force_at_local_point((-accel_force, 0))
                fuel -= fuel_accel_drain
        else:
            torque_air_base = 125000
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                car_body.torque += torque_air_base * dt * 60
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                car_body.torque -= torque_air_base * dt * 60
        fuel -= fuel_deplete_rate
    else:
        if game_time - out_of_gas_time > 20:
            screen.fill((20, 20, 20))
            text = font.render("Out of Gas, Game Over!", True, (255, 50, 50))
            screen.blit(text, (WIDTH // 2 - 180, HEIGHT // 2))
            pygame.display.flip()
            pygame.time.wait(3000)
            break

    fuel = max(0, fuel)

    # only spawn if fuel low, and no gas can close ahead
    if fuel < low_fuel_threshold:
        nearest_can_ahead = None
        for g in gas_cans:
            if g["x"] > car_body.position.x:
                nearest_can_ahead = g
                break
        # spawn if no can nearby
        if (not nearest_can_ahead) or (
            nearest_can_ahead["x"] - car_body.position.x > min_gas_distance
        ):
            new_x = car_body.position.x + smart_spawn_distance
            spawn_gas_can(new_x)

    # ===== TRACK EXTENSION =====
    space.step(dt)
    while track_pts[-1][0] - car_body.position.x < buffer_ahead:
        add_track_point(track_x)
        track_x += track_step
    while track_pts and track_pts[1][0] < car_body.position.x - buffer_behind:
        track_pts.pop(0)

    # ===== COINS =====
    if car_body.position.x > next_coin_x - 4000:
        next_coin_x += random.randint(coin_spacing_min, coin_spacing_max)
        spawn_coin_group(next_coin_x)

    # ===== COIN COLLECTION =====
    for coin in coins:
        if not coin["collected"]:
            dx = coin["x"] - car_body.position.x
            dy = coin["y"] - car_body.position.y
            if dx * dx + dy * dy < (coin_radius + car_w * 0.3) ** 2:
                coin["collected"] = True
                coin_score += 1
    coins = [c for c in coins if c["x"] > car_body.position.x - buffer_behind]

    # ===== GAS COLLECTION =====
    for gas in gas_cans:
        if not gas["collected"]:
            dx = gas["x"] - car_body.position.x
            dy = gas["y"] - car_body.position.y
            if dx * dx + dy * dy < (gas_radius + car_w * 0.4) ** 2:
                gas["collected"] = True
                fuel = min(100, fuel + gas_refill_amount)
                out_of_gas_time = None
    gas_cans = [g for g in gas_cans if g["x"] > car_body.position.x - buffer_behind]

    # ===== CAMERA =====
    target_cam_x = int(car_body.position.x - WIDTH // 2)
    target_cam_y = int(car_body.position.y - HEIGHT // 2)
    cam_x += (target_cam_x - cam_x) * cam_smooth
    cam_y += (target_cam_y - cam_y) * cam_smooth

    # ===== DRAW =====
    screen.fill((135, 206, 235))

    for i in range(len(track_pts) - 1):
        x1, y1 = track_pts[i]
        x2, y2 = track_pts[i + 1]
        if x2 < cam_x:
            continue
        if x1 - cam_x > WIDTH:
            break
        poly_pts = [
            (x1 - cam_x, HEIGHT),
            (x1 - cam_x, y1 - cam_y),
            (x2 - cam_x, y2 - cam_y),
            (x2 - cam_x, HEIGHT),
        ]
        pygame.draw.polygon(screen, (139, 69, 19), poly_pts)
        dx, dy = x2 - x1, y2 - y1
        seg_len = max(1, math.hypot(dx, dy))
        angle = math.degrees(math.atan2(-dy, dx))
        piece = pygame.transform.rotozoom(
            grass_tex, angle, seg_len / grass_tex.get_width()
        )
        pos = (x1 - cam_x, y1 - cam_y)
        screen.blit(piece, piece.get_rect(midleft=pos))

    for coin in coins:
        if not coin["collected"]:
            pygame.draw.circle(
                screen,
                (255, 215, 0),
                (int(coin["x"] - cam_x), int(coin["y"] - cam_y)),
                coin_radius,
            )

    for gas in gas_cans:
        if not gas["collected"]:
            pygame.draw.rect(
                screen,
                (255, 50, 50),
                (
                    int(gas["x"] - cam_x - gas_radius),
                    int(gas["y"] - cam_y - gas_radius),
                    gas_radius * 2,
                    gas_radius * 2,
                ),
            )
            pygame.draw.rect(
                screen,
                (200, 200, 200),
                (
                    int(gas["x"] - cam_x - 5),
                    int(gas["y"] - cam_y - gas_radius - 10),
                    10,
                    10,
                ),
            )

    rotated = pygame.transform.rotate(car_img, -math.degrees(car_body.angle))
    rect = rotated.get_rect(
        center=(car_body.position.x - cam_x, car_body.position.y - cam_y)
    )
    screen.blit(rotated, rect)

    distance_traveled += vx / PPM * dt
    speed_mps = vx / PPM
    speed_kmh = speed_mps * 3.6
    dist_text = font.render(f"Distance: {int(distance_traveled)} m", True, (0, 0, 0))
    speed_text = font.render(f"Speed: {int(speed_kmh)} km/h", True, (0, 0, 0))
    coin_text = font.render(f"Coins: {coin_score}", True, (255, 215, 0))
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 0, 0))

    screen.blit(dist_text, (WIDTH - 250, 10))
    screen.blit(speed_text, (WIDTH - 250, 35))
    screen.blit(coin_text, (WIDTH - 250, 60))
    screen.blit(fps_text, (10, 10))

    pygame.draw.rect(screen, (0, 0, 0), (30, HEIGHT - 40, fuel_bar_width + 4, 24))
    pygame.draw.rect(
        screen, (255, 50, 50), (32, HEIGHT - 38, int((fuel / 100) * fuel_bar_width), 20)
    )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
