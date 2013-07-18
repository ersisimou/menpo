import numpy as np
from pybug.transform import Transform


class StatisticallyDrivenTransform(Transform):

    def __init__(self, linear_model, transform_constructor, weights=None):
        """
        A transform that couples a traditional landmark-based transform to a
        statistical model, such that the parameters of the model are fully
        specified by the statistical model that drives the transform. The
        model is assumed to generate instance which dictate of the source
        landmarks of the transform. The mean of the model is always the
        target landmarks of the model.

        :param linear_model: A statistical linear shape model.
        :param transform_constructor: A function that returns a Transform
            object. It will be fed the source landmarks as the first
            argument and the target landmarks as the second. The target
            landmarks are always the model's mean - the source is set to the
            points generated from the model using the weights provided.
        :param weights: The reconstruction weights that will be fed to the
            model in order to generate an instance of the target landmarks.
        """
        self.model = linear_model
        if weights is None:
            # set all the weights to 0 (yielding the mean)
            weights = np.zeros(self.model.n_components)
        self.weights = weights
        self.transform_constructor = transform_constructor
        self.transform = transform_constructor(
            self.model.instance(weights).points, self.model.mean.points)

    @property
    def n_dim(self):
        return self.transform.n_dim

    def jacobian(self, points):
        """
        Chains together the jacobian of the warp wrt it's source landmarks
        (dW_dx) with the jacobian of the linear model wrt it's shape (dX_dp).
        Yields dW_dP of shape (n_points, n_params, n_dims)
        """
        dW_dX = self.transform.jacobian_source(points)
        c = self.model.components
        # c.shape     (n_params, [n_landmarks x n_dims]) *
        # dW_dX.shape (n_points, n_landmarks, n_dims)
        # dW_dp.shape (n_points, n_params, n_dims)
        # * components are parameters in this setting -> n_params == n_comps

        # from PointCloud.as_vector(), we know that c[0, :] has the stride
        # (x1, y1, x2, y2, ...., xn, yn)
        # -> reshaping the last axis of c to (n_landmarks, n_dims) will
        # correctly restore the final axis to be a dimension axis
        dX_dp = c.reshape(c.shape[0], -1, self.n_dim)
        # dW_dX.shape (n_points,           n_landmarks, n_dims)
        # dX_dp.shape (          n_params, n_landmarks, n_dims)
        # dW_dp.shape (n_points, n_params,              n_dims)
        # i = points, l = landmarks, d = dims, p = params
        dW_dp = np.einsum('ild, pld -> ipd', dW_dX, dX_dp)
        return dW_dp

    def from_vector(self, flattened):
        return StatisticallyDrivenTransform(self.model,
                                            self.transform_constructor,
                                            weights=flattened)

    def as_vector(self):
        return self.weights

    def _apply(self, x, **kwargs):
        return self.transform._apply(x, **kwargs)

    def compose(self, a):
        pass

    def inverse(self):
        pass