import gdsfactory as gf
#from uno_layout import LAYERS, DEFAULT_RADIUS, DEFAULT_EDGE_SEP, waveguide_xs
import uno_layout.components_wg as uno_wg
import numpy as np

from uno_layout import Settings, LayerMapUNO, waveguide_xs
LAYERS = LayerMapUNO
DEFAULT_WG_WIDTH = Settings.DEFAULT_WG_WIDTH
DEFAULT_RADIUS = Settings.DEFAULT_RADIUS
DEFAULT_EDGE_SEP = Settings.DEFAULT_EDGE_SEP
DEFAULT_TEXT_SIZE = Settings.DEFAULT_TEXT_SIZE
DEFAULT_DXDY = Settings.DEFAULT_DXDY

def naive_multiport_route(c, r1, r2, portMapping, xs):
    for thesePorts in portMapping:
        gf.routing.route_single(c, 
            r1.ports[thesePorts[0]], 
            r2.ports[thesePorts[1]], 
            cross_section = xs)

def count_optical_ports(componentIn):
    # count # of ports that start with 'o'
    # TODO fix with electrical/optical type
    count = 0
    for thisPort in componentIn.ports:
        if(thisPort[0] == 'o'):
            count += 1
    return count

@gf.cell
def offset_waveguide(componentIn, offsetDistance):
    # take a component and offset *just the waveguide layer*
    waveguideOnly = componentIn.extract([LAYERS.WG])
    noWaveguide = componentIn.remove_layers([LAYERS.WG])
    c = gf.Component()
    c << noWaveguide
    # do offsetDistance/2 because we're offsetting on both sides of wg
    c << waveguideOnly.offset(offsetDistance/2, layer = LAYERS.WG)
    return c
    
# TODO generic n-port

@gf.cell
def generic_2port(dutComponent: gf.Component, 
                  straight1 = 500e0, # length of straight waveguide before component
                  dxdy = (1000e0,1000e0), # location of 2nd coupler along x axis, and
                                      # location of 1st coupler along y axis, resp.
                  wgWidth = None, # routing waveguide width
                  labelIn = None, # input edge coupler label
                  labelOut = None, # output edge coupler label
                  doLength = True, # include annotation of total length of structure
                  rotateAngle = 0, # rotate component
                  flipHorizontal = False, # flip component
                  portMappings = ("o1", "o2"), # asignment of component Ports to 1st, 2nd edge couplers
                  tipWidth = None
                  ): 
    # generate structure with spiral, edge couplers, and routing between em
    c = gf.Component()
    # get cross section settings
    crossSection = waveguide_xs(wgWidth)
    # add generic 2-port component
    dut = c << dutComponent
    # do flipping/rotations
    if(flipHorizontal):
        dut.mirror((0,0), (0,1))
    if(rotateAngle != 0):
        dut.rotate(rotateAngle)
    dut.dmove(dut.ports['o2'].dcenter, (straight1, dxdy[1]))
    
    # edge couplers and routing
    ed = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, labelIn, labelOut, tipWidth = tipWidth)
    inRoute = gf.routing.route_single(c, ed.ports["o1"], dut.ports[portMappings[0]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    outRoute = gf.routing.route_single(c, ed.ports["o2"], dut.ports[portMappings[1]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    c.with_uuid = True
    
    if(doLength):
        # hacky code for labelling spiral cutback/delay test lines
        totalLength = dut.info["length"] + inRoute.length + outRoute.length
        c.info["length"] = totalLength
        c.name = f"{totalLength:.0f}umDelay"
        c << gf.components.text(text = f"{1e0*wgWidth:.0f}nm/{1e-4*totalLength:.2f}cm", 
                                layer = LAYERS.ANNOTATION,
                                position = (dut.dcenter.x, dut.dcenter.y),
                                justify = "center",
                                size = 25e0)
    return c

@gf.cell
def generic_3port(dutComponent: gf.Component, # see generic_2port for variable definitions
                    straightL = 500e0, 
                    dxdy = (1000e0,1000e0), 
                    wgWidth = None, 
                    edgeSep = DEFAULT_EDGE_SEP,
                    labelIn = None, 
                    labelOut = None,
                    rotateAngle = 0, 
                    flipHorizontal = False, 
                    portMappings = ("o1", "o2", "o3"),
                    putAfterBend = False,
                    doBundleRoute = False,
                    textPosition = None,
                    tipWidth = None):
    # generate structure with 3-port and route to edge couplers
    c = gf.Component()
    # get cross section settings
    crossSection = waveguide_xs(wgWidth)
    # add generic 3-port component
    dut = c << dutComponent
    # do flipping/rotations
    if(flipHorizontal):
        dut.mirror((0,0), (0,1))
    if(rotateAngle != 0):
        dut.rotate(rotateAngle)
    if(putAfterBend):
        dut.rotate(-90)
        # find center point of two output ports
        centerOutput = 0.5*(np.array(dut.ports[portMappings[1]].dcenter) + np.array(dut.ports[portMappings[2]].dcenter))
        dut.dmove(centerOutput, (dxdy[0] + edgeSep/2, straightL))
    else:
        
        dut.dmove(dut.ports[portMappings[0]].dcenter, (straightL, dxdy[1]))
    
    # edge couplers
    ed = c << uno_wg.edge_coupler_tri(dxdy, wgWidth, edgeSep, labelIn, labelOut, textPosition = textPosition, tipWidth = tipWidth)
    # routing
    gf.routing.route_single(c, ed.ports["o1"], dut.ports[portMappings[0]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    if(doBundleRoute):
        # do output routing as a bundle to avoid collisions?
        right_ports = [
            ed.ports["o2"], ed.ports["o3"]
        ]
        left_ports = [
            dut.ports[portMappings[1]], dut.ports[portMappings[2]]
        ]
        gf.routing.route_bundle(c,
            left_ports,
            right_ports,
            sort_ports=True,
            start_straight_length=0,
            enforce_port_ordering=False,
            cross_section = crossSection,
            radius = DEFAULT_RADIUS
        )
    else:
        gf.routing.route_single(c, ed.ports["o2"], dut.ports[portMappings[1]],
                                       radius=DEFAULT_RADIUS,
                                       cross_section=crossSection)
        gf.routing.route_single(c, ed.ports["o3"], dut.ports[portMappings[2]],
                                       radius=DEFAULT_RADIUS,
                                       cross_section=crossSection)
    c.with_uuid = True
    return c

def dp2tuple(this_point : gf.kdb.DPoint):
    return (this_point.x, this_point.y)