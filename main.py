import pygame, pymunk, math

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Pirate Sine Rider Endless Smooth")

# ===== PHYSICS =====
space = pymunk.Space()
space.gravity = (0, 900)

# ===== TEXTURES =====
dirt_tex  = pygame.image.load("dirt_tile.png").convert()
grass_tex = pygame.image.load("grass_top.png").convert_alpha()

# ===== CAR =====
car_img = pygame.image.load("car.png").convert_alpha()
car_img = pygame.transform.rotozoom(car_img, 0, 0.4)
car_w, car_h = car_img.get_size()
mass = 8
collision_h = car_h * 0.55
moment = pymunk.moment_for_box(mass, (car_w, collision_h)) * 1.3  # stable but nimble
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

def add_track_point(x):
    y = y_base + amp1*math.sin(x*freq1) + amp2*math.sin(x*freq2)
    track_pts.append((x, y))
    if len(track_pts) > 1:
        seg = pymunk.Segment(space.static_body, track_pts[-2], track_pts[-1], 4)
        seg.friction = 1.0
        seg.elasticity = 0.1
        space.add(seg)

for _ in range(buffer_ahead // track_step):
    add_track_point(track_x)
    track_x += track_step

# ===== HUD =====
font = pygame.font.SysFont(None,28)
flip_timer = 0
speed_limit = 2000
accel_force = 5000
boost_force = 600
distance_traveled = 0
PPM = 30  # pixels per meter

# ===== CAMERA SMOOTHING =====
cam_x, cam_y = 0, 0
cam_smooth = 0.1  # lower = snappier, higher = smoother

# ===== MAIN LOOP =====
running = True
while running:
    dt = 1/60
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    on_ground = bool(space.shape_query(car_shape))
    vx, vy = car_body.velocity

    # ----- DRIVING -----
    if on_ground:
        if keys[pygame.K_d] and vx < speed_limit:
            car_body.apply_force_at_local_point((accel_force,0))
            car_body.apply_force_at_local_point((boost_force*dt*60,0))
        if keys[pygame.K_a] and vx > -speed_limit:
            car_body.apply_force_at_local_point((-accel_force,0))
            car_body.apply_force_at_local_point((-boost_force*dt*60,0))
    else:
        # Air control ramps with speed
        torque_air_base = 60000
        torque_air_mult = min(1.0, abs(vx)/300)
        if keys[pygame.K_a]:
            car_body.torque += torque_air_base * torque_air_mult * dt * 60
        if keys[pygame.K_d]:
            car_body.torque -= torque_air_base * torque_air_mult * dt * 60

    # Cap upward velocity
    if car_body.velocity.y < -900:
        car_body.velocity = (car_body.velocity.x, -900)

    # Auto-upright
    ang = abs(math.degrees(car_body.angle)%360)
    if 90 < ang < 270:
        flip_timer += dt
        if flip_timer > 2:
            car_body.angle = 0
            car_body.angular_velocity = 0
            car_body.position = (car_body.position.x, car_body.position.y + 5)
            flip_timer = 0
    else:
        flip_timer = 0

    space.step(dt)

    # ----- EXTEND TRACK AHEAD -----
    while track_pts[-1][0] - car_body.position.x < buffer_ahead:
        add_track_point(track_x)
        track_x += track_step

    # ----- REMOVE TRACK BEHIND -----
    while track_pts and track_pts[1][0] < car_body.position.x - buffer_behind:
        track_pts.pop(0)

    # ----- CAMERA (Smooth Follow) -----
    target_cam_x = int(car_body.position.x - WIDTH//2)
    target_cam_y = int(car_body.position.y - HEIGHT//2)
    cam_x += (target_cam_x - cam_x) * cam_smooth
    cam_y += (target_cam_y - cam_y) * cam_smooth

    # Fill sky
    screen.fill((135,206,235))

    # Draw terrain
    for i in range(len(track_pts)-1):
        x1, y1 = track_pts[i]
        x2, y2 = track_pts[i+1]
        if x2 < cam_x: continue
        if x1 - cam_x > WIDTH: break

        # Dirt polygon
        poly_pts = [(x1 - cam_x, HEIGHT), (x1 - cam_x, y1 - cam_y),
                    (x2 - cam_x, y2 - cam_y), (x2 - cam_x, HEIGHT)]
        pygame.draw.polygon(screen, (139,69,19), poly_pts)

        # Grass strip
        dx, dy = x2-x1, y2-y1
        seg_len = max(1, math.hypot(dx, dy))
        angle = math.degrees(math.atan2(-dy, dx))
        piece = pygame.transform.rotozoom(grass_tex, angle, seg_len / grass_tex.get_width())
        pos = (x1 - cam_x, y1 - cam_y)
        screen.blit(piece, piece.get_rect(midleft=pos))

    # ----- CAR DRAW -----
    rotated = pygame.transform.rotate(car_img, -math.degrees(car_body.angle))
    rect = rotated.get_rect(center=(car_body.position.x - cam_x, car_body.position.y - cam_y))
    screen.blit(rotated, rect)

    # ----- SPEED & DISTANCE -----
    distance_traveled += vx / PPM * dt
    speed_mps = vx / PPM
    speed_kmh = speed_mps * 3.6
    dist_text = font.render(f"Distance: {int(distance_traveled)} m", True, (0,0,0))
    speed_text = font.render(f"Speed: {int(speed_kmh)} km/h", True, (0,0,0))
    screen.blit(dist_text, (WIDTH-250, 10))
    screen.blit(speed_text, (WIDTH-250, 35))

    # ----- FPS -----
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0,0,0))
    screen.blit(fps_text, (10,10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
