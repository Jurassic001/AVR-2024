from collision_avoidance import collision_dectector
from data import HAZARD_LIST

test = collision_dectector((472, 170, 200), 17.3622, HAZARD_LIST)

print(test.path_find((180, 80, 10), (450, 120, 85)))