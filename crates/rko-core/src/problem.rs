//! Problem definition contract and built-in problems.
//!
//! Objective:
//! - Describe what the engine needs from a random-key problem and ship a reference
//!   0/1 Knapsack used by tests and benchmarks.
//!
//! Technical approach:
//! - A `Problem` maps a key vector in `[0, 1)^n` directly to a finite minimization
//!   cost, fusing decoder and objective so no intermediate solution is allocated.
//! - Knapsack accumulates profit and weight in `f64`, which is exact for integers
//!   below 2^53 and lets the compiler vectorize the threshold test.
//!
//! Flow (pseudocode):
//! 1. For every key above 0.5 add the item's profit and weight.
//! 2. Penalize each unit of capacity excess by 100000.
//! 3. Return the negated penalized profit so the engine minimizes.
//!
//! Important criteria:
//! - `evaluate` must be deterministic and thread-safe (`Sync`).
//! - Non-finite results are rejected by the search wrapper, never propagated.
//!
//! Inputs/Outputs:
//! - Input: a key slice whose length equals `dimension()`.
//! - Output: a finite cost to minimize.

/// Random-key problem evaluated by the engine.
pub trait Problem: Sync {
    /// Number of random keys expected by `evaluate`.
    fn dimension(&self) -> usize;

    /// Decodes and scores one key vector; lower is better.
    fn evaluate(&self, keys: &[f64]) -> f64;

    /// Evaluations between wall-clock checks; use 1 for expensive callbacks.
    fn check_stride(&self) -> u32 {
        8
    }
}

/// Error raised while parsing a Knapsack instance.
#[derive(Debug)]
pub enum InstanceError {
    /// The file contains fewer numbers than the declared item count requires.
    Truncated,
    /// A token could not be parsed as an integer.
    Malformed(String),
}

impl std::fmt::Display for InstanceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Truncated => write!(f, "instance ended before all items were read"),
            Self::Malformed(token) => write!(f, "malformed integer token: {token}"),
        }
    }
}

impl std::error::Error for InstanceError {}

/// 0/1 Knapsack with a linear capacity-excess penalty.
#[derive(Clone, Debug)]
pub struct Knapsack {
    profits: Vec<f64>,
    weights: Vec<f64>,
    capacity: f64,
}

impl Knapsack {
    /// Penalty applied per unit of capacity excess.
    pub const PENALTY: f64 = 100_000.0;

    /// Builds a Knapsack from parallel profit and weight vectors.
    #[must_use]
    pub fn new(profits: &[i64], weights: &[i64], capacity: i64) -> Self {
        assert_eq!(
            profits.len(),
            weights.len(),
            "profits and weights must align"
        );
        Self {
            profits: profits.iter().map(|&value| value as f64).collect(),
            weights: weights.iter().map(|&value| value as f64).collect(),
            capacity: capacity as f64,
        }
    }

    /// Parses the RKO text format: item count, capacity, then profit/weight pairs.
    pub fn parse(text: &str) -> Result<Self, InstanceError> {
        let mut numbers = Vec::new();
        for token in text.split_whitespace() {
            numbers.push(
                token
                    .parse::<i64>()
                    .map_err(|_| InstanceError::Malformed(token.to_owned()))?,
            );
        }
        if numbers.len() < 2 {
            return Err(InstanceError::Truncated);
        }
        let count = usize::try_from(numbers[0]).map_err(|_| InstanceError::Truncated)?;
        let capacity = numbers[1];
        if numbers.len() < 2 + 2 * count {
            return Err(InstanceError::Truncated);
        }
        let mut profits = Vec::with_capacity(count);
        let mut weights = Vec::with_capacity(count);
        for item in 0..count {
            profits.push(numbers[2 + 2 * item]);
            weights.push(numbers[3 + 2 * item]);
        }
        Ok(Self::new(&profits, &weights, capacity))
    }

    /// Returns profit, weight and feasibility of the selection encoded by `keys`.
    #[must_use]
    pub fn solution(&self, keys: &[f64]) -> (i64, i64, bool) {
        let (profit, weight) = self.totals(keys);
        (profit as i64, weight as i64, weight <= self.capacity)
    }

    /// Capacity of the knapsack.
    #[must_use]
    pub fn capacity(&self) -> f64 {
        self.capacity
    }

    /// Penalized cost for given profit and weight totals.
    #[inline]
    #[must_use]
    pub fn cost_from_totals(&self, profit: f64, weight: f64) -> f64 {
        Self::PENALTY * (weight - self.capacity).max(0.0) - profit
    }

    /// Profit and weight of the selection encoded by `keys` (key above 0.5 selects).
    #[inline]
    #[must_use]
    pub fn totals(&self, keys: &[f64]) -> (f64, f64) {
        let mut profit = 0.0;
        let mut weight = 0.0;
        for ((&key, &item_profit), &item_weight) in
            keys.iter().zip(&self.profits).zip(&self.weights)
        {
            let selected = key > 0.5;
            profit += if selected { item_profit } else { 0.0 };
            weight += if selected { item_weight } else { 0.0 };
        }
        (profit, weight)
    }
}

impl Problem for Knapsack {
    fn dimension(&self) -> usize {
        self.profits.len()
    }

    #[inline]
    fn evaluate(&self, keys: &[f64]) -> f64 {
        let (profit, weight) = self.totals(keys);
        self.cost_from_totals(profit, weight)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evaluates_selection_and_penalty() {
        let problem = Knapsack::new(&[10, 20, 30], &[5, 6, 7], 12);
        assert_eq!(problem.evaluate(&[0.9, 0.9, 0.1]), -30.0);
        assert_eq!(problem.evaluate(&[0.9, 0.9, 0.9]), 100_000.0 * 6.0 - 60.0);
        assert_eq!(problem.solution(&[0.9, 0.9, 0.1]), (30, 11, true));
        assert_eq!(problem.solution(&[0.9, 0.9, 0.9]), (60, 18, false));
    }

    #[test]
    fn threshold_is_strict() {
        let problem = Knapsack::new(&[10], &[1], 5);
        assert_eq!(problem.evaluate(&[0.5]), 0.0);
        assert_eq!(problem.evaluate(&[0.5000001]), -10.0);
    }

    #[test]
    fn parses_reference_format() {
        let problem = Knapsack::parse("2\n10\n5 3\n7 4\n").unwrap();
        assert_eq!(problem.dimension(), 2);
        assert_eq!(problem.evaluate(&[1.0, 1.0]), -12.0);
        assert!(Knapsack::parse("3\n10\n1 2").is_err());
        assert!(Knapsack::parse("x").is_err());
    }
}
