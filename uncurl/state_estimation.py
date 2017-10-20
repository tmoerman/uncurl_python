# state estimation with poisson convex mixture model

from .clustering import kmeans_pp, poisson_cluster
from uncurl.nolips import nolips_update_w, objective, sparse_objective
from uncurl.nolips import sparse_nolips_update_w
# try to use parallel; otherwise
#from uncurl.nolips_parallel import sparse_nolips_update_w as parallel_sparse_nolips_update_w
try:
    from uncurl.nolips_parallel import sparse_nolips_update_w as parallel_sparse_nolips_update_w
except:
    print('Warning: cannot import sparse nolips')
    # if parallel can't be used, do not use parallel update function...
    pass
from .preprocessing import cell_normalize, log1p

import numpy as np
from scipy import sparse
from scipy.optimize import minimize
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD

eps=1e-8

def _create_w_objective(m, X):
    """
    Creates an objective function and its derivative for W, given M and X (data)

    Args:
        m (array): genes x clusters
        X (array): genes x cells
    """
    genes, clusters = m.shape
    cells = X.shape[1]
    m_sum = m.sum(0)
    def objective(w):
        # convert w into a matrix first... because it's a vector for
        # optimization purposes
        w = w.reshape((m.shape[1], X.shape[1]))
        d = m.dot(w)+eps
        # derivative of objective wrt all elements of w
        # for w_{ij}, the derivative is... m_j1+...+m_jn sum over genes minus 
        # x_ij
        temp = X/d
        m2 = m.T.dot(temp)
        deriv = m_sum.reshape((clusters, 1)) - m2
        return np.sum(d - X*np.log(d))/genes, deriv.flatten()/genes
    return objective

def _create_m_objective(w, X):
    """
    Creates an objective function and its derivative for M, given W and X

    Args:
        w (array): clusters x cells
        X (array): genes x cells
    """
    clusters, cells = w.shape
    genes = X.shape[0]
    w_sum = w.sum(1)
    def objective(m):
        m = m.reshape((X.shape[0], w.shape[0]))
        d = m.dot(w)+eps
        temp = X/d
        w2 = w.dot(temp.T)
        deriv = w_sum - w2.T
        return np.sum(d - X*np.log(d))/genes, deriv.flatten()/genes
    return objective

def initialize_from_assignments(assignments, k, max_assign_weight=0.75):
    """
    Creates a weight initialization matrix from Poisson clustering assignments.

    Args:
        assignments (array): 1D array of integers, of length cells
        k (int): number of states/clusters
        max_assign_weight (float, optional): between 0 and 1 - how much weight to assign to the highest cluster. Default: 0.75

    Returns:
        init_W (array): k x cells
    """
    cells = len(assignments)
    init_W = np.zeros((k, cells))
    for i, a in enumerate(assignments):
        # entirely arbitrary... maybe it would be better to scale
        # the weights based on k?
        init_W[a, i] = max_assign_weight
        for a2 in range(k):
            if a2!=a:
                init_W[a2, i] = max_assign_weight/(k-1)
    return init_W

def initialize_means(data, clusters, k):
    """
    Initializes the M matrix given the data and a set of cluster labels.
    Cluster centers are set to the mean of each cluster.

    Args:
        data (array): genes x cells
        clusters (array): 1d array of ints (0...k-1)
        k (int): number of clusters
    """
    init_w = np.zeros((data.shape[0], k))
    if sparse.issparse(data):
        for i in range(k):
            if data[:,clusters==i].shape[1]==0:
                point = np.random.randint(0, data.shape[1])
                init_w[:,i] = data[:,point].toarray().flatten()
            else:
                init_w[:,i] = np.array(data[:,clusters==i].mean(1)).flatten()
    else:
        for i in range(k):
            if data[:,clusters==i].shape[1]==0:
                point = np.random.randint(0, data.shape[1])
                init_w[:,i] = data[:,point].flatten()
            else:
                init_w[:,i] = data[:,clusters==i].mean(1)
    return init_w


def poisson_estimate_state(data, clusters, init_means=None, init_weights=None, method='NoLips', max_iters=15, tol=1e-10, disp=True, inner_max_iters=300, normalize=True, initialization='tsvd', parallel=True, n_threads=4):
    """
    Uses a Poisson Covex Mixture model to estimate cell states and
    cell state mixing weights.

    To lower computational costs, use a sparse matrix, set disp to False, and set tol to 0.

    Args:
        data (array): genes x cells array or sparse matrix.
        clusters (int): number of mixture components
        init_means (array, optional): initial centers - genes x clusters. Default: from Poisson kmeans
        init_weights (array, optional): initial weights - clusters x cells, or assignments as produced by clustering. Default: from Poisson kmeans
        method (str, optional): optimization method. Current options are 'NoLips' and 'L-BFGS-B'. Default: 'NoLips'.
        max_iters (int, optional): maximum number of iterations. Default: 15
        tol (float, optional): if both M and W change by less than tol (RMSE), then the iteration is stopped. Default: 1e-10
        disp (bool, optional): whether or not to display optimization parameters. Default: True
        inner_max_iters (int, optional): Number of iterations to run in the optimization subroutine for M and W. Default: 300
        normalize (bool, optional): True if the resulting W should sum to 1 for each cell. Default: True.
        initialization (str, optional): If initial means and weights are not provided, this describes how they are initialized. Options: 'cluster' (poisson cluster for means and weights), 'kmpp' (kmeans++ for means, random weights), 'km' (regular k-means), 'tsvd' (tsvd(50) + k-means). Default: tsvd.
        parallel (bool, optional): Whether to use parallel updates (sparse NoLips only). Default: True
        n_threads (int, optional): How many threads to use in the parallel computation. Default: 4

    Returns:
        M (array): genes x clusters - state means
        W (array): clusters x cells - state mixing components for each cell
        ll (float): final log-likelihood
    """
    genes, cells = data.shape
    if init_means is None:
        if initialization=='cluster':
            assignments, means = poisson_cluster(data, clusters)
            if init_weights is None:
                init_weights = initialize_from_assignments(assignments, clusters,
                        max_assign_weight=0.6)
        elif initialization=='kmpp':
            means, assignments = kmeans_pp(data, clusters)
        elif initialization=='km':
            km = KMeans(clusters)
            # TODO: should the data be log-normalized? how much
            # computational time does that add?
            assignments = km.fit_predict(log1p(cell_normalize(data)).T)
            init_weights = initialize_from_assignments(assignments, clusters)
            means = initialize_means(data, assignments, clusters)
        elif initialization=='tsvd':
            tsvd = TruncatedSVD(50)
            km = KMeans(clusters)
            data_reduced = tsvd.fit_transform(log1p(cell_normalize(data)).T)
            assignments = km.fit_predict(data_reduced)
            init_weights = initialize_from_assignments(assignments, clusters)
            means = initialize_means(data, assignments, clusters)
    else:
        means = init_means.copy()
    means = means.astype(float)
    if init_weights is not None:
        if len(init_weights.shape)==1:
            init_weights = initialize_from_assignments(init_weights, clusters)
        w_init = init_weights.copy()
    else:
        w_init = np.random.random((clusters, cells))
    nolips_iters = inner_max_iters
    X = data.astype(float)
    XT = X.T
    is_sparse = False
    if sparse.issparse(X):
        is_sparse = True
        update_fn = sparse_nolips_update_w
        if parallel:
            update_fn = parallel_sparse_nolips_update_w
        Xsum = np.asarray(X.sum(0)).flatten()
        Xsum_m = np.asarray(X.sum(1)).flatten()
        # L-BFGS-B won't work right now for sparse matrices
        # convert to csc
        X = sparse.csc_matrix(X)
        method = 'NoLips'
        objective_fn = sparse_objective
        XT = sparse.csc_matrix(XT)
    else:
        objective_fn = objective
        update_fn = nolips_update_w
        Xsum = X.sum(0)
        Xsum_m = X.sum(1)
        # If method is NoLips, converting to a sparse matrix
        # will always improve the performance (?) and never lower accuracy...
        # will almost always improve performance?
        # if sparsity is below 40%?
        if method == 'NoLips':
            if np.count_nonzero(X) < 0.4*genes*cells:
                is_sparse = True
                update_fn = sparse_nolips_update_w
                if parallel:
                    update_fn = parallel_sparse_nolips_update_w
                X = sparse.csc_matrix(X)
                objective_fn = sparse_objective
                XT = sparse.csc_matrix(XT)
    for i in range(max_iters):
        if disp:
            print('iter: {0}'.format(i))
        # step 1: given M, estimate W
        if method=='NoLips':
            for j in range(nolips_iters):
                if is_sparse and parallel:
                    w_new = update_fn(X, means, w_init, Xsum, n_threads=n_threads)
                else:
                    w_new = update_fn(X, means, w_init, Xsum)
                #w_new = w_res.x.reshape((clusters, cells))
                #w_new = w_new/w_new.sum(0)
                if tol > 0:
                    w_diff = np.sqrt(np.sum((w_new - w_init)**2)/(clusters*cells))
                    w_init = w_new
                    if w_diff < tol:
                        break
                else:
                    w_init = w_new
        elif method=='L-BFGS-B':
            w_objective = _create_w_objective(means, data)
            w_bounds = [(0, None) for c in range(clusters*cells)]
            w_res = minimize(w_objective, w_init.flatten(),
                    method='L-BFGS-B', jac=True, bounds=w_bounds,
                    options={'disp':disp, 'maxiter':inner_max_iters})
            w_new = w_res.x.reshape((clusters, cells))
            w_init = w_new
        if disp:
            w_ll = objective_fn(X, means, w_new)
            print('Finished updating W. Objective value: {0}'.format(w_ll))
        # step 2: given W, update M
        if method=='NoLips':
            for j in range(nolips_iters):
                if is_sparse and parallel:
                    m_new = update_fn(XT, w_new.T, means.T, Xsum_m,
                            n_threads=n_threads)
                else:
                    m_new = update_fn(XT, w_new.T, means.T, Xsum_m)
                if tol > 0:
                    m_diff = np.sqrt(np.sum((m_new.T - means)**2)/(clusters*genes))
                    means = m_new.T
                    if m_diff <= tol:
                        break
                else:
                    means = m_new.T
        elif method=='L-BFGS-B':
            m_objective = _create_m_objective(w_new, data)
            m_init = means.flatten()
            m_bounds = [(0,None) for c in range(genes*clusters)]
            m_res = minimize(m_objective, m_init,
                    method='L-BFGS-B', jac=True, bounds=m_bounds,
                    options={'disp':disp, 'maxiter':inner_max_iters})
            means = m_res.x.reshape((genes, clusters))
        if disp:
            m_ll = objective_fn(X, means, w_new)
            print('Finished updating M. Objective value: {0}'.format(m_ll))
    if normalize:
        w_new = w_new/w_new.sum(0)
    m_ll = objective_fn(X, means, w_new)
    return means, w_new, m_ll
