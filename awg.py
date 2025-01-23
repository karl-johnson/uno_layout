# functions useful for generating arrayed waveguide gratings


import gdsfactory as gf
from uno_layout import Settings, LayerMapUNO, waveguide_xs
import uno_layout.components_wg as uno_wg
import numpy as np
import math
import uno_layout.tools as uno_tools
LAYERS = LayerMapUNO
DEFAULT_WG_WIDTH = Settings.DEFAULT_WG_WIDTH
DEFAULT_RADIUS = Settings.DEFAULT_RADIUS
DEFAULT_EDGE_SEP = Settings.DEFAULT_EDGE_SEP
DEFAULT_TEXT_SIZE = Settings.DEFAULT_TEXT_SIZE
DEFAULT_DXDY = Settings.DEFAULT_DXDY


@gf.cell()
def rowland_fsp(r_a:float = 50, y_span:float = 25, 
                n_io = 1, d_io = 2, # 'r' subscripts in paper
                n_array = 9, d_array = 2, # 'a' subscripts in paper
                input_wg_length = 20, output_wg_length = 50, # length of waveguides coming out of this component
                #desired_port_sep = 5, # instead of doing input and output lengths, 
                xs = waveguide_xs(), n_curve = 64,
                ports_inside_arc: float = 0.05 # offset port placements to ensure waveguide overlap with slab
                ):
    # free space propagation region following Rowland circle
    # this part does the slab waveguide and also short waveguides that bend to manhattan ports
    # https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=577370 Fig. 1
    # on the array side, the radius of curvature is Ra
    # on the image side, the radius of curvature is Ra/2
    c = gf.Component()
    # y span is meaningless if it's greater than r_a
    if y_span > r_a:
        y_span = r_a
        print("Warning: rowland y_span > r_a, changing to r_a")
        
    # create two curves and then just connect together
    # n is the number of points per curve
    # r_a/2 radius curve is input side, we put on the left
    
    # offset parameter here is for when we offset ports later
    io_curve = lambda angle, offset : ((r_a/2 - (r_a/2 + offset)*math.cos(angle)), (r_a/2 + offset) * math.sin(angle))
    array_curve = lambda angle, offset : ((r_a + offset) * math.cos(angle), (r_a + offset) * math.sin(angle))
    
    
    input_angle_span = math.asin(y_span/r_a)
    input_angles = np.linspace(input_angle_span, -input_angle_span, n_curve)
    input_arc = [io_curve(i, 0) for i in input_angles]

    output_angle_span = math.asin(0.5*y_span/r_a)
    output_angles = np.linspace(-output_angle_span, output_angle_span, n_curve)
    output_arc = [array_curve(i, 0) for i in output_angles]

    full_shape = input_arc + output_arc;

    c.add_polygon(full_shape, layer = LAYERS.WG)
    
    # now doing circular bends to manhattan ports
    
    input_port_angles = [2*d_io/r_a * (i - 0.5*(n_io-1)) for i in range(n_io)]
    
    # pre-calculated required bend length
    # TODO: handle case that xs is callable and not the xs itself
    input_bend_length = max(input_port_angles)*xs.radius
    for input_angle in enumerate(input_port_angles):
        # first, insert straight waveguide
        # this_wg = c << gf.components.straight(length = input_wg_length + ports_inside_arc, cross_section=xs)
        # this_wg.drotate(-math.degrees(input_angle[1])+180).dmove(io_curve(input_angle[1], -ports_inside_arc))
        # # now add a lil bend to make it straight, all bends are same length
        # if(input_angle[1] == 0):
        #     this_bend = c << gf.components.straight(length = input_bend_length, cross_section=xs)
        # else:
        #     this_radius = abs(input_bend_length/input_angle[1])
        #     this_bend = c << gf.components.bend_circular(radius = this_radius, angle = math.degrees(input_angle[1]), cross_section = xs)
        # this_bend.connect('o1', this_wg.ports['o2'])
        c.add_port(f'i{input_angle[0]}', 
                   center = io_curve(input_angle[1], -ports_inside_arc),
                   orientation = -math.degrees(input_angle[1])+180,
                   cross_section=xs)
        
    output_port_angles = [d_array/r_a * (i - 0.5*(n_array-1)) for i in range(n_array)]
    output_bend_length = max(output_port_angles)*xs.radius
    for output_angle in enumerate(output_port_angles):
        # first, insert straight waveguide
        # this_wg = c << gf.components.straight(length = output_wg_length + ports_inside_arc, cross_section=xs)
        # this_wg.drotate(math.degrees(output_angle[1])).dmove(array_curve(output_angle[1], -ports_inside_arc))
        # # now add a lil bend to make it straight, all bends are same length
        # if(output_angle[1] == 0):
        #     this_bend = c << gf.components.straight(length = output_bend_length, cross_section=xs)
        # else:
        #     this_radius = abs(output_bend_length/output_angle[1])
        #     this_bend = c << gf.components.bend_circular(radius = this_radius, angle = -math.degrees(output_angle[1]), cross_section = xs)
        # this_bend.connect('o1', this_wg.ports['o2'])
        c.add_port(f'o{output_angle[0]}',
                   center = array_curve(output_angle[1], -ports_inside_arc),
                   orientation = math.degrees(output_angle[1]),
                   cross_section=xs)
        
    c.flatten()
    return c    

@gf.cell(check_instances=False)
def awg(fsp, # this must be callable, for now all parameters identical for 1st and 2nd
        n_i = 1, # num inputs
        n_a = 8, # num array waveguides
        n_o = 8, # num outputs
        delta_L = 10, # length difference between arms
        fsp_spacing = 100, 
        fsp_angle = -10, # 0 means parallel, <0 means facing each other
        start_length = 200,
        min_waveguide_spacing = 5,
        xs = waveguide_xs(),
        debug_print = True):
    c = gf.Component()
    
    f1 = c << fsp(n_io = n_i, n_array = n_a)
    f1.drotate(fsp_angle)
    f2 = c << fsp(n_io = n_o, n_array = n_a)
    f2.drotate(fsp_angle).dmirror_y().dmovey(-fsp_spacing)
    
    L_desired = start_length
    for wg_idx in range(n_a):
        this_port_1 = f1.ports[f'o{wg_idx}']
        this_port_2 = f2.ports[f'o{wg_idx}']
        d = np.linalg.norm(np.array(this_port_1.dcenter)-np.array(this_port_2.dcenter))
        # assumes symmetry!!!
        if(this_port_1.orientation < 180):
            phi_deg = 90 + this_port_1.orientation
        else:
            phi_deg = this_port_1.orientation - 270
        #if phi_deg < +180: phi_deg -= 180 #  TODO probably more edge cases here...
        

        this_wg = c << fancy_awg_bend(d, phi_deg, L_desired, xs = waveguide_xs(), wg_idx = wg_idx)
        this_wg.connect('o1', this_port_1)
        
        L_desired += delta_L
        
    
    # get path length difference using combination of port-to-port spacing and extension of loops
    
    # last_y_spacing = 0
    # last_x_offset = xs.radius
    # for wg_idx in range(n_a):
    #     this_port_1 = f1.ports[f'o{wg_idx}']
    #     this_port_2 = f2.ports[f'o{wg_idx}']
        
    #     if(wg_idx == 0):
    #         this_x_offset = last_x_offset
    #     else:
    #         this_y_spacing = abs(this_port_1.dcenter[1] - this_port_2.dcenter[1])
    #         # delta length between arms is
    #         # delta_L = (this_y_spacing - last_y_spacing) + 2*this_x_offset
    #         # therefore:
    #         this_x_delta = 0.5*(delta_L - (this_y_spacing - last_y_spacing))
    #         if(this_x_delta < min_waveguide_spacing):
    #             raise Exception("AWG delta_L (f{delta_L}) incompatible with fsp region waveguide spacing and min_waveguide_spacing")
    #         this_x_offset = last_x_offset + this_x_delta
        
        # ROUTE SINGLE
        #gf.routing.route_single_from_steps(c, this_port_1, this_port_2, steps = [{'dx': this_x_offset}])
        
        # last_x_offset = this_x_offset
        # last_y_spacing = this_y_spacing
        
        #gf.routing.route_single(c, , , cross_section = xs)
    
    # if fsp_out is None:
    #     if fsp_in is None:
    #         fsp_out = rowland_fsp()
    #     else:
    #         fsp_out = fsp_in
    # fsp_in = rowland_fsp() if fsp_in is None else fsp_in
    
    
    # f1 = c << fsp_in
    # f2 = (c << fsp_out).dmovey(0,100)
    
    # for this_port in f1.ports:
    #     w = c << gf.components.straight(cross_section = xs)
    #     w.connect('o1', this_port)
    # c.flatten()
    
    
    return c

@gf.cell
def fancy_awg_bend(d, phi_deg, L_desired, xs = waveguide_xs(), wg_idx = None):
    # figure out routing between angled ports of two AWG couplers using just one arc and two straight lines
    # the waveguide direction of both couplers must form an angle of phi with
    #   respect to the line connecting the two ports, which has length d
    
    # TODO optimize using euler bends
    phi = math.radians(phi_deg)
    # the math here is quite a fun geometry problem!!!
    # compute straight length
    s = 0.5* (phi*d/math.sin(phi) - L_desired) / (phi/math.tan(phi) - 1)
    if s < 0:
        raise Exception(f"AWG waveguide {wg_idx}: AWG routing requires straight length < 0, meaning the required length is too short for the distance needing to be routed. Try a configuration that increases the desired length (starting length ^) or reduces the required distance to be routed.")
    radius = (d - 2*s*math.cos(phi))/(2*math.sin(phi))
    if radius < xs.radius:
        print(f"Warning! AWG waveguide {wg_idx}: AWG routing requires bend radius ({radius}) < min bend radius ({xs.radius}), meaning the desired length is too long. Try a configuration that decreases the desired length.")
        
    # generate path all at once and avoid non-manhattan connection nightmare
    p = (gf.path.straight(s) 
        + gf.path.arc(radius = radius, angle = -2*phi_deg)
        + gf.path.straight(s))
    print(p.length())
    return gf.path.extrude(p, xs)
    
    
    