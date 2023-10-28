import math, Geometry3D, logging, sqlite3, os, pathlib
import numpy as np

class collision_dectector():
    """ A class to allow for the dectection and avoidence of hazards on a field. """
    def __init__(self, field_dimensions: tuple, drone_radius: float, hazards: list = []) -> None:
        """ Will use hazards stored in database.db, unless other hazards are given. """
        self.field_length = field_dimensions[0]
        self.field_width = field_dimensions[1]
        self.field_height = field_dimensions[2]
        self.AVR_rad = drone_radius
        self.hazards = []
        self.field_rec = geo3D_rect(self.field_length, self.field_width, self.field_height)
        os.chdir(pathlib.Path(__file__).parent.resolve())
        if not hazards:
            with sqlite3.connect('database.db') as conn:
                c = conn.cursor()
                c.execute("""SELECT * FROM hazards""")
                for row in c:
                    self.hazards.append((eval(row[0]), row[1], eval(row[2])))
        
    def path_check(self, start_pos: tuple, end_pos: tuple) -> list:
        """ Checks path for hazards and field out.\n\nReturns a list of objects path collides with. """
        path_clear = True
        collided_geo = []
        flight_path = Geometry3D.Cylinder(Geometry3D.Point(list(start_pos)), self.AVR_rad, Geometry3D.Vector(np.subtract(end_pos, start_pos)))
        if not Geometry3D.intersection(Geometry3D.Point(list(end_pos)), self.field_rec):
            path_clear = False
            logging.warning(f'[{start_pos} -> {end_pos}] Results in AVR moving out of bounds, comand canceled.')
        if self.hazards:
            for hazard in self.hazards:
                hazard_geo = Geometry3D.Cylinder(Geometry3D.Point(list(hazard[0])), hazard[1], Geometry3D.Vector(list(hazard[2])))
                if Geometry3D.intersection(flight_path, hazard_geo):
                    path_clear = False
                    collided_geo.append(hazard_geo)
                    logging.warning(f'[{start_pos} -> {end_pos}] Results in AVR hitting hazard at {hazard[0]}')
        return collided_geo
    
    def path_find(self, start: tuple, end: tuple) -> list:
        """  Finds list of positions to reach position with out hitting a hazard.\n\nReturns a list of tuples. Ex: [(x, y, z), (x2, y2, z2), ...]"""
        collided_geos = self.path_check(start, end)
        nodes = []
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("""SELECT * FROM path_nodes""")
            for row in c:
                nodes.append((eval(row[0]), row[1]))
        node_size = (self.field_length/int(self.field_length/self.AVR_rad-0.5), self.field_width/int(self.field_width/self.AVR_rad-0.5), self.field_height/int(self.field_height/self.AVR_rad-0.5))
        # Define the surrounding nodes in 3D space
        surrounding_nodes = [
            (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)
        ]

        def heuristic(node):
            return ((node[0] - end[0])**2+(node[1] - end[1])**2+(node[2] - end[2])**2)**0.5 # Direct dist
            return abs(node[0] - end[0]) + abs(node[1] - end[1]) + abs(node[2] - end[2])  # Grid dist

        def get_neighbors(node):
            neighbors = []
            for dx, dy, dz in surrounding_nodes:
                x, y, z = node[0] + dx, node[1] + dy, node[2] + dz
                if (
                    0 <= x < len(nodes[0][0]) and
                    0 <= y < len(nodes[0]) and
                    0 <= z < len(nodes) and
                    nodes[z][y][x] != 1
                ):
                    neighbors.append((x, y, z))
            return neighbors

        open_set = [start]
        came_from = {}
        g_score = {(x, y, z): float('inf') for z, layer in enumerate(nodes) for y, row in enumerate(layer) for x, _ in enumerate(row)}
        g_score[start] = 0
        f_score = {(x, y, z): float('inf') for z, layer in enumerate(nodes) for y, row in enumerate(layer) for x, _ in enumerate(row)}
        f_score[start] = heuristic(start)

        while open_set:
            current = min(open_set, key=lambda node: f_score[node])

            if current == end:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                # Path cleanup
                # Get rid of extraneous path nodes
                opti_path = [path[0]]
                prev_node = None
                print(path)
                for i in range(len(path)):
                    if i+1 > len(path)-1:
                        break
                    for j in range(len(path[i+1])):
                        if abs(path[i+1][j] - path[i][j]) == 1:
                            k=i
                            while abs(path[k+1][j] - path[k][j]) == 1:
                                k+=1
                                if k+1 > len(path)-1:
                                    break
                            print(path[k])
                            opti_path.append(path[k])
                            break
                opti_path = [i for n, i in enumerate(opti_path) if i not in opti_path[:n]]
                # Shorten path by turning repeated turns into diagonals
                smooth_path = [opti_path[0]]
                for i in range(len(path)):
                    j = i+1
                    while j in range(len(path)):
                        print(path[i], path[j])
                        collided = False 
                        for geo in collided_geos:
                            if Geometry3D.intersection(geo, Geometry3D.Cylinder(Geometry3D.Point(list(path[i])), self.AVR_rad, Geometry3D.Vector(np.subtract(path[j], path[i])))):
                                smooth_path.append(path[j-1])
                                smooth_path.append(path[j])
                                break
                        if collided:
                            i = j
                            break
                        j+=1
                # Adjust path to center of nodes
                for node in smooth_path:
                    node = tuple(np.add(node, np.divide(node_size, 2)))
                return smooth_path

            open_set.remove(current)
            for neighbor in get_neighbors(current):
                tentative_g_score = g_score[current] + 1
                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic(neighbor)
                    if neighbor not in open_set:
                        open_set.append(neighbor)

        print("No valid path found")
        return None
        
                        
def data_for_cylinder_along_z(center_x,center_y,radius,height_z, start_z = 0):
    z = np.linspace(start_z, height_z, 50)
    theta = np.linspace(0, 2*np.pi, 50)
    theta_grid, z_grid=np.meshgrid(theta, z)
    x_grid = radius*np.cos(theta_grid) + center_x
    y_grid = radius*np.sin(theta_grid) + center_y
    return x_grid,y_grid,z_grid
def geo3D_rect(length: int, width: int, height: int, pos: tuple = (0, 0, 0)) -> Geometry3D.ConvexPolyhedron:
    """ Function that creates a 3d rectangle based on the length, width and height parameters\n\nReturns a Geometry3D.ConvexPolyhedron object."""
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
    return point.x, point.y, point.z