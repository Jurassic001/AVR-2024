import math, Geometry3D, logging, heapq
import numpy as np

class collision_dectector():
    def __init__(self, field_dimensions: tuple, drone_radius: float, hazards: list = []) -> None:
        self.field_length = field_dimensions[0]
        self.field_width = field_dimensions[1]
        self.field_height = field_dimensions[2]
        self.AVR_rad = drone_radius
        self.hazards = hazards
        self.field_rec = self.geo3D_rect(self.field_length, self.field_width, self.field_height)
        
    def path_check(self, start_pos: tuple, end_pos: tuple) -> list:
        """ Checks path for hazards and field out.\n\nReturns a list of objects path collides with. """
        path_clear = True
        collided_geo = []
        flight_path = Geometry3D.Cylinder(Geometry3D.Point(list(start_pos)), self.AVR_rad, Geometry3D.Vector(np.subtract(end_pos, start_pos)))
        if not Geometry3D.intersection(Geometry3D.Point(list(end_pos)), self.field_rec):
            path_clear = False
            logging.warning(f'({start_pos} -> {end_pos}) Results in AVR moving out of bounds, comand canceled.')
        if self.hazards:
            for hazard in self.hazards:
                hazard_geo = Geometry3D.Cylinder(Geometry3D.Point(list(hazard[0])), hazard[1], Geometry3D.Vector(list(hazard[2])))
                if Geometry3D.intersection(flight_path, hazard_geo):
                    path_clear = False
                    collided_geo.append(hazard_geo)
                    logging.warning(f'({start_pos} -> {end_pos}) Results in AVR hitting hazard at {hazard[0]}')
        return collided_geo
    
    def path_find(self, start_pos: tuple, end_pos: tuple) -> list:
        """  Finds list of positions to reach position with out hitting a hazard.\n\nReturns a list of tuples. Ex: [(x, y, z), (x2, y2, z2), ...]"""
        collided_geos = self.path_check(start_pos, end_pos)
        node_size = (self.field_length/self.AVR_rad, self.field_width/self.AVR_rad, self.field_height/self.AVR_rad)
        node_field = [[[None]*self.field_height/node_size[2]]*self.field_length/node_size[0]]*self.field_width/node_size[1]
        for y, w in enumerate(node_field):
            for x, l in enumerate(w):
                for z, h in enumerate(l):
                    node_block = self.geo3D_rect(node_size[0], node_size[1], node_size[2], (x * node_size[0], y * node_size[1], z * node_size[2]))
                    h = False
                    for geo in collided_geos:
                        if Geometry3D.intersection(geo, node_block):
                            h = True
                            break
        
                        
    def data_for_cylinder_along_z(self, center_x,center_y,radius,height_z, start_z = 0):
        z = np.linspace(start_z, height_z, 50)
        theta = np.linspace(0, 2*np.pi, 50)
        theta_grid, z_grid=np.meshgrid(theta, z)
        x_grid = radius*np.cos(theta_grid) + center_x
        y_grid = radius*np.sin(theta_grid) + center_y
        return x_grid,y_grid,z_grid
    def geo3D_rect(self, length: int, width: int, height: int, pos: tuple = (0, 0, 0)):
        """ function that creates a 3d rectangle based on the length, width and heigh parameters """
        a = Geometry3D.Point(list(pos))
        b = Geometry3D.Point(list(np.add(pos, (length, 0, 0))))
        c = Geometry3D.Point(list(np.add(pos, (0, width, 0))))
        d = Geometry3D.Point(list(np.add(pos, (length, width, 0))))
        e = Geometry3D.Point(list(np.add(pos, (0, 0, height))))
        f = Geometry3D.Point(list(np.add(pos, (length, 0, height))))
        g = Geometry3D.Point(list(np.add(pos, (0, width, height))))
        h = Geometry3D.Point(list(np.add(pos, (length, width, height))))
        field_face0 = Geometry3D.ConvexPolygon((a, b, c, d))
        field_face1 = Geometry3D.ConvexPolygon((a, b, f, e))
        field_face2 = Geometry3D.ConvexPolygon((a, c, g, e))
        field_face3 = Geometry3D.ConvexPolygon((c, d, h, g))
        field_face4 = Geometry3D.ConvexPolygon((b, d, h, f))
        field_face5 = Geometry3D.ConvexPolygon((e, f, h, g))
        return Geometry3D.ConvexPolyhedron((field_face0,field_face1,field_face2,field_face3,field_face4,field_face5))
    
    def geoPoint_to_tuple(self, point: Geometry3D.Point):
        return (point.x, point.y, point.z)
    
class Node:
    def __init__(self, x, y, z, cost, parent = None):
        self.x = x
        self.y = y
        self.z = z
        self.cost = cost
        self.parent = parent
        
    def __lt__(self, other):
        return self.cost < other.cost