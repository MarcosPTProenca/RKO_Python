//! Neighborhood local searches and Random Variable Neighborhood Descent.
//!
//! Objective:
//! - Provide swap, mirror and Farey-interval sweeps plus the RVND driver that
//!   combines them with Nelder-Mead, all on reusable scratch buffers.
//!
//! Technical approach:
//! - Every sweep visits a freshly shuffled coordinate order. Strategy 1 accepts an
//!   improving move immediately and continues from it (reverting rejected moves in
//!   place); strategy 2 scores every move against a fixed base and applies only the
//!   best one at the end.
//! - RVND repeatedly draws one of four neighborhoods at random from the remaining
//!   set, refreshing the set after an improvement and dropping the drawn
//!   neighborhood otherwise.
//!
//! Flow (pseudocode):
//! 1. Shuffle the visiting order.
//! 2. Evaluate each neighbor through `Search::eval`, keeping or reverting it.
//! 3. RVND: pick a neighborhood, run it on a copy, adopt it only if it improves.
//!
//! Important criteria:
//! - Cost per sweep is `O(n^2)` (swap), `O(n)` (mirror) and `O(18 n)` (Farey) evaluations.
//! - The incumbent cost is supplied by the caller and never re-evaluated.
//!
//! Inputs/Outputs:
//! - Input: keys, their cost, a strategy (1 or 2), `Search`, `Pool` and `Rng`.
//! - Output: improved keys in place and their cost.

use crate::operators::{NelderMead, PoolPolicy};
use crate::pool::Pool;
use crate::rng::Rng;
use crate::search::{Search, Stop};

/// Interval boundaries of the Farey discretization.
pub const FAREY: [f64; 19] = [
    0.00, 0.142_857, 0.166_667, 0.20, 0.25, 0.285_714, 0.333_333, 0.40, 0.428_571, 0.50, 0.571_429,
    0.60, 0.666_667, 0.714_286, 0.75, 0.80, 0.833_333, 0.857_143, 1.0,
];

/// Flips one key about 0.5, guarding values at the lower boundary.
#[inline]
fn mirrored(value: f64) -> f64 {
    if value > 0.000_01 {
        1.0 - value
    } else {
        0.999_99
    }
}

/// Reusable local-search engine with scratch buffers.
#[derive(Clone, Debug, Default)]
pub struct LocalSearch {
    order: Vec<usize>,
    candidate: Vec<f64>,
    nelder_mead: NelderMead,
}

impl LocalSearch {
    /// Creates an engine with empty buffers and random pool vertices.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Creates an engine whose Nelder-Mead uses the given pool vertex policy.
    #[must_use]
    pub fn with_policy(policy: PoolPolicy) -> Self {
        Self {
            order: Vec::new(),
            candidate: Vec::new(),
            nelder_mead: NelderMead::new(policy),
        }
    }

    /// Runs Nelder-Mead from `keys`.
    pub fn nelder_mead(
        &mut self,
        keys: &mut [f64],
        cost: f64,
        search: &mut Search<'_>,
        pool: &Pool,
        rng: &mut Rng,
    ) -> Result<f64, Stop> {
        self.nelder_mead.run(keys, cost, search, pool, rng)
    }

    fn shuffled_order(&mut self, n: usize, rng: &mut Rng) {
        self.order.clear();
        self.order.extend(0..n);
        rng.shuffle(&mut self.order);
    }

    /// Pairwise-swap sweep over all coordinate pairs.
    pub fn swap(
        &mut self,
        keys: &mut [f64],
        cost: f64,
        strategy: u8,
        search: &mut Search<'_>,
        rng: &mut Rng,
    ) -> Result<f64, Stop> {
        let n = keys.len();
        if n < 2 {
            return Ok(cost);
        }
        self.shuffled_order(n, rng);
        search.sync(keys);
        let mut best = cost;
        let mut chosen = None;
        for i in 0..n - 1 {
            for j in i + 1..n {
                let (a, b) = (self.order[i], self.order[j]);
                let changes = [(a, keys[b]), (b, keys[a])];
                let value = search.probe(keys, &changes)?;
                if value < best {
                    best = value;
                    if strategy == 1 {
                        search.commit(keys, &changes);
                    } else {
                        chosen = Some(changes);
                    }
                }
            }
        }
        if let Some(changes) = chosen {
            search.commit(keys, &changes);
        }
        Ok(best)
    }

    /// Single-coordinate mirror sweep.
    pub fn mirror(
        &mut self,
        keys: &mut [f64],
        cost: f64,
        strategy: u8,
        search: &mut Search<'_>,
        rng: &mut Rng,
    ) -> Result<f64, Stop> {
        let n = keys.len();
        if n == 0 {
            return Ok(cost);
        }
        self.shuffled_order(n, rng);
        search.sync(keys);
        let mut best = cost;
        let mut chosen = None;
        for position in 0..n {
            let index = self.order[position];
            let changes = [(index, mirrored(keys[index]))];
            let value = search.probe(keys, &changes)?;
            if value < best {
                best = value;
                if strategy == 1 {
                    search.commit(keys, &changes);
                } else {
                    chosen = Some(changes);
                }
            }
        }
        if let Some(changes) = chosen {
            search.commit(keys, &changes);
        }
        Ok(best)
    }

    /// Farey-interval resampling sweep over each coordinate.
    pub fn farey(
        &mut self,
        keys: &mut [f64],
        cost: f64,
        strategy: u8,
        search: &mut Search<'_>,
        rng: &mut Rng,
    ) -> Result<f64, Stop> {
        let n = keys.len();
        if n == 0 {
            return Ok(cost);
        }
        self.shuffled_order(n, rng);
        search.sync(keys);
        let mut best = cost;
        let mut chosen = None;
        for position in 0..n {
            let index = self.order[position];
            for interval in 0..FAREY.len() - 1 {
                let value = rng.uniform(FAREY[interval], FAREY[interval + 1]);
                let changes = [(index, value)];
                let result = search.probe(keys, &changes)?;
                if result < best {
                    best = result;
                    if strategy == 1 {
                        search.commit(keys, &changes);
                    } else {
                        chosen = Some(changes);
                    }
                }
            }
        }
        if let Some(changes) = chosen {
            search.commit(keys, &changes);
        }
        Ok(best)
    }

    /// Random Variable Neighborhood Descent over swap, mirror, Nelder-Mead and Farey.
    pub fn rvnd(
        &mut self,
        keys: &mut [f64],
        cost: f64,
        strategy: u8,
        search: &mut Search<'_>,
        pool: &Pool,
        rng: &mut Rng,
    ) -> Result<f64, Stop> {
        let mut current_cost = cost;
        let mut remaining = [0_u8, 1, 2, 3];
        let mut count = 4;
        let mut candidate = std::mem::take(&mut self.candidate);
        let result = (|| {
            while count > 0 {
                let position = rng.below(count);
                candidate.clear();
                candidate.extend_from_slice(keys);
                let value = match remaining[position] {
                    0 => self.swap(&mut candidate, current_cost, strategy, search, rng)?,
                    1 => self.mirror(&mut candidate, current_cost, strategy, search, rng)?,
                    2 => self
                        .nelder_mead
                        .run(&mut candidate, current_cost, search, pool, rng)?,
                    _ => self.farey(&mut candidate, current_cost, strategy, search, rng)?,
                };
                if value < current_cost {
                    keys.copy_from_slice(&candidate);
                    current_cost = value;
                    remaining = [0, 1, 2, 3];
                    count = 4;
                } else {
                    remaining[position] = remaining[count - 1];
                    count -= 1;
                }
            }
            Ok(current_cost)
        })();
        self.candidate = candidate;
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::operators::random_keys;
    use crate::problem::{Knapsack, Problem};
    use std::sync::atomic::AtomicBool;
    use std::time::{Duration, Instant};

    fn problem() -> Knapsack {
        let profits: Vec<i64> = (0..30).map(|index| 5 + (index * 17) % 23).collect();
        let weights: Vec<i64> = (0..30).map(|index| 3 + (index * 11) % 19).collect();
        Knapsack::new(&profits, &weights, 120)
    }

    fn run_sweep(
        strategy: u8,
        sweep: impl Fn(
            &mut LocalSearch,
            &mut [f64],
            f64,
            u8,
            &mut Search<'_>,
            &mut Rng,
        ) -> Result<f64, Stop>,
    ) {
        let problem = problem();
        let cancel = AtomicBool::new(false);
        let now = Instant::now();
        let mut search = Search::new(&problem, &cancel, now, now + Duration::from_secs(10), 0);
        let mut rng = Rng::new(3);
        let mut local = LocalSearch::new();
        for _ in 0..5 {
            let mut keys = vec![0.0; 30];
            random_keys(&mut keys, &mut rng);
            let before = problem.evaluate(&keys);
            let after = sweep(
                &mut local,
                &mut keys,
                before,
                strategy,
                &mut search,
                &mut rng,
            )
            .unwrap();
            assert!(after <= before);
            assert_eq!(
                after,
                problem.evaluate(&keys),
                "returned cost must match keys"
            );
            assert!(keys.iter().all(|key| (0.0..1.0).contains(key)));
        }
    }

    #[test]
    fn sweeps_return_consistent_costs_for_both_strategies() {
        for strategy in [1, 2] {
            run_sweep(strategy, |local, keys, cost, strategy, search, rng| {
                local.swap(keys, cost, strategy, search, rng)
            });
            run_sweep(strategy, |local, keys, cost, strategy, search, rng| {
                local.mirror(keys, cost, strategy, search, rng)
            });
            run_sweep(strategy, |local, keys, cost, strategy, search, rng| {
                local.farey(keys, cost, strategy, search, rng)
            });
        }
    }

    #[test]
    fn incremental_and_plain_evaluation_follow_identical_trajectories() {
        struct Plain(Knapsack);
        impl Problem for Plain {
            fn dimension(&self) -> usize {
                self.0.dimension()
            }
            fn evaluate(&self, keys: &[f64]) -> f64 {
                self.0.evaluate(keys)
            }
        }
        let fast = problem();
        let slow = Plain(fast.clone());
        let cancel = AtomicBool::new(false);
        for strategy in [1, 2] {
            let mut outcomes = Vec::new();
            for incremental in [true, false] {
                let target: &dyn Problem = if incremental { &fast } else { &slow };
                let now = Instant::now();
                let mut search =
                    Search::new(target, &cancel, now, now + Duration::from_secs(30), 0);
                let pool = Pool::new(5);
                let mut rng = Rng::new(21);
                let mut local = LocalSearch::new();
                let mut keys = vec![0.0; 30];
                random_keys(&mut keys, &mut rng);
                let start = search.eval(&keys).unwrap();
                let cost = local
                    .rvnd(&mut keys, start, strategy, &mut search, &pool, &mut rng)
                    .unwrap();
                outcomes.push((keys, cost, search.evaluations()));
            }
            assert_eq!(outcomes[0], outcomes[1], "strategy {strategy}");
        }
    }

    #[test]
    fn rvnd_reaches_local_optimum_for_all_neighborhoods() {
        let problem = problem();
        let cancel = AtomicBool::new(false);
        let now = Instant::now();
        let mut search = Search::new(&problem, &cancel, now, now + Duration::from_secs(30), 0);
        let pool = Pool::new(5);
        let mut rng = Rng::new(8);
        let mut local = LocalSearch::new();
        let mut keys = vec![0.0; 30];
        random_keys(&mut keys, &mut rng);
        let before = problem.evaluate(&keys);
        let after = local
            .rvnd(&mut keys, before, 1, &mut search, &pool, &mut rng)
            .unwrap();
        assert!(after < before);
        assert_eq!(after, problem.evaluate(&keys));
        let mut mirrored_keys = keys.clone();
        let again = local
            .mirror(&mut mirrored_keys, after, 2, &mut search, &mut rng)
            .unwrap();
        assert_eq!(again, after, "RVND result must be mirror-optimal");
    }

    #[test]
    fn deadline_interrupts_a_long_sweep() {
        let problem = Knapsack::new(&vec![5; 3000], &vec![3; 3000], 600);
        let cancel = AtomicBool::new(false);
        let now = Instant::now();
        let mut search = Search::new(&problem, &cancel, now, now + Duration::from_millis(5), 0);
        let mut rng = Rng::new(1);
        let mut keys = vec![0.2; 3000];
        let first = search.eval(&keys).unwrap();
        let mut local = LocalSearch::new();
        let outcome = local.swap(&mut keys, first, 2, &mut search, &mut rng);
        assert_eq!(outcome, Err(Stop::TimeLimit));
    }
}
