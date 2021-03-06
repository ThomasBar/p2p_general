# -*- coding: utf-8 -*-
"""
Created on Mon Jan 15 10:11:54 2018

@author: fmoret
"""

# Import Gurobi Library
import gurobipy as gb
import numpy as np

# Class which can have attributes set.
class expando(object):
    pass


# Subproblem
class Prosumer:
    def __init__(self, inc, data=None, rho=1):
        self.data = expando()
        try:
            self.data.a = data['a'].values
            self.data.b = data['b'].values
            self.data.Pmin = data['Pmin'].values
            self.data.Pmax = data['Pmax'].values
            self.data.num_assets = data.shape[0]
        except TypeError:
            self.data.a = 0
            self.data.b = 0
            self.data.Pmin = -np.inf
            self.data.Pmax = np.inf
            self.data.num_assets = 0
        self.data.partners = inc.nonzero()
        self.data.pref = inc[inc.nonzero()]
        self.data.num_partners = len(self.data.pref)
        self.data.rho = rho
        
        self.variables = expando()
        self.constraints = expando()
        self.results = expando()
        self._build_model()

    def optimize(self, trade):
        self._iter_update(trade)
        self._update_objective()
        self.model.optimize()
        for i in range(self.data.num_partners):
            self.t_old[i] = self.variables.t[i].x
        trade[self.data.partners] = self.t_old
        return trade

    ###
    #   Model Building
    ###
    def _build_model(self):
        self.model = gb.Model()
        self.model.setParam( 'OutputFlag', False )
        self._build_variables()
        self._build_constraints()
        self._build_objective()
        self.model.update()

    def _build_variables(self):
        m = self.model
        self.variables.p = np.array([m.addVar(lb = self.data.Pmin[i], ub = self.data.Pmax[i], name = 'p') for i in range(self.data.num_assets)])
        self.variables.t = np.array([m.addVar(lb = -gb.GRB.INFINITY, obj=self.data.pref[i], name = 't') for i in range(self.data.num_partners)])
        self.t_old = np.zeros(self.data.num_partners)
        self.y = np.zeros(self.data.num_partners)
        m.update()
        
    def _build_constraints(self):
        self.constraints.pow_bal = self.model.addConstr(sum(self.variables.p) == sum(self.variables.t))
        
    def _build_objective(self):
        self.obj_assets = sum(self.data.b*self.variables.p + self.data.a*self.variables.p*self.variables.p)
        
    ###
    #   Model Updating
    ###    
    def _update_objective(self):
        augm_lag = (
                    self.data.rho/2*sum( ( (self.t_old - self.t_others)/2 - self.variables.t + self.y )*
                                        ( (self.t_old - self.t_others)/2 - self.variables.t + self.y ) )
                     - self.data.rho/2*sum(self.y*self.y)
                   )
        self.model.setObjective(self.obj_assets + augm_lag)
        self.model.update()
        
    ###
    #   Iteration Update
    ###    
    def _iter_update(self, trade):
        self.t_others = trade[self.data.partners]
        self.y -=  (self.t_old + self.t_others)/2