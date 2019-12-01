import math
from functools import reduce
from structure.flight import Flight
from structure.Wing import Wing
from structure.component import Component
from structure.Equipment import Equipment
from aerodynamic_utils import np_from_xfoil

class Plane():
    TIME_INCR = 0.05                    # time increment
    def __init__(self, *, x_axis_len, flight: Flight):
        self.flight = flight
        self.project_name = None
        self.components = []
        self.fuselage_mass = 0.0
        self.total_mass = 0.0
        self.x_axis_len = x_axis_len
        self.x_axis = {} # {'propeller': {'begin': 10.0, 'end': 12.0, 'obj': obj_reference}}
        self.wind_gust_offset = None
        self.wind_gust_force = None
        self.angular_velocity = 0.0

    def add_component(self, *, component: Component, x_offset): # only for wetted surfaces
        if x_offset + component.root_chord > self.x_axis_len:
            raise ValueError(f"The component's end at {x_offset+component.root_chord} falls beyond the plane's centerline of length {self.x_axis_len}")
        self.components.append((component, x_offset))
        component_cg = component.root_chord / 2      # assume even weight distribution
        self.x_axis[component.name] = {'begin': x_offset, 'end': x_offset + component.root_chord, 'mass': component.mass, 'obj': component}
        self.total_mass += component.mass

    def remove_component(self, *, component_name):
        self.total_mass -= self.x_axis[component_name]['obj'].mass
        components = [c for c in self.components if c[0].name != component_name]
        del self.x_axis[component_name]['obj']
        del self.x_axis[component_name]

    def move_component(self, *, name, distance):
        new_begin = round(self.x_axis[name]['begin'] + distance, 4)
        new_end = round(self.x_axis[name]['end'] + distance, 4)
        if new_begin < 0:
            raise OutsideCenterlineException("Component offset cannot be less than zero.")
        if new_end > self.x_axis_len:
            raise OutsideCenterlineException("Component cannot extend beyond the centerline.")
        self.x_axis[name]['begin'] = new_begin
        self.x_axis[name]['end'] = new_end
        print (f"Unable to move {name}")

    def add_equipment(self, *, name, x_offset, length, mass, eq_type=None):
       if x_offset + length > self.x_axis_len:
           raise ValueError(f"The equipment's end at {x_offset+length} falls beyond the plane's centerline of length {self.x_axis_len}")
       self.x_axis[name] = {'begin': x_offset, 'end': x_offset + length, 'mass': mass, 'obj': Equipment(name, mass, length), 'type': eq_type}
       self.total_mass += mass

    def set_xobj_or_none(self, component_name, field_name, new_value):
        if getattr(self.x_axis[component_name]['obj'], field_name, None) is not None:
            setattr(self.x_axis[component_name]['obj'], field_name, new_value)
            return True
        else:
            return False

    def validate_param_update(self, *, input_fields):
        component_name = input_fields['comp_name_orig_input']
        entity_map = {'comp_name_input':  'name', \
                      'comp_mass_input':  'mass', \
                     'comp_width_input':  'length', \
                'comp_xfoil_data_input':  'xfoil_data', \
                       'comp_aoi_input':  'aoi', \
                 'comp_rootchord_input':  'root_chord', \
                  'comp_tipchord_input':  'tip_chord', \
                   'comp_charlen_input':  'characteristic_length', \
                       'comp_thickness':  'thickness', \
                  'comp_semispan_input':  'semispan', \
                     'comp_wetted_area':  'wetted_area'
        }

        for param_name, new_value in input_fields.items():
            if param_name == 'comp_name_input':
                if component_name in ['wings', 'htail'] and new_value not in ['wings', 'htail']:
                    raise FormValidationException("`wings` and `htail` are reserved component names")
               # todo: sprawdzic czy nazwy komponentow unikatowe
            # SHARED CHECK FOR ALL COMPONENTS:
            try:
                if param_name in ['comp_mass_input', 'comp_width_input']:
                    try:
                        new_value = float(new_value)
                        if new_value <=0:
                            raise FormValidationException
                    except FormValidationException:
                        raise FormValidationException(f"Parameter {param_name} must be greater than zero")
                if param_name == 'comp_x_offset_input':
                    if float(new_value) < 0 or float(new_value) > self.x_axis_len:
                        raise FormValidationException("Component cannot extend beyond the centerline")
                if param_name == 'comp_width_input':
                    if float(new_value) < 0 or self.x_axis[component_name]['begin'] + float(new_value) > self.x_axis_len:
                        raise FormValidationException("Component cannot extend beyond the centerline")
                # CHECKS ONLY FOR LIFTING SURFACES:
                if component_name not in ['wings', 'htail']:
                    continue
                if param_name in ['comp_charlen_input', 'comp_thickness', 'comp_wetted_area', 'comp_semispan_input']:
                    if float(new_value) <= 0:
                        raise FormValidationException(f"Parameter {param_name} must have a value greater than zero")
                if param_name == 'comp_rootchord_input':
                    if float(input_fields['comp_rootchord_input']) < float(input_fields['comp_tipchord_input']):
                        raise FormValidationException("Tip chord cannot be longer than root chord")
                if param_name == 'comp_tipchord_input':
                    if float(input_fields['comp_tipchord_input']) > float(input_fields['comp_rootchord_input']):
                        raise FormValidationException("Tip chord cannot be longer than root chord")
            except ValueError:
                raise ValueError("Incorrect data in the form")
        for param_name, new_value in input_fields.items():
            if param_name in ['comp_x_offset_input', 'comp_name_input']:
                continue
            if component_name not in ['wings', 'htail'] and param_name not in ['comp_mass_input', 'comp_width_input']:
                continue
            if param_name not in ['comp_name_input', 'comp_xfoil_data_input']:
                try:
                    new_value = float(new_value)
                except ValueError:
                    print(f"Cannot understand `{new_value}` for `{param_name}`")
                    continue
            if self.set_xobj_or_none(component_name, entity_map[param_name], new_value) == True:
                print(f"Setting {param_name} to {new_value}")
            else:
                print(f"Unable to set {param_name} to {new_value}")
        old_comp_name = component_name
        new_comp_name = input_fields['comp_name_input']
        old_begin = self.x_axis[old_comp_name]['begin']
        if component_name in ['wings', 'htail']:
            self.x_axis[old_comp_name]['end'] = old_begin + float(input_fields['comp_rootchord_input'])
        else:
            self.x_axis[old_comp_name]['end'] = old_begin + float(input_fields['comp_width_input'])
        self.x_axis[old_comp_name]['mass'] = float(input_fields['comp_mass_input'])
        new_begin = float(input_fields['comp_x_offset_input'])
        self.move_component(name=old_comp_name, distance=new_begin - old_begin)
        new_dict_elem = self.x_axis.pop(old_comp_name)
        self.x_axis[new_comp_name] = new_dict_elem

    def set_thrust(self, val):
        self.flight.thrust = val

    @property
    def cg_offset(self): # CAREFUL with subsequent aerodynamic properties: fuselage CG was not included before!
        total_moment = self.fuselage_mass * (self.x_axis_len / 2) # for the fuselage
        total_mass = self.fuselage_mass
        for el_name, elem in self.x_axis.items():
            elem_cg = elem['begin'] + ((elem['end'] - elem['begin'])/2)
            print (f"'{el_name}' cg = {elem_cg}, mass = {elem['mass']}")
            total_moment += (elem_cg * elem['mass'])
            total_mass += elem['mass']
        return total_moment / total_mass

    @property
    def np_offset(self):
        """ Rough estimation without a specific flight condition """
        #mac_wing = self.x_axis['wings']['begin'] + (0.25*self.x_axis['wings']['obj'].chord)
        #mac_tail = self.x_axis['htail']['begin'] + (0.25*self.x_axis['htail']['obj'].chord)
        if self.x_axis.get('wings') is None or self.x_axis.get('htail') is None:
            return None
        wing_obj = self.x_axis['wings']['obj']
        tail_obj = self.x_axis['htail']['obj']
        wing_ac_offset = self.x_axis['wings']['begin'] + wing_obj.AC
        tail_ac_offset = self.x_axis['htail']['begin'] + tail_obj.AC
        tail_arm = tail_ac_offset - wing_ac_offset
        tail_volume = (tail_obj.area * tail_arm) / (wing_obj.area * wing_obj.MAC)
        np_perc_mac = 0.25 + (0.8 * tail_volume * (tail_obj.aspect_ratio/wing_obj.aspect_ratio) * 0.6) # neutral point as % of MAC
        np_le_offset = wing_obj.MAC*np_perc_mac
        # print (f"NP (% of MAC) = {np_perc_mac}, from LE: {np_le_offset}")
        return self.x_axis['wings']['begin'] + np_le_offset

    @property
    def np_xfoil(self):
        """ Estimation from wing and tail's lift coefficients """
        if self.x_axis.get('wings') is None or self.x_axis.get('htail') is None:
            return
        if self.x_axis['wings']['obj'].cl_data is None or self.x_axis['htail']['obj'].cl_data is None:
            print ("Cannot estimate the neutral point from Xfoil data")
            return None
        if self.x_axis['wings']['obj'].Re is None or self.x_axis['htail']['obj'].Re is None:
            print ("Cannot estimate the neutral point without flight conditions")
            return None
        npm = np_from_xfoil(cl_data_wing=self.x_axis['wings']['obj'].cl_data,\
                            cl_data_tail=self.x_axis['htail']['obj'].cl_data,\
                            Re_wing=self.x_axis['wings']['obj'].Re,\
                            Re_tail=self.x_axis['htail']['obj'].Re,\
                            alpha_wing=self.x_axis['wings']['obj'].aoa,\
                            alpha_tail=self.x_axis['htail']['obj'].aoa,\
                            l_H=(self.x_axis['htail']['begin'] + self.x_axis['htail']['obj'].AC) - (self.x_axis['wings']['begin'] + self.x_axis['wings']['obj'].AC),\
                            S=self.x_axis['wings']['obj'].area,\
                            S_H=self.x_axis['htail']['obj'].area,\
                            eps=0.1) # assume fixed 10% downwash angle
        return self.x_axis['wings']['obj'].AC + npm

    @property
    def wing_cp_offset(self):
        return self.x_axis['wings']['obj'].Xcp + self.x_axis['wings']['begin']

    @property
    def tail_cp_offset(self):
        return self.x_axis['htail']['obj'].Xcp + self.x_axis['htail']['begin']

    @property
    def wing_pitching_moment(self):
        arm = self.wing_cp_offset - self.cg_offset
        force = self.x_axis['wings']['obj'].L
        return force*arm

    @property
    def tail_pitching_moment(self):
        arm = self.tail_cp_offset - self.cg_offset
        force = self.x_axis['htail']['obj'].L
        return force*arm

    @property
    def wind_gust_moment(self):
        if self.wind_gust_force is None or self.wind_gust_offset is None:
            return 0.0
        else:
            arm = self.cg_offset - self.wind_gust_offset
            force = self.wind_gust_force
            return force*arm

    @property
    def total_moment(self): # including inflight variation of forces (BROKEN - DO NOT USE)
        tot = 0.0
        if self.x_axis['wings']['cg'] > self.cg_offset:
            tot += self.wing_pitching_moment
        else:
            tot -= self.wing_pitching_moment
        if self.x_axis['htail']['cg'] > self.cg_offset:
            tot += self.tail_pitching_moment
        else:
            tot -= self.tail_pitching_moment
        if self.wind_gust_force is not None:
            if self.wind_gust_offset > self.cg_offset:
                tot += self.wind_gust_moment
            else:
                tot -= self.wind_gust_moment
        return tot

    @property
    def angular_acceleration(self):
        wing_cp_to_cg_arm = (self.x_axis['wings']['begin'] + self.x_axis['wings']['obj'].Xcp) - self.cg_offset
        tail_cp_to_cg_arm = (self.x_axis['htail']['begin'] + self.x_axis['htail']['obj'].Xcp) - self.cg_offset
        gust_to_cg_arm = 0 if self.wind_gust_offset is None else self.cg_offset - self.wind_gust_offset
        total_moment_of_inertia = (math.pow(gust_to_cg_arm, 2)*self.total_mass + math.pow(wing_cp_to_cg_arm, 2)*self.total_mass + math.pow(tail_cp_to_cg_arm, 2)*self.total_mass)
        #total_moment = self.wind_gust_moment + self.wing_pitching_moment + self.tail_pitching_moment
        total_moment = self.total_moment
        #if total_moment < 0.5:
        #    total_moment = 0.0
        return 0.175*(total_moment / total_moment_of_inertia) # in degrees per second squared

    def _tick(self):
        curr_drag = reduce(lambda x,y: x+y, map(lambda z: z[0].D, self.components)) # sum up drag from all components
        curr_drag = reduce(lambda x,y: x+y, map(lambda z: z[0].D, self.components)) # sum up drag from all components
        curr_net_thrust = self.flight.thrust - curr_drag
        self.flight.true_airspeed = self.flight.true_airspeed + ((curr_net_thrust / self.total_mass)*Plane.TIME_INCR) # V = V0 + at, where a is net_thrust / aircraft mass
        self.angular_velocity = self.angular_velocity + self.angular_acceleration * Plane.TIME_INCR
        self.flight.pitch += (self.angular_velocity * Plane.TIME_INCR)

class OutsideCenterlineException(Exception):
    pass

class FormValidationException(Exception):
    pass
