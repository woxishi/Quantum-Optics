import numpy as np
import tensorflow as tf
from network import NeuralNetwork
from qutip import fidelity
from qutip.states import coherent, basis
from quoptics.states import cat, squeezed
from quoptics.states import StateIterator

sess = tf.Session()
net = NeuralNetwork(sess)
net.restore("weights")
T = 100

def complex_range(max_x, npts):
    """
    Returns an array consisting of equally spaced points in the square
    of side length max_x centred at the origin in the complex plane.

    :param npts: The number of points in the array. Should be a square number
    :param max_x: Side length of the square to sample
    """
    length = int(np.round(np.sqrt(npts)))
    x_vals = np.linspace(0, max_x, length)
    X, Y = np.meshgrid(x_vals, x_vals)
    X = X.reshape(length**2)
    Y = Y.reshape(length**2)
    output = X + 1j*Y
    return output


def find_fidelity_fn(state):
    """
    Classifies the input state using the neural network, then returns a function
    that calculates the fidelity between the input state and the type of state
    it was classified as, along with a range of parameter values to try.
    For example, if the input state |psi> is classified as a coherent state, the
    function returned will be:
        f(alpha) = |<psi|alpha>|^2
    And trial_values will be a list of complex numbers covering the grid formed
    by +/-1.5 and +/-1.5i

    :param state: A qutip.Qobj instance
    """
    input = state.data.toarray().T[0]
    input = np.abs(input)

    type = net.classify(input)
    trial_values = None

    fid_fn = None
    if type == 0:
        fid_fn = np.vectorize(lambda param: fidelity(state, basis(T, param)))
        trial_values = np.linspace(0, T-1, T, dtype=int)
    elif type == 1:
        fid_fn = np.vectorize(lambda param: fidelity(state, coherent(T, param)))
        trial_values = complex_range(1.5, 100)
    elif type == 2:
        fid_fn = np.vectorize(lambda param: fidelity(state, squeezed(T, param)))
        trial_values = complex_range(1.7, 100)
    elif type == 3:
        fid_fn = lambda param: fidelity(state, cat(T, param[0], theta=param[1]))
        # Fidelity function for non-exact cat states have 2 parameters
        alpha = complex_range(1.0, 50)
        theta = np.linspace(0, 2*np.pi, 50)
        alpha, theta = np.meshgrid(alpha, theta)
        alpha = alpha.reshape(alpha.size)
        theta = theta.reshape(theta.size)

        trial_values = zip(alpha, theta)
        trial_values = np.array(list(trial_values)).T
    else:
        raise Exception(("Neural network returned unknown classification. "
        "Expected one of [0,1,2,3] but received {}.").format(type))

    return fid_fn, trial_values

def calc_fidelity(state):
    """
    Calculates the maximum fidelity of the input state with the class of states
    the inputs state is classified is. E.g. if `state` is a coherent state,
    then:
        F = \max_{\alpha} |<\psi|\alpha>|^2
    is calculated.

    :param state: a qutip.Qobj instance
    """
    # fid is a function that takes a parameter as input and calculates the
    # fidelity of `state` with the fock/coherent/squezed/cat state with the
    # given parameter. See find_fidelity_fn for more details. trial is an array
    # of values to try for the parameter.
    # import pdb; pdb.set_trace()
    fid, trial = find_fidelity_fn(state)
    # Calculate the fidelity for each trial value of the parameter
    # TODO: Speed this up. Try only calculating all states in the search space
    # for each type of state once at the start, then calcuting fidelity is
    # only a matrix multiplication
    fid_values = np.apply_along_axis(fid, 0, trial)
    # Return the maximum fidelity value
    return np.max(fid_values)

if __name__ == '__main__':
    # Generate 100 random states (with labels)
    states = [x for x in StateIterator(100, T=100)]
    # Discard the state labels - we don't need them
    states, _ = zip(*states)
    # Calculate the classification probability and fidelity for each state
    probabilities = np.empty(100)
    fidelities = np.empty(100)
    for i, state in enumerate(states):
        data = np.abs(state.data.toarray().T[0])
        probabilities[i] = np.max(net.classify_dist(data))
        fidelities[i] = calc_fidelity(state)
        print("State {}: ({}, {})".format(i, probabilities[i], fidelities[i]))
    # Plot fidelity against probability
    import matplotlib.pyplot as plt
    plt.figure()
    plt.scatter(fidelities, probabilities, s=10, marker='x')
    plt.xlim([0, 1.02])
    plt.ylim([0, 1.02])
    plt.xlabel("Fidelity")
    plt.ylabel("Probability")
    plt.show()
