.. SimulaQron documentation master file, created by
   sphinx-quickstart on Fri May 26 13:25:00 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SimulaQron Documentation
========================

Welcome to the SimulaQron Pre-Beta! This is a first pre beta release - despite all our better efforts, we are sure that the documentation is still insufficient, and the code has bugs. As a participant in the Pre-Beta we would love to hear from you and get your feedback about anything related to SimulaQron. Please see below for how to use github to submit bug reports (or feature requests :-) )

SimulaQron is a distributed simulation of the end nodes in a future quantum internet with the specific goal to explore application development. 
The end nodes in a quantum internet are few qubit processors, which may exchange qubits using
a quantum internet. 
Specifically, SimulaQron
allows the installation of a local simulation program on each computer in the network that provides the illusion of having a local quantum processor to potential applications.
The local simulation programs on each classical computer connect to each other classically, forming a simulated quantum internet allowing the exchange of simulated qubits between the different
network nodes, as well as the creation of simulated entanglement.

SimulaQron is written in `Python <http://www.python.org/>`_ and uses the `Twisted <https://twistedmatrix.com/>`_ Perspective Broker. To perform the local qubit simulation, SimulaQron uses `QuTip <http://qutip.org/>`_ but any other quantum simulator with a python interface can easily be used as a local backend. The main challenge of SimulaQron is to allow the simulation of virtual qubits at different network nodes: since these may be entangled they cannot be simulated on one network node, which is solved by a transparent distributed simulation on top of in principle any local simulation engine.

The documentation below assumes familiarity with classical network programming concepts, Python, Twisted, as well as an elementary understanding of quantum information. We will post a paper to the arXiv describing the internal structure of SimulaQron in more detail when releasing the actual Beta of SimulaQron after this Pre-Beta release. For programming, however, this documentation is the place to look!

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   Overview
   GettingStarted
   PythonLib
   Examples
   SimulaQron
   FurtherReading


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
