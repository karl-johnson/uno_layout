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


@gf.cell(check_instances=False)
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
        this_wg = c << gf.components.straight(length = input_wg_length + ports_inside_arc, cross_section=xs)
        this_wg.drotate(-math.degrees(input_angle[1])+180).dmove(io_curve(input_angle[1], -ports_inside_arc))
        # now add a lil bend to make it straight, all bends are same length
        if(input_angle[1] == 0):
            this_bend = c << gf.components.straight(length = input_bend_length, cross_section=xs)
        else:
            this_radius = abs(input_bend_length/input_angle[1])
            this_bend = c << gf.components.bend_circular(radius = this_radius, angle = math.degrees(input_angle[1]), cross_section = xs)
        this_bend.connect('o1', this_wg.ports['o2'])
        c.add_port(f'i{input_angle[0]}', port = this_bend.ports['o2'])
        
    output_port_angles = [d_array/r_a * (i - 0.5*(n_array-1)) for i in range(n_array)]
    output_bend_length = max(output_port_angles)*xs.radius
    for output_angle in enumerate(output_port_angles):
        # first, insert straight waveguide
        this_wg = c << gf.components.straight(length = output_wg_length + ports_inside_arc, cross_section=xs)
        this_wg.drotate(math.degrees(output_angle[1])).dmove(array_curve(output_angle[1], -ports_inside_arc))
        # now add a lil bend to make it straight, all bends are same length
        if(output_angle[1] == 0):
            this_bend = c << gf.components.straight(length = output_bend_length, cross_section=xs)
        else:
            this_radius = abs(output_bend_length/output_angle[1])
            this_bend = c << gf.components.bend_circular(radius = this_radius, angle = -math.degrees(output_angle[1]), cross_section = xs)
        this_bend.connect('o1', this_wg.ports['o2'])
        c.add_port(f'o{output_angle[0]}', port = this_bend.ports['o2'])

    return c    

@gf.cell(check_instances=False)
def awg(fsp, # this must be callable, for now all parameters identical for 1st and 2nd
        n_i = 1, # num inputs
        n_a = 8, # num array waveguides
        n_o = 8, # num outputs
        delta_L = 10, # length difference between arms
        fsp_spacing = 100,
        min_waveguide_spacing = 5,
        xs = waveguide_xs()):
    c = gf.Component()
    
    f1 = c << fsp(n_io = n_i, n_array = n_a)
    f2 = c << fsp(n_io = n_o, n_array = n_a)
    f2.dmovey(-fsp_spacing)
    
    # get path length difference using combination of port-to-port spacing and extension of loops
    # need to performa a check that the desired delta_L can actually be achieved
    
    
    gf.route.route_single()
    
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

