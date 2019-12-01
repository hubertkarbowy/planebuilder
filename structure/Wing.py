import math
import os
import glob
import re
from structure.component import Component
from structure.flight import Flight
from aerodynamic_utils import *

class Wing(Component):
    def __init__(self, *, params_dict, flight:Flight):
        super().__init__(params_dict=params_dict, flight=flight)
        self.sweep = params_dict.get('sweep') or 0.0
        self.root_chord = A = params_dict['root_chord']
        self.tip_chord = B = params_dict.get('tip_chord') or self.root_chord
        self.semispan = Y = params_dict['semispan']     # for *ONE* wing
        #try:
        #    self.MAC_d = Y * ((A - self.MAC)/(A-B))              # distance from root chord to mean chord
        #except ZeroDivisionError:
        #    self.MAC_d = 0.0
        # self.taper = self.tip_chord / self.root_chord
        
        self.thickness = params_dict.get('thickness') or (params_dict['thickness_ratio']*self.root_chord)
        self.thickness_ratio = params_dict.get('thickness_ratio') or self.thickness / self.root_chord # fixme: as property
        self.wetted_area = params_dict.get('wetted_area') or 2*self.area # rough approximation
        ############## WING SURFACE SPECS ############
        self.xfoil_data = params_dict.get('xfoil_data')
        self.aoi = params_dict.get('aoi') or 3.0
        self.e = params_dict.get('e') or 0.85 # Oswald efficiency facto
        ########## FIXED OR APPROXIMATED PROPERTIES ######
        self._ar = params_dict.get('aspect_ratio')
        self.cl_data = None
        self.cd_data = None
        self.cm_data = None

    @property
    def span(self):
        return self.semispan * 2

    @property
    def area(self):
        print("AREA IS ", str(((self.root_chord + self.tip_chord) / 2) * self.span))
        return ((self.root_chord + self.tip_chord) / 2) * self.span

    @property
    def aspect_ratio(self):
        return self._ar or math.pow(self.span, 2) / self.area

    @property
    def MAC(self): # mean aerodynamic chord
        A = self.root_chord; B = self.tip_chord
        return A - (2*(A-B)*(0.5*A + B)/(3*(A+B)))

    @property
    def AC(self): # aerodynamic center from the leading edge
        return 0.25 * self.MAC

    @property
    def aoa(self):
        return self.flight.pitch + self.aoi

    @property
    def form_factor(self):
        return 1 + 2*(self.thickness_ratio) + 60*(math.pow(self.thickness_ratio, 4))

    @property # lift varies with angle of attack
    def Cl(self):
        if self.flight.true_airspeed < 1:
            return 0
        elif (self.xfoil_data is None):
            return 1.0 # a good approximation for just about any AOA
        else:
            return interpolate_2d_linear(dict_fn=self.cl_data, Re=self.Re, aoa=self.aoa)

    @property
    def Cm(self):
        return interpolate_2d_linear(dict_fn=self.cm_data, Re=self.Re, aoa=self.aoa)

    @property # lift-induced drag coefficient - difficult to estimate...
    def Cdi(self):
        #if (self.xfoil_data is None):
        if self.flight.true_airspeed < 1:
            return 0
        elif False:
            return 0.0
        else:
            # return interpolate_2d_linear(dict_fn=self.cd_data, Re=self.Re, aoa=self.aoa)
            return math.pow(self.Cl, 2) / (math.pi * self.aspect_ratio * self.e)

    @property
    def L(self): # lift force
        return self.Cl * 0.5 * self.flight.rho * math.pow(self.flight.true_airspeed, 2) * self.area

    def load_xfoil_data(self):
        if self.xfoil_data == None:
            print ("No airfoil data!")
        else:
            #xfoil_data_files = [f for f in os.listdir(self.xfoil_data) if os.path.isfile(os.path.join(self.xfoil_data, f))]
            xfoil_data_files = glob.glob(f"{self.xfoil_data}/*.pol")
            print (xfoil_data_files)
            self.cl_data = {}
            self.cd_data = {}
            self.cm_data = {}
            for f in xfoil_data_files:
                with open(f, 'r') as xfoil_file:
                    reynolds_num = 0.0
                    values_row = 0; min_aoa = -100.0; max_aoa = 100.0
                    for line in xfoil_file:
                        if "Re = " in line: # parse Reynolds number
                            reynolds_num = float(re.search('Re =\s+([0-9]\.[0-9]+\se\s?-?[0-9])', line).group(1).replace(" ", ""))
                            print (f"Parsing data for Re = {reynolds_num}")
                            self.cl_data[reynolds_num] = {}
                            self.cd_data[reynolds_num] = {}
                            self.cm_data[reynolds_num] = {}
                        coeff_values = re.search("^\s+(?P<AOA>-?[0-9]+\.[0-9]+)\s+(?P<Cl>-?[0-9]+\.[0-9]+)\s+(?P<Cd>-?[0-9]+\.[0-9]+)\s+(?P<Cdp>-?[0-9]+\.[0-9]+)\s+(?P<CM>-?[0-9]+\.[0-9]+)", line)
                        if coeff_values is not None:
                            if values_row == 0:
                                min_aoa = round(float(coeff_values['AOA']), 2)
                            max_aoa = round(float(coeff_values['AOA']), 2)
                            self.cl_data[reynolds_num][round(float(coeff_values['AOA']), 2)] = float(coeff_values['Cl']) # lift coefficient by angle of attack at this Reynolds number
                            self.cd_data[reynolds_num][round(float(coeff_values['AOA']), 2)] = float(coeff_values['Cd']) # total parasitic drag coefficient
                            self.cm_data[reynolds_num][round(float(coeff_values['AOA']), 2)] = float(coeff_values['CM']) # total moment coefficient
                    # Xfoil skips some values at random, so we'll interpolate them here as well:
                    present_aoa_values = sorted(self.cl_data[reynolds_num].keys())
                    aoa_range = [round(x*0.10, 2) for x in range(-150, 149)]
                    for aoa in aoa_range:
                        if aoa not in present_aoa_values:
                            lower, upper = get_two_nearest(x=aoa, vector=present_aoa_values)
                            cl_lower = self.cl_data[reynolds_num][lower]; cl_upper = self.cl_data[reynolds_num][upper]
                            cd_lower = self.cd_data[reynolds_num][lower]; cd_upper = self.cd_data[reynolds_num][upper]
                            cm_lower = self.cm_data[reynolds_num][lower]; cm_upper = self.cm_data[reynolds_num][upper]
                            interp_cl = interpolate_1d_linear(x = aoa, x1=lower, y1=cl_lower, x2=upper, y2=cl_upper)
                            interp_cd = interpolate_1d_linear(x = aoa, x1=lower, y1=cd_lower, x2=upper, y2=cd_upper)
                            interp_cm = interpolate_1d_linear(x = aoa, x1=lower, y1=cm_lower, x2=upper, y2=cm_upper)
                            self.cl_data[reynolds_num][aoa] = interp_cl
                            self.cl_data[reynolds_num][aoa] = interp_cd
                            self.cm_data[reynolds_num][aoa] = interp_cm
                            print (f"Alpha {aoa} not present in Xfoil output for R={reynolds_num} - interpolating from {get_two_nearest(x=aoa, vector=present_aoa_values)}: Cl={interp_cl}, Cd={interp_cd}")

    def get_aerodynamic_properties(self):
        return {'Cl': self.Cl,
                'Cdi': self.Cdi,
                'Cdp': self.Cdp,
                'Cd' : self.Cdi + self.Cdp}
        #if coeff == 'Cl':
        #    data_source = self.cl_data
        #elif coeff == 'Cdi':
        #    data_source = self.cd_data
        #elif coeff == 'Cdp':
        #    print ("Induced drag coefficient to be calculated")
        #    return -99.9
        #elif coeff == 'Cd':
        #    print ("Total drag coefficient to be calculated")
        #    return -99.99
        #else:
        #    raise ValueError("Allowable coefficients: Cl, Cdi, Cdp, Cd\n(lift, lift-induced drag, parasite drag, total drag")
        #print (data_source[Re])
        #return data_source[Re][aoa]
