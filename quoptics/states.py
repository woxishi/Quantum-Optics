import numpy as np
from abc import ABC, abstractmethod
from scipy.special import factorial
from . import conf
from . import operators as ops

## Classes representing different types of state
class _State(ABC):
    """
    Base state object
    """
    def __init__(self, analytic=True, T=None, **kwargs):
        self._analytic = analytic
        self._T = conf.T if T is None else T
        self._data = np.empty(self.T)
        self.params = kwargs
        super().__init__()
        self._gen_data()

    # Make self.data read-only
    @property
    def data(self):
        return self._data

    @property
    def analytic(self):
        return self._analytic

    # Re-calculate data using correct method when self.analytic is changed
    @analytic.setter
    def analytic(self, value):
        self._analytic = value
        self._gen_data()

    @property
    def T(self):
        return self._T

    # Recalculate data with correct truncation when self.T is changed
    @T.setter
    def T(self, value):
        self._T = value
        self._gen_data()

    def inner_prod(self, state):
        """Calculates the inner product of this state with another"""
        phi_star = np.conj(state.data)
        psi = self.data
        return np.dot(phi_star, psi)

    def norm(self):
        """Calculates the inner product of the state with itself (the norm)"""
        return np.real(self.inner_prod(self))

    def avg_n(self):
        """Calculates the expected/average number of photons in the state"""
        n = ops.number(self.T) # Number operator
        n_psi = n @ self.data
        return np.dot(np.conj(self.data), n_psi)

    def _gen_data(self):
        self._data = self._gen_analytic() if self.analytic else self._gen_op()

    @abstractmethod
    def _gen_analytic(self):
        """Calculates the state data using an analytic expression"""
        pass

    @abstractmethod
    def _gen_op(self):
        """
        Calculates the state data by acting on the vacuum state with the
        apppropriate operator
        """
        pass

class Fock(_State):
    """
    Basis number states
    :param n: Number of the Fock state
    """
    def __init__(self, n, analytic=True, T=None):
        self.type = 'fock'
        self._n = 0
        super().__init__(analytic=analytic, T=T, n=n)
        self.n = n # Validate n

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, value):
        if value != int(value) or value < 0:
            raise ValueError("n must be a non-negative integer")
        self._n = value
        self._gen_data()

    def _gen_analytic(self):
        return _fock(self.n, self.T)

    def _gen_op(self):
        creation = ops.creation(self.T)
        fock_op = np.linalg.matrix_power(creation, self.n)
        norm_factor = np.product([np.sqrt(i) for i in range(1, self.n+1)])
        return (fock_op @ _fock(0, self.T)) / norm_factor

class Coherent(_State):
    """
    Coherent states from analytic expression in Fock basis
    :param alpha: Complex number parametrising the coherent state
    """
    def __init__(self, alpha, analytic=True, T=None):
        self.type = 'coherent'
        self._alpha = alpha
        super().__init__(analytic=analytic, T=T, alpha=alpha)

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value
        self._gen_data()

    def _gen_analytic(self):
        return _coherent1(self.alpha, self.T)

    def _gen_op(self):
        return _coherent2(self.alpha, self.T)

class Cat(Coherent):
    """
    Cat states are a superposition of coherent states given by:
        |cat> = (1\sqrt(2))*(|alpha> +/- |-alpha>)
    Where |alpha> are coherent states
    :param alpha: Complex number parametrising the state
    :param sign: The sign to use when combining the coherent states ('+' or '-')
    """
    def __init__(self, alpha, sign='+', analytic=True, T=None):
        # Sign needs to be set before call to super, since super.__init__ will
        # call _gen_data, which requires self._sign to be set
        self._validate_sign(sign)
        self._sign = '+'
        super().__init__(alpha, analytic=analytic, T=T)
        self.type = 'cat'
        self.params['sign'] = sign

    @property
    def sign(self):
        return self._sign

    @sign.setter
    def sign(self, value):
        self._validate_sign(value)
        self._sign = value
        self._gen_data()

    def _validate_sign(self, sign):
        if sign not in ['+', '-']:
            raise ValueError("Sign must be either '+' or '-'.")

    def _gen_analytic(self):
        alpha = _coherent1(self.alpha, self.T)
        minus_alpha = _coherent1(-self.alpha, self.T)
        data = None
        if self.sign == '+':
            data = alpha + minus_alpha
        else:
            data = alpha - minus_alpha
        return (1.0/np.sqrt(2)) * data

    def _gen_op(self):
        alpha = _coherent2(self.alpha, self.T)
        minus_alpha = _coherent2(-self.alpha, self.T)
        data = None
        if self.sign == '+':
            data = alpha + minus_alpha
        else:
            data = alpha - minus_alpha
        return (1.0/np.sqrt(2)) * data

class Squeezed(_State):
    """
    Squeezed states (single-mode) from analytic expression in Fock basis
    :param z: Complex number that parametrises the squeezed state
    """
    def __init__(self, z, analytic=True, T=None):
        self.type = 'squeezed'
        self._z = z
        super().__init__(analytic=analytic, T=T, z=z)

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, value):
        self._z = value
        self._gen_data()

    def _gen_analytic(self):
        return _squeezed1(self.z, self.T)

    def _gen_op(self):
        return _squeezed2(self.z, self.T)

## Helper methods for generating state data
def _fock(n, T):
    data = np.zeros(T)
    data[n] = 1
    return data

def _coherent1(alpha, T):
    data = [(alpha**n)/np.sqrt(factorial(n)) for n in range(T)]
    data = np.array(data)
    data = data * np.exp(-(np.abs(alpha)**2)/2)
    return data

def _coherent2(alpha, T):
    """
    Coherent states created from the displacement operator
    :param alpha: Complex number parametrising the coherent state
    """
    D = ops.displacement(alpha, T)
    state = D @ _fock(0, T) # Act on vacuum state with D(alpha)
    state = np.array(state) # Convert from np.matrix to np.array
    return state

def _squeezed1(z, T):
    if z == 0:
        # S(0) is the identity operator, so S(0)|0> = |0>
        return _fock(0, T)

    def c(i):
        """Coefficient of basis state |i>"""
        n = i/2
        cn = 1.0/np.sqrt(np.cosh(np.abs(z)))*np.sqrt(factorial(2*n))
        cn *= 1.0/factorial(n)
        cn *= (-z/(2.0*np.abs(z)))**n
        cn *= np.tanh(np.abs(z))**n
        return cn
    state = [c(n) for n in range(T)]

    # Squeezed states only have an even number of photons - set coefficients of
    # odd Fock states to 0
    zeros = np.zeros(len(state[1::2]))
    state[1::2] = zeros
    return np.array(state)

def _squeezed2(z, T):
    """
    Squeezed states (single-mode) from squeezing operator
    :param z: Complex number that parametrises the squeezed state
    """
    # Single-mode squeezing operator
    S = ops.squeezing(z, T)
    state = S @ _fock(0, T)
    return np.array(state)
