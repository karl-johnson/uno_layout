import numpy as np
import gdsfactory as gf
from uno_layout import LAYERS, DEFAULT_ROUTE_WIDTH, DEFAULT_TEXT_SIZE, routing_xs

@gf.cell
def rect_heater(length = 50e0, width = 10e0, routeWidth = None):
    # legacy method of construction, could be replaced with simple Path
    c = gf.Component()
    c << gf.components.rectangle(size = (width, length), 
                                         layer = LAYERS.HEATER, 
                                         centered = True)
    xs = routing_xs(routeWidth)
    c.add_port('e0', center = (0, -length/2), orientation = -90, 
               cross_section=xs)
    c.add_port('e1', center = (0, length/2), orientation = 90, 
               cross_section=xs)
    return c

@gf.cell
def rectPad(width = 200e0,
            height = 150e0,
            openingInset = 30e0,
            routeWidth = None):
    c = gf.Component()
    c << gf.components.rectangle(size = (width, height), 
                                         layer = LAYERS.ROUTING, 
                                         centered = True)
    c << gf.components.rectangle(size = (width - openingInset, 
                                         height - openingInset), 
                                         layer = LAYERS.PAD, 
                                         centered = True)
    routeWidth = DEFAULT_ROUTE_WIDTH if routeWidth is None else routeWidth
    c.add_port('e0', layer = LAYERS.ROUTING, width = routeWidth, 
               center = (0, height/2), orientation = 90, 
               )
    return c

# copy-pasted gdsfactory pad array and simplified it
@gf.cell
def pad_array(
    pad: gf.Component,
    spacing: tuple[float, float] = (150.0e0, 150.0e0),
    columns: int = 6,
    rows: int = 1,
    cross_section: gf.CrossSection = routing_xs(),
    pad_rotation: int = 0,
    ) -> gf.Component:
    """Returns 2D array of pads with incremented electrical port #'s
    """
    c = gf.Component()
    c.add_ref(pad, columns=columns, rows=rows, spacing=spacing)
    for col in range(columns):
        for row in range(rows):
            thisPad = (c << pad).rotate(pad_rotation).dmove((col * spacing[0], row * spacing[1]))
            c.add_port(name = f"e{row+1}{col+1}", port =  thisPad.ports['e0'])
    return c

@gf.cell
def snake_heater(length = 1000e0,
                 N = 5e0,
                 spacing = 25e0,
                 width = 10e0,
                 extraEnds = 50e0,
                 rotateAngle = 0e0):
    thisSection = gf.cross_section.cross_section(width = width, 
                                                 layer = LAYERS.HEATER,
                                                 port_names=('e0', 'e1'))
    # N = 0 is just straight. every N after that alternates forward/back
    points = []
    lastX = 0
    lastY = 0
    for idx in range(N):
        point1 = (lastX, lastY)
        point2 = (lastX, lastY + length)
        if(idx % 2 == 0):
            points.append(point1)
            points.append(point2)
        else:
            points.append(point2)
            points.append(point1)
        lastX += spacing
    
    # add some extra length at ends as it often makes routing easier
    points.insert(0, (0, -extraEnds))
    if(N % 2 == 0):
        points.append((lastX - spacing, -extraEnds))
    else:
        points.append((lastX - spacing, length + extraEnds))
    
    P = gf.Path(points)
    P.dmovex(-spacing*(N-1)/2)
    P.dmovey(-length/2)
    P.rotate(rotateAngle)
    c = gf.Component()
    snake = c << gf.path.extrude(P, thisSection)
    c << gf.components.text(text = f"{1e-3*P.length():.0f}mm/{width:.2f}um = {P.length()/width:.1f}", 
                            layer = LAYERS.ANNOTATION,
                            position = np.array(snake.dcenter) - np.array((0,2*DEFAULT_TEXT_SIZE)),
                            justify = "center",
                            size = DEFAULT_TEXT_SIZE)
    c.add_ports(snake.ports)
    return c