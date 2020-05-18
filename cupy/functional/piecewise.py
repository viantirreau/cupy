import cupy

from cupy import core

_piecewise_krnl = core.ElementwiseKernel(
    'U condlist, raw S funclist, int64 xsiz',
    'raw I prev, raw T y',
    '''
        if (condlist){
          __syncthreads();
          if (prev[i % xsiz] < i)
            prev[i % xsiz] = i;
          __syncthreads();
          if (prev[i % xsiz] == i)
            y[i % xsiz] = funclist[i / xsiz];
        }
        ''',
    'piecewise_kernel'
)


def piecewise(x, condlist, funclist):
    """Evaluate a piecewise-defined function.

        Args:
            x (cupy.ndarray): input domain
            condlist (cupy.ndarray or list):
                conditions list ( boolean arrays or boolean scalars).
                Each boolean array/ scalar corresponds to a function
                in funclist. Length of funclist is equal to that
                of condlist. If one extra function is given, it is used
                as otherwise condition
            funclist (cupy.ndarray or list): list of scalar functions.

        Returns:
            cupy.ndarray: the result of calling the functions in funclist
                on portions of x defined by condlist.

        .. warning::

            This function currently doesn't support callable functions,
            args and kw parameters.

        .. seealso:: :func:`numpy.piecewise`
        """

    if any(callable(item) for item in funclist):
        raise NotImplementedError(
            'Callable functions are not supported currently')
    if cupy.isscalar(x):
        x = cupy.asarray(x)
    if cupy.isscalar(condlist):
        condlist = cupy.full(shape=x.shape, fill_value=condlist)
    if cupy.isscalar(condlist) or (
            (not isinstance(condlist[0], (list, cupy.ndarray)))
            and x.ndim != 0):
        condlist = [condlist]
    condlist = cupy.array(condlist, dtype=bool)
    condlen = len(condlist)
    funclen = len(funclist)
    if condlen == funclen:
        y = cupy.zeros(shape=x.shape, dtype=x.dtype)
    elif condlen + 1 == funclen:  # o.w
        y = cupy.full(shape=x.shape, fill_value=funclist[-1], dtype=x.dtype)
        funclist = funclist[:-1]
    else:
        raise ValueError('with {} condition(s), either {} or {} functions'
                         ' are expected'.format(condlen, condlen, condlen + 1))
    funclist = cupy.asarray(funclist)
    prev = cupy.full(shape=x.shape, fill_value=-1, dtype=int)
    _piecewise_krnl(condlist, funclist, x.size, prev, y)
    return y
