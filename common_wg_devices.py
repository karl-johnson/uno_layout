import gdsfactory as gf
from uno_layout import Settings, LayerMapUNO, waveguide_xs
import uno_layout.components_wg as uno_wg
import numpy as np
import uno_layout.tools as uno_tools
LAYERS = LayerMapUNO
DEFAULT_WG_WIDTH = Settings.DEFAULT_WG_WIDTH
DEFAULT_RADIUS = Settings.DEFAULT_RADIUS
DEFAULT_EDGE_SEP = Settings.DEFAULT_EDGE_SEP
DEFAULT_TEXT_SIZE = Settings.DEFAULT_TEXT_SIZE
DEFAULT_DXDY = Settings.DEFAULT_DXDY
DEFAULT_GRATING_DIST = Settings.DEFAULT_GRATING_DIST



@gf.cell
def dir_pol_splitter(xsIn, gapIn = 450, lengthIn = 15000, numStages = 3000, 
                   coupDy = 4000, coupDx = 10000, stageDx = 70000, stageDy = 15000):
    # polarization splitter made by cascaded dir couplers
    # through is TE, cross is TM, as TM coupling coeff is much higher
    inPort = 'o1'
    unusedPort = 'o2'
    tePort = 'o4'
    tmPort = 'o3'
    c = gf.Component()
    
    
    baseCoupler = gf.components.coupler(gap = gapIn, length = lengthIn, cross_section=xsIn)
    # place first coupler
    c1 = c << baseCoupler
    
    lastTE = c1.ports[tePort]
    lastTM = c1.ports[tmPort]
    # place taper + bend on unused input/outputs to reduce leakage and reflections
    bendRadius = 5000
    thisBend = gf.components.bend_euler(radius = bendRadius, cross_section = xsIn, angle = -90)
    tipWidth = 100
    thisTaper = gf.components.taper_cross_section(
        cross_section1 = xsIn,
        cross_section2 = waveguide_xs(tipWidth))
    
    
    t1 = c << thisBend
    t1.connect('o1', c1.ports[unusedPort])
    (c << thisTaper).connect('o1', t1.ports['o2'])
    
    # if doing multi-stage, place next couplers
    if(numStages > 1):
        for stageIdx in range(1, numStages):
            # place next couplers
            thisCTE = c << baseCoupler
            thisCTE.dmirror_x()
            thisCTE.dmove((stageIdx*stageDx, -stageDy/2))
            c.add(gf.routing.get_route_sbend(lastTE, 
                                              thisCTE.ports[inPort],
                                              cross_section=xsIn).references)
            lastTE = thisCTE.ports[tePort]
            b1 = (c << thisBend).dmirror()
            b1.connect('o1', thisCTE.ports[unusedPort])
            (c << thisTaper).connect('o1', b1.ports['o2'])
            (c << thisTaper).connect('o1', thisCTE.ports[tmPort])
            
            
            
            thisCTM = c << baseCoupler
            thisCTM.dmove((stageIdx*stageDx, stageDy/2))
            c.add(gf.routing.get_route_sbend(lastTM, 
                                              thisCTM.ports[inPort],
                                              cross_section=xsIn).references)
            lastTM = thisCTM.ports[tmPort]
            b2 = (c << thisBend)
            b2.connect('o1', thisCTM.ports[unusedPort])
            (c << thisTaper).connect('o1', b2.ports['o2'])
            (c << thisTaper).connect('o1', thisCTM.ports[tePort])
    
    
    c.add_port('o1', port = c1.ports['o1'])
    c.add_port('o2', port = lastTE)
    c.add_port('o3', port = lastTM)
    
    return c

# MOST generic function supporting
# - 1 or 2 coupler racetrack
# - heaters
# - does not include routing
@gf.cell
def gen_racetrack(numCouplers, # must be 1 or 2
                    wgWidth = DEFAULT_WG_WIDTH, # optical parameters
                    ringLength = 500e0, 
                    couplingLength = 10e0, 
                    couplerDx = 30e0, 
                    couplerDy = 10e0, 
                    thisGap = 0.5e0, 
                    eulerRadius = 35e0,
                    includeHeater = True,
                    heaterWidth = 5e0, # electrical parameters
                    leadDxDy = None,
                    leadSep = 5e0,
                    halfRingHeater = False
                    ):
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    leadDxDy = (20e0,7.5e0) if leadDxDy is None else leadDxDy
    half_coupler = uno_wg.coupler_asymmetric(gap = thisGap, 
                                                    cross_section = crossSection,
                                                    dx = couplerDx, dy = couplerDy)
    # # place bottom ring couplers
    c1 = c << half_coupler
    c2 = c << half_coupler
    c2.dmirror_x()
    # # add coupling length
    c2.dmove(c2.ports['o1'].dcenter, c1.ports['o1'].dcenter)
    c1.dmove((couplingLength, 0))

    # coupling region straight wgs
    s1 = c << gf.components.straight(length = couplingLength, cross_section = crossSection)
    s1.connect('o1', c1.ports['o1'])
    s2 = c << gf.components.straight(length = couplingLength, cross_section = crossSection)
    s2.connect('o1', c1.ports['o0'])

    # create most basic unit of the ring manually for APPROX length
    ringBend = gf.path.euler(radius = eulerRadius, angle = -180)
    totStraightLength = ringLength - 2*ringBend.length() - 2*couplingLength - 4*couplerDy
    ringPathStraight = gf.path.straight(length = totStraightLength/4)
    baseRingPath = ringPathStraight + ringBend + ringPathStraight
    p1 = c << gf.path.extrude(baseRingPath, cross_section = crossSection)
    p2 = c << gf.path.extrude(baseRingPath.dmirror(), cross_section = crossSection)
    p1.dmirror_x() 
    p2.dmirror_x() # I dare you to try and change/simplify the double mirror on p2

    # move ring paths in place
    p1.connect('o1', c1.ports['o3'])
    p2.connect('o1', c2.ports['o3'])
    
    # add the two optical ports that will be same in either case
    c.add_port('o1', port = c1.ports['o2'])
    c.add_port('o2', port = c2.ports['o2'])

    if(numCouplers == 1):
        print(1)
        # close ring with waveguide
        gf.routing.route_single(c, p1.ports['o2'], p2.ports['o2'])
    elif(numCouplers == 2):
        # close ring with coupler
        c3 = c << half_coupler
        c3.dmirror()
        c4 = c << half_coupler
        c3.connect('o3', p1.ports['o2'])
        c4.connect('o3', p2.ports['o2'])
        gf.routing.route_single(c, c3.ports["o1"], c4.ports["o1"],cross_section=waveguide_xs)
        gf.routing.route_single(c, c3.ports["o0"], c4.ports["o0"],cross_section=waveguide_xs)
        # add those extra ports
        c.add_port('o3', port = c3.ports['o2'])
        c.add_port('o4', port = c4.ports['o2']) 
    else:
        raise Exception("numCouplers must be 1 or 2!")

    if includeHeater:
        
        # now can use same paths + route strategy for heater
        heaterSection = gf.CrossSection(sections = [gf.Section(width = heaterWidth, layer = LAYERS.HEATER, port_names = ("e1", "e2"))])
        h1 = c << gf.path.extrude(baseRingPath, cross_section = heaterSection)
        h1.dmove(h1.ports['e1'].dcenter, p2.ports['o2'].dcenter)
        
        # now add leads, which are L-shaped
        lPath = gf.path.Path([(0,0),(leadDxDy[0],0),leadDxDy])
        elecL = gf.path.extrude(lPath, heaterSection)
        l1 = c << elecL
        l2 = c << elecL 
        l2.dmirror_y()
        # what we do with these leads depends on if we're using a half-ring heater or not
        if halfRingHeater:
            l1.connect('e1', h1.ports['e1'])
            l2.connect('e1', h1.ports['e2'])
        else:
            # this is kinda insane but using a dummy Component for objects that will be the subject of a boolean operation later
            # i.e. we have cast those original components to a ghost dimension
            c2 = gf.Component()
            h2 = c2 << gf.path.extrude(baseRingPath, cross_section = heaterSection)
            h2.drotate(180)
            h2.dmove(h2.ports['e2'].dcenter, p1.ports['o2'].dcenter)
            gf.routing.route_single_electrical(c, h1.ports["e1"], h2.ports["e2"], cross_section=heaterSection)
            gf.routing.route_single_electrical(c, h1.ports["e2"], h2.ports["e1"], cross_section=heaterSection)
            # to form leads, use boolean operation to cut a chunk out of one side, then add leads
            subtrBlock = c2 << gf.components.rectangle(size = (h2.dsize_info.width, leadSep), layer = LAYERS.HEATER)
            # move to a spot that it's (almost) guaranteed to overlap fully
            subtrBlock.dmove((subtrBlock.dcenter.x, subtrBlock.dcenter.y), (h2.dcenter.x + .1,h2.dcenter.y))    
            h2_cut = c << gf.boolean(h2, subtrBlock, 'A-B', layer = LAYERS.HEATER)
            l1.dmove((l1.dxmin, l1.dymin), (h2_cut.dxmax - heaterWidth, subtrBlock.dymax))
            l2.dmove((l2.dxmin, l2.dymax), (h2_cut.dxmax - heaterWidth, subtrBlock.dymin))
       
        c.add_port('e1', port = l1.ports['e2'])
        c.add_port('e2', port = l2.ports['e2'])
    
    # #print(totalLength)
    # totalLength = (2*baseRingPath.length() + 4*couplerDy 
    #                 + 2*couplingLength)
    # c << gf.components.text(text = f"{totalLength:.1f}um", 
    #                         layer = LAYERS.ANNOTATION,
    #                         position = (c1.dcenter.x, p1.dcenter.y + 30e0),
    #                         justify = "center",
    #                         size = DEFAULT_TEXT_SIZE)
    return c

@gf.cell
def ring_with_grating_couplers(ring: gf.Component | gf.ComponentReference | dict = gen_racetrack(couplerDx=50,numCouplers=2,includeHeater=False),
                             gratingCoupler: gf.Component | gf.ComponentReference | dict = None, Label = None):
    if type(ring) == dict:
        if "couplerDx" not in ring:
            ring["couplerDx"] = 50
        ring["numCouplers"] = 2
        ring["includeHeater"] = False
        ring = gen_racetrack(**ring)
    if type(gratingCoupler) == dict:
        gratingCoupler = uno_wg.apodized_grating_coupler_rectangular(gratingCoupler)
    c = gf.Component()
    g = list[gf.ComponentReference]()
    for i in range(4):
        g.append(c << gratingCoupler)
        g[i].drotate(-90,center="o2")
        g[i].dmove(gratingCoupler.ports["o2"].dcenter,(i*DEFAULT_GRATING_DIST,0))
        c.add_port("o"+str(i+1),g[i].ports["o2"])
    r = c << ring
    r.dmove(((r.ports["o1"].dx+r.ports["o4"].dx)/2,(r.ports["o1"].dy+r.ports["o4"].dy)/2),(DEFAULT_GRATING_DIST*1.5,200+g[0].ports["o1"].dy))
    gf.routing.route_bundle(c,[r.ports["o4"],r.ports["o2"],r.ports["o1"],r.ports["o3"]],[x.ports["o1"] for x in g],cross_section = waveguide_xs)
    
    c.info["measurement"] = "ring"
    
    if Label is not None:
        t = c << gf.components.text(Label,size=20,position=(DEFAULT_GRATING_DIST*1.5,300),justify="center",layer=LAYERS.LABEL)
    return c

@gf.cell
def two_grating_loopback(gratingCoupler = None, Label = None):
    c = gf.Component()
    c1 = c << gratingCoupler
    c1.drotate(-90)
    c2 = c << gratingCoupler
    c2.drotate(-90)
    c2.dmove(origin=(0,0),destination=(DEFAULT_GRATING_DIST,0))
    gf.routing.route_single(c,c1.ports["o1"],c2.ports["o1"],cross_section=waveguide_xs,start_straight_length=50)
    c.add_port(name="o1", port=c1.ports["o2"])
    c.add_port(name="o2", port=c2.ports["o2"])
    c.info["measurement"] = "alignment"
    
    if Label is not None:
        t = c << gf.components.text(Label,size=20,position=(DEFAULT_GRATING_DIST/2, c1.ports["o1"].dy),justify="center",layer=LAYERS.LABEL)
    return c

# routes electrical and optical made by gen_racetrack
@gf.cell
def gen_routed_racetrack(ringComponent = None,
                         wgWidth = 0.5e0,
                         offsetX = 500e0,
                         dxdy = (1000e0,1000e0),
                         inLabel = "Ri",
                         outLabel = "Ro",
                         routingRad = DEFAULT_RADIUS,
                         inputSep = 200e0,
                         outputSep = 200e0,
                         edgeCouplerTip = 0.11e0):
    crossSection = waveguide_xs(wgWidth)
    portOrder = ["o2", "o1", "o4", "o3"]
    c = gf.Component()
    r = c << ringComponent
    r.dmove(r.ports[portOrder[0]].dcenter, (offsetX, dxdy[1]))
    # detect whether ringComponent has 1 or 2 couplers, hacky method for now
    numPorts = uno_tools.count_optical_ports(ringComponent)
    
    
    
    e1 = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, 
                                       inLabel+'-0', outLabel+'-0', tipWidth=edgeCouplerTip)
    c.add(gf.routing.get_route(e1.ports["o1"], 
                                      r.ports[portOrder[0]],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(e1.ports["o2"], 
                                      r.ports[portOrder[1]],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    if(numPorts == 4):
        e2 = c << uno_wg.edge_coupler_pair(np.array(dxdy) + np.array((outputSep, inputSep)), wgWidth,
                                    inLabel+'-1', outLabel+'-1', tipWidth=edgeCouplerTip)
        c.add(gf.routing.get_route(e2.ports["o1"], 
                                          r.ports[portOrder[2]],
                                          radius=routingRad,
                                          cross_section=crossSection).references)
        
        c.add(gf.routing.get_route(e2.ports["o2"], 
                                          r.ports[portOrder[3]],
                                          radius=routingRad,
                                          cross_section=crossSection).references)
    return c

@gf.cell 
def gen_MZI_unbal(coupler, offsetX, dxdy, wgWidth, dL,
                  labelIn = "", labelOut = "", edgeSep = DEFAULT_EDGE_SEP):
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    #thisBend = partial(gf.components.bend_euler, angle = 90)
    # put down edge couplers
    e1 = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, labelIn, labelOut)
    e2 = c << uno_wg.edge_coupler_pair(np.array(dxdy) + edgeSep, wgWidth, None, None)
    # put down mzi from gdsfactory
    m = c << gf.components.mzi2x2_2x2(delta_length = dL,
                                      splitter = coupler,
                                      combiner = coupler,
                                      #bend = thisBend,
                                      port_e1_splitter = 'p2', 
                                      port_e0_splitter = 'p4',
                                      port_e1_combiner = 'p2',
                                      port_e0_combiner = 'p4',
                                      cross_section = crossSection,
                                      mirror_bot = False)
    m.dmirror_x()
    m.dmove((0,0), (offsetX,dxdy[1]+edgeSep/2))
    # s bends
    # add s bends to separate paths during long runs
    sBendX = 150e0
    # use distance between ports of coupler to guage proper dy (like route_sbend)
    couplerPortSep = (m.ports["o1"].dcenter - m.ports["o2"].dcenter)[1]
    sBendY = (edgeSep - couplerPortSep)/2
    baseSbend = gf.components.bend_s(size=(sBendX, sBendY), 
                                     cross_section=crossSection)
    s1 = c << baseSbend
    s2 = c << baseSbend
    s3 = c << baseSbend
    s4 = c << baseSbend
    
    s1.dmirror_y()
    s3.dmirror_y()
    s1.connect('o1', m.ports['o1'])
    s2.connect('o1', m.ports['o2'])
    s3.connect('o1', m.ports['o3'])
    s4.connect('o1', m.ports['o4'])
    
    c.add(gf.routing.get_route(e2.ports["o1"], 
                                      s1.ports["o2"],
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(e1.ports["o1"], 
                                      s2.ports["o2"],
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(s3.ports['o2'], 
                                      e1.ports["o2"],
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(s4.ports['o2'], 
                                      e2.ports["o2"],
                                      cross_section=crossSection).references)
    c << gf.components.text(text = f"{1e-3*dL:.2f}mm", 
                            layer = LAYERS.ANNOTATION,
                            position = (m.dcenter[0], m.dcenter[1]),
                            justify = "center",
                            size = DEFAULT_TEXT_SIZE)
    return c