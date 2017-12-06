# basic functions for visualization of clustering, state estimation, lineage

import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

def visualize_poisson_w(w, labels, filename, method='pca', figsize=(18,10), title='', **scatter_options):
    """
    Saves a scatter plot of a visualization of W, the result from Poisson SE.
    """
    if method == 'pca':
        pca = PCA(2)
        r_dim_red = pca.fit_transform(w.T).T
    elif method == 'tsne':
        pass
    else:
        print("Method is not available. use 'pca' (default) or 'tsne'.")
        return
    visualize_dim_red(r_dim_red, labels, filename, figsize, title, **scatter_options)

def visualize_dim_red(r, labels, filename=None, figsize=(18,10), title='', legend=True, label_map=None, **scatter_options):
    """
    Saves a scatter plot of a (2,n) matrix r, where each column is a cell.

    Args:
        r (array): (2,n) matrix
        labels (array): (n,) array of ints
        filename (string): string to save the output graph. If None, then this just displays the plot.
        figsize (tuple): Default: (18, 10)
        title (string): graph title
        legend (bool): Default: True
        label_map (dict): map of labels to label names. Default: None
    """
    fig = plt.figure(figsize=figsize)
    plt.cla()
    for i in set(labels):
        label = i
        if label_map is not None:
            label = label_map[i]
        plt.scatter(r[0, labels==i], r[1, labels==i], label=label, **scatter_options)
    plt.title(title)
    if legend:
        plt.legend()
    if filename is not None:
        plt.savefig(filename, dpi=100)
        plt.close()
    return fig
