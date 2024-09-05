import gdsfactory as gf
from uno_layout import LAYERS, DEFAULT_WG_WIDTH, DEFAULT_EDGE_SEP, DEFAULT_ROUTE_WIDTH
import uno_layout.components_wg as uno_wg
import uno_layout.components_heater as uno_ht

@gf.cell
def boschGapTest(tWidthList, 
                 dx = 1000e3, 
                 dy = 1000e3, 
                 tLength = 500e3, 
                 bridge = 50e3):
    c = gf.Component()
    thisDx = dx
    thisDy = dy
    for tWidth in tWidthList:
        thisDx += tWidth/2
        thisRect = c << gf.components.rectangle(size = (tWidth, tLength), 
                                                layer = LAYERS.BOSCH, 
                                                centered = True)
        thisRect.move((thisDx, thisDy))
        thisDx += tWidth/2 + bridge
    return c

@gf.cell
def boschBridgeTest(tBridgeList,
                    tLength = 500e3,
                    tWidth = 100e3,
                    dx = 3100e3,
                    wdy = 3100e3,
                    rdy = 500e3,
                    wgWidth = DEFAULT_WG_WIDTH,
                    edgeSep = DEFAULT_EDGE_SEP):
    # run waveguides through bosch "bridges" to see what's safe
    # dx and wdy refer to dx and dy of first waveguide - first Bosch will be closer in    
    c = gf.Component()
    
    rectDx = dx
    rectDy = rdy
    
    wgDx = dx
    wgDy = wdy
    thisRect = c << gf.components.rectangle(size = (tWidth, tLength), 
                                            layer = LAYERS.BOSCH, 
                                            centered = True)
    thisRect.move((rectDx, rectDy))
    rectDx += tWidth
    wgDx += tWidth/2
    
    for tBridgeIdx in enumerate(tBridgeList):
        tBridge = tBridgeIdx[1]
        rectDx += tBridge
        thisRect = c << gf.components.rectangle(size = (tWidth, tLength), 
                                                layer = LAYERS.BOSCH, 
                                                centered = True)
        thisRect.move((rectDx, rectDy))
        rectDx += tWidth
        wgDx += tBridge/2
        c << uno_wg.straight_waveguide(wgDx, wgDy, wgWidth,
                                labelIn = f"B{tBridgeIdx[0]}", 
                                labelOut = f"B{tBridgeIdx[0]}")
        wgDx += tBridge/2 + tWidth
        wgDy += edgeSep
    return c

@gf.cell
def routingTestStructure(padSep = 1000e3, width = DEFAULT_ROUTE_WIDTH):
    c = gf.Component()
    p1 = c << uno_ht.rectPad()
    p2 = c << uno_ht.rectPad()
    p2.rotate(180)
    p2.move((0, padSep))
    thisSection = gf.cross_section.cross_section(width = width, 
                                                 layer = LAYERS.ROUTING)
    route = gf.routing.get_route_electrical(
        p1.ports["e0"], p2.ports["e0"], cross_section = thisSection
    )
    c.add(route.references)
    
    return c

@gf.cell
def straightHeaterTestStructure(padSep = 1000e3, heaterLength = 500e3, width = 25e3):
    c = gf.Component()
    p1 = c << uno_ht.rectPad()
    p2 = c << uno_ht.rectPad()
    p2.rotate(180)
    p2.move((0, padSep))
    h = c << uno_ht.rect_heater(heaterLength, width)
    h.move((0, padSep/2))
    thisSection = gf.cross_section.cross_section(width = max(width, DEFAULT_ROUTE_WIDTH), 
                                                 layer = LAYERS.ROUTING)
    c.add(gf.routing.get_route_electrical(
        p1.ports["e0"], h.ports["e0"], cross_section = thisSection
    ).references)
    c.add(gf.routing.get_route_electrical(
        p2.ports["e0"], h.ports["e1"], cross_section = thisSection
    ).references)
    return c

@gf.cell
def snakeHeaterTestStructure(padSep = 1000e3, hLength = 500e3, hNum = 7, hSpacing = 25e3, width = 10e3):
    c = gf.Component()
    p1 = c << uno_ht.rectPad()
    p2 = c << uno_ht.rectPad()
    p2.rotate(180)
    p2.move((0, padSep))
    h = c << uno_ht.snake_heater(hLength, hNum, hSpacing, width)
    h.move((0, padSep/2))
    thisSection = gf.cross_section.cross_section(width = max(width, DEFAULT_ROUTE_WIDTH), 
                                                 layer = LAYERS.ROUTING)
    c.add(gf.routing.get_route_electrical(
        p1.ports["e0"], h.ports["e0"], cross_section = thisSection
    ).references)
    c.add(gf.routing.get_route_electrical(
        p2.ports["e0"], h.ports["e1"], cross_section = thisSection
    ).references)
    return c
