import pygame
import random
import sys
import math
import os
import json

# Mengatur working directory ke folder tempat script berada agar path assets selalu benar
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Inisialisasi Pygame dan mixer untuk suara
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Konstanta ukuran layar dan frame rate
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Warna-warna tema Avatar: lautan dalam, glow cyan, merah bahaya, dll
OCEAN_BLUE = (5, 25, 70)
GLOW_CYAN = (0, 200, 255)
RED_DANGER = (200, 50, 50)
WHITE = (255, 255, 255)
YELLOW_GLOW = (255, 255, 150)

# Membuat window game dan mengatur judul
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Avatar: The Way of Water - Tulkun Defense")
clock = pygame.time.Clock()

# ======================
# KELAS DASAR UNTUK SEMUA OBJEK GAME
# ======================
class GameObject:
    def __init__(self, x, y, width, height):
        self.__x = x
        self.__y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x, y, width, height)  # Untuk deteksi collision
        self.image = None
    
    # Property untuk mengakses dan mengubah posisi dengan aman (enkapsulasi)
    @property
    def x(self):
        return self.__x
    
    @x.setter
    def x(self, value):
        self.__x = value
        self.rect.x = value
    
    @property
    def y(self):
        return self.__y
    
    @y.setter
    def y(self, value):
        self.__y = value
        self.rect.y = value
    
    # Memuat gambar dari folder assets
    def load_image(self, filename):
        path = os.path.join('assets', filename)
        if os.path.exists(path):
            try:
                self.image = pygame.image.load(path)
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    self.image = self.image.convert()
                else:
                    self.image = self.image.convert_alpha()
                print(f"Berhasil load gambar: {filename}")
            except pygame.error as e:
                print(f"Gagal load {filename}: {e}")
                self.image = None
        else:
            print(f"File gambar tidak ditemukan: {path}")
            self.image = None
    
    # Menggambar gambar yang sudah discale ke ukuran objek
    def draw_image(self, surface):
        if self.image:
            scaled = pygame.transform.scale(self.image, (self.width, self.height))
            surface.blit(scaled, self.rect)

# ======================
# SISTEM PARTIKEL UNTUK EFEK LEDAKAN
# ======================
class Particle(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, random.randint(4, 10), random.randint(4, 10))
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-6, 6)
        self.life = 50
        self.max_life = 50
        self.color = random.choice([GLOW_CYAN, YELLOW_GLOW, (255, 150, 50)])
    
    # Update posisi dan gravitasi partikel
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3  # Gravitasi ke bawah
        self.life -= 1
        self.rect.center = (self.x, self.y)
    
    # Gambar partikel dengan transparansi yang menurun seiring waktu
    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        if alpha > 0:
            color = (*self.color, alpha)
            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (self.width//2, self.height//2), self.width//2)
            surface.blit(s, self.rect)

# ======================
# KELAS PROYEKTIL DASAR
# ======================
class Projectile(GameObject):
    def __init__(self, x, y, speed_x, speed_y, width=40, height=10):
        super().__init__(x, y, width, height)
        self.speed_x = speed_x
        self.speed_y = speed_y
    
    # Update posisi proyektil setiap frame
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.center = (self.x, self.y)

# Proyektil musuh: Harpoon
class Harpoon(Projectile):
    def __init__(self, x, y, speed_x, speed_y):
        super().__init__(x, y, speed_x, speed_y)
    
    # Gambar bentuk harpoon merah
    def draw(self, surface):
        pygame.draw.polygon(surface, RED_DANGER, [
            (self.rect.left, self.rect.top),
            (self.rect.right, self.rect.centery),
            (self.rect.left, self.rect.bottom)
        ])

# Proyektil pemain: Sonic Wave
class SonicWave(Projectile):
    def __init__(self, x, y):
        super().__init__(x, y, 18, 0, 1, 1)
        self.radius = 15
    
    # Gelombang melebar seiring bergerak
    def update(self):
        self.x += self.speed_x
        self.radius += 10
    
    # Gambar lingkaran glow biru dengan efek transparan
    def draw(self, surface):
        pygame.draw.circle(surface, GLOW_CYAN, (int(self.x), int(self.y)), int(self.radius), 6)
        pygame.draw.circle(surface, (0, 255, 255, 100), (int(self.x), int(self.y)), int(self.radius + 10), 4)

# ======================
# EYWA SEED (COIN / KOLEKSI)
# ======================
class Coin(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40)
        self.speed = random.uniform(1.5, 3.5)
        self.glow_phase = random.random() * math.tau
        self.load_image('eywa.png')
    
    def update(self):
        self.x -= self.speed
        self.glow_phase += 0.15
        self.rect.center = (self.x, self.y)
    
    # Efek glow berdenyut seperti biji Eywa
    def draw(self, surface):
        intensity = 100 + 155 * abs(math.sin(self.glow_phase))
        color = (0, intensity // 3, intensity)
        center = self.rect.center
        pygame.draw.circle(surface, color, center, 20)
        pygame.draw.circle(surface, GLOW_CYAN, center, 20, 4)
        if self.image:
            self.draw_image(surface)

# ======================
# PEMAIN: TULKUN
# ======================
class Tulkun(GameObject):
    def __init__(self):
        super().__init__(100, SCREEN_HEIGHT // 2 - 50, 200, 100)
        self.speed = 5
        self.health = 5
        self.max_health = 5
        self.load_image('tulkun.png')
    
    # Input gerak pemain menggunakan WASD atau arrow keys
    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = self.speed
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = self.speed
        self.x += dx
        self.y += dy
        # Batas layar agar tidak keluar
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(0, min(SCREEN_HEIGHT - self.height, self.y))
        self.rect.topleft = (self.x, self.y)
    
    def draw(self, surface):
        if self.image:
            self.draw_image(surface)
        else:
            # Fallback jika gambar tidak ada
            pygame.draw.ellipse(surface, (100, 150, 200), self.rect)
            pygame.draw.ellipse(surface, GLOW_CYAN, (self.rect.right - 30, self.rect.centery - 15, 40, 30))

# ======================
# MUSUH: HUNTER SHIP (KAPAL RDA)
# ======================
class HunterShip(GameObject):
    def __init__(self, base_speed=2):
        y = random.randint(80, SCREEN_HEIGHT - 130)
        super().__init__(SCREEN_WIDTH + 50, y, 120, 60)
        self.speed = base_speed + random.uniform(0.5, 2)
        self.shoot_timer = random.randint(80, 160)
        self.load_image('ship.png')
    
    # Musuh bergerak dari kanan ke kiri dan countdown untuk menembak
    def update(self):
        self.x -= self.speed
        self.rect.topleft = (self.x, self.y)
        self.shoot_timer -= 1
    
    def draw(self, surface):
        if self.image:
            self.draw_image(surface)
        else:
            # Fallback gambar kapal
            pygame.draw.rect(surface, (80, 80, 80), self.rect)
            pygame.draw.polygon(surface, RED_DANGER, [
                (self.rect.right, self.rect.top + 10),
                (self.rect.right + 40, self.rect.centery),
                (self.rect.right, self.rect.bottom - 10)
            ])

# ======================
# KELAS UTAMA PENGATUR GAME (GAME MANAGER)
# ======================
class Game:
    def __init__(self):
        # Inisialisasi semua objek game
        self.tulkun = Tulkun()
        self.ships = []
        self.harpoons = []
        self.waves = []
        self.coins = []
        self.particles = []
        self.score = 0
        self.high_score = self.load_high_score()
        self.font = pygame.font.SysFont("Arial", 36, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 24)
        self.ship_timer = 0
        self.coin_timer = 0
        self.base_ship_speed = 2.0
        
        # Flag untuk mendeteksi pertama kali game over
        self.is_game_over = False
        
        # Memuat background dan sound effects
        self.background = None
        self.load_background('background.jpg')
        
        # Memuat semua SFX
        self.sounds = {}
        sound_files = {
            'wave': 'wave.mp3',
            'explosion': 'explosion.mp3',
            'coin': 'coin.mp3',
            'harpoon': 'harpoon.mp3'
        }
        for key, filename in sound_files.items():
            path = os.path.join('assets', filename)
            if os.path.exists(path):
                try:
                    self.sounds[key] = pygame.mixer.Sound(path)
                    self.sounds[key].set_volume(0.5)
                    print(f"SFX dimuat: {filename}")
                except:
                    print(f"Gagal load SFX: {filename}")
            else:
                print(f"SFX tidak ditemukan: {filename}")
        
        # Mulai musik latar normal
        self.play_normal_music()
    
    # Memutar musik ambient lautan saat permainan normal
    def play_normal_music(self):
        try:
            pygame.mixer.music.load(os.path.join('assets', 'ocean_bg.mp3'))
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.3)
            print("Memutar musik normal: ocean_bg.mp3")
        except:
            print("ocean_bg.mp3 tidak ditemukan")
    
    # Ganti musik menjadi "The Songcord" saat game over
    def play_game_over_music(self):
        try:
            pygame.mixer.music.load(os.path.join('assets', 'the_songcord.mp3'))
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.4)
            print("Game Over - Memutar: the_songcord.mp3")
        except:
            print("the_songcord.mp3 tidak ditemukan - musik game over tidak diputar")
    
    # Memainkan sound effect tertentu
    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()
    
    # Memuat background dari assets
    def load_background(self, filename):
        path = os.path.join('assets', filename)
        if os.path.exists(path):
            self.background = pygame.image.load(path).convert()
            print(f"Background dimuat: {filename}")
    
    # Membaca high score dari file JSON
    def load_high_score(self):
        if os.path.exists('highscore.json'):
            with open('highscore.json', 'r') as f:
                return json.load(f).get('high_score', 0)
        return 0
    
    # Menyimpan high score jika skor saat ini lebih tinggi
    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            with open('highscore.json', 'w') as f:
                json.dump({'high_score': self.high_score}, f)
    
    # Spawn musuh baru
    def spawn_ship(self):
        self.ships.append(HunterShip(self.base_ship_speed))
    
    # Spawn Eywa Seed (coin)
    def spawn_coin(self, x=None, y=None):
        x = x or SCREEN_WIDTH + 50
        y = y or random.randint(80, SCREEN_HEIGHT - 100)
        self.coins.append(Coin(x, y))
    
    # Efek ledakan dengan banyak partikel
    def spawn_explosion(self, x, y):
        for _ in range(30):
            self.particles.append(Particle(x, y))
    
    # Tembak Sonic Wave dari posisi Tulkun
    def shoot_wave(self):
        self.waves.append(SonicWave(self.tulkun.rect.right + 20, self.tulkun.rect.centery))
        self.play_sound('wave')
    
    # Logika utama game setiap frame
    def update(self):
        # Deteksi game over dan ganti musik sekali saja
        if self.tulkun.health <= 0 and not self.is_game_over:
            self.is_game_over = True
            self.play_game_over_music()
            self.save_high_score()
        
        # Hanya jalankan logika jika belum game over
        if self.tulkun.health > 0:
            self.tulkun.handle_input()
            
            # Tingkatkan kesulitan seiring skor
            self.base_ship_speed = 2.0 + (self.score // 400) * 0.6
            
            # Timer spawn musuh
            self.ship_timer += 1
            if self.ship_timer > max(50, 120 - (self.score // 150)):
                self.spawn_ship()
                self.ship_timer = 0
            
            # Timer spawn coin acak
            self.coin_timer += 1
            if self.coin_timer > 150:
                self.spawn_coin()
                self.coin_timer = 0
            
            # Update semua musuh dan logika tembak harpoon
            for ship in self.ships[:]:
                ship.update()
                if ship.shoot_timer <= 0:
                    dx = (self.tulkun.x - ship.x) / 150
                    dy = (self.tulkun.y - ship.y) / 150
                    self.harpoons.append(Harpoon(ship.rect.left - 20, ship.rect.centery, -10 + dx, dy))
                    self.play_sound('harpoon')
                    ship.shoot_timer = random.randint(100, 200)
                if ship.x < -150:
                    self.ships.remove(ship)
            
            # Update semua objek bergerak
            for obj in self.harpoons + self.waves + self.coins + self.particles:
                obj.update()
            
            # Deteksi Sonic Wave mengenai kapal
            for wave in self.waves[:]:
                for ship in self.ships[:]:
                    dist = math.hypot(wave.x - ship.rect.centerx, wave.y - ship.rect.centery)
                    if dist < wave.radius + 40:
                        self.spawn_explosion(ship.rect.centerx, ship.rect.centery)
                        self.play_sound('explosion')
                        if ship in self.ships:
                            self.ships.remove(ship)
                        self.score += 50
                        self.spawn_coin(ship.x, ship.y)
                        break
            
            # Deteksi harpoon mengenai Tulkun
            for harpoon in self.harpoons[:]:
                if harpoon.rect.colliderect(self.tulkun.rect):
                    self.harpoons.remove(harpoon)
                    self.tulkun.health -= 1
                    self.spawn_explosion(self.tulkun.rect.centerx, self.tulkun.rect.centery)
                    self.play_sound('explosion')
            
            # Deteksi ambil coin
            for coin in self.coins[:]:
                if self.tulkun.rect.colliderect(coin.rect):
                    self.coins.remove(coin)
                    self.score += 10
                    self.play_sound('coin')
            
            # Bersihkan objek yang sudah tidak diperlukan
            self.particles = [p for p in self.particles if p.life > 0]
            self.harpoons = [h for h in self.harpoons if h.x > -100]
            self.waves = [w for w in self.waves if w.x < SCREEN_WIDTH + 200]
            self.coins = [c for c in self.coins if c.x > -100]
    
    # Menggambar semua elemen ke layar
    def draw(self, surface):
        # Gambar background
        if self.background:
            scaled_bg = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))
            surface.blit(scaled_bg, (0, 0))
        else:
            surface.fill(OCEAN_BLUE)
            for _ in range(30):
                pygame.draw.circle(surface, (0, 60, 120, 100),
                                   (random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)),
                                   random.randint(30, 100))
        
        # Gambar semua objek game
        self.tulkun.draw(surface)
        for obj_list in [self.ships, self.harpoons, self.waves, self.coins, self.particles]:
            for obj in obj_list:
                obj.draw(surface)
        
        # Tampilkan UI: teks skor dan health
        health_text = self.font.render(f"Spirit Strength: {self.tulkun.health}/5", True, GLOW_CYAN)
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        high_text = self.small_font.render(f"High Score: {self.high_score}", True, YELLOW_GLOW)
        surface.blit(health_text, (20, 20))
        surface.blit(score_text, (20, 70))
        surface.blit(high_text, (20, 120))
        
        # Health bar visual
        bar_x, bar_y = 20, 160
        bar_width = 250
        bar_height = 25
        fill_width = (self.tulkun.health / self.tulkun.max_health) * bar_width
        pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=12)
        pygame.draw.rect(surface, GLOW_CYAN, (bar_x, bar_y, fill_width, bar_height), border_radius=12)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 4, border_radius=12)
        
        # Layar game over dengan overlay gelap
        if self.tulkun.health <= 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            game_over = self.font.render("The Great Balance is Broken...", True, RED_DANGER)
            restart = self.small_font.render("Press R to Connect Again with Eywa", True, WHITE)
            surface.blit(game_over, (SCREEN_WIDTH//2 - game_over.get_width()//2, SCREEN_HEIGHT//2 - 60))
            surface.blit(restart, (SCREEN_WIDTH//2 - restart.get_width()//2, SCREEN_HEIGHT//2 + 10))
        
        pygame.display.flip()

# ======================
# MAIN LOOP GAME
# ======================
def main():
    game = Game()
    running = True
    
    while running:
        # Handle event (tombol ditekan, quit, dll)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and game.tulkun.health > 0:
                    game.shoot_wave()
                if event.key == pygame.K_r and game.tulkun.health <= 0:
                    game = Game()  # Restart game
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update dan gambar setiap frame
        game.update()
        game.draw(screen)
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()