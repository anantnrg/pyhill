import pygame, pymunk, math, random, sys
import json, os

PLAYERS_FILE = "players.json"

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
clock = pygame.time.Clock()
pygame.display.set_caption("Pyhill")
coin_icon = pygame.image.load("coin_icon.png").convert_alpha()
coin_icon = pygame.transform.rotozoom(coin_icon, 0, 2)
gas_icon = pygame.image.load("gas_icon.png").convert_alpha()
gas_icon = pygame.transform.rotozoom(gas_icon, 0, 4)


def reset_game_state():
    global space, track_pts, track_x, coins, gas_cans, next_coin_x
    global fuel, distance_traveled, coin_score, game_time
    global out_of_gas_time, upside_down_start, engine_disabled
    global cam_x, cam_y, y_base, amp1, amp2, freq1, freq2, buffer_ahead, buffer_behind
    global \
        coin_spacing_min, \
        coin_spacing_max, \
        min_gas_distance, \
        smart_spawn_distance, \
        flip_count

    # ===== PHYSICS =====
    space = pymunk.Space()
    space.gravity = (0, 500)

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

    globals()["track_y"] = track_y  # rebind function globally for reuse

    def add_track_point(x):
        y = track_y(x)
        track_pts.append((x, y))
        if len(track_pts) > 1:
            seg = pymunk.Segment(space.static_body, track_pts[-2], track_pts[-1], 4)
            seg.friction = 1.0
            seg.elasticity = 0.1
            space.add(seg)

    globals()["add_track_point"] = add_track_point

    for _ in range(buffer_ahead // track_step):
        add_track_point(track_x)
        track_x += track_step

    # ===== COINS & GAS =====
    coins = []
    gas_cans = []
    coin_spacing_min = 1000
    coin_spacing_max = 1600
    next_coin_x = 800

    # ===== GAME STATS =====
    game_time = 0
    fuel = 100
    distance_traveled = 0
    coin_score = 0
    out_of_gas_time = None
    upside_down_start = None
    engine_disabled = False

    # ===== CAMERA =====
    cam_x, cam_y = 0, 0
    smart_spawn_distance = 1000
    min_gas_distance = 2500
    flip_count = 0


def load_players():
    if os.path.exists(PLAYERS_FILE):
        try:
            with open(PLAYERS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_players(players):
    with open(PLAYERS_FILE, "w") as f:
        json.dump(players, f, indent=2)


# ===== PHYSICS =====
space = pymunk.Space()
space.gravity = (0, 500)

# ===== LOAD CARS =====
car_files = ["car1.png", "car2.png", "car3.png"]
car_images = [pygame.image.load(f).convert_alpha() for f in car_files]
selected_car_index = 0  # which car player picked

# ===== TEXTURES =====
dirt_tex = pygame.image.load("dirt_tile.png").convert()
grass_tex = pygame.image.load("grass_top.png").convert_alpha()


# ===== FUNCTIONS =====
def create_car(selected_car_img):
    car_img = pygame.transform.rotozoom(selected_car_img, 0, 0.4)
    car_w, car_h = car_img.get_size()
    mass = 8
    collision_h = car_h * 0.55
    moment = pymunk.moment_for_box(mass, (car_w, collision_h)) * 1.3
    car_body = pymunk.Body(mass, moment)
    car_body.position = (200, 150)
    car_shape = pymunk.Poly.create_box(car_body, (car_w, collision_h), radius=14)
    car_shape.friction = 0.15
    space.add(car_body, car_shape)
    return car_img, car_body, car_shape, car_w, car_h


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

# ===== COINS & GAS =====
coins = []
coin_spacing_min = 1000
coin_spacing_max = 1600
next_coin_x = 800
coin_radius = 18

gas_cans = []
gas_radius = 20
gas_refill_amount = 100
game_time = 0
last_spawn_x = 0

font = pygame.font.SysFont("Rajdhani", 36, True)
collect_font = pygame.font.SysFont("Rajdhani", 64, True)
flip_timer = 0
speed_limit = 12000
accel_force = 11000
distance_traveled = 0
PPM = 30
cam_x, cam_y = 0, 0
cam_smooth = 0.1
coin_score = 0
fuel = 100
fuel_deplete_rate = 0.05
fuel_accel_drain = 0.2
fuel_bar_width = 400
out_of_gas_time = None
low_fuel_threshold = 30
smart_spawn_distance = 1000
min_gas_distance = 2500
upside_down_start = None
engine_disabled = False
flip_count = 0


def spawn_coin_group(x_start):
    group_size = random.randint(2, 6)
    gap = 45
    for i in range(group_size):
        x = x_start + i * gap
        y = track_y(x) - 90
        coins.append({"x": x, "y": y, "collected": False})


def spawn_gas_can(x_start):
    y = track_y(x_start) - 100
    gas_cans.append({"x": x_start, "y": y, "collected": False})


spawn_coin_group(next_coin_x)
spawn_gas_can(2500)

players = load_players()
current_player = None


# ===== CAR SELECTION MENU =====
def car_selection_menu():
    global selected_car_index
    menu_font = pygame.font.SysFont(None, 80)
    small_font = pygame.font.SysFont(None, 36)
    title_text = menu_font.render("SELECT YOUR RIDE", True, (255, 215, 0))

    waiting = True
    while waiting:
        screen.fill((25, 25, 35))

        # handle events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return  # back to main menu
                elif e.key == pygame.K_LEFT:
                    selected_car_index = (selected_car_index - 1) % len(car_images)
                elif e.key == pygame.K_RIGHT:
                    selected_car_index = (selected_car_index + 1) % len(car_images)
                elif e.key == pygame.K_SPACE:
                    waiting = False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for i, img in enumerate(car_images):
                    rect = pygame.Rect(
                        WIDTH // 2 + (i - selected_car_index) * 300 - 100,
                        HEIGHT // 2 - 100,
                        200,
                        200,
                    )
                    if rect.collidepoint(mx, my):
                        selected_car_index = i
                        waiting = False

        # draw title
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 6))

        # draw cars
        for i, img in enumerate(car_images):
            scale = 0.6 if i == selected_car_index else 0.35
            car_display = pygame.transform.rotozoom(img, 0, scale)
            rect = car_display.get_rect(
                center=(
                    WIDTH // 2 + (i - selected_car_index) * 300,
                    HEIGHT // 2 + 50,
                )
            )
            screen.blit(car_display, rect)

        hint_text = small_font.render(
            "← → to select  |  SPACE to confirm", True, (220, 220, 220)
        )
        screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT - 100))

        pygame.display.flip()
        clock.tick(30)


# ===== MAIN MENU =====
def main_menu():
    global current_player, players  # so we can modify them

    menu_font = pygame.font.SysFont("Rajdhani", 256, True)
    small_font = pygame.font.SysFont("Rajdhani", 48, True)
    tiny_font = pygame.font.SysFont("Rajdhani", 32, True)

    title_text = menu_font.render("PYHILL", True, (255, 215, 0))

    # button setup
    button_w, button_h = 420, 120
    start_btn_rect = pygame.Rect(
        WIDTH - button_w - 60, HEIGHT - button_h - 60, button_w, button_h
    )
    car_btn_rect = pygame.Rect(
        WIDTH // 2 - button_w // 2, HEIGHT // 2 - 40, button_w, button_h
    )
    score_btn_rect = pygame.Rect(
        WIDTH // 2 - button_w // 2, HEIGHT // 2 + 120, button_w, button_h
    )
    exit_btn_rect = pygame.Rect(40, HEIGHT - 100, 220, 70)

    # player UI top-right
    player_box_rect = pygame.Rect(WIDTH - 460, 40, 400, 120)

    waiting = True
    while waiting:
        screen.fill((20, 20, 30))
        wave = math.sin(pygame.time.get_ticks() * 0.002) * 30

        # title
        screen.blit(
            title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 8 + wave)
        )

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                pygame.event.clear()
                waiting = False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True

        # reusable button drawer
        def draw_button(rect, text, color_idle, color_hover):
            hovered = rect.collidepoint(mx, my)
            color = color_hover if hovered else color_idle
            pygame.draw.rect(screen, color, rect, border_radius=12)
            pygame.draw.rect(screen, (0, 0, 0), rect, 3, border_radius=12)
            label = small_font.render(text, True, (0, 0, 0))
            screen.blit(
                label,
                (
                    rect.centerx - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )
            return hovered

        # draw menu buttons
        if draw_button(start_btn_rect, "START", (0, 220, 0), (0, 255, 0)) and clicked:
            if current_player:
                waiting = False
        if (
            draw_button(car_btn_rect, "SELECT CAR", (255, 230, 120), (255, 255, 180))
            and clicked
        ):
            car_selection_menu()
        if (
            draw_button(score_btn_rect, "HIGH SCORES", (120, 180, 255), (160, 210, 255))
            and clicked
        ):
            print("High scores screen placeholder!")
        if (
            draw_button(exit_btn_rect, "EXIT", (180, 80, 80), (255, 100, 100))
            and clicked
        ):
            pygame.quit()
            sys.exit()

        # ===== PLAYER BOX (top-right) =====
        pygame.draw.rect(screen, (60, 60, 80), player_box_rect, border_radius=10)

        if current_player:
            player_text = tiny_font.render(
                f"Player: {current_player}", True, (255, 255, 255)
            )
            screen.blit(player_text, (player_box_rect.x + 20, player_box_rect.y + 15))

            stats = players[current_player]
            stat_str = f"Coins: {stats['Coins']} | Flips: {stats['Flips']} | Dist: {stats['Max Distance']}"
            stat_text = tiny_font.render(stat_str, True, (220, 220, 220))
            screen.blit(stat_text, (player_box_rect.x + 20, player_box_rect.y + 70))

            change_rect = pygame.Rect(
                player_box_rect.right - 160, player_box_rect.y + 30, 140, 60
            )
            if (
                draw_button(change_rect, "CHANGE", (200, 200, 100), (255, 255, 150))
                and clicked
            ):
                current_player = None
        else:
            add_rect = pygame.Rect(
                player_box_rect.x + 20, player_box_rect.y + 30, 360, 60
            )
            if (
                draw_button(
                    add_rect, "SELECT / CREATE PLAYER", (200, 200, 100), (255, 255, 150)
                )
                and clicked
            ):
                current_player = player_select_menu()

        pygame.display.flip()
        clock.tick(30)


def player_select_menu():
    global players
    small_font = pygame.font.SysFont("Rajdhani", 40, True)
    tiny_font = pygame.font.SysFont("Rajdhani", 28, True)
    waiting = True
    while waiting:
        screen.fill((25, 25, 35))
        title = small_font.render("SELECT PLAYER", True, (255, 215, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return None

        y = 200
        for name in players.keys():
            rect = pygame.Rect(WIDTH // 2 - 300, y, 600, 80)
            hovered = rect.collidepoint(mx, my)
            color = (120, 180, 255) if hovered else (100, 100, 140)
            pygame.draw.rect(screen, color, rect, border_radius=12)
            pygame.draw.rect(screen, (0, 0, 0), rect, 3, border_radius=12)
            text = tiny_font.render(name, True, (0, 0, 0))
            screen.blit(
                text,
                (
                    rect.centerx - text.get_width() // 2,
                    rect.centery - text.get_height() // 2,
                ),
            )
            if hovered and clicked:
                return name
            y += 100

        # add new player button
        add_rect = pygame.Rect(WIDTH // 2 - 300, y + 40, 600, 80)
        pygame.draw.rect(screen, (180, 220, 120), add_rect, border_radius=12)
        pygame.draw.rect(screen, (0, 0, 0), add_rect, 3, border_radius=12)
        text = tiny_font.render("CREATE NEW PLAYER", True, (0, 0, 0))
        screen.blit(
            text,
            (
                add_rect.centerx - text.get_width() // 2,
                add_rect.centery - text.get_height() // 2,
            ),
        )
        if add_rect.collidepoint(mx, my) and clicked:
            new_name = input("Enter yer name, matey: ")
            if new_name.strip():
                players[new_name] = {"Max Distance": 0, "Coins": 0, "Flips": 0}
                save_players(players)
                return new_name

        pygame.display.flip()
        clock.tick(30)


def confirm_exit_menu():
    small_font = pygame.font.SysFont("Rajdhani", 64, True)
    button_font = pygame.font.SysFont("Rajdhani", 48, True)

    yes_rect = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2, 180, 80)
    no_rect = pygame.Rect(WIDTH // 2 + 40, HEIGHT // 2, 180, 80)

    while True:
        screen.fill((20, 20, 20))
        prompt = small_font.render("Return to Main Menu?", True, (255, 255, 255))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 3))

        mx, my = pygame.mouse.get_pos()
        clicked = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True

        def draw_button(rect, text, base_col, hover_col):
            hovered = rect.collidepoint(mx, my)
            color = hover_col if hovered else base_col
            pygame.draw.rect(screen, color, rect, border_radius=12)
            label = button_font.render(text, True, (0, 0, 0))
            screen.blit(
                label,
                (
                    rect.centerx - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )
            return hovered

        if draw_button(yes_rect, "YES", (255, 100, 100), (255, 150, 150)) and clicked:
            return True
        if draw_button(no_rect, "NO", (120, 255, 120), (160, 255, 160)) and clicked:
            return False

        pygame.display.flip()
        clock.tick(30)


def show_game_over(reason_text):
    small_font = pygame.font.SysFont("Rajdhani", 64, True)
    button_font = pygame.font.SysFont("Rajdhani", 48, True)
    btn_rect = pygame.Rect(WIDTH - 300, HEIGHT - 120, 260, 80)

    waiting = True
    while waiting:
        screen.fill((10, 10, 10))
        reason = small_font.render(reason_text, True, (255, 60, 60))
        score_info = button_font.render(
            f"Coins: {coin_score}  |  Flips: {flip_count}  |  Distance: {int(distance_traveled)}m",
            True,
            (255, 255, 255),
        )
        screen.blit(
            score_info, (WIDTH // 2 - score_info.get_width() // 2, HEIGHT // 2 - 60)
        )
        info = button_font.render("Press ESC or click RETURN", True, (255, 255, 255))

        screen.blit(reason, (WIDTH // 2 - reason.get_width() // 2, HEIGHT // 3))
        pygame.draw.rect(screen, (255, 50, 50), btn_rect, border_radius=12)
        label = button_font.render("RETURN", True, (0, 0, 0))
        screen.blit(
            label,
            (
                btn_rect.centerx - label.get_width() // 2,
                btn_rect.centery - label.get_height() // 2,
            ),
        )
        screen.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2 + 100))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                waiting = False
            if (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
                and btn_rect.collidepoint(e.pos)
            ):
                waiting = False
        clock.tick(30)
    main_menu()


# ===== GAME LOOP =====
def game_loop():
    reset_game_state()
    global \
        fuel, \
        distance_traveled, \
        coin_score, \
        game_time, \
        out_of_gas_time, \
        track_x, \
        engine_disabled, \
        upside_down_start, \
        flip_count

    selected_car_img = car_images[selected_car_index]
    car_img, car_body, car_shape, car_w, car_h = create_car(selected_car_img)
    floating_texts = []

    running = True
    while running:
        dt = 1 / 60
        game_time += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                paused = True
                if confirm_exit_menu():
                    return
                paused = False

        keys = pygame.key.get_pressed()
        on_ground = bool(space.shape_query(car_shape))
        vx, vy = car_body.velocity

        out_of_fuel = fuel <= 0
        if out_of_fuel and out_of_gas_time is None:
            out_of_gas_time = game_time

        # DRIVE
        if not out_of_fuel:
            angle_deg = math.degrees(car_body.angle) % 360
            angular_speed = abs(car_body.angular_velocity)
            vel_mag = (car_body.velocity[0] ** 2 + car_body.velocity[1] ** 2) ** 0.5

            if 170 < angle_deg < 190 and angular_speed < 1:
                engine_disabled = True
            # check if mostly upside down (170–190°)
            if 170 < angle_deg < 190 and vel_mag < 50 and angular_speed < 1:
                if upside_down_start is None:
                    upside_down_start = game_time
                elif game_time - upside_down_start > 5:
                    # Only after 5 seconds of being still
                    show_game_over("You Flipped! Game Over!")
                    return
            else:
                upside_down_start = None  # reset timer if moved or recovered

            if on_ground:
                if not engine_disabled:
                    if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) and vx < speed_limit:
                        car_body.apply_force_at_local_point((accel_force, 0))
                        fuel -= fuel_accel_drain
                    if (keys[pygame.K_a] or keys[pygame.K_LEFT]) and vx > -speed_limit:
                        car_body.apply_force_at_local_point((-accel_force, 0))
                        fuel -= fuel_accel_drain
            else:
                # IN-AIR: apply player torque, but ALWAYS track rotation delta every frame
                angular_impulse = 0.15  # tweak for sensitivity
                # apply instant angular changes (no wind-up)
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    if car_body.angular_velocity <= 5:
                        car_body.angular_velocity += angular_impulse
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    if car_body.angular_velocity >= -5:
                        car_body.angular_velocity -= angular_impulse

                # initialize rotation tracking fields on first airborne frame
                if not hasattr(car_body, "rot_accum"):
                    car_body.rot_accum = 0.0
                    car_body.last_angle = car_body.angle

                # compute angle delta this frame (in degrees) and normalize across wrap
                current_angle = math.degrees(car_body.angle) % 360
                last_angle_deg = math.degrees(car_body.last_angle) % 360
                delta = current_angle - last_angle_deg
                # normalize to [-180, 180] to handle wrap-around
                if delta > 180:
                    delta -= 360
                elif delta < -180:
                    delta += 360

                car_body.rot_accum += delta

                # full flip detection (±360° accumulated)
                if abs(car_body.rot_accum) >= 360.0:
                    flip_count += 1
                    coin_score += 1000
                    car_body.rot_accum = 0.0  # reset for next flip
                    floating_texts.append(
                        {
                            "text": f"+1000 FLIP #{flip_count}!",
                            "x": car_body.position.x,
                            "y": car_body.position.y - 60,
                            "timer": 2.0,
                            "color": (0, 0, 0),
                        }
                    )

                # save current angle for next frame
                car_body.last_angle = car_body.angle

            fuel -= fuel_deplete_rate
        else:
            if game_time - out_of_gas_time > 5:
                show_game_over("Out of Gas, Game Over!")
                return

        fuel = max(0, fuel)

        # SMART GAS SPAWN
        if fuel < low_fuel_threshold:
            nearest_can_ahead = None
            for g in gas_cans:
                if g["x"] > car_body.position.x:
                    nearest_can_ahead = g
                    break
            if (not nearest_can_ahead) or (
                nearest_can_ahead["x"] - car_body.position.x > min_gas_distance
            ):
                new_x = car_body.position.x + smart_spawn_distance
                spawn_gas_can(new_x)

        # TRACK EXTENSION
        space.step(dt)
        while track_pts[-1][0] - car_body.position.x < buffer_ahead:
            add_track_point(track_x)
            track_x += track_step
        while track_pts and track_pts[1][0] < car_body.position.x - buffer_behind:
            track_pts.pop(0)

        # COINS
        global next_coin_x
        if car_body.position.x > next_coin_x - 4000:
            next_coin_x += random.randint(coin_spacing_min, coin_spacing_max)
            spawn_coin_group(next_coin_x)

        for coin in coins:
            if not coin["collected"]:
                dx = coin["x"] - car_body.position.x
                dy = coin["y"] - car_body.position.y
                if dx * dx + dy * dy < (coin_radius + car_w * 0.3) ** 2:
                    coin["collected"] = True
                    floating_texts.append(
                        {
                            "text": "+1",
                            "x": coin["x"],
                            "y": coin["y"] - 40,
                            "timer": 1.0,
                            "color": (0, 0, 0),
                        }
                    )
                    coin_score += 1
        coins[:] = [c for c in coins if c["x"] > car_body.position.x - buffer_behind]

        # GAS COLLECTION
        for gas in gas_cans:
            if not gas["collected"]:
                dx = gas["x"] - car_body.position.x
                dy = gas["y"] - car_body.position.y
                if dx * dx + dy * dy < (gas_radius + car_w * 0.4) ** 2:
                    gas["collected"] = True
                    fuel = min(100, fuel + gas_refill_amount)
                    out_of_gas_time = None
        gas_cans[:] = [
            g for g in gas_cans if g["x"] > car_body.position.x - buffer_behind
        ]

        # CAMERA
        target_cam_x = int(car_body.position.x - WIDTH // 2)
        target_cam_y = int(car_body.position.y - HEIGHT // 2)
        global cam_x, cam_y
        cam_x += (target_cam_x - cam_x) * cam_smooth
        cam_y += (target_cam_y - cam_y) * cam_smooth

        # DRAW
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
        dist_text = font.render(
            f"Distance: {int(distance_traveled)} m", True, (0, 0, 0)
        )
        speed_text = font.render(f"Speed: {int(speed_kmh)} km/h", True, (0, 0, 0))
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 0, 0))
        coin_text = font.render(f"{coin_score}", True, (255, 215, 0))

        screen.blit(dist_text, (WIDTH - 250, 10))
        screen.blit(speed_text, (WIDTH - 250, 35))
        screen.blit(coin_icon, (WIDTH - 310, 60))
        screen.blit(coin_text, (WIDTH - 250, 65))
        screen.blit(fps_text, (10, 10))

        screen.blit(gas_icon, (40, HEIGHT - 120))
        pygame.draw.rect(screen, (0, 0, 0), (100, HEIGHT - 110, fuel_bar_width + 4, 36))
        pygame.draw.rect(
            screen,
            (255, 50, 50),
            (102, HEIGHT - 108, int((fuel / 100) * fuel_bar_width), 32),
        )

        for ftext in floating_texts[:]:
            alpha = int(255 * (ftext["timer"] / 1.5))
            if alpha < 0:
                alpha = 0
            surf = collect_font.render(ftext["text"], True, ftext["color"])
            surf.set_alpha(alpha)
            screen.blit(surf, (ftext["x"] - cam_x, ftext["y"] - cam_y))
            ftext["y"] -= 40 * dt  # float upward
            ftext["timer"] -= dt
            if ftext["timer"] <= 0:
                floating_texts.remove(ftext)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# ===== RUN =====
if __name__ == "__main__":
    while True:
        main_menu()
        game_loop()
