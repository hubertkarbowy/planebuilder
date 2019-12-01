import math
from abc import ABC, abstractmethod
from .flight import Flight


class Component(ABC):

    def __init__(self, *, params_dict, flight:Flight):
        self.flight = flight
        self.characteristic_length = params_dict['characteristic_length']
        self.mass = params_dict.get('mass')
        self.ref_area = params_dict['ref_area']
        self.name = params_dict.get('name')
        if self.name is None:
            raise ValueError("Name must be given")
        self.crud_factor = params_dict.get('crud_factor') or 0.28
        # filled in by constructors in subclasses:
        self.wetted_area = None
        
    @property
    def Re(self):
        #return (self.flight.rho * self.flight.true_airspeed * self.characteristic_length) \
        #        / self.flight.air_viscosity
        if self.flight is None or self.flight.true_airspeed < 0.8:
            print ("No flight conditions to calculate Reynolds number")
            return None
        return (self.flight.true_airspeed * self.characteristic_length) \
                / self.flight.air_viscosity
    @property
    @abstractmethod
    def form_factor(self):
        pass

    @property # flat-plane coefficient
    def Cf(self):
        if self.Re < 100:
            return 0
        else:
            return (0.455 / math.pow(math.log10(self.Re), 2.58))

    @property # drag coefficient for parasitic drag
    def Cdp(self):
        return (self.Cf * self.form_factor * self.wetted_area) / self.ref_area

    @property # induced drag coefficient - assume 0 and override in lifting surfaces
    def Cdi(self):
        return 0.0

    @property # lift coefficient - assume 0 and override in lifting surfaces
    def Cl(self):
        return 0.0

    @property
    def D_i(self): # induced drag force
        return self.Cdi * 0.5 * self.flight.rho * math.pow(self.flight.true_airspeed, 2) * self.ref_area

    @property
    def D_p(self): # parasitic drag force
        return self.Cdp * 0.5 * self.flight.rho * math.pow(self.flight.true_airspeed, 2) * self.ref_area

    @property
    def D(self): # total drag force
        return self.D_i + self.D_p

    @property
    def L(self):
        return 0.0
