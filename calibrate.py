import csv
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from sklearn.ensemble import RandomForestRegressor

# This script requires the Turbo library and dbfread/dbf packages.
# Install dependencies before running:
# pip install turbo scikit-learn dbfread dbf

FF_FILE = 'FF-PK.DBF'
LOG_FILE = 'log-turbo.csv'
FF_LOG_FILE = 'Xxxx.csv'

DIMENSION = 220
MAX_ITERS = 1000
BATCH_SIZE = 6


def read_log():
    history_x = []
    history_y = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                y = float(row['fitness'])
                # friction factors are stored as flattened vectors if present
                if 'ff' in row:
                    x = np.fromstring(row['ff'], sep=' ')
                    if len(x) == DIMENSION:
                        history_x.append(x)
                        history_y.append(y)
                else:
                    history_y.append(y)
    return history_x, history_y


def log_iteration(iteration, ff_values, fitness):
    exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        fieldnames = ['iteration', 'fitness', 'ff']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({
            'iteration': iteration,
            'fitness': fitness,
            'ff': ' '.join(map(str, ff_values))
        })


# Placeholder DBF update function. Requires dbf package.
# Updates HBSH-PK field for each record

def update_friction_factors(ff_values):
    import dbf
    table = dbf.Table(FF_FILE)
    table.open(mode=dbf.READ_WRITE)
    for rec, val in zip(table, ff_values):
        rec['HBSH-PK'] = val
        rec.store()
    table.close()


def append_ff_csv(ff_values, iteration):
    column = f'Iteration-{iteration:04d}'
    if not os.path.exists(FF_LOG_FILE):
        with open(FF_LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ['Index', column]
            writer.writerow(header)
            for i, val in enumerate(ff_values, 1):
                writer.writerow([i, val])
    else:
        with open(FF_LOG_FILE, newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0] + [column]
        new_rows = []
        for i, row in enumerate(rows[1:]):
            row.append(str(ff_values[i]))
            new_rows.append(row)
        with open(FF_LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_rows)


def run_external_scripts():
    subprocess.run(['runtpp', 'script1.s'], check=True)
    subprocess.run(['runtpp', 'script2.s'], check=True)
    with open('cr.txt') as f:
        value = float(f.read().strip())
    os.remove('cr.txt')
    return value


def evaluate(ff_values, iteration):
    update_friction_factors(ff_values)
    fitness = run_external_scripts()
    append_ff_csv(ff_values, iteration)
    log_iteration(iteration, ff_values, fitness)
    return fitness


def propose_candidates(model, num, lb, ub):
    # Sample many random points and pick those with lowest predicted fitness
    xs = np.random.uniform(lb, ub, size=(1000, DIMENSION))
    preds = model.predict(xs)
    inds = np.argsort(preds)[:num]
    return xs[inds]


def main():
    lb = np.zeros(DIMENSION)
    ub = np.ones(DIMENSION) * 10

    X_hist, y_hist = read_log()
    iteration = len(y_hist) + 1
    stagnation = []

    while iteration <= MAX_ITERS:
        if len(X_hist) < 10:
            candidates = np.random.uniform(lb, ub, size=(BATCH_SIZE, DIMENSION))
        else:
            model = RandomForestRegressor()
            model.fit(np.array(X_hist), np.array(y_hist))
            candidates = propose_candidates(model, BATCH_SIZE, lb, ub)

        with ProcessPoolExecutor(max_workers=BATCH_SIZE) as ex:
            futures = [ex.submit(evaluate, cand, iteration + i) for i, cand in enumerate(candidates)]
            results = [f.result() for f in futures]

        for cand, fit in zip(candidates, results):
            print('=========', flush=True)
            print(f'Iteration {iteration}: fitness {fit}', flush=True)
            print('=========', flush=True)
            X_hist.append(cand)
            y_hist.append(fit)
            iteration += 1
            if len(stagnation) < 3:
                stagnation.append(fit)
            else:
                stagnation.pop(0)
                stagnation.append(fit)
            if len(stagnation) == 3 and max(stagnation) - min(stagnation) < 0.01:
                return

if __name__ == '__main__':
    main()
