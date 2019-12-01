from structure.Plane import Plane
from structure.flight import Flight
from structure.Wing import Wing
import json

def load_plane(*, conf_file, preflight=None):
    with open(conf_file, 'r') as f:
        plane_conf = json.load(f)
    if preflight is not None:
        f = preflight
    else:
        f = Flight()
    pl = Plane(x_axis_len=plane_conf['fuselage']['centerline'], flight=f)
    pl.project_name = plane_conf['project_name']
    pl.fuselage_mass = plane_conf['fuselage']['mass']
    for surface in plane_conf['lifting_surfaces']:
        params_dict = {}
        for k,v in surface.items():
            params_dict[k] = v
        wing = Wing(params_dict=params_dict, flight=f)
        wing.load_xfoil_data()
        pl.add_component(component=wing, x_offset=params_dict['offset'])
    for equipment in plane_conf['non_lifting_components']:
        pl.add_equipment(name=equipment['name'], x_offset=equipment['offset'], length=equipment['length'], mass=equipment['mass'], eq_type=equipment.get('type'))
    return pl

def save_plane(*, conf_file, plane: Plane, preflight=None):
    plane_object = {'project_name': plane.project_name, 'flight_conditions': {}, \
                  'fuselage': {'mass': plane.fuselage_mass, 'centerline': plane.x_axis_len}, \
                  'lifting_surfaces': [], 'non_lifting_components': []
                 }
    for lifting_surface in ['wings', 'htail']:
        surface_entry = plane.x_axis.get(lifting_surface)
        if surface_entry is not None:
            surface_obj = surface_entry['obj']
            surface_data = {'name': lifting_surface, 'type': lifting_surface, \
                            'offset': surface_entry['begin'], 'semispan': surface_obj.semispan, \
                            'root_chord': surface_obj.root_chord, 'tip_chord': surface_obj.tip_chord, \
                            'characteristic_length': surface_obj.characteristic_length, \
                            'thickness': surface_obj.thickness, \
                            'thickness_ratio': surface_obj.thickness_ratio, \
                            'wetted_area': surface_obj.wetted_area, \
                            'mass': surface_obj.mass, 'ref_area': surface_obj.ref_area, \
                            'xfoil_data': surface_obj.xfoil_data, \
                            'aoi': surface_obj.aoi
                            }
            plane_object['lifting_surfaces'].append(surface_data)
    for eq_name, equipment in plane.x_axis.items():
        if eq_name in ['wings', 'htail']:
            continue
        equipment_data = {'name': eq_name, 'type': equipment.get('type'), \
                'offset': equipment.get('begin'), \
                'length': equipment.get('end') - equipment.get('begin'), \
                'mass': equipment.get('mass')
                }
        plane_object['non_lifting_components'].append(equipment_data)
    serialized=json.dumps(plane_object, indent=4)
    with open(conf_file, 'w') as f:
        f.write(serialized)

def new_plane_from_gui(dialog_params):
    new_plane = Plane(x_axis_len=dialog_params['centerline'], flight=None)
    new_plane.fuselage_mass = dialog_params['fuselage_mass']
    new_plane.project_name = dialog_params['project_name']
    save_plane(conf_file=dialog_params['new_file'], plane=new_plane)
