# app.py
import streamlit as st
import random
import pandas as pd
from collections import defaultdict

# -----------------------
# Config page
# -----------------------
st.set_page_config(page_title="Optimasi Penjadwalan Mata Kuliah", layout="wide")

# -----------------------
# Styling (ONLY UI, not logic)
# -----------------------
st.markdown("""
    <style>
    .title { font-size:26px; font-weight:700; color:#1363DF; text-align:left; }
    .subtitle { color:#333; margin-bottom:10px; }
    .stButton>button { background-color: #1363DF; color: white; }
    .stAlert { border-radius:8px; }
    /* smaller table padding */
    .stTable table td, .stTable table th { padding: 8px 10px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------
# Session-state containers (preserve user's data)
# -----------------------
if "courses" not in st.session_state:
    st.session_state.courses = []   # list of dicts: kode, mata_kuliah, dosen
if "rooms" not in st.session_state:
    st.session_state.rooms = []     # list of room names
if "timeslots" not in st.session_state:
    st.session_state.timeslots = [] # list of "Hari Sesi" strings

# -----------------------
# Page title & description
# -----------------------
st.markdown('<div class="title">📅 Optimasi Penjadwalan Mata Kuliah</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Masukkan data (Kode Mata Kuliah, Mata Kuliah, Dosen, Ruang, Sesi). Klik <b>Generate Jadwal</b> untuk menjalankan Genetic Algorithm.</div>', unsafe_allow_html=True)

# -----------------------
# Tabs: input forms (unchanged semantics)
# -----------------------
tab1, tab2, tab3 = st.tabs(["Mata Kuliah", "Ruang Kuliah", "Sesi Kuliah"])

with tab1:
    with st.form("form_course", clear_on_submit=True):
        course_code = st.text_input("Kode Mata Kuliah")
        course_name = st.text_input("Nama Mata Kuliah")
        lecturer = st.text_input("Nama Dosen")
        submit_course = st.form_submit_button("Tambah Mata Kuliah")
        if submit_course:
            if course_code.strip() and course_name.strip() and lecturer.strip():
                st.session_state.courses.append({
                    "kode": course_code.strip(),
                    "mata_kuliah": course_name.strip(),
                    "dosen": lecturer.strip()
                })
                st.success(f"Mata kuliah '{course_name.strip()}' ditambahkan.")
            else:
                st.error("Isi semua field (kode, nama, dosen).")

    if st.session_state.courses:
        df_courses = pd.DataFrame(st.session_state.courses)
        df_courses.index = range(1, len(df_courses) + 1)
        df_courses.index.name = "No"
        st.subheader("Daftar Mata Kuliah")
        st.table(df_courses)

with tab2:
    with st.form("form_room", clear_on_submit=True):
        room_name = st.text_input("Nama Ruang")
        submit_room = st.form_submit_button("Tambah Ruang")
        if submit_room:
            if room_name.strip():
                st.session_state.rooms.append(room_name.strip())
                st.success(f"Ruang '{room_name.strip()}' ditambahkan.")
            else:
                st.error("Nama ruang tidak boleh kosong.")
    if st.session_state.rooms:
        df_rooms = pd.DataFrame(st.session_state.rooms, columns=["Ruang"])
        df_rooms.index = range(1, len(df_rooms) + 1)
        df_rooms.index.name = "No"
        st.subheader("Daftar Ruang")
        st.table(df_rooms)

with tab3:
    with st.form("form_time", clear_on_submit=True):
        day = st.selectbox("Hari", ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"])
        session = st.selectbox("Sesi", ["Sesi 1", "Sesi 2", "Sesi 3", "Sesi 4"])
        submit_time = st.form_submit_button("Tambah Sesi")
        if submit_time:
            ts = f"{day} {session}"
            st.session_state.timeslots.append(ts)
            st.success(f"Sesi '{ts}' ditambahkan.")
    if st.session_state.timeslots:
        df_times = pd.DataFrame(st.session_state.timeslots, columns=["Hari & Sesi"])
        df_times.index = range(1, len(df_times) + 1)
        df_times.index.name = "No"
        st.subheader("Daftar Sesi")
        st.table(df_times)

# -----------------------
# Sidebar: GA parameters (tweakable)
# -----------------------
st.sidebar.header("Pengaturan Genetic Algorithm")
POP_SIZE = st.sidebar.number_input("Population size", min_value=10, max_value=1000, value=80, step=10)
GENERATIONS = st.sidebar.number_input("Generations", min_value=10, max_value=2000, value=300, step=10)
CROSSOVER_RATE = st.sidebar.slider("Crossover rate", 0.0, 1.0, 0.8)
MUTATION_RATE = st.sidebar.slider("Mutation rate", 0.0, 1.0, 0.05)
ELITISM = st.sidebar.number_input("Elitism (keep best)", min_value=0, max_value=20, value=2, step=1)
SEED = st.sidebar.number_input("Random seed (0 = random)", min_value=0, value=42, step=1)

# -----------------------
# Small helpers for GA (do not change app logic)
# -----------------------
def _make_sessions():
    # produce list of sessions (one per course)
    sessions = []
    for c in st.session_state.courses:
        sessions.append({
            "kode": c["kode"],
            "mata_kuliah": c["mata_kuliah"],
            "dosen": c["dosen"]
        })
    return sessions

def generate_initial_population(pop_size):
    sessions = _make_sessions()
    population = []
    room_pool = st.session_state.rooms.copy()
    ts_pool = st.session_state.timeslots.copy()
    if not room_pool or not ts_pool:
        return []
    for _ in range(pop_size):
        indiv = []
        for s in sessions:
            indiv.append({
                "kode": s["kode"],
                "mata_kuliah": s["mata_kuliah"],
                "dosen": s["dosen"],
                "ruang": random.choice(room_pool),
                "waktu": random.choice(ts_pool)
            })
        population.append(indiv)
    return population

def evaluate_penalty(indiv):
    """
    Penalty-based fitness:
    - heavy penalty for room-time conflict
    - heavy penalty for dosen-time conflict
    - small penalty for duplicate mata kuliah in same time (if any)
    Lower penalty is better; fitness = 1/(1+penalty)
    """
    penalty = 0
    room_time = defaultdict(list)
    dosen_time = defaultdict(list)
    code_time = defaultdict(list)
    for i, s in enumerate(indiv):
        rt = (s["ruang"], s["waktu"])
        dt = (s["dosen"], s["waktu"])
        ct = (s["kode"], s["waktu"])
        room_time[rt].append(i)
        dosen_time[dt].append(i)
        code_time[ct].append(i)
    # count conflicts
    for k, v in room_time.items():
        if len(v) > 1:
            penalty += (len(v)-1) * 10
    for k, v in dosen_time.items():
        if len(v) > 1:
            penalty += (len(v)-1) * 15
    for k, v in code_time.items():
        if len(v) > 1:
            penalty += (len(v)-1) * 2
    return penalty

def fitness(indiv):
    pen = evaluate_penalty(indiv)
    return 1.0 / (1.0 + pen)

# GA operators
def tournament_selection(pop, fitnesses, k=3):
    idxs = random.sample(range(len(pop)), k if k < len(pop) else len(pop))
    best = idxs[0]
    for i in idxs[1:]:
        if fitnesses[i] > fitnesses[best]:
            best = i
    return pop[best]

def single_point_crossover(a, b):
    n = len(a)
    if n < 2:
        return a.copy(), b.copy()
    pt = random.randint(1, n-1)
    child1 = [dict(x) for x in (a[:pt] + b[pt:])]
    child2 = [dict(x) for x in (b[:pt] + a[pt:])]
    return child1, child2

def mutate(ind, mutation_rate):
    room_pool = st.session_state.rooms
    ts_pool = st.session_state.timeslots
    for i in range(len(ind)):
        if random.random() < mutation_rate:
            if random.random() < 0.6:
                ind[i]["waktu"] = random.choice(ts_pool)
            if random.random() < 0.7:
                ind[i]["ruang"] = random.choice(room_pool)
    return ind

def run_ga(pop_size, generations, crossover_rate, mutation_rate, elitism):
    if SEED != 0:
        random.seed(SEED)
    pop = generate_initial_population(pop_size)
    if not pop:
        return None, "Tidak ada room atau timeslot yang terdaftar."

    best_overall = None
    best_pen = float("inf")

    for gen in range(1, generations+1):
        fitnesses = [fitness(ind) for ind in pop]
        penalties = [evaluate_penalty(ind) for ind in pop]

        # update best
        min_pen = min(penalties)
        idx_min = penalties.index(min_pen)
        if min_pen < best_pen:
            best_pen = min_pen
            best_overall = [dict(x) for x in pop[idx_min]]

        # build next population
        new_pop = []
        # elitism: copy best individuals
        sorted_idx = sorted(range(len(pop)), key=lambda i: penalties[i])
        for e in range(min(elitism, len(pop))):
            new_pop.append([dict(x) for x in pop[sorted_idx[e]]])

        # fill rest
        while len(new_pop) < pop_size:
            parent_a = tournament_selection(pop, fitnesses)
            parent_b = tournament_selection(pop, fitnesses)
            if random.random() < crossover_rate:
                child1, child2 = single_point_crossover(parent_a, parent_b)
            else:
                child1, child2 = [dict(x) for x in parent_a], [dict(x) for x in parent_b]
            child1 = mutate(child1, mutation_rate)
            child2 = mutate(child2, mutation_rate)
            new_pop.append(child1)
            if len(new_pop) < pop_size:
                new_pop.append(child2)
        pop = new_pop

    return best_overall, best_pen

# -----------------------
# Color map for days (styling only)
# -----------------------
color_map = {
    "Senin": "#E8F8F5",
    "Selasa": "#FDEDEC",
    "Rabu": "#FEF9E7",
    "Kamis": "#F4F6F7",
    "Jumat": "#F5EEF8",
    "Sabtu": "#FEF5E7"
}

def style_schedule_df(df):
    # add No column if not present
    if "No" not in df.columns:
        df.insert(0, "No", range(1, len(df)+1))
    # styler
    def row_color(row):
        hari = row["waktu"].split()[0] if isinstance(row["waktu"], str) else ""
        bg = color_map.get(hari, "")
        return [f"background-color: {bg}" for _ in row]
    sty = df.style.apply(row_color, axis=1)\
                  .set_properties(**{"text-align": "center", "padding": "6px"})\
                  .set_table_styles([{"selector":"th", "props":[("background-color","#2F4F4F"),("color","white"),("text-align","center")]}])
    return sty

# -----------------------
# Run button (main)
# -----------------------
if st.button("🚀 Generate Jadwal"):
    # validation: must have courses, rooms, timeslots
    if not st.session_state.courses:
        st.error("Daftar mata kuliah kosong — tambahkan minimal 1.")
    elif not st.session_state.rooms:
        st.error("Daftar ruang kosong — tambahkan minimal 1.")
    elif not st.session_state.timeslots:
        st.error("Daftar sesi kosong — tambahkan minimal 1.")
    else:
        with st.spinner("Menjalankan Genetic Algorithm (sedang optimasi)..."):
            best, best_pen = run_ga(POP_SIZE, GENERATIONS, CROSSOVER_RATE, MUTATION_RATE, ELITISM)
        if best is None:
            st.error("GA gagal dijalankan (cek rooms/timeslots).")
        else:
            df = pd.DataFrame(best)
            df.index = range(1, len(df) + 1)
            df.index.name = "No"
            st.subheader("Hasil Jadwal Kuliah Optimal")
            st.write(f"Penalty (semakin kecil semakin bagus): {best_pen}")
            st.dataframe(style_schedule_df(df), use_container_width=True)

# -----------------------
# Footer: tips
# -----------------------
st.markdown("---")
st.markdown("**Tips:** jika masih ada bentrok (penalty > 0), coba naikkan *Generations* atau *Population size*, atau tambahkan lebih banyak timeslot/ruang.")
