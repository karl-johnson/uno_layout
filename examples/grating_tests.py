import gdsfactory as gf
import uno_layout.components_wg as uno_wg
import uno_layout.tools as uno_tools
import uno_layout.common_wg_devices as uno_wgd
#from uno_layout import waveguide_xs, LAYERS
import numpy as np
from functools import partial
from uno_layout.tools import dp2tuple

from uno_layout import Settings, LayerMapUNO, waveguide_xs
LAYERS = LayerMapUNO
DEFAULT_WG_WIDTH = Settings.DEFAULT_WG_WIDTH
DEFAULT_RADIUS = Settings.DEFAULT_RADIUS
DEFAULT_EDGE_SEP = Settings.DEFAULT_EDGE_SEP
DEFAULT_TEXT_SIZE = Settings.DEFAULT_TEXT_SIZE
DEFAULT_DXDY = Settings.DEFAULT_DXDY



dieWidth = 12000e0
desWidth = 8000e0
logoFile = "uno_layout/examples/kj.gds"
globalWgWidth = 0.50e0

@gf.cell
def full_chip():
    c = gf.Component()
    c << uno_wg.die_and_floorplan(dieWidth = dieWidth, desWidth = desWidth)
    ringLength = 500e0
    structure_spacing = 700e0
    middle_spacing = 1200e0
    # TE arrays
    TEringPartial = partial(sixteen_grating_3_rings,
                            thisWgWidth=globalWgWidth,
                            couplerGaps = [0.3e0, 0.3e0, 0.2e0],
                            couplerLengths = [2e0, 7e0, 2.5e0],
                            ringLengths = [ringLength, ringLength, ringLength])
    # TE1 = (c << TEringPartial(ant_grating_TE_air(globalWgWidth))).rotate(180)
    # TE1.move(TE1.center, (0, middle_spacing/2))

    our_grating_TE = uno_wg.apodized_grating_coupler_rectangular(
            wg_width = globalWgWidth, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.85, 
            R = 0.025, 
            lambda_c = 1.55, # um 
            no = 2.69, 
            ne = 1.444,
            width_grating = 20, 
            length_taper = 300)
    TE2 = (c << TEringPartial(our_grating_TE)).drotate(180)
    TE2.dmove(dp2tuple(TE2.dcenter), (0, middle_spacing/2 + structure_spacing))
    
    our_grating_TE_air = uno_wg.apodized_grating_coupler_rectangular(
            wg_width = globalWgWidth, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.85, 
            R = 0.025, 
            lambda_c = 1.55, # um 
            no = 2.65, 
            ne = 1.222,
            width_grating = 20, 
            length_taper = 300)
    TE0 = (c << TEringPartial(our_grating_TE_air)).drotate(180)
    TE0.dmove(dp2tuple(TE0.dcenter), (0, middle_spacing/2 + 2*structure_spacing))
    
    # TM arrays
    TMringPartial = partial(sixteen_grating_3_rings,
                            thisWgWidth=globalWgWidth,
                            couplerGaps = [0.7, 0.65, 0.6],
                            couplerLengths = [0.1, 2, 3.5],
                            ringLengths = [ringLength, ringLength, ringLength])
    # TM1 = (c << TMringPartial(ant_grating_TM_air(globalWgWidth))).rotate(180)
    # TM1.move(TM1.center, (0, -middle_spacing/2))
    
    our_grating_TM = uno_wg.apodized_grating_coupler_rectangular(
            wg_width = globalWgWidth, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.9, 
            R = 0.025, 
            lambda_c = 1.55, # um 
            no = 1.95, 
            ne = 1.444,
            width_grating = 20, 
            length_taper = 300)

    TM2 = (c << TMringPartial(our_grating_TM)).drotate(180)
    TM2.dmove(dp2tuple(TM2.dcenter), (0, -middle_spacing/2 - structure_spacing))
    
    our_grating_TM_air = uno_wg.apodized_grating_coupler_rectangular(
            wg_width = globalWgWidth, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.9, 
            R = 0.015, 
            lambda_c = 1.55, # um 
            no = 1.74, 
            ne = 1.444,
            width_grating = 20, 
            length_taper = 300)

    TM3 = (c << TMringPartial(our_grating_TM_air)).drotate(180)
    TM3.dmove(dp2tuple(TM3.dcenter), (0, -middle_spacing/2 - 2*structure_spacing))
    
    ts = c << uno_wg.timestamp(designerLogo = None, #logoFile,
                          quadrantLabel = "F")
    ts.dmove(dp2tuple(ts.dcenter), (-400,150))
    # labels
    y1 = 325
    c << gf.components.text("TE", position = (-2000, y1), size = 50, layer = LAYERS.LABEL)
    c << gf.components.text("TM", position = (-2000, -300), size = 50, layer = LAYERS.LABEL)
    c << gf.components.text("20", position = (-1300, y1), size = 50, layer = LAYERS.LABEL)
    c << gf.components.text("10", position = (-40, y1), size = 50, layer = LAYERS.LABEL)
    c << gf.components.text("3", position = (1235, y1), size = 50, layer = LAYERS.LABEL)

    # waveguides and cleave markers for FIB
    (c << uno_wg.fib_structures(globalWgWidth, 0.2, length = 600)).drotate(-90).dmove((-50,0))
    
    (c << uno_wg.mla_cross(LAYERS.LABEL, thick = 20, length = 200)).dmove((4000,0))
    (c << uno_wg.mla_cross(LAYERS.LABEL, thick = 20, length = 200)).dmove((-4000,0))
        
    
    return c

@gf.cell
def sixteen_grating_3_rings(gratingComponent,
                            thisWgWidth = 0.45e0,
                            numGratings = 16,
                            gratingPitch = 250e0,
                            couplerGaps = [0.1e0, 0.2e0, 0.3e0],
                            couplerLengths = [15e0, 20e0, 25e0],
                            ringLengths = [500e0, 600e0, 700e0],
                            loopback_spacing_to_grating = 50e0):
    c = gf.Component()
    waveguideXs = waveguide_xs(thisWgWidth)
    gratingArray = c << gf.components.grating_coupler_array(
        grating_coupler = gratingComponent,
        n = numGratings, 
        pitch = gratingPitch,
        rotation = 90, 
        with_loopback = False)

    # loop back on ports 1-16    
    loopback_y1 = gratingArray.dymin - loopback_spacing_to_grating
    loopback_y2 = gratingArray.dymax + loopback_spacing_to_grating
    gf.routing.route_single_from_steps(c,
        gratingArray.ports["o0"], gratingArray.ports['o15'], 
        steps = [
        {"y": loopback_y1},
        {"dx": -gratingPitch},
        {"y": loopback_y2},
        {"dx": (numGratings+1)*gratingPitch},
        {"y": loopback_y1},
        {"dx": -gratingPitch}
        ])#,
        #cross_section = waveguideXs
        #)
    
    
    gf.routing.route_single(c,
        gratingArray.ports["o7"], gratingArray.ports['o8'])#, cross_section = waveguideXs
        #)
    
    # on a 16-port ring, room for 3 add-drop rings on (2,3,4,5), (6,7,10,11), (12,13,14,15)

    
    portsForHorizLoc = ['o3', 'o8', 'o13']
    portMappings = [[('o1', 'o2'), ('o2', 'o4'), ('o3', 'o3'), ('o4', 'o1')],
                          [('o5', 'o2'), ('o6', 'o4'), ('o9', 'o3'), ('o10', 'o1')],
                          [('o11', 'o2'), ('o12', 'o4'), ('o13', 'o3'), ('o14', 'o1')]]
    
    for i in range(3):
        thisRing = c << uno_wgd.gen_racetrack(numCouplers = 2,
                            wgWidth = thisWgWidth,
                            ringLength = ringLengths[i], 
                            couplingLength = couplerLengths[i], 
                            couplerDx = 30, 
                            couplerDy = 10, 
                            thisGap = couplerGaps[i], 
                            includeHeater = False)
        thisMiddlePort = portsForHorizLoc[i]
        thisRing.dmove(dp2tuple(thisRing.dcenter), gratingArray.ports[thisMiddlePort].dcenter + np.array((-gratingPitch/2,-160)))
        uno_tools.naive_multiport_route(c, gratingArray, thisRing,  portMappings[i], waveguideXs)
    return c

@gf.cell
def our_grating_TE(wgWidth):
    c = gf.Component()
    g = c << uno_wg.apodized_grating_coupler_rectangular(
            wg_width = 0.5, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.9, 
            R = 0.025, 
            lambda_c = 1.55, # um 
            no = 2.69, 
            ne = 1.444,
            width_grating = 20, 
            length_taper = 300)
    c.add_port(name = 'o1', port = g.ports['o1'])
    return c


@gf.cell
def our_grating_TM(wgWidth):
    c = gf.Component()
    g = c << uno_wg.apodized_grating_coupler_rectangular(
            wg_width = 0.5, 
            fiber_angle = 12, 
            N = 30, 
            F0 = 0.9, 
            R = 0.025, 
            lambda_c = 1.55, # um 
            no = 1.95, 
            ne = 1.444,
            width_grating = 20, 
            length_taper = 300)
    c.add_port(name = 'o1', port = g.ports['o1'])
    return c

gf.clear_cache()
full_chip().show()