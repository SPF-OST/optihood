.. _advanced_under_development_features:

Advanced under-development features
===================================



Clustering
----------

Clustering feature allows the users to improve the optimization speed by specifying a set of dates which could be considered
representative of the whole year (or the entire duration of the analysis). For example: four typical days could be selected
, one representing each season, and optihood would then provide the optimal design plan of the energy network based on these
days. Since the time resolution of the optimization problem would be much lower than simulating the whole year, the speed
of optimization is much faster when clustering is used.

Any clustering method (for example K-means clustering) can be chosen by the user and the results could be fed to optihood
for faster optimization. Note that in optihood one could use the results from clustering (which is to be done independently)
but the implementation of the clustering method itself is not a part of the optihood framework. The following results are
required from the clustering algorithm:

- Number of clusters
- Days of year representing each cluster
- Number of days in each cluster

In order to use the clustering feature, first a dictionary containing one item for each cluster, where keys and values are
the cluster's representative date and number of days, respectively, should be defined::

    cluster = {"2018-07-30": 26,
               "2018-02-03": 44,
               "2018-07-23": 32,
               "2018-09-18": 28,
               "2018-04-15": 22,
               "2018-10-01": 32,
               "2018-11-04": 32,
               "2018-10-11": 37,
               "2018-01-24": 15,
               "2018-08-18": 26,
               "2018-05-28": 23,
               "2018-02-06": 48}

Here, the days of the year have been represented using 12 clusters, where the first cluster consists of 26 days and is
represented by the date 30 June 2018.

This dictionary should be passed in the ``setFromExcel`` and ``optimize`` functions of the EnergyNetwork class::

    # set a time period for the optimization problem according to the number of clusers
    network = EnergyNetwork(pd.date_range("2018-01-01 00:00:00", "2018-01-12 23:00:00", freq="60min"), temperatureSH, temperatureDHW)

    # pass the dictionary defining the clusters to setFromExcel function
    network.setFromExcel("scenario.xls", numberOfBuildings=4, clusterSize=cluster, opt="costs")

    # pass the dictionary defining the clusters to optimize function
    envImpact, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', clusterSize=cluster)

Note that the time period would need to be adjusted to include the timesteps corresponding to 12 days (12 x 24 = 288 timesteps
if hourly resolution is considered). Try the example on `selective days clustering <https://github.com/SPF-OST/optihood/blob/main/data/examples/selective_days_clustering.py>`_
for a better grasp.

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
