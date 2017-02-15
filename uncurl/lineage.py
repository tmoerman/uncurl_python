# Lineage tracing and pseudotime calculation

import numpy as np
from scipy.optimize import curve_fit

from dim_reduce import dim_reduce

def fourier_series(x, *a):
    """
    Arbitrary dimensionality fourier series.

    The first parameter is a_0, and the second parameter is the interval/scale
    parameter.

    The parameters are altering sin and cos paramters.

    n = (len(a)-2)/2
    """
    output = 0
    output += a[0]/2
    w = a[1]
    for n in range(2, len(a), 2):
        n_ = n/2
        val1 = a[n]
        val2 = a[n+1]
        output += val1*np.sin(n_*x*w)
        output += val2*np.cos(n_*x*w)
    return output

def poly_curve(x, *a):
    """
    Arbitrary dimension polynomial.
    """
    output = a[0]
    for n in range(1, len(a)):
        output += a[n]*x**n
    return output

def mst(points):
    """
    Finds the minimum spanning tree of the provided array of 2d points, using
    Euclidean distance.

    NOT IMPLEMENTED AND ALSO UNNECESSARY

    Args:
        points (array) = 2 x n array

    Returns:
        list of edges - tuples of indices
    """
    # TODO (actually this isn't even used)
    n = points.shape[1]
    distances = np.array([[np.sum(np.sqrt((points[:,i]-points[:,j])**2)) for i in range(n)] for j in range(n)])

def lineage(data, means, weights, curve_function='poly'):
    """
    Lineage graph produced by minimum spanning tree

    Args:
        data (array): genes x cells
        means (array): genes x clusters - output of state estimation
        weights (array): clusters x cells - output of state estimation
        curve_function (string): either 'poly' or 'fourier'. Default: 'poly'

    Returns:
        - curve parameters - list of lists for each cluster
        - smoothed data in 2d space - 2 x cells
        - list of edges - pairs of cell indices
        - cell cluster assignments - list of ints
    """
    if curve_function=='poly':
        func = poly_curve
    elif curve_function=='fourier':
        func = fourier_series
    # step 1: dimensionality reduction
    X = dim_reduce(data, means, weights, 2)
    reduced_data = np.dot(X.T, weights)
    # 2. identifying dominant cell types - max weight for each cell
    genes, cells = data.shape
    clusters = means.shape[1]
    cell_cluster_assignments = []
    for i in range(cells):
        max_cluster = weights[:,i].argmax()
        cell_cluster_assignments.append(max_cluster)
    cell_cluster_assignments = np.array(cell_cluster_assignments)
    # 3. fit smooth curve over cell types -5th order fourier series
    # cluster_curves contains the parameters for each curve.
    cluster_curves = []
    # cluster_fitted_vals is a 2 x cells array
    cluster_fitted_vals = np.zeros(reduced_data.shape)
    # cluster_edges contain a list of ordered pairs (indices) connecting cells
    # in each cluster.
    cluster_edges = []
    for c in range(clusters):
        cluster_cells = reduced_data[:, cell_cluster_assignments==c]
        # y = f(x)
        if curve_function=='fourier':
            p0 = [1.0]*10
            # scipy is bad at finding the correct scale
            p0[1] = 0.0001
            bounds = (-np.inf, np.inf)
        else:
            p0 = [1.0]*6
            bounds = (-np.inf, np.inf)
        p_x, pcov_x = curve_fit(func, cluster_cells[0,:],
                cluster_cells[1,:],
                p0=p0, bounds=bounds)
        perr_x = np.sum(np.sqrt(np.diag(pcov_x)))
        #print perr_x
        # x = f(y)
        p_y, pcov_y = curve_fit(func, cluster_cells[1,:],
                cluster_cells[0,:],
                p0=p0, bounds=bounds)
        perr_y = np.sum(np.sqrt(np.diag(pcov_y)))
        #print perr_y
        if perr_x <= perr_y:
            x_vals = reduced_data[0,:]
            cluster_curves.append(p_x)
            y_vals = np.array([func(x, *p_x) for x in x_vals])
            #print 'error:', np.sum(np.sqrt((y_vals - reduced_data[1,:])**2)[cell_cluster_assignments==c])
            fitted_vals = np.array([x_vals, y_vals])
            cluster_fitted_vals[:,cell_cluster_assignments==c] = fitted_vals[:,cell_cluster_assignments==c]
            # sort points by increasing X, connect points
            x_indices = np.argsort(x_vals)
            x_indices = [x for x in x_indices if cell_cluster_assignments[x]==c]
            new_cluster_edges = []
            for i, j in zip(x_indices[:-1], x_indices[1:]):
                new_cluster_edges.append((i,j))
            cluster_edges.append(new_cluster_edges)
        else:
            y_vals = reduced_data[1,:]
            cluster_curves.append(p_y)
            x_vals = np.array([func(x, *p_y) for x in y_vals])
            #print 'error:', np.sum(np.sqrt((x_vals - reduced_data[0,:])**2)[cell_cluster_assignments==c])
            fitted_vals = np.array([x_vals, y_vals])
            cluster_fitted_vals[:,cell_cluster_assignments==c] = fitted_vals[:,cell_cluster_assignments==c]
            # sort points by increasing Y, connect points
            y_indices = np.argsort(y_vals)
            y_indices = [x for x in y_indices if cell_cluster_assignments[x]==c]
            new_cluster_edges = []
            for i,j in zip(y_indices[:-1], y_indices[1:]):
                new_cluster_edges.append((i,j))
            cluster_edges.append(new_cluster_edges)
    # 4. connect each cluster together
    # for each cluster, find the closest point in another cluster, and connect
    # those points. Add that point to cluster_edges.
    # build a distance matrix between the reduced points...
    distances = np.array([[sum((x - y)**2) for x in cluster_fitted_vals.T] for y in cluster_fitted_vals.T])
    for c1 in range(clusters):
        min_dist = np.inf
        min_index = None
        for c2 in range(clusters):
            if c1!=c2:
                distances_c = distances[cell_cluster_assignments==c1,:][:, cell_cluster_assignments==c2]
                mindex = np.unravel_index(distances_c.argmin(), distances_c.shape)
                if distances_c[mindex] < min_dist:
                    min_dist = distances_c[mindex]
                    min_index = np.where(distances==min_dist)
                    min_index = (min_index[0][0], min_index[1][0])
        cluster_edges[c1].append(min_index)
    # flatten cluster_edges?
    cluster_edges = [i for sublist in cluster_edges for i in sublist]
    return cluster_curves, cluster_fitted_vals, cluster_edges, cell_cluster_assignments

def pseudotime():
    """
    """
    # TODO
