import random
from collections import defaultdict
import streamlit as st

def generate_initial_population(pop_size):
    sessions = [
        {"kode": c["kode"], "mata_kuliah": c["mata_kuliah"], "dosen": c["dosen"]}
        for c in st.session_state.courses
    ]
    room_pool = st.session_state.rooms.copy()
    ts_pool = st.session_state.timeslots.copy()
    if not room_pool or not ts_pool:
        return []
    return [
        [
            {
                **s,
                "ruang": random.choice(room_pool),
                "waktu": random.choice(ts_pool)
            }
            for s in sessions
        ]
        for _ in range(pop_size)
    ]

def evaluate_penalty(indiv):
    penalty = 0
    room_time = defaultdict(list)
    dosen_time = defaultdict(list)
    code_time = defaultdict(list)
    for i, s in enumerate(indiv):
        room_time[(s["ruang"], s["waktu"])].append(i)
        dosen_time[(s["dosen"], s["waktu"])].append(i)
        code_time[(s["kode"], s["waktu"])].append(i)
    for v in room_time.values():
        if len(v) > 1:
            penalty += (len(v)-1) * 10
    for v in dosen_time.values():
        if len(v) > 1:
            penalty += (len(v)-1) * 15
    for v in code_time.values():
        if len(v) > 1:
            penalty += (len(v)-1) * 2
    return penalty

def fitness(indiv):
    return 1.0 / (1.0 + evaluate_penalty(indiv))

def tournament_selection(pop, fitnesses, k=3):
    idxs = random.sample(range(len(pop)), min(k, len(pop)))
    return pop[max(idxs, key=lambda i: fitnesses[i])]

def single_point_crossover(a, b):
    n = len(a)
    if n < 2:
        return a.copy(), b.copy()
    pt = random.randint(1, n-1)
    return a[:pt] + b[pt:], b[:pt] + a[pt:]

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

def run_ga(pop_size, generations, crossover_rate, mutation_rate, elitism, seed):
    if seed != 0:
        random.seed(seed)
    pop = generate_initial_population(pop_size)
    if not pop:
        return None, "Tidak ada room atau timeslot yang terdaftar."

    best_overall, best_pen = None, float("inf")
    for _ in range(generations):
        fitnesses = [fitness(ind) for ind in pop]
        penalties = [evaluate_penalty(ind) for ind in pop]
        min_pen = min(penalties)
        idx_min = penalties.index(min_pen)
        if min_pen < best_pen:
            best_pen = min_pen
            best_overall = [dict(x) for x in pop[idx_min]]
        new_pop = []
        sorted_idx = sorted(range(len(pop)), key=lambda i: penalties[i])
        for e in range(min(elitism, len(pop))):
            new_pop.append([dict(x) for x in pop[sorted_idx[e]]])
        while len(new_pop) < pop_size:
            pa = tournament_selection(pop, fitnesses)
            pb = tournament_selection(pop, fitnesses)
            if random.random() < crossover_rate:
                c1, c2 = single_point_crossover(pa, pb)
            else:
                c1, c2 = [dict(x) for x in pa], [dict(x) for x in pb]
            new_pop.append(mutate(c1, mutation_rate))
            if len(new_pop) < pop_size:
                new_pop.append(mutate(c2, mutation_rate))
        pop = new_pop
    return best_overall, best_pen
