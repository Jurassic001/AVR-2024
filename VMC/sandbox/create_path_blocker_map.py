import Geometry3D, sqlite3, os, pathlib
from collision_avoidance import *
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

field_dimensions = (472, 170, 200)
field_length, field_width, field_height = field_dimensions
AVR_rad = 17.3622

hazards = []

os.chdir(pathlib.Path(__file__).parent.resolve())
print(os.getcwd())
with sqlite3.connect('database.db') as conn:
    c = conn.cursor()
    c.execute("""SELECT * FROM hazards""")
    for row in c:
        hazards.append((eval(row[0]), row[1], eval(row[2])))

collider = collision_dectector(field_dimensions, AVR_rad, hazards)

node_size = (field_length/int(field_length/AVR_rad-0.5), field_width/int(field_width/AVR_rad-0.5), field_height/int(field_height/AVR_rad-0.5))

print(node_size, field_dimensions)
print(int(field_length/node_size[0]), int(field_width/node_size[1]), int(field_height/node_size[2]))
nodes = [[[None for _ in range(int(field_length/node_size[0]))] for _ in range(int(field_width/node_size[1]))] for _ in range(int(field_height/node_size[2]))]
blocked_nodes = []
for z, h in enumerate(nodes):
    for y, w in enumerate(h):
        for x, node in enumerate(w):
            node_block = geo3D_rect(node_size[0], node_size[1], node_size[2], (x * node_size[0], y * node_size[1], z * node_size[2]))
            blocked = False
            for hazard in hazards:
                hit = None
                if Geometry3D.intersection(Geometry3D.Cylinder(Geometry3D.Point(list(hazard[0])), hazard[1], Geometry3D.Vector(list(hazard[2]))), node_block):
                    blocked = True
                    hit = hazard[0]
                    break
            print((x, y, z), hit, blocked)
            node = blocked
            blocked_nodes.append((x, y, z))
            
print(blocked_nodes)
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
x, y, z = zip(*blocked_nodes)
# Plot the points
ax.scatter(x, y, z, c='r', marker='s')
ax.set_xlim(0, len(nodes[0][0])-1)
ax.set_ylim(0, len(nodes[0])-1)
ax.set_zlim(0, len(nodes)-1)
ax.set_xlabel('Length')
ax.set_ylabel('Width')
ax.set_zlabel('Height')
plt.tight_layout()
# Show the plot
plt.show()