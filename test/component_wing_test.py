#!/usr/bin/env python3
import sys
#sys.path.append('/wymiana/Projekty/Studia/MY1wlasne/asp/airplane_stability/')
#sys.path.append('..')
print (sys.path)
import pytest
from structure.Wing import Wing
from structure.flight import Flight

@pytest.fixture
def setup_flight_params():
    f = Flight()
    f.true_airspeed = 20.42
    test_wing = Wing(params_dict={
        'length': 0.7954,
        'chord': 0.3134,
        'thickness': 0.0376,
        'thickness_ratio': 0.12,
        'wetted_area': 1.1046,
        'mass': 3.1743,
        'ref_area': 0.4985
        }, flight=f)
    return {'flight': f, 'wing': test_wing}

def test_ReynoldsNumber(setup_flight_params):
    test_wing = setup_flight_params['wing']
    assert 515321 <= test_wing.R <= 515322

def test_wingFormFactor(setup_flight_params):
    test_wing=setup_flight_params['wing']
    assert 1.25 <= test_wing.form_factor <= 1.26

