#![doc = "Optional random-key recombination using original Python RNG calls and owned numerical snapshots."]

use pyo3::buffer::PyBuffer;
use pyo3::exceptions::PyMemoryError;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[doc = "Apply one existing blending decision without changing draw thresholds."]
fn blend_gene(a: f64, b: f64, first: f64, second: f64, complement: bool) -> f64 {
    if first < 0.02 {
        second
    } else if second < 0.5 {
        a
    } else if complement {
        (1.0 - b).clamp(0.0, 0.9999999)
    } else {
        b
    }
}

#[doc = "Reserve input-sized storage without aborting the process on allocation failure."]
fn owned_capacity<T>(length: usize) -> PyResult<Vec<T>> {
    let mut values = Vec::new();
    values
        .try_reserve_exact(length)
        .map_err(|_| PyMemoryError::new_err("native blending allocation failed"))?;
    Ok(values)
}

#[doc = "Copy buffer contents into independently owned, fallibly allocated numerical storage."]
fn snapshot(buffer: &PyBuffer<f64>, py: Python<'_>) -> PyResult<Vec<f64>> {
    let mut values = owned_capacity(buffer.item_count())?;
    values.resize(buffer.item_count(), 0.0);
    buffer.copy_to_slice(py, &mut values)?;
    Ok(values)
}

#[doc = "Use the original RNG callable with owned draws and safe numeric buffer transport."]
#[pyfunction]
fn blend_buffers_rng(
    py: Python<'_>,
    parent_a: &Bound<'_, PyAny>,
    parent_b: &Bound<'_, PyAny>,
    output: &Bound<'_, PyAny>,
    complement: bool,
    draw: &Bound<'_, PyAny>,
) -> PyResult<()> {
    let a = PyBuffer::<f64>::get(parent_a)?;
    let b = PyBuffer::<f64>::get(parent_b)?;
    let o = PyBuffer::<f64>::get(output)?;
    if [a.dimensions(), b.dimensions(), o.dimensions()]
        .iter()
        .any(|&n| n != 1)
        || [&a, &b, &o].iter().any(|buffer| !buffer.is_c_contiguous())
        || o.readonly()
    {
        return Err(PyValueError::new_err(
            "contiguous vectors and writable output required",
        ));
    }
    let n = a.item_count();
    if n != b.item_count() || n != o.item_count() {
        return Err(PyValueError::new_err("buffer lengths are inconsistent"));
    }
    let mut draws = owned_capacity(n)?;
    py.check_signals()?;
    for i in 0..n {
        if i > 0 && i % 1024 == 0 {
            py.check_signals()?;
        }
        draws.push((
            draw.call0()?.extract::<f64>()?,
            draw.call0()?.extract::<f64>()?,
        ));
    }
    let a = snapshot(&a, py)?;
    let b = snapshot(&b, py)?;
    let mut values = owned_capacity(n)?;
    for (i, (first, second)) in draws.into_iter().enumerate() {
        values.push(blend_gene(a[i], b[i], first, second, complement));
    }
    o.copy_from_slice(py, &values)
}

#[pymodule(gil_used = true)]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(blend_buffers_rng, module)?)?;
    module.add("BLENDING_CONTRACT", "rko-blending-rng-buffer-v1")?;
    module.add(
        "BUILD_MODE",
        if cfg!(debug_assertions) {
            "debug"
        } else {
            "release"
        },
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::blend_gene;
    use super::owned_capacity;

    #[test]
    fn oversized_allocation_is_an_error_not_a_panic() {
        assert!(owned_capacity::<f64>(usize::MAX).is_err());
    }

    #[test]
    fn mutation_and_inheritance_thresholds_match_reference() {
        assert_eq!(blend_gene(0.1, 0.8, 0.02, 0.5, false), 0.8);
        assert_eq!(blend_gene(0.1, 0.8, 0.02, 0.49, true), 0.1);
        assert_eq!(blend_gene(0.1, 0.8, 0.019, 0.7, true), 0.7);
    }

    #[test]
    fn complementary_clipping_matches_reference() {
        assert_eq!(blend_gene(0.1, 0.0, 1.0, 0.5, true), 0.9999999);
        assert_eq!(blend_gene(0.1, 2.0, 1.0, 0.5, true), 0.0);
        assert!(blend_gene(-0.0, 0.8, 0.1, 0.1, false).is_sign_negative());
    }
}
