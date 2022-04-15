import gym
import numpy as np
import math
import pybullet as p
from .ball import Ball
from .plane import Plane
from .turtlebot import Car
from .walls import Walls
import matplotlib.pyplot as plt
from typing import Generic

class TurtleRLEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, *args, **kwargs):
        super(Generic,self).__init__()
        self.action_space = gym.spaces.box.Box(
            low=np.array([0, -.6], dtype=np.float32),
            high=np.array([1, .6], dtype=np.float32))
        self.observation_space = gym.spaces.box.Box(
            low=np.array([-10, -10, -1, -1, -5, -5, -10, -10], dtype=np.float32),
            high=np.array([10, 10, 1, 1, 5, 5, 10, 10], dtype=np.float32))
        self.np_random, _ = gym.utils.seeding.np_random()

        if kwargs["env_type"] == "gui":
            self.client = p.connect(p.GUI)
        else:
            self.client = p.connect(p.DIRECT)
        # Reduce length of episodes for RL algorithms
        p.setTimeStep(1/30, self.client)

        self.car = None
        self.goal = None
        self.done = False
        self.prev_dist_to_goal = None
        self.rendered_img = None
        self.render_rot_matrix = None
        self.reset()

    def step(self, action):
        # Feed action to the car and get observation of car's state
        self.car.apply_action(action)
        p.stepSimulation()
        car_ob = self.car.get_observation()

        # Compute reward as L2 change in distance to goal
        dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
                                  (car_ob[1] - self.goal[1]) ** 2))
        if self.prev_dist_to_goal == None:
            reward = 0    
        else:
            reward = max(self.prev_dist_to_goal - dist_to_goal, 0)
        self.prev_dist_to_goal = dist_to_goal

        # Done by running off boundaries
        if (car_ob[0] >= 10 or car_ob[0] <= -10 or
                car_ob[1] >= 10 or car_ob[1] <= -10):
            self.done = True
        # Done by reaching goal
        elif dist_to_goal < .5:
            self.done = True
            reward = 50

        self.render('gui')
        img_array = self.rendered_img.make_image(None,magnification=1/3.69)
        img_array = img_array[0][0:50,0:100,1]
        return img_array, reward, self.done, dict()
        #ob = np.array(car_ob + self.goal, dtype=np.float32)
        #return ob, reward, self.done, dict()

    def seed(self, seed=None):
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        return [seed]

    def reset(self):
        p.resetSimulation(self.client)
        p.setGravity(0, 0, -10)
        # Reload the plane and car
        Plane(self.client)
        Walls(self.client)
        self.car = Car(self.client)

        # Set the goal to a random target
        x = (self.np_random.uniform(1, 1.5) if self.np_random.randint(2) else
             self.np_random.uniform(-1, -1.5))
        y = (self.np_random.uniform(1, 1.5) if self.np_random.randint(2) else
             self.np_random.uniform(-1, -1.5))
        self.goal = (x, y)
        self.done = False

        # Visual element of the goal
        Ball(self.client, self.goal)

        # Get observation to return
        car_ob = self.car.get_observation()

        self.prev_dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
                                           (car_ob[1] - self.goal[1]) ** 2))
        #return np.array(car_ob + self.goal, dtype=np.float32)
        self.render('gui')
        img_array = self.rendered_img.make_image(None,magnification=1/3.69)
        img_array = img_array[0][0:50,0:100,1]
        return img_array

    def render(self, mode='human'):
        if self.rendered_img is None:
            self.rendered_img = plt.imshow(np.zeros((100, 100, 4)))

        # Base information
        car_id, client_id = self.car.get_ids()
        proj_matrix = p.computeProjectionMatrixFOV(fov=80, aspect=1,
                                                   nearVal=0.01, farVal=100)
        pos, ori = [list(l) for l in
                    p.getBasePositionAndOrientation(car_id, client_id)]
        pos[2] = 0.3148

        # Rotate camera direction
        rot_mat = np.array(p.getMatrixFromQuaternion(ori)).reshape(3, 3)
        camera_vec = np.matmul(rot_mat, [1, 0, 0])
        up_vec = np.matmul(rot_mat, np.array([0, 0, 1]))
        view_matrix = p.computeViewMatrix(pos, pos + camera_vec, up_vec)

        # Display image
        frame = p.getCameraImage(100, 100, view_matrix, proj_matrix)[2]
        frame = np.reshape(frame, (100, 100, 4))
        self.rendered_img.set_data(frame)
        
        if mode == 'human':
            plt.draw()
            plt.pause(.00001)

    def close(self):
        p.disconnect(self.client)