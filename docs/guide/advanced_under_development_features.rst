.. _advanced_under_development_features:

Advanced under-development features
===================================




Ice storage
------------

The IceStorage class was implemented within the storages module of optihood. The formulation of the ice
storage model is based on the solution of the energy conservation law applied to the water of the storage as
per Carbonell et al. (2015) [1]. It is basically the same as the energy conservation law for hot water storage with
the inclusion of the latent heat term for ice formation :math:`\frac{h_f}{V}\frac{\delta M_{ice}}{\delta t}`:

.. math::

      \rho c_p V \frac{\delta T_{stor}}{\delta t} = -(UA)_{tank} \cdot (T_{stor} - T_{amb}) + \frac{h_f}{V} \frac{\delta M_{ice}}{\delta t} + sum_{i=1}^n \dot Q_{hx-port}(i)

where :math:`\rho` and :math:`c_p` stand for the density and specific heat capacity of water, respectively. :math:`V` is the storage volume, :math:`T_{stor}` is the average temperature of the storage, :math:`T_{amb}` is the ambient air temperature, :math:`(U A)_{tank}` is the product of overall heat transfer coefficient and the external area of the storage tank, :math:`M_{ice}` is the mass of ice and :math:`h_f` the latent heat of fusion. :math:`q_{hx-port}` are the heat fluxes between the heat exchanger and the direct ports and can be represented as:

.. math::

      \sum_i \dot{Q}_{x-port}(i) = \sum_i \dot{Q}_{in}(i) - \sum_i \dot{Q}_{out}(i)

here :math:`Q_{in}` and :math:`Q_{out}` are the heat inflows and outflows to/from the ice storage tank, respectively.
The term for heat of solidification and melting appearing in Eq. 4 can be discretized as:

.. math::

      \dot{Q}_{tot} = h_f \frac{M_{ice}^{t+1} - M_{ice}}{\Delta t}

The complete discretized equation for ice storage model is represented as:

.. math::

      \rho c_p V \frac{T_{stor}^{t+1} - T_{stor}^t}{\delta t} = -(UA)_{tank} \cdot (T_{stor}^t - T_{amb}^t) + h_f  \frac{M_{ice}^{t+1} - M_{ice}}{\Delta t} + sum_{i=1}^n \dot{Q}_{hx-port}(i)^t

In order to solve this equation one can split the formulation in two parts. One considering only the sensible
part where the Mice = 0 kg and a second formulation for the latent part assuming T = 0 °C. The equation
with ice formation is reduced to:

.. math::

      0 = (UA)_{tank} \cdot (T_{stor}^t - T_{amb}^t) + h_f  \frac{M_{ice}^{t+1} - M_{ice}}{\Delta t} + sum_{i=1}^n \dot {Q}_{hx-port}(i)^t

In addition, the following constraints were implemented. The constraint to set up the initial conditions such
as initial storage temperature and initial mass of ice is given by:

.. math::

   \begin{align*}
   \begin{bmatrix}
   T_{stor}^0 \\
   M_{ice}^0
   \end{bmatrix}
   &= \begin{bmatrix}
   T_{stor}^{init} \\
   0
   \end{bmatrix}
   \end{align*}

The constraint for the temperature of storage during ice formation is given by:

.. math::

      T_{stor}^i \geq 0 \forall i \in t

The mass ice fraction also known as ice packing factor, :math:`f^t`, is calculated as:

.. math::

      f^t = \frac{M_{ice}^t}{M_{water,\text{max}}}

where, :math:`M_{water,max}` denotes the overall amount of water and ice in the storage tank. The constraint on the
maximum allowed value of :math:`f^t` is represented as:

.. math::

      f^t \leq f_{max}

Depending on the ice storage design, the :math:`f_{max}` can be in the range of 0.5 to 0.8.

References
==========

[1]  Carbonell, D., Philippen, D., Haller, M. Y., and Frank, E. (2015). Modeling of an ice storage based on a
de-icing concept for solar heating applications. Solar Energy, 121:2–16.
