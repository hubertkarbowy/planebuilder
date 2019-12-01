import math

def get_two_nearest(*, x, vector):
    tmp = sorted(vector)
    if x <= vector[0]:
        return vector[0], vector[1]
    elif x >= vector[-1]:
        return vector[-2], vector[-1]
    else:
        for idx, elem in enumerate(vector):
            if elem >= x:
                return vector[idx-1], vector[idx]

def interpolate_1d_linear(*, x, x1, y1, x2, y2):
    # y = mx + b, so first get m and b
    m = (y1 - y2) / (x1 -x2)
    b = y1 - (m*x1)
    return (m*x + b)

def interpolate_2d_linear(*, dict_fn, Re, aoa, aoa_range=None):
    """ Interpolate Cl and Cd coefficient values given a Reynolds number and an angle of attack.
        Basically a 2D linear interpolation."""
    # print (dict_fn.keys())
    if aoa_range is None:
        aoa_range = [round(x* 0.10, 2) for x in range(-140,121)] # alpha from -14 to +12 degrees in increments of 0.1
    Re_known = sorted(dict_fn.keys())
    p11 = (None, None); p12 = (None, None); p21 = (None, None); p22 = (None, None)
    if Re <= Re_known[0]:
        p11 = (Re_known[0], None); p12 = (Re_known[0], None); p21 = (Re_known[1], None); p22 = (Re_known[1], None)
    elif Re >= Re_known[-1]:
        p11 = (Re_known[-2], None); p12 = (Re_known[-2], None); p21 = (Re_known[-1], None); p22 = (Re_known[-1], None)
    else:
        for idx, item in enumerate(Re_known):
            if (idx + 2) == len(Re_known):
                break
            if Re_known[idx] <= Re <= Re_known[idx+1]:
                p11 = (Re_known[idx], None); p12 = (Re_known[idx], None); p21 = (Re_known[idx+1], None); p22 = (Re_known[idx+1], None)
    # min_aoa = min(sorted(dict_fn[p11[0]].keys()), sorted
    if (aoa <= aoa_range[0]):
        aoa_0 = aoa_range[0]; aoa_1 = aoa_range[1]
    elif (aoa > aoa_range[-1]):
        aoa_0 = aoa_range[-2]; aoa_1 = aoa_range[-1]
    else:
        aoa_0 = list(filter(lambda x: x <= aoa, aoa_range))[-1]
        aoa_1 = list(filter(lambda x: x > aoa, aoa_range))[0]
    p11 = (p11[0], aoa_0); p12 = (p12[0], aoa_1); p21 = (p21[0], aoa_0); p22 = (p22[0], aoa_1)
    ######## Get function values ########
    f_p11 = dict_fn[p11[0]][p11[1]]; f_p12 = dict_fn[p12[0]][p12[1]]
    f_p21 = dict_fn[p21[0]][p21[1]]; f_p22 = dict_fn[p22[0]][p22[1]]
    ######## Interpolate along Re #######
    #print (f"Res: {f_p11}, {f_p12} {f_p21} {f_p22}")
    f_Re1 = ((p21[0] - Re) / (p21[0] - p11[0]))*f_p11 + ((Re - p11[0])/(p21[0] - p11[0]))*f_p21
    f_Re2 = ((p21[0] - Re) / (p21[0] - p11[0]))*f_p12 + ((Re - p11[0])/(p21[0] - p11[0]))*f_p22
    #print (f"f_Re1: {f_Re1}, f_Re2: {f_Re2}")
    ######## Interpolate along AOA ######
    f_approx = ((p22[1] - aoa) / (p22[1] - p21[1]))*f_Re1 + ((aoa - p21[1])/(p22[1]-p21[1]))*f_Re2
    # print (f">> coeff({Re}, {aoa}) ~ {f_approx}")
    return f_approx

def dCl_da(cl_data, Re, alpha, h=0.01):
    """ Approximate the derivative of Cl over AOA """
    f = interpolate_2d_linear(dict_fn=cl_data, Re=Re, aoa=alpha)
    f_h = interpolate_2d_linear(dict_fn=cl_data, Re=Re, aoa=alpha+h)
    return (f_h - f) / h

def np_from_xfoil(*, cl_data_wing, cl_data_tail, Re_wing, Re_tail, alpha_wing, alpha_tail, l_H, S, S_H, eps):
    """
    a   - dCl / dalpha for the wing
    a_t - dCl / dalpha for the tail
    l_H - distance between wing's and tails's AC
    S -  wing area
    S_H - tail area
    eps - downwash (as % of the wing's alpha)
    """
    a = dCl_da(cl_data_wing, Re_wing, alpha_wing)
    a_t = dCl_da(cl_data_tail, Re_tail, alpha_tail)
    np = (a_t * (1-eps) * S_H * l_H) / (S * a) # relative to the wing's AC!
    return np
