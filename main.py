import pygame, pymunk, math

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

space = pymunk.Space()
space.gravity = (0, 900)

# --- Infinite-feel Hills ---
track_pts = []
for x in range(0, 200000, 30):  # smoother
    y = 450 + 160 * math.sin(x * 0.0016) + 70 * math.sin(x * 0.004)
    track_pts.append((x, y))
for i in range(len(track_pts) - 1):
    seg = pymunk.Segment(space.static_body, track_pts[i], track_pts[i + 1], 4)
    seg.friction = 1.0
    seg.elasticity = 0.1
    space.add(seg)

# --- Car sprite ---
car_img = pygame.image.load("car.png").convert_alpha()
car_w, car_h = car_img.get_size()

# --- Car physics ---
mass = 8
collision_h = car_h * 0.55
moment = pymunk.moment_for_box(mass, (car_w, collision_h))
car_body = pymunk.Body(mass, moment)
car_body.position = (200, 150)

# Rounded box collider instead of segment (so torque works!)
car_shape = pymunk.Poly.create_box(car_body, (car_w, collision_h), radius=14)
car_shape.friction = 0.15
car_shape.elasticity = 0.2
space.add(car_body, car_shape)

# --- Driving constants ---
flip_timer = 0.0
speed_limit = 2000
accel_force = 9500
boost_force = 14000

running = True
while running:
    dt = 1/60
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    on_ground = bool(space.shape_query(car_shape))
    vel_x = car_body.velocity.x

    if on_ground:
        # Drive forces
        if keys[pygame.K_d] and abs(vel_x) < speed_limit:
            car_body.apply_force_at_local_point((accel_force, 0))
            car_body.apply_force_at_local_point((boost_force*dt*60, 0))
        if keys[pygame.K_a] and abs(vel_x) < speed_limit:
            car_body.apply_force_at_local_point((-accel_force, 0))
            car_body.apply_force_at_local_point((-boost_force*dt*60, 0))
        # steady nudge uphill
        if (keys[pygame.K_d] or keys[pygame.K_a]) and abs(vel_x) < speed_limit:
            car_body.apply_force_at_local_point(
                (math.copysign(1800, (keys[pygame.K_d]) - (keys[pygame.K_a])), 0)
            )
    else:
        # --- Air control: now uses torque properly ---
        gentle_torque = 240000
        if keys[pygame.K_a]:
            car_body.torque += gentle_torque   # rotate left
        if keys[pygame.K_d]:
            car_body.torque -= gentle_torque   # rotate right

    # Cap insane upward velocity
    if car_body.velocity.y < -900:
        car_body.velocity = (car_body.velocity.x, -900)

    # Auto-upright after 2s upside down
    ang = abs(math.degrees(car_body.angle) % 360)
    if 90 < ang < 270:
        flip_timer += dt
        if flip_timer > 2:
            car_body.angle = 0
            car_body.angular_velocity = 0
            car_body.position = (car_body.position.x, car_body.position.y + 5)
            flip_timer = 0
    else:
        flip_timer = 0

    # Step physics
    space.step(dt)

    # Camera follow X + Y
    cam_x = car_body.position.x - WIDTH // 2
    cam_y = car_body.position.y - HEIGHT // 2

    # --- Draw ---
    screen.fill((40,40,60))
    pygame.draw.polygon(
        screen, (60,180,60),
        [(track_pts[0][0]-cam_x, HEIGHT)]
        + [(x-cam_x, y - cam_y) for x, y in track_pts]
        + [(track_pts[-1][0]-cam_x, HEIGHT)]
    )

    rotated_car = pygame.transform.rotate(car_img, -math.degrees(car_body.angle))
    rect = rotated_car.get_rect(center=(car_body.position.x - cam_x,
                                        car_body.position.y - cam_y))
    screen.blit(rotated_car, rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
