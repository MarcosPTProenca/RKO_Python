//! Metaheuristic implementations and their shared run context.
//!
//! Objective:
//! - Group the search algorithms behind one calling convention so the portfolio
//!   scheduler can run them uniformly on worker threads.
//!
//! Technical approach:
//! - Each algorithm is a function over a `Context` bundling the budgeted `Search`,
//!   the shared `Pool`, a private `Rng`, and the algorithm's `Spec`.
//! - Algorithms never check the clock themselves: every candidate goes through
//!   `Search::eval`, whose `Stop` error unwinds the loop through `?`.
//!
//! Flow (pseudocode):
//! 1. The scheduler builds a `Context` per search.
//! 2. The algorithm loops until `Search::eval` returns `Stop`.
//! 3. The scheduler reads the incumbent and counters from the `Search`.
//!
//! Important criteria:
//! - A `Context` is owned by one thread; only the `Pool` is shared.
//! - Parameter vectors follow the axis order of the packaged TOML files.
//!
//! Inputs/Outputs:
//! - Input: a `Spec` (offline values or feasible online states) and a `Context`.
//! - Output: `Result<(), Stop>`; results live in the `Search` incumbent and the pool.

pub mod brkga;
pub mod sa;

use crate::pool::Pool;
use crate::rng::Rng;
use crate::search::{Search, Stop};

/// Algorithms implemented natively.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Algorithm {
    /// Biased random-key genetic algorithm.
    Brkga,
    /// Simulated annealing.
    Sa,
}

impl Algorithm {
    /// Canonical display name.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Brkga => "BRKGA",
            Self::Sa => "SA",
        }
    }

    /// Parses a canonical or underscore-separated algorithm name.
    #[must_use]
    pub fn parse(name: &str) -> Option<Self> {
        match name.to_ascii_uppercase().as_str() {
            "BRKGA" => Some(Self::Brkga),
            "SA" => Some(Self::Sa),
            _ => None,
        }
    }
}

/// Parameters for one search: fixed values or feasible online states.
#[derive(Clone, Debug)]
pub struct Spec {
    /// Algorithm to run.
    pub algorithm: Algorithm,
    /// Offline parameter values in axis order.
    pub offline: Vec<f64>,
    /// Feasible online parameter vectors in enumeration order.
    pub states: Vec<Vec<f64>>,
    /// Whether Q-learning selects parameters online.
    pub adaptive: bool,
}

/// Everything one search needs while running.
pub struct Context<'a, 'b> {
    /// Budgeted evaluator and incumbent.
    pub search: &'a mut Search<'b>,
    /// Shared elite pool.
    pub pool: &'a Pool,
    /// Private random stream.
    pub rng: &'a mut Rng,
    /// Index recorded as the producer of pool entries.
    pub source: usize,
}

impl Spec {
    /// Runs the configured algorithm until the search budget is exhausted.
    pub fn run(&self, context: &mut Context<'_, '_>) -> Result<(), Stop> {
        match self.algorithm {
            Algorithm::Brkga => brkga::run(self, context),
            Algorithm::Sa => sa::run(self, context),
        }
    }
}
