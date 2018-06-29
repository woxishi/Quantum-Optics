# Quantum Optics   

Python code with the ultimate goal of classifying quantum states of light using
a neural network

The `quoptics` module contains useful code for producing various states (e.g.
coherent states, squeezed states, etc). It also has matrix representations of
various operators.
The vectors it produces are in the Fock basis, so the nth component of the
vector is the coefficient of |n>, or equivalently `psi[n] = <psi|n>`

Run `python data/gen_data.py` to generate training/test/validation data for the
network. The data is produced as an array of states and an array of labels, such
 that states[n] is labelled by label[n]. The labels are integers labelling what
 type the state is according to:

| Label  | State Type |
| ------ | ---------- |
|    0   |    Fock    |
|    1   |  Coherent  |
|    2   |  Squeezed  |

Once the data has been generated, run `python network.py` to train and test the
neural network.
