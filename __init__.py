import gdsfactory as gf
from gdsfactory.technology import LayerMap
from gdsfactory.typings import Layer

""" Library of common tools and components for waveguide layout in UCSD UNO group.
 Also includes standard layer assignments etc, similar to Applied Nanotools'
 Naming conventions:
     classes: CapWords
     functions: lowercase_with_underscores
     local variables: camelCase (for legacy reasons)
"""
class Settings:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Settings, cls).__new__(cls)
        return cls.instance
    # recommended way to reference layers: from uno_layout import LAYERS
    # then you can simply do LAYERS.WG etc everywhere
    DEFAULT_WG_WIDTH = 0.5
    DEFAULT_RADIUS = 25
    DEFAULT_EDGE_SEP = 100
    DEFAULT_ROUTE_WIDTH = 25
    DEFAULT_TEXT_SIZE = 50
    DEFAULT_DXDY = 30

class LayerMapUNO:#(LayerMap):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(LayerMapUNO, cls).__new__(cls)
        return cls.instance
    # this is the recommended way to reference layers. 
    WG: Layer = (1,0) # waveguide
    LABEL: Layer = (2,0) # waveguide-layer labels written at a lower E beam res
    BOSCH: Layer = (7,0) # deep trench etch for edge couplers and thermals
    HEATER: Layer = (11, 0) # high resistance heaters (e.g, TiW)
    ROUTING: Layer = (12, 0) # low resistance routing (e.g, TiW/Al bilayer)
    PAD: Layer = (13, 0) # opening in oxide passivation for heater pads
    
    FLOORPLAN: Layer = (100, 0) # design area
    DIE: Layer = (101,0) # physical size of die
    SEM: Layer = (200, 0) # regions you want to image with SEM
    ANT_EDGE_TRENCH: Layer = (201, 0)
    ANT_HANDLING: Layer = (202, 0)
    ANT_THERMAL_TRENCH: Layer = (203, 0)
    ANNOTATION: Layer = (210, 0) # gds-only annotations, not printed


def waveguide_xs(width=None, layer=None, radius=None):
    width = Settings.DEFAULT_WG_WIDTH if width is None else width
    layer = LayerMapUNO.WG if layer is None else layer
    radius = Settings.DEFAULT_RADIUS if radius is None else radius
    # returns a simple waveguide cross-section so we don't have to deal with
    # annoying Section and CrossSection synax all the time
    # default if passed None:
    #wgWidth = DEFAULT_WG_WIDTH if wgWidth is None else wgWidth
    s0 = gf.Section(
        width=width,
        layer= LayerMapUNO.WG,
        port_names=("o1", "o2"),
        name = "Wvg")
    return gf.CrossSection(sections = [s0], radius = radius)




def routing_xs(rtWidth = Settings.DEFAULT_ROUTE_WIDTH):
    # default if passed None:
    rtWidth = Settings.DEFAULT_ROUTE_WIDTH if rtWidth is None else rtWidth
    return gf.cross_section.cross_section(width = rtWidth, 
                                   layer = Settings.LAYERS.ROUTING,
                                   port_names=('e0', 'e1'),
                                   port_types=('electrical', 'electrical'))

