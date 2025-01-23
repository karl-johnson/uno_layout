import numpy as np
import numpy.random as np_random
from random import random
from math import cos, sin, floor, sqrt, pi, ceil
import scipy.stats
import random
import gdsfactory as gf
from uno_layout import Settings, LayerMapUNO, waveguide_xs
DEFAULT_EDGE_SEP = Settings.DEFAULT_EDGE_SEP # Not used yet
DEFAULT_TEXT_SIZE = Settings.DEFAULT_TEXT_SIZE


DEFAULT_BOSCH_WIDTH = 300e0
DEFAULT_DES_WIDTH = 8000e0
DEFAULT_DICE_WIDTH = 93e0

DEFAULT_ASYM_COUPLER_HALF_STRAIGHT_LENGTH = 10


    
    
    
    

# this is a copy of gdsfactory's coupler_asymmetric but uses 4 ports instead of 3
@gf.cell
def coupler_asymmetric(
    gap: float = 0.234,
    dy: float = 2.5,
    dx: float = 10.0,
    cross_section = waveguide_xs(Settings.DEFAULT_WG_WIDTH),
) -> gf.Component:
    """Bend coupled to straight waveguide.

    Args:
        gap: um.
        dy: port to port vertical spacing.
        dx: bend length in x direction.
        cross_section: spec.

    .. code::

                        dx
                     |-----|
                      _____ o2
                     /         |
             o0_____/          |
         gap o1____________    |  dy
                            o3
    """
    c = gf.Component()
    x = gf.get_cross_section(cross_section)
    width = x.width
    bend = gf.components.bend_s(size=(dx, dy - gap - width), cross_section=cross_section)
    wg = gf.components.straight(cross_section=cross_section, length = DEFAULT_ASYM_COUPLER_HALF_STRAIGHT_LENGTH)

    w = bend.ports[0].dwidth
    y = (w + gap) / 2

    wg = c << wg
    bend = c << bend
    bend.dmirror_y()
    bend.dxmin = 0
    wg.dxmin = 0

    bend.dmovey(-y)
    wg.dmovey(+y)

    # port_width = 2 * w + gap
    # c.add_port(
    #     name="o1",
    #     center=(0, 0),
    #     width=port_width,
    #     orientation=180,
    #     cross_section=x,
    # )
    c.add_port(name="o0", port=bend.ports[0])
    c.add_port(name="o1", port=wg.ports[0])
    c.add_port(name="o2", port=bend.ports[1])
    c.add_port(name="o3", port=wg.ports[1])
    
    c.flatten()
    return c

@gf.cell
def asymmetric_coupler(wgWidth = 0.5, couplingLength = 10.0, 
                           couplerDx =10.0, couplerDy = 10.0, couplerGap = 0.5, busLen = 20.0, crossSection=None):
    c = gf.Component()
    if crossSection == None:
        crossSection = waveguide_xs(wgWidth)
    if callable(crossSection):
        if wgWidth is not None:
            crossSection = crossSection(width=wgWidth)
        else:
            crossSection = crossSection()
    wgWidth = crossSection.width

    if (busLen<couplingLength): couplingLength=couplingLength
    
    s1 = c << gf.components.straight(length=couplingLength, cross_section=crossSection)
    s1.dmovex(-couplingLength/2)
    s2 = c << gf.components.straight(length=busLen, cross_section=crossSection)
    s2.dmovex(-busLen/2)
    s1.dmovey((couplerGap + wgWidth)/2)
    s2.dmovey(-(couplerGap + wgWidth)/2)

    b1 = c << gf.components.bend_s(size=(couplerDx,couplerDy), cross_section=crossSection)
    b2 = c << gf.components.bend_s(size=(couplerDx,couplerDy), cross_section=crossSection)
    b2.mirror_x()
    b1.connect("o1", s1.ports["o2"])
    b2.connect("o1", s1.ports["o1"])
    c.add_port(port=b2.ports['o2'],name="o1")
    c.add_port(port=s2.ports['o1'],name="o2")
    c.add_port(port=b1.ports['o2'],name="o3")
    c.add_port(port=s2.ports['o2'],name="o4")
    c.flatten(False)
    return c


def coupler_asymmetric_full(
    gap: float = 0.25,
    dy: float = 2.5,
    dx: float = 10.0,
    coupling_length: float = 5,
    cross_section = waveguide_xs(Settings.DEFAULT_WG_WIDTH),
) -> gf.Component:
    c = gf.Component()
    """
    Same as coupler_asymmetric but does both sides:
                              dx
                           |------|
             o0 ____         _____ o2
                    \       /         |
                     \_____/          |
         gap o1 __________________ o3 |  dy
                            
    """
    # place half ring couplers
    half_coupler = coupler_asymmetric(gap, dy, dx, cross_section)
    c1 = c << half_coupler
    c2 = c << half_coupler
    c2.dmirror_x()
    # # add coupling length
    c2.dmove(c2.ports['o1'].dcenter, c1.ports['o1'].dcenter)
    c1.dmove((coupling_length, 0))

    # coupling region straight wgs
    s1 = c << gf.components.straight(length = coupling_length, cross_section = cross_section)
    s1.connect('o1', c1.ports['o1'])
    s2 = c << gf.components.straight(length = coupling_length, cross_section = cross_section)
    s2.connect('o1', c1.ports['o0'])
    
    # promote ports
    c.add_port(name = 'o0', port = c1.ports['o2'])
    c.add_port(name = 'o1', port = c1.ports['o3'])
    c.add_port(name = 'o2', port = c2.ports['o2'])
    c.add_port(name = 'o3', port = c2.ports['o3'])
    
    return c

@gf.cell 
def apodized_grating_coupler_rectangular(
        wg_width = 0.5e0, 
        fiber_angle = 12e0, 
        N = 30, 
        F0 = 0.9e0, 
        R = 0.025e0, 
        lambda_c = 1.55e0, # um 
        no = 2.69e0, 
        ne = 1.444e0,
        width_grating = 20e0, 
        length_taper = 300e0,
        polarization = 'te',
        layerSlab= None,
        crossSection = None
        ):
    if crossSection is None:
        crossSection = waveguide_xs
    curr_pos = 0
    widths = []
    gaps = []
    for i in range(N):
        F = F0 - R*curr_pos
        this_neff = F*no + (1-F)*ne  
        this_period = lambda_c / (this_neff - sin(fiber_angle/180*pi)) 
        widths.append(F * this_period)
        gaps.append((1-F) * this_period)
        curr_pos = curr_pos + this_period
    return gf.components.grating_coupler_rectangular_arbitrary(
        gaps = gaps, 
        widths = widths,
        width_grating = width_grating,
        length_taper = length_taper,
        layer_slab = layerSlab,
        cross_section=crossSection,
        polarization = polarization)

@gf.cell 
def apodized_grating_coupler_focused(
        wg_width = 0.5e0, 
        fiber_angle = 12e0, 
        N = 30, 
        F0 = 0.9e0, 
        R = 0.025e0, 
        lambda_c = 1.55e0, # um 
        no = 2.69e0, 
        ne = 1.444e0,
        length_taper = 50e0,
        crossSection = None,
        polarization = 'te',
        layer_grating = None):
    if crossSection is None:
        crossSection = waveguide_xs
    curr_pos = 0
    widths = []
    gaps = []
    for i in range(N):
        F = F0 - R*curr_pos
        this_neff = F*no + (1-F)*ne  
        this_period = lambda_c / (this_neff - sin(fiber_angle/180*pi)) 
        widths.append(F * this_period)
        gaps.append((1-F) * this_period)
        curr_pos = curr_pos + this_period
    
    
    return gf.components.grating_coupler_elliptical_arbitrary(
        gaps = gaps, 
        widths = widths,
        taper_length = length_taper,
        layer_grating = layer_grating,
        cross_section=crossSection,
        layer_slab = False,
        polarization = polarization)



@gf.cell
def mode_filter(wgWidth = Settings.DEFAULT_WG_WIDTH,
                radius = Settings.DEFAULT_RADIUS):
    # series of 4 bends to toss out any weakly-guided modes
    c = gf.Component()
    thisXs = waveguide_xs(wgWidth)
    rightBend = gf.components.bend_euler(radius = radius, angle=90, cross_section = thisXs)
    leftBend = gf.components.bend_euler(radius = radius, angle=-90, cross_section = thisXs)
    symbol_to_component = {
        "r": (rightBend, "o1", "o2"),
        "L": (leftBend, "o1", "o2"),
    }
    sequence = "LrrL"
    c = gf.components.component_sequence(
        sequence=sequence, symbol_to_component=symbol_to_component
    )
    
    return c

@gf.cell
def random_fill_naive(size = (100e0,50e0), # dimensions of region
                postRad = 0.5e0, # radius of posts
                density = 1e-4, # avg # of posts per sq micron
                layer = LayerMapUNO.WG,
                seed = 0):
    # fill a region with random posts to scatter light
    c = gf.Component()
    # seed RNG for deterministic results
    np.random.seed(seed)
    # num posts
    numPosts = round(density*size[0]*size[1]);
    postCoords = np.array(size)*np_random.rand(numPosts, 2)
    postCoords = poisson_disc_samples(size[0], size[1])
    for i in range(numPosts):
        (c << gf.components.circle(radius = postRad, layer = layer)).dmove(postCoords[i])
    c.flatten()
    return c
@gf.cell
def random_fill_poisson(size = (100e0,50e0), # dimensions of region
                postRad = 0.5e0, # radius of posts
                radius = 2.5e0, # attempted distance between posts
                layer = LayerMapUNO.WG,
                seed = 0):
    # fill a region with random posts to scatter light
    c = gf.Component()
    np.random.seed(seed)
    postCoords = poisson_disc_samples(size[0], size[1], radius)
    numPosts = len(postCoords)
    for i in range(numPosts):
        (c << gf.components.circle(radius = postRad, layer = layer)).dmove(postCoords[i])
    c.flatten()
    return c

# bridson algorithm for poisson disk sampling, copied from https://github.com/emulbreh/bridson/blob/master/bridson/__init__.py
def poisson_disc_samples(width, height, r, k=5):
    tau = 2 * np.pi
    cellsize = r / sqrt(2)

    grid_width = int(ceil(width / cellsize))
    grid_height = int(ceil(height / cellsize))
    grid = [None] * (grid_width * grid_height)

    def euclidean_distance(a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return sqrt(dx * dx + dy * dy)

    def grid_coords(p):
        return int(floor(p[0] / cellsize)), int(floor(p[1] / cellsize))

    def fits(p, gx, gy):
        yrange = list(range(max(gy - 2, 0), min(gy + 3, grid_height)))
        for x in range(max(gx - 2, 0), min(gx + 3, grid_width)):
            for y in yrange:
                g = grid[x + y * grid_width]
                if g is None:
                    continue
                if euclidean_distance(p, g) <= r:
                    return False
        return True

    random_func = np_random.rand
    p = width * random_func(), height * random_func()
    queue = [p]
    grid_x, grid_y = grid_coords(p)
    grid[grid_x + grid_y * grid_width] = p

    while queue:
        qi = int(random_func() * len(queue))
        qx, qy = queue[qi]
        queue[qi] = queue[-1]
        queue.pop()
        for _ in range(k):
            alpha = tau * random_func()
            d = r * sqrt(3 * random_func() + 1)
            px = qx + d * cos(alpha)
            py = qy + d * sin(alpha)
            if not (0 <= px < width and 0 <= py < height):
                continue
            p = (px, py)
            grid_x, grid_y = grid_coords(p)
            if not fits(p, grid_x, grid_y):
                continue
            queue.append(p)
            grid[grid_x + grid_y * grid_width] = p
    return [p for p in grid if p is not None]


@gf.cell
def die_and_floorplan(dieWidth = 10000e0, desWidth = DEFAULT_DES_WIDTH):
    c = gf.Component()
    # die
    c << gf.components.rectangle(
        size = [dieWidth, dieWidth], centered = True,
        layer = LayerMapUNO.DIE)
    # design region
    c << gf.components.rectangle(
        size = [desWidth, desWidth], centered = True,
        layer = LayerMapUNO.FLOORPLAN)
    return c

@gf.cell
def ant_4x4_template():
    desWidth = 8780e0
    deepTrenchWidth = 260e0
    # place design area and dicing/deep trench for Si ANT MPW rules
    c = gf.Component()
    # design region
    c << gf.components.rectangle(
        size = [desWidth, desWidth], centered = True,
        layer = LayerMapUNO.FLOORPLAN)
    # deep trench
    c << gf.components.rectangle(
        size = (desWidth,deepTrenchWidth), 
        layer = LayerMapUNO.ANT_EDGE_TRENCH, 
        centered = True)
    c << gf.components.rectangle(
        size = (deepTrenchWidth,desWidth), 
        layer = LayerMapUNO.ANT_EDGE_TRENCH, 
        centered = True)
    return c

@gf.cell
def ant_trench_perimeter():
    innerWidth = 8780e0
    outerWidth = 9300e0
    c = gf.Component()
    for angle in [0, 90, 180, 270]:
        (c << gf.components.bbox(
            left = -outerWidth/2, bottom = innerWidth/2, top = outerWidth/2, right = outerWidth/2,
            layer = LayerMapUNO.ANT_EDGE_TRENCH)).drotate(angle)
    return c

@gf.cell
def mla_cross(layer, 
              thick = 20e0, 
              length = 200e0, 
              dot = False, 
              dotRad = 10e0, 
              dotDx = 50e0, 
              dotDy = 50e0):
    
    # alignment cross includes dot to indicate which corner this is
    c = gf.Component()
    
    c << gf.components.cross(thick, length, layer = layer)
    if(dot):
        circ = c << gf.components.circle(radius = dotRad, layer = layer)
        circ.dmove((-dotDx, -dotDy))
    return c

@gf.cell
def mla_crosses(dx = 4000e0, 
                dy = 4000e0, 
                thisLayer = LayerMapUNO.LABEL,
                includeArrow = True):
    c = gf.Component()
    cross = mla_cross(layer = thisLayer)
    for cIdx in range(4):
        thisC = c << cross
        thisC.dmove((dx,dy))
        if(cIdx == 1 or cIdx == 3):
            thisC.mirror((0,1))
        if(cIdx == 2 or cIdx == 3):
            thisC.mirror((1,0))
    # big "this way up" arrows
    if(includeArrow):
        a = c << arrow(height = 100)
        a.dmove((dx/2, dy))
        a = c << arrow(height = 100)
        a.dmove((-dx/2, dy))
    return c

@gf.cell
def arrow(height = 25e0, layer = LayerMapUNO.LABEL):
    c = gf.Component()
    arrowPolygon = height*np.array([[-0.2,-1], [0.2, -1], [0.2,0.6], [0.4,0.6], [0,1], [-0.4, 0.6], [-0.2, 0.6], [-0.2,0]])
    c.add_polygon(arrowPolygon, layer = layer)
    return c

@gf.cell
def bosch_for_quadrants(boschWidth = DEFAULT_BOSCH_WIDTH, 
                      desWidth = DEFAULT_DES_WIDTH):
    # marks on wg layer
    c = gf.Component()
    # Bosch deep trench zones
    c << gf.components.rectangle(
        size = (boschWidth, desWidth), centered=True,
        layer = LayerMapUNO.BOSCH)
    c << gf.components.rectangle(
        size = (desWidth, boschWidth), centered=True, # alternative to rotate(90)
        layer = LayerMapUNO.BOSCH)
    return c

@gf.cell
def dicing_lanes(lanesX, # x coordinates of vertical dicing (list)
                 lanesY, # y coordinates of horizontal dicing (list)
                 bladeWidth = DEFAULT_DICE_WIDTH, # width of dicing blade
                 tickSeparation = DEFAULT_DES_WIDTH + 500e0, # location of dicing marks
                 tickLayer = LayerMapUNO.LABEL,
                 doBosch = True,
                 doCrosses = True,
                 boschWidth = DEFAULT_BOSCH_WIDTH,
                 boschLength = DEFAULT_DES_WIDTH,
                 boschLayer = LayerMapUNO.BOSCH):
    
    c = gf.Component()
    
    # dicing ticks
    # for thisX in lanesX:
    #     thisT = c << dicing_end_ticks(separation = tickSeparation, laneWidth = DEFAULT_DICE_WIDTH)
    #     thisT.rotate(90)
    #     thisT.move((thisX, 0))
    # for thisY in lanesY:
    #     thisT = c << dicing_end_ticks(separation = tickSeparation, laneWidth = DEFAULT_DICE_WIDTH)
    #     thisT.move((0, thisY))
        
    # crosses
    if(doCrosses):
        crossForDicing = mla_cross(layer= tickLayer, dot = False)
        for thisX in lanesX:
            thisT = c << crossForDicing 
            thisT.dmove((thisX, tickSeparation/2))
            thisT = c << crossForDicing 
            thisT.dmove((thisX, -tickSeparation/2))
        for thisY in lanesY:
            thisT = c << crossForDicing 
            thisT.dmove((tickSeparation/2, thisY))
            thisT = c << crossForDicing 
            thisT.dmove((-tickSeparation/2, thisY))
    
    if(doBosch):
        for thisX in lanesX:
            thisR = c << gf.components.rectangle(
                size = (boschWidth, boschLength), centered=True,
                layer = boschLayer)
            
            thisR.dmove((thisX, 0))
        for thisY in lanesY:
            thisR = c << gf.components.rectangle(
                size = (boschLength, boschWidth), centered=True,
                layer = boschLayer)
            thisR.dmove((0, thisY))
    return c

@gf.cell 
def dicing_end_ticks(separation, laneWidth = DEFAULT_DICE_WIDTH, layer = LayerMapUNO.LABEL):
    c = gf.Component()
    t1 = c << dicing_tick_single(layer = layer).drotate(90)
    t1.dmove((separation/2, laneWidth/2))
    t2 = c << dicing_tick_single(layer = layer).drotate(180)
    t2.dmove((separation/2, -laneWidth/2))
    t1 = c << dicing_tick_single(layer = layer).drotate(0)
    t1.dmove((-separation/2, laneWidth/2))
    t2 = c << dicing_tick_single(layer = layer).drotate(270)
    t2.dmove((-separation/2, -laneWidth/2))
    return c

@gf.cell 
def dicing_tick_single(w1 = 75e0, w2 = 75e0, bevel = 5e0, layer = LayerMapUNO.LABEL, position = (0,0)):
    c = gf.Component()
    # this will raise an error unless you force one element to be float with
    # a decimal etc.
    tickPolygon = np.array([[0.0,0], [w1, 0], [w1, bevel], [bevel, w2], [0, w2]])
    tickPolygon += np.array(position)
    c.add_polygon(tickPolygon, layer = layer)
    return c

@gf.cell
def straight_waveguide(dxdy = Settings.DEFAULT_DXDY,
                       wgWidth = None, 
                       labelIn = None, 
                       labelOut = None,
                       tipWidth = None,
                       boschWidth = DEFAULT_BOSCH_WIDTH):
    # straight waveguide from in->out at specified dx/dy
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    ed = c << edge_coupler_pair(dxdy, wgWidth, labelIn, labelOut,
                                tipWidth = tipWidth,
                                boschWidth = boschWidth)
    
    gf.routing.route_single(c, ed.ports["o1"], ed.ports["o2"],cross_section=crossSection)
    return c

@gf.cell
def fib_structures(thisWgWidth, thisGap, length = 100e0):
    c = gf.Component()
    # waveguides of various widths for FIB milling + cross section imaging
    (c << gf.components.rectangle(
        layer = LayerMapUNO.WG, 
        size = (length,thisWgWidth),
        centered = True))
    (c << gf.components.rectangle(
        layer = LayerMapUNO.WG, 
        size = (length,1),
        centered = True)).dmove((0,50e0))
    # also do same geometry as coupling region in ring
    (c << gf.components.coupler_straight(
        gap = thisGap,
        length = length,
        cross_section = waveguide_xs(thisWgWidth))).dmove((-length/2,100e0))
    # label
    # c << gf.components.text('FIB', size = 40, layer = LayerMapUNO.LABEL, position = (225, 25))
    return c

# array of edge couplers for fiber arrays
@gf.cell
def edge_coupler_array(couplerComponent = None, 
                       n = 16,
                       dx = 127e0,
                       couplerRotation = 90):
    c = gf.Component()
    couplerComponent = edge_coupler() if couplerComponent is None else couplerComponent
    for i in range(n):
        thisC = (c << couplerComponent).drotate(couplerRotation)
        thisC.dmovex(dx*i)
        c.add_port(f"o{i}", port = thisC.ports['o2'])
    return c


@gf.cell
def edge_coupler_pair(dxdy = Settings.DEFAULT_DXDY,
                      wgWidth = None, 
                      labelIn = None, 
                      labelOut = None, 
                      tipWidth = None,
                      boschWidth = DEFAULT_BOSCH_WIDTH):
    dx = dxdy[0]
    dy = dxdy[1]
    c = gf.Component()
    e1 = c << edge_coupler(tipWidth, wgWidth, straightLength = boschWidth/2)
    e1.dmove(e1.ports["o1"].dcenter, (0, dy))
    e2 = c << edge_coupler(tipWidth, wgWidth, straightLength = boschWidth/2)
    e2.drotate(90)
    e2.dmove(e2.ports["o1"].dcenter, (dx, 0))
    c.add_port("o1", port = e1.ports["o2"], orientation = 0)
    c.add_port("o2", port = e2.ports["o2"], orientation = 90)
    if labelIn is not None:
        c << gf.components.text(text = labelIn, size = Settings.DEFAULT_TEXT_SIZE, 
                                position = (boschWidth, dy + 15e0),
                                layer = LayerMapUNO.LABEL)
    if labelOut is not None:
        ot = c << gf.components.text(text = labelOut, size = Settings.DEFAULT_TEXT_SIZE,
                                layer = LayerMapUNO.LABEL,
                                justify = "right")
        ot.drotate(-90)
        ot.dmove((dx + 15e0, boschWidth))

    return c

@gf.cell
def edge_coupler_tri(dxdy = Settings.DEFAULT_DXDY,
                      wgWidth = None, 
                     edgeSep = None, 
                     labelIn = None, 
                     labelOut = None, 
                     tipWidth = None,
                     boschWidth = None,
                     textPosition = None):
    # labelOut must be a tuple!
    dx = dxdy[0]
    dy = dxdy[1]
    c = gf.Component()
    thisEdgeCoupler = edge_coupler(tipWidth, wgWidth, straightLength=boschWidth)
    e1 = c << thisEdgeCoupler
    e1.dmove(e1.ports["o1"].dcenter, (0, dy))
    e2 = c << thisEdgeCoupler
    e2.drotate(90)
    e0 = c << thisEdgeCoupler
    e0.drotate(90)
    
    e2.dmove(e2.ports["o1"].dcenter, (dx, 0))
    e0.dmove(e0.ports["o1"].dcenter, (dx + edgeSep, 0))
    
    c.add_port("o1", port = e1.ports["o2"], orientation = 0)
    c.add_port("o2", port = e2.ports["o2"], orientation = 90)
    c.add_port("o3", port = e0.ports["o2"], orientation = 90)
    if textPosition is None:
        textPosition = (300e0,15e0)
    textPositionNp = np.array(textPosition)
    if labelIn is not None:
        c << gf.components.text(text = labelIn, size = 40e0, 
                                position = np.array((0,dy)) + textPositionNp,
                                layer = LayerMapUNO.LABEL)
    if labelOut is not None:
        ot = c << gf.components.text(text = labelOut[0], size = 40e0,
                                layer = LayerMapUNO.LABEL,
                                justify = "right")
        ot.drotate(-90)
        ot.dmove(np.array((dx,0)) + np.flip(textPositionNp))
        
        ot = c << gf.components.text(text = labelOut[1], size = 40e0,
                                layer = LayerMapUNO.LABEL,
                                justify = "right")
        ot.drotate(-90)
        ot.dmove(np.array((dx + edgeSep,0)) + np.flip(textPositionNp))
    return c

@gf.cell
def normal_mmi_with_sbend(wgWidth = 0.5e0):
    # TODO figure out why no width mismatch errors on this + mode filter
    # decent broadband TE/TM coupler, with s bend escapes so waveguides
    # aren't super close AND SUPER ANNOYING TO ROUTE UGGGGH
    c = gf.Component()
    xs = waveguide_xs(wgWidth)
    mmiSplitter = c << gf.components.mmi1x2(width = wgWidth,
                                            width_taper = 1e0,
                                            length_taper = 15e0,
                                            length_mmi = 5.5e0,
                                            width_mmi = 2.5e0,
                                            gap_mmi = 0.25e0)
    s1 = c << gf.components.bend_s((30e0,10e0), cross_section = xs)
    s1.connect('o1', mmiSplitter.ports['o2'])
    s2 = c << gf.components.bend_s((30e0,-10e0), cross_section = xs)
    s2.connect('o1', mmiSplitter.ports['o3'])
    
    c.add_port('o1', port = mmiSplitter.ports['o1'])
    c.add_port('o2', port = s1.ports['o2'])
    c.add_port('o3', port = s2.ports['o2'])
    return c

@gf.cell
def edge_coupler(tipWidth = None, # tip width
                 wgWidth = None,
                 taperLength = None,
                 straightLength = None):
    # TODO make it easier to globally set edge coupler tip width!
    # straight section at tip width while under dicing blade, then taper
    wgWidth = Settings.DEFAULT_WG_WIDTH if wgWidth is None else wgWidth
    tipWidth = 0.11e0 if tipWidth is None else tipWidth
    taperLength = 50e0 if taperLength is None else taperLength
    straightLength = DEFAULT_BOSCH_WIDTH/2 if straightLength is None else straightLength
    
    c = gf.Component()
    straightPath = gf.path.straight(length = straightLength)
    #aperPath = gf.path.straight(length = taperLength)
    p1 = c << gf.path.extrude(straightPath, layer = LayerMapUNO.WG, width = tipWidth)
    p2 = c << gf.components.taper(length = taperLength, width1 = tipWidth, width2 = wgWidth, layer= LayerMapUNO.WG)
    p2.connect('o1', p1.ports['o2'])
    c.add_port('o1', port = p1.ports['o1'])
    c.add_port('o2', port = p2.ports['o2'])
    return c


@gf.cell
def y_splitter_adiabatic(w1 = Settings.DEFAULT_WG_WIDTH, g1 = 0.15e0, t1 = 0.15e0, 
                         w2 = Settings.DEFAULT_WG_WIDTH, g2 = 0.15e0, t2 = 0.15e0, 
                         length = 30e0, escape = 25e0, outSep = 5e0, thisLayer = (1,0)):
    # do taper region with gdsfactory trickery
    # first CrossSection
    startOffset = w1/2 + g1 + t1/2
    s10 = gf.Section(width=w1, offset=0, layer=thisLayer, name = "center")
    s11 = gf.Section(width=t1, offset=startOffset, layer=thisLayer, name = "top")
    s12 = gf.Section(width=t1, offset=-startOffset, layer=thisLayer, name = "bot")
    X1 = gf.CrossSection(sections=[s10, s11, s12])
    # second CrossSection that we want to transition to
    endOffset = w2/2 + g2 + t2/2
    s20 = gf.Section(width=t2, offset=0, layer=thisLayer, name = "center")
    s21 = gf.Section(width=w2, offset=endOffset, layer=thisLayer, name = "top")
    s22 = gf.Section(width=w2, offset=-endOffset, layer=thisLayer, name = "bot")
    X2 = gf.CrossSection(sections=[s20, s21, s22])
    
    c = gf.Component()
    c << gf.components.taper_cross_section(length = length,
                                              cross_section1 = X1,
                                              cross_section2 = X2,
                                              linear=True)
    # cross section for escapes
    X3 = gf.CrossSection(sections=[gf.Section(width=w2, offset=0, layer=thisLayer)])
    e1 = c << gf.components.bend_s(size = [escape, outSep/2 - endOffset], cross_section=X3)
    # we could try to fuss with ports but not worth it
    e1.dmove((length, endOffset))
    e2 = c << gf.components.bend_s(size = [escape, -(outSep/2 - endOffset)], cross_section=X3)
    # we could try to fuss with ports but not worth it
    e2.dmove((length, -endOffset))
    # put one at the front for good measure
    X4 = gf.CrossSection(sections=[gf.Section(width=w1, offset=0, layer=thisLayer)])
    s = c << gf.components.straight(length = escape, cross_section = X4)
    s.dmove((-escape, 0))
    
    # Ports
    c.add_port('o1', center = (-escape, 0), orientation=180, cross_section=X4)
    c.add_port('o2', center = (length+escape, outSep/2), orientation= 0, cross_section=X3)
    c.add_port('o3', center = (length+escape, -outSep/2), orientation= 0, cross_section=X3)
    return c
    
@gf.cell 
def timestamp(position = (0,0),
              quadrantLabel = "QUAD_NAME",
              designerLogo = None,
              designerLogoGdsHeight = 64e0):
    c = gf.Component()
    timestampTextSize = 50e0
    timeStamp = c << gf.components.version_stamp(labels = [quadrantLabel], 
                                     with_qr_code=False, 
                                     layer=LayerMapUNO.LABEL, 
                                     pixel_size=1, text_size=timestampTextSize)
    timeStamp.dmove((0,0),position)
    if designerLogo is not None:
        logo = c << designer_logo(height = 75e0, file = designerLogo, gdsHeight = designerLogoGdsHeight)
        logo.dmove((logo.dxmax,logo.dymin), (timeStamp.dxmax, timeStamp.dymin))
    return c


@gf.cell 
def designer_logo(height = 75e0, # height when placed in layout
                  file = None, # file containing logo, assumed square
                  gdsHeight = 64e0): # logo height in original file
    # unique logo for designer to put alongside timestamp
    if file is None:
        raise Exception("No designer logo file supplied")
    polygons = gf.read.import_gds(file).get_polygons()
    scaledPoly = [height/gdsHeight*polygon for polygon in polygons]
    c = gf.Component()
    for thisPoly in scaledPoly:
        
        thisPoly
        c.add_polygon(thisPoly, layer = LayerMapUNO.LABEL)
    return c