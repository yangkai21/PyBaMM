#
# Class for leading-order electrolyte diffusion employing stefan-maxwell
#
import pybamm
import numpy as np

from .base_electrolyte_diffusion import BaseElectrolyteDiffusion


class LeadingOrder(BaseElectrolyteDiffusion):
    """Class for conservation of mass in the electrolyte employing the
    Stefan-Maxwell constitutive equations. (Leading refers to leading order
    of asymptotic reduction)

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel


    **Extends:** :class:`pybamm.electrolyte_diffusion.BaseElectrolyteDiffusion`
    """

    def __init__(self, param):
        super().__init__(param)

    def get_fundamental_variables(self):
        c_e_av = pybamm.Variable(
            "X-averaged electrolyte concentration",
            domain="current collector",
            bounds=(0, np.inf),
        )
        c_e_av.print_name = "c_e_av"

        c_e_dict = {
            domain: pybamm.PrimaryBroadcast(c_e_av, domain)
            for domain in self.options.whole_cell_domains
        }

        variables = self._get_standard_concentration_variables(c_e_dict)

        N_e = pybamm.FullBroadcastToEdges(
            0, self.options.whole_cell_domains, "current collector"
        )
        variables.update(self._get_standard_flux_variables(N_e))

        return variables

    def get_coupled_variables(self, variables):
        c_e = variables["Electrolyte concentration"]
        eps = variables["Porosity"]

        variables.update(self._get_total_concentration_electrolyte(eps * c_e))

        return variables

    def set_rhs(self, variables):
        param = self.param

        c_e_av = variables["X-averaged electrolyte concentration"]

        T_av = variables["X-averaged cell temperature"]

        eps_n_av = variables["X-averaged negative electrode porosity"]
        eps_s_av = variables["X-averaged separator porosity"]
        eps_p_av = variables["X-averaged positive electrode porosity"]

        deps_n_dt_av = variables["X-averaged negative electrode porosity change"]
        deps_p_dt_av = variables["X-averaged positive electrode porosity change"]

        div_Vbox_s_av = variables[
            "X-averaged separator transverse volume-averaged acceleration"
        ]

        sum_a_j_n_0 = variables[
            "Sum of x-averaged negative electrode volumetric "
            "interfacial current densities"
        ]
        sum_a_j_p_0 = variables[
            "Sum of x-averaged positive electrode volumetric "
            "interfacial current densities"
        ]
        sum_s_j_n_0 = variables[
            "Sum of x-averaged negative electrode electrolyte reaction source terms"
        ]
        sum_s_j_p_0 = variables[
            "Sum of x-averaged positive electrode electrolyte reaction source terms"
        ]
        source_terms = (
            param.n.l * (sum_s_j_n_0 - param.t_plus(c_e_av, T_av) * sum_a_j_n_0)
            + param.p.l * (sum_s_j_p_0 - param.t_plus(c_e_av, T_av) * sum_a_j_p_0)
        ) / param.gamma_e

        self.rhs = {
            c_e_av: 1
            / (param.n.l * eps_n_av + param.s.l * eps_s_av + param.p.l * eps_p_av)
            * (
                source_terms
                - c_e_av * (param.n.l * deps_n_dt_av + param.p.l * deps_p_dt_av)
                - c_e_av * param.s.l * div_Vbox_s_av
            )
        }

    def set_initial_conditions(self, variables):
        c_e = variables["X-averaged electrolyte concentration"]
        self.initial_conditions = {c_e: self.param.c_e_init}
