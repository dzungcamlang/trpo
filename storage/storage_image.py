import cv2
from utils import *
from parameters import pms


class Storage(object):
    def __init__(self, agent, env, baseline):
        self.paths = []
        self.env = env
        self.agent = agent
        self.obs = []
        self.obs_origin = []
        self.baseline = baseline

    def get_single_path(self):
        self.obs_origin, self.obs, actions, rewards, action_dists = [], [], [], [], []
        ob = self.env.reset()
        ob = self.env.render('rgb_array')
        # self.agent.prev_action *= 0.0
        # self.agent.prev_obs *= 0.0
        episode_steps = 0
        for _ in xrange(pms.max_path_length):
            self.obs_origin.append(ob)
            deal_ob = self.deal_image(ob)
            action, action_dist = self.agent.get_action(deal_ob)
            self.obs.append(deal_ob)
            actions.append(action)
            action_dists.append(action_dist)
            res = self.env.step(action) # res
            if pms.render:
                self.env.render()
            ob = res[0]
            ob = self.env.render('rgb_array')
            rewards.append([res[1]])
            episode_steps += 1
            if res[2]:
                break
        path = dict(
            observations=np.concatenate([self.obs]),
            agent_infos=np.concatenate([action_dists]),
            rewards=np.array(rewards),
            actions=np.array(actions),
            episode_steps=episode_steps
        )
        self.paths.append(path)
        # self.agent.prev_action *= 0.0
        # self.agent.prev_obs *= 0.0
        return path

    def get_paths(self):
        paths = self.paths
        self.paths = []
        return paths

    def process_paths(self, paths):
        sum_episode_steps = 0
        for path in paths:
            sum_episode_steps += path['episode_steps']
            # r_t+V(S_{t+1})-V(S_t) = returns-baseline
            # path_baselines = np.append(self.baseline.predict(path) , 0)
            # # r_t+V(S_{t+1})-V(S_t) = returns-baseline
            # path["advantages"] = np.concatenate(path["rewards"]) + \
            #          pms.discount * path_baselines[1:] - \
            #          path_baselines[:-1]
            # path["returns"] = np.concatenate(discount(path["rewards"], pms.discount))
            path_baselines = np.append(self.baseline.predict(path) , 0)
            deltas = np.concatenate(path["rewards"]) + \
                     pms.discount * path_baselines[1:] - \
                     path_baselines[:-1]
            path["advantages"] = discount(
                deltas , pms.discount * pms.gae_lambda)
            path["returns"] = np.concatenate(discount(path["rewards"] , pms.discount))
        # Updating policy.
        action_dist_n = np.concatenate([path["agent_infos"] for path in paths])
        obs_n = np.concatenate([path["observations"] for path in paths])
        action_n = np.concatenate([path["actions"] for path in paths])
        rewards = np.concatenate([path["rewards"] for path in paths])
        advantages = np.concatenate([path["advantages"] for path in paths])

        if pms.center_adv:
            advantages = (advantages - np.mean(advantages)) / (advantages.std() + 1e-8)

        self.baseline.fit(paths)

        samples_data = dict(
            observations=obs_n,
            actions=action_n,
            rewards=rewards,
            advantages=advantages,
            agent_infos=action_dist_n,
            paths=paths,
            sum_episode_steps=sum_episode_steps
        )
        return samples_data

    def deal_image(self, image):
        index = len(self.obs_origin)
        image_end = []
        if index<pms.history_number:
            image_end = self.obs_origin[0:index]
            for i in range(pms.history_number-index):
                image_end.append(image)
        else:
            image_end = self.obs_origin[index-pms.history_number:index]

        image_end = np.concatenate(image_end)
        # image_end = image_end.reshape((pms.obs_height, pms.obs_width, pms.history_number))
        obs = cv2.resize(cv2.cvtColor(image_end, cv2.COLOR_RGB2GRAY) / 255., (pms.obs_height, pms.obs_width))
        return np.expand_dims(obs, 0)