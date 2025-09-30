from oemof.tools import economics

intRate = 0.04

def get_cost_per_capacity_data(data):
    cost_dict = {}
    for i, r in data.iterrows():
        cost_dict.update({r["label"]: (r["invest_base"], r["invest_cap"])})
    return cost_dict


def calculate_annualized_cost(cost_present, lifetime):
    annualized_cost = economics.annuity(cost_present, lifetime, intRate)
    return annualized_cost