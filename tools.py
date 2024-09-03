import gdsfactory as gf
from uno_layout import LAYERS, DEFAULT_RADIUS, DEFAULT_EDGE_SEP, waveguide_xs
import uno_layout.components_wg as uno_wg
import numpy as np

def naive_multiport_route(c, r1, r2, portMapping, xs):
    for thesePorts in portMapping:
        c.add(gf.routing.get_route(
            r1.ports[thesePorts[0]], r2.ports[thesePorts[1]], cross_section = xs).references)

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
                  straight1 = 500, # length of straight waveguide before component
                  dxdy = (1000,1000), # location of 2nd coupler along x axis, and
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
    dut.move(dut.ports['o2'], (straight1, dxdy[1]))
    
    # edge couplers and routing
    ed = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, labelIn, labelOut, tipWidth = tipWidth)
    inRoute = gf.routing.get_route(ed.ports["o1"], dut.ports[portMappings[0]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    c.add(inRoute.references)
    outRoute = gf.routing.get_route(ed.ports["o2"], dut.ports[portMappings[1]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    c.add(outRoute.references)
    c.with_uuid = True
    
    if(doLength):
        # hacky code for labelling spiral cutback/delay test lines
        totalLength = dut.info["length"] + inRoute.length + outRoute.length
        c.info["length"] = totalLength
        c.name = f"{totalLength:.0f}umDelay"
        c << gf.components.text(text = f"{1e3*wgWidth:.0f}nm/{1e-4*totalLength:.2f}cm", 
                                layer = LAYERS.ANNOTATION,
                                position = (dut.center[0], dut.center[1]),
                                justify = "center",
                                size = 25)
    return c

@gf.cell
def generic_3port(dutComponent: gf.Component, # see generic_2port for variable definitions
                    straightL = 500, 
                    dxdy = (1000,1000), 
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
        centerOutput = 0.5*(np.array(dut.ports[portMappings[1]].center) + np.array(dut.ports[portMappings[2]].center))
        dut.move(centerOutput, (dxdy[0] + edgeSep/2, straightL))
    else:
        
        dut.move(dut.ports[portMappings[0]], (straightL, dxdy[1]))
    
    # edge couplers
    ed = c << uno_wg.edge_coupler_tri(dxdy, wgWidth, edgeSep, labelIn, labelOut, textPosition = textPosition, tipWidth = tipWidth)
    # routing
    inRoute = gf.routing.get_route(ed.ports["o1"], dut.ports[portMappings[0]],
                                   radius=DEFAULT_RADIUS,
                                   cross_section=crossSection)
    c.add(inRoute.references)
    if(doBundleRoute):
        # do output routing as a bundle to avoid collisions?
        right_ports = [
            ed.ports["o2"], ed.ports["o3"]
        ]
        left_ports = [
            dut.ports[portMappings[1]], dut.ports[portMappings[2]]
        ]
        outRoutes = gf.routing.get_bundle(
            left_ports,
            right_ports,
            sort_ports=True,
            start_straight_length=0,
            enforce_port_ordering=False,
            cross_section = crossSection,
            radius = DEFAULT_RADIUS
        )
        for route in outRoutes:
            c.add(route.references)
    else:
        outRoute1 = gf.routing.get_route(ed.ports["o2"], dut.ports[portMappings[1]],
                                       radius=DEFAULT_RADIUS,
                                       cross_section=crossSection)
        c.add(outRoute1.references)
        outRoute2 = gf.routing.get_route(ed.ports["o3"], dut.ports[portMappings[2]],
                                       radius=DEFAULT_RADIUS,
                                       cross_section=crossSection)
        c.add(outRoute2.references)
    c.with_uuid = True
    return c