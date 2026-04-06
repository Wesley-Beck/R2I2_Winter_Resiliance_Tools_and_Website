"""
Monte Carlo FDI cross-comparison and similarity analysis.

Quantifies how similar different fire danger indices are to each other
using randomization-based statistical testing. This answers: "Do FWI
and ERC identify the same hotspots, or different ones?"

Methods:
1. Spatial rank correlation between FDI pairs
2. Bootstrap confidence intervals for correlation
3. Permutation test for hotspot overlap significance
4. Multi-FDI similarity matrix with clustering
"""

import numpy as np
from scipy.stats import rankdata


def rank_correlation(x, y):
    """Compute Spearman rank correlation between two arrays.

    Args:
        x, y: 1-D arrays of same length

    Returns:
        rho: Spearman correlation coefficient
    """
    valid = ~(np.isnan(x) | np.isnan(y))
    x_v = x[valid]
    y_v = y[valid]

    if len(x_v) < 3:
        return np.nan

    rx = rankdata(x_v)
    ry = rankdata(y_v)

    d = rx - ry
    n = len(rx)
    rho = 1.0 - 6.0 * np.sum(d ** 2) / (n * (n ** 2 - 1))
    return float(rho)


def bootstrap_correlation(x, y, n_bootstrap=1000, confidence=0.95, seed=42):
    """Bootstrap confidence interval for rank correlation.

    Args:
        x, y: 1-D arrays
        n_bootstrap: number of bootstrap samples
        confidence: confidence level (default 0.95)
        seed: random seed for reproducibility

    Returns:
        dict with: observed, mean, ci_low, ci_high, std
    """
    rng = np.random.RandomState(seed)
    valid = ~(np.isnan(x) | np.isnan(y))
    x_v = x[valid]
    y_v = y[valid]
    n = len(x_v)

    if n < 10:
        return {"observed": np.nan, "mean": np.nan,
                "ci_low": np.nan, "ci_high": np.nan, "std": np.nan}

    observed = rank_correlation(x_v, y_v)

    boot_rhos = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        boot_rhos[i] = rank_correlation(x_v[idx], y_v[idx])

    alpha = (1 - confidence) / 2
    ci_low = float(np.nanpercentile(boot_rhos, 100 * alpha))
    ci_high = float(np.nanpercentile(boot_rhos, 100 * (1 - alpha)))

    return {
        "observed": float(observed),
        "mean": float(np.nanmean(boot_rhos)),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "std": float(np.nanstd(boot_rhos)),
    }


def permutation_test_hotspot_overlap(mask_a, mask_b, n_permutations=5000, seed=42):
    """Test whether two FDI hotspot masks overlap more than chance.

    Args:
        mask_a, mask_b: boolean arrays of shape (n_points,)
        n_permutations: number of random permutations
        seed: random seed

    Returns:
        dict with:
            observed_overlap: fraction of points that are hotspots in both
            expected_overlap: mean overlap under null (random)
            p_value: one-sided p-value (probability of >= observed overlap by chance)
            z_score: standardized effect size
    """
    rng = np.random.RandomState(seed)
    n = len(mask_a)
    a = np.asarray(mask_a, dtype=bool)
    b = np.asarray(mask_b, dtype=bool)

    observed = np.sum(a & b) / n

    null_overlaps = np.empty(n_permutations)
    for i in range(n_permutations):
        shuffled_b = rng.permutation(b)
        null_overlaps[i] = np.sum(a & shuffled_b) / n

    expected = float(np.mean(null_overlaps))
    std_null = float(np.std(null_overlaps))
    p_value = float(np.mean(null_overlaps >= observed))
    z_score = (observed - expected) / std_null if std_null > 0 else 0.0

    return {
        "observed_overlap": float(observed),
        "expected_overlap": expected,
        "p_value": p_value,
        "z_score": z_score,
        "n_permutations": n_permutations,
    }


def fdi_similarity_matrix(fdi_means_dict, method="rank_correlation",
                          n_bootstrap=1000, seed=42):
    """Compute pairwise similarity matrix between FDI systems.

    Args:
        fdi_means_dict: dict mapping FDI name → 1-D array of temporal means
            per point (n_points,)
        method: "rank_correlation" or "bootstrap" (includes CIs)
        n_bootstrap: bootstrap samples (only for method="bootstrap")
        seed: random seed

    Returns:
        names: list of FDI names (row/column labels)
        matrix: np.ndarray of shape (n_fdis, n_fdis) with correlation values
        details: dict of (name_i, name_j) → result dict (for bootstrap method)
    """
    names = sorted(fdi_means_dict.keys())
    n = len(names)
    matrix = np.eye(n, dtype=np.float64)
    details = {}

    for i in range(n):
        for j in range(i + 1, n):
            x = fdi_means_dict[names[i]]
            y = fdi_means_dict[names[j]]

            if method == "bootstrap":
                result = bootstrap_correlation(x, y, n_bootstrap, seed=seed)
                matrix[i, j] = result["observed"]
                matrix[j, i] = result["observed"]
                details[(names[i], names[j])] = result
            else:
                rho = rank_correlation(x, y)
                matrix[i, j] = rho
                matrix[j, i] = rho

    return names, matrix, details


def monte_carlo_fdi_comparison(fdi_data_dict, n_samples=1000,
                               percentile=90, seed=42):
    """Full Monte Carlo comparison of FDI systems.

    For each random sample of time steps, computes hotspots for each FDI
    and measures pairwise overlap. This reveals how stable the FDI
    agreement is across different time periods.

    Args:
        fdi_data_dict: dict mapping FDI name → (n_timesteps, n_points) array
        n_samples: number of Monte Carlo iterations
        percentile: hotspot percentile threshold
        seed: random seed

    Returns:
        dict with:
            mean_similarity: (n_fdis, n_fdis) matrix of mean overlap
            std_similarity: (n_fdis, n_fdis) matrix of overlap std
            names: FDI name list
            sample_results: list of per-sample overlap matrices
    """
    from .hotspots import find_hotspots

    rng = np.random.RandomState(seed)
    names = sorted(fdi_data_dict.keys())
    n_fdis = len(names)

    # Get common dimensions
    n_timesteps = min(d.shape[0] for d in fdi_data_dict.values())
    sample_size = max(n_timesteps // 3, 10)  # sample 1/3 of timesteps

    all_overlaps = np.zeros((n_samples, n_fdis, n_fdis))

    for s in range(n_samples):
        # Random subset of timesteps
        idx = rng.choice(n_timesteps, size=sample_size, replace=False)

        # Find hotspots for each FDI on this sample
        masks = {}
        for i, name in enumerate(names):
            subset = fdi_data_dict[name][idx, :]
            mask, _, _ = find_hotspots(subset, percentile)
            masks[name] = mask

        # Pairwise overlap
        for i in range(n_fdis):
            all_overlaps[s, i, i] = 1.0
            for j in range(i + 1, n_fdis):
                a = masks[names[i]]
                b = masks[names[j]]
                n_pts = len(a)
                # Jaccard similarity
                intersection = np.sum(a & b)
                union = np.sum(a | b)
                overlap = intersection / union if union > 0 else 0.0
                all_overlaps[s, i, j] = overlap
                all_overlaps[s, j, i] = overlap

    mean_sim = np.mean(all_overlaps, axis=0)
    std_sim = np.std(all_overlaps, axis=0)

    return {
        "mean_similarity": mean_sim,
        "std_similarity": std_sim,
        "names": names,
        "sample_results": all_overlaps,
    }


def cluster_fdis(similarity_matrix, names, n_clusters=3):
    """Simple agglomerative clustering of FDIs by similarity.

    Uses a basic nearest-neighbor approach (no scipy dependency).

    Args:
        similarity_matrix: (n_fdis, n_fdis) correlation/overlap matrix
        names: list of FDI names
        n_clusters: desired number of clusters

    Returns:
        clusters: dict mapping cluster_id → list of FDI names
        merge_history: list of (merged_pair, similarity) tuples
    """
    n = len(names)
    # Convert similarity to distance
    dist = 1.0 - np.clip(similarity_matrix, 0, 1)
    np.fill_diagonal(dist, np.inf)

    # Track cluster membership
    labels = list(range(n))
    active = set(range(n))
    merge_history = []

    while len(active) > n_clusters:
        # Find closest pair
        best_dist = np.inf
        best_i, best_j = -1, -1
        for i in active:
            for j in active:
                if i < j and dist[i, j] < best_dist:
                    best_dist = dist[i, j]
                    best_i, best_j = i, j

        if best_i < 0:
            break

        merge_history.append(((names[best_i], names[best_j]), 1.0 - best_dist))

        # Merge j into i (update distances with single-linkage)
        for k in active:
            if k != best_i and k != best_j:
                dist[best_i, k] = min(dist[best_i, k], dist[best_j, k])
                dist[k, best_i] = dist[best_i, k]

        # Reassign labels
        merge_label = labels[best_i]
        old_label = labels[best_j]
        for idx in range(n):
            if labels[idx] == old_label:
                labels[idx] = merge_label

        active.discard(best_j)
        dist[best_j, :] = np.inf
        dist[:, best_j] = np.inf

    # Build cluster dict
    clusters = {}
    for idx, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(names[idx])

    # Renumber clusters 0..n_clusters-1
    renumbered = {}
    for new_id, (_, members) in enumerate(sorted(clusters.items())):
        renumbered[new_id] = members

    return renumbered, merge_history
