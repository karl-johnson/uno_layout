import gdsfactory as gf
from uno_layout import LAYERS, DEFAULT_WG_WIDTH, DEFAULT_RADIUS, DEFAULT_EDGE_SEP, waveguide_xs
import uno_layout.components_wg as uno_wg
import numpy as np
import uno_layout.tools as uno_tools

@gf.cell
def dirPolSplitter(xsIn, gapIn = 0.45, lengthIn = 15, numStages = 3, 
                   coupDy = 4, coupDx = 10, stageDx = 70, stageDy = 15):
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
    thisBend = gf.components.bend_euler(radius = 5, cross_section = xsIn, angle = -90)
    thisTaper = gf.components.taper_cross_section(
        cross_section1 = xsIn,
        cross_section2 = waveguide_xs(0.1))
    
    
    t1 = c << thisBend
    t1.connect('o1', c1.ports[unusedPort])
    (c << thisTaper).connect('o1', t1.ports['o2'])
    
    # if doing multi-stage, place next couplers
    if(numStages > 1):
        for stageIdx in range(1, numStages):
            # place next couplers
            thisCTE = c << baseCoupler
            thisCTE.mirror((1,0))
            thisCTE.move((stageIdx*stageDx, -stageDy/2))
            c.add(gf.routing.get_route_sbend(lastTE, 
                                              thisCTE.ports[inPort],
                                              cross_section=xsIn).references)
            lastTE = thisCTE.ports[tePort]
            b1 = (c << thisBend).mirror()
            b1.connect('o1', thisCTE.ports[unusedPort])
            (c << thisTaper).connect('o1', b1.ports['o2'])
            (c << thisTaper).connect('o1', thisCTE.ports[tmPort])
            
            
            
            thisCTM = c << baseCoupler
            thisCTM.move((stageIdx*stageDx, stageDy/2))
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

@gf.cell
def gen_one_coupler_ring(offsetX = 500,
                         dxdy = (1000,1000), 
                         wgWidth = DEFAULT_WG_WIDTH, 
                         ringLength = 500, 
                         couplingLength = 10, 
                         couplerDx = 30, 
                         couplerDy = 10, 
                         thisGap = 0.5,
                         inLabel = "Ri", 
                         outLabel = "Ro", 
                         doFlipRing = True, 
                         doFlipLabel = True,
                         routingRad = DEFAULT_RADIUS):
    
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    half_coupler = gf.components.coupler_asymmetric(gap = thisGap, 
                                                    cross_section = crossSection,
                                                    dx = couplerDx, dy = couplerDy)
    # put down edge couplers
    e1 = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, inLabel, outLabel)
    # place ring couplers
    c1 = c << half_coupler
    c2 = c << half_coupler
    c1.move(c1.ports['o3'], (offsetX, dxdy[1]))
    c2.mirror((0,1))
    # add coupling length
    c2.move(c2.ports['o1'], c1.ports['o1'])
    c1.move((couplingLength, 0))
    # coupling cross section
    centerToCenter = wgWidth + thisGap
    s0 = gf.Section(width=wgWidth, offset=centerToCenter/2, layer=(1, 0), port_names=("in", "out"))
    s1 = gf.Section(width=wgWidth, offset=-centerToCenter/2, layer=(1, 0))
    couplerSection = gf.CrossSection(sections=[s0, s1])
    c.add(gf.routing.get_route(c1.ports["o1"], c2.ports["o1"], cross_section=couplerSection).references)
    # create most basic unit of the ring manually for APPROX length
    hardcodedRadius = 35
    ringBend = gf.path.euler(radius = hardcodedRadius, angle = -180)
    totStraightLength = ringLength - 2*ringBend.length()
    baseRingPath = gf.path.straight(length = totStraightLength/4)
    baseRingPath += ringBend
    p1 = c << gf.path.extrude(baseRingPath, cross_section = crossSection)
    
    p2 = c << gf.path.extrude(baseRingPath.mirror(), cross_section = crossSection)
    if doFlipRing:
        #c1.mirror(c1.ports['o1'].center, (c1.ports['o1'].center[0]+1, c1.ports['o1'].center[1]))
        p1.mirror((0,0), (1,0))
        p2.mirror((0,0), (1,0))
    
    # move ring paths in place
    p1.connect('o1', destination=c1.ports['o2'])
    p2.connect('o1', destination=c2.ports['o2'])
    
    # route all that is remaining
    c.add(gf.routing.get_route_sbend(e1.ports["o1"], 
                                      c2.ports["o3"],
                                      cross_section=crossSection).references)
    
    c.add(gf.routing.get_route(e1.ports["o2"], 
                                      c1.ports["o3"],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    rr = gf.routing.get_route(p1.ports["o2"], 
                                      p2.ports["o2"],
                                      radius=routingRad,
                                      cross_section=crossSection)
    c.add(rr.references)
    totalLength = 2*baseRingPath.length() + 2*rr.length
    #print(totalLength)
    c << gf.components.text(text = f"{1e-3*totalLength:.2f}mm", 
                            layer = LAYERS.ANNOTATION,
                            position = (c1.center[0], p1.center[1] + 30),
                            justify = "center",
                            size = 25)
    return c



# MOST generic function supporting
# - 1 or 2 coupler racetrack
# - heaters
# - does not include routing
@gf.cell
def gen_racetrack(numCouplers, # must be 1 or 2
                    wgWidth = DEFAULT_WG_WIDTH, # optical parameters
                    ringLength = 500, 
                    couplingLength = 10, 
                    couplerDx = 30, 
                    couplerDy = 10, 
                    thisGap = 0.5, 
                    eulerRadius = 35,
                    includeHeater = True,
                    heaterWidth = 5, # electrical parameters
                    leadDxDy = None,
                    leadSep = 5,
                    halfRingHeater = False
                    ):
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    # using this GDSfactory stock coupler ended up being kinda a bad idea
    # we have to use a two-waveguide cross section in coupling areas
    # which is not very elegant, in my opinion
    leadDxDy = (20,7.5) if leadDxDy is None else leadDxDy
    half_coupler = gf.components.coupler_asymmetric(gap = thisGap, 
                                                    cross_section = crossSection,
                                                    dx = couplerDx, dy = couplerDy)
    # place bottom ring couplers
    c1 = c << half_coupler
    c2 = c << half_coupler
    c2.mirror((0,1))
    # add coupling length
    c2.move(c2.ports['o1'], c1.ports['o1'])
    c1.move((couplingLength, 0))
    # coupling cross section
    centerToCenter = wgWidth + thisGap
    s0 = gf.Section(width=wgWidth, offset=centerToCenter/2, layer=(1, 0), port_names=("in", "out"))
    s1 = gf.Section(width=wgWidth, offset=-centerToCenter/2, layer=(1, 0))
    couplerSection = gf.CrossSection(sections=[s0, s1])
    couplerRoute1 = gf.routing.get_route(c1.ports["o1"], c2.ports["o1"], cross_section=couplerSection)
    c.add(couplerRoute1.references)

    # create most basic unit of the ring manually for APPROX length
    ringBend = gf.path.euler(radius = eulerRadius, angle = -180)
    totStraightLength = ringLength - 2*ringBend.length() - 2*couplingLength - 4*couplerDy
    ringPathStraight = gf.path.straight(length = totStraightLength/4)
    baseRingPath = ringPathStraight + ringBend + ringPathStraight
    p1 = c << gf.path.extrude(baseRingPath, cross_section = crossSection)
    p2 = c << gf.path.extrude(baseRingPath.mirror(), cross_section = crossSection)
    p1.mirror((0,0), (1,0)) 
    p2.mirror((0,0), (1,0)) # I dare you to try and change/simplify the double mirror on p2

    # move ring paths in place
    p1.connect('o1', destination=c1.ports['o2'])
    p2.connect('o1', destination=c2.ports['o2'])
    
    # add the two optical ports that will be same in either case
    c.add_port('o1', port = c1.ports['o3'])
    c.add_port('o2', port = c2.ports['o3'])

    if(numCouplers == 1):
        # close ring with waveguide
        couplerRoute2 = gf.routing.get_route(p1.ports['o2'], p2.ports['o2'], cross_section=crossSection)
        c.add(couplerRoute2.references)
    elif(numCouplers == 2):
        # close ring with coupler
        c3 = c << half_coupler
        c3.mirror()
        c4 = c << half_coupler
        c3.connect('o2', destination=p1.ports['o2'])
        c4.connect('o2', destination=p2.ports['o2'])
        couplerRoute2 = gf.routing.get_route(c3.ports["o1"], c4.ports["o1"], cross_section=couplerSection)
        c.add(couplerRoute2.references)
        # add those extra ports
        c.add_port('o3', port = c3.ports['o3'])
        c.add_port('o4', port = c4.ports['o3'])
    else:
        raise Exception("numCouplers must be 1 or 2!")

    if includeHeater:
        
        # now can use same paths + route strategy for heater
        heaterSection = gf.CrossSection(sections = [gf.Section(width = heaterWidth, layer = LAYERS.HEATER, port_names = ("e1", "e2"))])
        h1 = c << gf.path.extrude(baseRingPath, cross_section = heaterSection)
        h1.move('e1', destination = p2.ports['o2'])
        
        # now add leads, which are L-shaped
        lPath = gf.path.Path([(0,0),(leadDxDy[0],0),leadDxDy])
        elecL = gf.path.extrude(lPath, heaterSection)
        l1 = c << elecL
        l2 = c << elecL 
        l2.mirror((1,0))
        # what we do with these leads depends on if we're using a half-ring heater or not
        if halfRingHeater:
            l1.connect('e1', h1.ports['e1'])
            l2.connect('e1', h1.ports['e2'])
        else:
            # this is kinda insane but using a dummy Component for objects that will be the subject of a boolean operation later
            # i.e. we have cast those original components to a ghost dimension
            c2 = gf.Component()
            h2 = c2 << gf.path.extrude(baseRingPath, cross_section = heaterSection)
            h2.rotate(180)
            h2.move('e2', destination = p1.ports['o2'])
            c.add(gf.routing.get_route(h1.ports["e1"], h2.ports["e2"], cross_section=heaterSection).references)
            c.add(gf.routing.get_route(h1.ports["e2"], h2.ports["e1"], cross_section=heaterSection).references)
            # to form leads, use boolean operation to cut a chunk out of one side, then add leads
            subtrBlock = c2 << gf.components.rectangle(size = (h2.size[0], leadSep), layer = LAYERS.HEATER)
            # move to a spot that it's (almost) guaranteed to overlap fully
            subtrBlock.move(subtrBlock.center, np.array(h2.center) + np.array((.1,0)))    
            h2_cut = c << gf.geometry.boolean(h2, subtrBlock, 'A-B', layer = LAYERS.HEATER)
            l1.move((l1.xmin, l1.ymin), (h2_cut.xmax - heaterWidth, subtrBlock.ymax))
            l2.move((l2.xmin, l2.ymax), (h2_cut.xmax - heaterWidth, subtrBlock.ymin))
       
        c.add_port('e1', port = l1.ports['e2'])
        c.add_port('e2', port = l2.ports['e2'])
    
    #print(totalLength)
    totalLength = (2*baseRingPath.length() + 4*couplerDy 
                   + 2*couplingLength)
    c << gf.components.text(text = f"{totalLength:.1f}um", 
                            layer = LAYERS.ANNOTATION,
                            position = (c1.center[0], p1.center[1] + 30),
                            justify = "center",
                            size = 25)
    return c

# routes electrical and optical made by gen_racetrack
@gf.cell
def gen_routed_racetrack(ringComponent = None,
                         wgWidth = 0.5,
                         offsetX = 500,
                         dxdy = (1000,1000),
                         inLabel = "Ri",
                         outLabel = "Ro",
                         routingRad = DEFAULT_RADIUS,
                         inputSep = 200,
                         outputSep = 200,
                         edgeCouplerTip = 0.11):
    crossSection = waveguide_xs(wgWidth)
    portOrder = ["o2", "o1", "o4", "o3"]
    c = gf.Component()
    r = c << ringComponent
    r.move(r.ports[portOrder[0]], (offsetX, dxdy[1]))
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
def gen_two_coupler_ring(offsetX = 500, 
                         dxdy = (1000,1000),
                         wgWidth = DEFAULT_WG_WIDTH, 
                         ringLength = 500, 
                         couplingLength = 10, 
                         couplerDx = 30, 
                         couplerDy = 10, 
                         thisGap = 0.5,
                         inLabel = "Ri", 
                         outLabel = "Ro", 
                         doFlipRing = True, 
                         doFlipLabel = True,
                         routingRad = DEFAULT_RADIUS,
                         inputSep = 200,
                         outputSep = 200):
    # TODO FIX LENGTH CALCULATION
    c = gf.Component()
    crossSection = waveguide_xs(wgWidth)
    half_coupler = gf.components.coupler_asymmetric(gap = thisGap, 
                                                    cross_section = crossSection,
                                                    dx = couplerDx, dy = couplerDy)
    # put down edge couplers
    # WOW this is hacky
    # TODO fix magic numbers
    # inputSep = 200
    ringEdgeTipWidth = 0.11
    e1 = c << uno_wg.edge_coupler_pair(dxdy, wgWidth, inLabel+'-0', outLabel+'-0', tipWidth=ringEdgeTipWidth)
    e2 = c << uno_wg.edge_coupler_pair(np.array(dxdy) + np.array((outputSep, inputSep)), wgWidth,
                                inLabel+'-1', outLabel+'-1', tipWidth=ringEdgeTipWidth)
    
    # place ring couplers
    c1 = c << half_coupler
    c2 = c << half_coupler
    c1.move(c1.ports['o3'], (offsetX, dxdy[1]))
    c2.mirror((0,1))
    # add coupling length
    c2.move(c2.ports['o1'], c1.ports['o1'])
    c1.move((couplingLength, 0))
    # coupling cross section
    centerToCenter = wgWidth + thisGap
    s0 = gf.Section(width=wgWidth, offset=centerToCenter/2, layer=(1, 0), port_names=("in", "out"))
    s1 = gf.Section(width=wgWidth, offset=-centerToCenter/2, layer=(1, 0))
    couplerSection = gf.CrossSection(sections=[s0, s1])
    couplerRoute1 = gf.routing.get_route(c1.ports["o1"], c2.ports["o1"], cross_section=couplerSection)
    c.add(couplerRoute1.references)
    # create most basic unit of the ring manually for APPROX length
    hardcodedRadius = 35
    ringBend = gf.path.euler(radius = hardcodedRadius, angle = -180)
    totStraightLength = ringLength - 2*ringBend.length() - 2*couplingLength - 4*couplerDy
    ringPathStraight = gf.path.straight(length = totStraightLength/4)
    baseRingPath = ringPathStraight + ringBend + ringPathStraight
    p1 = c << gf.path.extrude(baseRingPath, cross_section = crossSection)
    p2 = c << gf.path.extrude(baseRingPath.mirror(), cross_section = crossSection)
    if doFlipRing:
        #c1.mirror(c1.ports['o1'].center, (c1.ports['o1'].center[0]+1, c1.ports['o1'].center[1]))
        p1.mirror((0,0), (1,0))
        p2.mirror((0,0), (1,0))
    
    # move ring paths in place
    p1.connect('o1', destination=c1.ports['o2'])
    p2.connect('o1', destination=c2.ports['o2'])
    
    # add top couplers
    c3 = c << half_coupler
    c3.mirror()
    c4 = c << half_coupler
    
    c3.connect('o2', destination=p1.ports['o2'])
    c4.connect('o2', destination=p2.ports['o2'])
    
    couplerRoute2 = gf.routing.get_route(c3.ports["o1"], c4.ports["o1"], cross_section=couplerSection)
    c.add(couplerRoute2.references)
    
    # route all that is remaining
    c.add(gf.routing.get_route(e1.ports["o1"], 
                                      c2.ports["o3"],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(e1.ports["o2"], 
                                      c1.ports["o3"],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    c.add(gf.routing.get_route(e2.ports["o1"], 
                                      c4.ports["o3"],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    
    c.add(gf.routing.get_route(e2.ports["o2"], 
                                      c3.ports["o3"],
                                      radius=routingRad,
                                      cross_section=crossSection).references)
    # rr = gf.routing.get_route(p1.ports["o2"], 
    #                                   p2.ports["o2"],
    #                                   radius=baseRad,
    #                                   cross_section=crossSection)
    #c.add(rr.references)
    
    # print(baseRingPath.length())
    # print(couplerDy)
    # print(couplerRoute1.length)
    # print(couplerRoute2.length)
    
    totalLength = (2*baseRingPath.length() + 4*couplerDy 
                   + 2*couplingLength)
    #print(totalLength)
    c << gf.components.text(text = f"{totalLength:.1f}um", 
                            layer = LAYERS.ANNOTATION,
                            position = (c1.center[0], p1.center[1] + 30),
                            justify = "center",
                            size = 25)
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
    m.mirror((0,0),(1,0))
    m.move((0,0), (offsetX,dxdy[1]+edgeSep/2))
    # s bends
    # add s bends to separate paths during long runs
    sBendX = 150
    # use distance between ports of coupler to guage proper dy (like route_sbend)
    couplerPortSep = (m.ports["o1"].center - m.ports["o2"].center)[1]
    sBendY = (edgeSep - couplerPortSep)/2
    baseSbend = gf.components.bend_s(size=(sBendX, sBendY), 
                                     cross_section=crossSection)
    s1 = c << baseSbend
    s2 = c << baseSbend
    s3 = c << baseSbend
    s4 = c << baseSbend
    
    s1.mirror((0,0),(0,1))
    s3.mirror((0,0),(0,1))
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
                            position = (m.center[0], m.center[1]),
                            justify = "center",
                            size = 25)
    return c