import sys
import time
import random
import math

# --- ANSI DISPLAY CORE ---
C_HIDE = '\033[?25l'
C_SHOW = '\033[?25h'
HOME = '\033[H'
CLEAR = '\033[2J'

# Colors
G = '\033[1;32m'
DG = '\033[0;32m'
C = '\033[1;36m'
W = '\033[1;37m'
R = '\033[1;31m'
Y = '\033[1;33m'
D = '\033[1;30m'
M = '\033[1;35m'
RESET = '\033[0m'

def move(y, x):
    return f'\033[{y};{x}H'

def p(text):
    sys.stdout.write(text)

# --- MATH & KINEMATICS ---
class Node:
    def __init__(self, id_str, is_hostile=False):
        self.id = id_str
        self.angle = random.uniform(0, math.pi * 2)
        self.radius = random.uniform(10.0, 18.0)
        self.speed = random.uniform(0.05, 0.15)
        self.is_hostile = is_hostile
        self.x = 0
        self.y = 0
        
    def update(self, converge_active):
        self.angle += self.speed
        if converge_active and not self.is_hostile:
            self.radius -= 0.05
            if self.radius < 2.0:
                self.radius = 2.0
        
        # Center of map is (22, 7) relative to map origin
        self.x = int(22 + (self.radius * 2) * math.cos(self.angle))
        self.y = int(7 + self.radius * math.sin(self.angle))

nodes = [Node(f"SKN-{random.randint(100,999)}N", False) for _ in range(6)]
hostiles = [Node(f"UAP-{random.randint(10,99)}X", True) for _ in range(3)]

# --- UI RENDER LOOP ---
def draw_bar(val, max_val, width, color):
    filled = int((val / max_val) * width)
    bar = "█" * filled + " " * (width - filled)
    return f"{color}[{bar}]{RESET}"

def run_tui():
    p(CLEAR + C_HIDE + HOME)
    sys.stdout.flush()
    
    # Draw Static UI
    p(move(1,1) + f"{W}[ SOVEREIGN STRATCOM // ORBITAL KINEMATICS v6.3 ]{RESET}")
    p(move(2,1) + f"{D}ARCHITECT: {W}C.E. HOLLAND{D}   SUBSTRATE: {W}SB ELITE{D}   SHIZUKU: {G}CONNECTED{D}   RUNTIME: {C}PyT{RESET}")
    
    p(move(4,1) + f"{C}[FLIGHT DYNAMICS]{RESET}")
    p(move(5,1) + f"{D}│{RESET} TEMP")
    p(move(6,1) + f"{D}│{RESET} CPU")
    p(move(7,1) + f"{D}│{RESET} MEM")
    
    p(move(9,1) + f"{C}[TOPOLOGICAL GOVERNANCE]{RESET}")
    p(move(10,1) + f"{D}│{RESET} ΔG")
    p(move(11,1) + f"{D}│{RESET} MANIFOLD  {W}SIMPLY_CONNECTED{RESET}")
    p(move(12,1) + f"{D}│{RESET} BETTI     {G}β_1=0 β_2=0{RESET}")
    
    p(move(22,1) + f"{C}[THREAT VECTORS]{RESET}")
    
    threat_log = []
    step = 0
    converge = False
    
    try:
        while True:
            buffer = ""
            step += 1
            if step > 50: converge = True
            
            # 1. Update Flight Dynamics
            temp = 37.0 + math.sin(step * 0.1) * 2.5
            cpu = 12.4 + random.uniform(-2, 5)
            mem = 7.82 + random.uniform(-0.1, 0.1)
            
            t_col = R if temp > 38.5 else G
            buffer += move(5, 7) + f"{t_col}{temp:04.1f}°C {draw_bar(temp, 45, 15, t_col)}"
            buffer += move(6, 7) + f"{W}{cpu:04.1f}%  {draw_bar(cpu, 100, 15, G)}"
            buffer += move(7, 7) + f"{W}{mem:04.2f} GB / 10.85 GB {draw_bar(mem, 12, 15, G)}"
            
            # 2. Update Topological Governance
            delta_g = int(28000 + math.cos(step * 0.05) * 2000)
            buffer += move(10, 7) + f"{W}{delta_g:,}{RESET}    "
            
            # 3. Draw Map Background (Grid 45x15 at X=35, Y=4)
            map_base_x = 35
            map_base_y = 4
            for y in range(15):
                row = ""
                for x in range(45):
                    if random.random() < 0.02:
                        row += f"{D}.{RESET}"
                    else:
                        row += " "
                buffer += move(map_base_y + y, map_base_x) + row
            
            # 4. Render Nodes on Map
            buffer += move(map_base_y + 7, map_base_x + 22) + f"{W}┼{RESET}" # Center
            
            for n in hostiles:
                n.update(False)
                if 0 <= n.x < 45 and 0 <= n.y < 15:
                    buffer += move(map_base_y + n.y, map_base_x + n.x) + f"{R}█{RESET}"
                    
            for n in nodes:
                n.update(converge)
                if 0 <= n.x < 45 and 0 <= n.y < 15:
                    # Trailing effect
                    buffer += move(map_base_y + n.y, map_base_x + n.x) + f"{G}█{RESET}"
                    
            # 5. Threat Vectors (Scrolling log)
            if step % 3 == 0:
                threat = random.choice(hostiles).id
                val = random.uniform(0.60, 0.99)
                threat_log.append(f"{D}│ TRACK:{RESET} {threat} {D}|{RESET} THREAT {R}{val:.2f}{RESET}")
                if len(threat_log) > 6:
                    threat_log.pop(0)
            
            for i, log_line in enumerate(threat_log):
                buffer += move(23 + i, 1) + log_line + "         "
                
            buffer += move(30, 1) + f"{D}[core/python3] VERITAS_GATE: {W}VINCIT OMNIA VERITAS{RESET}"
            
            # Flush frame to screen
            p(buffer)
            sys.stdout.flush()
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        p(C_SHOW + move(32, 1) + "\n")
        sys.exit(0)

if __name__ == "__main__":
    run_tui()

