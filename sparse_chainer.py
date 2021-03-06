import warnings

from chainer import cuda
import chainer
from chainer import configuration

import numpy

from scipy import sparse


class SparseLinearForwardCPU(chainer.links.Linear):

    def __init__(self, old_linear, W_mask=None, with_dense=False):
        W = old_linear.W.data
        b = getattr(old_linear, 'b', None)
        super(SparseLinearForwardCPU, self).__init__(
            W.shape[1], W.shape[0])
        self.W.data[:] = self.xp.array(W)
        if b is not None:
            b = b.data
            self.b.data[:] = self.xp.array(b)
        if not with_dense:
            delattr(self, 'W')
            if b is not None:
                delattr(self, 'b')

        xp = cuda.get_array_module(W)
        if W_mask is None:
            W_mask = xp.ones(W.shape).astype('f')

        if xp is numpy:
            self.sparse_W = sparse.csc_matrix(W * W_mask)
            if b is not None:
                self.sparse_b = numpy.array(b).astype('f')
        else:
            self.sparse_W = sparse.csr_matrix(
                xp.asnumpy(W) * xp.asnumpy(W_mask))
            if b is not None:
                self.sparse_b = xp.asnumpy(b)[None, ]

    def __call__(self, x):
        train = configuration.config.train
        if self.xp is numpy and not train:
            if isinstance(x, chainer.Variable):
                x = x.data
            if x.ndim > 2:
                x = x.reshape(x.shape[0], x.size // x.shape[0])
            return self.sparse_W.dot(x.T).T.astype('f') + \
                getattr(self, 'sparse_b', 0.)
        else:
            warnings.warn('SparseLinearForwardCPU link is made for'
                          ' inference usage. Sparse computation'
                          ' (scipy.sparse) computation is used'
                          ' only in inference mode'
                          ' rather than training mode.')
            if hasattr(self, 'W'):
                return super(SparseLinearForwardCPU, self).__call__(x)
            else:
                NotImplementedError
