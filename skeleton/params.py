import numpy as np
import time

EXTREME_SMALL = 10 ** -323
VERY_SMALL = 10 ** -10


def get_thetas(r, h):
    """
    :param r: variable r
    :param h: local neighborhood size
    :return: theta(r)
    """
    thetas = np.exp((-r ** 2) / ((h / 2) ** 2))
    # Clip to JUST not zero
    thetas = np.clip(thetas, EXTREME_SMALL, None)
    return thetas


def get_alphas(x: np.ndarray, points: np.ndarray, h: float):
    """
    :param x:  1x3 center we of interest, np.ndarray
    :param points:  Nx3 array of all the points, np.ndarray
    :param h: size of local neighborhood, float
    :return: alpha(i,j)
    """
    r = np.linalg.norm(x - points, axis=1) + VERY_SMALL
    theta = get_thetas(r, h)

    alphas = theta / r
    return alphas


def get_betas(x, points, h):
    """
    :param x:  1x3 center we of interest, np.ndarray
    :param points:  Nx3 array of all the points, np.ndarray
    :param h: size of local neighborhood, float
    :return: beta(i,i')
    """
    r = np.linalg.norm(x - points, axis=1) + VERY_SMALL
    theta = get_thetas(r, h)

    betas = theta / r ** 2

    return np.array(betas)


def get_density_weights(points, hd, for_center=False, center=None):
    """
    INPUTS:
        x: 1x3 center we of interest, np.ndarray
        points: Nx3 array of all the points, np.ndarray
        h: size of local neighboorhood, float
    RETURNS:
        - np.array Nx1 of density weights assoiscated to each point
    """
    if center is None:
        center = [0, 0, 0]

    density_weights = []

    if for_center:
        r = points - center
        r2 = np.einsum('ij,ij->i', r, r)
        density_weights = 1 + np.einsum('i->', np.exp((-r2) / ((hd / 2) ** 2)))
    else:

        for point in points:
            r = point - points
            r2 = np.einsum('ij,ij->i', r, r)
            # This calculation includes the point itself thus one entry will be zero resulting in the needed + 1 in
            # formula dj = 1+ sum(theta(p_i - p_j))
            density_weight = 1 + np.einsum('i->', np.exp((-r2) / ((hd / 2) ** 2)))
            density_weights.append(density_weight)

    return np.array(density_weights)


def get_term1(center: np.ndarray, points: np.ndarray, h: float, density_weights: np.ndarray):
    """
    :param center: 1x3 center we of interest, np.ndarray
    :param points: Nx3 array of all the points, np.ndarray
    :param h: size of local neighborhood, float
    :param density_weights:
    :return: term1 of the equation as float
    """

    t1_t = time.perf_counter()

    r = points - center
    r2 = np.einsum('ij,ij->i', r, r)

    thetas = np.exp(-r2 / ((h / 2) ** 2))

    alphas = thetas / np.sqrt(r2)
    alphas /= density_weights

    denom = np.einsum('i->', alphas)
    if denom > 10 ** -20:
        # term1 = np.sum((points.T*alphas).T, axis = 0)/denom
        term1 = np.einsum('j,jk->k', alphas, points) / denom
    else:
        term1 = np.array(False)

    t2_t = time.perf_counter()
    tt = round(t2_t - t1_t, 5)

    return term1, tt


def get_term2(center: np.ndarray, centers: np.ndarray, h: float):
    """
    :param center:  1x3 center we of interest, np.ndarray
    :param centers:  Nx3 array of all the centers (excluding the current center), np.ndarray
    :param h:  size of local neighborhood, float
    :return:  term2 of the equation as float
    """

    t1 = time.perf_counter()

    x = center - centers
    r2 = np.einsum('ij,ij->i', x, x)

    thetas = np.exp((-r2) / ((h / 2) ** 2))

    betas = thetas / r2

    denom = np.einsum('i->', betas)

    if denom > 10 ** -20:
        num = np.einsum('j,jk->k', betas, x)
        term2 = num / denom
    else:
        term2 = np.array(False)

    t2 = time.perf_counter()
    tt = round(t2 - t1, 4)
    return term2, tt


def get_sigma(center, centers, h):
    t1 = time.perf_counter()

    # These are the weights
    r = centers - center
    r2 = np.einsum('ij,ij->i', r, r)

    thetas = np.exp((-r2) / ((h / 2) ** 2))

    cov = np.einsum('j,jk,jl->kl', thetas, r, r)

    # Get eigenvalues and eigenvectors
    values, vectors = np.linalg.eig(cov)

    if np.iscomplex(values).any():
        values = np.real(values)

        vectors = np.real(vectors)
        vectors_norm = np.sqrt(np.einsum('ij,ij->i', vectors, vectors))
        vectors = vectors / vectors_norm

    # argsort always works from low --> to high so taking the negative values will give us high --> low indices
    sorted_indices = np.argsort(-values)

    sigma = np.max(values) / np.sum(values)
    vectors_sorted = vectors[:, sorted_indices]

    t2 = time.perf_counter()

    return sigma, vectors_sorted, t2 - t1
