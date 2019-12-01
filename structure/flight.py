class Flight:
    def __init__(self):
        # self.true_airspeed = 20.4216    # m/s
        self.true_airspeed = 0.0        # m/s
        # assume ISA conditions at sea level
        self.rho = 1.144                # kg / m3
        self.atm_pressure = 983.81*100  # Pa
        self.temperature = 283.593      # K
        self.altitude = 701.4           # m above sea level
        self.air_viscosity = 0.000014207  # kinematic viscosity of air at 10 deg C
        self.thrust = 0                 # N
        self.pitch = 0.0                # deg
    
    def set_isa_sealevel(self):
        self.rho = 1.225
        self.atm_pressure = 1013.25*100
        self.temperature = 288.15
        self.altitude = 0.0
