UNCURL
======

TODO: pypi

To install after cloning the repo: `pip install .`

To run tests: `python setup.py test`

Examples: see the examples folder.

## Features

### Clustering

The `poisson_cluster` function does Poisson clustering with hard assignments. It takes an array of features by examples and the number of clusters, and returns two arrays: an array of cluster assignments and an array of cluster centers.

The `nb_cluster` function is used for negative binomial clustering with the same parameters. It returns three arrays: P and R, the negative binomial parameters for all genes and clusters, and the cluster assignments for each cell.

Example:

```python
from uncurl import poisson_cluster, nb_cluster
import numpy as np

# data is a 2d array of floats, with dimensions genes x cells
data = np.loadtxt('counts.txt')
assignments_p, centers = poisson_cluster(data, 2)
P, R, assignments_nb = nb_cluster(data, 2)
```


### Qualitative to Quantitative Framework

The `qual2quant` function is used to convert binary data into starting points for clustering.

Example:

```python
from uncurl import qual2quant
import numpy as np

data = np.loadtxt('counts.txt')
bin_data = np.loadtxt('binary.txt')
starting_centers = qual2quant(data, bin_data)
```

### State Estimation

The `poisson_estimate_state` function is used to estimate cell types using the Poisson Convex Mixture Model.

Example:

```python
from uncurl import poisson_estimate_state

data = np.loadtxt('counts.txt')
M, W = poisson_estimate_state(data, 2)
```

### Dimensionality Reduction

The `dim_reduce` function performs dimensionality reduction using MDS.

### Lineage Estimation

The `lineage` function performs lineage estimation from the output of `poisson_estimate_state`. It fits the data to a different 5th degree polynomial for each cell type.

Example:

```python
from uncurl import poisson_estimate_state, lineage

data = np.loadtxt('counts.txt')
M, W = poisson_estimate_state(data, 2)
curve_params, smoothed_points, edges, cell_assignments = lineage(data, M, W)
```
